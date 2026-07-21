import asyncio
import logging
from typing import Any, List, Optional, Dict
from uuid import UUID
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, func
from sqlalchemy.orm import selectinload
from pydantic import BaseModel

from backend.core.database import get_db
from backend.utils.phone import mask_phone
from backend.api.deps import get_current_user
from backend.models.user import User
from backend.models.payment import Payment
from backend.models.order import Order, OrderItem
from backend.models.outlet import Outlet
from backend.models.shift import Shift, ShiftStatus
from backend.models.tab import Tab, TabSplit
from backend.models.table import Table
from backend.schemas.payment import PaymentCreate, PaymentResponse, PaymentStatus, PaymentMethod, RefundRequest, RefundApproval, RefundResponse
from backend.schemas.order import OrderStatus
from backend.schemas.response import StandardResponse
from backend.services.audit import log_audit
from backend.services.xendit import xendit_service
from backend.utils.encryption import decrypt_field
from backend.services.fonnte import send_whatsapp_message
from backend.models.event import Event

router = APIRouter()


async def _handle_tab_payment_webhook_paid(db: AsyncSession, payment: Payment) -> None:
    """Settle tab-side state when QRIS webhook arrives with status=paid.
    Mirrors cash path in tabs.py pay_full/pay_split/pay_items.

    Branches on which kind of tab payment this is:
      - Has TabSplit with payment_id=this.id → split or full path
        (pay-tab-full creates a single 'full' split too)
      - No TabSplit but has items with paid_payment_id=this.id → pay-items path

    Locks Tab via SELECT FOR UPDATE to serialize concurrent split webhooks.
    """
    from backend.models.event import Event as _Event

    paid_at = datetime.now(timezone.utc)

    # Lock tab row
    tab_q = (
        select(Tab)
        .options(
            selectinload(Tab.splits),
            selectinload(Tab.orders).selectinload(Order.items),
            selectinload(Tab.table),
        )
        .where(Tab.id == payment.tab_id)
        .with_for_update()
    )
    tab_res = await db.execute(tab_q)
    tab = tab_res.scalar_one_or_none()
    if not tab:
        logger.warning("tab_id %s not found for payment %s", payment.tab_id, payment.id)
        return

    tab_status = tab.status.value if hasattr(tab.status, 'value') else str(tab.status)
    if tab_status in ('paid', 'cancelled'):
        # Already settled by an earlier webhook OR cashier cancelled — idempotent skip.
        return

    # Find related TabSplit
    related_split = None
    for s in tab.splits:
        if s.payment_id == payment.id:
            related_split = s
            break

    if related_split is not None:
        # Split or pay-tab-full path
        related_split.status = 'paid'
        related_split.paid_at = paid_at
        related_split.row_version = (related_split.row_version or 0) + 1

        split_amount = float(related_split.amount or 0)
        tab.paid_amount = float(tab.paid_amount or 0) + split_amount

        # For pay-tab-full: settle remaining items (paid_at=now where paid_payment_id=this)
        # For pay-split: items not directly tied to split — only settle items where paid_payment_id=this.id
        for o in tab.orders:
            ostatus = o.status.value if hasattr(o.status, 'value') else str(o.status)
            if ostatus == 'cancelled' or o.deleted_at is not None:
                continue
            for item in (o.items or []):
                if item.deleted_at is None and item.paid_at is None and item.paid_payment_id == payment.id:
                    item.paid_at = paid_at
                    item.row_version = (item.row_version or 0) + 1

        # Check if all splits paid → close tab
        all_splits_paid = all(
            (s.status.value if hasattr(s.status, 'value') else str(s.status)) == 'paid'
            for s in tab.splits
        )
        if all_splits_paid:
            tab.status = 'paid'
            tab.closed_at = paid_at
            for o in tab.orders:
                ostatus = o.status.value if hasattr(o.status, 'value') else str(o.status)
                if ostatus not in ('completed', 'cancelled'):
                    o.status = 'completed'
                    o.row_version = (o.row_version or 0) + 1
            if tab.table_id:
                tbl = await db.get(Table, tab.table_id)
                if tbl and (tbl.status.value if hasattr(tbl.status, 'value') else str(tbl.status)) == 'occupied':
                    tbl.status = 'available'
                    tbl.row_version = (tbl.row_version or 0) + 1
    else:
        # pay-items path — settle items claimed by this payment
        affected_orders = []
        for o in tab.orders:
            ostatus = o.status.value if hasattr(o.status, 'value') else str(o.status)
            if ostatus == 'cancelled' or o.deleted_at is not None:
                continue
            order_touched = False
            for item in (o.items or []):
                if item.deleted_at is None and item.paid_at is None and item.paid_payment_id == payment.id:
                    item.paid_at = paid_at
                    item.row_version = (item.row_version or 0) + 1
                    order_touched = True
            if order_touched:
                affected_orders.append(o)

        # Auto-complete any orders where all items now paid
        for o in affected_orders:
            all_items_paid = all(
                (it.deleted_at is not None) or (it.paid_at is not None)
                for it in (o.items or [])
            )
            if all_items_paid:
                ostatus = o.status.value if hasattr(o.status, 'value') else str(o.status)
                if ostatus not in ('completed', 'cancelled'):
                    o.status = 'completed'
                    o.row_version = (o.row_version or 0) + 1

        # Close tab if remaining ≤ 0
        # Compute remaining inline (mirror tab_service.tab_remaining_after_items)
        from decimal import Decimal as _D
        total = _D(str(tab.total_amount or 0))
        paid_via_tab = _D(str(tab.paid_amount or 0))
        paid_via_items = _D('0')
        for o in tab.orders:
            ostatus = o.status.value if hasattr(o.status, 'value') else str(o.status)
            if ostatus == 'cancelled' or o.deleted_at is not None:
                continue
            for item in (o.items or []):
                if item.deleted_at is None and item.paid_at is not None:
                    paid_via_items += _D(str(item.total_price or 0))
        remaining = max(_D('0'), total - paid_via_tab - paid_via_items)
        if remaining <= _D('0.01'):
            tab.status = 'paid'
            tab.closed_at = paid_at
            for o in tab.orders:
                ostatus = o.status.value if hasattr(o.status, 'value') else str(o.status)
                if ostatus not in ('completed', 'cancelled'):
                    o.status = 'completed'
                    o.row_version = (o.row_version or 0) + 1
            if tab.table_id:
                tbl = await db.get(Table, tab.table_id)
                if tbl and (tbl.status.value if hasattr(tbl.status, 'value') else str(tbl.status)) == 'occupied':
                    tbl.status = 'available'
                    tbl.row_version = (tbl.row_version or 0) + 1

    tab.row_version = (tab.row_version or 0) + 1

    # WA receipt — fail-silent (Rule #54). Mirror tabs._send_tab_wa_receipts but
    # inline because webhook context can't easily call tab route helper.
    sent_to_customers = set()
    for order in (tab.orders or []):
        if not order.customer_id or order.customer_id in sent_to_customers:
            continue
        sent_to_customers.add(order.customer_id)
        try:
            from backend.models.customer import Customer as _Customer
            from backend.models.user import User as _UserModel
            customer = await db.get(_Customer, order.customer_id)
            if not customer or not customer.phone:
                continue
            outlet = await db.get(Outlet, payment.outlet_id)
            outlet_name = outlet.name if outlet else "Kasira"
            cashier_name = "-"
            if order.user_id:
                cashier = await db.get(_UserModel, order.user_id)
                if cashier:
                    cashier_name = cashier.full_name
            struk = _build_receipt_text(
                order, outlet_name, cashier_name, payment.payment_method, payment,
                outlet_slug=getattr(outlet, 'slug', None),
            )
            asyncio.create_task(send_whatsapp_message(customer.phone, struk))
        except Exception as e:
            logger.warning("tab webhook WA receipt fail-silent: %s", e)

    # Loyalty (Pro+) — mirror jalur cash di tabs.py. Self-guard: cuma jalan
    # kalau blok di atas beneran nutup tab ke 'paid'.
    try:
        from backend.services.loyalty_service import earn_points_for_tab

        outlet_for_loyalty = await db.get(Outlet, payment.outlet_id)
        if outlet_for_loyalty:
            await earn_points_for_tab(
                db, tab, payment.outlet_id, outlet_for_loyalty.tenant_id,
                source="tab_webhook",
            )
    except Exception:
        logger.warning("tab webhook loyalty fail-silent tab=%s", payment.tab_id, exc_info=True)


