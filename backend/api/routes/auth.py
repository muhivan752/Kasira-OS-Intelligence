import random
import logging
import uuid
from datetime import timedelta
from typing import Any, Optional

from fastapi import APIRouter, Body, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text

from backend.api import deps
from backend.core import security
from backend.core.config import settings
from backend.models.user import User
from backend.models.outlet import Outlet
from backend.models.tenant import Tenant
from backend.models.brand import Brand
from backend.schemas.token import Token
from backend.schemas.auth import OTPSendRequest, OTPVerifyRequest
from backend.schemas.response import StandardResponse
from backend.services.fonnte import send_whatsapp_message
from backend.services.redis import get_redis_client
from backend.services.audit import log_audit

router = APIRouter()
logger = logging.getLogger(__name__)

@router.post("/otp/send", response_model=StandardResponse[dict])
async def send_otp(
    request: OTPSendRequest,
    db: AsyncSession = Depends(deps.get_db)
) -> Any:
    """
    Send OTP via WhatsApp to the given phone number
    """
    # Check if user exists (skip for register purpose)
    stmt = select(User).where(User.phone == request.phone, User.deleted_at == None)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if request.purpose == "register":
        if user:
            raise HTTPException(status_code=400, detail="Nomor HP sudah terdaftar. Silakan login.")
    else:
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        if not user.is_active:
            raise HTTPException(status_code=400, detail="Inactive user")
        
    # Generate 6-digit OTP
    otp = str(random.randint(100000, 999999))
    
    redis = await get_redis_client()
    
    # Check rate limit: max 3x resend per 15 minutes
    rate_limit_key = f"otp_count:{request.phone}"
    current_count = await redis.get(rate_limit_key)
    if current_count and int(current_count) >= 10:
        raise HTTPException(status_code=429, detail="Too many OTP requests. Please try again after 15 minutes.")
    
    # Save to Redis with 5 minutes TTL
    await redis.setex(f"otp:{request.phone}", 300, otp)
    
    # Increment rate limit counter
    if not current_count:
        await redis.setex(rate_limit_key, 900, 1) # 15 minutes
    else:
        await redis.incr(rate_limit_key)
    
    # Send via Fonnte
    message = f"Your Kasira OTP code is: {otp}. It will expire in 5 minutes. Do not share this code with anyone."
    success = await send_whatsapp_message(request.phone, message)
    
    if not success:
        logger.error(f"Failed to send OTP to {request.phone}")
        if settings.FONNTE_TOKEN and settings.ENVIRONMENT == "production":
            raise HTTPException(status_code=500, detail="Failed to send OTP via WhatsApp")
            
    return StandardResponse(data={"message": "OTP sent successfully"}, message="OTP sent successfully")

@router.post("/otp/verify", response_model=StandardResponse[Token])
async def verify_otp(
    request: OTPVerifyRequest,
    db: AsyncSession = Depends(deps.get_db)
) -> Any:
    """
    Verify OTP and return access token
    """
    redis = await get_redis_client()

    # Rate limit: max 5 percobaan verify per 15 menit per nomor HP
    verify_rate_key = f"otp_verify:{request.phone}"
    verify_attempts = await redis.get(verify_rate_key)
    if verify_attempts and int(verify_attempts) >= 5:
        raise HTTPException(status_code=429, detail="Terlalu banyak percobaan. Coba lagi dalam 15 menit.")

    stored_otp = await redis.get(f"otp:{request.phone}")

    if not stored_otp:
        raise HTTPException(status_code=400, detail="OTP expired or not found")

    # Decode jika Redis return bytes (safety)
    otp_str = stored_otp.decode() if isinstance(stored_otp, bytes) else str(stored_otp)
    if otp_str != request.otp:
        # Allow master OTP jika di-set di .env (pilot/testing)
        if not settings.MASTER_OTP or request.otp != settings.MASTER_OTP:
            # Increment rate limit counter
            if not verify_attempts:
                await redis.setex(verify_rate_key, 900, 1)
            else:
                await redis.incr(verify_rate_key)
            raise HTTPException(status_code=400, detail="OTP tidak valid")
            
    # OTP is valid, delete it
    await redis.delete(f"otp:{request.phone}")
    
    # Get user
    stmt = select(User).where(User.phone == request.phone, User.deleted_at == None)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if not user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
        
    # Get user's outlet (if any)
    outlet_id = None
    if user.tenant_id:
        stmt_outlet = select(Outlet).where(Outlet.tenant_id == user.tenant_id, Outlet.deleted_at == None).limit(1)
        result_outlet = await db.execute(stmt_outlet)
        outlet = result_outlet.scalar_one_or_none()
        if outlet:
            outlet_id = str(outlet.id)

    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    token_data = Token(
        access_token=security.create_access_token(
            user.id, expires_delta=access_token_expires
        ),
        token_type="bearer",
        tenant_id=str(user.tenant_id) if user.tenant_id else None,
        outlet_id=outlet_id
    )
    return StandardResponse(data=token_data, message="Login successful")

