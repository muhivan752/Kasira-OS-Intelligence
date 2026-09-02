"""
Nota belanja → stok + HPP + histori harga + utang, dalam satu transaksi.

Ini titik input manusia pertama di "ERP yang ngisi sendiri": pemilik cuma
nyatet nota (atau foto → OCR), sisanya turunan:

  * baris BAHAN  → outlet_stock naik (lewat helper restock yang sama dengan
                   POST /ingredients/{id}/restock), cost_per_base_unit jadi
                   RATA-RATA BERGERAK, ingredient_suppliers + price_history
                   keisi, jadi pricing coach / menu engineering / KG langsung
                   baca HPP yang segar.
  * baris PRODUK → products.stock_qty naik lewat stock_service.restock_product
                   (tenant Starter non-F&B beli produk jadi), buy_price jadi
                   rata-rata bergerak juga.
  * total − paid → utang supplier, due_at dari payment_terms supplier.
  * event `purchase.received` di stream purchase:{id} buat projector ledger
    (gelombang 2) dan AI.

Tidak commit — route yang commit (pola sama kayak stock_service).
"""
import logging
from datetime import datetime, timezone, timedelta
from decimal import Decimal, ROUND_HALF_UP
from typing import Optional
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.models.brand import Brand
from backend.models.event import Event
from backend.models.ingredient import Ingredient
from backend.models.outlet import Outlet
from backend.models.product import Product, OutletStock
from backend.models.purchasing import (
    Supplier, IngredientSupplier, PurchaseOrder, PurchaseOrderItem, SupplierPriceHistory,
)
from backend.services.ingredient_stock_service import restock_ingredient_stock
from backend.services.stock_service import restock_product
from backend.services.unit_utils import UNIT_ALIASES

logger = logging.getLogger(__name__)

_Q2 = Decimal("0.01")


def _q2(x) -> Decimal:
    return Decimal(str(x)).quantize(_Q2, rounding=ROUND_HALF_UP)


def qty_to_base_unit(qty: float, unit: Optional[str], base_unit: str) -> Optional[float]:
    """
    "2 kg" buat bahan ber-base_unit gram → 2000. None kalau satuan nggak
    bisa dipetakan ke keluarga base_unit (kg → ml). Pakai tabel alias yang
    sama dengan HPP compute (gotcha #11) — jangan bikin tabel konversi kedua.
    """
    base = (base_unit or "").lower().strip()
    u = (unit or "").lower().strip()
    if not u or u == base:
        return float(qty)
    alias = UNIT_ALIASES.get(u)
    if alias is None:
        return None
    mapped_base, multiplier = alias
    if mapped_base != base:
        return None
    return float(qty) * multiplier


def moving_average(old_qty: float, old_cost: Decimal, add_qty: float, add_cost: Decimal) -> Decimal:
    """
    Rata-rata tertimbang antara stok lama dan barang baru. Kalau stok lama
    nol atau cost lama belum pernah diisi, harga baru yang dipakai apa
    adanya — jangan ngerata-ratain sama angka nol.
    """
    old_qty = max(float(old_qty or 0), 0.0)
    old_cost = Decimal(str(old_cost or 0))
    add_cost = Decimal(str(add_cost or 0))
    if old_qty <= 0 or old_cost <= 0:
        return _q2(add_cost)
    total_qty = Decimal(str(old_qty)) + Decimal(str(add_qty))
    if total_qty <= 0:
        return _q2(add_cost)
    return _q2((Decimal(str(old_qty)) * old_cost + Decimal(str(add_qty)) * add_cost) / total_qty)


async def _brand_ids_for_tenant(db: AsyncSession, tenant_id: UUID) -> list[UUID]:
    rows = (await db.execute(
        select(Brand.id).where(Brand.tenant_id == tenant_id, Brand.deleted_at.is_(None))
    )).scalars().all()
    return list(rows)


