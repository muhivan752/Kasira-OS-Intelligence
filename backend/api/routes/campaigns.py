"""
/campaigns — promo WhatsApp dari nomor toko sendiri (semua tier, butuh
token Fonnte outlet). Lihat campaign_service.py buat aturan kirim.
"""
import logging
from datetime import datetime, timezone
from typing import Any, List, Optional
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api import deps
from backend.core.database import get_db
from backend.models.user import User
from backend.models.outlet import Outlet
from backend.models.campaign import Campaign, CampaignMessage
from backend.schemas.response import StandardResponse
from backend.services.audit import log_audit
from backend.services import campaign_service as svc
from backend.utils.phone import mask_phone

logger = logging.getLogger(__name__)
router = APIRouter()


class CampaignCreate(BaseModel):
    outlet_id: UUID
    name: str = Field(..., min_length=1, max_length=120)
    template: str = Field(..., min_length=5, max_length=1500)
    target: str = "all"


class CampaignResponse(BaseModel):
    id: UUID
    outlet_id: UUID
    name: str
    template: str
    target: str
    status: str
    recipient_count: int
    sent_count: int
    failed_count: int
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    created_at: datetime
    row_version: int


class CampaignPreview(BaseModel):
    recipient_count: int
    sample: List[dict]
    wa_connected: bool
    rendered_example: str


def _resp(c: Campaign) -> CampaignResponse:
    return CampaignResponse(
        id=c.id, outlet_id=c.outlet_id, name=c.name, template=c.template, target=c.target, status=c.status,
        recipient_count=c.recipient_count, sent_count=c.sent_count, failed_count=c.failed_count,
        started_at=c.started_at, finished_at=c.finished_at, created_at=c.created_at, row_version=c.row_version,
    )


async def _outlet(db: AsyncSession, outlet_id: UUID, tenant_id: UUID) -> Outlet:
    o = (await db.execute(select(Outlet).where(Outlet.id == outlet_id, Outlet.deleted_at.is_(None)))).scalar_one_or_none()
    if not o or o.tenant_id != tenant_id:
        raise HTTPException(status_code=404, detail="Outlet tidak ditemukan")
    return o


@router.get("/", response_model=StandardResponse[List[CampaignResponse]])
async def list_campaigns(
    request: Request, outlet_id: UUID,
    db: AsyncSession = Depends(get_db), current_user: User = Depends(deps.get_current_user),
) -> Any:
    await _outlet(db, outlet_id, current_user.tenant_id)
    rows = (await db.execute(
        select(Campaign).where(Campaign.outlet_id == outlet_id, Campaign.deleted_at.is_(None))
        .order_by(Campaign.created_at.desc()).limit(100)
    )).scalars().all()
    return StandardResponse(success=True, data=[_resp(c) for c in rows], request_id=request.state.request_id)


@router.post("/preview", response_model=StandardResponse[CampaignPreview])
async def preview_campaign(
    request: Request, body: CampaignCreate,
    db: AsyncSession = Depends(get_db), current_user: User = Depends(deps.get_current_user),
) -> Any:
    """Berapa orang yang bakal dapet + contoh pesan jadi — sebelum tombol kirim."""
    outlet = await _outlet(db, body.outlet_id, current_user.tenant_id)
    recipients = await svc.resolve_recipients(db, tenant_id=current_user.tenant_id, target=body.target)
    sample = [{"name": c.name, "phone": mask_phone(c.phone)} for c in recipients[:5]]
    example = svc.render(body.template, nama=(recipients[0].name if recipients else "Budi"), toko=outlet.name or "")
    return StandardResponse(success=True, data=CampaignPreview(
        recipient_count=len(recipients), sample=sample,
        wa_connected=bool(outlet.fonnte_token), rendered_example=example,
    ), request_id=request.state.request_id)


