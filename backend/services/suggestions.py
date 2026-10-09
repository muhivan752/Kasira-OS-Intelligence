"""Mesin saran Selaris. Rancangan: docs/SARAN_DESIGN.md (9 Okt 2026).

Satu rumah untuk saran proaktif: detektor, simpan/perbarui, daftar per peran,
terapkan, abaikan, batalkan.

- Detektor = kode murni. Mereka yang memutuskan KAPAN ada saran dan SEMUA
  angkanya; teks kartu dirakit di layar dari `facts`. Model AI hanya dipakai
  untuk takaran resep perkiraan (lewat hpp_setup_service yang sudah ada).
- Terapkan memakai jalur yang sudah ada: resep lewat sesi + approve HPP,
  harga lewat aturan update produk (row_version + audit), pesan pemasok lewat
  WhatsApp (tidak menyentuh stok; pembelian tetap dicatat saat barang datang).
- Kalau salah, ketahuan dari: status + skip_reason per jenis di
  `stats_by_kind` (superadmin), dan saklar KIND_ENABLED untuk mematikan
  detektor tanpa deploy kode (env SUGGESTIONS_DISABLED=kind,kind).

Belum ditelan: tasks/kg_price_event_loop.py (WA harga bahan naik dari edit
manual). Dilebur saat tahap B membawa notifikasi; sampai itu keduanya jalan.
"""
import asyncio
import hashlib
import json
import logging
import math as _math
import os
import re
from datetime import datetime, timedelta, timezone
from decimal import Decimal, ROUND_CEILING
from types import SimpleNamespace
from urllib.parse import quote
from uuid import UUID, uuid4
from zoneinfo import ZoneInfo

from fastapi import HTTPException
from sqlalchemy import and_, func, select, text, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import selectinload

from backend.core.database import AsyncSessionLocal
from backend.models.ingredient import Ingredient
from backend.models.order import Order, OrderItem
from backend.models.outlet import Outlet
from backend.models.product import OutletStock, Product
from backend.models.purchasing import PurchaseOrder, PurchaseOrderItem, Supplier, SupplierPriceHistory
from backend.models.recipe import Recipe, RecipeIngredient
from backend.models.suggestion import Suggestion
from backend.models.tenant import Tenant

logger = logging.getLogger(__name__)

KINDS = {
    # kind: (visibility, butuh paket Pro)
    "stock_low": ("stock", False),
    "ingredient_price_up": ("hpp", True),
    "thin_margin": ("hpp", True),
    "recipe_missing": ("hpp", True),  # resep + HPP chat memang fitur Pro
}
SKIP_REASONS = ("Sudah tahu", "Angkanya tidak sesuai", "Nanti saja", "Tidak relevan")
MAX_OPEN_SHOWN = 5
STOCK_DAYS_TRIGGER = 3       # waktu kirim pemasok 1 hari + cadangan 2 hari
STOCK_COVER_DAYS = 7
PRICE_UP_MIN = Decimal("0.05")
PRICE_UP_MIN_IMPACT = Decimal("20000")
THIN_MARGIN = Decimal("0.20")
TARGET_MARGIN = Decimal("0.30")
MAX_RAISE = Decimal("1.25")
THIN_MIN_SOLD = 10
RECIPE_MIN_SOLD = 5
RECIPE_DRAFTS_PER_RUN = 2
LOOP_SECONDS = 1800
RUN_FROM_HOUR = 6


def now():
    return datetime.now(timezone.utc)


def disabled_kinds():
    return {k.strip() for k in os.getenv("SUGGESTIONS_DISABLED", "").split(",") if k.strip()}


def ceil500(value) -> Decimal:
    v = Decimal(str(value))
    return (v / 500).to_integral_value(rounding=ROUND_CEILING) * 500


def h(*parts) -> str:
    return hashlib.sha256("|".join(str(p) for p in parts).encode()).hexdigest()


def display_qty(qty: float, unit: str) -> tuple[float, str]:
    unit = (unit or "").lower()
    if unit in ("gram", "g") and qty >= 1000:
        return round(qty / 1000, 2), "kg"
    if unit == "ml" and qty >= 1000:
        return round(qty / 1000, 2), "liter"
    return round(qty, 2), unit


def money(v) -> float:
    return float(Decimal(str(v)).quantize(Decimal("1")))


# ───────────────────────── data bersama ─────────────────────────

async def sold_by_product(db, outlet_id, days: int) -> dict:
    from backend.services.finance_service import _paid_order_filter
    since = now() - timedelta(days=days)
    rows = await db.execute(
        select(OrderItem.product_id, func.sum(OrderItem.quantity))
        .join(Order, Order.id == OrderItem.order_id)
        .where(Order.outlet_id == outlet_id, Order.deleted_at.is_(None), Order.status != "cancelled",
               Order.created_at >= since, OrderItem.deleted_at.is_(None), _paid_order_filter())
        .group_by(OrderItem.product_id))
    return {pid: int(q or 0) for pid, q in rows}