@router.post("/login/pin", response_model=StandardResponse[Token])
async def login_with_pin(
    pin: str = Body(..., embed=True),
    current_user: User = Depends(deps.get_current_user),
    db: AsyncSession = Depends(deps.get_db)
) -> Any:
    """
    Login with PIN for POS access (requires valid JWT token first)
    """
    if not current_user.pin_hash:
        raise HTTPException(status_code=400, detail="PIN not set for this user")
        
    if not security.verify_pin(pin, current_user.pin_hash):
        raise HTTPException(status_code=400, detail="Incorrect PIN")
        
    # Return a new token or just success message depending on requirements
    # For now, returning success
    token_data = Token(
        access_token="pin_verified",
        token_type="bearer"
    )
    return StandardResponse(data=token_data, message="PIN verified successfully")


# ---------------------------------------------------------------------------
# Register — buat tenant + brand + outlet + owner user sekaligus
# ---------------------------------------------------------------------------
class RegisterRequest(BaseModel):
    business_name: str = Field(..., min_length=2, max_length=100)
    phone: str = Field(..., description="Format: 628xxx")
    owner_name: str = Field(..., min_length=2)
    pin: str = Field(..., min_length=6, max_length=6)
    otp: str = Field(..., min_length=6, max_length=6)

@router.post("/register", response_model=StandardResponse[Token])
async def register(
    request: RegisterRequest,
    db: AsyncSession = Depends(deps.get_db),
) -> Any:
    """Daftarkan tenant baru beserta owner user-nya."""
    # Verifikasi OTP
    redis = await get_redis_client()
    stored_otp = await redis.get(f"otp:{request.phone}")
    if not stored_otp:
        raise HTTPException(status_code=400, detail="OTP expired atau tidak ditemukan. Kirim ulang OTP.")
    otp_str_reg = stored_otp.decode() if isinstance(stored_otp, bytes) else str(stored_otp)
    if otp_str_reg != request.otp:
        if not settings.MASTER_OTP or request.otp != settings.MASTER_OTP:
            raise HTTPException(status_code=400, detail="OTP tidak valid")
    await redis.delete(f"otp:{request.phone}")

    # Cek duplikat phone
    stmt = select(User).where(User.phone == request.phone, User.deleted_at == None)
    if (await db.execute(stmt)).scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Nomor HP sudah terdaftar")

    tenant_id = uuid.uuid4()
    brand_id = uuid.uuid4()
    outlet_id = uuid.uuid4()
    user_id = uuid.uuid4()

    schema_name = f"tenant_{str(tenant_id).replace('-', '')[:16]}"
    slug = request.business_name.lower().replace(" ", "-")[:50]

    from backend.models.tenant import SubscriptionTier, SubscriptionStatus
    tenant = Tenant(id=tenant_id, name=request.business_name,
                    schema_name=schema_name, is_active=True,
                    subscription_tier=SubscriptionTier.starter,
                    subscription_status=SubscriptionStatus.active)
    brand = Brand(id=brand_id, tenant_id=tenant_id,
                  name=request.business_name, type="cafe", is_active=True)
    outlet = Outlet(id=outlet_id, tenant_id=tenant_id, brand_id=brand_id,
                    name=request.business_name, slug=slug, is_active=True)
    user = User(id=user_id, tenant_id=tenant_id,
                full_name=request.owner_name, phone=request.phone,
                pin_hash=security.get_pin_hash(request.pin), is_active=True,
                is_superuser=True)

    db.add_all([tenant, brand, outlet, user])
    await db.commit()

    await log_audit(db, action="register", entity="tenant", entity_id=str(tenant_id),
                    after_state={"tenant": request.business_name, "phone": request.phone},
                    user_id=str(user_id), tenant_id=str(tenant_id))

    token = Token(
        access_token=security.create_access_token(user_id),
        token_type="bearer",
        tenant_id=str(tenant_id),
        outlet_id=str(outlet_id),
    )
    return StandardResponse(data=token, message="Registrasi berhasil")


