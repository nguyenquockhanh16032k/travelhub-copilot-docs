from uuid import UUID

from pydantic import BaseModel, EmailStr, Field


class CustomerCreate(BaseModel):
    full_name: str = Field(min_length=1, max_length=255)
    email: EmailStr | None = None
    phone: str | None = Field(default=None, max_length=50)
    address: str | None = Field(default=None, max_length=500)
    user_id: UUID | None = None


class CustomerUpdate(BaseModel):
    full_name: str | None = Field(default=None, min_length=1, max_length=255)
    email: EmailStr | None = None
    phone: str | None = Field(default=None, max_length=50)
    address: str | None = Field(default=None, max_length=500)
    user_id: UUID | None = None


class CustomerResponse(BaseModel):
    id: UUID
    full_name: str
    email: str | None
    phone: str | None
    address: str | None
    user_id: UUID | None

    model_config = {"from_attributes": True}


class CustomerPage(BaseModel):
    items: list[CustomerResponse]
    total: int
    page: int
    size: int
    pages: int


class CustomerAccountOption(BaseModel):
    id: UUID
    email: EmailStr


class CustomerAccountPage(BaseModel):
    items: list[CustomerAccountOption]
    total: int
    page: int
    size: int
    pages: int