async def last_supplier(db, outlet_id, ingredient_id=None, product_id=None):
    col = PurchaseOrderItem.ingredient_id if ingredient_id else PurchaseOrderItem.product_id
    row = (await db.execute(
        select(Supplier).join(PurchaseOrder, PurchaseOrder.supplier_id == Supplier.id)
        .join(PurchaseOrderItem, PurchaseOrderItem.purchase_order_id == PurchaseOrder.id)
        .where(PurchaseOrder.outlet_id == outlet_id, PurchaseOrder.deleted_at.is_(None),
               PurchaseOrderItem.deleted_at.is_(None), col == (ingredient_id or product_id),
               Supplier.deleted_at.is_(None))
        .order_by(PurchaseOrder.created_at.desc()).limit(1))).scalar_one_or_none()
    return row


# ───────────────────────── detektor ─────────────────────────

def cand(kind, subject_type, subject_id, data_hash, facts, proposal, impact=0, urgent=False):
    return SimpleNamespace(kind=kind, subject_type=subject_type, subject_id=subject_id,
                           dedup_key=f"{kind}:{subject_id}", data_hash=data_hash, facts=facts,
                           proposal=proposal, impact=Decimal(str(impact or 0)), urgent=urgent)


def stock_candidate(*, kind_subject, subject_id, name, unit, stock, used_7d, active_days, min_stock,
                    pack, price_per_unit, supplier, cycle, tz, mode):
    """Murni: dari angka stok/pemakaian ke kandidat saran (atau None)."""
    if active_days < 3 and not (min_stock > 0 and stock <= min_stock):
        return None
    avg = used_7d / max(active_days, 1) if used_7d > 0 else 0.0
    days_left = (stock / avg) if avg > 0 else None
    low = (days_left is not None and days_left <= STOCK_DAYS_TRIGGER) or (min_stock > 0 and stock <= min_stock)
    if not low:
        return None
    need = max(avg * STOCK_COVER_DAYS - stock, avg) if avg > 0 else max(min_stock * 2 - stock, min_stock)
    pack = pack if pack and pack > 0 else 1.0
    packs = max(1, _math.ceil(need / pack - 1e-9))
    order_qty = packs * pack
    total = Decimal(str(price_per_unit or 0)) * Decimal(str(order_qty))
    runs_out = (now().astimezone(tz) + timedelta(days=days_left)).date().isoformat() if days_left is not None else None
    sq, su = display_qty(stock, unit)
    oq, ou = display_qty(order_qty, unit)
    facts = {"name": name, "mode": mode, "stock": sq, "stock_unit": su,
             "avg_daily": round(avg, 2), "avg_unit": unit, "days_left": round(days_left, 1) if days_left is not None else None,
             "runs_out_on": runs_out, "min_stock": min_stock, "order_qty": oq, "order_unit": ou,
             "price_per_unit": money(price_per_unit or 0), "price_unit": unit, "order_total": money(total),
             "supplier": {"id": str(supplier.id), "name": supplier.name, "has_phone": bool((supplier.phone or "").strip())} if supplier else None,
             "cover_days": STOCK_COVER_DAYS}
    proposal = {"action": "order_supplier", "subject": kind_subject, "subject_id": str(subject_id),
                "qty": order_qty, "unit": unit, "supplier_id": str(supplier.id) if supplier else None}
    return cand("stock_low", kind_subject, subject_id, h(subject_id, cycle), facts, proposal, urgent=True)


