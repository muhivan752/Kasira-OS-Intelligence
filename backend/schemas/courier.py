"""Kurir toko (delivery gelombang 2)."""
from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

VEHICLES = ('motor', 'mobil', 'sepeda', 'jalan_kaki')


class CourierBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=80)
    phone: Optional[str] = Field(None, max_length=20)
    vehicle: str = Field('motor', max_length=20)
    is_active: bool = True
    sort_order: int = 0


class CourierCreate(CourierBase):
    outlet_id: Optional[UUID] = None
    user_id: Optional[UUID] = None


class CourierUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=80)
    phone: Optional[str] = Field(None, max_length=20)
    vehicle: Optional[str] = Field(None, max_length=20)
    is_active: Optional[bool] = None
    sort_order: Optional[int] = None
    user_id: Optional[UUID] = None
    row_version: int


class CourierResponse(CourierBase):
    id: UUID
    outlet_id: Optional[UUID] = None
    user_id: Optional[UUID] = None
    row_version: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class OrderDispatch(BaseModel):
    """Kasir nyerahin pesanan ke kurir. Boleh pilih kurir terdaftar, boleh
    ketik nama buat yang sekali jalan (tetangga, ojol panggilan)."""
    courier_id: Optional[UUID] = None
    courier_name: Optional[str] = Field(None, max_length=80)


class OrderDelivered(BaseModel):
    """Serah terima. Dua-duanya opsional: kurir kehujanan nggak boleh kejebak
    wajib foto, dan yang nerima nggak selalu mau nyebut nama."""
    proof_image_url: Optional[str] = Field(None, max_length=500)
    received_by: Optional[str] = Field(None, max_length=80)


class OrderDeliveryFailed(BaseModel):
    reason: str = Field(..., min_length=3, max_length=200)
