from datetime import datetime
from decimal import Decimal
import uuid

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import Uuid

from app.db.base import Base, TimestampMixin, UUIDMixin
from app.models.customer import Customer
from app.models.identity import User
from app.models.tour import TourDeparture


booking_status = Enum(
    "pending",
    "confirmed",
    "cancelled",
    "expired",
    "rejected",
    "completed",
    name="booking_status",
    create_constraint=True,
)

payment_status = Enum(
    "pending",
    "paid",
    "failed",
    "refunded",
    name="payment_status",
    create_constraint=True,
)

payment_method = Enum(
    "cash",
    "bank_transfer",
    "card",
    "other",
    name="payment_method",
    create_constraint=True,
)


class Booking(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "bookings"
    __table_args__ = (UniqueConstraint("reference", name="uq_bookings_reference"),)

    reference: Mapped[str] = mapped_column(String(32), nullable=False)
    departure_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("tour_departures.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    customer_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("customers.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    contact_name: Mapped[str] = mapped_column(String(255), nullable=False)
    contact_email: Mapped[str] = mapped_column(String(255), nullable=False)
    contact_phone: Mapped[str] = mapped_column(String(50), nullable=False)
    passenger_count: Mapped[int] = mapped_column(
        Integer,
        CheckConstraint("passenger_count > 0", name="ck_bookings_passenger_count"),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        booking_status,
        default="pending",
        nullable=False,
    )
    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        index=True,
    )
    total_amount: Mapped[Decimal] = mapped_column(
        Numeric(14, 2),
        CheckConstraint("total_amount >= 0", name="ck_bookings_total_amount"),
        nullable=False,
    )
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    departure: Mapped[TourDeparture] = relationship(TourDeparture)
    customer: Mapped[Customer | None] = relationship(Customer)
    created_by_user: Mapped[User | None] = relationship(User)
    travelers: Mapped[list["BookingCustomer"]] = relationship(
        "BookingCustomer",
        back_populates="booking",
        cascade="all, delete-orphan",
    )
    status_history: Mapped[list["BookingStatusHistory"]] = relationship(
        "BookingStatusHistory",
        back_populates="booking",
        cascade="all, delete-orphan",
    )
    payments: Mapped[list["Payment"]] = relationship(
        "Payment",
        back_populates="booking",
        cascade="all, delete-orphan",
    )


class BookingCustomer(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "booking_customers"

    booking_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("bookings.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    traveler_type: Mapped[str] = mapped_column(String(20), nullable=False)

    booking: Mapped[Booking] = relationship(Booking, back_populates="travelers")


class BookingStatusHistory(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "booking_status_history"

    booking_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("bookings.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    old_status: Mapped[str | None] = mapped_column(String(20), nullable=True)
    new_status: Mapped[str] = mapped_column(String(20), nullable=False)
    actor_user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    changed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    booking: Mapped[Booking] = relationship(
        Booking,
        back_populates="status_history",
    )
    actor: Mapped[User | None] = relationship(User)


class Payment(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "payments"
    __table_args__ = (
        CheckConstraint("amount > 0", name="ck_payments_amount"),
        UniqueConstraint("transaction_reference", name="uq_payments_transaction_reference"),
    )

    booking_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("bookings.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    method: Mapped[str] = mapped_column(payment_method, nullable=False)
    status: Mapped[str] = mapped_column(
        payment_status,
        default="pending",
        nullable=False,
    )
    transaction_reference: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    requires_resolution: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )
    resolution_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    idempotency_key: Mapped[str | None] = mapped_column(
        String(128),
        nullable=True,
        unique=True,
    )
    idempotency_fingerprint: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
    )
    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    booking: Mapped[Booking] = relationship(Booking, back_populates="payments")
