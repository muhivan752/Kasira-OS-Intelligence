import re
from typing import Annotated, Literal
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field, StrictBool, field_validator, model_validator


class AccountBody(BaseModel):
    model_config = ConfigDict(extra="forbid")


class UsernameBody(AccountBody):
    shop_username: str = Field(min_length=3, max_length=64)
    username: str = Field(default="owner", min_length=3, max_length=64)

    @field_validator("shop_username", "username")
    @classmethod
    def username_format(cls, value):
        value = value.strip().lower()
        if not re.fullmatch(r"[a-z0-9][a-z0-9_-]{2,63}", value):
            raise ValueError("Gunakan 3 sampai 64 huruf, angka, tanda hubung atau garis bawah")
        return value


class PasswordLogin(UsernameBody):
    password: str = Field(min_length=1, max_length=128)

    @field_validator("username", mode="before")
    @classmethod
    def phone_login(cls, value):
        if isinstance(value, str) and re.fullmatch(r"[+\d ()-]{3,40}", value.strip()):
            from backend.schemas.customer_workspace import normalize_phone
            try:
                return normalize_phone(value)
            except ValueError:
                return value
        return value


class NewPassword(UsernameBody):
    password: str = Field(min_length=8, max_length=128)
    client_request_id: UUID


class PasswordRegister(NewPassword):
    business_name: str = Field(min_length=2, max_length=100)
    owner_name: str = Field(min_length=2, max_length=120)
    business_type: Literal["cafe", "resto", "warung", "other"] = "cafe"

    @field_validator("username")
    @classmethod
    def owner_username(cls, value):
        if value != "owner":
            raise ValueError("Akun pemilik menggunakan username owner")
        return value


class PasswordClaim(NewPassword):
    current_password: str | None = Field(default=None, max_length=128)


class ConsumeChallenge(UsernameBody):
    code: str = Field(min_length=32, max_length=128)
    password: str = Field(min_length=8, max_length=128)
    purpose: Literal["activation", "recovery"]
    client_request_id: UUID


class AccountRequest(AccountBody):
    client_request_id: UUID


HRIS_PERMISSIONS = frozenset({"hris.self", "hris.employees.manage", "hris.schedules.manage", "hris.attendance.manage", "hris.accounts.manage"})
from backend.schemas.access import POS_PERMISSIONS, BUSINESS_PERMISSIONS
SUPPORTED_ROLE_PERMISSIONS = HRIS_PERMISSIONS | POS_PERMISSIONS | BUSINESS_PERMISSIONS | {"ai.chat"}


class RoleSave(AccountRequest):
    id: UUID
    name: str = Field(min_length=2, max_length=100)
    row_version: Annotated[int, Field(strict=True, ge=0)] = 0
    scope: Literal["outlet", "tenant"] = "outlet"
    outlet_ids: list[UUID] = Field(max_length=100)
    permissions: dict[str, StrictBool]

    @model_validator(mode="after")
    def scope_targets(self):
        if (self.scope == "outlet" and not self.outlet_ids) or (self.scope == "tenant" and self.outlet_ids):
            raise ValueError("Pilih outlet untuk cakupan outlet; cakupan bisnis tidak memakai daftar outlet")
        return self

    @field_validator("permissions")
    @classmethod
    def supported_permissions(cls, value):
        if set(value) - SUPPORTED_ROLE_PERMISSIONS:
            raise ValueError("Izin jabatan belum didukung")
        return value

    @field_validator("outlet_ids")
    @classmethod
    def unique_outlets(cls, value):
        if len(set(value)) != len(value):
            raise ValueError("Outlet tidak boleh berulang")
        return value


class EmployeeAccountSave(AccountRequest):
    row_version: Annotated[int, Field(strict=True, ge=1)]
    user_row_version: Annotated[int, Field(strict=True, ge=1)] | None = None
    username: str = Field(min_length=3, max_length=64)
    role_id: UUID | None = None
    is_active: StrictBool = True

    @field_validator("username")
    @classmethod
    def staff_username(cls, value):
        value = UsernameBody.username_format(value)
        if value == "owner":
            raise ValueError("Username owner khusus pemilik")
        return value


class EmployeeLoginSetup(AccountBody):
    use_phone: StrictBool = False
    username: str | None = Field(default=None, min_length=3, max_length=64)
    role_id: UUID | None = None
    user_row_version: Annotated[int, Field(strict=True, ge=1)] | None = None
    password: str | None = Field(default=None, min_length=8, max_length=128)

    @field_validator("username")
    @classmethod
    def staff_username(cls, value):
        return EmployeeAccountSave.staff_username(value) if value is not None else None

    @model_validator(mode="after")
    def identifier(self):
        if not self.use_phone and not self.username:
            raise ValueError("Isi username akun atau gunakan nomor HP")
        return self