async def _handle_tab_payment_webhook_failed(db: AsyncSession, payment: Payment) -> None:
    """Release locks taken at QRIS init time when webhook arrives with status
    failed/expired/cancelled. So kasir can retry pay-split/pay-items.

      - TabSplit with payment_id=this → split.status='unpaid', payment_id=NULL
      - Items with paid_payment_id=this AND paid_at IS NULL → clear paid_payment_id
    """
    # Lock tab row
    tab_q = (
        select(Tab)
        .options(
            selectinload(Tab.splits),
            selectinload(Tab.orders).selectinload(Order.items),
        )
        .where(Tab.id == payment.tab_id)
        .with_for_update()
    )
    tab_res = await db.execute(tab_q)
    tab = tab_res.scalar_one_or_none()
    if not tab:
        return

    tab_status = tab.status.value if hasattr(tab.status, 'value') else str(tab.status)
    if tab_status in ('paid', 'cancelled'):
        # Tab already closed via another path — nothing to release.
        return

    for s in tab.splits:
        if s.payment_id == payment.id:
            s_status = s.status.value if hasattr(s.status, 'value') else str(s.status)
            if s_status != 'paid':  # Don't undo a paid split (paranoia)
                s.status = 'unpaid'
                s.payment_id = None
                s.row_version = (s.row_version or 0) + 1

    for o in (tab.orders or []):
        for item in (o.items or []):
            if item.paid_payment_id == payment.id and item.paid_at is None:
                item.paid_payment_id = None
                item.row_version = (item.row_version or 0) + 1

    tab.row_version = (tab.row_version or 0) + 1


# Field yg WAJIB di-strip sebelum simpan Xendit response ke DB / log.
# Defense-in-depth (Risk Hunt H1): Xendit response biasanya gak echo back API key,
# TAPI 401/403 error response kadang echo Authorization header parts. Mencegah
# leak via payment.xendit_raw column (persisted) + structured logging.
_XENDIT_SENSITIVE_KEYS = frozenset({
    "headers", "request", "request_headers",
    "authorization", "Authorization",
    "api_key", "apiKey", "secret_key", "secretKey",
    "private_key", "privateKey",
})


def _sanitize_xendit_response(payload: Any) -> Dict[str, Any]:
    """Strip sensitive fields recursively dari Xendit API response sebelum
    persist ke DB. Hanya kembalikan structure dict-like — non-dict pass-through.
    """
    if not isinstance(payload, dict):
        return payload
    return {
        k: _sanitize_xendit_response(v) if isinstance(v, dict) else v
        for k, v in payload.items()
        if k not in _XENDIT_SENSITIVE_KEYS
    }


async def _try_earn_loyalty_points(
    db: AsyncSession,
    order: Order,
    outlet_id: UUID,
    user_id: UUID,
    tenant_id: UUID,
    *,
    source: str = "pos",
) -> int:
    """Auto-earn loyalty setelah order lunas. Pro+ only, gak pernah ngeblok payment.

    Isinya pindah ke `backend/services/loyalty_service.py` supaya tabs.py dan
    sync.py bisa pake logika yang sama persis. Signature lama dipertahankan
    (termasuk `user_id` yang memang gak kepake) biar call site existing gak
    ikut berubah.
    """
    from backend.services.loyalty_service import earn_points_for_order

    return await earn_points_for_order(
        db, order, outlet_id, tenant_id, source=source,
    )


