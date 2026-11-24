from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING
import uuid

from sqlalchemy import (
    CheckConstraint,
    Date,
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

if TYPE_CHECKING:
    from app.models.itinerary import TourItinerary
    from app.models.operations import TourAssignment, TourExpense


tour_status = Enum(
    "draft",
    "published",
    "archived",
    name="tour_status",
    create_constraint=True,
)

departure_status = Enum(
    "draft",
    "open",
    "closed",
    "completed",
    "cancelled",
    name="departure_status",
    create_constraint=True,
)


class Tour(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "tours"
    __table_args__ = (UniqueConstraint("slug", name="uq_tours_slug"),)

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    duration_days: Mapped[int] = mapped_column(
        Integer,
        CheckConstraint("duration_days > 0", name="ck_tours_duration_positive"),
        nullable=False,
    )
    destination: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(tour_status, default="draft", nullable=False)

    departures: Mapped[list["TourDeparture"]] = relationship(
        "TourDeparture",
        back_populates="tour",
        cascade="all, delete-orphan",
    )
    itineraries: Mapped[list["TourItinerary"]] = relationship(
        "TourItinerary",
        back_populates="tour",
        cascade="all, delete-orphan",
    )


class TourDeparture(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "tour_departures"
    __table_args__ = (
        CheckConstraint("capacity >= 0", name="ck_tour_departures_capacity"),
        CheckConstraint(
            "available_seats >= 0",
            name="ck_tour_departures_available_seats",
        ),
        CheckConstraint(
            "available_seats <= capacity",
            name="ck_tour_departures_available_seats_capacity",
        ),
        CheckConstraint(
            "price >= 0",
            name="ck_tour_departures_price",
        ),
    )

    tour_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("tours.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    capacity: Mapped[int] = mapped_column(Integer, nullable=False)
    available_seats: Mapped[int] = mapped_column(Integer, nullable=False)
    price: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="VND", nullable=False)
    status: Mapped[str] = mapped_column(
        departure_status,
        default="draft",
        nullable=False,
    )

    tour: Mapped[Tour] = relationship(Tour, back_populates="departures")
    assignments: Mapped[list["TourAssignment"]] = relationship(
        "TourAssignment",
        back_populates="departure",
    )
    expenses: Mapped[list["TourExpense"]] = relationship(
        "TourExpense",
        back_populates="departure",
    )
