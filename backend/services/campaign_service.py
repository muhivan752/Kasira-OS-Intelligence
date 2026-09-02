"""
Kirim promo WhatsApp dari nomor toko sendiri.

Alur: pemilik bikin campaign (nama, pesan, target) → `preview` ngitung siapa
yang bakal dapet → `send` bikin satu baris campaign_messages per penerima
lalu ngirim satu-satu di background lewat token Fonnte outlet.

Aturan yang nggak boleh dilanggar:
- HANYA pelanggan `wa_marketing_consent = true` + punya nomor.
- Tiap pesan ditutup "Balas STOP untuk berhenti" — dan kalau ada yang bales
  STOP, kasir/pemilik cabut centang izin di profil (otomatisnya nunggu
  webhook Fonnte, belum).
- Jeda 1,2 detik antar pesan — Fonnte + WhatsApp ngeblokir nomor yang
  nyembur ratusan pesan dalam sedetik.
- Background task punya session sendiri + `SET LOCAL app.current_tenant_id`
  (gotcha #16) — kalau nggak, RLS ngasih nol baris tanpa error.
"""
from __future__ import annotations

import asyncio
import logging
import re
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from sqlalchemy import select, text, update
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.database import AsyncSessionLocal
from backend.models.campaign import Campaign, CampaignMessage
from backend.models.customer import Customer
from backend.models.outlet import Outlet
from backend.services.fonnte import send_whatsapp_with_token

logger = logging.getLogger(__name__)

SEND_GAP_SECONDS = 1.2
OPT_OUT_LINE = "\n\n_Balas STOP untuk berhenti menerima promo._"


def normalize_phone(raw: Optional[str]) -> Optional[str]:
    d = re.sub(r"\D", "", raw or "")
    if not d:
        return None
    if d.startswith("0"):
        d = "62" + d[1:]
    elif d.startswith("8"):
        d = "62" + d
    return d if 10 <= len(d) <= 15 else None


def render(template: str, *, nama: str, toko: str) -> str:
    first = (nama or "").strip().split(" ")[0] if nama else ""
    body = template.replace("{nama}", first or "Kak").replace("{toko}", toko)
    if "STOP" not in body.upper():
        body += OPT_OUT_LINE
    return body


async def resolve_recipients(db: AsyncSession, *, tenant_id: UUID, target: str) -> list[Customer]:
    """Target 'all' | 'segment:<key>' | 'tag:<uuid>'. Segmen/tag baca kolom/tabel
    dari sesi CRM (mig 095) kalau ada; kalau belum ada, jatuh ke 'all'."""
    stmt = select(Customer).where(
        Customer.tenant_id == tenant_id,
        Customer.deleted_at.is_(None),
        Customer.wa_marketing_consent.is_(True),
        Customer.phone.isnot(None),
    )
    kind, _, val = (target or "all").partition(":")
    if kind == "segment" and val and hasattr(Customer, "segment"):
        stmt = stmt.where(getattr(Customer, "segment") == val)
    elif kind == "tag" and val:
        try:
            from backend.models.crm import CustomerTagLink  # dari sesi CRM
            stmt = stmt.where(Customer.id.in_(
                select(CustomerTagLink.customer_id).where(CustomerTagLink.tag_id == UUID(val))
            ))
        except Exception:
            logger.warning("target tag dipakai tapi tabel tag belum ada — kirim ke semua yang setuju")
    rows = (await db.execute(stmt.order_by(Customer.last_visit_at.desc().nullslast()))).scalars().all()
    return [c for c in rows if normalize_phone(c.phone)]


async def enqueue(db: AsyncSession, campaign: Campaign, recipients: list[Customer]) -> int:
    n = 0
    for c in recipients:
        db.add(CampaignMessage(
            tenant_id=campaign.tenant_id, campaign_id=campaign.id, customer_id=c.id,
            phone=normalize_phone(c.phone), status="queued",
        ))
        n += 1
    campaign.recipient_count = n
    campaign.status = "sending"
    campaign.started_at = datetime.now(timezone.utc)
    campaign.row_version = (campaign.row_version or 0) + 1
    await db.flush()
    return n


async def run_campaign(campaign_id: UUID, tenant_id: UUID) -> None:
    """Background: kirim semua yang queued. Session sendiri, tenant context sendiri."""
    async with AsyncSessionLocal() as db:
        await db.execute(text(f"SET LOCAL app.current_tenant_id = '{tenant_id}'"))
        camp = (await db.execute(select(Campaign).where(Campaign.id == campaign_id))).scalar_one_or_none()
        if not camp:
            return
        outlet = await db.get(Outlet, camp.outlet_id)
        token = outlet.fonnte_token if outlet else None
        if not token:
            camp.status = "failed"; camp.finished_at = datetime.now(timezone.utc)
            await db.execute(update(CampaignMessage).where(
                CampaignMessage.campaign_id == camp.id, CampaignMessage.status == "queued"
            ).values(status="failed", error="Token Fonnte toko belum dipasang"))
            await db.commit()
            return

        queued = (await db.execute(
            select(CampaignMessage, Customer)
            .join(Customer, Customer.id == CampaignMessage.customer_id)
            .where(CampaignMessage.campaign_id == camp.id, CampaignMessage.status == "queued")
        )).all()
        sent = failed = 0
        for msg, cust in queued:
            body = render(camp.template, nama=cust.name or "", toko=outlet.name or "")
            ok = await send_whatsapp_with_token(token, msg.phone, body)
            msg.status = "sent" if ok else "failed"
            msg.sent_at = datetime.now(timezone.utc) if ok else None
            msg.error = None if ok else "Fonnte menolak / nomor tidak aktif"
            if ok:
                sent += 1
            else:
                failed += 1
            camp.sent_count = sent; camp.failed_count = failed
            await db.commit()
            await asyncio.sleep(SEND_GAP_SECONDS)

        camp.status = "done" if failed < max(1, len(queued)) else "failed"
        camp.finished_at = datetime.now(timezone.utc)
        camp.row_version = (camp.row_version or 0) + 1
        await db.commit()
        logger.info("campaign %s selesai: %d terkirim, %d gagal", camp.id, sent, failed)
