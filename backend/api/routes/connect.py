from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, UploadFile, File, Query
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from typing import List, Optional
import json
import logging
import asyncio
import uuid
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

from backend.core.database import get_db
from backend.utils.phone import mask_phone
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
from backend.services.ingredient_stock_service import deduct_ingredients_for_product
from backend.api.routes.products import compute_recipe_stock
from backend.services.variant_utils import resolve_variant, variant_price
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
    # Varian pilihan pelanggan (Hot/Ice, size). Harga TIDAK pernah dikirim dari
    # sini — dihitung ulang di server dari base_price + price_adjustment.
    # Storefront itu endpoint publik, apa pun yang datang dari klien soal harga
    # harus dianggap usulan, bukan fakta.
    product_variant_id: Optional[uuid.UUID] = None
    qty: int = Field(gt=0)
    notes: Optional[str] = None

class ConnectOrderInput(BaseModel):
    items: List[ConnectOrderItemInput]
    customer_name: str
    customer_phone: str
    order_type: str
    delivery_address: Optional[str] = None
    # Titik dari Google Maps (proxy /geo). Opsional: tanpa kunci Maps, pelanggan ketik alamat saja.
    delivery_lat: Optional[float] = Field(default=None, ge=-90, le=90)
    delivery_lng: Optional[float] = Field(default=None, ge=-180, le=180)
    table_id: Optional[uuid.UUID] = None  # for dine_in — auto-link to open tab
    idempotency_key: str
    payment_method: str = 'qris'  # 'qris' atau 'cash'
    # Catatan pelanggan ("tanpa gula", "titip di satpam"). Dulu dikirim web
    # tapi nggak ada di skema, jadi Pydantic membuangnya diam-diam.
    notes: Optional[str] = Field(default=None, max_length=300)

from backend.services.fonnte import send_whatsapp_message
from backend.services import payment_methods as _pm
from backend.services import geo_service as _geo

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


# ── Rute literal. WAJIB dideklarasikan sebelum "/{slug}..." (gotcha #43). ──

@router.get("/reservations/{reservation_id}", response_model=StandardResponse)
async def get_public_reservation(reservation_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    """Halaman lacak reservasi: status + DP (QR toko/rekening/bukti)."""
    from backend.models.reservation import Reservation, Table
    from backend.services import deposit_service as _dep
    reservation = (await db.execute(
        select(Reservation).where(Reservation.id == reservation_id, Reservation.deleted_at.is_(None))
    )).scalar_one_or_none()
    if not reservation:
        raise HTTPException(status_code=404, detail="Reservasi tidak ditemukan")
    outlet = await db.get(Outlet, reservation.outlet_id)
    table = await db.get(Table, reservation.table_id) if reservation.table_id else None
    dep_payment = await _dep.load_deposit_payment(db, reservation)
    return StandardResponse(success=True, data={
        "id": str(reservation.id),
        "status": reservation.status,
        "reservation_date": reservation.reservation_date.isoformat() if reservation.reservation_date else None,
        "start_time": reservation.start_time.strftime("%H:%M") if reservation.start_time else None,
        "end_time": reservation.end_time.strftime("%H:%M") if reservation.end_time else None,
        "guest_count": reservation.guest_count,
        "customer_name": reservation.customer_name,
        "table_name": table.name if table else None,
        "notes": reservation.notes,
        "created_at": reservation.created_at.isoformat() if reservation.created_at else None,
        "deposit": _dep.deposit_info(dep_payment, outlet, reservation.deposit_amount),
        "deposit_timeout_minutes": _dep.DEPOSIT_TIMEOUT_MINUTES,
        "outlet": {
            "name": outlet.name if outlet else None,
            "slug": outlet.slug if outlet else None,
            "whatsapp": ((outlet.whatsapp_number or "").strip() or None) if outlet else None,
            "address": outlet.address if outlet else None,
        },
    })


@router.post("/payments/{payment_id}/proof", response_model=StandardResponse)
async def upload_payment_proof(payment_id: uuid.UUID, file: UploadFile = File(...), db: AsyncSession = Depends(get_db)):
    """Pelanggan unggah bukti bayar (QRIS statis toko, transfer, DP reservasi).

    Publik, dikunci oleh id pembayaran (UUID acak) dan hanya untuk pembayaran
    manual yang masih pending. Kasir melihat gambarnya di kartu pesanan /
    reservasi sebelum menekan Terima/Konfirmasi. Sistem TIDAK menandai lunas
    dari sini: manusia yang memutuskan.
    """
    import os
    from backend.models.payment import Payment
    from backend.api.routes.media import UPLOAD_DIR, ALLOWED_EXTENSIONS, MAX_SIZE_MB
    payment = (await db.execute(
        select(Payment).where(Payment.id == payment_id, Payment.deleted_at.is_(None)).with_for_update()
    )).scalar_one_or_none()
    if not payment:
        raise HTTPException(status_code=404, detail="Pembayaran tidak ditemukan")
    status = payment.status.value if hasattr(payment.status, "value") else str(payment.status)
    if (payment.channel or "xendit") != "manual":
        raise HTTPException(status_code=400, detail="Pembayaran ini terkonfirmasi otomatis, tidak perlu bukti.")
    if status not in ("pending", "pending_manual_check"):
        raise HTTPException(status_code=400, detail=f"Pembayaran sudah {status}.")
    ext = os.path.splitext(file.filename or "")[1].lower() or ".jpg"
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail="Format gambar tidak didukung. Kirim JPG, PNG, atau WEBP.")
    content = await file.read()
    if len(content) > MAX_SIZE_MB * 1024 * 1024:
        raise HTTPException(status_code=400, detail=f"Ukuran file maksimal {MAX_SIZE_MB} MB")
    if len(content) < 1024:
        raise HTTPException(status_code=400, detail="File terlalu kecil, bukan gambar bukti.")
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    filename = f"proof-{uuid.uuid4()}{ext}"
    with open(os.path.join(UPLOAD_DIR, filename), "wb") as f:
        f.write(content)
    now = datetime.datetime.now(datetime.timezone.utc)
    payment.proof_image_url = f"{settings.SITE_URL}/uploads/{filename}"
    payment.proof_uploaded_at = now
    payment.row_version = (payment.row_version or 0) + 1
    await db.commit()

    # Kabari pemilik + app kasir: ada bukti masuk, saatnya cek.
    from backend.services import online_orders as _oo
    outlet = await db.get(Outlet, payment.outlet_id)
    ref = str(payment.reference_id or "")
    label = "DP reservasi" if ref.startswith("reservation:") else "pesanan online"
    if outlet is not None:
        asyncio.create_task(_oo.wa_owner(outlet, f"Bukti bayar {label} Rp {float(payment.amount_due):,.0f} masuk. Cek di aplikasi kasir lalu konfirmasi.".replace(",", ".")))
        asyncio.create_task(_oo.publish(outlet.id, "payment.proof", {"payment_id": str(payment.id), "order_id": str(payment.order_id) if payment.order_id else None}))
    return StandardResponse(success=True, data={"proof_image_url": payment.proof_image_url, "uploaded_at": now.isoformat()},
                            message="Bukti bayar diterima. Toko akan memeriksanya.")


