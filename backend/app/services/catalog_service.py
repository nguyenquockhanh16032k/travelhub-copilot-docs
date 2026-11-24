from dataclasses import dataclass
import math
from datetime import date
from decimal import Decimal
from uuid import UUID

import pycountry
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload
from sqlalchemy.sql.elements import ColumnElement

from app.core.business_time import business_date
from app.models.tour import Tour, TourDeparture
from app.schemas.catalog import (
    DepartureCreate,
    DepartureUpdate,
    TourCreate,
    TourUpdate,
)
from app.services.booking_service import expire_pending_bookings


class CatalogError(Exception):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


@dataclass(frozen=True)
class PublicTourSearchItem:
    tour: Tour
    starting_prices: list[tuple[str, Decimal]]
    next_departure: TourDeparture | None
    has_available_departure: bool


def _is_iso_currency(value: str) -> bool:
    return (
        len(value) == 3
        and value.isupper()
        and pycountry.currencies.get(alpha_3=value) is not None
    )


def _contains_pattern(value: str) -> str:
    escaped = value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"%{escaped}%"


def _public_departure_filters(
    today: date,
    departure_from: date | None,
    departure_to: date | None,
    currency: str | None,
    min_price: Decimal | None,
    max_price: Decimal | None,
) -> list[ColumnElement[bool]]:
    filters: list[ColumnElement[bool]] = [
        TourDeparture.status == "open",
        TourDeparture.start_date >= today,
    ]
    if departure_from is not None:
        filters.append(TourDeparture.start_date >= departure_from)
    if departure_to is not None:
        filters.append(TourDeparture.start_date <= departure_to)
    if currency is not None:
        filters.append(TourDeparture.currency == currency)
    if min_price is not None:
        filters.append(TourDeparture.price >= min_price)
    if max_price is not None:
        filters.append(TourDeparture.price <= max_price)
    return filters


def _public_currencies(
    db: Session,
    tour_filters: list[ColumnElement[bool]],
    today: date,
    departure_from: date | None,
    departure_to: date | None,
    traveler_count: int | None,
) -> list[str]:
    departure_filters: list[ColumnElement[bool]] = [
        TourDeparture.status == "open",
        TourDeparture.start_date >= today,
        TourDeparture.available_seats >= max(traveler_count or 1, 1),
    ]
    if departure_from is not None:
        departure_filters.append(TourDeparture.start_date >= departure_from)
    if departure_to is not None:
        departure_filters.append(TourDeparture.start_date <= departure_to)
    values = db.scalars(
        select(TourDeparture.currency)
        .join(Tour, Tour.id == TourDeparture.tour_id)
        .where(*tour_filters, *departure_filters)
        .distinct()
        .order_by(TourDeparture.currency)
    )
    return [value for value in values if _is_iso_currency(value)]


def list_tours(
    db: Session,
    page: int,
    size: int,
    destination: str | None,
    sort: str,
) -> tuple[list[Tour], int, int]:
    return _list_tours(db, page, size, destination, sort, published_only=True)


