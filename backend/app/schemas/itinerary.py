from uuid import UUID

from pydantic import BaseModel, Field


class ItineraryCreate(BaseModel):
    day_number: int = Field(gt=0)
    sequence: int = Field(gt=0)
    activity: str = Field(min_length=1, max_length=255)
    time: str | None = Field(default=None, max_length=50)
    location: str | None = Field(default=None, max_length=255)
    description: str | None = Field(default=None, max_length=10000)


class ItineraryUpdate(BaseModel):
    day_number: int | None = Field(default=None, gt=0)
    sequence: int | None = Field(default=None, gt=0)
    activity: str | None = Field(default=None, min_length=1, max_length=255)
    time: str | None = Field(default=None, max_length=50)
    location: str | None = Field(default=None, max_length=255)
    description: str | None = Field(default=None, max_length=10000)


class ItineraryResponse(BaseModel):
    id: UUID
    tour_id: UUID
    day_number: int
    sequence: int
    activity: str
    time: str | None
    location: str | None
    description: str | None

    model_config = {"from_attributes": True}
