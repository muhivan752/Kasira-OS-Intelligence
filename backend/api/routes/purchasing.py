"""
Purchasing — /suppliers + /purchases (nota belanja).

Semua tier. Yang Pro-only cuma BARIS BAHAN BAKU di nota (dicek di service),
karena ingredients router-nya sendiri udah Pro. Tenant Starter tetap bisa
nyatet nota produk jadi + utang supplier — itu justru yang mereka butuhin
(mayoritas Starter non-F&B).
"""
import logging
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from typing import Any, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select, func, update, false
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.api import deps
from backend.core.database import get_db
from backend.models.user import User
from backend.models.tenant import Tenant
from backend.models.outlet import Outlet
from backend.models.purchasing import Supplier, PurchaseOrder, PurchaseOrderItem
from backend.schemas.purchasing import (
    SupplierCreate, SupplierUpdate, SupplierResponse,
    PurchaseCreate, PurchaseResponse, PurchaseLineResponse, PurchasePay, PurchaseSummary,
)
from backend.schemas.response import StandardResponse
from backend.services.audit import log_audit
from backend.services.subscription import get_tier_name, is_pro_tier
from backend.services import purchasing_service as svc

logger = logging.getLogger(__name__)

suppliers_router = APIRouter()
purchases_router = APIRouter()


# ───────────────────────── helpers ─────────────────────────

async def _outlet_of_tenant(db: AsyncSession, outlet_id: UUID, tenant_id: UUID) -> Outlet:
    outlet = (await db.execute(
        select(Outlet).where(Outlet.id == outlet_id, Outlet.deleted_at.is_(None))
    )).scalar_one_or_none()
    if not outlet or outlet.tenant_id != tenant_id:
        raise HTTPException(status_code=404, detail="Outlet tidak ditemukan")
    return outlet


async def _tenant_outlet_ids(db: AsyncSession, tenant_id: UUID) -> list[UUID]:
    return list((await db.execute(
        select(Outlet.id).where(Outlet.tenant_id == tenant_id, Outlet.deleted_at.is_(None))
    )).scalars().all())


def _po_to_response(po: PurchaseOrder, effects: Optional[list] = None) -> PurchaseResponse:
    effect_by_name = {e["name"]: e for e in (effects or [])}
    items = []
    for it in po.items:
        if it.deleted_at is not None:
            continue
        eff = effect_by_name.get(it.display_name, {})
        items.append(PurchaseLineResponse(
            id=it.id,
            ingredient_id=it.ingredient_id,
            product_id=it.product_id,
            is_other=it.is_other,
            name=it.display_name,
            quantity=it.quantity,
            unit=it.unit,
            qty_base=it.qty_base,
            unit_price=it.unit_price,
            total_price=it.total_price,
            cost_before=eff.get("cost_before"),
            cost_after=eff.get("cost_after"),
        ))
    return PurchaseResponse(
        id=po.id,
        outlet_id=po.outlet_id,
        supplier_id=po.supplier_id,
        supplier_name=po.supplier.name if po.supplier else None,
        po_number=po.po_number,
        status=str(getattr(po.status, "value", po.status)),
        invoice_no=po.invoice_no,
        photo_url=po.photo_url,
        notes=po.notes,
        received_at=po.received_at,
        total_amount=po.total_amount,
        paid_amount=po.paid_amount,
        outstanding_amount=po.outstanding_amount,
        due_at=po.due_at,
        row_version=po.row_version,
        created_at=po.created_at,
        items=items,
    )


# ───────────────────────── suppliers ─────────────────────────

