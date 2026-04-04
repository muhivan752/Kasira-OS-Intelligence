from uuid import UUID
from pydantic import BaseModel, Field

class ProductRestock(BaseModel):
    quantity: int = Field(..., gt=0, description="Jumlah stok yang diterima")
    outlet_id: UUID = Field(..., description="Outlet yang menerima barang")
    notes: str | None = None