async def next_po_number(db: AsyncSession, outlet_id: UUID, when: datetime) -> str:
    """NB-20260902-003 — urut per outlet per hari. Unique index (outlet_id, po_number)."""
    day = when.astimezone(timezone(timedelta(hours=7))).strftime("%Y%m%d")
    prefix = f"NB-{day}-"
    count = (await db.execute(
        select(func.count(PurchaseOrder.id)).where(
            PurchaseOrder.outlet_id == outlet_id,
            PurchaseOrder.po_number.like(f"{prefix}%"),
        )
    )).scalar() or 0
    return f"{prefix}{count + 1:03d}"


async def resolve_supplier(
    db: AsyncSession, *, tenant_id: UUID, supplier_id: Optional[UUID], supplier_name: Optional[str],
) -> Optional[Supplier]:
    """supplier_id → harus milik tenant. Nama doang → cari (case-insensitive) atau bikin."""
    if supplier_id:
        sup = (await db.execute(
            select(Supplier).where(
                Supplier.id == supplier_id,
                Supplier.tenant_id == tenant_id,
                Supplier.deleted_at.is_(None),
            )
        )).scalar_one_or_none()
        if not sup:
            raise HTTPException(status_code=404, detail="Supplier tidak ditemukan")
        return sup
    name = (supplier_name or "").strip()
    if not name:
        return None
    sup = (await db.execute(
        select(Supplier).where(
            Supplier.tenant_id == tenant_id,
            Supplier.deleted_at.is_(None),
            func.lower(Supplier.name) == name.lower(),
        )
    )).scalar_one_or_none()
    if sup:
        return sup
    sup = Supplier(tenant_id=tenant_id, name=name)
    db.add(sup)
    await db.flush()
    return sup