@router.post("/", response_model=StandardResponse[CampaignResponse])
async def create_campaign(
    request: Request, body: CampaignCreate,
    db: AsyncSession = Depends(get_db), current_user: User = Depends(deps.get_current_user),
) -> Any:
    await _outlet(db, body.outlet_id, current_user.tenant_id)
    c = Campaign(
        tenant_id=current_user.tenant_id, outlet_id=body.outlet_id, name=body.name.strip(),
        template=body.template.strip(), target=body.target or "all", status="draft", created_by=current_user.id,
    )
    db.add(c); await db.flush()
    await log_audit(db=db, action="CREATE", entity="campaigns", entity_id=c.id,
                    after_state={"name": c.name, "target": c.target}, user_id=current_user.id, tenant_id=current_user.tenant_id)
    await db.commit(); await db.refresh(c)
    return StandardResponse(success=True, data=_resp(c), message="Draft promo disimpan", request_id=request.state.request_id)


@router.post("/{campaign_id}/send", response_model=StandardResponse[CampaignResponse])
async def send_campaign(
    request: Request, campaign_id: UUID, background: BackgroundTasks,
    db: AsyncSession = Depends(get_db), current_user: User = Depends(deps.get_current_user),
) -> Any:
    c = (await db.execute(select(Campaign).where(
        Campaign.id == campaign_id, Campaign.tenant_id == current_user.tenant_id, Campaign.deleted_at.is_(None)
    ))).scalar_one_or_none()
    if not c:
        raise HTTPException(status_code=404, detail="Promo tidak ditemukan")
    if c.status != "draft":
        raise HTTPException(status_code=400, detail=f"Promo sudah {c.status}")
    outlet = await _outlet(db, c.outlet_id, current_user.tenant_id)
    if not outlet.fonnte_token:
        raise HTTPException(status_code=400, detail="WhatsApp toko belum tersambung — pasang token Fonnte di Pengaturan dulu")

    recipients = await svc.resolve_recipients(db, tenant_id=current_user.tenant_id, target=c.target)
    if not recipients:
        raise HTTPException(status_code=400, detail="Belum ada pelanggan yang setuju dikirimi promo (centang izin WA di profil pelanggan)")
    n = await svc.enqueue(db, c, recipients)
    await log_audit(db=db, action="SEND", entity="campaigns", entity_id=c.id,
                    after_state={"recipients": n}, user_id=current_user.id, tenant_id=current_user.tenant_id)
    await db.commit(); await db.refresh(c)
    background.add_task(svc.run_campaign, c.id, current_user.tenant_id)
    return StandardResponse(success=True, data=_resp(c),
                            message=f"Mengirim ke {n} pelanggan dari nomor toko…", request_id=request.state.request_id)


@router.get("/{campaign_id}", response_model=StandardResponse[dict])
async def campaign_detail(
    request: Request, campaign_id: UUID,
    db: AsyncSession = Depends(get_db), current_user: User = Depends(deps.get_current_user),
) -> Any:
    c = (await db.execute(select(Campaign).where(
        Campaign.id == campaign_id, Campaign.tenant_id == current_user.tenant_id, Campaign.deleted_at.is_(None)
    ))).scalar_one_or_none()
    if not c:
        raise HTTPException(status_code=404, detail="Promo tidak ditemukan")
    msgs = (await db.execute(
        select(CampaignMessage.status, func.count(CampaignMessage.id))
        .where(CampaignMessage.campaign_id == c.id).group_by(CampaignMessage.status)
    )).all()
    return StandardResponse(success=True, data={
        **_resp(c).model_dump(), "by_status": {s: int(n) for s, n in msgs},
    }, request_id=request.state.request_id)


@router.delete("/{campaign_id}", response_model=StandardResponse[dict])
async def delete_campaign(
    request: Request, campaign_id: UUID,
    db: AsyncSession = Depends(get_db), current_user: User = Depends(deps.get_current_user),
) -> Any:
    c = (await db.execute(select(Campaign).where(
        Campaign.id == campaign_id, Campaign.tenant_id == current_user.tenant_id, Campaign.deleted_at.is_(None)
    ))).scalar_one_or_none()
    if not c:
        raise HTTPException(status_code=404, detail="Promo tidak ditemukan")
    if c.status == "sending":
        raise HTTPException(status_code=400, detail="Lagi dikirim, tunggu selesai")
    c.deleted_at = datetime.now(timezone.utc); c.row_version += 1
    await db.commit()
    return StandardResponse(success=True, data={"ok": True}, message="Promo dihapus", request_id=request.state.request_id)
