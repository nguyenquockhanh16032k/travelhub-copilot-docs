import re
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class SupplierCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    service_category: str = Field(min_length=1, max_length=100)

    @field_validator("name", "service_category")
    @classmethod
    def trim_required_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("value must not be empty")
        return value


class SupplierUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    service_category: str | None = Field(default=None, min_length=1, max_length=100)

    @field_validator("name", "service_category")
    @classmethod
    def trim_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        if not value:
            raise ValueError("value must not be empty")
        return value


class SupplierResponse(BaseModel):
    id: UUID
    name: str
    service_category: str

    model_config = {"from_attributes": True}


class SupplierPage(BaseModel):
    items: list[SupplierResponse]
    total: int
    page: int
    size: int
    pages: int


class TourExpenseCreate(BaseModel):
    supplier_id: UUID | None = None
    category: str = Field(min_length=1, max_length=100)
    amount: Decimal = Field(gt=0, max_digits=14, decimal_places=2)
    currency: str = Field(min_length=3, max_length=3)
    status: str = Field(min_length=1, max_length=50)
    note: str | None = Field(default=None, max_length=5000)

    @field_validator("category", "status")
    @classmethod
    def trim_required_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("value must not be empty")
        return value

    @field_validator("currency")
    @classmethod
    def normalize_currency(cls, value: str) -> str:
        value = value.strip()
        if not re.fullmatch(r"[A-Za-z]{3}", value):
            raise ValueError("currency must be a three-letter code")
        return value.upper()


class TourExpenseUpdate(BaseModel):
    supplier_id: UUID | None = None
    category: str | None = Field(default=None, min_length=1, max_length=100)
    amount: Decimal | None = Field(
        default=None,
        gt=0,
        max_digits=14,
        decimal_places=2,
    )
    currency: str | None = Field(default=None, min_length=3, max_length=3)
    status: str | None = Field(default=None, min_length=1, max_length=50)
    note: str | None = Field(default=None, max_length=5000)

    @field_validator("category", "status")
    @classmethod
    def trim_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        if not value:
            raise ValueError("value must not be empty")
        return value

    @field_validator("currency")
    @classmethod
    def normalize_optional_currency(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        if not re.fullmatch(r"[A-Za-z]{3}", value):
            raise ValueError("currency must be a three-letter code")
        return value.upper()


class TourExpenseResponse(BaseModel):
    id: UUID
    departure_id: UUID
    supplier_id: UUID | None
    category: str
    amount: Decimal
    currency: str
    status: str
    note: str | None
    supplier: SupplierResponse | None

    model_config = {"from_attributes": True}


class TourExpensePage(BaseModel):
    items: list[TourExpenseResponse]
    total: int
    page: int
    size: int
    pages: int
