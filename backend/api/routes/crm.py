"""
/crm — gelombang 3 sisi data (semua tier).

  GET  /crm/segments/summary            hitung per segmen (auto-refresh kalau > 6 jam)
  POST /crm/segments/refresh            paksa hitung ulang
  GET/POST /crm/tags · DELETE /crm/tags/{id}
  PUT  /crm/customers/{id}/tags         {tag_ids: [...]}  (daftar final)
  GET  /crm/customers/{id}/timeline · POST /crm/customers/{id}/notes
  PUT  /crm/customers/{id}/profile      {birthday?, wa_marketing_consent?}
  GET/POST/PUT/DELETE /crm/vouchers
  POST /crm/vouchers/validate           {code, customer_id?, subtotal} → discount
  POST /crm/vouchers/redeem             {code, order_id?, customer_id?, subtotal}
"""
import logging
from datetime import datetime, timezone, date
from decimal import Decimal, ROUND_HALF_UP
from typing import Any, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy import select, func, delete
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api import deps
from backend.core.database import get_db
from backend.models.user import User
from backend.models.customer import Customer
from backend.models.crm import (
    CustomerTag, CustomerTagLink, CustomerTimeline, Voucher, VoucherRedemption,
    SEGMENT_KEYS, TAG_COLORS, TIMELINE_KINDS,
)
from backend.schemas.response import StandardResponse
from backend.services.audit import log_audit
from backend.services import crm_service as svc

logger = logging.getLogger(__name__)
router = APIRouter()
_Q2 = Decimal("0.01")


def _q2(x) -> Decimal:
    return Decimal(str(x or 0)).quantize(_Q2, rounding=ROUND_HALF_UP)


async def _customer(db: AsyncSession, customer_id: UUID, tenant_id: UUID) -> Customer:
    c = (await db.execute(select(Customer).where(
        Customer.id == customer_id, Customer.tenant_id == tenant_id, Customer.deleted_at.is_(None)
    ))).scalar_one_or_none()
    if not c:
        raise HTTPException(status_code=404, detail="Pelanggan tidak ditemukan")
    return c


# ───────────────────────── segmen ─────────────────────────

@router.get("/segments/summary", response_model=StandardResponse[list])
async def segments_summary(request: Request, db: AsyncSession = Depends(get_db), current_user: User = Depends(deps.get_current_user)) -> Any:
    if await svc.needs_refresh(db, current_user.tenant_id):
        await svc.refresh_segments(db, current_user.tenant_id)
        await db.commit()
    data = await svc.segment_summary(db, current_user.tenant_id)
    return StandardResponse(success=True, data=data, request_id=request.state.request_id)


@router.post("/segments/refresh", response_model=StandardResponse[dict])
async def segments_refresh(request: Request, db: AsyncSession = Depends(get_db), current_user: User = Depends(deps.get_current_user)) -> Any:
    res = await svc.refresh_segments(db, current_user.tenant_id)
    await db.commit()
    return StandardResponse(success=True, data=res, message=f"{res['total']} pelanggan dihitung ulang", request_id=request.state.request_id)


# ───────────────────────── tag ─────────────────────────

class TagIn(BaseModel):
    name: str = Field(..., min_length=1, max_length=40)
    color: str = "violet"


@router.get("/tags", response_model=StandardResponse[list])
async def list_tags(request: Request, db: AsyncSession = Depends(get_db), current_user: User = Depends(deps.get_current_user)) -> Any:
    rows = (await db.execute(
        select(CustomerTag, func.count(CustomerTagLink.id))
        .outerjoin(CustomerTagLink, CustomerTagLink.tag_id == CustomerTag.id)
        .where(CustomerTag.tenant_id == current_user.tenant_id, CustomerTag.deleted_at.is_(None))
        .group_by(CustomerTag.id).order_by(CustomerTag.name)
    )).all()
    return StandardResponse(success=True, data=[
        {"id": str(t.id), "name": t.name, "color": t.color, "count": int(n), "row_version": t.row_version} for t, n in rows
    ], request_id=request.state.request_id)


