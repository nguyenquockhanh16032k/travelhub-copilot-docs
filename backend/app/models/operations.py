import uuid
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, ForeignKey, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import Uuid

from app.db.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.identity import User
    from app.models.tour import TourDeparture


class Guide(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "guides"
    __table_args__ = (
        CheckConstraint("length(trim(full_name)) > 0", name="ck_guides_full_name"),
    )

    user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(50), nullable=True)

    user: Mapped["User | None"] = relationship("User")
    assignments: Mapped[list["TourAssignment"]] = relationship(
        "TourAssignment",
        back_populates="guide",
    )


class TourAssignment(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "tour_assignments"
    __table_args__ = (
        CheckConstraint("length(trim(role)) > 0", name="ck_tour_assignments_role"),
        CheckConstraint(
            "length(trim(status)) > 0",
            name="ck_tour_assignments_status",
        ),
    )

    departure_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("tour_departures.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    guide_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("guides.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    role: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False)

    departure: Mapped["TourDeparture"] = relationship(
        "TourDeparture",
        back_populates="assignments",
    )
    guide: Mapped[Guide] = relationship(Guide, back_populates="assignments")


class Supplier(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "suppliers"
    __table_args__ = (
        CheckConstraint("length(trim(name)) > 0", name="ck_suppliers_name"),
        CheckConstraint(
            "length(trim(service_category)) > 0",
            name="ck_suppliers_service_category",
        ),
    )

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    service_category: Mapped[str] = mapped_column(String(100), nullable=False)

    expenses: Mapped[list["TourExpense"]] = relationship(
        "TourExpense",
        back_populates="supplier",
    )


class TourExpense(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "tour_expenses"
    __table_args__ = (
        CheckConstraint("amount > 0", name="ck_tour_expenses_amount"),
        CheckConstraint(
            "length(trim(category)) > 0",
            name="ck_tour_expenses_category",
        ),
        CheckConstraint(
            "length(trim(status)) > 0",
            name="ck_tour_expenses_status",
        ),
    )

    departure_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("tour_departures.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    supplier_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("suppliers.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    category: Mapped[str] = mapped_column(String(100), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)

    departure: Mapped["TourDeparture"] = relationship(
        "TourDeparture",
        back_populates="expenses",
    )
    supplier: Mapped[Supplier | None] = relationship(
        Supplier,
        back_populates="expenses",
    )
