from typing import Generator, Optional
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from backend.core import security
from backend.core.config import settings
from backend.core.database import get_db, tenant_context
from backend.models.user import User
from backend.models.tenant import Tenant
from backend.schemas.token import TokenPayload

security_bearer = HTTPBearer()

async def get_current_user(
    db: AsyncSession = Depends(get_db), 
    token: HTTPAuthorizationCredentials = Depends(security_bearer)
) -> User:
    try:
        payload = jwt.decode(
            token.credentials, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        token_data = TokenPayload(**payload)
    except (JWTError, ValidationError):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Token tidak valid",
        )
    
    stmt = select(User).where(User.id == token_data.sub, User.deleted_at == None)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(status_code=404, detail="Pengguna tidak ditemukan")
    if not user.is_active:
        raise HTTPException(status_code=400, detail="Akun tidak aktif")
    return user

async def get_current_tenant(
    request: Request,
    db: AsyncSession = Depends(get_db)
) -> Tenant:
    tenant_id = request.headers.get("X-Tenant-ID")
    if not tenant_id or tenant_id == "public":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Header X-Tenant-ID wajib diisi"
        )
        
    stmt = select(Tenant).where(Tenant.schema_name == tenant_id, Tenant.deleted_at == None)
    result = await db.execute(stmt)
    tenant = result.scalar_one_or_none()
    
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant tidak ditemukan")
    if not tenant.is_active:
        raise HTTPException(status_code=400, detail="Tenant tidak aktif")
    return tenant

def get_current_active_superuser(
    current_user: User = Depends(get_current_user),
) -> User:
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=400, detail="Akses ditolak"
        )
    return current_user
