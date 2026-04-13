from typing import Optional
from pydantic import BaseModel

class Token(BaseModel):
    access_token: str
    token_type: str
    tenant_id: Optional[str] = None
    outlet_id: Optional[str] = None
    stock_mode: Optional[str] = None

class TokenPayload(BaseModel):
    sub: Optional[str] = None
