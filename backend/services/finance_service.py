"""
Keuangan ringan — laba rugi & arus kas yang KEBENTUK SENDIRI.

Nggak ada jurnal, nggak ada ledger yang diisi. Semua angka dihitung dari
tabel yang udah diisi jalur lain:

  Laba rugi (akrual, per bulan WIB):
    pendapatan  = Σ total_amount order LUNAS (pola `_paid_order_filter` reports.py —
                  order tab dibaca dari tab.status, gotcha #24)
    − refund    = Σ payment_refunds completed
    − HPP       = Σ qty × cost per item terjual
                  cost = HPP resep (menu_engineering._get_hpp_map) kalau ada,
                         else product.buy_price (Starter / produk jadi)
    − beban     = Σ expenses + kas kecil shift (cash_activities expense)
    = laba bersih

  Arus kas (kas beneran gerak, per bulan):
    masuk  = payments paid (amount_paid − change) per metode → akun kas
           + cash_activities income
    keluar = refunds + expenses (yang BUKAN dari nota) + nota belanja yang dibayar
           + cash_activities expense

Nota belanja sengaja nggak masuk laba rugi (itu stok, jadi HPP waktu terjual),
tapi masuk arus kas. Baris "Lainnya" di nota jadi `expenses` dengan
`purchase_id` — masuk laba rugi sebagai beban, TAPI di arus kas diwakili
pembayaran nota-nya (biar nggak dobel).
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone, timedelta, date
from decimal import Decimal, ROUND_HALF_UP
from typing import Optional
from uuid import UUID
from zoneinfo import ZoneInfo

from fastapi import HTTPException
from sqlalchemy import select, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.models.finance import (
    Expense, CashAccount, EXPENSE_CATEGORIES, EXPENSE_CATEGORY_KEYS,
)
from backend.models.order import Order, OrderItem
from backend.models.outlet import Outlet
from backend.models.payment import Payment
from backend.models.payment_refund import PaymentRefund
from backend.models.product import Product
from backend.models.purchasing import PurchaseOrder
from backend.models.shift import Shift, CashActivity, CashActivityType
from backend.models.tab import Tab
from backend.schemas.finance import (
    FinanceSummary, CategoryAmount, AccountFlow, MonthPoint, ExpenseResponse,
)

logger = logging.getLogger(__name__)

WIB = ZoneInfo("Asia/Jakarta")
_Q2 = Decimal("0.01")
CATEGORY_LABEL = dict(EXPENSE_CATEGORIES)


def _q2(x) -> Decimal:
    return Decimal(str(x or 0)).quantize(_Q2, rounding=ROUND_HALF_UP)


def month_bounds(month: str) -> tuple[datetime, datetime]:
    """'2026-09' → (awal bulan WIB, awal bulan berikutnya WIB) dalam UTC."""
    try:
        y, m = (int(p) for p in month.split("-"))
        start = datetime(y, m, 1, tzinfo=WIB)
    except Exception:
        raise HTTPException(status_code=400, detail="Format bulan harus YYYY-MM")
    end = datetime(y + (m // 12), (m % 12) + 1, 1, tzinfo=WIB)
    return start.astimezone(timezone.utc), end.astimezone(timezone.utc)


def _paid_order_filter():
    # Salinan pola reports.py — import langsung bikin dependency route→route.
    return or_(
        and_(
            Order.tab_id.is_(None),
            Order.id.in_(select(Payment.order_id).where(Payment.status == "paid", Payment.deleted_at.is_(None))),
        ),
        and_(
            Order.tab_id.isnot(None),
            Order.tab_id.in_(select(Tab.id).where(Tab.status == "paid", Tab.deleted_at.is_(None))),
        ),
    )


# ───────────────────────── akun kas ─────────────────────────

DEFAULT_ACCOUNTS = [
    ("Kas Laci", "cash_drawer", ["cash"], 0),
    ("Rekening Bank", "bank", ["transfer", "card"], 1),
    ("QRIS & Xendit", "settlement", ["qris", "ewallet"], 2),
]


async def ensure_accounts(db: AsyncSession, tenant_id: UUID) -> list[CashAccount]:
    """Tenant baru langsung punya 3 akun standar — nol setup."""
    rows = (await db.execute(
        select(CashAccount).where(CashAccount.tenant_id == tenant_id, CashAccount.deleted_at.is_(None))
        .order_by(CashAccount.sort_order, CashAccount.name)
    )).scalars().all()
    if rows:
        return list(rows)
    created = []
    for name, kind, methods, order in DEFAULT_ACCOUNTS:
        acc = CashAccount(tenant_id=tenant_id, name=name, kind=kind, default_for=methods, sort_order=order)
        db.add(acc)
        created.append(acc)
    await db.flush()
    return created


def account_for_method(accounts: list[CashAccount], method: str) -> Optional[CashAccount]:
    m = (method or "cash").lower()
    for a in accounts:
        if m in (a.default_for or []):
            return a
    # ewallet/card yang belum dipetakan → akun pertama non-laci, else laci
    for a in accounts:
        if a.kind != "cash_drawer":
            return a
    return accounts[0] if accounts else None


# ───────────────────────── HPP per produk ─────────────────────────

async def cost_map_for_brand(db: AsyncSession, brand_id: UUID) -> dict[UUID, Decimal]:
    """HPP resep (Pro) di-override-in buy_price kalau resepnya nggak ada."""
    from backend.services.menu_engineering_service import _get_hpp_map
    cost: dict[UUID, Decimal] = {}
    try:
        cost.update(await _get_hpp_map(db, brand_id))
    except Exception:
        logger.warning("hpp map gagal, fallback buy_price", exc_info=True)
    rows = (await db.execute(
        select(Product.id, Product.buy_price).where(Product.brand_id == brand_id, Product.deleted_at.is_(None))
    )).all()
    for pid, buy in rows:
        if pid not in cost and buy is not None and buy > 0:
            cost[pid] = _q2(buy)
    return cost


# ───────────────────────── blok hitung per bulan ─────────────────────────

async def _pnl_block(db: AsyncSession, outlet: Outlet, start: datetime, end: datetime, cost: dict) -> dict:
    """Pendapatan, refund, HPP, jumlah order untuk satu rentang."""
    base = [
        Order.outlet_id == outlet.id,
        Order.deleted_at.is_(None),
        Order.status != "cancelled",
        Order.created_at >= start,
        Order.created_at < end,
        _paid_order_filter(),
    ]
    rev_row = (await db.execute(
        select(func.coalesce(func.sum(Order.total_amount), 0), func.count(Order.id)).where(*base)
    )).one()
    revenue = _q2(rev_row[0]); orders_count = int(rev_row[1])

    items = (await db.execute(
        select(OrderItem.product_id, func.sum(OrderItem.quantity))
        .join(Order, Order.id == OrderItem.order_id)
        .where(*base, OrderItem.deleted_at.is_(None))
        .group_by(OrderItem.product_id)
    )).all()
    cogs = Decimal("0"); qty_total = 0; qty_costed = 0
    for pid, qty in items:
        qty = int(qty or 0); qty_total += qty
        c = cost.get(pid)
        if c is not None:
            cogs += c * qty; qty_costed += qty

    refunds = _q2((await db.execute(
        select(func.coalesce(func.sum(PaymentRefund.amount), 0))
        .join(Payment, Payment.id == PaymentRefund.payment_id)
        .where(
            Payment.outlet_id == outlet.id,
            PaymentRefund.status == "completed",
            PaymentRefund.deleted_at.is_(None),
            func.coalesce(PaymentRefund.completed_at, PaymentRefund.created_at) >= start,
            func.coalesce(PaymentRefund.completed_at, PaymentRefund.created_at) < end,
        )
    )).scalar())

    return {
        "revenue": revenue, "refunds": refunds, "cogs": _q2(cogs), "orders_count": orders_count,
        "coverage": (qty_costed / qty_total) if qty_total else 1.0,
    }


async def _expense_block(db: AsyncSession, tenant_id: UUID, outlet: Outlet, start: datetime, end: datetime) -> dict:
    rows = (await db.execute(
        select(Expense.category, func.coalesce(func.sum(Expense.amount), 0), func.count(Expense.id))
        .where(
            Expense.tenant_id == tenant_id,
            Expense.deleted_at.is_(None),
            or_(Expense.outlet_id == outlet.id, Expense.outlet_id.is_(None)),
            Expense.paid_at >= start, Expense.paid_at < end,
        ).group_by(Expense.category)
    )).all()
    by_cat = {r[0]: (_q2(r[1]), int(r[2])) for r in rows}

    petty = (await db.execute(
        select(CashActivity.activity_type, func.coalesce(func.sum(CashActivity.amount), 0))
        .join(Shift, Shift.id == CashActivity.shift_id)
        .where(
            Shift.outlet_id == outlet.id,
            CashActivity.deleted_at.is_(None),
            CashActivity.created_at >= start, CashActivity.created_at < end,
        ).group_by(CashActivity.activity_type)
    )).all()
    petty_out = Decimal("0"); petty_in = Decimal("0")
    for t, amt in petty:
        tv = getattr(t, "value", t)
        if tv == "expense":
            petty_out += _q2(amt)
        else:
            petty_in += _q2(amt)

    total = sum((v[0] for v in by_cat.values()), Decimal("0"))
    return {"by_cat": by_cat, "total": _q2(total), "petty_out": petty_out, "petty_in": petty_in}


async def _cash_block(db: AsyncSession, tenant_id: UUID, outlet: Outlet, start: datetime, end: datetime,
                      accounts: list[CashAccount]) -> dict:
    flows: dict[Optional[UUID], dict] = {
        a.id: {"name": a.name, "kind": a.kind, "in": Decimal("0"), "out": Decimal("0")} for a in accounts
    }

    def add(acc: Optional[CashAccount], direction: str, amount: Decimal):
        key = acc.id if acc else None
        if key not in flows:
            flows[key] = {"name": acc.name if acc else "Tanpa akun", "kind": acc.kind if acc else "other",
                          "in": Decimal("0"), "out": Decimal("0")}
        flows[key][direction] += _q2(amount)

    # masuk: pembayaran lunas per metode
    pays = (await db.execute(
        select(Payment.payment_method, func.coalesce(func.sum(Payment.amount_paid - func.coalesce(Payment.change_amount, 0)), 0))
        .where(
            Payment.outlet_id == outlet.id, Payment.status == "paid", Payment.deleted_at.is_(None),
            func.coalesce(Payment.paid_at, Payment.created_at) >= start,
            func.coalesce(Payment.paid_at, Payment.created_at) < end,
        ).group_by(Payment.payment_method)
    )).all()
    for method, amt in pays:
        add(account_for_method(accounts, getattr(method, "value", method)), "in", amt)

    # keluar: refund (balik lewat metode yang sama)
    refs = (await db.execute(
        select(Payment.payment_method, func.coalesce(func.sum(PaymentRefund.amount), 0))
        .join(Payment, Payment.id == PaymentRefund.payment_id)
        .where(
            Payment.outlet_id == outlet.id, PaymentRefund.status == "completed", PaymentRefund.deleted_at.is_(None),
            func.coalesce(PaymentRefund.completed_at, PaymentRefund.created_at) >= start,
            func.coalesce(PaymentRefund.completed_at, PaymentRefund.created_at) < end,
        ).group_by(Payment.payment_method)
    )).all()
    for method, amt in refs:
        add(account_for_method(accounts, getattr(method, "value", method)), "out", amt)

    # keluar: pengeluaran (yang bukan dari nota — nota dihitung di bawah)
    exps = (await db.execute(
        select(Expense.cash_account_id, Expense.payment_method, func.coalesce(func.sum(Expense.amount), 0))
        .where(
            Expense.tenant_id == tenant_id, Expense.deleted_at.is_(None), Expense.purchase_id.is_(None),
            or_(Expense.outlet_id == outlet.id, Expense.outlet_id.is_(None)),
            Expense.paid_at >= start, Expense.paid_at < end,
        ).group_by(Expense.cash_account_id, Expense.payment_method)
    )).all()
    acc_by_id = {a.id: a for a in accounts}
    for acc_id, method, amt in exps:
        add(acc_by_id.get(acc_id) or account_for_method(accounts, method), "out", amt)

    # keluar: nota belanja yang dibayar (paid_amount di bulan nota diterima — pendekatan v1)
    purchases_paid = _q2((await db.execute(
        select(func.coalesce(func.sum(PurchaseOrder.paid_amount), 0)).where(
            PurchaseOrder.outlet_id == outlet.id, PurchaseOrder.deleted_at.is_(None),
            PurchaseOrder.status == "received",
            PurchaseOrder.received_at >= start, PurchaseOrder.received_at < end,
        )
    )).scalar())
    if purchases_paid > 0:
        add(account_for_method(accounts, "cash"), "out", purchases_paid)

    # kas kecil shift
    petty = (await db.execute(
        select(CashActivity.activity_type, func.coalesce(func.sum(CashActivity.amount), 0))
        .join(Shift, Shift.id == CashActivity.shift_id)
        .where(Shift.outlet_id == outlet.id, CashActivity.deleted_at.is_(None),
               CashActivity.created_at >= start, CashActivity.created_at < end)
        .group_by(CashActivity.activity_type)
    )).all()
    laci = account_for_method(accounts, "cash")
    for t, amt in petty:
        add(laci, "out" if getattr(t, "value", t) == "expense" else "in", amt)

    payables = _q2((await db.execute(
        select(func.coalesce(func.sum(PurchaseOrder.total_amount - PurchaseOrder.paid_amount), 0)).where(
            PurchaseOrder.outlet_id == outlet.id, PurchaseOrder.deleted_at.is_(None),
            PurchaseOrder.status == "received", PurchaseOrder.total_amount > PurchaseOrder.paid_amount,
        )
    )).scalar())

    out = []
    for key, f in flows.items():
        out.append(AccountFlow(id=key, name=f["name"], kind=f["kind"], inflow=_q2(f["in"]), outflow=_q2(f["out"]), net=_q2(f["in"] - f["out"])))
    cash_in = sum((f.inflow for f in out), Decimal("0")); cash_out = sum((f.outflow for f in out), Decimal("0"))
    return {"accounts": out, "in": _q2(cash_in), "out": _q2(cash_out), "purchases_paid": purchases_paid, "payables": payables}


# ───────────────────────── ringkasan ─────────────────────────

_ID_MONTHS = ["Jan", "Feb", "Mar", "Apr", "Mei", "Jun", "Jul", "Agu", "Sep", "Okt", "Nov", "Des"]


async def summary(db: AsyncSession, *, tenant_id: UUID, outlet: Outlet, month: str) -> FinanceSummary:
    start, end = month_bounds(month)
    accounts = await ensure_accounts(db, tenant_id)
    cost = await cost_map_for_brand(db, outlet.brand_id) if outlet.brand_id else {}

    pnl = await _pnl_block(db, outlet, start, end, cost)
    exp = await _expense_block(db, tenant_id, outlet, start, end)
    cash = await _cash_block(db, tenant_id, outlet, start, end, accounts)

    net_revenue = pnl["revenue"] - pnl["refunds"]
    gross = net_revenue - pnl["cogs"]
    beban = exp["total"] + exp["petty_out"]
    net = gross - beban

    by_cat = [
        CategoryAmount(key=k, label=CATEGORY_LABEL.get(k, k), amount=v[0], count=v[1])
        for k, v in sorted(exp["by_cat"].items(), key=lambda kv: -kv[1][0])
    ]

    # tren 6 bulan (termasuk bulan ini)
    trend: list[MonthPoint] = []
    y, m = (int(p) for p in month.split("-"))
    for i in range(5, -1, -1):
        mm = m - i; yy = y
        while mm <= 0:
            mm += 12; yy -= 1
        key = f"{yy:04d}-{mm:02d}"
        s, e = month_bounds(key)
        if key == month:
            p, x = pnl, exp
        else:
            p = await _pnl_block(db, outlet, s, e, cost)
            x = await _expense_block(db, tenant_id, outlet, s, e)
        rev = p["revenue"] - p["refunds"]; ex = x["total"] + x["petty_out"]
        trend.append(MonthPoint(month=key, label=_ID_MONTHS[mm - 1], revenue=_q2(rev), cogs=p["cogs"],
                                expenses=_q2(ex), net=_q2(rev - p["cogs"] - ex)))

    recurring_pending = await count_recurring_pending(db, tenant_id, outlet.id, month)

    return FinanceSummary(
        month=month, outlet_id=outlet.id,
        revenue=pnl["revenue"], refunds=pnl["refunds"], net_revenue=_q2(net_revenue),
        cogs=pnl["cogs"], cogs_coverage=round(float(pnl["coverage"]), 3),
        gross_profit=_q2(gross), gross_margin_pct=round(float(gross / net_revenue * 100), 1) if net_revenue else 0.0,
        expenses_total=exp["total"], expenses_by_category=by_cat, petty_cash_out=exp["petty_out"],
        net_profit=_q2(net), net_margin_pct=round(float(net / net_revenue * 100), 1) if net_revenue else 0.0,
        orders_count=pnl["orders_count"],
        cash_in=cash["in"], cash_out=cash["out"], cash_net=_q2(cash["in"] - cash["out"]),
        accounts=cash["accounts"], purchases_paid=cash["purchases_paid"], payables_outstanding=cash["payables"],
        trend=trend, recurring_pending=recurring_pending,
    )


# ───────────────────────── pengeluaran ─────────────────────────

def expense_to_response(e: Expense) -> ExpenseResponse:
    return ExpenseResponse(
        id=e.id, outlet_id=e.outlet_id, category=e.category, category_label=CATEGORY_LABEL.get(e.category, e.category),
        amount=e.amount, paid_at=e.paid_at, payment_method=e.payment_method,
        cash_account_id=e.cash_account_id, cash_account_name=e.cash_account.name if e.cash_account else None,
        supplier_id=e.supplier_id, supplier_name=e.supplier.name if e.supplier else None,
        purchase_id=e.purchase_id, note=e.note, photo_url=e.photo_url, recurring=e.recurring,
        row_version=e.row_version, created_at=e.created_at,
    )


async def list_expenses(db: AsyncSession, *, tenant_id: UUID, outlet_id: UUID, month: str) -> list[Expense]:
    start, end = month_bounds(month)
    return list((await db.execute(
        select(Expense)
        .options(selectinload(Expense.cash_account), selectinload(Expense.supplier))
        .where(
            Expense.tenant_id == tenant_id, Expense.deleted_at.is_(None),
            or_(Expense.outlet_id == outlet_id, Expense.outlet_id.is_(None)),
            Expense.paid_at >= start, Expense.paid_at < end,
        ).order_by(Expense.paid_at.desc(), Expense.created_at.desc())
    )).scalars().all())


async def count_recurring_pending(db: AsyncSession, tenant_id: UUID, outlet_id: UUID, month: str) -> int:
    """Template bulanan (recurring=monthly) bulan LALU yang belum ada padanannya bulan ini."""
    start, end = month_bounds(month)
    prev_end = start; prev_start = (start.astimezone(WIB) - timedelta(days=1)).replace(day=1).astimezone(timezone.utc)
    prev = (await db.execute(
        select(Expense).where(
            Expense.tenant_id == tenant_id, Expense.deleted_at.is_(None), Expense.recurring == "monthly",
            or_(Expense.outlet_id == outlet_id, Expense.outlet_id.is_(None)),
            Expense.paid_at >= prev_start, Expense.paid_at < prev_end,
        )
    )).scalars().all()
    if not prev:
        return 0
    cur = (await db.execute(
        select(Expense.category, Expense.note, Expense.amount).where(
            Expense.tenant_id == tenant_id, Expense.deleted_at.is_(None),
            or_(Expense.outlet_id == outlet_id, Expense.outlet_id.is_(None)),
            Expense.paid_at >= start, Expense.paid_at < end,
        )
    )).all()
    have = {(c, (n or "").strip().lower()) for c, n, _ in cur}
    return sum(1 for e in prev if (e.category, (e.note or "").strip().lower()) not in have)


async def copy_recurring(db: AsyncSession, *, tenant_id: UUID, outlet_id: UUID, month: str, user_id: UUID) -> list[Expense]:
    """Salin template bulanan dari bulan lalu ke bulan ini (yang belum ada)."""
    start, end = month_bounds(month)
    prev_end = start; prev_start = (start.astimezone(WIB) - timedelta(days=1)).replace(day=1).astimezone(timezone.utc)
    prev = (await db.execute(
        select(Expense).where(
            Expense.tenant_id == tenant_id, Expense.deleted_at.is_(None), Expense.recurring == "monthly",
            or_(Expense.outlet_id == outlet_id, Expense.outlet_id.is_(None)),
            Expense.paid_at >= prev_start, Expense.paid_at < prev_end,
        )
    )).scalars().all()
    cur = (await db.execute(
        select(Expense.category, Expense.note).where(
            Expense.tenant_id == tenant_id, Expense.deleted_at.is_(None),
            or_(Expense.outlet_id == outlet_id, Expense.outlet_id.is_(None)),
            Expense.paid_at >= start, Expense.paid_at < end,
        )
    )).all()
    have = {(c, (n or "").strip().lower()) for c, n in cur}
    created = []
    for e in prev:
        if (e.category, (e.note or "").strip().lower()) in have:
            continue
        # tanggal = hari yang sama di bulan ini (dibatasi 28), jam 09:00 WIB
        day = min(e.paid_at.astimezone(WIB).day, 28)
        s_wib = start.astimezone(WIB)
        paid_at = s_wib.replace(day=day, hour=9, minute=0, second=0, microsecond=0)
        if paid_at.astimezone(timezone.utc) > datetime.now(timezone.utc):
            paid_at = datetime.now(WIB)
        n = Expense(
            tenant_id=tenant_id, outlet_id=e.outlet_id, category=e.category, amount=e.amount,
            paid_at=paid_at.astimezone(timezone.utc), payment_method=e.payment_method,
            cash_account_id=e.cash_account_id, supplier_id=e.supplier_id, note=e.note,
            recurring="monthly", recorded_by=user_id,
        )
        db.add(n); created.append(n)
    await db.flush()
    return created


def guess_category(name: str) -> str:
    n = (name or "").lower()
    if any(k in n for k in ("gas", "elpiji", "lpg", "bensin", "solar")):
        return "gas"
    if any(k in n for k in ("plastik", "tisu", "tissue", "sabun", "sedotan", "cup", "gelas", "kantong", "kresek", "sendok")):
        return "perlengkapan"
    if any(k in n for k in ("parkir", "ongkir", "ojek", "grab", "gojek", "bensin")):
        return "transport"
    if any(k in n for k in ("listrik", "air", "pdam", "token")):
        return "listrik_air"
    return "lainnya"
