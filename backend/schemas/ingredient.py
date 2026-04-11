from typing import Optional, List
from pydantic import BaseModel, Field, ConfigDict
from uuid import UUID
from datetime import datetime
from decimal import Decimal


class IngredientCreate(BaseModel):
    brand_id: UUID
    name: str
    tracking_mode: str = "simple"  # simple | detail
    base_unit: str  # gram, ml, pcs
    unit_type: str  # WEIGHT, VOLUME, COUNT, CUSTOM
    cost_per_base_unit: Decimal = Decimal("0")
    ingredient_type: str = "recipe"  # recipe | overhead
    overhead_cost_per_day: Optional[Decimal] = None


class IngredientUpdate(BaseModel):
    name: Optional[str] = None
    base_unit: Optional[str] = None
    unit_type: Optional[str] = None
    cost_per_base_unit: Optional[Decimal] = None
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
    cost_per_base_unit: Decimal
    ingredient_type: str
    overhead_cost_per_day: Optional[Decimal] = None
    row_version: int
    created_at: datetime
    updated_at: datetime

    # Injected from outlet_stock join
    current_stock: Optional[float] = None
    min_stock: Optional[float] = None

    model_config = ConfigDict(from_attributes=True)


class IngredientRestock(BaseModel):
    outlet_id: UUID
    quantity: float = Field(..., gt=0)
    notes: Optional[str] = None
