import asyncio
from typing import Any, List, Optional, Dict
from uuid import UUID
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, func

from backend.core.database import get_db
from backend.api.deps import get_current_user
from backend.models.user import User
from backend.models.payment import Payment
from backend.models.order import Order
from backend.models.outlet import Outlet
from backend.models.shift import Shift, ShiftStatus
from backend.schemas.payment import PaymentCreate, PaymentResponse, PaymentStatus, PaymentMethod
from backend.schemas.order import OrderStatus
from backend.schemas.response import StandardResponse
from backend.models.audit_log import log_audit
from backend.services.midtrans import midtrans_service
from backend.utils.encryption import decrypt_field
from backend.services.fonnte import send_whatsapp_message

router = APIRouter()

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

    # Verify order exists if provided
    if payment_in.order_id:
        order = await db.get(Order, payment_in.order_id)
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
    
    # Generate QRIS via Midtrans if method is qris
    if payment_in.payment_method == PaymentMethod.qris:
        outlet = await db.get(Outlet, payment_in.outlet_id)
        if not outlet or not outlet.midtrans_server_key_encrypted:
            payment.status = PaymentStatus.failed
            payment.midtrans_raw = {"error": "Outlet not configured for QRIS"}
        else:
            try:
                server_key = decrypt_field(outlet.midtrans_server_key_encrypted)
                midtrans_res = await midtrans_service.create_qris_transaction(
                    order_id=str(payment.id),
                    gross_amount=float(payment.amount_due),
                    server_key=server_key,
                    is_production=outlet.midtrans_is_production,
                    custom_field1=str(payment.order_id) if payment.order_id else None,
                    custom_field2=str(current_user.tenant_id)
                )
                
                # Extract QRIS URL from actions
                actions = midtrans_res.get("actions", [])
                for action in actions:
                    if action.get("name") == "generate-qr-code":
                        qris_url = action.get("url")
                        break
                        
                payment.qris_url = qris_url
                payment.midtrans_raw = midtrans_res
                
            except Exception as e:
                # If Midtrans fails, we save the payment as failed
                payment.status = PaymentStatus.failed
                payment.midtrans_raw = {"error": str(e)}
    
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
                
            stmt = (
                update(Order)
                .where(Order.id == payment_in.order_id)
                .values(
                    status=new_order_status,
                    row_version=Order.row_version + 1
                )
            )
            await db.execute(stmt)
            
            # Send WA receipt
            if order.customer_id:
                from backend.models.customer import Customer
                customer = await db.get(Customer, order.customer_id)
                if customer and customer.phone:
                    outlet = await db.get(Outlet, payment_in.outlet_id)
                    outlet_name = outlet.name if outlet else "Kasira"
                    struk = (
                        f"Struk Kasira\n"
                        f"Outlet: {outlet_name}\n"
                        f"Order: #{order.display_number}\n\n"
                        f"Total: Rp{float(order.total_amount):,.0f}\n"
                        f"Telah Lunas\n\n"
                        f"Terima kasih!"
                    )
                    asyncio.create_task(
                        send_whatsapp_message(customer.phone, struk)
                    )
        
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
        request_id=request.state.request_id
    )
    
    return StandardResponse(
        success=True,
        data=PaymentResponse.model_validate(payment),
        request_id=request.state.request_id,
        message="Payment created successfully"
    )

@router.post("/webhook/midtrans")
async def midtrans_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Handle Midtrans webhook notifications.
    """
    payload = await request.json()
    
    order_id = payload.get("order_id") # This is our payment.id
    status_code = payload.get("status_code")
    gross_amount = payload.get("gross_amount")
    signature_key = payload.get("signature_key")
    transaction_status = payload.get("transaction_status")
    
    try:
        payment_uuid = UUID(order_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid order_id format")
        
    # Extract tenant_id from custom_field2 and set search_path
    tenant_id = payload.get("custom_field2")
    if tenant_id:
        try:
            # Validate UUID format to prevent SQL injection
            valid_tenant_id = str(UUID(tenant_id))
            from sqlalchemy import text
            await db.execute(text(f'SET search_path TO "{valid_tenant_id}", public'))
        except ValueError:
            pass # Ignore invalid tenant_id, let db.get fail naturally
        
    # Use SELECT FOR UPDATE to prevent race conditions
    stmt = select(Payment).where(Payment.id == payment_uuid).with_for_update()
    result = await db.execute(stmt)
    payment = result.scalar_one_or_none()
    
    if not payment:
        raise HTTPException(status_code=404, detail="Pembayaran tidak ditemukan")
        
    outlet = await db.get(Outlet, payment.outlet_id)
    if not outlet or not outlet.midtrans_server_key_encrypted:
        raise HTTPException(status_code=400, detail="Outlet not configured for QRIS")
        
    server_key = decrypt_field(outlet.midtrans_server_key_encrypted)
    
    # Verify signature
    is_valid = midtrans_service.verify_signature(
        order_id=order_id,
        status_code=status_code,
        gross_amount=gross_amount,
        signature_key=signature_key,
        server_key=server_key
    )
    
    if not is_valid:
        raise HTTPException(status_code=400, detail="Signature tidak valid")
        
    # Determine new status
    new_status = payment.status
    if transaction_status in ['settlement', 'capture']:
        if float(gross_amount) < float(payment.amount_due):
            new_status = PaymentStatus.failed # Reject if underpaid
        else:
            new_status = PaymentStatus.paid
    elif transaction_status in ['deny', 'cancel', 'expire', 'failure']:
        new_status = PaymentStatus.failed
        
    if new_status != payment.status:
        payment.status = new_status
        payment.midtrans_raw = payload
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
                        
                    stmt = (
                        update(Order)
                        .where(Order.id == payment.order_id)
                        .values(
                            status=new_order_status,
                            row_version=Order.row_version + 1
                        )
                    )
                    await db.execute(stmt)
                    
                    # Send WA receipt
                    if order.customer_id:
                        from backend.models.customer import Customer
                        customer = await db.get(Customer, order.customer_id)
                        if customer and customer.phone:
                            outlet = await db.get(Outlet, payment.outlet_id)
                            outlet_name = outlet.name if outlet else "Kasira"
                            struk = (
                                f"Struk Kasira\n"
                                f"Outlet: {outlet_name}\n"
                                f"Order: #{order.display_number}\n\n"
                                f"Total: Rp{float(order.total_amount):,.0f}\n"
                                f"Telah Lunas\n\n"
                                f"Terima kasih!"
                            )
                            asyncio.create_task(
                                send_whatsapp_message(customer.phone, struk)
                            )
                
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
