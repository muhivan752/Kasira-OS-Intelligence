from sqlalchemy import Column, String, Boolean, ForeignKey, Integer, Float, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from backend.models.base import BaseModel


class Recipe(BaseModel):
    __tablename__ = "recipes"

    product_id = Column(UUID(as_uuid=True), ForeignKey('products.id', ondelete='CASCADE'), nullable=False)
    version = Column(Integer, server_default='1', nullable=False)
    is_active = Column(Boolean, server_default='true', nullable=False)
    ai_assisted = Column(Boolean, server_default='false', nullable=False)
    created_by = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    notes = Column(Text, nullable=True)
    row_version = Column(Integer, server_default='0', nullable=False)

    # Relationships
    product = relationship("Product", back_populates="recipes")
    ingredients = relationship("RecipeIngredient", back_populates="recipe", lazy="selectin")


class RecipeIngredient(BaseModel):
    __tablename__ = "recipe_ingredients"

    recipe_id = Column(UUID(as_uuid=True), ForeignKey('recipes.id', ondelete='CASCADE'), nullable=False)
    ingredient_id = Column(UUID(as_uuid=True), ForeignKey('ingredients.id', ondelete='RESTRICT'), nullable=False)
    quantity = Column(Float, nullable=False)
    quantity_unit = Column(String, nullable=False)
    notes = Column(Text, nullable=True)
    is_optional = Column(Boolean, server_default='false', nullable=False)
    row_version = Column(Integer, server_default='0', nullable=False)

    # Relationships
    recipe = relationship("Recipe", back_populates="ingredients")
    ingredient = relationship("Ingredient", back_populates="recipe_ingredients")