async def receive_purchase(
    db: AsyncSession,
    *,
    tenant_id: UUID,
    tier: str,
    is_pro: bool,
    outlet_id: UUID,
    supplier: Optional[Supplier],
    lines: list,
    invoice_no: Optional[str],
    photo_url: Optional[str],
    notes: Optional[str],
    received_at: Optional[datetime],
    paid_amount: Optional[Decimal],
    due_at: Optional[datetime],
    user_id: UUID,
) -> tuple[PurchaseOrder, list[dict]]:
    """
    Bikin nota berstatus `received` + semua efek sampingnya. Return
    (purchase_order, line_effects) — line_effects nyimpen cost_before/after
    per baris buat ditampilin di UI.
    """
    outlet = (await db.execute(
        select(Outlet).where(Outlet.id == outlet_id, Outlet.deleted_at.is_(None))
    )).scalar_one_or_none()
    if not outlet or outlet.tenant_id != tenant_id:
        raise HTTPException(status_code=404, detail="Outlet tidak ditemukan")

    brand_ids = await _brand_ids_for_tenant(db, tenant_id)
    now = datetime.now(timezone.utc)
    received_at = received_at or now

    po = PurchaseOrder(
        outlet_id=outlet_id,
        supplier_id=supplier.id if supplier else None,
        po_number=await next_po_number(db, outlet_id, received_at),
        status='received',
        received_at=received_at,
        invoice_no=(invoice_no or None),
        photo_url=photo_url,
        notes=notes,
        created_by=user_id,
        received_by=user_id,
        total_amount=Decimal("0"),
        paid_amount=Decimal("0"),
    )
    db.add(po)
    await db.flush()  # butuh po.id buat FK item + payload event

    total = Decimal("0")
    effects: list[dict] = []
    event_lines: list[dict] = []

    for line in lines:
        qty = float(line.quantity)
        unit_price = _q2(line.unit_price)
        line_total = _q2(line.total_price) if line.total_price is not None else _q2(Decimal(str(qty)) * unit_price)
        total += line_total

        if line.ingredient_id:
            if not is_pro:
                raise HTTPException(
                    status_code=403,
                    detail="Bahan baku & resep itu fitur Pro. Di paket Starter, catat nota untuk produk jadi.",
                )
            ing = (await db.execute(
                select(Ingredient).where(
                    Ingredient.id == line.ingredient_id,
                    Ingredient.brand_id.in_(brand_ids),
                    Ingredient.deleted_at.is_(None),
                )
            )).scalar_one_or_none()
            if not ing:
                raise HTTPException(status_code=404, detail="Bahan baku tidak ditemukan")

            qty_base = qty_to_base_unit(qty, line.unit, ing.base_unit)
            if qty_base is None or qty_base <= 0:
                raise HTTPException(
                    status_code=400,
                    detail=f"Satuan '{line.unit}' tidak bisa dikonversi ke {ing.base_unit} untuk {ing.name}",
                )
            cost_per_base_new = _q2(line_total / Decimal(str(qty_base)))

            # Stok sebelum restock = basis rata-rata bergerak.
            stock_before, _ = await restock_ingredient_stock(
                db,
                ingredient_id=ing.id,
                outlet_id=outlet_id,
                quantity=qty_base,
                user_id=user_id,
                notes=f"Nota {po.po_number}" + (f" · {supplier.name}" if supplier else ""),
                source={"purchase_id": str(po.id), "supplier_id": str(supplier.id) if supplier else None},
            )
            cost_before = _q2(ing.cost_per_base_unit or 0)
            cost_after = moving_average(stock_before, cost_before, qty_base, cost_per_base_new)

            # buy_price/buy_qty = "terakhir beli": Rp line_total buat qty_base base_unit.
            ing.buy_price = line_total
            ing.buy_qty = qty_base
            ing.cost_per_base_unit = cost_after
            ing.row_version = (ing.row_version or 0) + 1

            if supplier:
                await _touch_ingredient_supplier(
                    db, ingredient=ing, supplier=supplier,
                    price_per_base=cost_per_base_new, when=received_at, user_id=user_id,
                )

            db.add(PurchaseOrderItem(
                purchase_order_id=po.id,
                ingredient_id=ing.id,
                name_snapshot=ing.name,
                quantity=qty,
                unit=(line.unit or ing.base_unit),
                qty_base=qty_base,
                unit_price=unit_price,
                total_price=line_total,
                received_quantity=qty,
            ))
            effects.append({
                "name": ing.name, "cost_before": cost_before, "cost_after": cost_after,
                "unit": ing.base_unit,
            })
            event_lines.append({
                "ingredient_id": str(ing.id), "name": ing.name, "qty_base": qty_base,
                "base_unit": ing.base_unit, "total": str(line_total),
                "cost_before": str(cost_before), "cost_after": str(cost_after),
            })

        else:
            prod = (await db.execute(
                select(Product).where(
                    Product.id == line.product_id,
                    Product.brand_id.in_(brand_ids),
                    Product.deleted_at.is_(None),
                )
            )).scalar_one_or_none()
            if not prod:
                raise HTTPException(status_code=404, detail="Produk tidak ditemukan")
            if qty != int(qty):
                raise HTTPException(status_code=400, detail=f"Jumlah produk {prod.name} harus bilangan bulat")

            cost_before = _q2(prod.buy_price or 0)
            cost_after = moving_average(prod.stock_qty if prod.stock_enabled else 0, cost_before, qty, unit_price)

            if prod.stock_enabled:
                # Jalur restock produk yang udah ada (event stock.restock +
                # optimistic lock + auto-unhide). unit_buy_price = rata-rata
                # baru, jadi buy_price ter-snapshot sekalian.
                prod = await restock_product(
                    db,
                    product=prod,
                    quantity=int(qty),
                    outlet_id=outlet_id,
                    user_id=user_id,
                    notes=f"Nota {po.po_number}",
                    unit_buy_price=cost_after,
                    tier=tier,
                )
            else:
                # Produk tanpa tracking stok: cuma harga belinya yang diupdate.
                prod.buy_price = cost_after
                prod.row_version = (prod.row_version or 0) + 1

            db.add(PurchaseOrderItem(
                purchase_order_id=po.id,
                product_id=prod.id,
                name_snapshot=prod.name,
                quantity=qty,
                unit=(line.unit or "pcs"),
                qty_base=qty,
                unit_price=unit_price,
                total_price=line_total,
                received_quantity=qty,
            ))
            effects.append({
                "name": prod.name, "cost_before": cost_before, "cost_after": cost_after, "unit": "pcs",
            })
            event_lines.append({
                "product_id": str(prod.id), "name": prod.name, "qty": qty,
                "total": str(line_total), "cost_before": str(cost_before), "cost_after": str(cost_after),
            })

    po.total_amount = _q2(total)
    paid = _q2(total) if paid_amount is None else _q2(min(paid_amount, total))
    po.paid_amount = paid
    if paid < po.total_amount:
        terms = supplier.payment_terms_days if supplier else 0
        po.due_at = due_at or (received_at + timedelta(days=terms or 7))
    else:
        po.due_at = None

    db.add(Event(
        outlet_id=outlet_id,
        stream_id=f"purchase:{po.id}",
        event_type="purchase.received",
        event_data={
            "purchase_id": str(po.id),
            "po_number": po.po_number,
            "supplier_id": str(supplier.id) if supplier else None,
            "supplier_name": supplier.name if supplier else None,
            "total": str(po.total_amount),
            "paid": str(po.paid_amount),
            "outstanding": str(po.outstanding_amount),
            "due_at": po.due_at.isoformat() if po.due_at else None,
            "lines": event_lines,
        },
        event_metadata={"tier": tier, "user_id": str(user_id), "ts": now.isoformat()},
    ))

    # Cache konteks AI nyimpen HPP — harus dilepas begitu harga bahan berubah.
    try:
        from backend.services.redis import get_redis_client
        redis = await get_redis_client()
        await redis.delete(f"ai:context:{outlet_id}")
    except Exception:
        logger.warning("gagal invalidate ai:context sesudah nota", exc_info=True)

    await db.flush()
    return po, effects