async def detect_stock(db, outlet, tz) -> list:
    out = []
    if outlet.stock_mode == "recipe":
        rows = (await db.execute(select(Ingredient, OutletStock).join(OutletStock, OutletStock.ingredient_id == Ingredient.id)
            .where(OutletStock.outlet_id == outlet.id, OutletStock.deleted_at.is_(None),
                   Ingredient.deleted_at.is_(None), Ingredient.ingredient_type == "recipe"))).all()
        used = {r[0]: r for r in (await db.execute(text(
            "SELECT ingredient_id, sum(abs(quantity_change)), min(created_at) FROM stock_events "
            "WHERE outlet_id = :o AND event_type = 'consume' AND deleted_at IS NULL "
            "AND created_at >= now() - interval '7 days' GROUP BY ingredient_id"), {"o": outlet.id})).all()}
        cycles = dict((await db.execute(text(
            "SELECT ingredient_id, max(created_at) FROM stock_events WHERE outlet_id = :o "
            "AND event_type = 'receive' AND deleted_at IS NULL GROUP BY ingredient_id"), {"o": outlet.id})).all())
        for ing, st in rows:
            u = used.get(ing.id)
            total = float(u[1]) if u else 0.0
            active = min(7, (now() - u[2]).days + 1) if u else 0
            supplier = await last_supplier(db, outlet.id, ingredient_id=ing.id)
            c = stock_candidate(kind_subject="ingredient", subject_id=ing.id, name=ing.name, unit=ing.base_unit,
                stock=float(st.computed_stock or 0), used_7d=total, active_days=active,
                min_stock=float(st.min_stock_base or 0), pack=float(ing.buy_qty or 0),
                price_per_unit=ing.cost_per_base_unit, supplier=supplier, cycle=cycles.get(ing.id), tz=tz, mode="recipe")
            if c:
                out.append(c)
    else:
        sold = await sold_by_product(db, outlet.id, 7)
        first = dict((await db.execute(
            select(OrderItem.product_id, func.min(Order.created_at)).join(Order, Order.id == OrderItem.order_id)
            .where(Order.outlet_id == outlet.id, Order.created_at >= now() - timedelta(days=7), Order.deleted_at.is_(None))
            .group_by(OrderItem.product_id))).all())
        products = (await db.execute(select(Product).where(Product.brand_id == outlet.brand_id,
            Product.deleted_at.is_(None), Product.is_active.is_(True), Product.stock_enabled.is_(True)))).scalars().all()
        for p in products:
            f = first.get(p.id)
            active = min(7, (now() - f).days + 1) if f else 0
            supplier = await last_supplier(db, outlet.id, product_id=p.id)
            c = stock_candidate(kind_subject="product", subject_id=p.id, name=p.name, unit="pcs",
                stock=float(p.stock_qty or 0), used_7d=float(sold.get(p.id, 0)), active_days=active,
                min_stock=float(getattr(p, "stock_low_threshold", 0) or 0), pack=1.0,
                price_per_unit=p.buy_price or 0, supplier=supplier, cycle=p.last_restock_at, tz=tz, mode="simple")
            if c:
                out.append(c)
    return out


def price_target(cost: Decimal, base: Decimal, margin: Decimal) -> Decimal | None:
    """Harga jual untuk margin `margin`, dibulatkan ke atas ke Rp 500, maksimal naik 25%."""
    if margin >= 1 or cost <= 0 or base <= 0:
        return None
    target = ceil500(cost / (1 - margin))
    cap = ceil500(base * MAX_RAISE)
    new = min(target, cap)
    return new if new > base else None


async def detect_prices(db, outlet, sold30, cost) -> tuple[list, set]:
    """Harga bahan naik (dari pembelian) dan margin tipis. Balikin juga produk yang sudah dibahas."""
    out, covered = [], set()
    rows = (await db.execute(select(SupplierPriceHistory, Ingredient, Supplier)
        .join(Ingredient, Ingredient.id == SupplierPriceHistory.ingredient_id)
        .join(Supplier, Supplier.id == SupplierPriceHistory.supplier_id)
        .where(Ingredient.brand_id == outlet.brand_id, Ingredient.deleted_at.is_(None),
               SupplierPriceHistory.effective_date >= now() - timedelta(days=14),
               SupplierPriceHistory.old_price.is_not(None), SupplierPriceHistory.old_price > 0)
        .order_by(SupplierPriceHistory.effective_date.desc()))).all()
    latest = {}
    for sph, ing, sup in rows:
        latest.setdefault(ing.id, (sph, ing, sup))
    for sph, ing, sup in latest.values():
        old, new = Decimal(str(sph.old_price)), Decimal(str(sph.new_price))
        if new < old * (1 + PRICE_UP_MIN):
            continue
        uses = (await db.execute(select(RecipeIngredient).join(Recipe, Recipe.id == RecipeIngredient.recipe_id)
            .join(Product, Product.id == Recipe.product_id)
            .options(selectinload(RecipeIngredient.ingredient))
            .where(RecipeIngredient.ingredient_id == ing.id, RecipeIngredient.deleted_at.is_(None),
                   RecipeIngredient.is_optional.is_(False), Recipe.is_active.is_(True), Recipe.deleted_at.is_(None),
                   Product.brand_id == outlet.brand_id, Product.deleted_at.is_(None)))).scalars().all()
        from backend.services.unit_utils import normalize_recipe_qty
        affected = []
        for ri in uses:
            rec = await db.get(Recipe, ri.recipe_id)
            product = await db.get(Product, rec.product_id)
            q = normalize_recipe_qty(ri)
            n = sold30.get(product.id, 0)
            if not q or n <= 0 or product.id not in cost:
                continue
            delta = Decimal(str(q)) * (new - old)
            affected.append((product, delta, n))
        impact = sum((d * n for _, d, n in affected), Decimal(0))
        if not affected or impact < PRICE_UP_MIN_IMPACT:
            continue
        affected.sort(key=lambda x: x[1] * x[2], reverse=True)
        top, delta, n = affected[0]
        base = Decimal(str(top.base_price or 0))
        cost_now = cost[top.id]
        cost_before = cost_now - delta
        margin_before = (base - cost_before) / base if base > 0 else Decimal(0)
        new_price = price_target(cost_now, base, margin_before) if margin_before > 0 else None
        unit_factor = 1000 if (ing.base_unit or "").lower() in ("gram", "ml") else 1
        facts = {"ingredient": ing.name, "unit": "kg" if ing.base_unit == "gram" else "liter" if ing.base_unit == "ml" else ing.base_unit,
                 "old_price": money(old * unit_factor), "new_price": money(new * unit_factor),
                 "pct": round(float((new - old) / old * 100), 1), "date": sph.effective_date.date().isoformat(),
                 "supplier": sup.name, "monthly_loss": money(impact),
                 "products": [{"id": str(p.id), "name": p.name, "sold_30d": k, "cost_up": money(d)} for p, d, k in affected[:5]],
                 "top": {"id": str(top.id), "name": top.name, "base_price": money(base), "cost_before": money(cost_before),
                         "cost_now": money(cost_now), "margin_before": round(float(margin_before * 100), 1),
                         "margin_now": round(float((base - cost_now) / base * 100), 1) if base > 0 else None,
                         "new_price": money(new_price) if new_price else None,
                         "margin_new": round(float((new_price - cost_now) / new_price * 100), 1) if new_price else None,
                         "sold_30d": n}}
        proposal = ({"action": "update_price", "product_id": str(top.id), "old_price": money(base), "new_price": money(new_price)}
                    if new_price else {"action": "none"})
        covered.update(p.id for p, _, _ in affected)
        out.append(cand("ingredient_price_up", "ingredient", ing.id, h(ing.id, sph.id), facts, proposal, impact=impact))
    products = (await db.execute(select(Product).where(Product.brand_id == outlet.brand_id,
        Product.deleted_at.is_(None), Product.is_active.is_(True)))).scalars().all()
    for p in products:
        n = sold30.get(p.id, 0)
        base = Decimal(str(p.base_price or 0))
        if p.id in covered or n < THIN_MIN_SOLD or base <= 0 or p.id not in cost:
            continue
        c = cost[p.id]
        margin = (base - c) / base
        if margin >= THIN_MARGIN:
            continue
        new_price = price_target(c, base, TARGET_MARGIN)
        if not new_price:
            continue
        impact = (new_price - base) * n
        facts = {"name": p.name, "base_price": money(base), "cost": money(c), "margin": round(float(margin * 100), 1),
                 "profit_per_unit": money(base - c), "new_price": money(new_price),
                 "margin_new": round(float((new_price - c) / new_price * 100), 1), "sold_30d": n, "monthly_gain": money(impact)}
        proposal = {"action": "update_price", "product_id": str(p.id), "old_price": money(base), "new_price": money(new_price)}
        out.append(cand("thin_margin", "product", p.id, h(p.id, money(base), round(float(c), -2)), facts, proposal, impact=impact))
    return out, covered


