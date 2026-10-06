"""
Purchasing — /suppliers + /purchases (nota belanja).

Semua tier. Yang Pro-only cuma BARIS BAHAN BAKU di nota (dicek di service),
karena ingredients router-nya sendiri udah Pro. Tenant Starter tetap bisa
nyatet nota produk jadi + utang supplier — itu justru yang mereka butuhin
(mayoritas Starter non-F&B).
"""
import logging
import hashlib
import json
from collections import defaultdict, deque
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from typing import Any, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, Query
from sqlalchemy import select, func, update, false, text, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.api import deps
from backend.core.database import get_db
from backend.models.user import User
from backend.models.tenant import Tenant
from backend.models.outlet import Outlet
from backend.models.purchasing import Supplier, PurchaseOrder, PurchaseOrderItem
from backend.models.audit_log import AuditLog
from backend.models.event import Event
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


async def _invalidate_received(db, outlet_id, tenant_id):
    try:
        outlet = await db.get(Outlet, outlet_id)
        rows = (await db.execute(select(Outlet.id, Outlet.slug).where(
            Outlet.tenant_id == tenant_id, Outlet.brand_id == outlet.brand_id, Outlet.deleted_at.is_(None),
        ))).all()
        from backend.services.redis import get_redis_client
        redis = await get_redis_client()
        keys = [key for oid, slug in rows for key in (f'ai:context:{oid}', f'connect:storefront:{slug}')]
        if keys:
            await redis.delete(*keys)
    except Exception:
        logger.warning('Purchase received cache refresh unavailable', exc_info=True)


async def _replay(db, body, user, entity, action, scope=None):
    fingerprint = hashlib.sha256(json.dumps({'body': body.model_dump(mode='json', exclude={'client_request_id'}), 'scope': scope},
                                            sort_keys=True).encode()).hexdigest()
    metadata = {}
    if body.client_request_id:
        key = str(body.client_request_id)
        await db.execute(text('SELECT pg_advisory_xact_lock(hashtextextended(:key, 0))'),
                         {'key': f'purchasing:{user.tenant_id}:{key}'})
        previous = (await db.execute(select(AuditLog).where(
            AuditLog.tenant_id == user.tenant_id,
            AuditLog.after_state['client_request_id'].astext == key,
        ).order_by(AuditLog.created_at).limit(1))).scalar_one_or_none()
        if previous:
            if (previous.user_id != user.id or previous.entity != entity or previous.action != action
                    or previous.after_state.get('fingerprint') != fingerprint):
                raise HTTPException(status_code=409, detail='Permintaan ini sudah digunakan untuk data berbeda')
            return previous.entity_id, metadata
        metadata = {'client_request_id': key, 'fingerprint': fingerprint}
    return None, metadata