@router.get("/geo/static")
async def geo_static_map(lat: float = Query(..., ge=-90, le=90), lng: float = Query(..., ge=-180, le=180),
                         zoom: int = 16, w: int = 640, h: int = 320):
    """Pratinjau peta (PNG) lewat proxy supaya kunci Maps nggak ke browser."""
    png = await _geo.static_map_png(lat, lng, zoom=zoom, width=w, height=h)
    if png is None:
        raise HTTPException(status_code=404, detail="Peta tidak tersedia")
    return Response(content=png, media_type="image/png", headers={"Cache-Control": "public, max-age=86400"})


@router.get("/{slug}/geo/autocomplete", response_model=StandardResponse)
async def geo_autocomplete(slug: str, q: str = Query(..., min_length=3, max_length=120), session: Optional[str] = None,
                           db: AsyncSession = Depends(get_db)):
    outlet = (await db.execute(select(Outlet).where(Outlet.slug == slug, Outlet.deleted_at.is_(None)))).scalar_one_or_none()
    if not outlet:
        raise HTTPException(status_code=404, detail="Outlet tidak ditemukan")
    items = await _geo.autocomplete(q, lat=outlet.latitude, lng=outlet.longitude, session=session)
    return StandardResponse(success=True, data=items)


@router.get("/{slug}/geo/place", response_model=StandardResponse)
async def geo_place(slug: str, place_id: Optional[str] = None, lat: Optional[float] = None, lng: Optional[float] = None,
                    session: Optional[str] = None, db: AsyncSession = Depends(get_db)):
    """Detail titik: dari place_id (pilihan autocomplete) atau lat/lng (lokasi HP).
    Sekalian hitung jarak ke toko dan apakah masih dalam radius antar."""
    outlet = (await db.execute(select(Outlet).where(Outlet.slug == slug, Outlet.deleted_at.is_(None)))).scalar_one_or_none()
    if not outlet:
        raise HTTPException(status_code=404, detail="Outlet tidak ditemukan")
    if place_id:
        point = await _geo.place_details(place_id, session=session)
    elif lat is not None and lng is not None:
        point = await _geo.reverse(lat, lng) or {"lat": lat, "lng": lng, "address": ""}
    else:
        raise HTTPException(status_code=400, detail="Kirim place_id atau lat dan lng")
    if point is None:
        raise HTTPException(status_code=404, detail="Alamat tidak ditemukan")
    distance = None
    within = None
    radius = float(outlet.delivery_radius_km or 0)
    if outlet.latitude is not None and outlet.longitude is not None:
        distance = round(_geo.haversine_km(outlet.latitude, outlet.longitude, point["lat"], point["lng"]), 2)
        within = (distance <= radius + 0.3) if radius > 0 else True
    return StandardResponse(success=True, data={**point, "distance_km": distance, "within_radius": within, "radius_km": radius or None})


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

    # Jenis usaha buat JSON-LD di halaman toko (CafeOrCoffeeShop / Restaurant / Store).
    from backend.models.brand import Brand
    _brand = (await db.execute(select(Brand).where(Brand.id == outlet.brand_id))).scalar_one_or_none() if outlet.brand_id else None
    _bt = getattr(_brand, "type", None)
    business_type = _bt.value if hasattr(_bt, "value") else (str(_bt) if _bt else "other")

    # Check if reservation is enabled
    from backend.models.reservation import ReservationSettings
    resv_settings = (await db.execute(
        select(ReservationSettings).where(ReservationSettings.outlet_id == outlet.id)
    )).scalar_one_or_none()
    reservation_enabled = resv_settings.is_enabled if resv_settings else False
    from backend.services import deposit_service as _dep
    _resv_settings = (await db.execute(select(ReservationSettings).where(ReservationSettings.outlet_id == outlet.id))).scalar_one_or_none()
    _resv_deposit_amount = float(_resv_settings.deposit_amount) if _dep.deposit_required(_resv_settings, outlet) else None
    _resv_deposit_methods = _dep.deposit_methods(outlet) if _resv_deposit_amount else []

    # Get active products — recipe mode doesn't use stock_qty
    stock_mode = getattr(outlet, 'stock_mode', 'simple')
    stock_mode = stock_mode.value if hasattr(stock_mode, 'value') else str(stock_mode or 'simple')

    if stock_mode == 'recipe':
        products_result = await db.execute(
            select(Product).where(
                Product.brand_id == outlet.brand_id,
                Product.is_active == True,
                Product.deleted_at.is_(None)
            )
        )
        products = products_result.scalars().all()

        recipe_stock_map = await compute_recipe_stock(db, outlet.id, [p.id for p in products])
        products_with_stock = [(p, recipe_stock_map.get(p.id, 0)) for p in products]
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
            "phone": mask_phone(outlet.phone),
            # Sengaja TIDAK di-mask: ini nomor yang pemilik publikasikan buat pelanggan.
            "whatsapp": (outlet.whatsapp_number or "").strip() or None,
            "cover_image_url": outlet.cover_image_url,
            "is_open": outlet.is_open,
            "online_orders_enabled": bool(getattr(outlet, 'online_orders_enabled', True)),
            "accepting_orders": bool(outlet.is_open and getattr(outlet, 'online_orders_enabled', True)),
            "auto_cancel_minutes": int(getattr(outlet, 'online_auto_cancel_minutes', 10) or 10),
            # Metode bayar yang toko aktifkan + saluran QRIS (xendit | manual).
            # Storefront cuma nawarin yang ada di sini.
            **_pm.public_config(outlet),
            # Peta (services/geo_service.py). maps_enabled = kunci server terpasang.
            "latitude": outlet.latitude,
            "longitude": outlet.longitude,
            "delivery_radius_km": float(outlet.delivery_radius_km) if outlet.delivery_radius_km is not None else None,
            "maps_enabled": _geo.enabled(),
            "opening_hours": outlet.opening_hours if isinstance(outlet.opening_hours, str) else "",
            # Buat JSON-LD + halaman /jelajah. Alamat lengkap udah ada di `address`.
            "business_type": business_type,
            "city": outlet.city,
            "province": outlet.province,
            "tier": outlet_tier,
            "trust_badge": "Verified Partner",
            "reservation_enabled": reservation_enabled,
            # DP reservasi (deposit_service): amount None = toko nggak minta DP,
            # atau minta tapi nggak punya metode non-tunai aktif.
            "reservation_deposit_amount": _resv_deposit_amount,
            "reservation_deposit_methods": _resv_deposit_methods
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
                "image_url": p.image_url,
                # Varian aktif saja — yang lagi dimatikan pemilik (es batu
                # habis) nggak boleh bisa dipesan dari storefront. Harga
                # dikirim SUDAH JADI supaya halaman pelanggan nggak perlu
                # ngitung sendiri dan nggak mungkin beda sama server.
                "variants": [
                    {
                        "id": str(v.id),
                        "name": v.name,
                        "price": float(variant_price(p, v)),
                    }
                    for v in p.variants if v.is_active
                ],
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
    delivery_lat = delivery_lng = delivery_distance_km = None
    if input_data.order_type == "delivery" and input_data.delivery_lat is not None and input_data.delivery_lng is not None:
        delivery_lat, delivery_lng = input_data.delivery_lat, input_data.delivery_lng

    # Get outlet
    result = await db.execute(
        select(Outlet).where(Outlet.slug == slug, Outlet.deleted_at.is_(None))
    )
    outlet = result.scalar_one_or_none()
    if not outlet:
        raise HTTPException(status_code=404, detail="Outlet tidak ditemukan")
        
    if not outlet.is_open:
        raise HTTPException(status_code=400, detail="Toko sedang tutup. Silakan pesan lagi saat toko buka.")
    if not getattr(outlet, 'online_orders_enabled', True):
        raise HTTPException(status_code=400, detail="Toko sedang tidak menerima pesanan online. Silakan hubungi toko lewat WhatsApp.")
    if delivery_lat is not None and outlet.latitude is not None and outlet.longitude is not None:
        delivery_distance_km = round(_geo.haversine_km(outlet.latitude, outlet.longitude, delivery_lat, delivery_lng), 2)
        radius = float(outlet.delivery_radius_km or 0)
        if radius > 0 and delivery_distance_km > radius + 0.3:
            raise HTTPException(status_code=400, detail=(
                f"Alamat Anda {delivery_distance_km:.1f} km dari toko, di luar jangkauan antar ({radius:.0f} km). "
                "Pilih ambil sendiri atau hubungi toko lewat WhatsApp."
            ))

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
                pay_data = {
                    "method": payment.payment_method if payment else "tab",
                    "status": payment.status if payment else "pending_tab",
                    "qris_url": q_url,
                    "qris_expired_at": None,
                } if payment else {
                    "method": "tab",
                    "status": "pending_tab",
                    "qris_url": None,
                    "qris_expired_at": None,
                }
                return StandardResponse(
                    success=True,
                    data={
                        "order_id": str(order.id),
                        "display_number": order.display_number,
                        "status": order.status,
                        "estimated_minutes": order.eta_minutes or (15 if str(getattr(order.order_type, "value", order.order_type)) == "takeaway" else 30),
                        "tab_number": None,
                        "payment": pay_data,
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

    # Fetch stock_mode + tenant tier upfront (dipakai buat pre-check + deduct)
    sm = getattr(outlet, 'stock_mode', 'simple')
    stock_mode = sm.value if hasattr(sm, 'value') else str(sm or 'simple')

    from backend.models.tenant import Tenant
    tenant_obj = (await db.execute(
        select(Tenant).where(Tenant.id == outlet.tenant_id)
    )).scalar_one_or_none()
    raw_tier = getattr(tenant_obj, 'subscription_tier', 'starter') or 'starter'
    outlet_tier = raw_tier.value if hasattr(raw_tier, 'value') else str(raw_tier)

    # Recipe mode: prefetch available portions per product untuk pre-check
    recipe_stock_map = {}
    if stock_mode == 'recipe':
        recipe_stock_map = await compute_recipe_stock(
            db, outlet.id, [it.product_id for it in input_data.items]
        )

    # Calculate totals and validate stock
    subtotal = 0
    order_items = []
    stock_deductions = []  # (product, qty) — deduct setelah order dibuat (butuh order_id)
    item_names = []  # (qty, nama lengkap) buat WA ke pemilik
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
            if stock_mode == 'recipe':
                available = recipe_stock_map.get(product.id, 0)
                if available < item_input.qty:
                    raise HTTPException(status_code=400, detail=f"Stok habis untuk produk {product.name}")
            else:
                if product.stock_qty < item_input.qty:
                    raise HTTPException(status_code=400, detail=f"Stok habis untuk produk {product.name}")
            stock_deductions.append((product, item_input.qty))

        # Varian: wajib divalidasi milik produk ini. Endpoint publik, jadi
        # tanpa cek ini siapa pun bisa pasangin variant_id murah ke produk
        # mahal (atau sebaliknya) lewat request buatan tangan.
        try:
            variant = await resolve_variant(db, product.id, item_input.product_variant_id)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

        unit_price = variant_price(product, variant)
        item_total = unit_price * item_input.qty
        subtotal += item_total

        item_modifiers = {"variant_name": variant.name} if variant is not None else None

        order_items.append(OrderItem(
            product_id=product.id,
            product_variant_id=variant.id if variant is not None else None,
            quantity=item_input.qty,
            unit_price=unit_price,
            total_price=item_total,
            modifiers=item_modifiers,
            notes=item_input.notes
        ))
        item_names.append((item_input.qty, f"{product.name} ({variant.name})" if variant is not None else product.name))

    # Create order
    from sqlalchemy import text
    result = await db.execute(
        text("SELECT nextval('order_display_seq')")
    )
    display_number = result.scalar()

    today = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%d")
    order_number = f"ORD-{today}-{display_number}"

    # Resolve table_id for dine_in orders
    resolved_table_id = None
    if db_order_type == 'dine_in' and input_data.table_id:
        from backend.models.reservation import Table as TableModel
        table_result = await db.execute(
            select(TableModel).where(
                TableModel.id == input_data.table_id,
                TableModel.outlet_id == outlet.id,
                TableModel.is_active == True,
                TableModel.deleted_at.is_(None),
            )
        )
        table_obj = table_result.scalar_one_or_none()
        if table_obj:
            resolved_table_id = table_obj.id

    order = Order(
        outlet_id=outlet.id,
        customer_id=customer.id,
        order_number=order_number,
        display_number=display_number,
        status="pending",
        order_type=db_order_type,
        table_id=resolved_table_id,
        subtotal=subtotal,
        total_amount=subtotal,
        source="storefront",
        delivery_address=input_data.delivery_address if input_data.order_type == "delivery" else None,
        delivery_lat=delivery_lat,
        delivery_lng=delivery_lng,
        delivery_distance_km=delivery_distance_km,
        notes=(input_data.notes or "").strip() or None,
    )
    db.add(order)
    await db.flush()

    # Add items to order
    for item in order_items:
        item.order_id = order.id
        db.add(item)

    # Deduct stock via event-sourced service (Golden Rule #8)
    # Branch by stock_mode — recipe outlet deduct ingredients, bukan product.stock_qty
    for product, qty in stock_deductions:
        if stock_mode == 'recipe':
            await deduct_ingredients_for_product(
                db,
                product_id=product.id,
                quantity=qty,
                outlet_id=outlet.id,
                order_id=order.id,
                user_id=None,
                tier=outlet_tier,
                product_name=product.name,
            )
        else:
            await deduct_stock(
                db,
                product=product,
                quantity=qty,
                outlet_id=outlet.id,
                order_id=order.id,
                user_id=None,
                tier=outlet_tier,
            )

    # Auto-link dine_in order to open tab — PRO ONLY (tabs are Pro feature)
    linked_tab_number = None
    is_pro = outlet_tier.lower() in {'pro', 'business', 'enterprise'}

    if resolved_table_id and is_pro:
        # Nempel ke tab meja yang terbuka, atau BUKA tab baru. Tanpa tab,
        # pesanan meja nggak punya jalur bayar (lihat order_lifecycle).
        from backend.services.order_lifecycle import open_tab_for_storefront_order
        open_tab = await open_tab_for_storefront_order(db, order, outlet, customer_name=input_data.customer_name)
        if open_tab is not None:
            linked_tab_number = open_tab.tab_number

    # Create Payment — SKIP if dine-in linked to tab (tab handles payment)
    from backend.models.payment import Payment
    from backend.schemas.payment import PaymentMethod, PaymentStatus
    from backend.services.xendit import xendit_service

    qris_url = None
    qris_expired_at = None
    payment = None

    # Dine-in Pro = ALWAYS skip payment (bayar nanti via Tab, baik tab sudah ada atau belum)
    dine_in_tab_mode = (db_order_type == 'dine_in' and is_pro and resolved_table_id)

    if dine_in_tab_mode:
        # Bayar nanti lewat tab meja. Status tetap 'pending' sampai kasir
        # mengonfirmasi (accept) — sama seperti pesanan online lainnya.
        pass
    else:
        # Normal flow: create payment immediately
        pay_method = PaymentMethod.qris if input_data.payment_method == 'qris' else PaymentMethod.cash
        if not _pm.is_enabled(outlet, pay_method):
            raise HTTPException(status_code=400, detail=_pm.disabled_error(pay_method)["message"])
        # QRIS statis toko (nggak ada Xendit): pelanggan bayar ke QR milik toko
        # dan kirim bukti lewat WA; kasir menerima pesanan = memastikan uangnya
        # masuk (order_lifecycle.accept_order). Sampai itu status 'pending'.
        pay_channel = _pm.resolve_channel(outlet, pay_method)
        manual_qris = pay_method == PaymentMethod.qris and pay_channel == _pm.CHANNEL_MANUAL
        initial_status = PaymentStatus.pending if pay_method == PaymentMethod.qris else PaymentStatus.paid

        payment = Payment(
            order_id=order.id,
            outlet_id=outlet.id,
            payment_method=pay_method,
            channel=pay_channel,
            amount_due=subtotal,
            amount_paid=subtotal if pay_method == PaymentMethod.cash else 0,
            change_amount=0,
            status=initial_status,
            idempotency_key=input_data.idempotency_key
        )
        db.add(payment)
        await db.flush()

        if pay_method == PaymentMethod.qris and not manual_qris:
            if outlet.xendit_api_key or outlet.xendit_business_id:
                # CRITICAL #12 fail-safe: distinguish permanent (4xx) vs
                # transient (retry exhausted) error.
                from backend.services.xendit import XenditTransientError, XenditPermanentError
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
                except XenditPermanentError as e:
                    logger.error("connect xendit permanent payment=%s: %s", payment.id, e)
                    payment.status = PaymentStatus.failed
                    payment.xendit_raw = {"error": str(e), "error_type": "permanent"}
                except XenditTransientError as e:
                    logger.error(
                        "connect xendit transient retry exhausted payment=%s: %s",
                        payment.id, e,
                    )
                    payment.status = PaymentStatus.pending_manual_check
                    payment.xendit_raw = {
                        "error": str(e),
                        "error_type": "transient_exhausted",
                        "admin_action": "Verify via Xendit dashboard — QRIS mungkin ter-create tapi response drop.",
                    }
                except Exception as e:
                    logger.exception("connect xendit unexpected payment=%s", payment.id)
                    payment.status = PaymentStatus.pending_manual_check
                    payment.xendit_raw = {"error": str(e), "error_type": "unexpected"}
            else:
                payment.status = PaymentStatus.failed
                payment.xendit_raw = {"error": "Outlet belum terhubung Xendit"}
        # Tunai: pembayaran dicatat 'paid' (diterima kasir saat serah terima),
        # tapi ORDER tetap 'pending' sampai toko mengonfirmasi. Dulu langsung
        # 'preparing' tanpa ada yang tahu — pesanan hantu di dapur.

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
            "customer_phone": mask_phone(input_data.customer_phone),
            "payment_method": input_data.payment_method,
            "source": "storefront",
        },
        event_metadata={
            "ts": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        },
    ))

    # Append payment event (skip if dine-in tab — no payment created)
    if payment:
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

    # Kabar ke pelanggan (WA), ke pemilik (WA cadangan), ke app kasir (SSE).
    # QRIS yang belum dibayar: pelanggan dulu; toko dikabari waktu webhook paid.
    from backend.services import online_orders as _oo
    from types import SimpleNamespace
    manual_qris_pending = bool(
        payment is not None and payment.payment_method == 'qris'
        and (payment.channel or 'xendit') == 'manual' and payment.status != 'paid'
    )
    # QRIS manual TIDAK dianggap "menunggu bayar": nggak ada webhook yang
    # bakal ngabarin toko, jadi toko dikabari sekarang seperti tunai.
    awaiting_payment = bool(
        payment is not None and payment.payment_method == 'qris'
        and payment.status != 'paid' and not manual_qris_pending
    )
    background_tasks.add_task(
        _oo.wa_customer, outlet, input_data.customer_phone,
        _oo.msg_received(order, outlet, awaiting_payment=awaiting_payment,
                         auto_cancel_minutes=int(outlet.online_auto_cancel_minutes or 10),
                         manual_qris=manual_qris_pending),
    )
    if not awaiting_payment:
        item_objs = [SimpleNamespace(quantity=q, product_name=n) for q, n in item_names]
        background_tasks.add_task(
            _oo.wa_owner, outlet,
            _oo.msg_owner_new_order(order, outlet, input_data.customer_name, item_objs,
                                    paid=bool(payment is not None and payment.status == 'paid'),
                                    manual_qris=manual_qris_pending),
        )
        background_tasks.add_task(_oo.publish, outlet.id, "order.created", {
            "order_id": str(order.id), "display_number": order.display_number,
            "order_type": db_order_type, "total_amount": float(subtotal),
            "customer_name": input_data.customer_name, "paid": bool(payment is not None and payment.status == 'paid'),
        })

    return StandardResponse(
        success=True,
        data={
            "order_id": str(order.id),
            "display_number": order.display_number,
            "status": order.status,
            "estimated_minutes": order.eta_minutes or (15 if str(getattr(order.order_type, "value", order.order_type)) == "takeaway" else 30),
            "table_id": str(resolved_table_id) if resolved_table_id else None,
            "tab_number": linked_tab_number,
            "payment": {
                "method": payment.payment_method if payment else None,
                "status": payment.status if payment else "tab",
                "channel": payment.channel if payment else None,
                "qris_url": qris_url,
                "qris_expired_at": qris_expired_at,
                "qris_static_image_url": outlet.qris_static_image_url if manual_qris_pending else None,
            } if payment else {
                "method": "tab",
                "status": "pending_tab",
                "qris_url": None,
                "qris_expired_at": None,
            },
        },
        message="Pesanan masuk ke tab meja" if linked_tab_number else "Order created successfully"
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
    """Semua meja aktif di outlet, termasuk status dan info tab aktif."""
    result = await db.execute(
        select(Outlet).where(Outlet.slug == slug, Outlet.deleted_at.is_(None))
    )
    outlet = result.scalar_one_or_none()
    if not outlet:
        raise HTTPException(status_code=404, detail="Outlet tidak ditemukan")

    from backend.models.reservation import Table as TableModel

    # Check tier for tab info
    from backend.models.tenant import Tenant as TenantModel
    t_result = await db.execute(select(TenantModel).where(TenantModel.id == outlet.tenant_id))
    t_obj = t_result.scalar_one_or_none()
    raw_t = getattr(t_obj, 'subscription_tier', 'starter') or 'starter'
    tier_str = raw_t.value if hasattr(raw_t, 'value') else str(raw_t)
    is_pro_outlet = tier_str.lower() in {'pro', 'business', 'enterprise'}

    tables_result = await db.execute(
        select(TableModel).where(
            TableModel.outlet_id == outlet.id,
            TableModel.is_active == True,
            TableModel.deleted_at.is_(None),
        ).order_by(TableModel.name)
    )
    tables = tables_result.scalars().all()

    # Get open tabs for these tables (Pro only)
    open_tabs = {}
    if is_pro_outlet:
        from backend.models.tab import Tab
        table_ids = [t.id for t in tables]
        if table_ids:
            tabs_result = await db.execute(
                select(Tab).where(
                    Tab.table_id.in_(table_ids),
                    Tab.status.in_(['open', 'asking_bill', 'splitting']),
                    Tab.deleted_at.is_(None),
                )
            )
            for tab in tabs_result.scalars().all():
                open_tabs[tab.table_id] = {
                    "tab_id": str(tab.id),
                    "tab_number": tab.tab_number,
                    "status": tab.status,
                    "total_amount": float(tab.total_amount),
                    "guest_count": tab.guest_count,
                }

    return StandardResponse(
        success=True,
        data={
            "tables": [
                {
                    "id": str(t.id),
                    "name": t.name,
                    "capacity": t.capacity,
                    "floor_section": t.floor_section,
                    "status": t.status,
                    "has_open_tab": t.id in open_tabs,
                    "tab": open_tabs.get(t.id),
                }
                for t in tables
            ],
            "is_pro": is_pro_outlet,
        },
        message="Daftar meja",
    )


@router.post("/{slug}/request-bill", response_model=StandardResponse)
async def storefront_request_bill(
    slug: str,
    table_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Customer minta bill dari storefront (public, no auth). Pro only — tabs are Pro feature."""
    result = await db.execute(
        select(Outlet).where(Outlet.slug == slug, Outlet.deleted_at.is_(None))
    )
    outlet = result.scalar_one_or_none()
    if not outlet:
        raise HTTPException(status_code=404, detail="Outlet tidak ditemukan")

    # Tier check — tabs/bill request is Pro only
    from backend.models.tenant import Tenant as TenantCheck
    tc = (await db.execute(select(TenantCheck).where(TenantCheck.id == outlet.tenant_id))).scalar_one_or_none()
    raw = getattr(tc, 'subscription_tier', 'starter') or 'starter'
    tier = raw.value if hasattr(raw, 'value') else str(raw)
    if tier.lower() not in {'pro', 'business', 'enterprise'}:
        raise HTTPException(status_code=403, detail="Fitur ini hanya tersedia untuk paket Pro")

    from backend.models.tab import Tab
    tab_result = await db.execute(
        select(Tab).where(
            Tab.table_id == table_id,
            Tab.outlet_id == outlet.id,
            Tab.status == 'open',
            Tab.deleted_at.is_(None),
        ).order_by(Tab.created_at.desc()).limit(1)
    )
    tab = tab_result.scalar_one_or_none()
    if not tab:
        raise HTTPException(status_code=404, detail="Tidak ada tab aktif untuk meja ini")

    tab.status = 'asking_bill'
    tab.row_version += 1
    await db.commit()

    return StandardResponse(
        success=True,
        data={"tab_id": str(tab.id), "tab_number": tab.tab_number, "status": "asking_bill"},
        message="Bill diminta — kasir akan segera menghampiri",
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
            "customer_phone": mask_phone(customer.phone) if customer else None,
            "reservation_time": reservation.reservation_time.isoformat(),
            "guest_count": reservation.guest_count,
            "table_name": table_name,
            "status": reservation.status,
            "notes": reservation.notes,
            "outlet": {
                "name": outlet.name if outlet else "",
                "phone": mask_phone(outlet.phone) if outlet else "",
            },
        },
    )


def _iso(dt):
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=datetime.timezone.utc)
    return dt.isoformat()


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
    # Dipakai di payment_data (QRIS statis toko) dan outlet_data di bawah.
    outlet = await db.get(Outlet, order.outlet_id)

    payment_data = None
    if payment:
        raw = payment.xendit_raw or {}
        q_url = payment.qris_url or raw.get("qr_string") or raw.get("qr_url")
        # Expired at = created_at + 15 menit (fallback kalau tidak tersimpan)
        expired_at = None
        is_manual = (payment.channel or 'xendit') == 'manual'
        if payment.payment_method == 'qris' and payment.status == 'pending' and not is_manual:
            exp = payment.created_at + datetime.timedelta(minutes=15)
            expired_at = exp.isoformat() + "Z"
        payment_data = {
            "payment_id": str(payment.id),
            "method": payment.payment_method,
            "status": payment.status,
            "channel": payment.channel,
            "proof_image_url": payment.proof_image_url,
            "qris_url": q_url,
            "qris_expired_at": expired_at,
            # QR statis toko buat halaman lacak: pelanggan bayar lalu kirim bukti.
            "qris_static_image_url": outlet.qris_static_image_url if (outlet and is_manual and payment.payment_method == 'qris') else None,
        }

    # Load items with product names
    items_data = []
    for item in (order.items or []):
        prod_result = await db.execute(
            select(Product).where(Product.id == item.product_id)
        )
        prod = prod_result.scalar_one_or_none()
        vname = item.modifiers.get("variant_name") if isinstance(item.modifiers, dict) else None
        base_name = prod.name if prod else "Produk"
        items_data.append({
            "id": str(item.id),
            "product_name": f"{base_name} ({vname})" if vname else base_name,
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
        "name": outlet.name,
        "slug": outlet.slug,
        "phone": mask_phone(outlet.phone),
        # Nomor yang pemilik publikasikan — tombol "Hubungi toko" pakai ini,
        # BUKAN `phone` yang disamarkan (dulu bikin link wa.me mati).
        "whatsapp": (outlet.whatsapp_number or "").strip() or None,
        "auto_cancel_minutes": int(getattr(outlet, 'online_auto_cancel_minutes', 10) or 10),
    } if outlet else {}

    table_name = None
    if order.table_id:
        from backend.models.reservation import Table as _T
        t = await db.get(_T, order.table_id)
        table_name = t.name if t else None

    # Batas konfirmasi yang dijanjikan ke pelanggan: dihitung dari waktu bayar
    # (QRIS) atau waktu pesan (tunai), cuma selama masih menunggu konfirmasi.
    confirm_deadline = None
    if order.status == 'pending' and order.accepted_at is None and outlet is not None:
        limit_min = int(getattr(outlet, 'online_auto_cancel_minutes', 10) or 10)
        if payment is None or payment.payment_method != 'qris' or payment.status == 'paid':
            base = payment.paid_at if (payment is not None and payment.payment_method == 'qris' and payment.paid_at) else order.created_at
            confirm_deadline = (base + datetime.timedelta(minutes=limit_min)).isoformat()

    refund_data = None
    if payment is not None and order.status == 'cancelled':
        from backend.models.payment_refund import PaymentRefund as _PR
        rf = (await db.execute(
            select(_PR).where(_PR.payment_id == payment.id, _PR.deleted_at.is_(None))
            .order_by(_PR.created_at.desc()).limit(1)
        )).scalar_one_or_none()
        if rf is not None:
            refund_data = {"amount": float(rf.amount), "status": rf.status}

    return StandardResponse(
        success=True,
        data={
            "id": str(order.id),
            "order_number": order.order_number,
            "display_number": order.display_number,
            "status": order.status,
            "order_type": order.order_type,
            "total_amount": float(order.total_amount),
            "created_at": _iso(order.created_at),
            "estimated_minutes": order.eta_minutes or (15 if order.order_type == "takeaway" else 30),
            "eta_minutes": order.eta_minutes,
            "accepted_at": _iso(order.accepted_at),
            "ready_at": _iso(order.ready_at),
            "updated_at": _iso(order.updated_at),
            "cancel_reason": order.cancel_reason,
            "confirm_deadline": confirm_deadline,
            "source": order.source,
            "customer_name": order.customer_name,
            "notes": order.notes,
            "table_name": table_name,
            "delivery_address": order.delivery_address,
            "delivery_lat": order.delivery_lat,
            "delivery_lng": order.delivery_lng,
            "delivery_distance_km": float(order.delivery_distance_km) if order.delivery_distance_km is not None else None,
            "payment_method": payment.payment_method if payment else None,
            "items": items_data,
            "payment": payment_data,
            "refund": refund_data,
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

    # Determine initial status. DP wajib = selalu pending sampai DP diterima
    # dan kasir konfirmasi, apa pun auto_confirm.
    from backend.services import deposit_service as _dep
    needs_deposit = _dep.deposit_required(settings_row, outlet)
    initial_status = "confirmed" if (settings_row.auto_confirm and not needs_deposit) else "pending"

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
        deposit_amount=settings_row.deposit_amount if needs_deposit else None,
        confirmed_at=datetime.datetime.now(datetime.timezone.utc) if initial_status == "confirmed" else None,
    )
    db.add(reservation)
    await db.flush()

    dep_payment = None
    if needs_deposit:
        dep_payment = await _dep.create_deposit_payment(db, outlet, reservation, method=body.payment_method, tenant_id=outlet.tenant_id)
    await db.commit()
    await db.refresh(reservation)
    deposit = _dep.deposit_info(dep_payment, outlet, reservation.deposit_amount)
    track_url = f"{settings.SITE_URL}/{outlet.slug}/reservation/{reservation.id}"

    # Kabar: pelanggan selalu (DP = instruksi bayar), pemilik untuk yang butuh
    # tindakan (pending). Lewat pintu yang sama dengan pesanan online.
    from backend.services import online_orders as _oo
    if body.customer_phone:
        asyncio.create_task(_oo.wa_customer(
            outlet, body.customer_phone,
            _oo.msg_customer_reservation(reservation, outlet, deposit=deposit, track=track_url),
        ))
    if initial_status == "pending":
        asyncio.create_task(_oo.wa_owner(outlet, _oo.msg_owner_new_reservation(reservation, outlet, deposit=deposit)))
        asyncio.create_task(_oo.publish(outlet.id, "reservation.created", {"reservation_id": str(reservation.id)}))

    status_msg = (
        "Reservasi dikonfirmasi" if initial_status == "confirmed"
        else ("Reservasi diterima, bayar DP untuk mengamankan meja" if needs_deposit else "Reservasi diterima, menunggu konfirmasi")
    )

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
            "deposit_required": needs_deposit,
            "deposit_amount": float(settings_row.deposit_amount) if needs_deposit else None,
            "deposit": deposit,
            "track_url": track_url,
        },
        message=status_msg,
    )
