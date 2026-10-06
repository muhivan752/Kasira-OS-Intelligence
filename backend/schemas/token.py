from typing import Optional
from pydantic import BaseModel

class Token(BaseModel):
    access_token: str
    token_type: str
    tenant_id: Optional[str] = None
    outlet_id: Optional[str] = None
    stock_mode: Optional[str] = None
    subscription_tier: Optional[str] = None
    phone: Optional[str] = None
    user_id: Optional[str] = None
    username: Optional[str] = None
    shop_username: Optional[str] = None
    access: Optional[dict] = None

class TokenPayload(BaseModel):
    sub: Optional[str] = None
