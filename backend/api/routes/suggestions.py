"""Saran Selaris: daftar, terapkan, abaikan, batalkan. Aturannya di services/suggestions.py."""
import asyncio
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, ConfigDict
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.deps import get_current_user, get_platform_admin
from backend.core.database import get_db
from backend.models.user import User
from backend.schemas.response import StandardResponse
from backend.services import suggestions as svc

router = APIRouter()


class SkipBody(BaseModel):
    model_config = ConfigDict(extra="forbid")
    reason: Literal["Sudah tahu", "Angkanya tidak sesuai", "Nanti saja", "Tidak relevan"]


class ApplyBody(BaseModel):
    model_config = ConfigDict(extra="forbid")
    new_price: int | None = None   # Ubah harga usulan sebelum diterapkan
    qty: float | None = None       # Ubah jumlah pesanan (satuan yang ditampilkan)


class RefreshBody(BaseModel):
    model_config = ConfigDict(extra="forbid")
    outlet_id: UUID


@router.get("", response_model=StandardResponse)
async def list_suggestions(outlet_id: UUID, request: Request, db: AsyncSession = Depends(get_db),
                           current_user: User = Depends(get_current_user)):
    return StandardResponse(data=await svc.list_for(db, current_user, request.state.access, outlet_id))


@router.post("/{suggestion_id}/apply", response_model=StandardResponse)
async def apply_suggestion(suggestion_id: UUID, request: Request, body: ApplyBody | None = None,
                           db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    params = body.model_dump(exclude_none=True) if body else None
    return StandardResponse(data=await svc.apply(db, current_user, request.state.access, suggestion_id, params))


@router.post("/{suggestion_id}/skip", response_model=StandardResponse)
async def skip_suggestion(suggestion_id: UUID, body: SkipBody, request: Request, db: AsyncSession = Depends(get_db),
                          current_user: User = Depends(get_current_user)):
    return StandardResponse(data=await svc.skip(db, current_user, request.state.access, suggestion_id, body.reason))


@router.post("/{suggestion_id}/undo", response_model=StandardResponse)
async def undo_suggestion(suggestion_id: UUID, request: Request, db: AsyncSession = Depends(get_db),
                          current_user: User = Depends(get_current_user)):
    return StandardResponse(data=await svc.undo(db, current_user, request.state.access, suggestion_id))


@router.post("/refresh", response_model=StandardResponse)
async def refresh_suggestions(body: RefreshBody, request: Request, current_user: User = Depends(get_current_user)):
    """Pemilik minta Selaris memeriksa ulang sekarang (jalan di belakang, kartu muncul beberapa saat lagi)."""
    access = request.state.access
    if access.mode != "owner" or body.outlet_id not in access.outlet_ids:
        raise HTTPException(403, "Hanya pemilik usaha yang dapat memeriksa ulang")
    asyncio.create_task(svc.run_due_once(force_outlet=body.outlet_id))
    return StandardResponse(data={"queued": True})


@router.get("/stats", response_model=StandardResponse)
async def suggestion_stats(db: AsyncSession = Depends(get_db), admin: User = Depends(get_platform_admin)):
    return StandardResponse(data=await svc.stats_by_kind(db))
