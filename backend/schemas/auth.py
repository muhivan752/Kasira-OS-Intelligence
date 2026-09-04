from typing import Literal, Optional
from pydantic import BaseModel, Field

class OTPSendRequest(BaseModel):
    phone: str = Field(..., description="Phone number in international format, e.g., 628123456789")
    purpose: Optional[Literal["login", "register"]] = Field("login", description="login = existing user, register = new user")
    # Kanal dipilih USER di layar masuk/daftar, bukan ditebak server. Kode
    # nggak pernah loncat kanal: minta Sefrekuensi tapi nomornya nggak ada
    # di sana = 404 SEFREKUENSI_NOT_FOUND, bukan diam diam lewat WA.
    channel: Literal["whatsapp", "sefrekuensi"] = Field("whatsapp", description="Kanal pengiriman kode")

class OTPVerifyRequest(BaseModel):
    phone: str = Field(..., description="Phone number in international format, e.g., 628123456789")
    otp: str = Field(..., description="6-digit OTP code")