async def _touch_ingredient_supplier(
    db: AsyncSession, *, ingredient: Ingredient, supplier: Supplier,
    price_per_base: Decimal, when: datetime, user_id: UUID,
):
    """Upsert ingredient_suppliers + tulis supplier_price_history kalau harga geser."""
    link = (await db.execute(
        select(IngredientSupplier).where(
            IngredientSupplier.ingredient_id == ingredient.id,
            IngredientSupplier.supplier_id == supplier.id,
            IngredientSupplier.deleted_at.is_(None),
        )
    )).scalar_one_or_none()

    old_price = link.last_purchase_price if link else None
    if link is None:
        link = IngredientSupplier(
            ingredient_id=ingredient.id, supplier_id=supplier.id,
            typical_price_per_base_unit=price_per_base,
        )
        db.add(link)
    else:
        # Harga "biasanya" = rata-rata 70/30 lama-baru — lebih tenang dari
        # harga terakhir doang, tapi tetap ngikut tren.
        prev = Decimal(str(link.typical_price_per_base_unit or price_per_base))
        link.typical_price_per_base_unit = _q2(prev * Decimal("0.7") + price_per_base * Decimal("0.3"))
        if old_price:
            diff = (price_per_base - Decimal(str(old_price))) / Decimal(str(old_price)) if old_price else 0
            link.price_trend = 'rising' if diff > Decimal("0.05") else ('falling' if diff < Decimal("-0.05") else 'stable')
        link.row_version = (link.row_version or 0) + 1

    link.last_purchase_price = price_per_base
    link.last_purchased_at = when

    if old_price is None or _q2(old_price) != price_per_base:
        db.add(SupplierPriceHistory(
            supplier_id=supplier.id,
            ingredient_id=ingredient.id,
            old_price=_q2(old_price) if old_price is not None else None,
            new_price=price_per_base,
            effective_date=when,
            created_by=user_id,
        ))


async def load_purchase(db: AsyncSession, purchase_id: UUID) -> Optional[PurchaseOrder]:
    return (await db.execute(
        select(PurchaseOrder)
        .options(
            selectinload(PurchaseOrder.items).selectinload(PurchaseOrderItem.ingredient),
            selectinload(PurchaseOrder.items).selectinload(PurchaseOrderItem.product),
            selectinload(PurchaseOrder.supplier),
        )
        .where(PurchaseOrder.id == purchase_id, PurchaseOrder.deleted_at.is_(None))
        .execution_options(populate_existing=True)
    )).scalar_one_or_none()
