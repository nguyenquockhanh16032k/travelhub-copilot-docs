from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.api.dependencies import require_permission
from app.core.permissions import Permission
from app.db.session import get_db
from app.models.identity import User
from app.schemas.itinerary import (
    ItineraryCreate,
    ItineraryResponse,
    ItineraryUpdate,
)
from app.services.itinerary_service import (
    ItineraryError,
    create_itinerary_item,
    delete_itinerary_item,
    list_itineraries,
    update_itinerary_item,
)


router = APIRouter(
    prefix="/tours/{tour_id}/itineraries",
    tags=["itineraries"],
)
can_read_itineraries = require_permission(Permission.ITINERARIES_READ)
can_write_itineraries = require_permission(Permission.ITINERARIES_WRITE)


def itinerary_error(exc: ItineraryError) -> HTTPException:
    status_code = status.HTTP_404_NOT_FOUND
    if exc.code in {"ITINERARY_POSITION_EXISTS"}:
        status_code = status.HTTP_409_CONFLICT
    if exc.code == "INVALID_ITINERARY":
        status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
    return HTTPException(
        status_code=status_code,
        detail={"code": exc.code, "message": exc.message},
    )


@router.get("", response_model=list[ItineraryResponse])
def read_itineraries(
    tour_id: UUID,
    db: Session = Depends(get_db),
    _user: User = Depends(can_read_itineraries),
) -> list[ItineraryResponse]:
    try:
        return [
            ItineraryResponse.model_validate(item)
            for item in list_itineraries(db, tour_id)
        ]
    except ItineraryError as exc:
        raise itinerary_error(exc) from None


@router.post(
    "",
    response_model=ItineraryResponse,
    status_code=status.HTTP_201_CREATED,
)
def post_itinerary_item(
    tour_id: UUID,
    payload: ItineraryCreate,
    db: Session = Depends(get_db),
    _user: User = Depends(can_write_itineraries),
) -> ItineraryResponse:
    try:
        item = create_itinerary_item(db, tour_id, payload)
        return ItineraryResponse.model_validate(item)
    except ItineraryError as exc:
        raise itinerary_error(exc) from None


@router.patch("/{itinerary_id}", response_model=ItineraryResponse)
def patch_itinerary_item(
    tour_id: UUID,
    itinerary_id: UUID,
    payload: ItineraryUpdate,
    db: Session = Depends(get_db),
    _user: User = Depends(can_write_itineraries),
) -> ItineraryResponse:
    try:
        item = update_itinerary_item(db, tour_id, itinerary_id, payload)
        return ItineraryResponse.model_validate(item)
    except ItineraryError as exc:
        raise itinerary_error(exc) from None


@router.delete(
    "/{itinerary_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def remove_itinerary_item(
    tour_id: UUID,
    itinerary_id: UUID,
    db: Session = Depends(get_db),
    _user: User = Depends(can_write_itineraries),
) -> Response:
    try:
        delete_itinerary_item(db, tour_id, itinerary_id)
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    except ItineraryError as exc:
        raise itinerary_error(exc) from None