@router.post("/tags", response_model=StandardResponse[dict])
async def create_tag(request: Request, body: TagIn, db: AsyncSession = Depends(get_db), current_user: User = Depends(deps.get_current_user)) -> Any:
    color = body.color if body.color in TAG_COLORS else "violet"
    dup = (await db.execute(select(CustomerTag).where(
        CustomerTag.tenant_id == current_user.tenant_id, CustomerTag.deleted_at.is_(None),
        func.lower(CustomerTag.name) == body.name.strip().lower(),
    ))).scalar_one_or_none()
    if dup:
        return StandardResponse(success=True, data={"id": str(dup.id), "name": dup.name, "color": dup.color}, request_id=request.state.request_id)
    t = CustomerTag(tenant_id=current_user.tenant_id, name=body.name.strip(), color=color)
    db.add(t); await db.commit(); await db.refresh(t)
    return StandardResponse(success=True, data={"id": str(t.id), "name": t.name, "color": t.color}, message="Tag dibuat", request_id=request.state.request_id)


@router.delete("/tags/{tag_id}", response_model=StandardResponse[dict])
async def delete_tag(request: Request, tag_id: UUID, db: AsyncSession = Depends(get_db), current_user: User = Depends(deps.get_current_user)) -> Any:
    t = (await db.execute(select(CustomerTag).where(CustomerTag.id == tag_id, CustomerTag.tenant_id == current_user.tenant_id, CustomerTag.deleted_at.is_(None)))).scalar_one_or_none()
    if not t:
        raise HTTPException(status_code=404, detail="Tag tidak ditemukan")
    t.deleted_at = datetime.now(timezone.utc)
    await db.execute(delete(CustomerTagLink).where(CustomerTagLink.tag_id == t.id))
    await db.commit()
    return StandardResponse(success=True, data={"ok": True}, message="Tag dihapus", request_id=request.state.request_id)


class CustomerTagsIn(BaseModel):
    tag_ids: List[UUID]


@router.put("/customers/{customer_id}/tags", response_model=StandardResponse[list])
async def set_customer_tags(request: Request, customer_id: UUID, body: CustomerTagsIn, db: AsyncSession = Depends(get_db), current_user: User = Depends(deps.get_current_user)) -> Any:
    c = await _customer(db, customer_id, current_user.tenant_id)
    valid = set((await db.execute(select(CustomerTag.id).where(
        CustomerTag.tenant_id == current_user.tenant_id, CustomerTag.deleted_at.is_(None), CustomerTag.id.in_(body.tag_ids or [UUID(int=0)])
    ))).scalars().all())
    await db.execute(delete(CustomerTagLink).where(CustomerTagLink.customer_id == c.id))
    for tid in valid:
        db.add(CustomerTagLink(tenant_id=current_user.tenant_id, customer_id=c.id, tag_id=tid))
    await db.commit()
    rows = (await db.execute(select(CustomerTag).where(CustomerTag.id.in_(valid) if valid else False))).scalars().all()
    return StandardResponse(success=True, data=[{"id": str(t.id), "name": t.name, "color": t.color} for t in rows], request_id=request.state.request_id)


# ───────────────────────── timeline / profil ─────────────────────────

class NoteIn(BaseModel):
    body: str = Field(..., min_length=1, max_length=500)
    kind: str = "note"


@router.get("/customers/{customer_id}/timeline", response_model=StandardResponse[dict])
async def customer_timeline(request: Request, customer_id: UUID, db: AsyncSession = Depends(get_db), current_user: User = Depends(deps.get_current_user)) -> Any:
    c = await _customer(db, customer_id, current_user.tenant_id)
    rows = (await db.execute(
        select(CustomerTimeline).where(CustomerTimeline.customer_id == c.id, CustomerTimeline.deleted_at.is_(None))
        .order_by(CustomerTimeline.created_at.desc()).limit(100)
    )).scalars().all()
    tags = (await db.execute(
        select(CustomerTag).join(CustomerTagLink, CustomerTagLink.tag_id == CustomerTag.id)
        .where(CustomerTagLink.customer_id == c.id, CustomerTag.deleted_at.is_(None))
    )).scalars().all()
    return StandardResponse(success=True, data={
        "customer": {
            "id": str(c.id), "name": c.name, "segment": c.segment, "segment_label": svc.SEGMENT_LABEL.get(c.segment or "", None),
            "rfm_recency_days": c.rfm_recency_days, "rfm_frequency_90d": c.rfm_frequency_90d,
            "rfm_monetary_90d": str(c.rfm_monetary_90d or 0), "birthday": c.birthday.isoformat() if c.birthday else None,
            "wa_marketing_consent": bool(c.wa_marketing_consent), "favorite_product_id": str(c.favorite_product_id) if c.favorite_product_id else None,
            "total_visits": c.total_visits, "total_spent": str(c.total_spent or 0), "last_visit_at": c.last_visit_at.isoformat() if c.last_visit_at else None,
        },
        "tags": [{"id": str(t.id), "name": t.name, "color": t.color} for t in tags],
        "timeline": [{"id": str(r.id), "kind": r.kind, "body": r.body, "created_at": r.created_at.isoformat()} for r in rows],
    }, request_id=request.state.request_id)


