from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

DEVICE_TYPES = ("kasir", "dapur", "owner")


class DeviceRegister(BaseModel):
    """Daftar/perbarui HP ini buat notifikasi.

    `fcm_token` yang jadi identitas, bukan id perangkat: token itu yang
    dipegang Firebase, dan dia bisa berganti sendiri sewaktu-waktu.
    """
    fcm_token: str = Field(min_length=10, max_length=4096)
    outlet_id: UUID
    device_name: str = Field(default="Perangkat", max_length=120)
    device_type: str = "kasir"


class DeviceUnregister(BaseModel):
    fcm_token: str = Field(min_length=10, max_length=4096)


class DeviceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    outlet_id: Optional[UUID] = None
    device_name: str
    device_type: str
    is_revoked: bool
    last_seen_at: Optional[datetime] = None
    created_at: datetime