@suppliers_router.get("/", response_model=StandardResponse[List[SupplierResponse]])
async def list_suppliers(
    request: Request,
    include_inactive: bool = False,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    stmt = select(Supplier).where(
        Supplier.tenant_id == current_user.tenant_id,
        Supplier.deleted_at.is_(None),
    )
    if not include_inactive:
        stmt = stmt.where(Supplier.is_active.is_(True))
    suppliers = (await db.execute(stmt.order_by(Supplier.name))).scalars().all()

    # Ringkasan belanja per supplier — satu query agregat, bukan N+1.
    agg: dict = {}
    if suppliers:
        outlet_ids = await _tenant_outlet_ids(db, current_user.tenant_id)
        rows = (await db.execute(
            select(
                PurchaseOrder.supplier_id,
                func.count(PurchaseOrder.id),
                func.coalesce(func.sum(PurchaseOrder.total_amount), 0),
                func.coalesce(func.sum(PurchaseOrder.total_amount - PurchaseOrder.paid_amount), 0),
            )
            .where(
                PurchaseOrder.supplier_id.in_([s.id for s in suppliers]),
                PurchaseOrder.outlet_id.in_(outlet_ids) if outlet_ids else false(),
                PurchaseOrder.deleted_at.is_(None),
                PurchaseOrder.status == 'received',
            )
            .group_by(PurchaseOrder.supplier_id)
        )).all()
        agg = {r[0]: r for r in rows}

    out = []
    for s in suppliers:
        resp = SupplierResponse.model_validate(s)
        if s.id in agg:
            _, cnt, tot, outstanding = agg[s.id]
            resp.purchase_count = int(cnt)
            resp.purchase_total = Decimal(str(tot))
            resp.outstanding_total = Decimal(str(max(outstanding, 0)))
        out.append(resp)
    return StandardResponse(success=True, data=out, request_id=request.state.request_id)


@suppliers_router.post("/", response_model=StandardResponse[SupplierResponse])
async def create_supplier(
    request: Request,
    body: SupplierCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    dup = (await db.execute(
        select(Supplier).where(
            Supplier.tenant_id == current_user.tenant_id,
            Supplier.deleted_at.is_(None),
            func.lower(Supplier.name) == body.name.strip().lower(),
        )
    )).scalar_one_or_none()
    if dup:
        raise HTTPException(status_code=400, detail=f"Supplier '{dup.name}' sudah ada")

    sup = Supplier(tenant_id=current_user.tenant_id, **body.model_dump())
    sup.name = sup.name.strip()
    db.add(sup)
    await db.flush()
    await log_audit(
        db=db, action="CREATE", entity="suppliers", entity_id=sup.id,
        after_state=body.model_dump(), user_id=current_user.id, tenant_id=current_user.tenant_id,
    )
    await db.commit()
    await db.refresh(sup)
    return StandardResponse(
        success=True, data=SupplierResponse.model_validate(sup),
        message="Supplier ditambahkan", request_id=request.state.request_id,
    )


@suppliers_router.put("/{supplier_id}", response_model=StandardResponse[SupplierResponse])
async def update_supplier(
    request: Request,
    supplier_id: UUID,
    body: SupplierUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    sup = (await db.execute(
        select(Supplier).where(
            Supplier.id == supplier_id,
            Supplier.tenant_id == current_user.tenant_id,
            Supplier.deleted_at.is_(None),
        )
    )).scalar_one_or_none()
    if not sup:
        raise HTTPException(status_code=404, detail="Supplier tidak ditemukan")
    if sup.row_version != body.row_version:
        raise HTTPException(status_code=409, detail="Data supplier sudah berubah, muat ulang dulu")

    before = {"name": sup.name, "phone": sup.phone, "payment_terms_days": sup.payment_terms_days, "is_active": sup.is_active}
    changes = body.model_dump(exclude_unset=True, exclude={"row_version"})
    for k, v in changes.items():
        setattr(sup, k, v.strip() if isinstance(v, str) and k == "name" else v)
    sup.row_version += 1
    await log_audit(
        db=db, action="UPDATE", entity="suppliers", entity_id=sup.id,
        before_state=before, after_state=changes, user_id=current_user.id, tenant_id=current_user.tenant_id,
    )
    await db.commit()
    await db.refresh(sup)
    return StandardResponse(
        success=True, data=SupplierResponse.model_validate(sup),
        message="Supplier diperbarui", request_id=request.state.request_id,
    )


@suppliers_router.delete("/{supplier_id}", response_model=StandardResponse[dict])
async def delete_supplier(
    request: Request,
    supplier_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    sup = (await db.execute(
        select(Supplier).where(
            Supplier.id == supplier_id,
            Supplier.tenant_id == current_user.tenant_id,
            Supplier.deleted_at.is_(None),
        )
    )).scalar_one_or_none()
    if not sup:
        raise HTTPException(status_code=404, detail="Supplier tidak ditemukan")
    # Soft delete (Rule #7). Nota lama tetap nunjuk ke sini lewat FK RESTRICT.
    sup.deleted_at = datetime.now(timezone.utc)
    sup.is_active = False
    sup.row_version += 1
    await log_audit(
        db=db, action="DELETE", entity="suppliers", entity_id=sup.id,
        user_id=current_user.id, tenant_id=current_user.tenant_id,
    )
    await db.commit()
    return StandardResponse(success=True, data={"ok": True}, message="Supplier dihapus", request_id=request.state.request_id)


# ───────────────────────── purchases (nota) ─────────────────────────

@purchases_router.get("/summary", response_model=StandardResponse[PurchaseSummary])
async def purchase_summary(
    request: Request,
    outlet_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    await _outlet_of_tenant(db, outlet_id, current_user.tenant_id)
    wib = timezone(timedelta(hours=7))
    now_wib = datetime.now(wib)
    month_start = now_wib.replace(day=1, hour=0, minute=0, second=0, microsecond=0).astimezone(timezone.utc)

    base = [
        PurchaseOrder.outlet_id == outlet_id,
        PurchaseOrder.deleted_at.is_(None),
        PurchaseOrder.status == 'received',
    ]
    month_row = (await db.execute(
        select(func.coalesce(func.sum(PurchaseOrder.total_amount), 0), func.count(PurchaseOrder.id))
        .where(*base, PurchaseOrder.received_at >= month_start)
    )).one()
    out_row = (await db.execute(
        select(
            func.coalesce(func.sum(PurchaseOrder.total_amount - PurchaseOrder.paid_amount), 0),
            func.count(PurchaseOrder.id),
        ).where(*base, PurchaseOrder.total_amount > PurchaseOrder.paid_amount)
    )).one()
    next_due = (await db.execute(
        select(PurchaseOrder)
        .options(selectinload(PurchaseOrder.supplier))
        .where(*base, PurchaseOrder.total_amount > PurchaseOrder.paid_amount, PurchaseOrder.due_at.isnot(None))
        .order_by(PurchaseOrder.due_at.asc())
        .limit(1)
    )).scalar_one_or_none()

    data = PurchaseSummary(
        month_total=Decimal(str(month_row[0])),
        month_count=int(month_row[1]),
        outstanding_total=Decimal(str(out_row[0])),
        outstanding_count=int(out_row[1]),
        next_due_at=next_due.due_at if next_due else None,
        next_due_supplier=(next_due.supplier.name if next_due and next_due.supplier else None),
        next_due_amount=next_due.outstanding_amount if next_due else None,
    )
    return StandardResponse(success=True, data=data, request_id=request.state.request_id)


@purchases_router.get("/", response_model=StandardResponse[List[PurchaseResponse]])
async def list_purchases(
    request: Request,
    outlet_id: UUID,
    unpaid_only: bool = False,
    supplier_id: Optional[UUID] = None,
    skip: int = 0,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    await _outlet_of_tenant(db, outlet_id, current_user.tenant_id)
    stmt = (
        select(PurchaseOrder)
        .options(
            selectinload(PurchaseOrder.items).selectinload(PurchaseOrderItem.ingredient),
            selectinload(PurchaseOrder.items).selectinload(PurchaseOrderItem.product),
            selectinload(PurchaseOrder.supplier),
        )
        .where(
            PurchaseOrder.outlet_id == outlet_id,
            PurchaseOrder.deleted_at.is_(None),
            PurchaseOrder.status == 'received',
        )
    )
    if unpaid_only:
        stmt = stmt.where(PurchaseOrder.total_amount > PurchaseOrder.paid_amount)
    if supplier_id:
        stmt = stmt.where(PurchaseOrder.supplier_id == supplier_id)
    stmt = stmt.order_by(PurchaseOrder.received_at.desc().nullslast(), PurchaseOrder.created_at.desc()).offset(skip).limit(min(limit, 200))
    pos = (await db.execute(stmt)).scalars().all()
    return StandardResponse(
        success=True, data=[_po_to_response(p) for p in pos], request_id=request.state.request_id,
    )


@purchases_router.post("/", response_model=StandardResponse[PurchaseResponse])
async def create_purchase(
    request: Request,
    body: PurchaseCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """Catat nota belanja: stok naik, HPP jadi rata-rata bergerak, utang kecatat."""
    tenant = (await db.execute(select(Tenant).where(Tenant.id == current_user.tenant_id))).scalar_one_or_none()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant tidak ditemukan")
    tier = get_tier_name(tenant)
    is_pro = is_pro_tier(tenant)

    supplier = await svc.resolve_supplier(
        db, tenant_id=current_user.tenant_id,
        supplier_id=body.supplier_id, supplier_name=body.supplier_name,
    )

    po, effects = await svc.receive_purchase(
        db,
        tenant_id=current_user.tenant_id,
        tier=tier,
        is_pro=is_pro,
        outlet_id=body.outlet_id,
        supplier=supplier,
        lines=body.items,
        invoice_no=body.invoice_no,
        photo_url=body.photo_url,
        notes=body.notes,
        received_at=body.received_at,
        paid_amount=body.paid_amount,
        due_at=body.due_at,
        user_id=current_user.id,
    )

    await log_audit(
        db=db, action="CREATE", entity="purchase_orders", entity_id=po.id,
        after_state={
            "po_number": po.po_number, "supplier": supplier.name if supplier else None,
            "total": str(po.total_amount), "paid": str(po.paid_amount), "lines": len(body.items),
        },
        user_id=current_user.id, tenant_id=current_user.tenant_id,
    )
    await db.commit()

    loaded = await svc.load_purchase(db, po.id)
    return StandardResponse(
        success=True,
        data=_po_to_response(loaded, effects),
        message=f"Nota {po.po_number} dicatat",
        request_id=request.state.request_id,
    )


@purchases_router.get("/{purchase_id}", response_model=StandardResponse[PurchaseResponse])
async def get_purchase(
    request: Request,
    purchase_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    po = await svc.load_purchase(db, purchase_id)
    if not po:
        raise HTTPException(status_code=404, detail="Nota tidak ditemukan")
    await _outlet_of_tenant(db, po.outlet_id, current_user.tenant_id)
    return StandardResponse(success=True, data=_po_to_response(po), request_id=request.state.request_id)


@purchases_router.post("/{purchase_id}/pay", response_model=StandardResponse[PurchaseResponse])
async def pay_purchase(
    request: Request,
    purchase_id: UUID,
    body: PurchasePay,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """Bayar utang nota (sebagian atau lunas). Optimistic lock via row_version."""
    po = await svc.load_purchase(db, purchase_id)
    if not po:
        raise HTTPException(status_code=404, detail="Nota tidak ditemukan")
    await _outlet_of_tenant(db, po.outlet_id, current_user.tenant_id)
    if po.outstanding_amount <= 0:
        raise HTTPException(status_code=400, detail="Nota ini sudah lunas")

    new_paid = min(po.paid_amount + body.amount, po.total_amount)
    result = await db.execute(
        update(PurchaseOrder)
        .where(PurchaseOrder.id == po.id, PurchaseOrder.row_version == body.row_version)
        .values(
            paid_amount=new_paid,
            due_at=None if new_paid >= po.total_amount else PurchaseOrder.due_at,
            row_version=PurchaseOrder.row_version + 1,
        )
    )
    if result.rowcount == 0:
        raise HTTPException(status_code=409, detail="Nota sudah berubah, muat ulang dulu")

    from backend.models.event import Event
    db.add(Event(
        outlet_id=po.outlet_id,
        stream_id=f"purchase:{po.id}",
        event_type="purchase.paid",
        event_data={
            "purchase_id": str(po.id), "amount": str(body.amount),
            "paid_after": str(new_paid), "total": str(po.total_amount),
            "user_id": str(current_user.id),
        },
    ))
    await log_audit(
        db=db, action="PAY", entity="purchase_orders", entity_id=po.id,
        before_state={"paid": str(po.paid_amount)}, after_state={"paid": str(new_paid)},
        user_id=current_user.id, tenant_id=current_user.tenant_id,
    )
    await db.commit()
    loaded = await svc.load_purchase(db, po.id)
    return StandardResponse(
        success=True, data=_po_to_response(loaded),
        message="Lunas" if new_paid >= po.total_amount else "Pembayaran dicatat",
        request_id=request.state.request_id,
    )