@router.post("/customers/{customer_id}/notes", response_model=StandardResponse[dict])
async def add_note(request: Request, customer_id: UUID, body: NoteIn, db: AsyncSession = Depends(get_db), current_user: User = Depends(deps.get_current_user)) -> Any:
    c = await _customer(db, customer_id, current_user.tenant_id)
    kind = body.kind if body.kind in TIMELINE_KINDS else "note"
    n = CustomerTimeline(tenant_id=current_user.tenant_id, customer_id=c.id, kind=kind, body=body.body.strip(), created_by=current_user.id)
    db.add(n); await db.commit(); await db.refresh(n)
    return StandardResponse(success=True, data={"id": str(n.id), "kind": n.kind, "body": n.body, "created_at": n.created_at.isoformat()}, message="Catatan disimpan", request_id=request.state.request_id)


class ProfileIn(BaseModel):
    birthday: Optional[date] = None
    wa_marketing_consent: Optional[bool] = None


@router.put("/customers/{customer_id}/profile", response_model=StandardResponse[dict])
async def update_profile(request: Request, customer_id: UUID, body: ProfileIn, db: AsyncSession = Depends(get_db), current_user: User = Depends(deps.get_current_user)) -> Any:
    c = await _customer(db, customer_id, current_user.tenant_id)
    changes = body.model_dump(exclude_unset=True)
    if "birthday" in changes:
        c.birthday = changes["birthday"]
    if "wa_marketing_consent" in changes and changes["wa_marketing_consent"] is not None:
        c.wa_marketing_consent = changes["wa_marketing_consent"]
        c.consent_given_at = datetime.now(timezone.utc) if changes["wa_marketing_consent"] else None
        c.consent_source = "profile"
        db.add(CustomerTimeline(tenant_id=current_user.tenant_id, customer_id=c.id, kind="consent",
                                body=("Setuju dikirimi promo WA" if changes["wa_marketing_consent"] else "Berhenti menerima promo WA"),
                                created_by=current_user.id))
    c.row_version = (c.row_version or 0) + 1
    await log_audit(db=db, action="UPDATE", entity="customers", entity_id=c.id, after_state={k: str(v) for k, v in changes.items()},
                    user_id=current_user.id, tenant_id=current_user.tenant_id)
    await db.commit()
    return StandardResponse(success=True, data={"ok": True}, message="Profil diperbarui", request_id=request.state.request_id)


# ───────────────────────── voucher ─────────────────────────

class VoucherIn(BaseModel):
    code: str = Field(..., min_length=3, max_length=32)
    name: Optional[str] = Field(None, max_length=80)
    kind: str = "percent"
    value: Decimal = Field(..., gt=0)
    max_discount: Optional[Decimal] = Field(None, gt=0)
    min_purchase: Decimal = Field(Decimal("0"), ge=0)
    valid_from: Optional[datetime] = None
    valid_until: Optional[datetime] = None
    quota_total: Optional[int] = Field(None, ge=1)
    quota_per_customer: Optional[int] = Field(None, ge=1)
    segment: Optional[str] = None
    is_active: bool = True


class VoucherUpdate(VoucherIn):
    code: Optional[str] = Field(None, min_length=3, max_length=32)
    value: Optional[Decimal] = Field(None, gt=0)
    row_version: int


def _voucher_out(v: Voucher, used: int = 0) -> dict:
    return {
        "id": str(v.id), "code": v.code, "name": v.name, "kind": v.kind, "value": str(v.value),
        "max_discount": str(v.max_discount) if v.max_discount is not None else None, "min_purchase": str(v.min_purchase or 0),
        "valid_from": v.valid_from.isoformat() if v.valid_from else None, "valid_until": v.valid_until.isoformat() if v.valid_until else None,
        "quota_total": v.quota_total, "quota_per_customer": v.quota_per_customer, "segment": v.segment,
        "is_active": v.is_active, "used_count": used, "row_version": v.row_version, "created_at": v.created_at.isoformat(),
    }