async def recipe_draft(db, outlet, product):
    """Takaran perkiraan dari model, modal dihitung kode (hpp_setup_service.prepare)."""
    from backend.services import hpp_setup_service as hpp
    ctx = await hpp.context(db, outlet.brand_id)
    msg = (f"Lengkapi estimasi resep {product.name} untuk 1 porsi. Pakai bahan yang sudah ada di toko kalau cocok, "
           "beri takaran dan harga beli perkiraan yang umum untuk usaha di Indonesia.")
    turn = SimpleNamespace(message=msg, reply=None)
    answer, _ = await hpp.generate(None, [turn], ctx, "estimate")
    if answer.draft is None:
        return None, None, msg
    draft = answer.draft.model_dump(mode="json")
    preview = hpp.prepare(answer.draft, ctx, [msg], "estimate")
    return draft, preview, msg


def preview_summary(preview):
    if not preview:
        return None
    return {"ready": preview["ready"], "total_cost": preview["total_cost"], "missing": preview["missing"][:3],
            "lines": [{"name": l["name"], "qty": l["input_quantity"], "unit": l["input_unit"] or l["unit"],
                       "cost": l["line_cost"], "estimated": l["is_estimated"], "price_source": l["price_source"]}
                      for l in preview["lines"]]}


async def detect_recipes(db, outlet, sold30, cost, existing_open: set) -> list:
    if outlet.stock_mode != "recipe":
        return []
    out, drafts = [], 0
    products = (await db.execute(select(Product).where(Product.brand_id == outlet.brand_id,
        Product.deleted_at.is_(None), Product.is_active.is_(True)))).scalars().all()
    for p in sorted(products, key=lambda p: sold30.get(p.id, 0), reverse=True):
        n = sold30.get(p.id, 0)
        if n < RECIPE_MIN_SOLD or p.id in cost:
            continue
        key = f"recipe_missing:{p.id}"
        facts = {"name": p.name, "sold_30d": n, "base_price": money(p.base_price or 0), "preview": None}
        proposal = {"action": "apply_recipe", "product_id": str(p.id), "draft": None, "message": None}
        if key not in existing_open and drafts < RECIPE_DRAFTS_PER_RUN:
            drafts += 1
            try:
                draft, preview, msg = await recipe_draft(db, outlet, p)
                facts["preview"] = preview_summary(preview)
                proposal.update(draft=draft, message=msg)
            except Exception:  # noqa: BLE001  tanpa draf, kartu tetap muncul dan membuka percakapan resep
                logger.warning("suggestions: draf resep %s gagal", p.id, exc_info=True)
        elif key in existing_open:
            facts = proposal = None  # yang sudah terbuka dipertahankan apa adanya
        out.append(cand("recipe_missing", "product", p.id, h(p.id), facts, proposal, impact=0))
    return out


