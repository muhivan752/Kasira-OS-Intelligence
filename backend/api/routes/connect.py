from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from typing import List, Optional
import json
import uuid
from pydantic import BaseModel, Field

from backend.core.database import get_db
from backend.core.config import settings
from backend.models.outlet import Outlet
from backend.models.product import Product
from backend.models.category import Category
from backend.models.order import Order, OrderItem
from backend.schemas.response import StandardResponse
import redis.asyncio as redis
from backend.models.connect import ConnectOutlet, ConnectOrder
from backend.models.customer import Customer
from backend.services.audit import log_audit
from backend.services.stock_service import deduct_stock
from backend.models.event import Event
import datetime

router = APIRouter()

# Redis client
redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)


async def invalidate_storefront_cache(outlet_id: uuid.UUID, db: AsyncSession):
    """Invalidate storefront cache for an outlet. Call when tier/settings change."""
    try:
        result = await db.execute(
            select(Outlet).where(Outlet.id == outlet_id, Outlet.deleted_at.is_(None))
        )
        outlet = result.scalar_one_or_none()
        if outlet and outlet.slug:
            await redis_client.delete(f"connect:storefront:{outlet.slug}")
    except Exception:
        pass


async def invalidate_storefront_cache_by_tenant(tenant_id: uuid.UUID, db: AsyncSession):
    """Invalidate storefront cache for ALL outlets of a tenant."""
    try:
        result = await db.execute(
            select(Outlet).where(Outlet.tenant_id == tenant_id, Outlet.deleted_at.is_(None))
        )
        outlets = result.scalars().all()
        for outlet in outlets:
            if outlet.slug:
                await redis_client.delete(f"connect:storefront:{outlet.slug}")
    except Exception:
        pass

class ConnectOrderItemInput(BaseModel):
    product_id: uuid.UUID
    qty: int = Field(gt=0)
    notes: Optional[str] = None

class ConnectOrderInput(BaseModel):
    items: List[ConnectOrderItemInput]
    customer_name: str
    customer_phone: str
    order_type: str
    delivery_address: Optional[str] = None
    idempotency_key: str
    payment_method: str = 'qris'  # 'qris' atau 'cash'

from backend.services.fonnte import send_whatsapp_message

async def send_wa_confirmation_real(
    phone: str, display_number: str,
    outlet_name: str, customer_name: str
):
    message = (
        f"Pesanan #{display_number} diterima!\n"
        f"Outlet: {outlet_name}\n"
        f"Terima kasih {customer_name}!\n"
        f"Kami segera memproses pesanan Anda."
    )
    await send_whatsapp_message(phone, message)


async def send_wa_booking_confirmation(
    phone: str, booking_id: str, outlet_name: str,
    customer_name: str, reservation_time_str: str, guest_count: int
):
    message = (
        f"Booking meja diterima!\n"
        f"Outlet: {outlet_name}\n"
        f"Nama: {customer_name}\n"
        f"Waktu: {reservation_time_str}\n"
        f"Jumlah tamu: {guest_count} orang\n"
        f"Status: Menunggu konfirmasi outlet.\n"
        f"ID Booking: {booking_id[:8].upper()}"
    )
    await send_whatsapp_message(phone, message)

