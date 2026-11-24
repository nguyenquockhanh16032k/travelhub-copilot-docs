from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.itinerary import TourItinerary
from app.models.tour import Tour
from app.schemas.itinerary import ItineraryCreate, ItineraryUpdate


class ItineraryError(Exception):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


def list_itineraries(db: Session, tour_id: UUID) -> list[TourItinerary]:
    if db.get(Tour, tour_id) is None:
        raise ItineraryError("TOUR_NOT_FOUND", "Tour not found")
    return list(
        db.scalars(
            select(TourItinerary)
            .where(TourItinerary.tour_id == tour_id)
            .order_by(TourItinerary.day_number, TourItinerary.sequence)
        )
    )


def create_itinerary_item(
    db: Session,
    tour_id: UUID,
    payload: ItineraryCreate,
) -> TourItinerary:
    if db.get(Tour, tour_id) is None:
        raise ItineraryError("TOUR_NOT_FOUND", "Tour not found")
    if _position_exists(db, tour_id, payload.day_number, payload.sequence):
        raise ItineraryError(
            "ITINERARY_POSITION_EXISTS",
            "An itinerary item already uses this day and sequence",
        )

    item = TourItinerary(tour_id=tour_id, **payload.model_dump())
    db.add(item)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        if _is_position_conflict(exc):
            raise ItineraryError(
                "ITINERARY_POSITION_EXISTS",
                "An itinerary item already uses this day and sequence",
            ) from None
        raise
    db.refresh(item)
    return item


def update_itinerary_item(
    db: Session,
    tour_id: UUID,
    itinerary_id: UUID,
    payload: ItineraryUpdate,
) -> TourItinerary:
    item = db.scalar(
        select(TourItinerary).where(
            TourItinerary.id == itinerary_id,
            TourItinerary.tour_id == tour_id,
        )
    )
    if item is None:
        raise ItineraryError("ITINERARY_NOT_FOUND", "Itinerary item not found")

    values = payload.model_dump(exclude_unset=True)
    for required_field in ("day_number", "sequence", "activity"):
        if required_field in values and values[required_field] is None:
            raise ItineraryError(
                "INVALID_ITINERARY",
                f"{required_field} cannot be null",
            )

    day_number = values.get("day_number", item.day_number)
    sequence = values.get("sequence", item.sequence)
    if _position_exists(db, tour_id, day_number, sequence, exclude_id=item.id):
        raise ItineraryError(
            "ITINERARY_POSITION_EXISTS",
            "An itinerary item already uses this day and sequence",
        )

    for field, value in values.items():
        setattr(item, field, value)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        if _is_position_conflict(exc):
            raise ItineraryError(
                "ITINERARY_POSITION_EXISTS",
                "An itinerary item already uses this day and sequence",
            ) from None
        raise
    db.refresh(item)
    return item


def delete_itinerary_item(
    db: Session,
    tour_id: UUID,
    itinerary_id: UUID,
) -> None:
    item = db.scalar(
        select(TourItinerary).where(
            TourItinerary.id == itinerary_id,
            TourItinerary.tour_id == tour_id,
        )
    )
    if item is None:
        raise ItineraryError("ITINERARY_NOT_FOUND", "Itinerary item not found")
    db.delete(item)
    db.commit()


def _position_exists(
    db: Session,
    tour_id: UUID,
    day_number: int,
    sequence: int,
    exclude_id: UUID | None = None,
) -> bool:
    query = select(TourItinerary.id).where(
        TourItinerary.tour_id == tour_id,
        TourItinerary.day_number == day_number,
        TourItinerary.sequence == sequence,
    )
    if exclude_id is not None:
        query = query.where(TourItinerary.id != exclude_id)
    return db.scalar(query) is not None


def _is_position_conflict(exc: IntegrityError) -> bool:
    diagnostic = getattr(exc.orig, "diag", None)
    if (
        getattr(diagnostic, "constraint_name", None)
        == "uq_tour_itineraries_tour_day_sequence"
    ):
        return True
    return (
        "UNIQUE constraint failed: tour_itineraries.tour_id, "
        "tour_itineraries.day_number, tour_itineraries.sequence"
    ) in str(exc.orig)
