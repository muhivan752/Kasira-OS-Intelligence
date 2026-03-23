from typing import Optional
from pydantic import BaseModel, UUID4
from datetime import datetime

class TenantBase(BaseModel):
    name: str
    schema_name: str
    is_active: Optional[bool] = True

class TenantCreate(TenantBase):
    pass

class TenantUpdate(TenantBase):
    name: Optional[str] = None
    schema_name: Optional[str] = None

class TenantInDBBase(TenantBase):
    id: UUID4
    row_version: int
    created_at: datetime
    updated_at: datetime
    deleted_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class Tenant(TenantInDBBase):
    pass
