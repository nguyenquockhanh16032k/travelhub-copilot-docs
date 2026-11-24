from datetime import date
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel


class UpcomingDepartureSummary(BaseModel):
    id: UUID
    tour_title: str
    start_date: date
    end_date: date
    available_seats: int
    price: Decimal
    currency: str


class PaymentCurrencySummary(BaseModel):
    currency: str
    paid_amount: Decimal
    pending_amount: Decimal


class DashboardSummary(BaseModel):
    booking_count: int
    pending_booking_count: int
    upcoming_departures: list[UpcomingDepartureSummary]
    payments_by_currency: list[PaymentCurrencySummary]


class OperationalDepartureSummary(BaseModel):
    id: UUID
    tour_title: str
    start_date: date
    end_date: date
    available_seats: int


class OperationalDashboardSummary(BaseModel):
    booking_count: int
    pending_booking_count: int
    upcoming_departures: list[OperationalDepartureSummary]
