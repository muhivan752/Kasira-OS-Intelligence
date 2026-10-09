"""Hapus akun: status, minta hapus, batalkan. Aturannya di services/account_deletion.py."""
from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.deps import get_current_user
from backend.core.database import get_db
from backend.models.user import User
from backend.schemas.response import StandardResponse
from backend.services import account_deletion as svc

router = APIRouter()


class DeletionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    confirm: str


@router.get("", response_model=StandardResponse)
async def deletion_status(db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    return StandardResponse(data=await svc.status_for(db, current_user))


@router.post("", response_model=StandardResponse)
async def request_deletion(body: DeletionRequest, db: AsyncSession = Depends(get_db),
                           current_user: User = Depends(get_current_user)):
    return StandardResponse(data=await svc.request_deletion(db, current_user, body.confirm))


@router.delete("", response_model=StandardResponse)
async def cancel_deletion(db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    return StandardResponse(data=await svc.cancel_deletion(db, current_user))
