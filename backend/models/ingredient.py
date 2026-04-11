from sqlalchemy import Column, String, Boolean, ForeignKey, Integer, Numeric, Float
from sqlalchemy.dialects.postgresql import UUID, ENUM
from sqlalchemy.orm import relationship
from backend.models.base import BaseModel


class Ingredient(BaseModel):
    __tablename__ = "ingredients"

    brand_id = Column(UUID(as_uuid=True), ForeignKey('brands.id', ondelete='CASCADE'), nullable=False)
    name = Column(String, nullable=False)
    tracking_mode = Column(ENUM('simple', 'detail', name='tracking_mode', create_type=False), nullable=False)
    base_unit = Column(String, nullable=False)  # e.g. "gram", "ml", "pcs"
    unit_type = Column(ENUM('WEIGHT', 'VOLUME', 'COUNT', 'CUSTOM', name='unit_type', create_type=False), nullable=False)
    buy_price = Column(Numeric(12, 2), server_default='0', nullable=False)
    buy_qty = Column(Float, server_default='1', nullable=False)
    cost_per_base_unit = Column(Numeric(12, 2), server_default='0', nullable=False)
    ai_setup_complete = Column(Boolean, server_default='false', nullable=False)
    needs_review = Column(Boolean, server_default='false', nullable=False)
    ingredient_type = Column(ENUM('recipe', 'overhead', name='ingredient_type', create_type=False), server_default='recipe', nullable=False)
    overhead_cost_per_day = Column(Numeric(12, 2), nullable=True)
    row_version = Column(Integer, server_default='0', nullable=False)

    # Relationships
    recipe_ingredients = relationship("RecipeIngredient", back_populates="ingredient")
    outlet_stocks = relationship("OutletStock", back_populates="ingredient")
