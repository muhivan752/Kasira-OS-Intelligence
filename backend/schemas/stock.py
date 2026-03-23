from pydantic import BaseModel, Field

class ProductRestock(BaseModel):
    quantity: int = Field(..., gt=0, description="Quantity to add to stock")
    notes: str | None = None
