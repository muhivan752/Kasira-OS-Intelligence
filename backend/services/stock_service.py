"""
Kasira Stock Service — Event-Sourced, Tier-Aware

Starter: source of truth = transaksi
  - products.stock_qty = denormalized cache
  - events table = append-only event log (stock.sale, stock.restock)
  - Replay events → recompute stock kapanpun dibutuhkan

Pro (future): same + outlet_stock CRDT untuk offline sync multi-device

Golden Rules yang dipakai:
  #8  — event store append-only, TIDAK BOLEH update/delete
  #19 — Starter: transaction-first, restock manual hanya saat terima barang
  #20 — Stok = 0 → auto-hidden di kasir DAN storefront
  #28 — order_display_number dari PostgreSQL SEQUENCE (sudah di orders.py)
  #29 — row_version wajib di products
  #30 — optimistic lock WHERE row_version = :expected
  #47 — CHECK (stock_qty >= 0) di DB level
"""

import logging
from typing import Optional
from uuid import UUID
from datetime import datetime, timezone

from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.product import Product
from backend.models.event import Event

logger = logging.getLogger(__name__)

PRO_TIERS = {"pro", "business", "enterprise"}


async def _is_sale_already_recorded(db: AsyncSession, product_id: UUID, order_id: UUID) -> bool:
    """Idempotency check — cegah double deduct kalau order sync dua kali."""
    result = await db.execute(
        select(Event).where(
            Event.stream_id == f"product:{product_id}",
            Event.event_type == "stock.sale",
            Event.event_data["order_id"].astext == str(order_id),
        ).limit(1)
    )
    return result.scalar_one_or_none() is not None


async def deduct_stock(
    db: AsyncSession,
    *,
    product: Product,
    quantity: int,
    outlet_id: UUID,
    order_id: UUID,
    user_id: Optional[UUID],
    tier: str = "starter",
) -> Product:
    """
    Deduct stock dari transaksi (sale event).
    - Tulis event stock.sale ke events table (append-only)
    - Update products.stock_qty cache dengan optimistic lock
    - Auto-hide produk jika stok = 0

    Raises HTTPException 400 jika stok tidak cukup.
    Raises HTTPException 409 jika optimistic lock conflict.
    """
    from fastapi import HTTPException

    if not product.stock_enabled:
        return product

    # Idempotency: skip kalau stock.sale untuk order ini sudah ada (offline sync ulang)
    if await _is_sale_already_recorded(db, product.id, order_id):
        logger.info(f"stock.sale already recorded for order {order_id}, skipping deduct")
        return product

    if product.stock_qty < quantity:
        raise HTTPException(
            status_code=400,
            detail={
                "code": "STOCK_INSUFFICIENT",
                "mode": "simple",
                "message": f"Stok {product.name} tidak mencukupi. Tersedia: {product.stock_qty}",
                "items": [{
                    "name": product.name,
                    "product_name": product.name,
                    "available": product.stock_qty,
                    "needed": quantity,
                    "unit": "pcs",
                }],
            },
        )

    stock_before = product.stock_qty
    stock_after = stock_before - quantity
    is_active = product.is_active

    if stock_after <= 0 and product.stock_auto_hide:
        is_active = False

    # 1. Append event ke event store (source of truth)
    event = Event(
        outlet_id=outlet_id,
        stream_id=f"product:{product.id}",
        event_type="stock.sale",
        event_data={
            "product_id": str(product.id),
            "outlet_id": str(outlet_id),
            "quantity": quantity,
            "stock_before": stock_before,
            "stock_after": stock_after,
            "order_id": str(order_id),
        },
        event_metadata={
            "tier": tier,
            "user_id": str(user_id) if user_id else None,
            "ts": datetime.now(timezone.utc).isoformat(),
        },
    )
    db.add(event)

    # 2. Update cache dengan optimistic lock — Rule #30: retry max 3x → baru error
    for attempt in range(3):
        # Re-fetch product untuk dapat row_version terbaru saat retry
        if attempt > 0:
            refreshed = await db.get(Product, product.id)
            if not refreshed or refreshed.stock_qty < quantity:
                raise HTTPException(
                    status_code=400,
                    detail={
                        "code": "STOCK_INSUFFICIENT",
                        "mode": "simple",
                        "message": f"Stok {product.name} tidak mencukupi",
                        "items": [{
                            "name": product.name,
                            "product_name": product.name,
                            "available": refreshed.stock_qty if refreshed else 0,
                            "needed": quantity,
                            "unit": "pcs",
                        }],
                    },
                )
            stock_before = refreshed.stock_qty
            stock_after = stock_before - quantity
            is_active = True if stock_after > 0 else (refreshed.is_active and not refreshed.stock_auto_hide)
            current_version = refreshed.row_version
        else:
            current_version = product.row_version

        try:
            result = await db.execute(
                update(Product)
                .where(Product.id == product.id, Product.row_version == current_version)
                .values(
                    stock_qty=stock_after,
                    is_active=is_active,
                    sold_today=Product.sold_today + quantity,
                    sold_total=Product.sold_total + quantity,
                    row_version=Product.row_version + 1,
                )
                .returning(Product)
            )
            updated = result.scalar_one_or_none()
            if updated is not None:
                # Invalidate storefront cache saat stok berubah
                try:
                    from backend.core.config import settings
                    import redis.asyncio as _redis
                    _r = _redis.from_url(settings.REDIS_URL, decode_responses=True)
                    # Get outlet slug for cache key
                    from backend.models.outlet import Outlet
                    from backend.models.brand import Brand
                    brand = await db.get(Brand, updated.brand_id)
                    if brand:
                        outlet_res = await db.execute(
                            select(Outlet).where(Outlet.brand_id == brand.id, Outlet.deleted_at.is_(None)).limit(1)
                        )
                        outlet = outlet_res.scalar_one_or_none()
                        if outlet and outlet.slug:
                            await _r.delete(f"connect:storefront:{outlet.slug}")
                        if outlet:
                            await _r.delete(f"ai:context:{outlet.id}")
                    await _r.aclose()
                except Exception:
                    pass  # Cache invalidation failure is non-critical
                return updated
        except IntegrityError:
            # CHECK (stock_qty >= 0) violated — race condition
            await db.rollback()
            raise HTTPException(
                status_code=400,
                detail={
                    "code": "STOCK_RACE_CONDITION",
                    "mode": "simple",
                    "message": f"Stok {product.name} baru saja terjual. Silakan cek ulang stok.",
                    "items": [{
                        "name": product.name,
                        "product_name": product.name,
                        "available": 0,
                        "needed": quantity,
                        "unit": "pcs",
                    }],
                },
            )

    raise HTTPException(status_code=409, detail="Konflik data produk setelah 3x retry, silakan coba lagi")