@router.get("/{slug}", response_model=StandardResponse)
async def get_connect_storefront(slug: str, db: AsyncSession = Depends(get_db)):
    # Check cache
    cache_key = f"connect:storefront:{slug}"
    try:
        cached_data = await redis_client.get(cache_key)
        if cached_data:
            return StandardResponse(success=True, data=json.loads(cached_data), message="Storefront retrieved from cache")
    except Exception as e:
        print(f"Redis error: {e}")

    # Get outlet
    result = await db.execute(
        select(Outlet).where(Outlet.slug == slug, Outlet.deleted_at.is_(None))
    )
    outlet = result.scalar_one_or_none()
    if not outlet:
        raise HTTPException(status_code=404, detail="Outlet tidak ditemukan")

    # Get tenant tier
    from backend.models.tenant import Tenant
    tenant_result = await db.execute(
        select(Tenant).where(Tenant.id == outlet.tenant_id, Tenant.deleted_at.is_(None))
    )
    tenant = tenant_result.scalar_one_or_none()
    raw_tier = getattr(tenant, "subscription_tier", "starter") if tenant else "starter"
    outlet_tier = raw_tier.value if hasattr(raw_tier, 'value') else str(raw_tier or "starter")

    # Check if reservation is enabled
    from backend.models.reservation import ReservationSettings
    resv_settings = (await db.execute(
        select(ReservationSettings).where(ReservationSettings.outlet_id == outlet.id)
    )).scalar_one_or_none()
    reservation_enabled = resv_settings.is_enabled if resv_settings else False

    # Get active products — recipe mode doesn't use stock_qty
    stock_mode = getattr(outlet, 'stock_mode', 'simple')
    stock_mode = stock_mode.value if hasattr(stock_mode, 'value') else str(stock_mode or 'simple')

    if stock_mode == 'recipe':
        # Recipe mode: include all active products, calculate stock from ingredients
        products_result = await db.execute(
            select(Product).where(
                Product.brand_id == outlet.brand_id,
                Product.is_active == True,
                Product.deleted_at.is_(None)
            )
        )
        products = products_result.scalars().all()

        # Calculate available stock from recipe ingredients
        from backend.models.recipe import Recipe, RecipeIngredient
        from backend.models.product import OutletStock
        import math

        recipe_stock_map = {}  # product_id -> available portions
        for p in products:
            recipe_result = await db.execute(
                select(Recipe)
                .options(selectinload(Recipe.ingredients).selectinload(RecipeIngredient.ingredient))
                .where(
                    Recipe.product_id == p.id,
                    Recipe.is_active == True,
                    Recipe.deleted_at.is_(None),
                )
            )
            recipe = recipe_result.scalar_one_or_none()
            if not recipe:
                recipe_stock_map[p.id] = 0
                continue

            active_ingredients = [
                ri for ri in recipe.ingredients
                if ri.deleted_at is None and not ri.is_optional and ri.quantity > 0
                and ri.ingredient is not None and ri.ingredient.deleted_at is None
            ]
            if not active_ingredients:
                recipe_stock_map[p.id] = 0
                continue

            # Get outlet stock for all ingredients
            ingredient_ids = [ri.ingredient_id for ri in active_ingredients]
            stocks_result = await db.execute(
                select(OutletStock).where(
                    OutletStock.outlet_id == outlet.id,
                    OutletStock.ingredient_id.in_(ingredient_ids),
                    OutletStock.deleted_at.is_(None),
                )
            )
            stock_map = {s.ingredient_id: s.computed_stock for s in stocks_result.scalars().all()}

            # Available portions = min(ingredient_stock / qty_per_portion) for all ingredients
            min_portions = float('inf')
            for ri in active_ingredients:
                available = stock_map.get(ri.ingredient_id, 0.0)
                portions = available / ri.quantity
                min_portions = min(min_portions, portions)

            recipe_stock_map[p.id] = max(0, int(math.floor(min_portions))) if min_portions != float('inf') else 0

        # Show ALL active products, mark availability based on stock
        products_with_stock = [
            (p, recipe_stock_map.get(p.id, 0)) for p in products
        ]
    else:
        # Simple mode: show all active products
        products_result = await db.execute(
            select(Product).where(
                Product.brand_id == outlet.brand_id,
                Product.is_active == True,
                Product.deleted_at.is_(None)
            )
        )
        products = products_result.scalars().all()
        products_with_stock = [(p, p.stock_qty) for p in products]

    # Get categories for this brand
    categories_result = await db.execute(
        select(Category).where(
            Category.brand_id == outlet.brand_id,
            Category.deleted_at.is_(None)
        )
    )
    categories = categories_result.scalars().all()

    data = {
        "outlet": {
            "id": str(outlet.id),
            "name": outlet.name,
            "slug": outlet.slug,
            "address": outlet.address,
            "phone": outlet.phone,
            "cover_image_url": outlet.cover_image_url,
            "is_open": outlet.is_open,
            "opening_hours": outlet.opening_hours if isinstance(outlet.opening_hours, str) else "",
            "tier": outlet_tier,
            "trust_badge": "Verified Partner",
            "reservation_enabled": reservation_enabled
        },
        "categories": [
            {"id": str(c.id), "name": c.name} for c in categories
        ],
        "products": [
            {
                "id": str(p.id),
                "name": p.name,
                "description": p.description,
                "price": float(p.base_price),
                "stock": stock,
                "is_available": (not p.stock_enabled) or stock > 0,
                "category_id": str(p.category_id) if p.category_id else None,
                "image_url": p.image_url
            } for p, stock in products_with_stock
        ],
        "menu": [
            {
                "id": str(p.id),
                "name": p.name,
                "price": float(p.base_price),
                "stock": stock,
                "is_available": (not p.stock_enabled) or stock > 0,
                "image_url": p.image_url
            } for p, stock in products_with_stock
        ]
    }

    # Set cache
    try:
        await redis_client.setex(cache_key, 60, json.dumps(data))
    except Exception as e:
        print(f"Redis error: {e}")

    return StandardResponse(success=True, data=data, message="Storefront retrieved")

