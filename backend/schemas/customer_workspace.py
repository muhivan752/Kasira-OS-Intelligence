import re
from datetime import date, datetime
from zoneinfo import ZoneInfo
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


def normalize_phone(value: str | None) -> str | None:
    if not value or not value.strip():
        return None
    if re.search(r"[^0-9+ ()-]", value):
        raise ValueError("Nomor HP hanya boleh berisi angka dan tanda pemisah")
    digits = re.sub(r"\D", "", value)
    if digits.startswith("0"):
        digits = "62" + digits[1:]
    if not 8 <= len(digits) <= 15:
        raise ValueError("Nomor HP harus 8 sampai 15 digit setelah normalisasi. Gunakan 08 atau kode negara")
    return digits


class CustomerFields(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    name: str = Field(min_length=1, max_length=120)
    phone: str | None = Field(default=None, max_length=40)
    email: str | None = Field(default=None, max_length=254)
    notes: str | None = Field(default=None, max_length=2000)
    birthday: date | None = None
    wa_marketing_consent: bool = False

    @field_validator("phone")
    @classmethod
    def phone_format(cls, value):
        return normalize_phone(value)

    @field_validator("email")
    @classmethod
    def email_format(cls, value):
        if not value:
            return None
        if not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", value):
            raise ValueError("Alamat email belum valid")
        return value

    @field_validator("notes")
    @classmethod
    def optional_text(cls, value):
        return value or None

    @field_validator("birthday")
    @classmethod
    def birthday_past(cls, value):
        if value and value > datetime.now(ZoneInfo("Asia/Jakarta")).date():
            raise ValueError("Tanggal lahir tidak boleh di masa depan")
        return value


class CustomerSave(CustomerFields):
    client_request_id: UUID
    row_version: int | None = Field(default=None, ge=0)


class CustomerNote(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    client_request_id: UUID
    body: str = Field(min_length=1, max_length=500)
    kind: Literal["note", "complaint"] = "note"
