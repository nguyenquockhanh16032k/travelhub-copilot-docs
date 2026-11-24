from decimal import Decimal
from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, model_validator


BookingStatus = Literal[
    "pending",
    "confirmed",
    "cancelled",
    "expired",
    "rejected",
    "completed",
]
PaymentStatus = Literal["pending", "paid", "failed", "refunded"]
PaymentMethod = Literal["cash", "bank_transfer", "card", "other"]
PaymentCompletionStatus = Literal[
    "UNPAID",
    "PARTIALLY_PAID",
    "FULLY_PAID",
    "OVERPAID",
]


class TravelerInput(BaseModel):
    full_name: str = Field(min_length=1, max_length=255)
    traveler_type: str = Field(min_length=1, max_length=20)


class BookingCreate(BaseModel):
    departure_id: UUID
    customer_id: UUID | None = None
    contact_name: str = Field(min_length=1, max_length=255)
    contact_email: EmailStr
    contact_phone: str = Field(min_length=1, max_length=50)
    travelers: list[TravelerInput] = Field(min_length=1, max_length=100)
    notes: str | None = Field(default=None, max_length=5000)

    @model_validator(mode="after")
    def validate_travelers(self) -> "BookingCreate":
        if len(self.travelers) > 100:
            raise ValueError("A booking cannot contain more than 100 travelers")
        return self


class StatusChange(BaseModel):
    reason: str | None = Field(default=None, max_length=1000)


class BookingUpdate(BaseModel):
    contact_name: str | None = Field(default=None, min_length=1, max_length=255)
    contact_email: EmailStr | None = None
    contact_phone: str | None = Field(default=None, min_length=1, max_length=50)
    travelers: list[TravelerInput] | None = Field(
        default=None,
        min_length=1,
        max_length=100,
    )

    @model_validator(mode="after")
    def validate_changes(self) -> "BookingUpdate":
        if not self.model_fields_set:
            raise ValueError("At least one field must be provided")
        if any(
            field in self.model_fields_set and getattr(self, field) is None
            for field in (
                "contact_name",
                "contact_email",
                "contact_phone",
                "travelers",
            )
        ):
            raise ValueError("Updated fields cannot be null")
        return self


class PaymentCreate(BaseModel):
    booking_id: UUID
    amount: Decimal = Field(gt=0, max_digits=14, decimal_places=2)
    currency: str = Field(default="VND", min_length=3, max_length=3)
    method: PaymentMethod
    status: PaymentStatus = "pending"
    transaction_reference: str | None = Field(default=None, max_length=255)
    notes: str | None = Field(default=None, max_length=5000)


class PaymentExceptionCreate(PaymentCreate):
    status: Literal["paid"] = "paid"
    reason: str = Field(min_length=1, max_length=1000)
    confirmation: Literal[True]


class PaymentExceptionVerify(BaseModel):
    reason: str = Field(min_length=1, max_length=1000)
    confirmation: Literal[True]


class BookingCustomerResponse(BaseModel):
    id: UUID
    full_name: str
    traveler_type: str

    model_config = {"from_attributes": True}


class BookingStatusResponse(BaseModel):
    id: UUID
    old_status: str | None
    new_status: str
    actor_user_id: UUID | None
    reason: str | None
    changed_at: datetime

    model_config = {"from_attributes": True}


class CustomerPaymentResponse(BaseModel):
    id: UUID
    amount: Decimal
    currency: str
    method: PaymentMethod
    status: PaymentStatus
    transaction_reference: str | None
    recorded_at: datetime

    model_config = {"from_attributes": True}


class CustomerBookingStatusResponse(BaseModel):
    old_status: BookingStatus | None
    new_status: BookingStatus
    changed_at: datetime


class CustomerBookingResponse(BaseModel):
    id: UUID
    reference: str
    status: BookingStatus
    passenger_count: int
    total_amount: Decimal
    currency: str
    verified_paid_amount: Decimal
    outstanding_balance: Decimal
    payment_completion_status: PaymentCompletionStatus
    expires_at: datetime | None
    tour_title: str
    destination: str
    duration_days: int
    departure_start_date: date
    departure_end_date: date
    departure_status: str
    travelers: list[BookingCustomerResponse]
    status_history: list[CustomerBookingStatusResponse]
    payments: list[CustomerPaymentResponse]


class CustomerBookingPage(BaseModel):
    items: list[CustomerBookingResponse]
    total: int
    page: int
    size: int
    pages: int


class BookingResponse(BaseModel):
    id: UUID
    reference: str
    departure_id: UUID
    customer_id: UUID | None
    contact_name: str
    contact_email: str
    contact_phone: str
    passenger_count: int
    status: BookingStatus
    expires_at: datetime | None
    total_amount: Decimal
    currency: str
    notes: str | None
    travelers: list[BookingCustomerResponse] = []
    status_history: list[BookingStatusResponse] = []

    model_config = {"from_attributes": True}


class StaffBookingResponse(BaseModel):
    id: UUID
    reference: str
    departure_id: UUID
    customer_id: UUID | None
    contact_name: str
    contact_email: str
    contact_phone: str
    passenger_count: int
    status: BookingStatus
    expires_at: datetime | None
    notes: str | None
    travelers: list[BookingCustomerResponse] = []
    status_history: list[BookingStatusResponse] = []

    model_config = {"from_attributes": True}


class PaymentResponse(BaseModel):
    id: UUID
    booking_id: UUID
    amount: Decimal
    currency: str
    method: PaymentMethod
    status: PaymentStatus
    transaction_reference: str | None
    notes: str | None
    requires_resolution: bool
    resolution_reason: str | None
    recorded_at: datetime

    model_config = {"from_attributes": True}


class PaymentAdminResponse(PaymentResponse):
    booking_reference: str
    booking_status: BookingStatus
    booking_total: Decimal
    verified_paid_amount: Decimal
    outstanding_balance: Decimal
    overpaid_amount: Decimal
    payment_completion_status: PaymentCompletionStatus
    recorded_by: str | None
    verified_by: str | None


class PaymentBookingSummary(BaseModel):
    booking_id: UUID
    booking_reference: str
    booking_status: BookingStatus
    booking_total: Decimal
    currency: str
    verified_paid_amount: Decimal
    outstanding_balance: Decimal
    overpaid_amount: Decimal
    payment_completion_status: PaymentCompletionStatus


class PaymentPage(BaseModel):
    items: list[PaymentAdminResponse]
    total: int
    page: int
    size: int
    pages: int
    booking_summary: PaymentBookingSummary | None = None