# ───────────────────────── simpan ─────────────────────────

async def run_outlet(db, tenant, outlet) -> dict:
    """Satu putaran detektor untuk satu outlet. Pemanggil sudah memasang RLS tenant."""
    tz = ZoneInfo(outlet.timezone or "Asia/Jakarta")
    pro = _is_pro(tenant)
    off = disabled_kinds()
    from backend.services.finance_service import cost_map_for_brand
    sold30 = await sold_by_product(db, outlet.id, 30)
    cost = await cost_map_for_brand(db, outlet.brand_id)
    open_rows = {s.dedup_key: s for s in (await db.execute(select(Suggestion).where(
        Suggestion.tenant_id == tenant.id, Suggestion.outlet_id == outlet.id, Suggestion.status == "open"))).scalars()}
    await reconcile_recipes(db, open_rows.values())
    cands = []
    if "stock_low" not in off:
        cands += await detect_stock(db, outlet, tz)
    if pro:
        price, _ = await detect_prices(db, outlet, sold30, cost)
        cands += [c for c in price if c.kind not in off]
        if "recipe_missing" not in off:
            cands += await detect_recipes(db, outlet, sold30, cost, set(open_rows))
    seen, counts = set(), {"new": 0, "updated": 0, "expired": 0}
    for c in cands:
        seen.add(c.dedup_key)
        row = open_rows.get(c.dedup_key)
        if row:
            if c.facts is not None and row.hpp_session_id is None:
                row.facts, row.proposal = c.facts, c.proposal
            row.impact_rp, row.urgent, row.data_hash = c.impact, c.urgent, c.data_hash
            row.updated_at, row.row_version = now(), row.row_version + 1
            counts["updated"] += 1
            continue
        last = (await db.execute(select(Suggestion).where(Suggestion.tenant_id == tenant.id,
            Suggestion.outlet_id == outlet.id, Suggestion.dedup_key == c.dedup_key)
            .order_by(Suggestion.created_at.desc()).limit(1))).scalar_one_or_none()
        if last and last.data_hash == c.data_hash and last.status in ("applied", "skipped", "undone"):
            continue  # sudah diputuskan untuk data yang sama: jangan diulang
        res = await db.execute(insert(Suggestion).values(
            id=uuid4(), tenant_id=tenant.id, outlet_id=outlet.id, kind=c.kind, subject_type=c.subject_type,
            subject_id=c.subject_id, dedup_key=c.dedup_key, data_hash=c.data_hash, facts=c.facts,
            proposal=c.proposal, impact_rp=c.impact, urgent=c.urgent, visibility=KINDS[c.kind][0],
            status="open", expires_at=now() + timedelta(days=3 if c.kind == "stock_low" else 14),
            created_at=now(), updated_at=now(), row_version=0)
            .on_conflict_do_nothing(index_elements=["tenant_id", "outlet_id", "dedup_key"],
                                    index_where=text("status = 'open'")))
        counts["new"] += res.rowcount or 0
    for key, row in open_rows.items():
        if row.status == "open" and (key not in seen or (row.expires_at and row.expires_at < now())):
            row.status, row.updated_at, row.row_version = "expired", now(), row.row_version + 1
            counts["expired"] += 1
    await db.commit()
    return counts


def _is_pro(tenant) -> bool:
    from backend.services.subscription import is_pro_tier
    return is_pro_tier(tenant)


async def reconcile_recipes(db, rows):
    """Saran resep yang sesi HPP-nya sudah di-approve = diterapkan."""
    from backend.models.hpp_setup import HppSetupSession
    for row in rows:
        if row.kind == "recipe_missing" and row.hpp_session_id and row.status == "open":
            session = await db.get(HppSetupSession, row.hpp_session_id)
            if session and session.status == "applied":
                row.status, row.decided_by, row.decided_at = "applied", session.user_id, session.updated_at or now()
                row.result = session.result
                row.row_version += 1


# ───────────────────────── daftar per peran ─────────────────────────

def can_view(access, kind) -> bool:
    if access.mode == "owner" or access.allows("hpp.view"):
        return True
    return kind == "stock_low" and access.allows("stock.view")


def can_apply(access, kind) -> bool:
    if access.mode == "owner":
        return True
    if kind == "stock_low":
        return access.allows("purchasing.manage")
    if kind == "recipe_missing":
        return all(access.allows(p) for p in ("ai.chat", "hpp.view", "supplier.price.view", "hpp.manage"))
    return False  # ubah harga jual: pemilik saja, sama dengan update produk


