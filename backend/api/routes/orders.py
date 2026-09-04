from typing import Any, List, Optional
from uuid import UUID
from datetime import datetime, timezone, date
from decimal import Decimal
from sqlalchemy.orm import selectinload
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, text, func

from backend.core.database import get_db
from backend.core.config import settings
from backend.api.deps import get_current_user
from backend.models.user import User
from backend.models.order import Order, OrderItem
from backend.models.payment import Payment
from backend.models.product import Product
from backend.models.outlet import Outlet
from backend.models.outlet_tax_config import OutletTaxConfig
from backend.models.shift import Shift, ShiftStatus
from backend.models.tenant import Tenant
from backend.schemas.order import OrderCreate, OrderUpdateStatus, OrderResponse, OrderStatus, OrderType, OrderAccept, OrderReject, KitchenStatusUpdate
import asyncio
import json
from fastapi.responses import StreamingResponse
from backend.services import online_orders
from backend.services.order_lifecycle import (
    accept_order, cancel_order, mark_ready,
    restore_stock_for_order, recalc_tab_after_cancel, release_table_if_idle,
)
from backend.schemas.response import StandardResponse
from backend.services.audit import log_audit
from backend.models.reservation import Table
from backend.services.stock_service import deduct_stock, restore_stock_on_cancel
from backend.services.ingredient_stock_service import deduct_ingredients_for_product, restore_ingredients_on_cancel
from backend.services.variant_utils import resolve_variant
from backend.models.event import Event

router = APIRouter()