async def restore_stock_on_cancel(
    db: AsyncSession,
    *,
    product: Product,
    quantity: int,
    outlet_id: UUID,
    order_id: UUID,
    tier: str = "starter",
) -> Product:
    """
    Kembalikan stok saat order dibatalkan.
    - Tulis event stock.cancel_return ke events table
    - Update products.stock_qty cache
    - Re-aktifkan produk jika sebelumnya auto-hidden karena stok 0
    """
    from fastapi import HTTPException

    stock_before = product.stock_qty
    stock_after = stock_before + quantity

    is_active = True if stock_before == 0 and product.stock_auto_hide else product.is_active

    event = Event(
        outlet_id=outlet_id,
        stream_id=f"product:{product.id}",
        event_type="stock.cancel_return",
        event_data={
            "product_id": str(product.id),
            "outlet_id": str(outlet_id),
            "quantity": quantity,
            "stock_before": stock_before,
            "stock_after": stock_after,
            "order_id": str(order_id),
        },
        event_metadata={
            "tier": tier,
            "ts": datetime.now(timezone.utc).isoformat(),
        },
    )
    db.add(event)

    for attempt in range(3):
        if attempt > 0:
            refreshed = await db.get(Product, product.id)
            if not refreshed:
                raise HTTPException(status_code=404, detail="Produk tidak ditemukan")
            stock_before = refreshed.stock_qty
            stock_after = stock_before + quantity
            is_active = True if stock_before == 0 and refreshed.stock_auto_hide else refreshed.is_active
            current_version = refreshed.row_version
        else:
            current_version = product.row_version

        result = await db.execute(
            update(Product)
            .where(Product.id == product.id, Product.row_version == current_version)
            .values(
                stock_qty=stock_after,
                is_active=is_active,
                row_version=Product.row_version + 1,
            )
            .returning(Product)
        )
        updated = result.scalar_one_or_none()
        if updated is not None:
            try:
                from backend.core.config import settings
                import redis.asyncio as _redis
                _r = _redis.from_url(settings.REDIS_URL, decode_responses=True)
                from backend.models.outlet import Outlet
                from backend.models.brand import Brand
                brand = await db.get(Brand, updated.brand_id)
                if brand:
                    outlet_res = await db.execute(
                        select(Outlet).where(Outlet.brand_id == brand.id, Outlet.deleted_at.is_(None)).limit(1)
                    )
                    outlet = outlet_res.scalar_one_or_none()
                    if outlet and outlet.slug:
                        await _r.delete(f"connect:storefront:{outlet.slug}")
                    if outlet:
                        await _r.delete(f"ai:context:{outlet.id}")
                await _r.aclose()
            except Exception:
                pass
            return updated

    raise HTTPException(status_code=409, detail="Konflik data produk setelah 3x retry, silakan coba lagi")


