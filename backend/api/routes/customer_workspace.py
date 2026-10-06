import hashlib
import hmac
import json
from datetime import datetime, timezone
from typing import Literal
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import selectinload

from backend.api.deps import get_current_user
from backend.core.database import get_db
from backend.models.audit_log import AuditLog
from backend.models.customer import Customer
from backend.models.crm import CustomerTimeline
from backend.models.order import Order, OrderItem
from backend.models.product import Product
from backend.models.user import User
from backend.schemas.customer_workspace import CustomerSave, CustomerNote
from backend.schemas.response import StandardResponse
from backend.services import customer_workspace as svc

from backend.services.pos_access import PosAccessRoute
router = APIRouter(route_class=PosAccessRoute)


def access_metadata(request):
    context = getattr(request.state, "access", None)
    managed = context is not None and context.mode == "managed"
    return {"can_manage": not managed or context.allows("customers.manage"),
            "can_export": not managed or context.allows("customers.export"),
            "scope": "allowed_outlets" if managed else "tenant_all_outlets"}


def allowed_outlets(request):
    context = getattr(request.state, "access", None)
    return context.outlet_ids if context and context.mode == "managed" else None


def response(request, data, message=None):
    return StandardResponse(success=True, data=data, message=message, request_id=request.state.request_id)


async def customer(db, tenant_id, customer_id, lock=False):
    query = select(Customer).where(Customer.id == customer_id, Customer.tenant_id == tenant_id, Customer.deleted_at.is_(None))
    if lock:
        query = query.with_for_update().execution_options(populate_existing=True)
    c = await db.scalar(query)
    if not c:
        raise HTTPException(404, "Pelanggan tidak ditemukan")
    return c


async def replay(db, user, body, action, customer_id=None):
    fingerprint = hashlib.sha256(json.dumps({"action": action, "customer": str(customer_id), "user": str(user.id),
        "body": body.model_dump(mode="json")}, sort_keys=True).encode()).hexdigest()
    await db.execute(text("SELECT pg_advisory_xact_lock(hashtextextended(:key, 0))"),
                     {"key": f"customer-request:{user.tenant_id}:{body.client_request_id}"})
    existing = await db.scalar(select(AuditLog).where(AuditLog.tenant_id == user.tenant_id,
        AuditLog.entity == "customer_workspace", AuditLog.after_state["client_request_id"].astext == str(body.client_request_id)))
    if existing:
        if existing.after_state.get("fingerprint") != fingerprint:
            raise HTTPException(409, "Permintaan ini sudah dipakai dengan data berbeda")
        return fingerprint, existing.after_state["result"]
    return fingerprint, None


def audit(db, request, user, body, fingerprint, action, entity_id, result):
    db.add(AuditLog(tenant_id=user.tenant_id, user_id=user.id, action=action, entity="customer_workspace",
        entity_id=entity_id, request_id=request.state.request_id,
        after_state={"client_request_id": str(body.client_request_id), "fingerprint": fingerprint, "result": result}))