@router.post("/", response_model=StandardResponse[OrderResponse])
async def create_order(
    request: Request,
    order_in: OrderCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    """
    Create a new order and deduct stock (Transaction-First Simple Stock).
    """
    if not order_in.items:
        raise HTTPException(status_code=400, detail="Order harus memiliki minimal 1 item")

    # Validasi outlet milik tenant user
    outlet = (await db.execute(
        select(Outlet).where(
            Outlet.id == order_in.outlet_id,
            Outlet.tenant_id == current_user.tenant_id,
            Outlet.deleted_at.is_(None),
        )
    )).scalar_one_or_none()
    if not outlet:
        raise HTTPException(status_code=403, detail="Outlet tidak ditemukan atau bukan milik tenant Anda")

    # Idempotent: id dari klien udah ada → ini retry (respons pertama hilang
    # di jaringan). Balikin order yang sama, jangan bikin lagi + potong stok 2x.
    if order_in.id:
        existing = (await db.execute(
            select(Order)
            .options(selectinload(Order.items).selectinload(OrderItem.product))
            .where(Order.id == order_in.id, Order.outlet_id == order_in.outlet_id)
        )).scalar_one_or_none()
        if existing:
            return StandardResponse(
                success=True,
                message="Order already exists (idempotent)",
                data=OrderResponse.model_validate(existing),
                request_id=request.state.request_id,
            )

    # Validasi table untuk dine_in
    # Pro: wajib pilih meja. Starter: boleh dine-in tanpa meja.
    tenant_stmt = select(Tenant).where(Tenant.id == current_user.tenant_id)
    tenant_check = (await db.execute(tenant_stmt)).scalar_one_or_none()
    is_pro = getattr(getattr(tenant_check, "subscription_tier", None), "value", "starter") in ("pro", "business", "enterprise")

    table = None
    if order_in.order_type == OrderType.dine_in:
        if not order_in.table_id and is_pro:
            raise HTTPException(status_code=400, detail="Dine-in order wajib pilih meja")
        table = (await db.execute(
            select(Table).where(
                Table.id == order_in.table_id,
                Table.outlet_id == order_in.outlet_id,
                Table.is_active == True,
                Table.deleted_at.is_(None),
            ).with_for_update()
        )).scalar_one_or_none()
        if not table:
            raise HTTPException(status_code=404, detail="Meja tidak ditemukan")
        if table.status not in ("available", "occupied"):
            raise HTTPException(status_code=400, detail=f"Meja {table.name} sedang {table.status}, tidak bisa dipakai")
    elif order_in.table_id:
        # Takeaway/delivery should not have table
        order_in.table_id = None

    # Validasi shift. HP nyimpen shift_session_id di cache; begitu janitor
    # nutup sesi di 04.00, id itu basi. Dulu ditolak 400 "sudah ditutup" =
    # kasir pagi-pagi mentok. Sekarang id basi diperlakukan sama dengan
    # nggak ngirim: pakai (atau buka) shift yang terbuka di outlet.
    if order_in.shift_session_id:
        shift = (await db.execute(
            select(Shift).where(
                Shift.id == order_in.shift_session_id,
                Shift.outlet_id == order_in.outlet_id,
                Shift.status == ShiftStatus.open,
                Shift.deleted_at.is_(None),
            )
        )).scalar_one_or_none()
        if not shift:
            order_in.shift_session_id = None
        else:
            from backend.services.shift_service import assert_can_use_shift
            await assert_can_use_shift(db, shift, current_user.id)
    if not order_in.shift_session_id:
        # Shift otomatis: nggak ada yang terbuka → dibuka sendiri di transaksi
        # pertama. Kasir nggak pernah dihadang "buka shift dulu" lagi.
        from backend.services.shift_service import ensure_open_shift
        open_shift = await ensure_open_shift(
            db, order_in.outlet_id, current_user.id, current_user.tenant_id, source="order",
        )
        order_in.shift_session_id = open_shift.id

    # 1. Create Order
    result = await db.execute(text("SELECT nextval('order_display_seq')"))
    display_number = result.scalar()
    order_number = f"ORD-{datetime.now(timezone.utc).strftime('%Y%m%d')}-{display_number}"

    # Calculate totals server-side from items (fallback if client sends 0)
    from decimal import Decimal as D
    from backend.models.outlet_tax_config import OutletTaxConfig

    calculated_subtotal = sum(item.total_price for item in order_in.items)
    subtotal = order_in.subtotal if order_in.subtotal > 0 else calculated_subtotal
    discount = order_in.discount_amount or D(0)

    # Discount override check: if discount > 20% of subtotal, require permission
    discount_approved_by = None
    if discount > 0 and subtotal > 0:
        discount_pct = (discount / subtotal) * 100
        if discount_pct > 20 and not current_user.is_superuser:
            from backend.models.role import Role
            role = await db.get(Role, current_user.role_id) if current_user.role_id else None
            if not role or not role.can_discount_override:
                raise HTTPException(
                    status_code=403,
                    detail=f"Diskon {discount_pct:.0f}% melebihi batas 20%. Perlu persetujuan supervisor."
                )
            discount_approved_by = current_user.id

    # Auto-calculate tax & service charge from outlet config
    tax_config = (await db.execute(
        select(OutletTaxConfig).where(
            OutletTaxConfig.outlet_id == order_in.outlet_id,
            OutletTaxConfig.deleted_at == None,
        )
    )).scalar_one_or_none()

    taxable_amount = subtotal - discount  # tax calculated after discount

    if tax_config and tax_config.pb1_enabled and tax_config.tax_pct > 0:
        if tax_config.tax_inclusive:
            # Harga sudah termasuk pajak — extract tax from subtotal
            tax = taxable_amount - (taxable_amount / D(str(1 + tax_config.tax_pct / 100)))
        else:
            tax = taxable_amount * D(str(tax_config.tax_pct / 100))
        tax = tax.quantize(D("1"))  # round to whole rupiah
    else:
        tax = order_in.tax_amount or D(0)

    if tax_config and tax_config.service_charge_enabled and tax_config.service_charge_pct > 0:
        service_charge = taxable_amount * D(str(tax_config.service_charge_pct / 100))
        service_charge = service_charge.quantize(D("1"))
    else:
        service_charge = order_in.service_charge_amount or D(0)

    if tax_config and tax_config.tax_inclusive:
        # Total = subtotal (sudah termasuk tax) + service charge - discount
        calculated_total = subtotal + service_charge - discount
    else:
        calculated_total = subtotal + service_charge + tax - discount

    total_amount = calculated_total if (tax_config and (tax_config.pb1_enabled or tax_config.service_charge_enabled)) else (order_in.total_amount if order_in.total_amount > 0 else calculated_total)

    order = Order(
        **({"id": order_in.id} if order_in.id else {}),
        outlet_id=order_in.outlet_id,
        shift_session_id=order_in.shift_session_id,
        customer_id=order_in.customer_id,
        table_id=order_in.table_id,
        user_id=order_in.user_id or current_user.id,
        order_number=order_number,
        display_number=display_number,
        order_type=order_in.order_type,
        subtotal=subtotal,
        service_charge_amount=service_charge,
        tax_amount=tax,
        discount_amount=discount,
        total_amount=total_amount,
        notes=order_in.notes,
        discount_approved_by=discount_approved_by,
        status=OrderStatus.pending
    )
    db.add(order)
    await db.flush() # To get order.id

    # 2. Process Order Items and Deduct Stock — reuse tenant_check dari guard di atas
    raw_tier = getattr(tenant_check, "subscription_tier", "starter") or "starter" if tenant_check else "starter"
    tier = raw_tier.value if hasattr(raw_tier, 'value') else str(raw_tier)

    sm = getattr(outlet, 'stock_mode', 'simple')
    stock_mode = sm.value if hasattr(sm, 'value') else str(sm or 'simple')

    # Sort items by product_id → konsisten lock order across concurrent orders → no deadlock.
    sorted_items = sorted(order_in.items, key=lambda i: str(i.product_id))

    for item_in in sorted_items:
        # Fetch product to check stock
        product = await db.get(Product, item_in.product_id)
        if not product or product.deleted_at is not None:
            raise HTTPException(status_code=404, detail="Produk tidak ditemukan")

        # Varian: WAJIB divalidasi milik produknya sendiri. Tanpa cek ini klien
        # bisa ngirim product_id produk murah + variant_id punya produk lain,
        # dan harga jadi bisa diatur dari luar. Lihat `variant_utils`.
        try:
            variant = await resolve_variant(db, product.id, item_in.product_variant_id)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        # Nama varian ikut disimpan di `modifiers` supaya struk, layar dapur,
        # dan riwayat tetap kebaca "Kopi Susu (Dingin)" walau varian-nya nanti
        # dihapus pemilik. Nyimpen id doang bikin baris lama jadi teka-teki.
        if variant is not None:
            item_modifiers = dict(item_in.modifiers or {})
            item_modifiers.setdefault("variant_name", variant.name)
            item_in = item_in.model_copy(update={"modifiers": item_modifiers})

        # Deduct stock — branch by outlet stock_mode
        if product.stock_enabled:
            if stock_mode == "recipe":
                await deduct_ingredients_for_product(
                    db,
                    product_id=product.id,
                    quantity=item_in.quantity,
                    outlet_id=order_in.outlet_id,
                    order_id=order.id,
                    user_id=current_user.id,
                    tier=tier,
                    product_name=product.name,
                )
            else:
                await deduct_stock(
                    db,
                    product=product,
                    quantity=item_in.quantity,
                    outlet_id=order_in.outlet_id,
                    order_id=order.id,
                    user_id=current_user.id,
                    tier=tier,
                )

        # Create Order Item
        order_item = OrderItem(
            order_id=order.id,
            product_id=item_in.product_id,
            product_variant_id=item_in.product_variant_id,
            quantity=item_in.quantity,
            unit_price=item_in.unit_price,
            discount_amount=item_in.discount_amount,
            total_price=item_in.total_price,
            modifiers=item_in.modifiers,
            notes=item_in.notes
        )
        db.add(order_item)

    # Set table status to occupied if dine-in
    if table and table.status == "available":
        await db.execute(
            update(Table).where(Table.id == table.id)
            .values(status="occupied", row_version=Table.row_version + 1)
        )

    # Append order.created event to event store
    db.add(Event(
        outlet_id=order.outlet_id,
        stream_id=f"order:{order.id}",
        event_type="order.created",
        event_data={
            "order_id": str(order.id),
            "outlet_id": str(order.outlet_id),
            "order_number": order_number,
            "display_number": display_number,
            "order_type": order_in.order_type,
            "subtotal": float(subtotal),
            "tax_amount": float(tax),
            "service_charge": float(service_charge),
            "discount_amount": float(discount),
            "total_amount": float(total_amount),
            "item_count": len(order_in.items),
            "items": [
                {"product_id": str(i.product_id), "qty": i.quantity, "unit_price": float(i.unit_price)}
                for i in order_in.items
            ],
            "customer_id": str(order_in.customer_id) if order_in.customer_id else None,
            "table_id": str(order_in.table_id) if order_in.table_id else None,
            "source": "pos",
        },
        event_metadata={
            "tier": tier,
            "user_id": str(current_user.id),
            "ts": datetime.now(timezone.utc).isoformat(),
        },
    ))

    # 1. Pastikan commit sudah selesai
    await db.commit()

    # Re-set RLS tenant context: SET LOCAL resets after commit (new implicit tx).
    # Without this, selectinload query below gets blocked by RLS policy.
    await db.execute(text(f"SET LOCAL app.current_tenant_id = '{current_user.tenant_id}'"))

    # 2. Ambil ulang data Order — selectinload di semua level (wajib untuk async)
    query = (
        select(Order)
        .options(
            selectinload(Order.items).selectinload(OrderItem.product)
        )
        .where(Order.id == order.id)
    )

    result = await db.execute(query)
    order_loaded = result.scalar_one()

    # 3. Jalankan Audit Log
    await log_audit(
        db=db,
        action="CREATE",
        entity="order",
        entity_id=order_loaded.id,
        after_state={
            "order_number": order_loaded.order_number, 
            "total_amount": float(order_loaded.total_amount)
        },
        user_id=current_user.id,
        tenant_id=current_user.tenant_id,
    )

    # 4. Return Response
    return StandardResponse(
        success=True,
        message="Order created successfully",
        data=OrderResponse.model_validate(order_loaded),
        request_id=request.state.request_id
    )

@router.get("/", response_model=StandardResponse[List[OrderResponse]])
async def read_orders(
    request: Request,
    outlet_id: UUID,
    status: Optional[OrderStatus] = None,
    table_id: Optional[UUID] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    """
    Retrieve orders.
    """
    query = select(Order).options(
        selectinload(Order.items).selectinload(OrderItem.product)
    ).where(
        Order.outlet_id == outlet_id,
        Order.deleted_at.is_(None)
    )

    if status:
        query = query.where(Order.status == status)
    if table_id:
        query = query.where(Order.table_id == table_id)
    if start_date:
        start_dt = datetime.combine(start_date, datetime.min.time()).replace(tzinfo=timezone.utc)
        query = query.where(Order.created_at >= start_dt)
    if end_date:
        end_dt = datetime.combine(end_date, datetime.max.time()).replace(tzinfo=timezone.utc)
        query = query.where(Order.created_at <= end_dt)

    query = query.order_by(Order.created_at.desc()).offset(skip).limit(limit)

    result = await db.execute(query)
    orders = result.scalars().all()

    # Fetch payment info for these orders in one query
    order_ids = [o.id for o in orders]
    payment_map: dict = {}
    if order_ids:
        pay_result = await db.execute(
            select(Payment.order_id, Payment.payment_method, Payment.status).where(
                Payment.order_id.in_(order_ids),
                Payment.deleted_at.is_(None),
            )
        )
        for row in pay_result.all():
            payment_map[row.order_id] = {
                "payment_method": row.payment_method,
                "payment_status": row.status,
            }

    order_responses = []
    for o in orders:
        resp = OrderResponse.model_validate(o)
        pay_info = payment_map.get(o.id)
        if pay_info:
            resp.payment_method = pay_info["payment_method"]
            resp.payment_status = pay_info["payment_status"]
        order_responses.append(resp)

    return StandardResponse(
        success=True,
        data=order_responses,
        request_id=request.state.request_id
    )

ONLINE_ACTIVE_STATUSES = ("pending", "preparing", "ready")


async def _attach_payment_info(db, orders) -> list:
    order_ids = [o.id for o in orders]
    payment_map: dict = {}
    if order_ids:
        pay_result = await db.execute(
            select(Payment.order_id, Payment.payment_method, Payment.status, Payment.channel, Payment.proof_image_url).where(
                Payment.order_id.in_(order_ids), Payment.deleted_at.is_(None),
            ).order_by(Payment.created_at.asc())
        )
        for row in pay_result.all():
            payment_map[row.order_id] = {"payment_method": row.payment_method, "payment_status": row.status,
                                         "payment_channel": row.channel, "payment_proof_url": row.proof_image_url}
    out = []
    for o in orders:
        resp = OrderResponse.model_validate(o)
        info = payment_map.get(o.id)
        if info:
            resp.payment_method = info["payment_method"]
            resp.payment_status = info["payment_status"]
            resp.payment_channel = info["payment_channel"]
            resp.payment_proof_url = info["payment_proof_url"]
        out.append(resp)
    return out


async def _owned_outlet(db, outlet_id: UUID, current_user: User) -> Outlet:
    outlet = (await db.execute(
        select(Outlet).where(Outlet.id == outlet_id, Outlet.tenant_id == current_user.tenant_id, Outlet.deleted_at.is_(None))
    )).scalar_one_or_none()
    if not outlet:
        raise HTTPException(status_code=403, detail="Outlet tidak ditemukan atau bukan milik tenant Anda")
    return outlet


@router.get("/online", response_model=StandardResponse[List[OrderResponse]])
async def read_online_orders(
    request: Request,
    outlet_id: UUID,
    include_done: bool = False,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    """Pesanan dari storefront untuk layar "Pesanan Online" di app kasir.

    Default: yang masih hidup (pending, preparing, ready). QRIS yang belum
    dibayar SENGAJA disaring: kasir nggak perlu lihat pesanan yang pelanggannya
    belum tentu bayar. `include_done=true` menambahkan selesai/batal hari ini.
    """
    await _owned_outlet(db, outlet_id, current_user)
    q = select(Order).options(selectinload(Order.items).selectinload(OrderItem.product)).where(
        Order.outlet_id == outlet_id, Order.source == "storefront", Order.deleted_at.is_(None),
    )
    if include_done:
        start_today = datetime.now(timezone.utc) - __import__("datetime").timedelta(hours=24)
        q = q.where((Order.status.in_(ONLINE_ACTIVE_STATUSES)) | (Order.created_at >= start_today))
    else:
        q = q.where(Order.status.in_(ONLINE_ACTIVE_STATUSES))
    q = q.order_by(Order.created_at.desc()).limit(limit)
    orders = (await db.execute(q)).scalars().all()
    responses = await _attach_payment_info(db, orders)
    # Saring QRIS Xendit yang belum lunas dari daftar aktif. QRIS manual
    # (QR statis toko) TETAP tampil: kasir yang memastikan uangnya masuk.
    responses = [
        r for r in responses
        if not (r.status == OrderStatus.pending and r.payment_method == "qris"
                and r.payment_status != "paid" and (r.payment_channel or "xendit") != "manual")
    ]
    return StandardResponse(success=True, data=responses, request_id=request.state.request_id)


@router.get("/kitchen", response_model=StandardResponse[dict])
async def read_kitchen_orders(
    request: Request,
    outlet_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    """Papan dapur: {active: [...], done: [...]}.

    Yang masuk antrean dapur: order yang SUDAH pasti dibuat, yaitu
    - status preparing/ready/served (meja, tab, online yang sudah diterima), atau
    - status completed dalam 3 jam terakhir (pesanan kasir yang dibayar langsung;
      tanpa ini dapur nggak pernah lihat pesanan bawa pulang),
    dan belum ditandai `done` oleh dapur. Online yang masih `pending`
    (belum dikonfirmasi kasir) SENGAJA tidak masuk: kasir yang memutuskan.
    """
    await _owned_outlet(db, outlet_id, current_user)
    import datetime as _dt
    now = datetime.now(timezone.utc)
    base = select(Order).options(selectinload(Order.items).selectinload(OrderItem.product)).where(
        Order.outlet_id == outlet_id, Order.deleted_at.is_(None),
        Order.created_at >= now - _dt.timedelta(hours=14),
    )
    active_q = base.where(
        (Order.kitchen_status.is_(None)) | (Order.kitchen_status != "done"),
        (Order.status.in_(["preparing", "ready", "served"]))
        | ((Order.status == "completed") & (Order.created_at >= now - _dt.timedelta(hours=3))),
    ).order_by(Order.created_at.asc()).limit(80)
    done_q = base.where(Order.kitchen_status == "done").order_by(Order.updated_at.desc()).limit(40)
    active = (await db.execute(active_q)).scalars().all()
    done = (await db.execute(done_q)).scalars().all()

    table_ids = {o.table_id for o in active + done if o.table_id}
    table_names = {}
    if table_ids:
        rows = (await db.execute(select(Table.id, Table.name).where(Table.id.in_(table_ids)))).all()
        table_names = {r.id: r.name for r in rows}

    def ser(o: Order) -> dict:
        return {
            "id": str(o.id),
            "display_number": o.display_number,
            "order_number": o.order_number,
            "status": str(getattr(o.status, "value", o.status)),
            "kitchen_status": o.kitchen_status or "queued",
            "order_type": str(getattr(o.order_type, "value", o.order_type)),
            "source": o.source,
            "table_name": table_names.get(o.table_id),
            "customer_name": o.customer_name,
            "notes": o.notes,
            "created_at": o.created_at.isoformat(),
            "updated_at": o.updated_at.isoformat() if o.updated_at else None,
            "row_version": o.row_version,
            "items": [
                {"product_name": it.product_name, "quantity": it.quantity, "notes": it.notes}
                for it in o.items
            ],
        }

    return StandardResponse(success=True, data={"active": [ser(o) for o in active], "done": [ser(o) for o in done]},
                            request_id=request.state.request_id)


@router.post("/{order_id}/kitchen-status", response_model=StandardResponse[dict])
async def update_kitchen_status(
    request: Request,
    order_id: UUID,
    body: KitchenStatusUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    """Dapur: preparing -> ready -> done. Nggak menyentuh pembayaran.

    `ready` pada order yang statusnya masih `preparing` ikut menaikkan status
    order ke `ready` (pelanggan online dikabari "siap diambil"). Selain itu
    status order dibiarkan: penyelesaian tetap urusan kasir dan pembayaran.
    """
    order = await _load_order_full(db, order_id)
    outlet = await _owned_outlet(db, order.outlet_id, current_user)
    if str(getattr(order.status, "value", order.status)) == "cancelled":
        raise HTTPException(status_code=400, detail="Pesanan sudah dibatalkan")
    now = datetime.now(timezone.utc)
    order.kitchen_status = body.status
    order.updated_at = now
    notify_ready = False
    if body.status == "ready" and str(getattr(order.status, "value", order.status)) == "preparing":
        order.status = "ready"
        order.row_version += 1
        await mark_ready(db, order)
        notify_ready = order.source == "storefront"
    db.add(Event(
        outlet_id=order.outlet_id,
        stream_id=f"order:{order.id}",
        event_type=f"kitchen.{body.status}",
        event_data={"order_id": str(order.id), "outlet_id": str(order.outlet_id), "order_number": order.order_number},
        event_metadata={"user_id": str(current_user.id), "ts": now.isoformat()},
    ))
    phone = order.customer_phone
    await db.commit()
    if notify_ready:
        asyncio.create_task(online_orders.wa_customer(outlet, phone, online_orders.msg_ready(order, outlet)))
    return StandardResponse(success=True, data={"id": str(order.id), "kitchen_status": body.status,
                            "status": str(getattr(order.status, "value", order.status))},
                            request_id=request.state.request_id, message="Status dapur diperbarui")


@router.get("/stream")
async def stream_orders(
    outlet_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """SSE: kabar real-time pesanan online (order.created / accepted / ready / cancelled).

    Sumbernya Redis pub/sub kanal `orders:{outlet_id}` (lihat services/online_orders).
    Heartbeat komentar tiap 15 detik supaya koneksi lewat nginx dan Cloudflare
    nggak dianggap idle. Klien yang putus cukup connect lagi lalu GET /orders/online.
    """
    await _owned_outlet(db, outlet_id, current_user)

    async def gen():
        pubsub = online_orders._redis.pubsub()
        await pubsub.subscribe(online_orders.channel_for(outlet_id))
        try:
            yield "event: hello\ndata: {}\n\n"
            while True:
                msg = await pubsub.get_message(ignore_subscribe_messages=True, timeout=15.0)
                if msg is None:
                    yield ": ping\n\n"
                    continue
                data = msg.get("data")
                if isinstance(data, (bytes, bytearray)):
                    data = data.decode()
                try:
                    ev = json.loads(data).get("type", "message")
                except Exception:  # noqa: BLE001
                    ev = "message"
                yield f"event: {ev}\ndata: {data}\n\n"
        except asyncio.CancelledError:
            raise
        finally:
            try:
                await pubsub.unsubscribe(online_orders.channel_for(outlet_id))
                await pubsub.close()
            except Exception:  # noqa: BLE001
                pass

    return StreamingResponse(gen(), media_type="text/event-stream", headers={
        "Cache-Control": "no-cache", "X-Accel-Buffering": "no", "Connection": "keep-alive",
    })


async def _load_order_full(db, order_id: UUID) -> Order:
    order = (await db.execute(
        select(Order).options(selectinload(Order.items).selectinload(OrderItem.product)).where(Order.id == order_id)
    )).scalar_one_or_none()
    if not order or order.deleted_at is not None:
        raise HTTPException(status_code=404, detail="Order tidak ditemukan")
    return order


@router.post("/{order_id}/accept", response_model=StandardResponse[OrderResponse])
async def accept_online_order(
    request: Request,
    order_id: UUID,
    body: OrderAccept,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    """Toko menerima pesanan online + memberi perkiraan waktu. pending -> preparing."""
    order = await _load_order_full(db, order_id)
    outlet = await _owned_outlet(db, order.outlet_id, current_user)
    if str(getattr(order.status, 'value', order.status)) != "pending":
        raise HTTPException(status_code=400, detail="Pesanan ini sudah diproses")
    await accept_order(db, order, outlet, eta_minutes=body.eta_minutes, actor_user_id=current_user.id)
    phone = order.customer_phone
    await db.commit()
    await log_audit(db=db, action="ACCEPT_ONLINE_ORDER", entity="order", entity_id=order.id,
                    after_state={"eta_minutes": body.eta_minutes}, user_id=current_user.id, tenant_id=current_user.tenant_id)
    if order.source == "storefront":
        asyncio.create_task(online_orders.wa_customer(outlet, phone, online_orders.msg_accepted(order, outlet)))
    order = await _load_order_full(db, order_id)
    return StandardResponse(success=True, data=(await _attach_payment_info(db, [order]))[0],
                            request_id=request.state.request_id, message="Pesanan diterima")


@router.post("/{order_id}/reject", response_model=StandardResponse[OrderResponse])
async def reject_online_order(
    request: Request,
    order_id: UUID,
    body: OrderReject,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    """Toko menolak pesanan online dengan alasan. Stok kembali, QRIS di-refund, pelanggan dikabari."""
    order = await _load_order_full(db, order_id)
    outlet = await _owned_outlet(db, order.outlet_id, current_user)
    if str(getattr(order.status, 'value', order.status)) in ("completed", "cancelled"):
        raise HTTPException(status_code=400, detail="Pesanan ini sudah selesai atau dibatalkan")
    info = await cancel_order(db, order, outlet, reason=body.reason, actor_user_id=current_user.id, by="cashier")
    phone = order.customer_phone
    await db.commit()
    await log_audit(db=db, action="REJECT_ONLINE_ORDER", entity="order", entity_id=order.id,
                    after_state={"reason": body.reason, **info}, user_id=current_user.id, tenant_id=current_user.tenant_id)
    if order.source == "storefront":
        asyncio.create_task(online_orders.wa_customer(
            outlet, phone, online_orders.msg_cancelled(order, outlet, refund_amount=info["refund_amount"], refund_manual=info["refund_manual"])))
        if info["refund_manual"] and info["refund_amount"]:
            asyncio.create_task(online_orders.wa_owner(outlet, online_orders.msg_owner_refund_manual(order, outlet, info["refund_amount"])))
    order = await _load_order_full(db, order_id)
    return StandardResponse(success=True, data=(await _attach_payment_info(db, [order]))[0],
                            request_id=request.state.request_id, message="Pesanan ditolak")


@router.get("/{order_id}", response_model=StandardResponse[OrderResponse])
async def read_order(
    request: Request,
    order_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    """
    Get order by ID.
    """
    query = select(Order).options(
        selectinload(Order.items).selectinload(OrderItem.product)
    ).where(Order.id == order_id)
    result = await db.execute(query)
    order = result.scalar_one_or_none()
    
    if not order or order.deleted_at is not None:
        raise HTTPException(status_code=404, detail="Order tidak ditemukan")
        
    return StandardResponse(
        success=True,
        data=OrderResponse.model_validate(order),
        request_id=request.state.request_id
    )

@router.put("/{order_id}/status", response_model=StandardResponse[OrderResponse])
async def update_order_status(
    request: Request,
    order_id: UUID,
    status_in: OrderUpdateStatus,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    """
    Update order status with optimistic locking.
    """
    query = select(Order).options(selectinload(Order.items)).where(Order.id == order_id)
    result = await db.execute(query)
    order = result.scalar_one_or_none()
    
    if not order or order.deleted_at is not None:
        raise HTTPException(status_code=404, detail="Order tidak ditemukan")

    # Use client row_version if provided and matches, otherwise use server's current version
    current_rv = order.row_version
    if status_in.row_version > 0 and status_in.row_version != current_rv:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Order telah diubah, silakan refresh"
        )

    before_state = {"status": order.status}
    is_storefront = getattr(order, 'source', 'pos') == 'storefront'
    cur_status = str(getattr(order.status, 'value', order.status))

    # Pesanan online punya efek samping yang pesanan kasir nggak punya (WA ke
    # pelanggan, refund QRIS, perkiraan waktu). Tombol lama di app ("Terima &
    # Proses" = preparing, "Tolak" = cancelled) tetap jalan lewat sini.
    if is_storefront and status_in.status == OrderStatus.cancelled:
        outlet = await db.get(Outlet, order.outlet_id)
        info = await cancel_order(db, order, outlet, reason="Dibatalkan oleh toko", actor_user_id=current_user.id, by="cashier")
        phone = order.customer_phone
        await db.commit()
        if outlet is not None:
            asyncio.create_task(online_orders.wa_customer(
                outlet, phone, online_orders.msg_cancelled(order, outlet, refund_amount=info["refund_amount"], refund_manual=info["refund_manual"])))
            if info["refund_manual"] and info["refund_amount"]:
                asyncio.create_task(online_orders.wa_owner(outlet, online_orders.msg_owner_refund_manual(order, outlet, info["refund_amount"])))
        return await _status_response(db, request, order_id, before_state, current_user, "Pesanan dibatalkan")
    if is_storefront and status_in.status == OrderStatus.preparing and cur_status == "pending":
        outlet = await db.get(Outlet, order.outlet_id)
        await accept_order(db, order, outlet, eta_minutes=15, actor_user_id=current_user.id)
        phone = order.customer_phone
        await db.commit()
        if outlet is not None:
            asyncio.create_task(online_orders.wa_customer(outlet, phone, online_orders.msg_accepted(order, outlet)))
        return await _status_response(db, request, order_id, before_state, current_user, "Pesanan diterima")

    stmt = (
        update(Order)
        .where(Order.id == order_id, Order.row_version == current_rv)
        .values(
            status=status_in.status,
            row_version=Order.row_version + 1,
            updated_at=datetime.now(timezone.utc),
            **({"ready_at": datetime.now(timezone.utc)} if status_in.status == OrderStatus.ready else {}),
        )
        .returning(Order)
    )
    
    result = await db.execute(stmt)
    updated_order = result.scalar_one_or_none()
    
    if not updated_order:
        raise HTTPException(status_code=409, detail="Concurrent update detected.")

    # COD (tunai antar, delivery gelombang 1): uangnya baru masuk waktu kurir
    # sampai. Pesanan ditandai selesai = pembayaran tunai yang masih pending
    # ditandai lunas, supaya laporan (yang cuma menghitung order lunas) melihatnya.
    if is_storefront and status_in.status == OrderStatus.completed:
        from backend.services.order_lifecycle import latest_payment as _lp, _val as _v
        pay = await _lp(db, order.id)
        if pay is not None and _v(pay.payment_method) == "cash" and _v(pay.status) == "pending":
            _now = datetime.now(timezone.utc)
            pay.status = "paid"
            pay.paid_at = _now
            pay.amount_paid = pay.amount_due
            pay.row_version = (pay.row_version or 0) + 1

    # Efek samping lewat order_lifecycle (satu pintu bersama tolak/janitor pesanan online).
    if status_in.status == OrderStatus.cancelled:
        outlet = await db.get(Outlet, order.outlet_id)
        await restore_stock_for_order(db, order, outlet)
        await recalc_tab_after_cancel(db, order)
    if status_in.status in (OrderStatus.completed, OrderStatus.cancelled) and order.table_id:
        await release_table_if_idle(db, order)
    if is_storefront and status_in.status == OrderStatus.ready:
        await mark_ready(db, order)

    # Append order lifecycle event to event store
    status_val = status_in.status.value if hasattr(status_in.status, 'value') else str(status_in.status)
    event_type = f"order.{status_val}"
    db.add(Event(
        outlet_id=order.outlet_id,
        stream_id=f"order:{order.id}",
        event_type=event_type,
        event_data={
            "order_id": str(order.id),
            "outlet_id": str(order.outlet_id),
            "order_number": order.order_number,
            "from_status": before_state["status"].value if hasattr(before_state["status"], 'value') else str(before_state["status"]),
            "to_status": status_val,
            "total_amount": float(order.total_amount),
            "order_type": order.order_type,
            "item_count": len(order.items),
            "table_id": str(order.table_id) if order.table_id else None,
            "customer_id": str(order.customer_id) if order.customer_id else None,
        },
        event_metadata={
            "user_id": str(current_user.id),
            "ts": datetime.now(timezone.utc).isoformat(),
        },
    ))

    await db.commit()

    if is_storefront and status_in.status == OrderStatus.ready:
        outlet = await db.get(Outlet, order.outlet_id)
        if outlet is not None:
            asyncio.create_task(online_orders.wa_customer(outlet, order.customer_phone, online_orders.msg_ready(order, outlet)))

    return await _status_response(db, request, order_id, before_state, current_user, "Order status updated successfully")


async def _status_response(db, request, order_id, before_state, current_user, message):
    # Reload items for response (selectinload product to avoid MissingGreenlet on product_name)
    query = select(Order).options(
        selectinload(Order.items).selectinload(OrderItem.product)
    ).where(Order.id == order_id)
    updated_order_loaded = (await db.execute(query)).scalar_one()

    await log_audit(
        db=db,
        action="UPDATE_STATUS",
        entity="order",
        entity_id=updated_order_loaded.id,
        before_state=before_state,
        after_state={"status": updated_order_loaded.status},
        user_id=current_user.id,
        tenant_id=current_user.tenant_id,
    )
    return StandardResponse(
        success=True,
        data=(await _attach_payment_info(db, [updated_order_loaded]))[0],
        request_id=request.state.request_id,
        message=message,
    )


@router.get("/{order_id}/receipt", response_model=StandardResponse[dict])
async def get_order_receipt(
    request: Request,
    order_id: UUID,
    payment_id: Optional[UUID] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    """
    Return structured receipt data untuk reprint di mobile/POS.
    Flutter konsumsi JSON ini lalu rebuild ESC/POS bytes via buildReceipt().
    Offline fallback: Flutter bisa rebuild dari drift DB lokal.

    Optional ?payment_id=... — kalau diset, return SUBSET receipt:
    cuma items yg `paid_payment_id == payment_id` (untuk struk per ad-hoc payment).
    Subset totals di-recompute dari items yg ke-include + payment record yg match.
    Tanpa param → existing full-receipt behavior (backward compat).
    """
    # Load order + items (+ product untuk fallback nama item)
    query = select(Order).options(
        selectinload(Order.items).selectinload(OrderItem.product)
    ).where(Order.id == order_id, Order.deleted_at.is_(None))
    order = (await db.execute(query)).scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="Order tidak ditemukan")

    # Tenant scoping via outlet
    outlet = await db.get(Outlet, order.outlet_id)
    if not outlet or outlet.tenant_id != current_user.tenant_id:
        raise HTTPException(status_code=403, detail="Order bukan milik tenant Anda")

    # Determine target payment + items subset
    if payment_id:
        payment = await db.get(Payment, payment_id)
        if not payment or payment.outlet_id != outlet.id:
            raise HTTPException(status_code=404, detail="Payment tidak ditemukan")
        filtered_items = [i for i in order.items if i.paid_payment_id == payment_id]
        if not filtered_items:
            raise HTTPException(
                status_code=404,
                detail="Tidak ada item terkait payment ini di order"
            )
        is_subset = True
    else:
        # Latest payment untuk method, amount_paid, change
        payment = (await db.execute(
            select(Payment)
            .where(Payment.order_id == order.id, Payment.deleted_at.is_(None))
            .order_by(Payment.created_at.desc())
            .limit(1)
        )).scalar_one_or_none()
        filtered_items = list(order.items)
        is_subset = False

    # Tax config (NPWP + custom receipt footer)
    tax_cfg = (await db.execute(
        select(OutletTaxConfig).where(OutletTaxConfig.outlet_id == outlet.id)
    )).scalar_one_or_none()

    # Format tanggal WIB (sama seperti WhatsApp receipt)
    from datetime import timezone as tz, timedelta
    wib = tz(timedelta(hours=7))
    date_time = order.created_at.astimezone(wib).strftime("%d/%m/%Y %H:%M") if order.created_at else "-"

    # Payment method label human-readable (match WA receipt labels)
    method_label_map = {"cash": "Tunai", "qris": "QRIS", "card": "Kartu", "transfer": "Transfer"}
    payment_method_raw = payment.payment_method if payment else "cash"
    payment_method_label = method_label_map.get(payment_method_raw, payment_method_raw.upper())

    items = [
        {
            # `product_name` udah nyertain varian ("Kopi Susu (Dingin)") —
            # digabung di OrderItem.product_name biar semua pemakai (dapur,
            # split bill, struk WA, dashboard) dapat yang sama.
            "name": item.product_name or (item.product.name if item.product else "Item"),
            "qty": item.quantity,
            "price": float(item.unit_price or 0),
            "notes": item.notes,
        }
        for item in filtered_items
    ]

    if is_subset:
        # Subset totals: re-compute dari filtered items
        subset_subtotal = sum((Decimal(str(it.total_price or 0)) for it in filtered_items), Decimal('0'))
        # Tax/service share proportional
        order_subtotal = Decimal(str(order.subtotal or 0)) or Decimal('1')
        tax_share = (Decimal(str(order.tax_amount or 0)) * subset_subtotal / order_subtotal).quantize(Decimal('0.01')) if order_subtotal > 0 else Decimal('0')
        service_share = (Decimal(str(order.service_charge_amount or 0)) * subset_subtotal / order_subtotal).quantize(Decimal('0.01')) if order_subtotal > 0 else Decimal('0')
        total_val = float(payment.amount_due) if payment else float(subset_subtotal + tax_share + service_share)
        subtotal_val = float(subset_subtotal)
        tax_val = float(tax_share)
        service_val = float(service_share)
        discount_val = 0.0
    else:
        total_val = float(order.total_amount or 0)
        subtotal_val = float(order.subtotal or 0)
        tax_val = float(order.tax_amount or 0)
        service_val = float(order.service_charge_amount or 0)
        discount_val = float(order.discount_amount or 0)

    data = {
        "outlet_name": outlet.name or "Kasira",
        "outlet_address": outlet.address or "",
        "order_number": str(order.display_number),
        "date_time": date_time,
        "items": items,
        "subtotal": subtotal_val,
        "service_charge": service_val,
        "tax": tax_val,
        "discount": discount_val,
        "total": total_val,
        "payment_method": payment_method_label,
        "amount_paid": float(payment.amount_paid or total_val) if payment else total_val,
        "change_amount": float(payment.change_amount or 0) if payment else 0.0,
        "tax_number": tax_cfg.tax_number if tax_cfg else None,
        "custom_footer": tax_cfg.receipt_footer if tax_cfg else None,
        # Ongkir (delivery gelombang 1): di luar total, ditagih terpisah.
        "delivery_fee": float(getattr(order, "delivery_fee", 0) or 0),
        # Link toko di struk cetak (toko bisa ditemukan, 4 Sep 2026). Struk
        # WA udah lama bawa ini; yang kertas belum. Flutter yang nyetak.
        "storefront_url": f"{settings.SITE_URL}/{outlet.slug}" if outlet.slug else None,
        "is_subset": is_subset,
    }

    return StandardResponse(
        success=True,
        data=data,
        request_id=request.state.request_id,
    )
