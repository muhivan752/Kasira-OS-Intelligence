from typing import Optional, List
from pydantic import BaseModel, Field, ConfigDict, model_validator
from uuid import UUID
from datetime import datetime
from decimal import Decimal


class IngredientCreate(BaseModel):
    brand_id: UUID
    name: str
    tracking_mode: str = "simple"  # simple | detail
    base_unit: str  # gram, ml, pcs
    unit_type: str  # WEIGHT, VOLUME, COUNT, CUSTOM
    buy_price: Decimal = Decimal("0")  # Harga beli (Rp14.000)
    buy_qty: float = Field(1, gt=0)    # Qty beli dalam base_unit (1000 gram)
    ingredient_type: str = "recipe"  # recipe | overhead
    overhead_cost_per_day: Optional[Decimal] = None

    @model_validator(mode='after')
    def calculate_cost(self):
        """Auto-calculate cost_per_base_unit from buy_price / buy_qty."""
        # Validation only — actual cost stored in route handler
        return self


class IngredientUpdate(BaseModel):
    name: Optional[str] = None
    base_unit: Optional[str] = None
    unit_type: Optional[str] = None
    buy_price: Optional[Decimal] = None
    buy_qty: Optional[float] = Field(None, gt=0)
    ingredient_type: Optional[str] = None
    overhead_cost_per_day: Optional[Decimal] = None
    row_version: int


class IngredientResponse(BaseModel):
    id: UUID
    brand_id: UUID
    name: str
    tracking_mode: str
    base_unit: str
    unit_type: str
    buy_price: Decimal
    buy_qty: float
    cost_per_base_unit: Decimal  # auto-calculated: buy_price / buy_qty
    ingredient_type: str
    overhead_cost_per_day: Optional[Decimal] = None
    row_version: int
    created_at: datetime
    updated_at: datetime

    # Injected from outlet_stock join
    current_stock: Optional[float] = None
    min_stock: Optional[float] = None

    # Injected: recipe usage info
    used_in: Optional[list] = None  # [{product_name, qty_per_serving, unit}]

    model_config = ConfigDict(from_attributes=True)


class IngredientRestock(BaseModel):
    outlet_id: UUID
    quantity: float = Field(..., gt=0)
    notes: Optional[str] = None
