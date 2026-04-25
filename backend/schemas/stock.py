from decimal import Decimal
from uuid import UUID
from pydantic import BaseModel, Field

class ProductRestock(BaseModel):
    quantity: int = Field(..., gt=0, description="Jumlah stok yang diterima")
    outlet_id: UUID = Field(..., description="Outlet yang menerima barang")
    notes: str | None = None
    unit_buy_price: Decimal | None = Field(
        None, ge=0, description="Harga beli per unit (opsional). Jika diisi, snapshot products.buy_price + total_cost di event payload."
    )