def search_public_tours(
    db: Session,
    page: int,
    size: int,
    *,
    keyword: str | None,
    destination: str | None,
    min_price: Decimal | None,
    max_price: Decimal | None,
    departure_from: date | None,
    departure_to: date | None,
    min_duration: int | None,
    max_duration: int | None,
    traveler_count: int | None,
    available_only: bool,
    currency: str | None,
    sort: str,
) -> tuple[list[PublicTourSearchItem], int, int, list[str]]:
    if min_price is not None and max_price is not None and min_price > max_price:
        raise CatalogError("INVALID_PRICE_RANGE", "min_price must not exceed max_price")
    if departure_from is not None and departure_to is not None:
        if departure_from > departure_to:
            raise CatalogError(
                "INVALID_DEPARTURE_DATE_RANGE",
                "departure_from must not be after departure_to",
            )
    if min_duration is not None and max_duration is not None:
        if min_duration > max_duration:
            raise CatalogError(
                "INVALID_DURATION_RANGE",
                "min_duration must not exceed max_duration",
            )
    if currency is not None and not _is_iso_currency(currency):
        raise CatalogError(
            "INVALID_CURRENCY",
            "currency must be an uppercase ISO 4217 currency code",
        )
    if (min_price is not None or max_price is not None) and currency is None:
        raise CatalogError(
            "CURRENCY_REQUIRED_FOR_PRICE_FILTER",
            "Select a currency before filtering by price",
        )
    if sort in {"price_asc", "price_desc"} and currency is None:
        raise CatalogError(
            "CURRENCY_REQUIRED_FOR_PRICE_SORT",
            "Select a currency before sorting by price",
        )

    tour_filters: list[ColumnElement[bool]] = [Tour.status == "published"]
    if keyword and keyword.strip():
        pattern = _contains_pattern(keyword.strip())
        tour_filters.append(
            or_(
                Tour.title.ilike(pattern, escape="\\"),
                Tour.description.ilike(pattern, escape="\\"),
            )
        )
    if destination and destination.strip():
        tour_filters.append(
            Tour.destination.ilike(
                _contains_pattern(destination.strip()),
                escape="\\",
            )
        )
    if min_duration is not None:
        tour_filters.append(Tour.duration_days >= min_duration)
    if max_duration is not None:
        tour_filters.append(Tour.duration_days <= max_duration)

    today = business_date()
    departure_filters = _public_departure_filters(
        today,
        departure_from,
        departure_to,
        currency,
        min_price,
        max_price,
    )
    required_seats = max(traveler_count or 1, 1)
    bookable_departure_filters = [
        *departure_filters,
        TourDeparture.available_seats >= required_seats,
    ]
    candidate_departures = (
        select(TourDeparture.id)
        .join(Tour, Tour.id == TourDeparture.tour_id)
        .where(*tour_filters, *departure_filters)
    )
    expire_pending_bookings(db, departure_ids=candidate_departures)

    has_departure_filters = any(
        value is not None
        for value in (
            departure_from,
            departure_to,
            currency,
            min_price,
            max_price,
            traveler_count,
        )
    ) or available_only
    matching_departure = (
        select(TourDeparture.id)
        .where(
            TourDeparture.tour_id == Tour.id,
            *bookable_departure_filters,
        )
        .exists()
    )

    tour_query = select(Tour).where(*tour_filters)
    count_query = select(func.count(Tour.id)).where(*tour_filters)
    if has_departure_filters:
        tour_query = tour_query.where(matching_departure)
        count_query = count_query.where(matching_departure)

    if sort == "recently_added":
        order_clause = Tour.created_at.desc()
    elif sort in {"price_asc", "price_desc"}:
        price_order = (
            select(func.min(TourDeparture.price))
            .where(
                TourDeparture.tour_id == Tour.id,
                *bookable_departure_filters,
            )
            .scalar_subquery()
        )
        order_clause = (
            price_order.desc().nulls_last()
            if sort == "price_desc"
            else price_order.asc().nulls_last()
        )
    elif sort == "earliest_departure":
        departure_order = (
            select(func.min(TourDeparture.start_date))
            .where(
                TourDeparture.tour_id == Tour.id,
                *bookable_departure_filters,
            )
            .scalar_subquery()
        )
        order_clause = departure_order.asc().nulls_last()
    else:
        sort_fields = {
            "created_at": Tour.created_at,
            "title": Tour.title,
            "duration_days": Tour.duration_days,
        }
        descending = sort.startswith("-")
        field_name = sort.lstrip("-")
        if field_name not in sort_fields:
            raise CatalogError("INVALID_SORT", "Unsupported tour sort field")
        sort_column = sort_fields[field_name]
        order_clause = sort_column.desc() if descending else sort_column.asc()

    tours = list(
        db.scalars(
            tour_query.order_by(order_clause, Tour.id.asc())
            .offset((page - 1) * size)
            .limit(size)
        )
    )
    total = int(db.scalar(count_query) or 0)
    pages = math.ceil(total / size) if total else 0
    currencies = _public_currencies(
        db,
        tour_filters,
        today,
        departure_from,
        departure_to,
        traveler_count,
    )
    if not tours:
        return [], total, pages, currencies

    tour_ids = [tour.id for tour in tours]
    price_rows = db.execute(
        select(
            TourDeparture.tour_id,
            TourDeparture.currency,
            func.min(TourDeparture.price),
        )
        .where(
            TourDeparture.tour_id.in_(tour_ids),
            *bookable_departure_filters,
        )
        .group_by(TourDeparture.tour_id, TourDeparture.currency)
    )
    prices_by_tour: dict[UUID, list[tuple[str, Decimal]]] = {}
    for tour_id, price_currency, amount in price_rows:
        if _is_iso_currency(price_currency):
            prices_by_tour.setdefault(tour_id, []).append(
                (price_currency, amount)
            )
    for prices in prices_by_tour.values():
        prices.sort(key=lambda item: item[0])

    ranked_departures = (
        select(
            TourDeparture.id.label("id"),
            func.row_number()
            .over(
                partition_by=TourDeparture.tour_id,
                order_by=(TourDeparture.start_date, TourDeparture.id),
            )
            .label("position"),
        )
        .where(
            TourDeparture.tour_id.in_(tour_ids),
            *bookable_departure_filters,
        )
        .subquery()
    )
    next_departures = {
        departure.tour_id: departure
        for departure in db.scalars(
            select(TourDeparture)
            .join(ranked_departures, ranked_departures.c.id == TourDeparture.id)
            .where(ranked_departures.c.position == 1)
        )
    }

    results = [
        PublicTourSearchItem(
            tour=tour,
            starting_prices=prices_by_tour.get(tour.id, []),
            next_departure=next_departures.get(tour.id),
            has_available_departure=tour.id in next_departures,
        )
        for tour in tours
    ]
    return results, total, pages, currencies


