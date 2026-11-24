from datetime import date
from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.dependencies import require_permission
from app.core.permissions import Permission
from app.db.session import get_db
from app.models.identity import User
from app.schemas.catalog import (
    AdminDeparturePage,
    AdminDepartureResponse,
    DepartureCreate,
    DeparturePage,
    DepartureResponse,
    DepartureUpdate,
    PublicDepartureSummary,
    PublicTourCard,
    PublicTourPage,
    TourCreate,
    TourDetailResponse,
    TourPage,
    TourResponse,
    TourUpdate,
)
from app.services.catalog_service import (
    CatalogError,
    create_departure,
    create_tour,
    get_departure,
    get_tour,
    list_departures,
    list_manageable_departures,
    list_manageable_tours,
    search_public_tours,
    update_departure,
    update_tour,
)


router = APIRouter(tags=["catalog"])
can_read_tours = require_permission(Permission.TOURS_READ)
can_write_tours = require_permission(Permission.TOURS_WRITE)
can_read_departures = require_permission(Permission.DEPARTURES_READ)
can_write_departures = require_permission(Permission.DEPARTURES_WRITE)


def catalog_error(exc: CatalogError) -> HTTPException:
    code = exc.code
    status_code = status.HTTP_404_NOT_FOUND
    if code in {"SLUG_EXISTS", "CAPACITY_BELOW_RESERVED", "INVALID_DATES"}:
        status_code = status.HTTP_409_CONFLICT
    if code in {
        "INVALID_SORT",
        "INVALID_PRICE_RANGE",
        "INVALID_DEPARTURE_DATE_RANGE",
        "INVALID_DURATION_RANGE",
        "INVALID_CURRENCY",
        "CURRENCY_REQUIRED_FOR_PRICE_FILTER",
        "CURRENCY_REQUIRED_FOR_PRICE_SORT",
    }:
        status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
    return HTTPException(
        status_code=status_code,
        detail={"code": code, "message": exc.message},
    )


@router.get("/tours", response_model=PublicTourPage)
def read_tours(
    page: int = Query(default=1, ge=1),
    size: int = Query(default=20, ge=1, le=100),
    keyword: str | None = Query(default=None, max_length=255),
    destination: str | None = Query(default=None, max_length=255),
    min_price: Decimal | None = Query(
        default=None,
        ge=0,
        max_digits=14,
        decimal_places=2,
    ),
    max_price: Decimal | None = Query(
        default=None,
        ge=0,
        max_digits=14,
        decimal_places=2,
    ),
    departure_from: date | None = Query(default=None),
    departure_to: date | None = Query(default=None),
    min_duration: int | None = Query(default=None, ge=1),
    max_duration: int | None = Query(default=None, ge=1),
    traveler_count: int | None = Query(default=None, ge=1),
    available_only: bool = Query(default=False),
    currency: str | None = Query(default=None, min_length=3, max_length=3),
    sort: str = Query(
        default="recently_added",
        pattern=r"^(-?(created_at|title|duration_days)|recently_added|price_asc|price_desc|earliest_departure)$",
    ),
    db: Session = Depends(get_db),
) -> PublicTourPage:
    try:
        results, total, pages, currencies = search_public_tours(
            db,
            page,
            size,
            keyword=keyword,
            destination=destination,
            min_price=min_price,
            max_price=max_price,
            departure_from=departure_from,
            departure_to=departure_to,
            min_duration=min_duration,
            max_duration=max_duration,
            traveler_count=traveler_count,
            available_only=available_only,
            currency=currency,
            sort=sort,
        )
        return PublicTourPage(
            items=[
                PublicTourCard(
                    **TourResponse.model_validate(result.tour).model_dump(),
                    starting_prices=[
                        {"currency": price_currency, "amount": amount}
                        for price_currency, amount in result.starting_prices
                    ],
                    next_departure=(
                        PublicDepartureSummary.model_validate(
                            result.next_departure
                        )
                        if result.next_departure is not None
                        else None
                    ),
                    has_available_departure=result.has_available_departure,
                )
                for result in results
            ],
            total=total,
            page=page,
            size=size,
            pages=pages,
            currencies=currencies,
        )
    except CatalogError as exc:
        raise catalog_error(exc) from None


