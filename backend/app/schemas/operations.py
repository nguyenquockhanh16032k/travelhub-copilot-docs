from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, field_validator


class GuideCreate(BaseModel):
    full_name: str = Field(min_length=1, max_length=255)
    email: EmailStr | None = Field(default=None, max_length=255)
    phone: str | None = Field(default=None, max_length=50)
    user_id: UUID | None = None

    @field_validator("full_name")
    @classmethod
    def trim_full_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("full_name must not be empty")
        return value


class GuideUpdate(BaseModel):
    full_name: str | None = Field(default=None, min_length=1, max_length=255)
    email: EmailStr | None = Field(default=None, max_length=255)
    phone: str | None = Field(default=None, max_length=50)
    user_id: UUID | None = None

    @field_validator("full_name")
    @classmethod
    def trim_full_name(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        if not value:
            raise ValueError("full_name must not be empty")
        return value


class GuideResponse(BaseModel):
    id: UUID
    user_id: UUID | None
    full_name: str
    email: EmailStr | None
    phone: str | None

    model_config = {"from_attributes": True}


class GuidePage(BaseModel):
    items: list[GuideResponse]
    total: int
    page: int
    size: int
    pages: int


class TourAssignmentCreate(BaseModel):
    guide_id: UUID
    role: str = Field(min_length=1, max_length=100)
    status: str = Field(min_length=1, max_length=50)

    @field_validator("role", "status")
    @classmethod
    def trim_required_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("value must not be empty")
        return value


class TourAssignmentUpdate(BaseModel):
    guide_id: UUID | None = None
    role: str | None = Field(default=None, min_length=1, max_length=100)
    status: str | None = Field(default=None, min_length=1, max_length=50)

    @field_validator("role", "status")
    @classmethod
    def trim_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        if not value:
            raise ValueError("value must not be empty")
        return value


class TourAssignmentResponse(BaseModel):
    id: UUID
    departure_id: UUID
    guide_id: UUID
    role: str
    status: str
    guide: GuideResponse

    model_config = {"from_attributes": True}


class TourAssignmentPage(BaseModel):
    items: list[TourAssignmentResponse]
    total: int
    page: int
    size: int
    pages: int
