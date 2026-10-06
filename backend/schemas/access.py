from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, StrictBool, field_validator


POS_PERMISSIONS = frozenset({
    "pos.sell", "pos.refund", "pos.refund.approve", "pos.discount.override",
    "pos.shift.manage", "pos.cash.manage", "pos.kitchen", "sales.detail.view",
    "stock.view", "stock.receive", "stock.adjust", "customers.lookup",
})

BUSINESS_PERMISSIONS = frozenset({
    "finance.view", "finance.manage", "purchasing.view", "purchasing.manage",
    "supplier.price.view", "customers.view", "customers.manage", "customers.export",
    "hpp.view", "hpp.manage", "hpp.approve",
})


PERMISSIONS = frozenset({
    "pos.sell", "pos.refund", "pos.refund.approve", "pos.discount.override",
    "pos.shift.manage", "pos.cash.manage", "pos.kitchen",
    "sales.view", "sales.detail.view", "hpp.view", "hpp.manage", "hpp.approve",
    "stock.view", "stock.receive", "stock.adjust", "purchasing.view", "purchasing.manage",
    "supplier.price.view", "finance.view", "finance.manage", "customers.lookup",
    "customers.view", "customers.manage", "customers.export", "hris.self",
    "hris.employees.manage", "hris.schedules.manage", "hris.attendance.manage",
    "hris.exceptions.approve", "access.manage", "ai.chat",
})
HRIS_MANAGE = frozenset({"hris.employees.manage", "hris.schedules.manage", "hris.attendance.manage"})


class AccessPolicy(BaseModel):
    model_config = ConfigDict(extra="forbid")

    version: Literal[1]
    permissions: dict[str, StrictBool] = Field(default_factory=dict)
    outlet_ids: list[UUID] = Field(default_factory=list, max_length=100)
    brand_ids: list[UUID] = Field(default_factory=list, max_length=100)

    @field_validator("version", mode="before")
    @classmethod
    def integer_version(cls, value):
        if type(value) is not int:
            raise ValueError("Version must be an integer")
        return value

    @field_validator("permissions")
    @classmethod
    def known_permissions(cls, value):
        if value.keys() - PERMISSIONS:
            raise ValueError("Unknown permission")
        return value

    @field_validator("outlet_ids", "brand_ids")
    @classmethod
    def unique_targets(cls, value):
        if len(set(value)) != len(value):
            raise ValueError("Duplicate scope target")
        return value