@router.get("/vouchers", response_model=StandardResponse[list])
async def list_vouchers(request: Request, db: AsyncSession = Depends(get_db), current_user: User = Depends(deps.get_current_user)) -> Any:
    rows = (await db.execute(
        select(Voucher, func.count(VoucherRedemption.id))
        .outerjoin(VoucherRedemption, VoucherRedemption.voucher_id == Voucher.id)
        .where(Voucher.tenant_id == current_user.tenant_id, Voucher.deleted_at.is_(None))
        .group_by(Voucher.id).order_by(Voucher.created_at.desc())
    )).all()
    return StandardResponse(success=True, data=[_voucher_out(v, int(n)) for v, n in rows], request_id=request.state.request_id)


@router.post("/vouchers", response_model=StandardResponse[dict])
async def create_voucher(request: Request, body: VoucherIn, db: AsyncSession = Depends(get_db), current_user: User = Depends(deps.get_current_user)) -> Any:
    code = body.code.strip().upper().replace(" ", "")
    if body.kind not in ("percent", "amount"):
        raise HTTPException(status_code=400, detail="kind harus percent / amount")
    if body.kind == "percent" and body.value > 100:
        raise HTTPException(status_code=400, detail="Diskon persen maksimal 100")
    if body.segment and body.segment not in SEGMENT_KEYS:
        raise HTTPException(status_code=400, detail="Segmen tidak dikenal")
    dup = (await db.execute(select(Voucher).where(Voucher.tenant_id == current_user.tenant_id, Voucher.code == code, Voucher.deleted_at.is_(None)))).scalar_one_or_none()
    if dup:
        raise HTTPException(status_code=400, detail=f"Kode {code} sudah dipakai")
    v = Voucher(tenant_id=current_user.tenant_id, **{**body.model_dump(), "code": code})
    db.add(v); await db.commit(); await db.refresh(v)
    await log_audit(db=db, action="CREATE", entity="vouchers", entity_id=v.id, after_state={"code": code, "kind": v.kind, "value": str(v.value)}, user_id=current_user.id, tenant_id=current_user.tenant_id)
    await db.commit()
    return StandardResponse(success=True, data=_voucher_out(v), message=f"Voucher {code} dibuat", request_id=request.state.request_id)


@router.put("/vouchers/{voucher_id}", response_model=StandardResponse[dict])
async def update_voucher(request: Request, voucher_id: UUID, body: VoucherUpdate, db: AsyncSession = Depends(get_db), current_user: User = Depends(deps.get_current_user)) -> Any:
    v = (await db.execute(select(Voucher).where(Voucher.id == voucher_id, Voucher.tenant_id == current_user.tenant_id, Voucher.deleted_at.is_(None)))).scalar_one_or_none()
    if not v:
        raise HTTPException(status_code=404, detail="Voucher tidak ditemukan")
    if v.row_version != body.row_version:
        raise HTTPException(status_code=409, detail="Voucher sudah berubah, muat ulang")
    changes = body.model_dump(exclude_unset=True, exclude={"row_version"})
    if "code" in changes and changes["code"]:
        changes["code"] = changes["code"].strip().upper().replace(" ", "")
    for k, val in changes.items():
        setattr(v, k, val)
    v.row_version += 1
    await db.commit(); await db.refresh(v)
    return StandardResponse(success=True, data=_voucher_out(v), message="Voucher diperbarui", request_id=request.state.request_id)


@router.delete("/vouchers/{voucher_id}", response_model=StandardResponse[dict])
async def delete_voucher(request: Request, voucher_id: UUID, db: AsyncSession = Depends(get_db), current_user: User = Depends(deps.get_current_user)) -> Any:
    v = (await db.execute(select(Voucher).where(Voucher.id == voucher_id, Voucher.tenant_id == current_user.tenant_id, Voucher.deleted_at.is_(None)))).scalar_one_or_none()
    if not v:
        raise HTTPException(status_code=404, detail="Voucher tidak ditemukan")
    v.deleted_at = datetime.now(timezone.utc); v.is_active = False; v.row_version += 1
    await db.commit()
    return StandardResponse(success=True, data={"ok": True}, message="Voucher dihapus", request_id=request.state.request_id)


