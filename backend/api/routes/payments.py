import asyncio
from typing import Any, List, Optional, Dict
from uuid import UUID
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, func
from sqlalchemy.orm import selectinload
from pydantic import BaseModel

from backend.core.database import get_db
from backend.api.deps import get_current_user
from backend.models.user import User
from backend.models.payment import Payment
from backend.models.order import Order, OrderItem
from backend.models.outlet import Outlet
from backend.models.shift import Shift, ShiftStatus
from backend.schemas.payment import PaymentCreate, PaymentResponse, PaymentStatus, PaymentMethod
from backend.schemas.order import OrderStatus
from backend.schemas.response import StandardResponse
from backend.services.audit import log_audit
from backend.services.xendit import xendit_service
from backend.utils.encryption import decrypt_field
from backend.services.fonnte import send_whatsapp_message
from backend.models.event import Event

router = APIRouter()


async def _try_earn_loyalty_points(db: AsyncSession, order: Order, outlet_id: UUID, user_id: UUID, tenant_id: UUID):
    """Auto-earn loyalty points setelah order fully paid. Pro+ only, silently skip jika gagal."""
    try:
        if not order.customer_id:
            return
        from backend.models.tenant import Tenant
        tenant = (await db.execute(
            select(Tenant).where(Tenant.id == tenant_id)
        )).scalar_one_or_none()
        if not tenant:
            return
        raw_tier = getattr(tenant, "subscription_tier", "starter") or "starter"
        tier = raw_tier.value if hasattr(raw_tier, 'value') else str(raw_tier)
        if tier.lower() not in {"pro", "business", "enterprise"}:
            return

        from backend.models.loyalty import CustomerPoints, PointTransaction
        POINTS_PER_RUPIAH = 10_000

        # Idempotency check — Rule #35
        existing = (await db.execute(
            select(PointTransaction).where(
                PointTransaction.order_id == order.id,
                PointTransaction.type == 'earn',
            )
        )).scalar_one_or_none()
        if existing:
            return

        points_earned = int(float(order.total_amount) // POINTS_PER_RUPIAH)
        if points_earned == 0:
            return

        cp = (await db.execute(
            select(CustomerPoints).where(
                CustomerPoints.customer_id == order.customer_id,
                CustomerPoints.outlet_id == outlet_id,
                CustomerPoints.deleted_at.is_(None),
            ).with_for_update()
        )).scalar_one_or_none()

        if not cp:
            cp = CustomerPoints(
                customer_id=order.customer_id,
                outlet_id=outlet_id,
                balance=0,
                lifetime_earned=0,
            )
            db.add(cp)
            await db.flush()

        cp.balance += points_earned
        cp.lifetime_earned += points_earned
        cp.row_version += 1

        txn = PointTransaction(
            customer_id=order.customer_id,
            outlet_id=outlet_id,
            order_id=order.id,
            type='earn',
            points=points_earned,
            description=f"Earn dari transaksi Rp{int(order.total_amount):,}",
        )
        db.add(txn)
    except Exception:
        pass  # Loyalty gagal tidak boleh block payment


@router.post("/", response_model=StandardResponse[PaymentResponse])
async def create_payment(
    request: Request,
    payment_in: PaymentCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    """
    Create a new payment.
    """
    # Check idempotency key first to prevent duplicate payments and duplicate WA messages
    if payment_in.idempotency_key:
        existing_payment_query = select(Payment).where(
            Payment.idempotency_key == payment_in.idempotency_key,
            Payment.outlet_id == payment_in.outlet_id
        )
        existing_result = await db.execute(existing_payment_query)
        existing_payment = existing_result.scalar_one_or_none()
        if existing_payment:
            return StandardResponse(
                success=True,
                data=PaymentResponse.model_validate(existing_payment),
                request_id=request.state.request_id,
                message="Payment already processed (idempotent)"
            )

    # Verify order exists if provided (selectinload items+product for receipt)
    if payment_in.order_id:
        order_result = await db.execute(
            select(Order).options(
                selectinload(Order.items).selectinload(OrderItem.product)
            ).where(Order.id == payment_in.order_id)
        )
        order = order_result.scalar_one_or_none()
        if not order or order.deleted_at is not None:
            raise HTTPException(status_code=404, detail="Order tidak ditemukan")
        if order.status == OrderStatus.completed:
            raise HTTPException(status_code=400, detail="Order sudah selesai (sudah dibayar)")
            
    # Determine initial status based on method
    initial_status = PaymentStatus.pending
    paid_at = None
    qris_url = None
    
    if payment_in.payment_method == PaymentMethod.cash:
        initial_status = PaymentStatus.paid
        paid_at = datetime.now(timezone.utc)
        
    # Find active shift for the user in this outlet if not provided
    shift_session_id = payment_in.shift_session_id
    if not shift_session_id:
        shift_query = select(Shift).where(
            Shift.outlet_id == payment_in.outlet_id,
            Shift.user_id == current_user.id,
            Shift.status == ShiftStatus.open,
            Shift.deleted_at.is_(None)
        )
        shift_result = await db.execute(shift_query)
        active_shift = shift_result.scalar_one_or_none()
        if not active_shift:
            raise HTTPException(status_code=400, detail="Anda harus membuka Shift (Buka Kasir) terlebih dahulu sebelum menerima pembayaran.")
        shift_session_id = active_shift.id
        
    # Cash Math Validation
    if payment_in.payment_method == PaymentMethod.cash:
        if payment_in.amount_paid < payment_in.amount_due:
            raise HTTPException(status_code=400, detail="Nominal pembayaran kurang dari total tagihan.")
        # Force calculate change to prevent frontend manipulation
        payment_in.change_amount = payment_in.amount_paid - payment_in.amount_due
        
    # Double QRIS Validation
    if payment_in.payment_method == PaymentMethod.qris and payment_in.order_id:
        pending_qris_query = select(Payment).where(
            Payment.order_id == payment_in.order_id,
            Payment.payment_method == PaymentMethod.qris,
            Payment.status == PaymentStatus.pending,
            Payment.deleted_at.is_(None)
        )
        pending_qris_result = await db.execute(pending_qris_query)
        existing_qris = pending_qris_result.scalar_one_or_none()
        if existing_qris:
            # Return existing QRIS instead of creating a new one
            return StandardResponse(
                success=True,
                data=PaymentResponse.model_validate(existing_qris),
                request_id=request.state.request_id,
                message="QRIS payment already exists and is pending"
            )
        
    payment = Payment(
        order_id=payment_in.order_id,
        outlet_id=payment_in.outlet_id,
        invoice_id=payment_in.invoice_id,
        shift_session_id=shift_session_id,
        payment_method=payment_in.payment_method,
        amount_due=payment_in.amount_due,
        amount_paid=payment_in.amount_paid,
        change_amount=payment_in.change_amount,
        status=initial_status,
        reference_id=payment_in.reference_id,
        idempotency_key=payment_in.idempotency_key,
        is_partial=payment_in.is_partial,
        paid_at=paid_at,
        processed_by=current_user.id
    )
    
    db.add(payment)
    await db.flush() # Get payment.id for Midtrans order_id
    
    # Generate QRIS via Xendit if method is qris
    if payment_in.payment_method == PaymentMethod.qris:
        outlet = await db.get(Outlet, payment_in.outlet_id)
        if not outlet or not outlet.xendit_business_id:
            payment.status = PaymentStatus.failed
            payment.xendit_raw = {"error": "Outlet not configured for Xendit QRIS (Missing Sub-Account ID)"}
        else:
            try:
                xendit_res = await xendit_service.create_qris_transaction(
                    reference_id=f"{current_user.tenant_id}::{payment.id}",
                    amount=float(payment.amount_due),
                    for_user_id=outlet.xendit_business_id
                )
                        
                payment.qris_url = xendit_res.get("qr_string")
                payment.xendit_raw = xendit_res
                # Track QRIS expiry
                expires_at = xendit_res.get("expires_at")
                if expires_at:
                    try:
                        payment.qris_expired_at = datetime.fromisoformat(expires_at.replace("Z", "+00:00"))
                    except (ValueError, AttributeError):
                        pass
                
            except Exception as e:
                payment.status = PaymentStatus.failed
                payment.xendit_raw = {"error": str(e)}
    
    # If cash payment is successful, check if order is fully paid
    if initial_status == PaymentStatus.paid and payment_in.order_id:
        # Calculate total paid so far
        paid_query = select(func.sum(Payment.amount_paid)).where(
            Payment.order_id == payment_in.order_id,
            Payment.status == PaymentStatus.paid,
            Payment.deleted_at.is_(None)
        )
        paid_result = await db.execute(paid_query)
        total_paid_so_far = paid_result.scalar() or 0
        
        # Order is already fetched above
        if total_paid_so_far >= order.total_amount:
            new_order_status = OrderStatus.completed
            # If payment is not tied to a shift, it's an online payment, so set to preparing
            if payment.shift_session_id is None:
                new_order_status = OrderStatus.preparing
                
            order.status = new_order_status
            order.row_version += 1
            
            # Send WA receipt
            if order.customer_id:
                from backend.models.customer import Customer
                from backend.models.user import User as UserModel
                customer = await db.get(Customer, order.customer_id)
                if customer and customer.phone:
                    outlet = await db.get(Outlet, payment_in.outlet_id)
                    outlet_name = outlet.name if outlet else "Kasira"
                    cashier_name = "-"
                    if order.user_id:
                        cashier = await db.get(UserModel, order.user_id)
                        if cashier:
                            cashier_name = cashier.full_name
                    struk = _build_receipt_text(order, outlet_name, cashier_name, payment_in.payment_method)
                    try:
                        asyncio.create_task(
                            send_whatsapp_message(customer.phone, struk)
                        )
                    except Exception:
                        pass  # WA gagal tidak boleh block payment

            # Auto-earn loyalty points (Pro+)
            await _try_earn_loyalty_points(db, order, payment_in.outlet_id, current_user.id, current_user.tenant_id)

    # Append payment event to event store
    pay_evt_type = "payment.completed" if payment.status == PaymentStatus.paid else "payment.pending"
    db.add(Event(
        outlet_id=payment_in.outlet_id,
        stream_id=f"payment:{payment.id}",
        event_type=pay_evt_type,
        event_data={
            "payment_id": str(payment.id),
            "order_id": str(payment_in.order_id) if payment_in.order_id else None,
            "outlet_id": str(payment_in.outlet_id),
            "method": payment.payment_method.value if hasattr(payment.payment_method, 'value') else str(payment.payment_method),
            "amount_due": float(payment.amount_due),
            "amount_paid": float(payment.amount_paid),
            "change_amount": float(payment.change_amount) if payment.change_amount else 0,
            "source": "pos",
        },
        event_metadata={
            "user_id": str(current_user.id),
            "ts": datetime.now(timezone.utc).isoformat(),
        },
    ))

    await db.commit()
    await db.refresh(payment)

    # Audit log
    await log_audit(
        db=db,
        action="CREATE",
        entity="payment",
        entity_id=payment.id,
        after_state={"amount_paid": float(payment.amount_paid), "method": payment.payment_method, "status": payment.status},
        user_id=current_user.id,
        tenant_id=current_user.tenant_id,
    )
    
    return StandardResponse(
        success=True,
        data=PaymentResponse.model_validate(payment),
        request_id=request.state.request_id,
        message="Payment created successfully"
    )

async def _handle_subscription_webhook(db: AsyncSession, data: dict, payload: dict) -> dict:
    """Handle Xendit Invoice webhook for subscription billing."""
    import logging
    _sub_logger = logging.getLogger("subscription_webhook")

    external_id = data.get("external_id", "") or ""
    parts = external_id.split("::")
    if len(parts) != 3 or parts[0] != "sub":
        return {"status": "ok"}

    try:
        tenant_id = UUID(parts[1])
        invoice_id = UUID(parts[2])
    except ValueError:
        return {"status": "ok"}

    from backend.models.subscription_invoice import SubscriptionInvoice
    from backend.models.tenant import Tenant, SubscriptionStatus

    stmt = select(SubscriptionInvoice).where(
        SubscriptionInvoice.id == invoice_id,
        SubscriptionInvoice.tenant_id == tenant_id,
    ).with_for_update()
    result = await db.execute(stmt)
    invoice = result.scalar_one_or_none()

    if not invoice:
        _sub_logger.warning(f"Subscription invoice not found: {invoice_id}")
        return {"status": "ok"}

    xendit_status = str(data.get("status", "")).upper()
    invoice.xendit_raw = payload

    if xendit_status in ("PAID", "SETTLED"):
        if invoice.status != "paid":
            invoice.status = "paid"
            invoice.paid_at = datetime.now(timezone.utc)
            invoice.row_version += 1

            # Reactivate tenant
            tenant = (await db.execute(select(Tenant).where(Tenant.id == tenant_id))).scalar_one_or_none()
            if tenant:
                tenant.subscription_status = SubscriptionStatus.active
                tenant.is_active = True
                tenant.row_version += 1

                await log_audit(
                    db=db, action="SUBSCRIPTION_PAID", entity="subscription_invoices",
                    entity_id=invoice.id,
                    after_state={"amount": invoice.amount, "tier": invoice.tier},
                    user_id=None, tenant_id=tenant.id,
                )

                # Create referral commission if this tenant was referred
                try:
                    from backend.models.referral import Referral, ReferralCommission
                    ref_stmt = select(Referral).where(
                        Referral.referred_tenant_id == tenant_id,
                        Referral.status == "active",
                        Referral.deleted_at == None,
                    )
                    referral = (await db.execute(ref_stmt)).scalar_one_or_none()
                    if referral:
                        # Check idempotency
                        existing_comm = (await db.execute(
                            select(ReferralCommission.id).where(
                                ReferralCommission.invoice_id == invoice.id,
                            )
                        )).scalar_one_or_none()
                        if not existing_comm:
                            commission_amount = int(invoice.amount * referral.commission_pct / 100)
                            comm = ReferralCommission(
                                referral_id=referral.id,
                                invoice_id=invoice.id,
                                referrer_tenant_id=referral.referrer_tenant_id,
                                invoice_amount=invoice.amount,
                                commission_pct=referral.commission_pct,
                                commission_amount=commission_amount,
                                status="pending",
                            )
                            db.add(comm)
                            _sub_logger.info(
                                f"Referral commission created: Rp{commission_amount} "
                                f"for referrer {referral.referrer_tenant_id}"
                            )
                except Exception as e:
                    _sub_logger.error(f"Referral commission error: {e}")

            await db.commit()
            _sub_logger.info(f"Subscription invoice {invoice_id} paid for tenant {tenant_id}")

    elif xendit_status == "EXPIRED":
        if invoice.status not in ("paid", "cancelled"):
            invoice.status = "expired"
            invoice.row_version += 1
            await db.commit()
            _sub_logger.info(f"Subscription invoice {invoice_id} expired")

    return {"status": "ok"}


@router.post("/webhook/xendit")
async def xendit_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Handle Xendit webhook notifications.
    """
    xendit_callback_token = request.headers.get("x-callback-token")
    if not xendit_callback_token or not xendit_service.verify_webhook(xendit_callback_token):
        raise HTTPException(status_code=400, detail="Invalid Verification Token")

    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="Payload must be a JSON object")

    data = payload.get("data", payload)
    if not isinstance(data, dict):
        raise HTTPException(status_code=400, detail="Invalid data field in payload")

    # Check for subscription invoice webhook (external_id starts with "sub::")
    external_id = data.get("external_id", "") or data.get("reference_id", "")
    if isinstance(external_id, str) and external_id.startswith("sub::"):
        return await _handle_subscription_webhook(db, data, payload)

    reference_id_raw = data.get("reference_id", "")
    if "::" not in reference_id_raw:
        return {"status": "ok"}

    tenant_id_str, order_id_str = reference_id_raw.split("::", 1)
    
    try:
        payment_uuid = UUID(order_id_str)
        valid_tenant_id = str(UUID(tenant_id_str))
        # Gunakan tenant_context supaya search_path di-set via get_db dengan validasi
        from backend.core.database import tenant_context
        # Lookup schema_name dari tenant
        from backend.models.tenant import Tenant
        tenant_res = await db.execute(select(Tenant).where(Tenant.id == valid_tenant_id))
        tenant_obj = tenant_res.scalar_one_or_none()
        if not tenant_obj:
            return {"status": "ok"}
        from sqlalchemy import text as sql_text
        from backend.core.database import _SAFE_TENANT_RE
        if not _SAFE_TENANT_RE.match(tenant_obj.schema_name):
            return {"status": "ok"}
        await db.execute(sql_text(f'SET search_path TO "{tenant_obj.schema_name}", public'))
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid reference_id format")
        
    status_code = data.get("status", str(payload.get("status", "")).upper())
    gross_amount = data.get("amount", payload.get("amount", 0))
    
    # Use SELECT FOR UPDATE to prevent race conditions
    stmt = select(Payment).where(Payment.id == payment_uuid).with_for_update()
    result = await db.execute(stmt)
    payment = result.scalar_one_or_none()
    
    if not payment:
        raise HTTPException(status_code=404, detail="Pembayaran tidak ditemukan")
        
    # Determine new status
    new_status = payment.status
    if status_code in ['COMPLETED', 'SUCCEEDED', 'PAID']:
        if float(gross_amount) < float(payment.amount_due):
            new_status = PaymentStatus.failed # Reject if underpaid
        else:
            new_status = PaymentStatus.paid
    elif status_code in ['FAILED', 'EXPIRED']:
        new_status = PaymentStatus.failed

    if new_status != payment.status:
        payment.status = new_status
        payment.xendit_raw = payload
        payment.row_version += 1
        
        if new_status == PaymentStatus.paid:
            payment.paid_at = datetime.now(timezone.utc)
            payment.amount_paid = float(gross_amount) # Use actual paid amount
            
            # Update related order if exists
            if payment.order_id:
                # Calculate total paid
                paid_query = select(func.sum(Payment.amount_paid)).where(
                    Payment.order_id == payment.order_id,
                    Payment.status == PaymentStatus.paid,
                    Payment.id != payment.id, # Exclude current payment as it's not committed yet
                    Payment.deleted_at.is_(None)
                )
                paid_result = await db.execute(paid_query)
                total_paid_so_far = paid_result.scalar() or 0
                
                order = await db.get(Order, payment.order_id)
                total_paid = float(total_paid_so_far) + float(payment.amount_paid)
                
                if order and total_paid >= float(order.total_amount):
                    # If it's an online order payment (no shift), set to preparing so POS knows it needs to be made
                    new_order_status = OrderStatus.completed
                    if payment.shift_session_id is None:
                        new_order_status = OrderStatus.preparing

                    order.status = new_order_status
                    order.row_version += 1

                    # Update connect_order status jika ini storefront order
                    from backend.models.connect import ConnectOrder
                    co_stmt = select(ConnectOrder).where(
                        ConnectOrder.order_id == payment.order_id
                    )
                    co_result = await db.execute(co_stmt)
                    connect_order = co_result.scalar_one_or_none()
                    if connect_order and connect_order.status == 'pending':
                        connect_order.status = 'accepted'  # ENUM: pending/accepted/processing/ready/completed

                    # Send WA receipt
                    if order.customer_id:
                        from backend.models.customer import Customer
                        from backend.models.user import User as UserModel
                        customer = await db.get(Customer, order.customer_id)
                        if customer and customer.phone:
                            outlet = await db.get(Outlet, payment.outlet_id)
                            outlet_name = outlet.name if outlet else "Kasira"
                            cashier_name = "-"
                            if order.user_id:
                                cashier = await db.get(UserModel, order.user_id)
                                if cashier:
                                    cashier_name = cashier.full_name
                            struk = _build_receipt_text(order, outlet_name, cashier_name, payment.payment_method)
                            asyncio.create_task(
                                send_whatsapp_message(customer.phone, struk)
                            )

                    # Auto-earn loyalty points (Pro+)
                    # Use payment.outlet_id; no current_user in webhook context
                    outlet_for_loyalty = await db.get(Outlet, payment.outlet_id)
                    if outlet_for_loyalty:
                        await _try_earn_loyalty_points(
                            db, order, payment.outlet_id,
                            order.user_id or payment.outlet_id,  # fallback if no user
                            outlet_for_loyalty.tenant_id,
                        )

        # Append payment event from webhook
        wh_event_type = "payment.completed" if new_status == PaymentStatus.paid else "payment.failed"
        db.add(Event(
            outlet_id=payment.outlet_id,
            stream_id=f"payment:{payment.id}",
            event_type=wh_event_type,
            event_data={
                "payment_id": str(payment.id),
                "order_id": str(payment.order_id) if payment.order_id else None,
                "outlet_id": str(payment.outlet_id),
                "method": payment.payment_method.value if hasattr(payment.payment_method, 'value') else str(payment.payment_method),
                "amount_due": float(payment.amount_due),
                "amount_paid": float(gross_amount),
                "xendit_status": status_code,
                "source": "xendit_webhook",
            },
            event_metadata={
                "ts": datetime.now(timezone.utc).isoformat(),
            },
        ))

        await db.commit()

    return {"status": "ok"}

@router.get("/{payment_id}/status", response_model=StandardResponse[Dict[str, Any]])
async def get_payment_status(
    request: Request,
    payment_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    """
    Get payment status (polling endpoint for QRIS).
    """
    payment = await db.get(Payment, payment_id)
    if not payment or payment.deleted_at is not None:
        raise HTTPException(status_code=404, detail="Pembayaran tidak ditemukan")
        
    return StandardResponse(
        success=True,
        data={
            "id": str(payment.id),
            "status": payment.status,
            "paid_at": payment.paid_at,
            "qris_url": payment.qris_url
        },
        request_id=request.state.request_id
    )

@router.get("/", response_model=StandardResponse[List[PaymentResponse]])
async def read_payments(
    request: Request,
    outlet_id: UUID,
    order_id: Optional[UUID] = None,
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    """
    Retrieve payments.
    """
    query = select(Payment).where(
        Payment.outlet_id == outlet_id,
        Payment.deleted_at.is_(None)
    )
    
    if order_id:
        query = query.where(Payment.order_id == order_id)
        
    query = query.order_by(Payment.created_at.desc()).offset(skip).limit(limit)
    
    result = await db.execute(query)
    payments = result.scalars().all()
    
    return StandardResponse(
        success=True,
        data=[PaymentResponse.model_validate(p) for p in payments],
        request_id=request.state.request_id
    )

@router.get("/{payment_id}", response_model=StandardResponse[PaymentResponse])
async def read_payment(
    request: Request,
    payment_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    """
    Get payment by ID.
    """
    payment = await db.get(Payment, payment_id)
    if not payment or payment.deleted_at is not None:
        raise HTTPException(status_code=404, detail="Pembayaran tidak ditemukan")

    return StandardResponse(
        success=True,
        data=PaymentResponse.model_validate(payment),
        request_id=request.state.request_id
    )


class SendReceiptRequest(BaseModel):
    order_id: UUID
    phone: str


def _normalize_phone(phone: str) -> str:
    """Normalize phone to international format (62xxx) for Fonnte."""
    p = phone.strip().replace(" ", "").replace("-", "")
    if p.startswith("0"):
        return "62" + p[1:]
    if p.startswith("+"):
        return p[1:]
    return p


def _build_receipt_text(order: Order, outlet_name: str, cashier_name: str, payment_method: str) -> str:
    method_label = {"cash": "Tunai", "qris": "QRIS", "card": "Kartu", "transfer": "Transfer"}.get(payment_method, payment_method.upper())
    lines = [
        f"*Struk Pembayaran*",
        f"📍 {outlet_name}",
        f"No. Order: #{order.display_number}",
        f"Tanggal: {order.created_at.strftime('%d/%m/%Y %H:%M') if order.created_at else '-'}",
        f"Kasir: {cashier_name}",
        f"{'─' * 28}",
    ]
    for item in order.items:
        name = item.product_name or 'Item'
        qty = item.quantity
        price = float(item.unit_price)
        subtotal = float(item.total_price)
        lines.append(f"{name}")
        lines.append(f"  {qty}x Rp{price:,.0f}  =  Rp{subtotal:,.0f}")
    lines.append(f"{'─' * 28}")
    if order.tax_amount and float(order.tax_amount) > 0:
        lines.append(f"Pajak       : Rp{float(order.tax_amount):,.0f}")
    lines.append(f"*Total       : Rp{float(order.total_amount):,.0f}*")
    lines.append(f"Pembayaran  : {method_label}")
    lines.append(f"{'─' * 28}")
    lines.append(f"Terima kasih! 🙏")
    lines.append(f"_Powered by Kasira_")
    return "\n".join(lines)


@router.post("/send-receipt", response_model=StandardResponse[Dict[str, Any]])
async def send_receipt_whatsapp(
    request: Request,
    body: SendReceiptRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    """
    Send receipt via WhatsApp to a given phone number.
    """
    # Load order with items
    result = await db.execute(
        select(Order)
        .options(selectinload(Order.items).selectinload(OrderItem.product))
        .where(Order.id == body.order_id, Order.deleted_at.is_(None))
    )
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="Order tidak ditemukan")

    outlet = await db.get(Outlet, order.outlet_id)
    outlet_name = outlet.name if outlet else "Kasira"

    cashier_name = "-"
    if order.user_id:
        from backend.models.user import User as UserModel
        cashier = await db.get(UserModel, order.user_id)
        if cashier:
            cashier_name = cashier.full_name

    payment_method = "cash"
    payment_result = await db.execute(
        select(Payment)
        .where(Payment.order_id == order.id, Payment.deleted_at.is_(None))
        .order_by(Payment.created_at.desc())
        .limit(1)
    )
    latest_payment = payment_result.scalar_one_or_none()
    if latest_payment:
        payment_method = latest_payment.payment_method

    phone = _normalize_phone(body.phone)
    if len(phone) < 9:
        raise HTTPException(status_code=400, detail="Nomor HP tidak valid")

    receipt_text = _build_receipt_text(order, outlet_name, cashier_name, payment_method)
    sent = await send_whatsapp_message(phone, receipt_text)

    return StandardResponse(
        success=sent,
        data={"phone": phone, "sent": sent},
        request_id=request.state.request_id,
        message="Struk berhasil dikirim via WhatsApp" if sent else "Gagal mengirim struk"
    )
