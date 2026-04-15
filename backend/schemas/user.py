from typing import Optional
from pydantic import BaseModel, UUID4, model_validator
from datetime import datetime
from backend.utils.phone import mask_phone

# Shared properties
class UserBase(BaseModel):
    phone: Optional[str] = None
    is_active: Optional[bool] = True
    is_superuser: bool = False
    full_name: Optional[str] = None
    tenant_id: Optional[UUID4] = None
    role_id: Optional[UUID4] = None

# Properties to receive via API on creation
class UserCreate(UserBase):
    phone: str
    full_name: str
    tenant_id: UUID4

class UserCreateWithPIN(UserCreate):
    pin: Optional[str] = None

# Properties to receive via API on update
class UserUpdate(UserBase):
    pin: Optional[str] = None

class UserInDBBase(UserBase):
    id: UUID4
    created_at: datetime
    updated_at: datetime
    deleted_at: Optional[datetime] = None
    row_version: int

    class Config:
        from_attributes = True

# Additional properties to return via API
class User(UserInDBBase):
    @model_validator(mode="after")
    def _mask(self):
        self.phone = mask_phone(self.phone)
        return self

# Additional properties stored in DB
class UserInDB(UserInDBBase):
    pin_hash: Optional[str] = None
