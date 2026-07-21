from typing import Any, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, model_validator
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from backend.core.database import get_db
from backend.api.deps import get_current_user
from backend.models.user import User
from backend.models.customer import Customer
from backend.schemas.response import StandardResponse
from backend.services.audit import log_audit

router = APIRouter()


class CustomerCreate(BaseModel):
    name: str
    phone: Optional[str] = None
    email: Optional[str] = None


class CustomerResponse(BaseModel):
    id: UUID
    name: str
    phone: Optional[str] = None
    email: Optional[str] = None

    class Config:
        from_attributes = True

    @model_validator(mode="after")
    def _mask(self):
        from backend.utils.phone import mask_phone
        self.phone = mask_phone(self.phone)
        return self


@router.get("/", response_model=StandardResponse[List[CustomerResponse]])
async def list_customers(
    request: Request,
    outlet_id: Optional[UUID] = None,
    search: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    query = select(Customer).where(
        Customer.tenant_id == current_user.tenant_id,
        Customer.deleted_at.is_(None),
    )
    if search:
        from sqlalchemy import or_
        query = query.where(
            or_(
                Customer.name.ilike(f"%{search}%"),
                Customer.phone.ilike(f"%{search}%"),
            )
        )
    query = query.order_by(Customer.name).offset(skip).limit(limit)
    result = await db.execute(query)
    customers = result.scalars().all()

    return StandardResponse(
        success=True,
        data=[CustomerResponse.model_validate(c) for c in customers],
        request_id=request.state.request_id,
    )


@router.post("/", response_model=StandardResponse[CustomerResponse])
async def create_customer(
    request: Request,
    customer_in: CustomerCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    # Cek duplikat phone
    if customer_in.phone:
        dup_stmt = select(Customer).where(
            Customer.tenant_id == current_user.tenant_id,
            Customer.phone == customer_in.phone,
            Customer.deleted_at.is_(None),
        )
        if (await db.execute(dup_stmt)).scalar_one_or_none():
            raise HTTPException(status_code=400, detail="Pelanggan dengan nomor HP ini sudah terdaftar")

    customer = Customer(
        tenant_id=current_user.tenant_id,
        name=customer_in.name,
        phone=customer_in.phone,
        email=customer_in.email,
        phone_hmac='',
    )
    db.add(customer)
    await db.commit()
    await db.refresh(customer)

    await log_audit(
        db=db,
        action="CREATE",
        entity="customer",
        entity_id=customer.id,
        after_state={"name": customer.name, "phone": customer.phone},
        user_id=current_user.id,
        tenant_id=current_user.tenant_id,
    )

    return StandardResponse(
        success=True,
        data=CustomerResponse.model_validate(customer),
        request_id=request.state.request_id,
        message="Pelanggan berhasil ditambahkan",
    )


# ── CRM: daftar + detail + riwayat ────────────────────────────────────────────
# Endpoint di bawah ini buat halaman Pelanggan di dashboard owner. Beda dari
# `list_customers` di atas yang dipakai POS buat milih pelanggan saat transaksi
# (ringkas + nomor disamarkan).
#
# Nomor HP di sini TIDAK disamarkan: pemiliknya sendiri yang lihat, dan tanpa
# nomor utuh halaman ini nggak ada gunanya — nggak bisa dihubungi, nggak bisa
# diekspor. Tetap tenant-scoped + wajib login.

class CustomerUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    notes: Optional[str] = None


def _summary(c: Customer) -> dict:
    return {
        "id": str(c.id),
        "name": c.name,
        "phone": c.phone,
        "email": c.email,
        "notes": c.notes,
        "total_visits": int(c.total_visits or 0),
        "total_spent": float(c.total_spent or 0),
        "avg_spent": (float(c.total_spent or 0) / c.total_visits) if c.total_visits else 0.0,
        "first_visit_at": c.first_visit_at.isoformat() if c.first_visit_at else None,
        "last_visit_at": c.last_visit_at.isoformat() if c.last_visit_at else None,
        "wa_marketing_consent": bool(c.wa_marketing_consent),
        "created_at": c.created_at.isoformat() if c.created_at else None,
    }


@router.get("/crm", response_model=StandardResponse)
async def crm_list(
    request: Request,
    search: Optional[str] = None,
    sort: str = "last_visit",   # last_visit | spent | visits | name | newest
    segment: Optional[str] = None,  # lapse | repeat | top | baru | belum_belanja
    skip: int = 0,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    """Daftar pelanggan + angka belanjanya, buat halaman Pelanggan di dashboard."""
    from sqlalchemy import or_, func as _f

    base = [Customer.tenant_id == current_user.tenant_id, Customer.deleted_at.is_(None)]
    if search:
        s = f"%{search}%"
        base.append(or_(Customer.name.ilike(s), Customer.phone.ilike(s), Customer.email.ilike(s)))

    # Segmen. Sengaja cuma lima dan semuanya bisa dijawab dari kolom yang udah
    # dihitung — nggak ada skoring RFM atau model apa pun. Yang dibutuhin pemilik
    # warung itu "siapa yang perlu disapa", bukan angka yang harus ditafsirkan.
    from datetime import datetime as _dt, timedelta as _td, timezone as _tz
    now = _dt.now(_tz.utc)
    if segment == "lapse":
        # Pernah belanja, tapi 30 hari terakhir nggak kelihatan.
        base += [Customer.total_visits > 0, Customer.last_visit_at < now - _td(days=30)]
    elif segment == "repeat":
        base.append(Customer.total_visits > 1)
    elif segment == "top":
        base.append(Customer.total_spent > 0)
    elif segment == "baru":
        # Kunjungan pertamanya dalam 30 hari terakhir — orang yang baru kenal.
        base += [Customer.first_visit_at.isnot(None),
                 Customer.first_visit_at >= now - _td(days=30)]
    elif segment == "belum_belanja":
        # Nomornya kesimpan tapi belum pernah ada transaksi lunas atas namanya.
        base.append(Customer.total_visits == 0)

    if segment == "top":
        sort = "spent"
    order_by = {
        "spent": Customer.total_spent.desc(),
        "visits": Customer.total_visits.desc(),
        "name": Customer.name.asc(),
        "newest": Customer.created_at.desc(),
    }.get(sort, Customer.last_visit_at.desc().nullslast())

    rows = (await db.execute(
        select(Customer).where(*base).order_by(order_by).offset(skip).limit(min(limit, 200))
    )).scalars().all()

    total = (await db.execute(
        select(_f.count(Customer.id)).where(*base)
    )).scalar() or 0

    agg = (await db.execute(
        select(
            _f.coalesce(_f.sum(Customer.total_spent), 0),
            _f.count(Customer.id).filter(Customer.total_visits > 1),
        ).where(*base)
    )).first()

    # Jumlah tiap segmen — dihitung tanpa filter segmen aktif, biar angka di
    # chip nggak ikut berubah waktu salah satu segmen lagi dipilih.
    scope = [Customer.tenant_id == current_user.tenant_id, Customer.deleted_at.is_(None)]
    counts_row = (await db.execute(
        select(
            _f.count(Customer.id).filter(
                Customer.total_visits > 0,
                Customer.last_visit_at < now - _td(days=30)),
            _f.count(Customer.id).filter(Customer.total_visits > 1),
            _f.count(Customer.id).filter(
                Customer.first_visit_at.isnot(None),
                Customer.first_visit_at >= now - _td(days=30)),
            _f.count(Customer.id).filter(Customer.total_visits == 0),
        ).where(*scope)
    )).first()

    return StandardResponse(
        success=True,
        data={
            "total": int(total),
            "total_spent_all": float(agg[0] or 0),
            "repeat_customers": int(agg[1] or 0),
            "segments": {
                "lapse": int(counts_row[0] or 0),
                "repeat": int(counts_row[1] or 0),
                "baru": int(counts_row[2] or 0),
                "belum_belanja": int(counts_row[3] or 0),
            },
            "items": [_summary(c) for c in rows],
        },
        request_id=request.state.request_id,
    )


@router.get("/{customer_id}/detail", response_model=StandardResponse)
async def customer_detail(
    request: Request,
    customer_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    """Detail pelanggan + riwayat belanjanya.

    Angkanya dihitung ulang saat dibuka (bukan dibaca dari kolom yang bisa
    melenceng), lalu hasilnya disimpan balik — jadi daftar ikut akurat pelan-pelan
    tanpa perlu backfill lagi.
    """
    from backend.services.customer_stats import refresh_customer, paid_orders_of_customer
    from backend.models.order import Order, OrderItem
    from sqlalchemy.orm import selectinload

    cust = (await db.execute(select(Customer).where(
        Customer.id == customer_id,
        Customer.tenant_id == current_user.tenant_id,
        Customer.deleted_at.is_(None),
    ))).scalar_one_or_none()
    if not cust:
        raise HTTPException(status_code=404, detail="Pelanggan tidak ditemukan")

    await refresh_customer(db, cust.id)
    await db.commit()
    await db.refresh(cust)

    orders = (await db.execute(
        paid_orders_of_customer(cust.id)
        .options(selectinload(Order.items).selectinload(OrderItem.product))
        .order_by(Order.created_at.desc())
        .limit(50)
    )).scalars().all()

    history = [{
        "id": str(o.id),
        "order_number": o.order_number,
        "created_at": o.created_at.isoformat() if o.created_at else None,
        "total_amount": float(o.total_amount or 0),
        "order_type": str(getattr(o.order_type, "value", o.order_type)),
        "items": [
            {"name": (it.product.name if it.product else "Item"), "qty": it.quantity}
            for it in (o.items or [])
        ],
    } for o in orders]

    # Menu yang paling sering dia beli — sinyal paling kepakai buat nawarin
    # sesuatu yang relevan pas orangnya mampir lagi.
    fav: dict = {}
    for o in orders:
        for it in (o.items or []):
            nm = it.product.name if it.product else None
            if nm:
                fav[nm] = fav.get(nm, 0) + (it.quantity or 0)
    favourites = sorted(fav.items(), key=lambda kv: kv[1], reverse=True)[:5]

    return StandardResponse(
        success=True,
        data={
            **_summary(cust),
            "orders": history,
            "favourites": [{"name": n, "qty": q} for n, q in favourites],
        },
        request_id=request.state.request_id,
    )


@router.put("/{customer_id}", response_model=StandardResponse)
async def update_customer(
    request: Request,
    customer_id: UUID,
    body: CustomerUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    cust = (await db.execute(select(Customer).where(
        Customer.id == customer_id,
        Customer.tenant_id == current_user.tenant_id,
        Customer.deleted_at.is_(None),
    ))).scalar_one_or_none()
    if not cust:
        raise HTTPException(status_code=404, detail="Pelanggan tidak ditemukan")

    before = {"name": cust.name, "email": cust.email, "notes": cust.notes}
    if body.name is not None and body.name.strip():
        cust.name = body.name.strip()
    if body.email is not None:
        cust.email = body.email.strip() or None
    if body.notes is not None:
        cust.notes = body.notes.strip() or None
    await db.commit()
    await db.refresh(cust)

    await log_audit(
        db=db, action="UPDATE", entity="customer", entity_id=cust.id,
        before_state=before,
        after_state={"name": cust.name, "email": cust.email, "notes": cust.notes},
        user_id=current_user.id, tenant_id=current_user.tenant_id,
    )
    return StandardResponse(
        success=True, data=_summary(cust),
        request_id=request.state.request_id, message="Pelanggan diperbarui",
    )


@router.post("/refresh-stats", response_model=StandardResponse)
async def refresh_stats(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    """Hitung ulang angka belanja semua pelanggan tenant ini.

    Dipakai sekali buat ngisi data lama (kolomnya nol semua sejak migrasi 009
    karena nggak pernah ada yang ngisi), dan bisa dipanggil lagi kapan aja kalau
    angkanya kelihatan meleset.
    """
    from backend.services.customer_stats import refresh_tenant
    n = await refresh_tenant(db, current_user.tenant_id)
    await db.commit()
    return StandardResponse(
        success=True, data={"updated": n},
        request_id=request.state.request_id,
        message=f"{n} pelanggan dihitung ulang",
    )
