"""Fresh tenant-wide customer facts, independent of cached CRM counters."""
from datetime import datetime, timedelta, timezone
from decimal import Decimal, ROUND_HALF_UP
from uuid import UUID
import re

from sqlalchemy import case, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.customer import Customer
from backend.models.order import Order
from backend.models.outlet import Outlet
from backend.services.crm_service import _paid_order_filter


def amount(value) -> str:
    return format(Decimal(str(value or 0)).quantize(Decimal(".01"), rounding=ROUND_HALF_UP), ".2f")


def canonical_phone_column():
    digits = func.regexp_replace(Customer.phone, "[^0-9]", "", "g")
    return case((digits.like("0%"), func.concat("62", func.substr(digits, 2))), else_=digits)


def paid_scope(tenant_id: UUID):
    return (
        Order.outlet_id.in_(select(Outlet.id).where(Outlet.tenant_id == tenant_id)),
        Order.deleted_at.is_(None), Order.status != "cancelled", _paid_order_filter(),
    )


def facts_query(tenant_id: UUID):
    stats = select(
        Order.customer_id.label("customer_id"), func.count(Order.id).label("visits"),
        func.sum(Order.total_amount).label("spent"), func.min(Order.created_at).label("first_at"),
        func.max(Order.created_at).label("last_at"),
    ).where(*paid_scope(tenant_id)).group_by(Order.customer_id).subquery()
    return select(Customer, func.coalesce(stats.c.visits, 0).label("visits"),
                  func.coalesce(stats.c.spent, 0).label("spent"), stats.c.first_at, stats.c.last_at).outerjoin(
        stats, stats.c.customer_id == Customer.id
    ).where(Customer.tenant_id == tenant_id, Customer.deleted_at.is_(None)), stats


def customer_out(c, visits=0, spent=0, first_at=None, last_at=None):
    return {
        "id": str(c.id), "name": c.name, "phone": c.phone or None, "email": c.email, "notes": c.notes,
        "birthday": c.birthday.isoformat() if c.birthday else None,
        "wa_marketing_consent": bool(c.wa_marketing_consent),
        "consent_given_at": c.consent_given_at.isoformat() if c.consent_given_at else None,
        "row_version": int(c.row_version or 0), "total_visits": int(visits), "total_spent": amount(spent),
        "avg_spent": amount(Decimal(str(spent)) / visits) if visits else "0.00",
        "first_visit_at": first_at.isoformat() if first_at else None,
        "last_visit_at": last_at.isoformat() if last_at else None,
    }


async def customer_facts(db: AsyncSession, tenant_id: UUID, customer_id: UUID):
    query, _ = facts_query(tenant_id)
    row = (await db.execute(query.where(Customer.id == customer_id))).first()
    return customer_out(*row) if row else None


async def list_facts(db: AsyncSession, tenant_id: UUID, search: str, segment: str, sort: str, skip: int, limit: int):
    now = datetime.now(timezone.utc)
    query, stats = facts_query(tenant_id)
    visits = func.coalesce(stats.c.visits, 0)
    if search.strip():
        pattern = "%" + search.strip().replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%"
        matches = [col.ilike(pattern, escape="\\") for col in (Customer.name, Customer.phone, Customer.email)]
        if re.fullmatch(r"[+0-9 ()-]+", search.strip()):
            digits = re.sub(r"\D", "", search)
            if digits.startswith("0"):
                digits = "62" + digits[1:]
            if len(digits) >= 3:
                matches.append(canonical_phone_column().ilike(f"%{digits}%"))
        query = query.where(or_(*matches))
    filters = {
        "repeat": visits > 1,
        "lapse": stats.c.last_at < now - timedelta(days=30),
        "new": stats.c.first_at >= now - timedelta(days=30),
        "unspent": visits == 0,
        "consent": Customer.wa_marketing_consent.is_(True) & Customer.phone.isnot(None) & (Customer.phone != ""),
    }
    if segment:
        query = query.where(filters[segment])
    order_by = {"name": func.lower(Customer.name), "spent": func.coalesce(stats.c.spent, 0).desc(),
                "visits": visits.desc(), "newest": Customer.created_at.desc(), "last_visit": stats.c.last_at.desc().nullslast()}[sort]
    filtered = query.subquery()
    count = await db.scalar(select(func.count()).select_from(filtered))
    rows = (await db.execute(query.order_by(order_by, Customer.id).offset(skip).limit(limit))).all()
    # Global summary deliberately stays independent of search and the selected segment.
    whole, _ = facts_query(tenant_id)
    source = whole.subquery()
    summary = (await db.execute(select(func.count(), func.count().filter(source.c.visits > 1),
        func.coalesce(func.sum(source.c.spent), 0),
        func.count().filter(source.c.wa_marketing_consent.is_(True), source.c.phone.isnot(None), source.c.phone != ""),
    ).select_from(source))).one()
    return {"items": [customer_out(*row) for row in rows], "total": int(count), "skip": skip, "limit": limit,
            "summary": {"total": summary[0], "repeat": summary[1], "spent": amount(summary[2]), "consented": summary[3]},
            "generated_at": now.isoformat(), "scope": "tenant_all_outlets", "timezone": "Asia/Jakarta",
            "basis": "paid_orders_gross", "history_note": "Nilai nota berstatus lunas, sebelum pengurangan refund. Satu nota dihitung satu transaksi."}
