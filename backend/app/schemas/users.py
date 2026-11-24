from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, model_validator


AssignableRole = Literal["ADMIN", "STAFF", "CUSTOMER"]
UserRole = Literal["SUPER_ADMIN", "ADMIN", "STAFF", "CUSTOMER"]


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    role: UserRole


class UserUpdate(BaseModel):
    email: EmailStr | None = None
    password: str | None = Field(default=None, min_length=8, max_length=128)
    role: UserRole | None = None
    is_active: bool | None = None

    @model_validator(mode="after")
    def validate_changes(self) -> "UserUpdate":
        if not self.model_fields_set:
            raise ValueError("At least one field must be provided")
        if any(
            field in self.model_fields_set and getattr(self, field) is None
            for field in ("email", "password", "role", "is_active")
        ):
            raise ValueError("Updated fields cannot be null")
        return self


class UserResponse(BaseModel):
    id: UUID
    email: str
    is_active: bool
    roles: list[str]
    created_at: datetime


class UserPage(BaseModel):
    items: list[UserResponse]
    total: int
    page: int
    size: int
    pages: int


class AssignableRoleResponse(BaseModel):
    code: AssignableRole
    description: str