async def restock_product(
    db: AsyncSession,
    *,
    product: Product,
    quantity: int,
    outlet_id: UUID,
    user_id: Optional[UUID],
    notes: Optional[str] = None,
    tier: str = "starter",
) -> Product:
    """
    Tambah stok saat terima barang (restock event).
    Starter: hanya bisa restock saat terima barang — bukan input harian bebas (Rule #19).

    - Tulis event stock.restock ke events table
    - Update products.stock_qty cache
    - Auto-show produk jika sebelumnya hidden karena stok 0
    """
    from fastapi import HTTPException

    stock_before = product.stock_qty
    stock_after = stock_before + quantity

    # Re-aktifkan produk jika sebelumnya auto-hidden karena stok 0
    is_active = True if stock_before == 0 and product.stock_auto_hide else product.is_active

    # 1. Append event
    event = Event(
        outlet_id=outlet_id,
        stream_id=f"product:{product.id}",
        event_type="stock.restock",
        event_data={
            "product_id": str(product.id),
            "outlet_id": str(outlet_id),
            "quantity": quantity,
            "stock_before": stock_before,
            "stock_after": stock_after,
            "notes": notes,
        },
        event_metadata={
            "tier": tier,
            "user_id": str(user_id) if user_id else None,
            "ts": datetime.now(timezone.utc).isoformat(),
        },
    )
    db.add(event)

    # 2. Update cache dengan optimistic lock — Rule #30: retry max 3x → baru error
    for attempt in range(3):
        if attempt > 0:
            refreshed = await db.get(Product, product.id)
            if not refreshed:
                raise HTTPException(status_code=404, detail="Produk tidak ditemukan")
            stock_before = refreshed.stock_qty
            stock_after = stock_before + quantity
            is_active = True if stock_before == 0 and refreshed.stock_auto_hide else refreshed.is_active
            current_version = refreshed.row_version
        else:
            current_version = product.row_version

        result = await db.execute(
            update(Product)
            .where(Product.id == product.id, Product.row_version == current_version)
            .values(
                stock_qty=stock_after,
                is_active=is_active,
                last_restock_at=datetime.now(timezone.utc),
                row_version=Product.row_version + 1,
            )
            .returning(Product)
        )
        updated = result.scalar_one_or_none()
        if updated is not None:
            # Invalidate AI context cache
            try:
                from backend.core.config import settings
                import redis.asyncio as _redis
                _r = _redis.from_url(settings.REDIS_URL, decode_responses=True)
                await _r.delete(f"ai:context:{outlet_id}")
                await _r.aclose()
            except Exception:
                pass
            return updated

    raise HTTPException(status_code=409, detail="Konflik data produk setelah 3x retry, silakan coba lagi")


async def get_stock_history(
    db: AsyncSession,
    *,
    product_id: UUID,
    outlet_id: UUID,
    limit: int = 50,
) -> list:
    """Ambil riwayat stock events dari event store untuk satu produk."""
    result = await db.execute(
        select(Event)
        .where(
            Event.stream_id == f"product:{product_id}",
            Event.outlet_id == outlet_id,
            Event.event_type.in_(["stock.sale", "stock.restock", "stock.adjustment", "stock.waste", "stock.cancel_return"]),
        )
        .order_by(Event.created_at.desc())
        .limit(limit)
    )
    return result.scalars().all()


async def recompute_stock_from_events(
    db: AsyncSession,
    *,
    product_id: UUID,
    outlet_id: UUID,
) -> int:
    """
    Recompute stock dari event store — untuk audit/reconciliation.
    Source of truth = events, bukan products.stock_qty.
    """
    result = await db.execute(
        select(Event)
        .where(
            Event.stream_id == f"product:{product_id}",
            Event.outlet_id == outlet_id,
            Event.event_type.in_(["stock.sale", "stock.restock", "stock.adjustment", "stock.waste", "stock.cancel_return"]),
        )
        .order_by(Event.created_at.asc())
    )
    events = result.scalars().all()

    stock = 0
    for event in events:
        data = event.event_data or {}
        if event.event_type in ("stock.restock", "stock.cancel_return"):
            stock += data.get("quantity", 0)
        elif event.event_type in ("stock.sale", "stock.waste"):
            stock -= data.get("quantity", 0)
        elif event.event_type == "stock.adjustment":
            # adjustment menyimpan stock_after langsung
            stock = data.get("stock_after", stock)

    return max(stock, 0)