async def _try_earn_loyalty_points_for_receipt(
    db: AsyncSession, order: Order, outlet: Optional[Outlet], source: str = "send_receipt",
) -> int:
    """Earn dari jalur kirim struk — order biasa maupun order di dalam tab.

    Bedanya sama `_try_earn_loyalty_points`: order yang nempel di tab gak punya
    Payment per-order (bayarnya lewat split / pay-items di level tab), jadi
    predikat "sudah lunas" per-order selalu False. Untuk order tab, kelunasan
    dibaca dari `tab.status == 'paid'`.
    """
    from backend.services.loyalty_service import earn_points_for_order

    if not outlet or not order or not order.customer_id:
        return 0

    tab_id = getattr(order, "tab_id", None)
    if tab_id:
        tab = await db.get(Tab, tab_id)
        if not tab:
            return 0
        tab_status = tab.status.value if hasattr(tab.status, 'value') else str(tab.status)
        if tab_status != 'paid':
            return 0  # tab belum lunas — poin nyusul pas tab close
        return await earn_points_for_order(
            db, order, outlet.id, outlet.tenant_id,
            source=f"{source}_tab", require_fully_paid=False,
        )

    return await earn_points_for_order(
        db, order, outlet.id, outlet.tenant_id, source=source,
    )


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

    # Verify order exists if provided — SELECT FOR UPDATE to prevent double payment
    if payment_in.order_id:
        order_result = await db.execute(
            select(Order).options(
                selectinload(Order.items).selectinload(OrderItem.product)
            ).where(Order.id == payment_in.order_id).with_for_update()
        )
        order = order_result.scalar_one_or_none()
        if not order or order.deleted_at is not None:
            raise HTTPException(status_code=404, detail="Order tidak ditemukan")
        if order.status == OrderStatus.completed:
            raise HTTPException(status_code=400, detail="Order sudah selesai (sudah dibayar)")
        if order.status == OrderStatus.cancelled:
            raise HTTPException(
                status_code=400,
                detail="Order sudah dibatalkan otomatis oleh sistem (stale cleanup) — silakan buat order baru."
            )

    # Block partial payments for non-Pro tiers (Rule #43)
    if payment_in.is_partial:
        from backend.models.tenant import Tenant
        tenant = (await db.execute(
            select(Tenant).where(Tenant.id == current_user.tenant_id)
        )).scalar_one_or_none()
        raw_tier = getattr(tenant, "subscription_tier", "starter") or "starter" if tenant else "starter"
        tier = raw_tier.value if hasattr(raw_tier, 'value') else str(raw_tier)
        if tier.lower() not in {"pro", "business", "enterprise"}:
            raise HTTPException(status_code=403, detail="Partial payment hanya tersedia untuk paket Pro.")

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
    
    # Generate QRIS via Xendit if method is qris.
    # Fail-safe (CRITICAL #12): distinguishing configuration error vs transient
    # Xendit API failure. Retry exhausted = pending_manual_check (admin verify),
    # bukan failed terminal.
    if payment_in.payment_method == PaymentMethod.qris:
        outlet = await db.get(Outlet, payment_in.outlet_id)
        # BYOK pattern (mirror connect.py:528) — POS path harus konsisten dgn
        # storefront: prefer outlet's own API key, fallback ke sub-account
        # business_id (xenPlatform Phase 2). Outlet kosong both = config error.
        if not outlet or not (outlet.xendit_api_key or outlet.xendit_business_id):
            payment.status = PaymentStatus.failed
            payment.xendit_raw = {"error": "Outlet belum terhubung Xendit (API Key atau Sub-Account ID)"}
        else:
            from backend.services.xendit import XenditTransientError, XenditPermanentError
            try:
                xendit_res = await xendit_service.create_qris_transaction(
                    reference_id=f"{current_user.tenant_id}::{payment.id}",
                    amount=float(payment.amount_due),
                    # BYOK wins kalau ada — for_user_id dipake hanya kalau
                    # outlet pakai sub-account model (no own key).
                    for_user_id=outlet.xendit_business_id if not outlet.xendit_api_key else None,
                    platform_fee_percent=0.2,
                    merchant_api_key=outlet.xendit_api_key,
                )
                payment.qris_url = xendit_res.get("qr_string") or xendit_res.get("qr_url")
                payment.xendit_raw = _sanitize_xendit_response(xendit_res)
                expires_at = xendit_res.get("expires_at")
                if expires_at:
                    try:
                        payment.qris_expired_at = datetime.fromisoformat(expires_at.replace("Z", "+00:00"))
                    except (ValueError, AttributeError):
                        pass

            except XenditPermanentError as e:
                # 4xx — clear config error, langsung failed (gak akan recover)
                logger.error(
                    "xendit permanent error payment=%s: %s", payment.id, e,
                )
                payment.status = PaymentStatus.failed
                payment.xendit_raw = {"error": str(e), "error_type": "permanent"}

            except XenditTransientError as e:
                # Retry habis — uncertain state. Xendit MIGHT have accepted the
                # request. Admin perlu cek manual via dashboard Xendit.
                logger.error(
                    "xendit transient retry exhausted payment=%s: %s — "
                    "set ke pending_manual_check untuk admin review",
                    payment.id, e,
                )
                payment.status = PaymentStatus.pending_manual_check
                payment.xendit_raw = {
                    "error": str(e),
                    "error_type": "transient_exhausted",
                    "admin_action": "Verify manually via Xendit dashboard — "
                                    "transaction might have been created.",
                }

            except Exception as e:
                # Defensive — unexpected error. Set pending_manual_check (safer
                # than failed — preserve investigation path).
                logger.exception(
                    "xendit unexpected error payment=%s", payment.id,
                )
                payment.status = PaymentStatus.pending_manual_check
                payment.xendit_raw = {"error": str(e), "error_type": "unexpected"}
    
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

            # Release dine-in table when fully paid (mirror orders.py:519-533)
            if new_order_status == OrderStatus.completed and order.table_id:
                from backend.models.table import Table
                active_orders = (await db.execute(
                    select(func.count(Order.id)).where(
                        Order.table_id == order.table_id,
                        Order.id != order.id,
                        Order.status.notin_(["completed", "cancelled"]),
                        Order.deleted_at.is_(None),
                    )
                )).scalar() or 0
                if active_orders == 0:
                    await db.execute(
                        update(Table).where(Table.id == order.table_id)
                        .values(status="available", row_version=Table.row_version + 1)
                    )

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
                    struk = _build_receipt_text(order, outlet_name, cashier_name, payment_in.payment_method, payment, outlet_slug=getattr(outlet, 'slug', None))
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

    CRITICAL #12 fix: idempotent via xendit_webhook_events dedup table +
    hmac.compare_digest constant-time verification. Xendit kirim callback
    berulang (retry policy mereka) = kita process sekali.
    """
    xendit_callback_token = request.headers.get("x-callback-token")
    xendit_signature = request.headers.get("x-xendit-signature")
    xendit_timestamp = request.headers.get("x-xendit-timestamp")
    
    try:
        body_bytes = await request.body()
        payload = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    is_valid = False
    if xendit_signature and xendit_timestamp:
        is_valid = xendit_service.verify_webhook_signature(body_bytes, xendit_signature, xendit_timestamp)
    
    if not is_valid and xendit_callback_token:
        is_valid = xendit_service.verify_webhook(xendit_callback_token)
        
    if not is_valid:
        raise HTTPException(status_code=400, detail="Invalid Verification Token")


    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="Payload must be a JSON object")

    data = payload.get("data", payload)
    if not isinstance(data, dict):
        raise HTTPException(status_code=400, detail="Invalid data field in payload")

    # ─── Idempotency claim (CRITICAL #12 webhook dedup) ───────────────────────
    # Atomic INSERT ON CONFLICT. Kalau RETURNING kosong = callback sudah di-
    # process (Xendit retry duplicate) → return OK early, no re-process.
    # Callback ID priority: payload["id"] > data["id"] > SHA256(payload).
    import hashlib, json as _json
    callback_id = (
        payload.get("id")
        or data.get("id")
        or hashlib.sha256(_json.dumps(payload, sort_keys=True).encode()).hexdigest()[:64]
    )
    event_type = payload.get("event") or data.get("event_type") or "unknown"
    payload_str = _json.dumps(payload, sort_keys=True)
    payload_hash = hashlib.sha256(payload_str.encode()).hexdigest()

    from sqlalchemy import text as _sql_text
    claim = await db.execute(
        _sql_text(
            "INSERT INTO xendit_webhook_events "
            "(id, callback_id, external_id, event_type, payload_hash, processed_at) "
            "VALUES (gen_random_uuid(), :cid, :eid, :ev, :hash, now()) "
            "ON CONFLICT (callback_id) DO NOTHING RETURNING id"
        ),
        {
            "cid": str(callback_id)[:128],
            "eid": str(data.get("external_id") or data.get("reference_id") or "")[:255],
            "ev": str(event_type)[:64],
            "hash": payload_hash,
        },
    )
    claimed = claim.first() is not None
    if not claimed:
        logger.info(
            "xendit webhook dedup hit: callback_id=%s event=%s — already processed",
            callback_id, event_type,
        )
        await db.commit()  # commit the no-op attempt
        return {"status": "ok", "dedup": True}
    await db.commit()  # commit the dedup row; downstream process uses fresh TX

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

            # Tab payment branch — handles split/full/items reconciliation +
            # close logic + WA receipts. Skip order-only branch below to avoid
            # mis-completing the first order (payment.order_id is just an anchor
            # for tab payments; tab branch completes ALL orders correctly).
            if payment.tab_id:
                await _handle_tab_payment_webhook_paid(db, payment)
            elif payment.order_id:
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

                    # Release dine-in table when fully paid via webhook (mirror orders.py:519-533)
                    if new_order_status == OrderStatus.completed and order.table_id:
                        from backend.models.table import Table
                        active_orders = (await db.execute(
                            select(func.count(Order.id)).where(
                                Order.table_id == order.table_id,
                                Order.id != order.id,
                                Order.status.notin_(["completed", "cancelled"]),
                                Order.deleted_at.is_(None),
                            )
                        )).scalar() or 0
                        if active_orders == 0:
                            await db.execute(
                                update(Table).where(Table.id == order.table_id)
                                .values(status="available", row_version=Table.row_version + 1)
                            )

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
                            struk = _build_receipt_text(order, outlet_name, cashier_name, payment.payment_method, payment, outlet_slug=getattr(outlet, 'slug', None))
                            asyncio.create_task(
                                send_whatsapp_message(customer.phone, struk)
                            )

                    # Auto-earn loyalty points (Pro+)
                    # Use payment.outlet_id; no current_user in webhook context
                    outlet_for_loyalty = await db.get(Outlet, payment.outlet_id)
                    if outlet_for_loyalty:
                        # WAJIB flush dulu. Session ini autoflush=False, dan
                        # loyalty ngecek kelunasan lewat SUM(payments.amount_paid)
                        # di DB. Tanpa flush, status='paid' + amount_paid milik
                        # payment INI masih nyangkut di memori → SUM-nya kurang →
                        # order dikira belum lunas → poin gak pernah masuk.
                        await db.flush()
                        await _try_earn_loyalty_points(
                            db, order, payment.outlet_id,
                            order.user_id or payment.outlet_id,  # fallback if no user
                            outlet_for_loyalty.tenant_id,
                            source="webhook",
                        )
        elif new_status == PaymentStatus.failed:
            # Tab QRIS init expired/failed via Xendit — release locks so kasir
            # can retry pay-split/pay-items. (Order-only payments don't need
            # release; cashier just creates a new Payment row.)
            if payment.tab_id:
                await _handle_tab_payment_webhook_failed(db, payment)

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

    status_val = payment.status.value if hasattr(payment.status, 'value') else str(payment.status)
    method_val = payment.payment_method.value if hasattr(payment.payment_method, 'value') else str(payment.payment_method)
    return StandardResponse(
        success=True,
        data={
            "id": str(payment.id),
            "status": status_val,
            "payment_method": method_val,
            "paid_at": payment.paid_at,
            "qris_url": payment.qris_url,
            "qris_expired_at": payment.qris_expired_at,
            "amount_due": payment.amount_due,
            "amount_paid": payment.amount_paid,
            "tab_id": str(payment.tab_id) if payment.tab_id else None,
            "order_id": str(payment.order_id) if payment.order_id else None,
            "receipt_printed_at": payment.receipt_printed_at,
        },
        request_id=request.state.request_id
    )


@router.post("/{payment_id}/claim-print", response_model=StandardResponse[Dict[str, Any]])
async def claim_print_receipt(
    request: Request,
    payment_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    """Atomic claim of "I'm about to print receipt". Returns claimed=true if
    receipt_printed_at was NULL and we just set it. Returns claimed=false if
    another caller already printed (received a webhook + raced to print first,
    or cashier double-tap, etc.).

    Use case: Flutter autoprint path calls this BEFORE building+sending bytes
    to printer. If claimed=false → skip (someone else handled it). Manual
    reprint button bypasses this — uses /receipt endpoints + always prints.

    Race-safe via single UPDATE WHERE receipt_printed_at IS NULL.
    """
    from sqlalchemy import update as _sql_update
    now = datetime.now(timezone.utc)
    res = await db.execute(
        _sql_update(Payment)
        .where(Payment.id == payment_id, Payment.receipt_printed_at.is_(None))
        .values(receipt_printed_at=now)
        .execution_options(synchronize_session=False)
    )
    await db.commit()
    claimed = res.rowcount > 0
    # Re-read after commit so caller sees authoritative timestamp.
    payment = await db.get(Payment, payment_id)
    if not payment or payment.deleted_at is not None:
        raise HTTPException(status_code=404, detail="Pembayaran tidak ditemukan")
    return StandardResponse(
        success=True,
        data={
            "claimed": claimed,
            "receipt_printed_at": payment.receipt_printed_at,
        },
        request_id=request.state.request_id,
    )

@router.get("/refunds", response_model=StandardResponse[list[RefundResponse]])
async def list_refunds(
    request: Request,
    outlet_id: UUID,
    status: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    """List refunds for an outlet."""
    from backend.models.payment_refund import PaymentRefund

    query = (
        select(PaymentRefund)
        .join(Payment, PaymentRefund.payment_id == Payment.id)
        .where(Payment.outlet_id == outlet_id, PaymentRefund.deleted_at.is_(None))
        .order_by(PaymentRefund.created_at.desc())
        .limit(50)
    )
    if status:
        query = query.where(PaymentRefund.status == status)

    result = await db.execute(query)
    refunds = result.scalars().all()

    return StandardResponse(
        success=True,
        data=[RefundResponse.model_validate(r) for r in refunds],
        request_id=request.state.request_id,
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
    payment_id: Optional[UUID] = None  # subset receipt: cuma items yg paid_payment_id match
    customer_name: Optional[str] = None  # auto-create customer dgn nama ini (default: "Customer 0812****")
    # Izin kirim promo, ditanya kasir ke customer. Default False dan HARUS
    # tetap False kalau nggak dikirim — izin nggak boleh disimpulkan dari
    # "dia mau dikirimi struk". Struk itu bukti transaksi, promo itu iklan.
    marketing_consent: bool = False


def _normalize_phone(phone: str) -> str:
    """Normalize phone to international format (62xxx) for Fonnte."""
    p = phone.strip().replace(" ", "").replace("-", "")
    if p.startswith("0"):
        return "62" + p[1:]
    if p.startswith("+"):
        return p[1:]
    return p


def _build_receipt_text(
    order: Order,
    outlet_name: str,
    cashier_name: str,
    payment_method: str,
    payment_obj=None,
    outlet_slug: str = None,
    items_override: Optional[List] = None,
    totals_override: Optional[Dict[str, float]] = None,
) -> str:
    """Build WA receipt text.

    items_override: kalau dikasih, render items ini (bukan order.items penuh) — buat
    subset receipt warkop pay-items.
    totals_override: dict {subtotal, tax, service, discount, total} — wajib kalau pakai
    items_override (untuk recompute totals proportional). Kalau None, pakai order totals.
    """
    method_label = {"cash": "Tunai", "qris": "QRIS", "card": "Kartu", "transfer": "Transfer"}.get(payment_method, payment_method.upper())
    # WIB timezone
    from datetime import timezone as tz, timedelta
    wib = tz(timedelta(hours=7))
    order_time = order.created_at.astimezone(wib).strftime('%d/%m/%Y %H:%M') if order.created_at else '-'

    is_subset = items_override is not None
    items_to_render = items_override if is_subset else order.items

    lines = [
        f"*Struk Pembayaran*" + (" (Sebagian)" if is_subset else ""),
        f"📍 {outlet_name}",
        f"No. Order: #{order.display_number}",
        f"Tanggal: {order_time} WIB",
        f"Kasir: {cashier_name}",
        f"{'─' * 28}",
    ]
    for item in items_to_render:
        name = item.product_name or 'Item'
        qty = item.quantity
        price = float(item.unit_price)
        item_disc = float(item.discount_amount or 0)
        subtotal = float(item.total_price)
        lines.append(f"{name}")
        if item_disc > 0:
            lines.append(f"  {qty}x Rp{price:,.0f} - disc Rp{item_disc:,.0f}")
            lines.append(f"  = Rp{subtotal:,.0f}")
        else:
            lines.append(f"  {qty}x Rp{price:,.0f}  =  Rp{subtotal:,.0f}")
    lines.append(f"{'─' * 28}")

    if totals_override:
        subtotal_val = float(totals_override.get('subtotal', 0))
        discount_val = float(totals_override.get('discount', 0))
        service_val = float(totals_override.get('service', 0))
        tax_val = float(totals_override.get('tax', 0))
        total_val = float(totals_override.get('total', 0))
    else:
        subtotal_val = float(order.subtotal or 0)
        discount_val = float(order.discount_amount or 0)
        service_val = float(order.service_charge_amount or 0)
        tax_val = float(order.tax_amount or 0)
        total_val = float(order.total_amount or 0)

    lines.append(f"Subtotal    : Rp{subtotal_val:,.0f}")
    if discount_val > 0:
        lines.append(f"Diskon      : -Rp{discount_val:,.0f}")
    if service_val > 0:
        lines.append(f"Service     : Rp{service_val:,.0f}")
    if tax_val > 0:
        lines.append(f"Pajak       : Rp{tax_val:,.0f}")
    lines.append(f"{'─' * 28}")
    lines.append(f"*TOTAL       : Rp{total_val:,.0f}*")
    lines.append(f"Bayar ({method_label}) : Rp{total_val:,.0f}")

    # Show amount paid + change for cash
    if payment_obj:
        paid = float(payment_obj.amount_paid or 0)
        change = float(payment_obj.change_amount or 0)
        if paid > 0 and paid != total_val:
            lines.append(f"Dibayar     : Rp{paid:,.0f}")
        if change > 0:
            lines.append(f"Kembalian   : Rp{change:,.0f}")

    lines.append(f"{'─' * 28}")
    lines.append(f"Terima kasih! 🙏")
    if outlet_slug:
        lines.append(f"")
        lines.append(f"📱 Pesan lagi via online:")
        lines.append(f"https://kasira.online/{outlet_slug}")
    lines.append(f"_Powered by Kasira_")
    return "\n".join(lines)


@router.post("/send-receipt", response_model=StandardResponse[Dict[str, Any]])
async def send_receipt_whatsapp(
    request: Request,
    body: SendReceiptRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    """Send receipt via WhatsApp + upsert customer untuk AI/KG/event store.

    Behavior:
    - Normalize phone, validate min length
    - Upsert customer by (tenant_id, phone) — reuse existing or create new
    - Auto-link order.customer_id kalau masih NULL (customer data capture)
    - Optional payment_id → subset receipt (cuma items terkait payment, untuk pay-items)
    - Send WA via Fonnte
    - Emit event "receipt.wa_sent" untuk event store + AI context

    Reused untuk POS reguler + tab payment (split/full/items).
    """
    from backend.models.customer import Customer
    from sqlalchemy import or_

    # Load order + items + product
    result = await db.execute(
        select(Order)
        .options(selectinload(Order.items).selectinload(OrderItem.product))
        .where(Order.id == body.order_id, Order.deleted_at.is_(None))
    )
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="Order tidak ditemukan")

    outlet = await db.get(Outlet, order.outlet_id)
    if not outlet or outlet.tenant_id != current_user.tenant_id:
        raise HTTPException(status_code=403, detail="Order bukan milik tenant Anda")
    outlet_name = outlet.name if outlet else "Kasira"

    # Phone validation + normalization
    phone = _normalize_phone(body.phone)
    if len(phone) < 9:
        raise HTTPException(status_code=400, detail="Nomor HP tidak valid")

    # Determine target payment + items subset (mirror /orders/{id}/receipt logic)
    items_override = None
    totals_override = None
    payment_for_receipt = None

    if body.payment_id:
        payment_for_receipt = await db.get(Payment, body.payment_id)
        if not payment_for_receipt or payment_for_receipt.outlet_id != outlet.id:
            raise HTTPException(status_code=404, detail="Payment tidak ditemukan")
        filtered = [i for i in order.items if i.paid_payment_id == body.payment_id]
        if not filtered:
            raise HTTPException(
                status_code=404,
                detail="Tidak ada item terkait payment ini di order"
            )
        items_override = filtered
        # Recompute subset totals proportional (mirror orders.py:get_order_receipt)
        from decimal import Decimal as D
        subset_subtotal = sum((D(str(it.total_price or 0)) for it in filtered), D('0'))
        order_subtotal = D(str(order.subtotal or 0)) or D('1')
        if order_subtotal > 0:
            tax_share = (D(str(order.tax_amount or 0)) * subset_subtotal / order_subtotal).quantize(D('0.01'))
            service_share = (D(str(order.service_charge_amount or 0)) * subset_subtotal / order_subtotal).quantize(D('0.01'))
        else:
            tax_share = D('0')
            service_share = D('0')
        total_val = float(payment_for_receipt.amount_due) if payment_for_receipt else float(subset_subtotal + tax_share + service_share)
        totals_override = {
            'subtotal': float(subset_subtotal),
            'tax': float(tax_share),
            'service': float(service_share),
            'discount': 0.0,
            'total': total_val,
        }
    else:
        # Latest payment untuk method/amount/change
        payment_for_receipt = (await db.execute(
            select(Payment)
            .where(Payment.order_id == order.id, Payment.deleted_at.is_(None))
            .order_by(Payment.created_at.desc())
            .limit(1)
        )).scalar_one_or_none()

    payment_method = "cash"
    if payment_for_receipt:
        pm = payment_for_receipt.payment_method
        payment_method = pm.value if hasattr(pm, 'value') else str(pm)

    # Cashier name
    cashier_name = "-"
    if order.user_id:
        from backend.models.user import User as UserModel
        cashier = await db.get(UserModel, order.user_id)
        if cashier:
            cashier_name = cashier.full_name

    # ── Customer upsert (capture data for AI / KG / event store) ──
    import hashlib, hmac as _hmac
    phone_hmac = _hmac.new(b'kasira-phone-key', phone.encode(), hashlib.sha256).hexdigest()

    # Lookup existing customer by tenant + phone (or phone_hmac as fallback)
    existing_q = await db.execute(
        select(Customer).where(
            Customer.tenant_id == outlet.tenant_id,
            or_(Customer.phone == phone, Customer.phone_hmac == phone_hmac),
            Customer.deleted_at.is_(None),
        )
    )
    customer = existing_q.scalar_one_or_none()

    customer_created = False
    if not customer:
        # Auto-name fallback "Customer 0812****" kalau body.customer_name empty
        auto_name = body.customer_name.strip() if body.customer_name else None
        if not auto_name:
            auto_name = f"Customer {mask_phone(phone)}"
        customer = Customer(
            tenant_id=outlet.tenant_id,
            name=auto_name,
            phone=phone,
            phone_hmac=phone_hmac,
        )
        db.add(customer)
        await db.flush()
        customer_created = True
    elif body.customer_name and body.customer_name.strip() and not customer.name.startswith("Customer "):
        # Existing customer punya nama proper — jangan overwrite. Kalau nama auto-generated
        # ("Customer 0812****"), boleh upgrade dengan nama dari user.
        pass
    elif body.customer_name and body.customer_name.strip():
        customer.name = body.customer_name.strip()

    # Catat izin promo kalau kasir mencentangnya. Sekali diberikan jangan
    # dicabut diam-diam oleh transaksi berikutnya yang nggak dicentang —
    # pencabutan harus tindakan sadar, bukan efek samping.
    if body.marketing_consent and not customer.wa_marketing_consent:
        from datetime import datetime as _dt, timezone as _tz
        customer.wa_marketing_consent = True
        customer.consent_given_at = _dt.now(_tz.utc)
        customer.consent_source = 'kasir_input'

    # Auto-link order.customer_id kalau masih NULL (capture data point untuk AI)
    if order.customer_id is None:
        order.customer_id = customer.id

    # Auto-earn loyalty (Pro+). INI jalur mayoritas: kasir nangkep nomor
    # pelanggan di halaman struk, SESUDAH bayar. Waktu create_payment jalan
    # tadi order.customer_id masih NULL, jadi earn di sana ke-skip. Kalau gak
    # dipanggil ulang di sini, poinnya hilang permanen — itu bug aslinya.
    # Idempoten via UNIQUE(order_id,'earn'), jadi kirim struk berkali-kali
    # (atau reprint) gak bikin poin dobel.
    await _try_earn_loyalty_points_for_receipt(db, order, outlet, source="send_receipt")

    # Build receipt text
    receipt_text = _build_receipt_text(
        order, outlet_name, cashier_name, payment_method, payment_for_receipt,
        outlet_slug=getattr(outlet, 'slug', None),
        items_override=items_override,
        totals_override=totals_override,
    )

    # Send WA — fail-aware (tetap return status, gak raise)
    sent = await send_whatsapp_message(phone, receipt_text)

    # Emit event store entry (for AI context + KG ingestion downstream)
    try:
        db.add(Event(
            outlet_id=outlet.id,
            stream_id=f"order:{order.id}",
            event_type="receipt.wa_sent",
            event_data={
                "order_id": str(order.id),
                "payment_id": str(body.payment_id) if body.payment_id else None,
                "customer_id": str(customer.id),
                "customer_created": customer_created,
                "phone_masked": mask_phone(phone),
                "is_subset": items_override is not None,
                "sent": sent,
            },
            event_metadata={
                "actor": f"user:{current_user.id}",
                "ts": datetime.now(timezone.utc).isoformat(),
            },
        ))
    except Exception:
        pass  # event log gagal jangan block payment flow

    await db.commit()

    return StandardResponse(
        success=sent,
        data={
            "phone": mask_phone(phone),
            "sent": sent,
            "customer_id": str(customer.id),
            "customer_name": customer.name,
            "customer_created": customer_created,
        },
        request_id=request.state.request_id,
        message="Struk berhasil dikirim via WhatsApp" if sent else "Gagal mengirim struk (WhatsApp tidak terhubung)"
    )


# ── REFUND ENDPOINTS ─────────────────────────────────────────────────────────


async def _settle_refund(db: AsyncSession, refund, actor_user_id, now):
    """Selesaikan refund: stamp completed, tandai payment, balikin stok, revert item ad-hoc.

    Dipakai DUA jalur yang sebelumnya divergen:
      - request_refund() auto-approve (owner/superuser)
      - approve_refund() (jalur request kasir → approve owner)

    Sebelumnya jalur auto-approve cuma nge-stamp status='approved' lalu berhenti,
    dan approve_refund menolak apa pun yang != 'pending' — jadi refund auto-approve
    NGGAK PERNAH bisa selesai: uang keluar laci, payment tetap 'paid' di laporan,
    stok gak balik, dan guard dedup bikin nyangkut permanen.

    Stok HANYA dibalikin untuk refund PENUH. Refund parsial = itikad baik/potongan
    (barang tetap di tangan customer), jadi balikin 100% stok itu salah.
    Return: (payment, is_full_refund).
    """
    from backend.models.tab import Tab as _Tab
    from backend.services.stock_service import restore_stock_on_cancel
    from backend.services.ingredient_stock_service import restore_ingredients_on_cancel
    from backend.models.tenant import Tenant
    from decimal import Decimal as D

    refund.status = 'completed'
    refund.approved_by = actor_user_id
    refund.approved_at = now
    refund.completed_at = now
    refund.row_version = (refund.row_version or 0) + 1

    payment = (await db.execute(
        select(Payment).where(Payment.id == refund.payment_id).with_for_update()
    )).scalar_one_or_none()
    if not payment:
        return None, False

    refund_amt = D(str(refund.amount))
    is_full = refund_amt >= D(str(payment.amount_paid))

    payment.refunded_at = now
    payment.refund_amount = refund_amt
    payment.row_version += 1
    if is_full:
        payment.status = 'refunded'

    # Balikin stok — HANYA refund penuh.
    if is_full and payment.order_id:
        order = (await db.execute(
            select(Order)
            .where(Order.id == payment.order_id)
            .options(selectinload(Order.items).selectinload(OrderItem.product))
        )).scalar_one_or_none()
        if order and order.status == 'completed':
            outlet = await db.get(Outlet, order.outlet_id)
            tier = "starter"
            stock_mode = "simple"
            if outlet:
                sm = getattr(outlet, 'stock_mode', 'simple')
                stock_mode = sm.value if hasattr(sm, 'value') else str(sm or 'simple')
                if outlet.tenant_id:
                    tenant = await db.get(Tenant, outlet.tenant_id)
                    if tenant:
                        tier_val = getattr(tenant, 'subscription_tier', None) or "starter"
                        tier = tier_val.value if hasattr(tier_val, 'value') else str(tier_val)
            for item in order.items:
                product = item.product
                if product and product.stock_enabled:
                    if stock_mode == 'recipe':
                        await restore_ingredients_on_cancel(
                            db, product_id=product.id, quantity=item.quantity,
                            outlet_id=order.outlet_id, order_id=order.id, tier=tier,
                        )
                    else:
                        await restore_stock_on_cancel(
                            db, product=product, quantity=item.quantity,
                            outlet_id=order.outlet_id, order_id=order.id, tier=tier,
                        )

    # Revert per-item ad-hoc payment marks (Migration 085)
    # Items balik ke "unpaid pool" → kasir bisa rebill ke customer lain.
    # PENTING: pay-items SENGAJA gak nambah tab.paid_amount (source of truth = items.paid_at),
    # jadi refund pay-items HANYA revert items, JANGAN decrement tab.paid_amount.
    reverted_items = (await db.execute(
        select(OrderItem).where(OrderItem.paid_payment_id == payment.id)
    )).scalars().all()
    if reverted_items:
        for it in reverted_items:
            it.paid_at = None
            it.paid_payment_id = None
            it.row_version = (it.row_version or 0) + 1

        # Re-open tab kalau sudah closed (split via items refunded mid-close)
        if payment.tab_id:
            tab = await db.get(_Tab, payment.tab_id)
            if tab and tab.status == 'paid':
                tab.status = 'open'
                tab.closed_at = None
                tab.closed_by = None
                tab.row_version = (tab.row_version or 0) + 1

    return payment, is_full


@router.post("/refunds", response_model=StandardResponse[RefundResponse])
async def request_refund(
    request: Request,
    body: RefundRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    """Request a refund. Requires can_refund permission."""
    from backend.models.payment_refund import PaymentRefund
    from backend.models.role import Role
    from decimal import Decimal as D

    # Check permission
    if current_user.role_id:
        role = await db.get(Role, current_user.role_id)
        if role and not role.can_refund and not current_user.is_superuser:
            raise HTTPException(status_code=403, detail="Anda tidak punya izin untuk refund")
    elif not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Anda tidak punya izin untuk refund")

    # Validate payment exists and is paid
    payment = await db.execute(
        select(Payment).where(Payment.id == body.payment_id, Payment.deleted_at.is_(None)).with_for_update()
    )
    payment = payment.scalar_one_or_none()
    if not payment:
        raise HTTPException(status_code=404, detail="Payment tidak ditemukan")
    if payment.status != 'paid':
        raise HTTPException(status_code=400, detail=f"Payment status '{payment.status}', hanya payment 'paid' yang bisa di-refund")

    # Validate amount
    refund_amount = D(str(body.amount))
    if refund_amount > D(str(payment.amount_paid)):
        raise HTTPException(status_code=400, detail="Jumlah refund melebihi jumlah pembayaran")

    # Check no existing pending refund for this payment
    existing = await db.execute(
        select(PaymentRefund).where(
            PaymentRefund.payment_id == body.payment_id,
            PaymentRefund.status.in_(['pending', 'approved']),
            PaymentRefund.deleted_at.is_(None),
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Sudah ada refund pending untuk payment ini")

    refund = PaymentRefund(
        payment_id=body.payment_id,
        amount=refund_amount,
        reason=body.reason,
        requested_by=current_user.id,
    )
    db.add(refund)
    await db.flush()

    # Owner/superuser: auto-approve DAN langsung selesaikan.
    # Dulu di sini cuma stamp status='approved' tanpa memproses apa pun, dan
    # approve_refund menolak status != 'pending' → refund nyangkut selamanya.
    auto_approved = bool(current_user.is_superuser)
    if auto_approved:
        await _settle_refund(db, refund, current_user.id, datetime.now(timezone.utc))

    db.add(Event(
        outlet_id=payment.outlet_id,
        stream_id=f"refund:{refund.id}",
        event_type="refund.requested",
        event_data={
            "refund_id": str(refund.id),
            "payment_id": str(payment.id),
            "amount": float(refund_amount),
            "reason": body.reason,
            "auto_approved": current_user.is_superuser,
        },
        event_metadata={"ts": datetime.now(timezone.utc).isoformat(), "user_id": str(current_user.id)},
    ))
    if auto_approved:
        # Event stream harus konsisten dgn jalur approve_refund.
        db.add(Event(
            outlet_id=payment.outlet_id,
            stream_id=f"refund:{refund.id}",
            event_type="refund.completed",
            event_data={
                "refund_id": str(refund.id),
                "payment_id": str(payment.id),
                "amount": float(refund_amount),
                "approved_by": str(current_user.id),
                "auto_approved": True,
            },
            event_metadata={"ts": datetime.now(timezone.utc).isoformat(), "user_id": str(current_user.id)},
        ))
    await log_audit(
        db=db, action="CREATE", entity="refund", entity_id=refund.id,
        after_state={"payment_id": str(body.payment_id), "amount": float(refund_amount), "reason": body.reason},
        user_id=current_user.id, tenant_id=current_user.tenant_id,
    )
    await db.commit()

    return StandardResponse(
        success=True,
        data=RefundResponse.model_validate(refund),
        request_id=request.state.request_id,
        message="Refund berhasil diajukan dan diproses" if auto_approved else "Refund berhasil diajukan",
    )


@router.post("/refunds/{refund_id}/approve", response_model=StandardResponse[RefundResponse])
async def approve_refund(
    request: Request,
    refund_id: UUID,
    body: RefundApproval,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    """Approve a pending refund and process it. Requires can_approve_refund or superuser."""
    from backend.models.payment_refund import PaymentRefund
    from backend.models.role import Role
    from decimal import Decimal as D

    # Check permission
    if current_user.role_id:
        role = await db.get(Role, current_user.role_id)
        if role and not role.can_approve_refund and not current_user.is_superuser:
            raise HTTPException(status_code=403, detail="Anda tidak punya izin untuk approve refund")
    elif not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Anda tidak punya izin untuk approve refund")

    refund = await db.execute(
        select(PaymentRefund).where(PaymentRefund.id == refund_id, PaymentRefund.deleted_at.is_(None)).with_for_update()
    )
    refund = refund.scalar_one_or_none()
    if not refund:
        raise HTTPException(status_code=404, detail="Refund tidak ditemukan")
    if refund.status != 'pending':
        raise HTTPException(status_code=400, detail=f"Refund status '{refund.status}', hanya 'pending' yang bisa di-approve")
    if refund.row_version != body.row_version:
        raise HTTPException(status_code=409, detail="Data berubah, refresh dulu")

    now = datetime.now(timezone.utc)
    # Logika penyelesaian dipakai bareng dgn jalur auto-approve di request_refund().
    payment, _is_full = await _settle_refund(db, refund, current_user.id, now)

    db.add(Event(
        outlet_id=payment.outlet_id if payment else None,
        stream_id=f"refund:{refund.id}",
        event_type="refund.completed",
        event_data={
            "refund_id": str(refund.id),
            "payment_id": str(refund.payment_id),
            "amount": float(refund.amount),
            "approved_by": str(current_user.id),
        },
        event_metadata={"ts": now.isoformat(), "user_id": str(current_user.id)},
    ))
    await log_audit(
        db=db, action="UPDATE", entity="refund", entity_id=refund.id,
        after_state={"action": "approve", "status": "completed"},
        user_id=current_user.id, tenant_id=current_user.tenant_id,
    )
    await db.commit()

    return StandardResponse(
        success=True,
        data=RefundResponse.model_validate(refund),
        request_id=request.state.request_id,
        message="Refund disetujui dan diproses",
    )


@router.post("/refunds/{refund_id}/reject", response_model=StandardResponse[RefundResponse])
async def reject_refund(
    request: Request,
    refund_id: UUID,
    body: RefundApproval,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    """Reject a pending refund."""
    from backend.models.payment_refund import PaymentRefund

    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Hanya owner yang bisa reject refund")

    refund = await db.execute(
        select(PaymentRefund).where(PaymentRefund.id == refund_id, PaymentRefund.deleted_at.is_(None)).with_for_update()
    )
    refund = refund.scalar_one_or_none()
    if not refund:
        raise HTTPException(status_code=404, detail="Refund tidak ditemukan")
    if refund.status != 'pending':
        raise HTTPException(status_code=400, detail=f"Refund status '{refund.status}', hanya 'pending' yang bisa di-reject")
    if refund.row_version != body.row_version:
        raise HTTPException(status_code=409, detail="Data berubah, refresh dulu")

    refund.status = 'rejected'
    refund.approved_by = current_user.id
    refund.approved_at = datetime.now(timezone.utc)
    refund.row_version += 1

    await log_audit(
        db=db, action="UPDATE", entity="refund", entity_id=refund.id,
        after_state={"action": "reject"},
        user_id=current_user.id, tenant_id=current_user.tenant_id,
    )
    await db.commit()

    return StandardResponse(
        success=True,
        data=RefundResponse.model_validate(refund),
        request_id=request.state.request_id,
        message="Refund ditolak",
    )
