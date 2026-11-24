import uuid

from sqlalchemy import (
    CheckConstraint,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import Uuid

from app.db.base import Base, TimestampMixin, UUIDMixin
from app.models.tour import Tour


class TourItinerary(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "tour_itineraries"
    __table_args__ = (
        CheckConstraint("day_number > 0", name="day_number"),
        CheckConstraint("sequence > 0", name="sequence"),
        UniqueConstraint(
            "tour_id",
            "day_number",
            "sequence",
            name="uq_tour_itineraries_tour_day_sequence",
        ),
    )

    tour_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("tours.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    day_number: Mapped[int] = mapped_column(Integer, nullable=False)
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    activity: Mapped[str] = mapped_column(String(255), nullable=False)
    time: Mapped[str | None] = mapped_column(String(50), nullable=True)
    location: Mapped[str | None] = mapped_column(String(255), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    tour: Mapped[Tour] = relationship(Tour, back_populates="itineraries")