@router.get("/admin/tours", response_model=TourPage)
def read_manageable_tours(
    page: int = Query(default=1, ge=1),
    size: int = Query(default=20, ge=1, le=100),
    destination: str | None = Query(default=None, max_length=255),
    sort: str = Query(
        default="-created_at",
        pattern=r"^-?(created_at|title|duration_days)$",
    ),
    db: Session = Depends(get_db),
    _user: User = Depends(can_read_tours),
) -> TourPage:
    try:
        items, total, pages = list_manageable_tours(
            db,
            page,
            size,
            destination,
            sort,
        )
        return TourPage(items=items, total=total, page=page, size=size, pages=pages)
    except CatalogError as exc:
        raise catalog_error(exc) from None


@router.get("/tours/{tour_id}", response_model=TourDetailResponse)
def read_tour(tour_id: UUID, db: Session = Depends(get_db)) -> TourDetailResponse:
    try:
        tour = get_tour(db, tour_id)
        return TourDetailResponse(
            id=tour.id,
            title=tour.title,
            slug=tour.slug,
            description=tour.description,
            duration_days=tour.duration_days,
            destination=tour.destination,
            status=tour.status,
            departures=sorted(
                tour.departures,
                key=lambda departure: (departure.start_date, departure.id),
            ),
            itinerary=sorted(
                tour.itineraries,
                key=lambda item: (item.day_number, item.sequence),
            ),
        )
    except CatalogError as exc:
        raise catalog_error(exc) from None


@router.post(
    "/tours",
    response_model=TourResponse,
    status_code=status.HTTP_201_CREATED,
)
def post_tour(
    payload: TourCreate,
    db: Session = Depends(get_db),
    _user: User = Depends(can_write_tours),
) -> TourResponse:
    try:
        return TourResponse.model_validate(create_tour(db, payload))
    except CatalogError as exc:
        raise catalog_error(exc) from None


@router.patch("/tours/{tour_id}", response_model=TourResponse)
def patch_tour(
    tour_id: UUID,
    payload: TourUpdate,
    db: Session = Depends(get_db),
    _user: User = Depends(can_write_tours),
) -> TourResponse:
    try:
        return TourResponse.model_validate(update_tour(db, tour_id, payload))
    except CatalogError as exc:
        raise catalog_error(exc) from None


@router.get("/departures", response_model=DeparturePage)
def read_departures(
    page: int = Query(default=1, ge=1),
    size: int = Query(default=20, ge=1, le=100),
    tour_id: UUID | None = None,
    start_date: date | None = None,
    db: Session = Depends(get_db),
) -> DeparturePage:
    items, total, pages = list_departures(
        db,
        page,
        size,
        tour_id,
        start_date,
    )
    return DeparturePage(items=items, total=total, page=page, size=size, pages=pages)


@router.get("/admin/departures", response_model=AdminDeparturePage)
def read_manageable_departures(
    page: int = Query(default=1, ge=1),
    size: int = Query(default=20, ge=1, le=100),
    tour_id: UUID | None = None,
    start_date: date | None = None,
    db: Session = Depends(get_db),
    _user: User = Depends(can_read_departures),
) -> AdminDeparturePage:
    items, total, pages = list_manageable_departures(
        db,
        page,
        size,
        tour_id,
        start_date,
    )
    return AdminDeparturePage(
        items=[
            AdminDepartureResponse(
                **DepartureResponse.model_validate(item).model_dump(),
                tour_title=item.tour.title,
            )
            for item in items
        ],
        total=total,
        page=page,
        size=size,
        pages=pages,
    )


@router.get("/departures/{departure_id}", response_model=DepartureResponse)
def read_departure(
    departure_id: UUID,
    db: Session = Depends(get_db),
) -> DepartureResponse:
    try:
        return DepartureResponse.model_validate(get_departure(db, departure_id))
    except CatalogError as exc:
        raise catalog_error(exc) from None


@router.post(
    "/departures",
    response_model=DepartureResponse,
    status_code=status.HTTP_201_CREATED,
)
def post_departure(
    payload: DepartureCreate,
    db: Session = Depends(get_db),
    _user: User = Depends(can_write_departures),
) -> DepartureResponse:
    try:
        return DepartureResponse.model_validate(create_departure(db, payload))
    except CatalogError as exc:
        raise catalog_error(exc) from None


@router.patch("/departures/{departure_id}", response_model=DepartureResponse)
def patch_departure(
    departure_id: UUID,
    payload: DepartureUpdate,
    db: Session = Depends(get_db),
    _user: User = Depends(can_write_departures),
) -> DepartureResponse:
    try:
        return DepartureResponse.model_validate(
            update_departure(db, departure_id, payload)
        )
    except CatalogError as exc:
        raise catalog_error(exc) from None
