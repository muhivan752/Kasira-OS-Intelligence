import random
import logging
from datetime import timedelta
from typing import Any

from fastapi import APIRouter, Body, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from backend.api import deps
from backend.core import security
from backend.core.config import settings
from backend.models.user import User
from backend.schemas.token import Token
from backend.schemas.auth import OTPSendRequest, OTPVerifyRequest
from backend.schemas.response import StandardResponse
from backend.services.fonnte import send_whatsapp_message
from backend.services.redis import get_redis_client

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
    # Check if user exists
    stmt = select(User).where(User.phone == request.phone, User.deleted_at == None)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    
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
    if current_count and int(current_count) >= 3:
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
        logger.error(f"Failed to send OTP to {request.phone}. OTP was {otp}")
        # We might still want to return success in dev if Fonnte is not configured
        if settings.FONNTE_TOKEN:
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
    stored_otp = await redis.get(f"otp:{request.phone}")
    
    if not stored_otp:
        raise HTTPException(status_code=400, detail="OTP expired or not found")
        
    if stored_otp != request.otp:
        # For development, allow a master OTP if configured, or just fail
        if request.otp != "123456" or settings.ENVIRONMENT == "production":
            raise HTTPException(status_code=400, detail="Invalid OTP")
            
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
        
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    token_data = Token(
        access_token=security.create_access_token(
            user.id, expires_delta=access_token_expires
        ),
        token_type="bearer"
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