async def _purchase_detail(db, po):
    events = (await db.execute(select(Event).where(
        Event.stream_id == f'purchase:{po.id}', Event.outlet_id == po.outlet_id,
        Event.event_type.in_(['purchase.received', 'purchase.paid']),
    ).order_by(Event.created_at, Event.id))).scalars().all()
    received = next((e for e in events if e.event_type == 'purchase.received'), None)
    response = _po_to_response(po, (received.event_data.get('lines') or []) if received else None)
    previous = Decimal(str(received.event_data.get('paid', '0'))) if received else None
    if previous is not None and previous > 0:
        response.payments.append({'id': str(received.id), 'kind': 'initial', 'amount': str(previous),
                                  'paid_at': (po.received_at or received.created_at).isoformat()})
    for event in events:
        if event.event_type != 'purchase.paid':
            continue
        after = Decimal(str(event.event_data.get('paid_after', previous or '0')))
        before = Decimal(str(event.event_data['paid_before'])) if 'paid_before' in event.event_data else previous
        if before is None or after < before or before < 0:
            response.payment_history_incomplete = True
            previous = after
            continue
        if previous is not None and before != previous:
            response.payment_history_incomplete = True
        amount = after - before
        previous = after
        if amount > 0:
            response.payments.append({'id': str(event.id), 'kind': 'installment', 'amount': str(amount),
                                      'paid_at': event.created_at.isoformat()})
    if sum((Decimal(p['amount']) for p in response.payments), Decimal('0')) != po.paid_amount:
        response.payment_history_incomplete = True
    return response


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
    effect_groups = defaultdict(deque)
    for effect in effects or []:
        key = str(effect.get('ingredient_id') or effect.get('product_id') or effect.get('name'))
        effect_groups[key].append(effect)
    items = []
    for it in po.items:
        if it.deleted_at is not None:
            continue
        key = str(it.ingredient_id or it.product_id or it.display_name)
        eff = effect_groups[key].popleft() if effect_groups[key] else {}
        items.append(PurchaseLineResponse(
            id=it.id,
            ingredient_id=it.ingredient_id,
            product_id=it.product_id,
            is_other=it.is_other,
            name=it.display_name,
            quantity=it.quantity,
            unit=it.unit,
            base_unit=eff.get('base_unit') or ('pcs' if it.product_id else None),
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
    outlet_id: Optional[UUID] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    if outlet_id:
        await _outlet_of_tenant(db, outlet_id, current_user.tenant_id)
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
        if outlet_id:
            await _outlet_of_tenant(db, outlet_id, current_user.tenant_id)
        outlet_ids = [outlet_id] if outlet_id else await _tenant_outlet_ids(db, current_user.tenant_id)
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
    replay, metadata = await _replay(db, body, current_user, 'suppliers', 'CREATE')
    if replay:
        sup = await db.get(Supplier, replay)
        if not sup or sup.deleted_at:
            raise HTTPException(status_code=409, detail='Supplier dari permintaan ini sudah dihapus')
        return StandardResponse(success=True, data=SupplierResponse.model_validate(sup), request_id=request.state.request_id)
    await db.execute(text('SELECT pg_advisory_xact_lock(hashtextextended(:key, 0))'),
                     {'key': f'supplier-name:{current_user.tenant_id}'})
    dup = (await db.execute(
        select(Supplier).where(
            Supplier.tenant_id == current_user.tenant_id,
            Supplier.deleted_at.is_(None),
            func.lower(Supplier.name) == body.name.strip().lower(),
        )
    )).scalar_one_or_none()
    if dup:
        raise HTTPException(status_code=400, detail=f"Supplier '{dup.name}' sudah ada")

    sup = Supplier(tenant_id=current_user.tenant_id, **body.model_dump(exclude={'client_request_id'}))
    sup.name = sup.name.strip()
    db.add(sup)
    await db.flush()
    await log_audit(
        db=db, action="CREATE", entity="suppliers", entity_id=sup.id,
        after_state={**body.model_dump(mode='json'), **metadata}, user_id=current_user.id, tenant_id=current_user.tenant_id,
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
        ).with_for_update()
    )).scalar_one_or_none()
    if not sup:
        raise HTTPException(status_code=404, detail="Supplier tidak ditemukan")
    if sup.row_version != body.row_version:
        raise HTTPException(status_code=409, detail="Data supplier sudah berubah, muat ulang dulu")

    before = {"name": sup.name, "phone": sup.phone, "payment_terms_days": sup.payment_terms_days, "is_active": sup.is_active}
    changes = body.model_dump(exclude_unset=True, exclude={"row_version"})
    if 'name' in changes:
        await db.execute(text('SELECT pg_advisory_xact_lock(hashtextextended(:key, 0))'),
                         {'key': f'supplier-name:{current_user.tenant_id}'})
        duplicate = await db.scalar(select(Supplier.id).where(
            Supplier.tenant_id == current_user.tenant_id, Supplier.deleted_at.is_(None),
            Supplier.id != sup.id, func.lower(Supplier.name) == changes['name'].lower(),
        ).limit(1))
        if duplicate:
            raise HTTPException(status_code=400, detail='Nama supplier sudah digunakan')
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
        ).with_for_update()
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
    month: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    await _outlet_of_tenant(db, outlet_id, current_user.tenant_id)
    from backend.services.finance_service import month_bounds, WIB
    month = month or datetime.now(WIB).strftime('%Y-%m')
    month_start, month_end = month_bounds(month)

    base = [
        PurchaseOrder.outlet_id == outlet_id,
        PurchaseOrder.deleted_at.is_(None),
        PurchaseOrder.status == 'received',
    ]
    month_row = (await db.execute(
        select(func.coalesce(func.sum(PurchaseOrder.total_amount), 0), func.count(PurchaseOrder.id))
        .where(*base, PurchaseOrder.received_at >= month_start, PurchaseOrder.received_at < month_end)
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

    overdue = (await db.execute(select(
        func.coalesce(func.sum(PurchaseOrder.total_amount - PurchaseOrder.paid_amount), 0), func.count(PurchaseOrder.id),
    ).where(*base, PurchaseOrder.total_amount > PurchaseOrder.paid_amount,
            PurchaseOrder.due_at < datetime.now(timezone.utc)))).one()
    data = PurchaseSummary(
        month=month, generated_at=datetime.now(timezone.utc),
        overdue_total=overdue[0], overdue_count=overdue[1],
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
    month: Optional[str] = None,
    search: Optional[str] = Query(None, max_length=120),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
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
    if month:
        from backend.services.finance_service import month_bounds
        start, end = month_bounds(month)
        stmt = stmt.where(PurchaseOrder.received_at >= start, PurchaseOrder.received_at < end)
    if search and search.strip():
        term = '%' + search.strip().replace('\\', '\\\\').replace('%', '\\%').replace('_', '\\_') + '%'
        stmt = stmt.outerjoin(Supplier, Supplier.id == PurchaseOrder.supplier_id).where(or_(
            PurchaseOrder.po_number.ilike(term, escape='\\'), PurchaseOrder.invoice_no.ilike(term, escape='\\'),
            Supplier.name.ilike(term, escape='\\'),
        ))
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
    await _outlet_of_tenant(db, body.outlet_id, current_user.tenant_id)
    replay, metadata = await _replay(db, body, current_user, 'purchase_orders', 'CREATE')
    if replay:
        loaded = await svc.load_purchase(db, replay)
        if not loaded:
            raise HTTPException(status_code=409, detail='Nota dari permintaan ini tidak tersedia')
        return StandardResponse(success=True, data=await _purchase_detail(db, loaded), request_id=request.state.request_id)
    tenant = (await db.execute(select(Tenant).where(Tenant.id == current_user.tenant_id))).scalar_one_or_none()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant tidak ditemukan")
    tier = get_tier_name(tenant)
    is_pro = is_pro_tier(tenant)

    await db.execute(text('SELECT pg_advisory_xact_lock(hashtextextended(:key, 0))'),
                     {'key': f'supplier-name:{current_user.tenant_id}'})
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
            "total": str(po.total_amount), "paid": str(po.paid_amount), "lines": len(body.items), **metadata,
        },
        user_id=current_user.id, tenant_id=current_user.tenant_id,
    )
    await db.commit()

    loaded = await svc.load_purchase(db, po.id)
    await _invalidate_received(db, po.outlet_id, current_user.tenant_id)
    return StandardResponse(
        success=True,
        data=await _purchase_detail(db, loaded),
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
    return StandardResponse(success=True, data=await _purchase_detail(db, po), request_id=request.state.request_id)


@purchases_router.post("/{purchase_id}/pay", response_model=StandardResponse[PurchaseResponse])
async def pay_purchase(
    request: Request,
    purchase_id: UUID,
    body: PurchasePay,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """Bayar utang nota (sebagian atau lunas). Optimistic lock via row_version."""
    # The audit fingerprint also binds a payment request to this purchase.
    replay, metadata = await _replay(db, body, current_user, 'purchase_orders', 'PAY', str(purchase_id))
    if replay:
        loaded = await svc.load_purchase(db, replay)
        if not loaded:
            raise HTTPException(status_code=409, detail='Nota tidak tersedia')
        await _outlet_of_tenant(db, loaded.outlet_id, current_user.tenant_id)
        return StandardResponse(success=True, data=await _purchase_detail(db, loaded), request_id=request.state.request_id)
    await db.execute(select(PurchaseOrder.id).where(PurchaseOrder.id == purchase_id).with_for_update())
    po = await svc.load_purchase(db, purchase_id)
    if not po:
        raise HTTPException(status_code=404, detail="Nota tidak ditemukan")
    await _outlet_of_tenant(db, po.outlet_id, current_user.tenant_id)
    if po.row_version != body.row_version:
        raise HTTPException(status_code=409, detail='Nota sudah berubah, muat ulang dulu')
    if po.outstanding_amount <= 0:
        raise HTTPException(status_code=400, detail="Nota ini sudah lunas")

    paid_before = po.paid_amount
    new_paid = min(paid_before + body.amount, po.total_amount)
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
            "purchase_id": str(po.id), "amount": str(new_paid - paid_before),
            "paid_before": str(paid_before),
            "paid_after": str(new_paid), "total": str(po.total_amount),
            "user_id": str(current_user.id),
        },
    ))
    await log_audit(
        db=db, action='PAY', entity="purchase_orders", entity_id=po.id,
        before_state={"paid": str(paid_before)}, after_state={"paid": str(new_paid), **metadata},
        user_id=current_user.id, tenant_id=current_user.tenant_id,
    )
    await db.commit()
    loaded = await svc.load_purchase(db, po.id)
    return StandardResponse(
        success=True, data=await _purchase_detail(db, loaded),
        message="Lunas" if new_paid >= po.total_amount else "Pembayaran dicatat",
        request_id=request.state.request_id,
    )