class VoucherCheck(BaseModel):
    code: str
    customer_id: Optional[UUID] = None
    subtotal: Decimal = Field(..., ge=0)
    order_id: Optional[UUID] = None


async def _evaluate(db: AsyncSession, tenant_id: UUID, body: VoucherCheck) -> tuple[Voucher, Decimal]:
    code = body.code.strip().upper()
    v = (await db.execute(select(Voucher).where(Voucher.tenant_id == tenant_id, Voucher.code == code, Voucher.deleted_at.is_(None)))).scalar_one_or_none()
    if not v or not v.is_active:
        raise HTTPException(status_code=404, detail="Kode voucher tidak ditemukan / nonaktif")
    now = datetime.now(timezone.utc)
    if v.valid_from and now < v.valid_from:
        raise HTTPException(status_code=400, detail="Voucher belum berlaku")
    if v.valid_until and now > v.valid_until:
        raise HTTPException(status_code=400, detail="Voucher sudah kedaluwarsa")
    if body.subtotal < (v.min_purchase or 0):
        raise HTTPException(status_code=400, detail=f"Minimal belanja Rp {int(v.min_purchase):,}".replace(",", "."))
    if v.quota_total is not None:
        used = (await db.execute(select(func.count(VoucherRedemption.id)).where(VoucherRedemption.voucher_id == v.id))).scalar() or 0
        if used >= v.quota_total:
            raise HTTPException(status_code=400, detail="Kuota voucher habis")
    if body.customer_id:
        cust = (await db.execute(select(Customer).where(Customer.id == body.customer_id, Customer.tenant_id == tenant_id))).scalar_one_or_none()
        if v.segment and (not cust or cust.segment != v.segment):
            raise HTTPException(status_code=400, detail="Voucher ini khusus pelanggan segmen tertentu")
        if v.quota_per_customer is not None:
            used_c = (await db.execute(select(func.count(VoucherRedemption.id)).where(
                VoucherRedemption.voucher_id == v.id, VoucherRedemption.customer_id == body.customer_id))).scalar() or 0
            if used_c >= v.quota_per_customer:
                raise HTTPException(status_code=400, detail="Pelanggan ini sudah pakai voucher ini")
    elif v.segment:
        raise HTTPException(status_code=400, detail="Voucher khusus segmen — pilih pelanggan dulu")
    if v.kind == "percent":
        disc = body.subtotal * Decimal(str(v.value)) / Decimal("100")
        if v.max_discount is not None:
            disc = min(disc, Decimal(str(v.max_discount)))
    else:
        disc = Decimal(str(v.value))
    disc = min(_q2(disc), _q2(body.subtotal))
    return v, disc


@router.post("/vouchers/validate", response_model=StandardResponse[dict])
async def validate_voucher(request: Request, body: VoucherCheck, db: AsyncSession = Depends(get_db), current_user: User = Depends(deps.get_current_user)) -> Any:
    v, disc = await _evaluate(db, current_user.tenant_id, body)
    return StandardResponse(success=True, data={"voucher_id": str(v.id), "code": v.code, "name": v.name, "discount_amount": str(disc)}, request_id=request.state.request_id)


@router.post("/vouchers/redeem", response_model=StandardResponse[dict])
async def redeem_voucher(request: Request, body: VoucherCheck, db: AsyncSession = Depends(get_db), current_user: User = Depends(deps.get_current_user)) -> Any:
    v, disc = await _evaluate(db, current_user.tenant_id, body)
    r = VoucherRedemption(tenant_id=current_user.tenant_id, voucher_id=v.id, customer_id=body.customer_id, order_id=body.order_id, discount_amount=disc)
    db.add(r)
    if body.customer_id:
        db.add(CustomerTimeline(tenant_id=current_user.tenant_id, customer_id=body.customer_id, kind="voucher_used",
                                ref_id=v.id, body=f"Pakai voucher {v.code} (−Rp {int(disc):,})".replace(",", "."), created_by=current_user.id))
    await db.commit()
    return StandardResponse(success=True, data={"voucher_id": str(v.id), "code": v.code, "discount_amount": str(disc)}, message="Voucher dipakai", request_id=request.state.request_id)