def list_manageable_tours(
    db: Session,
    page: int,
    size: int,
    destination: str | None,
    sort: str,
) -> tuple[list[Tour], int, int]:
    return _list_tours(db, page, size, destination, sort, published_only=False)


def _list_tours(
    db: Session,
    page: int,
    size: int,
    destination: str | None,
    sort: str,
    published_only: bool,
) -> tuple[list[Tour], int, int]:
    sort_fields = {
        "created_at": Tour.created_at,
        "title": Tour.title,
        "duration_days": Tour.duration_days,
    }
    descending = sort.startswith("-")
    field_name = sort.lstrip("-")
    if field_name not in sort_fields:
        raise CatalogError("INVALID_SORT", "Unsupported tour sort field")

    query = select(Tour)
    count_query = select(func.count(Tour.id))
    if published_only:
        query = query.where(Tour.status == "published")
        count_query = count_query.where(Tour.status == "published")
    if destination:
        query = query.where(Tour.destination.ilike(f"%{destination}%"))
        count_query = count_query.where(Tour.destination.ilike(f"%{destination}%"))

    column = sort_fields[field_name]
    query = query.order_by(column.desc() if descending else column.asc())
    query = query.offset((page - 1) * size).limit(size)

    items = list(db.scalars(query))
    total = int(db.scalar(count_query) or 0)
    pages = math.ceil(total / size) if total else 0
    return items, total, pages


def get_tour(db: Session, tour_id: UUID) -> Tour:
    today = business_date()
    candidate_departures = (
        select(TourDeparture.id)
        .join(Tour, Tour.id == TourDeparture.tour_id)
        .where(
            Tour.id == tour_id,
            Tour.status == "published",
            TourDeparture.status == "open",
            TourDeparture.start_date >= today,
        )
    )
    expire_pending_bookings(db, departure_ids=candidate_departures)
    tour = db.scalar(
        select(Tour)
        .where(Tour.id == tour_id)
        .options(
            selectinload(Tour.itineraries),
            selectinload(
                Tour.departures.and_(
                    TourDeparture.status == "open",
                    TourDeparture.start_date >= today,
                    TourDeparture.available_seats > 0,
                )
            ),
        )
    )
    if tour is None or tour.status != "published":
        raise CatalogError("TOUR_NOT_FOUND", "Published tour not found")
    return tour


def create_tour(db: Session, payload: TourCreate) -> Tour:
    if db.scalar(select(Tour).where(Tour.slug == payload.slug)) is not None:
        raise CatalogError("SLUG_EXISTS", "A tour with this slug already exists")

    tour = Tour(**payload.model_dump())
    db.add(tour)
    db.commit()
    db.refresh(tour)
    return tour


def update_tour(db: Session, tour_id: UUID, payload: TourUpdate) -> Tour:
    tour = db.get(Tour, tour_id)
    if tour is None:
        raise CatalogError("TOUR_NOT_FOUND", "Tour not found")

    values = payload.model_dump(exclude_unset=True)
    if "slug" in values:
        existing = db.scalar(
            select(Tour).where(Tour.slug == values["slug"], Tour.id != tour_id)
        )
        if existing is not None:
            raise CatalogError("SLUG_EXISTS", "A tour with this slug already exists")

    for field, value in values.items():
        setattr(tour, field, value)
    db.commit()
    db.refresh(tour)
    return tour