@router.post("/{slug}/order", response_model=StandardResponse)
async def create_connect_order(
    slug: str, 
    input_data: ConnectOrderInput, 
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    if input_data.order_type not in ["pickup", "delivery", "takeaway", "dine_in"]:
        raise HTTPException(status_code=400, detail="Tipe order tidak valid")
    # Map 'pickup' → 'takeaway' to match DB enum
    db_order_type = "takeaway" if input_data.order_type == "pickup" else input_data.order_type

    if input_data.order_type == "delivery" and not input_data.delivery_address:
        raise HTTPException(status_code=400, detail="Alamat pengiriman wajib diisi")

    # Get outlet
    result = await db.execute(
        select(Outlet).where(Outlet.slug == slug, Outlet.deleted_at.is_(None))
    )
    outlet = result.scalar_one_or_none()
    if not outlet:
        raise HTTPException(status_code=404, detail="Outlet tidak ditemukan")
        
    if not outlet.is_open:
        raise HTTPException(status_code=400, detail="Maaf, outlet sedang tutup")

    # Check idempotency key (scoped ke outlet via connect_outlet)
    result = await db.execute(
        select(ConnectOrder).join(ConnectOutlet).where(
            ConnectOrder.idempotency_key == input_data.idempotency_key,
            ConnectOutlet.outlet_id == outlet.id,
        )
    )
    existing_connect_order = result.scalar_one_or_none()
    if existing_connect_order:
        if existing_connect_order.order_id:
            # Get the order
            order_result = await db.execute(
                select(Order).where(Order.id == existing_connect_order.order_id)
            )
            order = order_result.scalar_one_or_none()
            if order:
                # Get the payment
                from backend.models.payment import Payment
                payment_result = await db.execute(
                    select(Payment).where(Payment.order_id == order.id)
                )
                payment = payment_result.scalar_one_or_none()
                
                raw = (payment.xendit_raw or {}) if payment else {}
                q_url = (payment.qris_url or raw.get("qr_string")) if payment else None
                return StandardResponse(
                    success=True,
                    data={
                        "order_id": str(order.id),
                        "display_number": order.display_number,
                        "status": order.status,
                        "estimated_minutes": 15 if order.order_type == "pickup" else 30,
                        "payment": {
                            "method": payment.payment_method if payment else None,
                            "status": payment.status if payment else None,
                            "qris_url": q_url,
                            "qris_expired_at": None,
                        },
                    },
                    message="Order retrieved from idempotency key"
                )
        raise HTTPException(status_code=400, detail="Idempotency key already used but order not found")

    # Get or create connect_outlet for storefront
    result = await db.execute(
        select(ConnectOutlet).where(
            ConnectOutlet.outlet_id == outlet.id,
            ConnectOutlet.channel == 'other',
            ConnectOutlet.external_store_id == 'storefront'
        )
    )
    connect_outlet = result.scalar_one_or_none()
    if not connect_outlet:
        connect_outlet = ConnectOutlet(
            outlet_id=outlet.id,
            channel='other',
            external_store_id='storefront'
        )
        db.add(connect_outlet)
        await db.flush()

    # Get or create customer
    import hashlib, hmac as _hmac
    phone_hmac = _hmac.new(b'kasira-phone-key', input_data.customer_phone.encode(), hashlib.sha256).hexdigest()
    result = await db.execute(
        select(Customer).where(
            Customer.tenant_id == outlet.tenant_id,
            Customer.phone == input_data.customer_phone
        )
    )
    customer = result.scalar_one_or_none()
    if not customer:
        customer = Customer(
            tenant_id=outlet.tenant_id,
            name=input_data.customer_name,
            phone=input_data.customer_phone,
            phone_hmac=phone_hmac
        )
        db.add(customer)
        await db.flush()

    # Calculate totals and validate stock
    subtotal = 0
    order_items = []
    stock_deductions = []  # (product, qty) — deduct setelah order dibuat (butuh order_id)
    for item_input in input_data.items:
        # Use with_for_update to prevent race conditions on stock
        result = await db.execute(
            select(Product).where(
                Product.id == item_input.product_id,
                Product.deleted_at.is_(None)
            ).with_for_update()
        )
        product = result.scalar_one_or_none()

        if not product or not product.is_active:
            raise HTTPException(status_code=400, detail="Produk tidak tersedia")

        if product.stock_enabled:
            if product.stock_qty < item_input.qty:
                raise HTTPException(status_code=400, detail=f"Stok habis untuk produk {product.name}")
            stock_deductions.append((product, item_input.qty))

        item_total = product.base_price * item_input.qty
        subtotal += item_total

        order_items.append(OrderItem(
            product_id=product.id,
            quantity=item_input.qty,
            unit_price=product.base_price,
            total_price=item_total,
            notes=item_input.notes
        ))

    # Create order
    from sqlalchemy import text
    result = await db.execute(
        text("SELECT nextval('order_display_seq')")
    )
    display_number = result.scalar()

    today = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%d")
    order_number = f"ORD-{today}-{display_number}"

    order = Order(
        outlet_id=outlet.id,
        customer_id=customer.id,
        order_number=order_number,
        display_number=display_number,
        status="pending",
        order_type=db_order_type,
        subtotal=subtotal,
        total_amount=subtotal,
        notes=f"Delivery Address: {input_data.delivery_address}" if input_data.order_type == "delivery" else None
    )
    db.add(order)
    await db.flush()

    # Add items to order
    for item in order_items:
        item.order_id = order.id
        db.add(item)

    # Deduct stock via event-sourced service (Golden Rule #8)
    for product, qty in stock_deductions:
        await deduct_stock(
            db,
            product=product,
            quantity=qty,
            outlet_id=outlet.id,
            order_id=order.id,
            user_id=None,
            tier="starter",
        )

    # Create Payment
    from backend.models.payment import Payment
    from backend.schemas.payment import PaymentMethod, PaymentStatus
    from backend.services.xendit import xendit_service

    pay_method = PaymentMethod.qris if input_data.payment_method == 'qris' else PaymentMethod.cash
    initial_status = PaymentStatus.pending if pay_method == PaymentMethod.qris else PaymentStatus.paid

    payment = Payment(
        order_id=order.id,
        outlet_id=outlet.id,
        payment_method=pay_method,
        amount_due=subtotal,
        amount_paid=subtotal if pay_method == PaymentMethod.cash else 0,
        change_amount=0,
        status=initial_status,
        idempotency_key=input_data.idempotency_key
    )
    db.add(payment)
    await db.flush()

    qris_url = None
    qris_expired_at = None

    if pay_method == PaymentMethod.qris:
        if outlet.xendit_api_key or outlet.xendit_business_id:
            try:
                xendit_res = await xendit_service.create_qris_transaction(
                    reference_id=f"{outlet.tenant_id}::{payment.id}",
                    amount=float(payment.amount_due),
                    for_user_id=outlet.xendit_business_id if not outlet.xendit_api_key else None,
                    platform_fee_percent=0.2,
                    merchant_api_key=outlet.xendit_api_key,
                )
                qris_url = xendit_res.get("qr_string") or xendit_res.get("qr_url")
                payment.qris_url = qris_url
                payment.xendit_raw = xendit_res
                qris_expired_at = (
                    datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(minutes=15)
                ).isoformat()
            except Exception as e:
                payment.status = PaymentStatus.failed
                payment.xendit_raw = {"error": str(e)}
        else:
            # Outlet belum setup Xendit — tandai failed, kasir bisa fallback cash
            payment.status = PaymentStatus.failed
            payment.xendit_raw = {"error": "Outlet belum terhubung Xendit"}
    else:
        # Cash: order langsung masuk preparing
        order.status = "preparing"

    # Create connect order for idempotency
    connect_order = ConnectOrder(
        connect_outlet_id=connect_outlet.id,
        order_id=order.id,
        external_order_id=order_number,
        idempotency_key=input_data.idempotency_key,
        status="pending",
        raw_payload=input_data.model_dump(mode='json')
    )
    db.add(connect_order)

    # Append order.created event (storefront source)
    db.add(Event(
        outlet_id=outlet.id,
        stream_id=f"order:{order.id}",
        event_type="order.created",
        event_data={
            "order_id": str(order.id),
            "outlet_id": str(outlet.id),
            "order_number": order_number,
            "display_number": display_number,
            "order_type": input_data.order_type,
            "total_amount": float(subtotal),
            "item_count": len(order_items),
            "items": [
                {"product_id": str(i.product_id), "qty": i.quantity, "unit_price": float(i.unit_price)}
                for i in order_items
            ],
            "customer_id": str(customer.id),
            "customer_phone": input_data.customer_phone,
            "payment_method": input_data.payment_method,
            "source": "storefront",
        },
        event_metadata={
            "ts": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        },
    ))

    # Append payment event
    pay_event_type = "payment.completed" if payment.status == "paid" else "payment.pending"
    db.add(Event(
        outlet_id=outlet.id,
        stream_id=f"payment:{payment.id}",
        event_type=pay_event_type,
        event_data={
            "payment_id": str(payment.id),
            "order_id": str(order.id),
            "outlet_id": str(outlet.id),
            "method": input_data.payment_method,
            "amount_due": float(subtotal),
            "amount_paid": float(subtotal) if payment.status == "paid" else 0,
            "source": "storefront",
        },
        event_metadata={
            "ts": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        },
    ))

    await db.commit()
    await db.refresh(order)

    # Audit log (Golden Rule #2)
    await log_audit(
        db=db,
        action="CREATE_CONNECT_ORDER",
        entity="order",
        entity_id=str(order.id),
        after_state={
            "display_number": order.display_number,
            "total": float(subtotal),
            "payment_method": input_data.payment_method,
            "customer_phone": input_data.customer_phone,
        },
        user_id=None,
        tenant_id=str(outlet.tenant_id),
    )

    # Send WA confirmation
    background_tasks.add_task(
        send_wa_confirmation_real,
        input_data.customer_phone,
        str(order.display_number),
        outlet.name,
        input_data.customer_name
    )

    return StandardResponse(
        success=True,
        data={
            "order_id": str(order.id),
            "display_number": order.display_number,
            "status": order.status,
            "estimated_minutes": 15 if order.order_type == "pickup" else 30,
            "payment": {
                "method": payment.payment_method,
                "status": payment.status,
                "qris_url": qris_url,
                "qris_expired_at": qris_expired_at,
            },
        },
        message="Order created successfully"
    )

class BookingInput(BaseModel):
    customer_name: str
    customer_phone: str
    reservation_time: str  # ISO 8601 string, e.g. "2026-04-10T19:00:00+07:00"
    guest_count: int = Field(gt=0)
    table_id: Optional[uuid.UUID] = None
    notes: Optional[str] = None


@router.get("/{slug}/tables", response_model=StandardResponse)
async def get_available_tables(slug: str, db: AsyncSession = Depends(get_db)):
    """Meja tersedia untuk booking form di storefront."""
    result = await db.execute(
        select(Outlet).where(Outlet.slug == slug, Outlet.deleted_at.is_(None))
    )
    outlet = result.scalar_one_or_none()
    if not outlet:
        raise HTTPException(status_code=404, detail="Outlet tidak ditemukan")

    from backend.models.reservation import Table
    tables_result = await db.execute(
        select(Table).where(
            Table.outlet_id == outlet.id,
            Table.is_active == True,
            Table.status == 'available',
            Table.deleted_at.is_(None),
        ).order_by(Table.name)
    )
    tables = tables_result.scalars().all()

    return StandardResponse(
        success=True,
        data=[
            {
                "id": str(t.id),
                "name": t.name,
                "capacity": t.capacity,
                "status": t.status,
            }
            for t in tables
        ],
        message="Daftar meja tersedia",
    )


@router.post("/{slug}/booking", response_model=StandardResponse)
async def create_booking(
    slug: str,
    input_data: BookingInput,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """
    Buat booking meja dari storefront (tanpa login).
    Rule #33: reservations WAJIB row_version — double booking via Connect = real problem.
    Golden Rule #24: meja belum di-reserve sampai owner konfirmasi.
    """
    result = await db.execute(
        select(Outlet).where(Outlet.slug == slug, Outlet.deleted_at.is_(None))
    )
    outlet = result.scalar_one_or_none()
    if not outlet:
        raise HTTPException(status_code=404, detail="Outlet tidak ditemukan")

    if not outlet.is_open:
        raise HTTPException(status_code=400, detail="Maaf, outlet sedang tutup")

    # Parse reservation_time — accept ISO 8601 with/without timezone
    import datetime as dt
    try:
        # Python 3.11+ handles Z and +07:00; strip Z for older versions
        reservation_time_str = input_data.reservation_time.replace("Z", "+00:00")
        reservation_dt = dt.datetime.fromisoformat(reservation_time_str)
    except (ValueError, TypeError):
        raise HTTPException(status_code=400, detail="Format waktu tidak valid, gunakan ISO 8601 (contoh: 2026-04-10T19:00:00+07:00)")

    now_utc = dt.datetime.now(dt.timezone.utc)
    if reservation_dt.tzinfo:
        if reservation_dt <= now_utc:
            raise HTTPException(status_code=400, detail="Waktu reservasi harus di masa depan")
    elif reservation_dt <= now_utc.replace(tzinfo=None):
        raise HTTPException(status_code=400, detail="Waktu reservasi harus di masa depan")

    # Get or create customer
    cust_result = await db.execute(
        select(Customer).where(
            Customer.tenant_id == outlet.tenant_id,
            Customer.phone == input_data.customer_phone,
        )
    )
    customer = cust_result.scalar_one_or_none()
    if not customer:
        customer = Customer(
            tenant_id=outlet.tenant_id,
            name=input_data.customer_name,
            phone=input_data.customer_phone,
        )
        db.add(customer)
        await db.flush()

    # Validate table availability (Rule #33 — double booking protection)
    from backend.models.reservation import Reservation, Table
    if input_data.table_id:
        tbl_result = await db.execute(
            select(Table).where(
                Table.id == input_data.table_id,
                Table.outlet_id == outlet.id,
                Table.deleted_at.is_(None),
            ).with_for_update()
        )
        table = tbl_result.scalar_one_or_none()
        if not table:
            raise HTTPException(status_code=404, detail="Meja tidak ditemukan")
        if table.status != "available":
            raise HTTPException(
                status_code=409,
                detail=f"Meja tidak tersedia (status: {table.status}), pilih meja lain",
            )
        if table.capacity < input_data.guest_count:
            raise HTTPException(
                status_code=400,
                detail=f"Kapasitas meja hanya {table.capacity} orang",
            )

    reservation = Reservation(
        outlet_id=outlet.id,
        customer_id=customer.id,
        table_id=input_data.table_id,
        reservation_time=reservation_dt,
        guest_count=input_data.guest_count,
        status="pending",
        notes=input_data.notes,
    )
    db.add(reservation)
    await db.commit()
    await db.refresh(reservation)

    # Fetch table name for response
    table_name = None
    if input_data.table_id:
        tbl_res = await db.execute(select(Table).where(Table.id == input_data.table_id))
        tbl = tbl_res.scalar_one_or_none()
        table_name = tbl.name if tbl else None

    friendly_time = reservation_dt.strftime("%d %b %Y %H:%M")
    background_tasks.add_task(
        send_wa_booking_confirmation,
        input_data.customer_phone,
        str(reservation.id),
        outlet.name,
        input_data.customer_name,
        friendly_time,
        input_data.guest_count,
    )

    return StandardResponse(
        success=True,
        data={
            "booking_id": str(reservation.id),
            "customer_name": input_data.customer_name,
            "reservation_time": reservation_dt.isoformat(),
            "guest_count": input_data.guest_count,
            "table_name": table_name,
            "status": "pending",
        },
        message="Booking berhasil dibuat, menunggu konfirmasi dari outlet",
    )


@router.get("/bookings/{booking_id}", response_model=StandardResponse)
async def get_booking_status(booking_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    """Get booking status (polling dari storefront)."""
    from backend.models.reservation import Reservation, Table
    result = await db.execute(
        select(Reservation).where(
            Reservation.id == booking_id,
            Reservation.deleted_at.is_(None),
        )
    )
    reservation = result.scalar_one_or_none()
    if not reservation:
        raise HTTPException(status_code=404, detail="Booking tidak ditemukan")

    cust_result = await db.execute(select(Customer).where(Customer.id == reservation.customer_id))
    customer = cust_result.scalar_one_or_none()

    table_name = None
    if reservation.table_id:
        tbl_result = await db.execute(select(Table).where(Table.id == reservation.table_id))
        tbl = tbl_result.scalar_one_or_none()
        table_name = tbl.name if tbl else None

    outlet_result = await db.execute(
        select(Outlet).where(Outlet.id == reservation.outlet_id)
    )
    outlet = outlet_result.scalar_one_or_none()

    return StandardResponse(
        success=True,
        data={
            "booking_id": str(reservation.id),
            "customer_name": customer.name if customer else "Guest",
            "customer_phone": customer.phone if customer else None,
            "reservation_time": reservation.reservation_time.isoformat(),
            "guest_count": reservation.guest_count,
            "table_name": table_name,
            "status": reservation.status,
            "notes": reservation.notes,
            "outlet": {
                "name": outlet.name if outlet else "",
                "phone": outlet.phone if outlet else "",
            },
        },
    )


@router.get("/orders/{order_id}", response_model=StandardResponse)
async def get_connect_order_status(order_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Order).options(selectinload(Order.items)).where(Order.id == order_id)
    )
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="Order tidak ditemukan")

    # Load payment info
    from backend.models.payment import Payment
    pay_result = await db.execute(
        select(Payment).where(
            Payment.order_id == order.id,
            Payment.deleted_at.is_(None)
        ).order_by(Payment.created_at.desc()).limit(1)
    )
    payment = pay_result.scalar_one_or_none()

    payment_data = None
    if payment:
        raw = payment.xendit_raw or {}
        q_url = payment.qris_url or raw.get("qr_string") or raw.get("qr_url")
        # Expired at = created_at + 15 menit (fallback kalau tidak tersimpan)
        expired_at = None
        if payment.payment_method == 'qris' and payment.status == 'pending':
            exp = payment.created_at + datetime.timedelta(minutes=15)
            expired_at = exp.isoformat() + "Z"
        payment_data = {
            "method": payment.payment_method,
            "status": payment.status,
            "qris_url": q_url,
            "qris_expired_at": expired_at,
        }

    # Load items with product names
    items_data = []
    for item in (order.items or []):
        prod_result = await db.execute(
            select(Product).where(Product.id == item.product_id)
        )
        prod = prod_result.scalar_one_or_none()
        items_data.append({
            "id": str(item.id),
            "product_name": prod.name if prod else "Produk",
            "quantity": item.quantity,
            "price": float(item.unit_price),
            "subtotal": float(item.total_price),
            "notes": item.notes,
        })

    # Load outlet info for WA contact
    outlet_result = await db.execute(
        select(Outlet).where(Outlet.id == order.outlet_id)
    )
    outlet = outlet_result.scalar_one_or_none()
    outlet_data = {
        "name": outlet.name if outlet else "",
        "phone": outlet.phone if outlet else "",
    } if outlet else {}

    return StandardResponse(
        success=True,
        data={
            "id": str(order.id),
            "order_number": order.order_number,
            "display_number": order.display_number,
            "status": order.status,
            "order_type": order.order_type,
            "total_amount": float(order.total_amount),
            "created_at": order.created_at.isoformat() + "Z",
            "estimated_minutes": 15 if order.order_type == "pickup" else 30,
            "delivery_address": order.notes if order.order_type == "delivery" else None,
            "payment_method": payment.payment_method if payment else None,
            "items": items_data,
            "payment": payment_data,
            "outlet": outlet_data,
        },
        message="Order status retrieved"
    )


# ─── Storefront Reservation Endpoints (Public, no auth) ────────────────────

from backend.models.reservation import Reservation, Table, ReservationSettings
from backend.schemas.reservation import StorefrontReservationCreate


@router.get("/{slug}/reservation/slots")
async def get_available_slots(
    slug: str,
    reservation_date: datetime.date,
    guest_count: int = 2,
    db: AsyncSession = Depends(get_db),
):
    """Public: get available reservation slots for a date."""
    outlet = (await db.execute(
        select(Outlet).where(Outlet.slug == slug, Outlet.deleted_at.is_(None), Outlet.is_active == True)
    )).scalar_one_or_none()
    if not outlet:
        raise HTTPException(status_code=404, detail="Outlet tidak ditemukan")

    settings_row = (await db.execute(
        select(ReservationSettings).where(ReservationSettings.outlet_id == outlet.id)
    )).scalar_one_or_none()

    if not settings_row or not settings_row.is_enabled:
        raise HTTPException(status_code=400, detail="Reservasi tidak tersedia untuk outlet ini")

    # Validate date range
    today = datetime.date.today()
    max_date = today + datetime.timedelta(days=settings_row.max_advance_days)
    min_dt = datetime.datetime.now() + datetime.timedelta(hours=settings_row.min_advance_hours)

    if reservation_date < today:
        raise HTTPException(status_code=400, detail="Tidak bisa reservasi untuk tanggal yang sudah lewat")
    if reservation_date > max_date:
        raise HTTPException(status_code=400, detail=f"Reservasi maksimal {settings_row.max_advance_days} hari ke depan")

    # Generate time slots
    slot_duration = datetime.timedelta(minutes=settings_row.slot_duration_minutes)
    opening = datetime.datetime.combine(reservation_date, settings_row.opening_hour)
    closing = datetime.datetime.combine(reservation_date, settings_row.closing_hour)

    # Count available tables with enough capacity
    total_tables = (await db.execute(
        select(func.count(Table.id)).where(
            Table.outlet_id == outlet.id, Table.deleted_at.is_(None),
            Table.is_active == True, Table.capacity >= guest_count,
        )
    )).scalar() or 0

    slots = []
    current = opening
    while current + slot_duration <= closing:
        slot_start = current.time()
        slot_end = (current + slot_duration).time()

        # Skip slots in the past
        if reservation_date == today and current < min_dt:
            current += datetime.timedelta(minutes=30)  # 30 min increments
            continue

        # Count existing reservations in this slot
        existing = (await db.execute(
            select(func.count(Reservation.id)).where(
                Reservation.outlet_id == outlet.id,
                Reservation.reservation_date == reservation_date,
                Reservation.deleted_at.is_(None),
                Reservation.status.in_(['pending', 'confirmed', 'seated']),
                Reservation.start_time < slot_end,
                Reservation.end_time > slot_start,
            )
        )).scalar() or 0

        remaining = max(0, settings_row.max_reservations_per_slot - existing)

        # Check tables available for this slot
        tables_booked = (await db.execute(
            select(func.count(Reservation.table_id)).where(
                Reservation.outlet_id == outlet.id,
                Reservation.reservation_date == reservation_date,
                Reservation.table_id.isnot(None),
                Reservation.deleted_at.is_(None),
                Reservation.status.in_(['pending', 'confirmed', 'seated']),
                Reservation.start_time < slot_end,
                Reservation.end_time > slot_start,
            )
        )).scalar() or 0

        tables_free = max(0, total_tables - tables_booked)

        slots.append({
            "time": slot_start.strftime("%H:%M"),
            "available": remaining > 0 and tables_free > 0,
            "remaining_capacity": remaining,
            "tables_available": tables_free,
        })

        current += datetime.timedelta(minutes=30)

    return StandardResponse(
        success=True,
        data={"date": reservation_date.isoformat(), "slots": slots},
        message="Available slots retrieved",
    )


@router.post("/{slug}/reservation")
async def create_storefront_reservation(
    slug: str,
    body: StorefrontReservationCreate,
    db: AsyncSession = Depends(get_db),
):
    """Public: customer buat reservasi dari storefront."""
    outlet = (await db.execute(
        select(Outlet).where(Outlet.slug == slug, Outlet.deleted_at.is_(None), Outlet.is_active == True)
    )).scalar_one_or_none()
    if not outlet:
        raise HTTPException(status_code=404, detail="Outlet tidak ditemukan")

    settings_row = (await db.execute(
        select(ReservationSettings).where(ReservationSettings.outlet_id == outlet.id)
    )).scalar_one_or_none()

    if not settings_row or not settings_row.is_enabled:
        raise HTTPException(status_code=400, detail="Reservasi tidak tersedia")

    # Validate date
    today = datetime.date.today()
    max_date = today + datetime.timedelta(days=settings_row.max_advance_days)
    if body.reservation_date < today or body.reservation_date > max_date:
        raise HTTPException(status_code=400, detail="Tanggal reservasi tidak valid")

    # Calculate end_time
    slot_duration = datetime.timedelta(minutes=settings_row.slot_duration_minutes)
    start_dt = datetime.datetime.combine(body.reservation_date, body.start_time)
    end_time = (start_dt + slot_duration).time()

    # Check slot still available
    existing = (await db.execute(
        select(func.count(Reservation.id)).where(
            Reservation.outlet_id == outlet.id,
            Reservation.reservation_date == body.reservation_date,
            Reservation.deleted_at.is_(None),
            Reservation.status.in_(['pending', 'confirmed', 'seated']),
            Reservation.start_time < end_time,
            Reservation.end_time > body.start_time,
        )
    )).scalar() or 0

    if existing >= settings_row.max_reservations_per_slot:
        raise HTTPException(status_code=409, detail="Slot sudah penuh, silakan pilih waktu lain")

    # Auto-assign table
    from backend.api.routes.reservations import _auto_assign_table
    table = await _auto_assign_table(db, outlet.id, body.guest_count,
                                      body.reservation_date, body.start_time, end_time)

    # Determine initial status
    initial_status = "confirmed" if settings_row.auto_confirm else "pending"

    reservation = Reservation(
        outlet_id=outlet.id,
        tenant_id=outlet.tenant_id,
        table_id=table.id if table else None,
        reservation_date=body.reservation_date,
        start_time=body.start_time,
        end_time=end_time,
        guest_count=body.guest_count,
        customer_name=body.customer_name,
        customer_phone=body.customer_phone,
        source='storefront',
        notes=body.notes,
        status=initial_status,
        deposit_amount=settings_row.deposit_amount if settings_row.require_deposit else None,
        confirmed_at=datetime.datetime.now(datetime.timezone.utc) if initial_status == "confirmed" else None,
    )
    db.add(reservation)
    await db.commit()
    await db.refresh(reservation)

    # WA confirmation if auto-confirmed
    if initial_status == "confirmed" and body.customer_phone:
        try:
            from backend.api.routes.reservations import _send_wa_confirmation
            import asyncio
            asyncio.create_task(_send_wa_confirmation(
                body.customer_phone, outlet.name, body.reservation_date, body.start_time, body.guest_count,
            ))
        except Exception:
            pass

    status_msg = "Reservasi dikonfirmasi" if initial_status == "confirmed" else "Reservasi diterima, menunggu konfirmasi"

    return StandardResponse(
        success=True,
        data={
            "id": str(reservation.id),
            "status": initial_status,
            "reservation_date": body.reservation_date.isoformat(),
            "start_time": body.start_time.strftime("%H:%M"),
            "end_time": end_time.strftime("%H:%M"),
            "guest_count": body.guest_count,
            "table_name": table.name if table else "Akan ditentukan",
            "deposit_required": settings_row.require_deposit,
            "deposit_amount": float(settings_row.deposit_amount) if settings_row.require_deposit else None,
        },
        message=status_msg,
    )