@router.get("")
async def listing(request: Request, search: str = Query("", max_length=120),
                  segment: Literal["", "repeat", "lapse", "new", "unspent", "consent"] = "",
                  sort: Literal["last_visit", "spent", "visits", "newest", "name"] = "last_visit",
                  skip: int = Query(0, ge=0), limit: int = Query(50, ge=1, le=200),
                  db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    data = await svc.list_facts(db, user.tenant_id, search, segment, sort, skip, limit, allowed_outlets(request))
    data.update(access_metadata(request))
    data["workspace_key"] = hashlib.sha256(f"{user.tenant_id}:{user.id}".encode()).hexdigest()
    return response(request, data)


@router.get("/{customer_id}")
async def detail(request: Request, customer_id: UUID, skip: int = Query(0, ge=0),
                 db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    c = await customer(db, user.tenant_id, customer_id)
    facts = await svc.customer_facts(db, user.tenant_id, c.id, allowed_outlets(request))
    query = select(Order).where(Order.customer_id == c.id, *svc.paid_scope(user.tenant_id, allowed_outlets(request)))
    orders = (await db.execute(query.options(selectinload(Order.items).selectinload(OrderItem.product))
               .order_by(Order.created_at.desc(), Order.id).offset(skip).limit(20))).scalars().all()
    timeline = (await db.execute(select(CustomerTimeline).where(CustomerTimeline.customer_id == c.id,
        CustomerTimeline.tenant_id == user.tenant_id, CustomerTimeline.deleted_at.is_(None))
        .order_by(CustomerTimeline.created_at.desc(), CustomerTimeline.id).limit(100))).scalars().all()
    favourites = (await db.execute(select(Product.id, Product.name, func.sum(OrderItem.quantity))
        .join(OrderItem, OrderItem.product_id == Product.id).join(Order, Order.id == OrderItem.order_id)
        .where(Order.customer_id == c.id, *svc.paid_scope(user.tenant_id, allowed_outlets(request)), OrderItem.deleted_at.is_(None))
        .group_by(Product.id, Product.name).order_by(func.sum(OrderItem.quantity).desc(), Product.id).limit(5))).all()
    return response(request, {**facts, "orders": [{"id": str(o.id), "order_number": o.order_number,
        "created_at": o.created_at.isoformat(), "total_amount": svc.amount(o.total_amount),
        "items": [{"name": it.product_name or "Produk tidak tersedia", "qty": it.quantity}
                  for it in o.items if it.deleted_at is None]} for o in orders],
        "history_skip": skip, "history_limit": 20,
        "favourites": [{"id": str(pid), "name": name, "qty": int(qty)} for pid, name, qty in favourites],
        "timeline": [{"id": str(n.id), "kind": n.kind, "body": n.body, "created_at": n.created_at.isoformat()} for n in timeline],
        "timeline_limit": 100, "generated_at": datetime.now(timezone.utc).isoformat(),
        **access_metadata(request), "basis": "paid_orders_gross"})


async def save(request, body, db, user, customer_id=None):
    if customer_id and body.row_version is None:
        raise HTTPException(422, "Versi profil diperlukan. Muat ulang profil dahulu")
    fingerprint, result = await replay(db, user, body, "UPDATE" if customer_id else "CREATE", customer_id)
    if result:
        return response(request, result, "Permintaan sudah tersimpan")
    c = await customer(db, user.tenant_id, customer_id, lock=True) if customer_id else Customer(id=uuid4(), tenant_id=user.tenant_id)
    if customer_id and (c.row_version or 0) != body.row_version:
        raise HTTPException(409, "Profil sudah berubah. Muat ulang sebelum menyimpan")
    if body.wa_marketing_consent and not body.phone:
        raise HTTPException(400, "Isi nomor HP sebelum mencatat persetujuan promo")
    if body.phone:
        await db.execute(text("SELECT pg_advisory_xact_lock(hashtextextended(:key, 0))"),
                         {"key": f"customer-phone:{user.tenant_id}:{body.phone}"})
        duplicate = await db.scalar(select(Customer.id).where(Customer.tenant_id == user.tenant_id,
                                    svc.canonical_phone_column() == body.phone, Customer.id != c.id).limit(1))
        if duplicate:
            raise HTTPException(409, "Nomor HP ini sudah tercatat. Gunakan profil yang sudah ada")
    old_consent = bool(c.wa_marketing_consent)
    old_phone = c.phone
    for key, value in body.model_dump(exclude={"client_request_id", "row_version"}).items():
        setattr(c, key, value)
    # Existing schema requires a string even when the profile has no phone.
    c.phone = c.phone or ""
    c.phone_hmac = hmac.new(b"kasira-phone-key", (c.phone or f"no-phone:{c.id}").encode(), hashlib.sha256).hexdigest()
    if not customer_id:
        db.add(c)
        try:
            await db.flush()
        except IntegrityError:
            await db.rollback()
            raise HTTPException(409, "Kontak ini sudah tercatat. Muat ulang daftar pelanggan")
    if old_consent != c.wa_marketing_consent or old_phone != c.phone:
        c.consent_given_at = datetime.now(timezone.utc) if c.wa_marketing_consent else None
        c.consent_source = "profile"
        db.add(CustomerTimeline(tenant_id=user.tenant_id, customer_id=c.id, kind="consent",
            body="Persetujuan promo WhatsApp dicatat oleh pengguna" if c.wa_marketing_consent else "Tidak menerima promo WhatsApp",
            created_by=user.id))
    c.row_version = (c.row_version or 0) + 1
    c.segment_updated_at = None
    try:
        await db.flush()
        result = {"id": str(c.id), "row_version": c.row_version}
        audit(db, request, user, body, fingerprint, "UPDATE" if customer_id else "CREATE", c.id, result)
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(409, "Kontak ini sudah tercatat. Muat ulang daftar pelanggan")
    return response(request, result, "Profil pelanggan disimpan")


@router.post("")
async def create(request: Request, body: CustomerSave, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    return await save(request, body, db, user)


@router.put("/{customer_id}")
async def update(request: Request, customer_id: UUID, body: CustomerSave, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    return await save(request, body, db, user, customer_id)


@router.post("/{customer_id}/notes")
async def note(request: Request, customer_id: UUID, body: CustomerNote, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    c = await customer(db, user.tenant_id, customer_id)
    fingerprint, result = await replay(db, user, body, "NOTE", c.id)
    if result:
        return response(request, result, "Catatan sudah tersimpan")
    n = CustomerTimeline(id=uuid4(), tenant_id=user.tenant_id, customer_id=c.id, body=body.body,
                         kind=body.kind, created_by=user.id)
    db.add(n)
    result = {"id": str(n.id)}
    audit(db, request, user, body, fingerprint, "NOTE", c.id, result)
    await db.commit()
    return response(request, result, "Catatan pelanggan disimpan")
