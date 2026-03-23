from typing import Generic, TypeVar, Optional, Any
from pydantic import BaseModel, Field
from backend.core.request_context import get_request_id

DataT = TypeVar('DataT')

class ResponseMeta(BaseModel):
    page: Optional[int] = None
    per_page: Optional[int] = None
    total: Optional[int] = None
    total_pages: Optional[int] = None

class StandardResponse(BaseModel, Generic[DataT]):
    success: bool = True
    data: Optional[DataT] = None
    meta: Optional[ResponseMeta] = None
    request_id: str = Field(default_factory=get_request_id)
    message: Optional[str] = None
