from datetime import date
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, model_validator

from app.schemas.itinerary import ItineraryResponse


TourStatus = Literal["draft", "published", "archived"]
DepartureStatus = Literal["draft", "open", "closed", "completed", "cancelled"]


class TourCreate(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    slug: str = Field(min_length=1, max_length=255, pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
    description: str | None = Field(default=None, max_length=10000)
    duration_days: int = Field(gt=0)
    destination: str = Field(min_length=1, max_length=255)
    status: TourStatus = "draft"


class TourUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    slug: str | None = Field(
        default=None,
        min_length=1,
        max_length=255,
        pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$",
    )
    description: str | None = Field(default=None, max_length=10000)
    duration_days: int | None = Field(default=None, gt=0)
    destination: str | None = Field(default=None, min_length=1, max_length=255)
    status: TourStatus | None = None


class DepartureResponse(BaseModel):
    id: UUID
    tour_id: UUID
    start_date: date
    end_date: date
    capacity: int
    available_seats: int
    price: Decimal
    currency: str
    status: DepartureStatus

    model_config = {"from_attributes": True}


class AdminDepartureResponse(DepartureResponse):
    tour_title: str


class TourResponse(BaseModel):
    id: UUID
    title: str
    slug: str
    description: str | None
    duration_days: int
    destination: str
    status: TourStatus

    model_config = {"from_attributes": True}


class TourDetailResponse(TourResponse):
    departures: list[DepartureResponse] = []
    itinerary: list[ItineraryResponse] = []


class DepartureCreate(BaseModel):
    tour_id: UUID
    start_date: date
    end_date: date
    capacity: int = Field(gt=0)
    price: Decimal = Field(gt=0)
    currency: str = Field(default="VND", min_length=3, max_length=3)
    status: DepartureStatus = "draft"

    @model_validator(mode="after")
    def validate_dates(self) -> "DepartureCreate":
        if self.end_date < self.start_date:
            raise ValueError("end_date must not be before start_date")
        return self


class DepartureUpdate(BaseModel):
    start_date: date | None = None
    end_date: date | None = None
    capacity: int | None = Field(default=None, gt=0)
    price: Decimal | None = Field(default=None, gt=0)
    currency: str | None = Field(default=None, min_length=3, max_length=3)
    status: DepartureStatus | None = None

    @model_validator(mode="after")
    def validate_dates(self) -> "DepartureUpdate":
        if (
            self.start_date is not None
            and self.end_date is not None
            and self.end_date < self.start_date
        ):
            raise ValueError("end_date must not be before start_date")
        return self


class TourPage(BaseModel):
    items: list[TourResponse]
    total: int
    page: int
    size: int
    pages: int


class TourStartingPrice(BaseModel):
    currency: str
    amount: Decimal


class PublicDepartureSummary(BaseModel):
    id: UUID
    start_date: date
    end_date: date
    available_seats: int
    price: Decimal
    currency: str

    model_config = {"from_attributes": True}


class PublicTourCard(TourResponse):
    starting_prices: list[TourStartingPrice]
    next_departure: PublicDepartureSummary | None
    has_available_departure: bool


class PublicTourPage(BaseModel):
    items: list[PublicTourCard]
    total: int
    page: int
    size: int
    pages: int
    currencies: list[str]


class DeparturePage(BaseModel):
    items: list[DepartureResponse]
    total: int
    page: int
    size: int
    pages: int


class AdminDeparturePage(BaseModel):
    items: list[AdminDepartureResponse]
    total: int
    page: int
    size: int
    pages: int