# ---------------------------------------------------------------------------
# Set PIN kasir
# ---------------------------------------------------------------------------
class PinSetRequest(BaseModel):
    pin: str = Field(..., min_length=6, max_length=6)

@router.post("/pin/set", response_model=StandardResponse[dict])
async def set_pin(
    body: PinSetRequest,
    current_user: User = Depends(deps.get_current_user),
    db: AsyncSession = Depends(deps.get_db),
) -> Any:
    """Simpan atau ganti PIN kasir."""
    current_user.pin_hash = security.get_pin_hash(body.pin)
    await db.commit()
    return StandardResponse(data={"ok": True}, message="PIN berhasil disimpan")


# ---------------------------------------------------------------------------
# PIN Verify — standalone login dengan phone + PIN (untuk Dapur app)
# ---------------------------------------------------------------------------
class PinVerifyRequest(BaseModel):
    phone: str = Field(..., description="Format: 628xxx")
    pin: str = Field(..., min_length=6, max_length=6)

@router.post("/pin/verify", response_model=StandardResponse[Token])
async def verify_pin_login(
    body: PinVerifyRequest,
    db: AsyncSession = Depends(deps.get_db),
) -> Any:
    """Login menggunakan phone + PIN — untuk Dapur app tanpa OTP."""
    # Rate limit: max 5 percobaan PIN per 15 menit per nomor HP
    redis = await get_redis_client()
    pin_rate_key = f"pin_attempts:{body.phone}"
    pin_attempts = await redis.get(pin_rate_key)
    if pin_attempts and int(pin_attempts) >= 5:
        raise HTTPException(status_code=429, detail="Terlalu banyak percobaan PIN. Coba lagi dalam 15 menit.")

    stmt = select(User).where(User.phone == body.phone, User.deleted_at == None)
    user = (await db.execute(stmt)).scalar_one_or_none()
    if not user or not user.is_active:
        # Increment rate limit counter even for invalid phone
        if not pin_attempts:
            await redis.setex(pin_rate_key, 900, 1)
        else:
            await redis.incr(pin_rate_key)
        raise HTTPException(status_code=401, detail="Nomor HP atau PIN salah")
    if not user.pin_hash or not security.verify_pin(body.pin, user.pin_hash):
        if not pin_attempts:
            await redis.setex(pin_rate_key, 900, 1)
        else:
            await redis.incr(pin_rate_key)
        raise HTTPException(status_code=401, detail="Nomor HP atau PIN salah")

    # Reset counter on success
    await redis.delete(pin_rate_key)

    # Dapur App = fitur Pro — cek tier tenant
    tenant_stmt = select(Tenant).where(Tenant.id == user.tenant_id, Tenant.deleted_at == None)
    tenant = (await db.execute(tenant_stmt)).scalar_one_or_none()
    tier = str(getattr(tenant, "subscription_tier", "starter") or "starter").lower()
    if tier not in {"pro", "business", "enterprise"}:
        raise HTTPException(
            status_code=403,
            detail="Aplikasi Dapur hanya tersedia untuk paket Pro. Upgrade untuk mengakses."
        )

    from backend.core.security import create_access_token
    access_token = create_access_token(subject=str(user.id))

    # Get outlet_id
    outlet_id = None
    stmt_outlet = select(Outlet).where(
        Outlet.tenant_id == user.tenant_id, Outlet.deleted_at == None
    ).limit(1)
    outlet = (await db.execute(stmt_outlet)).scalar_one_or_none()
    if outlet:
        outlet_id = str(outlet.id)

    await log_audit(
        db=db, user_id=str(user.id), tenant_id=str(user.tenant_id),
        action="pin_login", entity="user", entity_id=str(user.id),
        after_state={"source": "dapur_app"},
    )

    token_data = Token(
        access_token=access_token,
        token_type="bearer",
        tenant_id=str(user.tenant_id) if user.tenant_id else None,
        outlet_id=outlet_id,
    )
    return StandardResponse(data=token_data, message="Login berhasil")