def present(row, access) -> dict:
    full = access.mode == "owner" or access.allows("hpp.view")
    facts = dict(row.facts or {})
    if not full:
        # Peringatan stok untuk karyawan: tanpa harga, total, dan pemasok.
        for k in ("price_per_unit", "price_unit", "order_total", "supplier"):
            facts.pop(k, None)
    return {"id": str(row.id), "kind": row.kind, "status": row.status, "urgent": row.urgent,
            "impact_rp": money(row.impact_rp), "facts": facts,
            "proposal": row.proposal if full else None,
            "can_apply": row.status == "open" and can_apply(access, row.kind),
            "can_undo": row.status in ("applied", "skipped") and access.mode == "owner" and row.kind != "recipe_missing",
            "skip_reason": row.skip_reason, "decided_at": row.decided_at.isoformat() if row.decided_at else None,
            "result": row.result if full else None, "hpp_session_id": str(row.hpp_session_id) if row.hpp_session_id else None,
            "created_at": row.created_at.isoformat()}


async def list_for(db, user, access, outlet_id) -> dict:
    if outlet_id not in access.outlet_ids:
        raise HTTPException(404, "Outlet aktif tidak ditemukan dalam akses akun ini")
    tenant = await db.get(Tenant, user.tenant_id)
    allowed = {k for k, (_, pro) in KINDS.items() if not pro or _is_pro(tenant)}
    rows = (await db.execute(select(Suggestion).where(Suggestion.tenant_id == user.tenant_id,
        Suggestion.outlet_id == outlet_id, Suggestion.deleted_at.is_(None),
        (Suggestion.status == "open") | (Suggestion.decided_at >= now() - timedelta(days=7)))
        .order_by(Suggestion.created_at.desc()))).scalars().all()
    await reconcile_recipes(db, rows)
    await db.commit()
    visible = [r for r in rows if r.kind in allowed and can_view(access, r.kind)]
    open_ = sorted([r for r in visible if r.status == "open"],
                   key=lambda r: (not r.urgent, -float(r.impact_rp), r.created_at))[:MAX_OPEN_SHOWN]
    decided = [r for r in visible if r.status in ("applied", "skipped", "undone")][:10]
    return {"open": [present(r, access) for r in open_], "decided": [present(r, access) for r in decided],
            "monthly_impact": money(sum((r.impact_rp for r in open_), Decimal(0)))}


# ───────────────────────── keputusan ─────────────────────────

async def _locked(db, user, suggestion_id) -> Suggestion:
    row = (await db.execute(select(Suggestion).where(Suggestion.id == suggestion_id,
        Suggestion.tenant_id == user.tenant_id, Suggestion.deleted_at.is_(None)).with_for_update())).scalar_one_or_none()
    if not row:
        raise HTTPException(404, "Saran tidak ditemukan")
    return row


def _decide(row, user, status):
    row.status, row.decided_by, row.decided_at = status, user.id, now()
    row.updated_at, row.row_version = now(), row.row_version + 1


async def apply(db, user, access, suggestion_id, params=None) -> dict:
    row = await _locked(db, user, suggestion_id)
    if row.outlet_id not in access.outlet_ids or not can_view(access, row.kind):
        raise HTTPException(404, "Saran tidak ditemukan")
    if row.status == "applied":
        return present(row, access)  # ketuk dua kali = hasil yang sama
    if row.status != "open":
        raise HTTPException(409, "Saran ini sudah diputuskan")
    if not can_apply(access, row.kind):
        raise HTTPException(403, "Akses ini belum diberikan oleh pemilik usaha")
    action = (row.proposal or {}).get("action")
    params = params or {}
    if action == "order_supplier":
        qty = params.get("qty")
        if qty is not None:
            if not 0 < qty <= 1_000_000:
                raise HTTPException(422, "Jumlah pesanan tidak masuk akal")
            row.facts = {**row.facts, "order_qty": qty}
            row.edited = True
        row.result = await _order_message(db, row)
        _decide(row, user, "applied")
    elif action == "update_price":
        new_price = row.proposal["new_price"]
        if params.get("new_price") is not None:
            new_price = params["new_price"]
            old = row.proposal["old_price"]
            if not (100 <= new_price <= old * 3) or new_price % 100:
                raise HTTPException(422, "Harga baru harus kelipatan Rp 100 dan paling banyak tiga kali harga sekarang")
            row.edited = new_price != row.proposal["new_price"]
        row.result, row.undo = await _set_price(db, user, row, new_price, row.proposal["old_price"])
        _decide(row, user, "applied")
    elif action == "apply_recipe":
        row.result = await _start_recipe(db, user, access, row)
        row.updated_at, row.row_version = now(), row.row_version + 1  # status tetap open sampai approve HPP
    else:
        raise HTTPException(422, "Saran ini tidak punya tindakan")
    await db.commit()
    return present(row, access)