def list_departures(
    db: Session,
    page: int,
    size: int,
    tour_id: UUID | None,
    start_date: date | None,
) -> tuple[list[TourDeparture], int, int]:
    today = business_date()
    public_filters = [
        Tour.status == "published",
        TourDeparture.status == "open",
        TourDeparture.start_date >= today,
    ]
    if tour_id is not None:
        public_filters.append(TourDeparture.tour_id == tour_id)
    if start_date:
        public_filters.append(TourDeparture.start_date >= start_date)

    candidate_departures = (
        select(TourDeparture.id)
        .join(Tour, Tour.id == TourDeparture.tour_id)
        .where(*public_filters)
    )
    expire_pending_bookings(db, departure_ids=candidate_departures)

    eligible_filters = [*public_filters, TourDeparture.available_seats > 0]
    query = (
        select(TourDeparture)
        .join(Tour, Tour.id == TourDeparture.tour_id)
        .where(*eligible_filters)
        .order_by(TourDeparture.start_date.asc(), TourDeparture.id.asc())
        .offset((page - 1) * size)
        .limit(size)
    )
    items = list(db.scalars(query))
    count_query = (
        select(func.count(TourDeparture.id))
        .join(Tour, Tour.id == TourDeparture.tour_id)
        .where(*eligible_filters)
    )
    total = int(db.scalar(count_query) or 0)
    pages = math.ceil(total / size) if total else 0
    return items, total, pages


def list_manageable_departures(
    db: Session,
    page: int,
    size: int,
    tour_id: UUID | None,
    start_date: date | None,
) -> tuple[list[TourDeparture], int, int]:
    query = select(TourDeparture).options(selectinload(TourDeparture.tour))
    count_query = select(func.count(TourDeparture.id))
    if tour_id is not None:
        query = query.where(TourDeparture.tour_id == tour_id)
        count_query = count_query.where(TourDeparture.tour_id == tour_id)
    if start_date is not None:
        query = query.where(TourDeparture.start_date >= start_date)
        count_query = count_query.where(TourDeparture.start_date >= start_date)

    query = (
        query.order_by(TourDeparture.start_date.asc(), TourDeparture.id)
        .offset((page - 1) * size)
        .limit(size)
    )
    items = list(db.scalars(query))
    total = int(db.scalar(count_query) or 0)
    pages = math.ceil(total / size) if total else 0
    return items, total, pages


def get_departure(db: Session, departure_id: UUID) -> TourDeparture:
    today = business_date()
    candidate_departures = (
        select(TourDeparture.id)
        .join(Tour, Tour.id == TourDeparture.tour_id)
        .where(
            TourDeparture.id == departure_id,
            Tour.status == "published",
            TourDeparture.status == "open",
            TourDeparture.start_date >= today,
        )
    )
    expire_pending_bookings(db, departure_ids=candidate_departures)
    departure = db.scalar(
        select(TourDeparture)
        .join(Tour, Tour.id == TourDeparture.tour_id)
        .where(
            TourDeparture.id == departure_id,
            Tour.status == "published",
            TourDeparture.status == "open",
            TourDeparture.start_date >= today,
            TourDeparture.available_seats > 0,
        )
    )
    if departure is None:
        raise CatalogError("DEPARTURE_NOT_FOUND", "Bookable departure not found")
    return departure


def create_departure(db: Session, payload: DepartureCreate) -> TourDeparture:
    tour = db.get(Tour, payload.tour_id)
    if tour is None:
        raise CatalogError("TOUR_NOT_FOUND", "Tour not found")

    departure = TourDeparture(
        **payload.model_dump(),
        available_seats=payload.capacity,
    )
    db.add(departure)
    db.commit()
    db.refresh(departure)
    return departure


def update_departure(
    db: Session,
    departure_id: UUID,
    payload: DepartureUpdate,
) -> TourDeparture:
    departure = db.get(TourDeparture, departure_id)
    if departure is None:
        raise CatalogError("DEPARTURE_NOT_FOUND", "Departure not found")

    values = payload.model_dump(exclude_unset=True)
    reserved = departure.capacity - departure.available_seats
    if "capacity" in values:
        if values["capacity"] < reserved:
            raise CatalogError(
                "CAPACITY_BELOW_RESERVED",
                "Capacity cannot be lower than reserved seats",
            )
        values["available_seats"] = values["capacity"] - reserved

    if "start_date" in values and "end_date" not in values:
        if departure.end_date < values["start_date"]:
            raise CatalogError("INVALID_DATES", "end_date must not be before start_date")
    if "end_date" in values and "start_date" not in values:
        if values["end_date"] < departure.start_date:
            raise CatalogError("INVALID_DATES", "end_date must not be before start_date")

    for field, value in values.items():
        setattr(departure, field, value)
    db.commit()
    db.refresh(departure)
    return departure