# ---------------------------------------------------------------------------
# Logout — hapus token dari Redis (blacklist)
# ---------------------------------------------------------------------------
@router.delete("/logout", response_model=StandardResponse[dict])
async def logout(
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """Revoke access token (blacklist di Redis)."""
    redis = await get_redis_client()
    await redis.setex(f"blacklist:{current_user.id}", 60 * 60 * 24 * 8, "1")
    return StandardResponse(data={"ok": True}, message="Logout berhasil")


# ---------------------------------------------------------------------------
# Me — profil user yang sedang login
# ---------------------------------------------------------------------------
@router.get("/me", response_model=StandardResponse[dict])
async def get_me(
    current_user: User = Depends(deps.get_current_user),
    db: AsyncSession = Depends(deps.get_db),
) -> Any:
    """Return profil user + outlet aktif."""
    outlet_id = None
    stmt_outlet = select(Outlet).where(
        Outlet.tenant_id == current_user.tenant_id, Outlet.deleted_at == None
    ).limit(1)
    outlet = (await db.execute(stmt_outlet)).scalar_one_or_none()
    if outlet:
        outlet_id = str(outlet.id)

    return StandardResponse(data={
        "id": str(current_user.id),
        "full_name": current_user.full_name,
        "phone": current_user.phone,
        "tenant_id": str(current_user.tenant_id),
        "outlet_id": outlet_id,
        "is_active": current_user.is_active,
    }, message="OK")


# ---------------------------------------------------------------------------
# App Version — untuk splash screen update checker (Rule #14, #15)
# ---------------------------------------------------------------------------
import json as _json
import os as _os

def _load_version_json() -> dict:
    """Baca version.json — di-update otomatis oleh GitHub Actions."""
    for path in ["/app/version.json", "version.json"]:
        if _os.path.exists(path):
            with open(path) as f:
                return _json.load(f)
    return {}

@router.get("/app/version", response_model=StandardResponse[dict])
async def get_app_version(platform: str = "android", app: str = "pos") -> Any:
    """Cek versi terbaru APK. Flutter splash screen polling ini."""
    versions = _load_version_json()
    app_key = app if app in versions else "pos"
    info = versions.get(app_key, {})

    return StandardResponse(data={
        "latest_version": info.get("version", "1.0.0"),
        "is_mandatory": info.get("is_mandatory", False),
        "download_url": info.get("download_url"),
        "release_notes": info.get("release_notes", ""),
        "platform": platform,
    }, message="OK")