async def _order_message(db, row) -> dict:
    f = row.facts
    supplier = await db.get(Supplier, UUID(row.proposal["supplier_id"])) if row.proposal.get("supplier_id") else None
    outlet = await db.get(Outlet, row.outlet_id)
    text_ = (f"Halo {supplier.name if supplier else ''}, saya mau pesan {f['order_qty']:g} {f['order_unit']} {f['name']}. "
             f"Bisa dikirim secepatnya? Terima kasih. {outlet.name}").replace("Halo ,", "Halo,")
    phone = re.sub(r"\D", "", (supplier.phone or "") if supplier else "")
    if phone.startswith("0"):
        phone = "62" + phone[1:]
    return {"message": text_, "wa_link": f"https://wa.me/{phone}?text={quote(text_)}" if phone else None}


async def _set_price(db, user, row, new_price, expected_old) -> tuple[dict, dict]:
    """Aturan sama dengan PUT /products/{id}: row_version naik + audit. Hanya kalau harga belum diubah orang."""
    from backend.services.audit import log_audit
    pid = UUID(row.proposal["product_id"])
    product = (await db.execute(select(Product).where(Product.id == pid, Product.deleted_at.is_(None))
        .with_for_update())).scalar_one_or_none()
    outlet = await db.get(Outlet, row.outlet_id)
    if not product or product.brand_id != outlet.brand_id:
        raise HTTPException(404, "Produk tidak ditemukan")
    if money(product.base_price) != money(expected_old):
        raise HTTPException(409, f"Harga {product.name} sudah berubah sejak saran dibuat. Muat ulang saran.")
    before = money(product.base_price)
    product.base_price = Decimal(str(new_price))
    product.row_version += 1
    product.updated_at = now()
    await log_audit(db=db, action="UPDATE", entity="product", entity_id=product.id,
        before_state={"base_price": before, "source": f"suggestion:{row.id}"},
        after_state={"base_price": float(new_price), "source": f"suggestion:{row.id}"},
        user_id=user.id, tenant_id=user.tenant_id)
    await _clear_cache(db, outlet)
    return ({"product_id": str(pid), "name": product.name, "old_price": before, "new_price": float(new_price)},
            {"product_id": str(pid), "old_price": before, "new_price": float(new_price)})


async def _clear_cache(db, outlet):
    try:
        from backend.services.redis import get_redis_client
        rows = (await db.execute(select(Outlet.id, Outlet.slug).where(Outlet.brand_id == outlet.brand_id,
            Outlet.deleted_at.is_(None)))).all()
        keys = [k for oid, slug in rows for k in (f"ai:context:{oid}", f"connect:storefront:{slug}")]
        if keys:
            await (await get_redis_client()).delete(*keys)
    except Exception:  # noqa: BLE001  cache kedaluwarsa sendiri
        logger.info("suggestions: cache refresh ditunda")


async def _start_recipe(db, user, access, row) -> dict:
    """Bikin sesi HPP dari draf saran. Persetujuannya tetap lewat POST /hpp-setup/sessions/{id}/approve."""
    from backend.models.audit_log import AuditLog
    from backend.models.hpp_setup import HppSetupSession, HppSetupTurn
    from backend.services import hpp_setup_service as hpp
    tenant = await db.get(Tenant, user.tenant_id)
    if not _is_pro(tenant):
        raise HTTPException(403, "Resep dan HPP tersedia di paket Pro")
    if row.hpp_session_id:
        session = await db.get(HppSetupSession, row.hpp_session_id)
        if session and session.status == "draft":
            return _session_ref(session)
    outlet = await db.get(Outlet, row.outlet_id)
    p = row.proposal
    draft = p.get("draft")
    preview, revision = None, 0
    if draft:
        ctx = await hpp.context(db, outlet.brand_id)
        preview = hpp.prepare(hpp.Draft.model_validate(draft), ctx, [p.get("message") or ""], "estimate")
        revision = 1
    session = HppSetupSession(id=uuid4(), tenant_id=user.tenant_id, outlet_id=outlet.id, user_id=user.id,
        access_version=access.version, mode="estimate", draft=draft, preview=preview, status="draft", revision=revision)
    db.add(session)
    await db.flush()
    if draft:
        db.add(HppSetupTurn(tenant_id=user.tenant_id, session_id=session.id, request_id=uuid4(), mode="estimate",
            message=p.get("message") or "", reply="Ini perkiraan resep dari Selaris. Cek takarannya, koreksi kalau beda, lalu simpan.",
            usage={"source": f"suggestion:{row.id}"}))
    db.add(AuditLog(tenant_id=user.tenant_id, user_id=user.id, action="HPP_SETUP_STARTED",
        entity="hpp_setup_session", entity_id=session.id, after_state={"mode": "estimate", "source": f"suggestion:{row.id}"}))
    row.hpp_session_id = session.id
    return _session_ref(session)


def _session_ref(session) -> dict:
    preview = session.preview or {}
    return {"hpp_session": {"id": str(session.id), "revision": session.revision,
            "fingerprint": preview.get("fingerprint"), "ready": bool(preview.get("ready")),
            "replaces_recipe": bool(preview.get("replaces_recipe"))}}


