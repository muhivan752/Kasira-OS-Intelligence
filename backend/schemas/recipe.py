from typing import Optional, List
from pydantic import BaseModel, ConfigDict
from uuid import UUID
from datetime import datetime
from decimal import Decimal


class RecipeIngredientInput(BaseModel):
    ingredient_id: UUID
    quantity: float
    quantity_unit: str
    is_optional: bool = False
    notes: Optional[str] = None


class RecipeCreate(BaseModel):
    product_id: UUID
    notes: Optional[str] = None
    ingredients: List[RecipeIngredientInput]


class RecipeUpdate(BaseModel):
    notes: Optional[str] = None
    ingredients: List[RecipeIngredientInput]


class RecipeIngredientResponse(BaseModel):
    id: UUID
    ingredient_id: UUID
    ingredient_name: Optional[str] = None
    ingredient_unit: Optional[str] = None
    ingredient_cost: Optional[Decimal] = None
    quantity: float
    quantity_unit: str
    is_optional: bool
    notes: Optional[str] = None
    line_cost: Optional[Decimal] = None  # quantity * ingredient_cost

    model_config = ConfigDict(from_attributes=True)


class RecipeResponse(BaseModel):
    id: UUID
    product_id: UUID
    product_name: Optional[str] = None
    version: int
    is_active: bool
    notes: Optional[str] = None
    ingredients: List[RecipeIngredientResponse] = []
    total_cost: Optional[Decimal] = None  # HPP
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class HPPIngredientDetail(BaseModel):
    name: str
    quantity: float
    unit: str
    buy_price: Decimal = Decimal("0")
    buy_qty: float = 1
    cost_per_unit: Decimal = Decimal("0")
    line_cost: Decimal = Decimal("0")


class HPPProductResponse(BaseModel):
    product_id: UUID
    product_name: str
    selling_price: Decimal
    recipe_cost: Decimal  # HPP
    margin_amount: Decimal
    margin_percent: float
    has_recipe: bool = True
    ingredients: List[HPPIngredientDetail] = []
