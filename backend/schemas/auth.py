from pydantic import BaseModel, Field

class OTPSendRequest(BaseModel):
    phone: str = Field(..., description="Phone number in international format, e.g., 628123456789")

class OTPVerifyRequest(BaseModel):
    phone: str = Field(..., description="Phone number in international format, e.g., 628123456789")
    otp: str = Field(..., description="6-digit OTP code")