async def skip(db, user, access, suggestion_id, reason) -> dict:
    if reason not in SKIP_REASONS:
        raise HTTPException(422, "Alasan tidak dikenal")
    row = await _locked(db, user, suggestion_id)
    if row.outlet_id not in access.outlet_ids or not can_view(access, row.kind):
        raise HTTPException(404, "Saran tidak ditemukan")
    if row.status == "skipped":
        return present(row, access)
    if row.status != "open":
        raise HTTPException(409, "Saran ini sudah diputuskan")
    if not can_apply(access, row.kind):
        raise HTTPException(403, "Akses ini belum diberikan oleh pemilik usaha")
    row.skip_reason = reason
    _decide(row, user, "skipped")
    await db.commit()
    return present(row, access)


async def undo(db, user, access, suggestion_id) -> dict:
    row = await _locked(db, user, suggestion_id)
    if access.mode != "owner" or row.outlet_id not in access.outlet_ids:
        raise HTTPException(403, "Hanya pemilik usaha yang dapat membatalkan")
    if row.kind == "recipe_missing":
        raise HTTPException(409, "Resep yang sudah disimpan diubah lewat menu Resep")
    if row.status == "skipped" or (row.status == "applied" and row.proposal.get("action") == "order_supplier"):
        row.status, row.decided_by, row.decided_at, row.skip_reason, row.result = "open", None, None, None, None
        row.updated_at, row.row_version = now(), row.row_version + 1
    elif row.status == "applied" and row.undo:
        product = (await db.execute(select(Product).where(Product.id == UUID(row.undo["product_id"])).with_for_update())).scalar_one_or_none()
        if not product or money(product.base_price) != money(row.undo["new_price"]):
            raise HTTPException(409, "Harga sudah diubah lagi sesudah saran diterapkan, jadi tidak dibatalkan otomatis")
        await _set_price(db, user, row, row.undo["old_price"], row.undo["new_price"])
        _decide(row, user, "undone")
    else:
        raise HTTPException(409, "Saran ini tidak bisa dibatalkan")
    await db.commit()
    return present(row, access)


async def stats_by_kind(db) -> list:
    rows = await db.execute(text(
        "SELECT kind, status, coalesce(skip_reason, ''), count(*) FROM suggestions "
        "WHERE created_at >= now() - interval '30 days' GROUP BY 1, 2, 3 ORDER BY 1, 2"))
    return [{"kind": k, "status": s, "skip_reason": r or None, "count": n} for k, s, r, n in rows]


# ───────────────────────── loop harian ─────────────────────────

async def run_due_once(force_outlet=None) -> int:
    """Jalankan detektor untuk outlet yang belum jalan hari ini (waktu lokal ≥ 06.00)."""
    from backend.services.redis import get_redis_client
    redis = None
    try:
        redis = await get_redis_client()
        if not force_outlet and not await redis.set("suggestions:lock", "1", nx=True, ex=LOOP_SECONDS - 60):
            return 0
    except Exception:  # noqa: BLE001
        logger.warning("suggestions: redis tidak tersedia, lanjut tanpa kunci", exc_info=True)
    async with AsyncSessionLocal() as db:
        await db.execute(text("SET LOCAL app.current_tenant_id = ''"))
        q = select(Outlet.id, Outlet.tenant_id, Outlet.timezone).join(Tenant, Tenant.id == Outlet.tenant_id).where(
            Outlet.deleted_at.is_(None), Outlet.is_active.is_(True), Tenant.deleted_at.is_(None),
            Tenant.is_active.is_(True), Tenant.is_demo.is_(False))
        if force_outlet:
            q = q.where(Outlet.id == force_outlet)
        outlets = (await db.execute(q)).all()
    done = 0
    for oid, tid, tzname in outlets:
        local = now().astimezone(ZoneInfo(tzname or "Asia/Jakarta"))
        key = f"suggestions:ran:{oid}:{local.date().isoformat()}"
        if not force_outlet:
            if local.hour < RUN_FROM_HOUR:
                continue
            try:
                if redis and await redis.get(key):
                    continue
            except Exception:  # noqa: BLE001
                pass
        async with AsyncSessionLocal() as db:
            try:
                await db.execute(text("SELECT set_config('app.current_tenant_id', :t, true)"), {"t": str(tid)})
                tenant = await db.get(Tenant, tid)
                outlet = await db.get(Outlet, oid)
                counts = await run_outlet(db, tenant, outlet)
                done += 1
                logger.info("suggestions: outlet %s %s", oid, counts)
                if redis:
                    await redis.set(key, "1", ex=26 * 3600)
            except Exception:  # noqa: BLE001  satu outlet gagal tidak menahan yang lain
                await db.rollback()
                logger.exception("suggestions: outlet %s gagal", oid)
    return done


async def suggestions_loop():
    await asyncio.sleep(90)
    while True:
        try:
            await run_due_once()
        except Exception:  # noqa: BLE001
            logger.exception("suggestions: loop error")
        await asyncio.sleep(LOOP_SECONDS)
