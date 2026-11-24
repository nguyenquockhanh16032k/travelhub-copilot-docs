from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from types import SimpleNamespace
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.models.booking import Booking
from app.api.dependencies import get_current_user
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models.identity import Role
from app.models.tour import Tour, TourDeparture


@pytest.fixture
def catalog_context(monkeypatch):
    from app.services import catalog_service

    monkeypatch.setattr(
        catalog_service,
        "business_date",
        lambda: date(2026, 1, 1),
    )
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        published = Tour(
            title="Da Lat",
            slug="da-lat",
            description="Da Lat tour",
            duration_days=3,
            destination="Da Lat",
            status="published",
        )
        draft = Tour(
            title="Hidden Tour",
            slug="hidden-tour",
            duration_days=2,
            destination="Hue",
            status="draft",
        )
        session.add_all([published, draft])
        session.flush()
        session.add(
            TourDeparture(
                tour_id=published.id,
                start_date=date(2026, 12, 1),
                end_date=date(2026, 12, 3),
                capacity=20,
                available_seats=20,
                price=Decimal("3500000.00"),
                currency="VND",
                status="open",
            )
        )
        session.commit()
        published_id = published.id

    def override_db():
        with Session(engine) as session:
            yield session

    admin = SimpleNamespace(
        roles=[Role(code="ADMIN", description="Administrator")]
    )
    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_current_user] = lambda: admin

    with TestClient(app) as client:
        yield client, engine, published_id

    app.dependency_overrides.clear()
    engine.dispose()


def _add_tour(
    engine,
    *,
    title: str,
    slug: str,
    destination: str,
    duration_days: int,
    description: str | None = None,
    status: str = "published",
    departures: list[dict] | None = None,
) -> UUID:
    with Session(engine) as session:
        tour = Tour(
            title=title,
            slug=slug,
            description=description,
            duration_days=duration_days,
            destination=destination,
            status=status,
        )
        session.add(tour)
        session.flush()
        for values in departures or []:
            session.add(
                TourDeparture(
                    tour_id=tour.id,
                    start_date=values["start_date"],
                    end_date=values["end_date"],
                    capacity=values["capacity"],
                    available_seats=values["available_seats"],
                    price=Decimal(values["price"]),
                    currency=values.get("currency", "VND"),
                    status=values.get("status", "open"),
                )
            )
        session.commit()
        return tour.id


def test_public_tour_listing_excludes_drafts(catalog_context) -> None:
    client, _, _ = catalog_context

    response = client.get("/api/v1/tours")

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["items"][0]["slug"] == "da-lat"
    assert body["items"][0]["starting_prices"] == [
        {"currency": "VND", "amount": "3500000.00"}
    ]
    assert body["items"][0]["next_departure"]["start_date"] == "2026-12-01"


def test_admin_tour_listing_includes_drafts(catalog_context) -> None:
    client, _, _ = catalog_context

    response = client.get("/api/v1/admin/tours")

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 2
    assert {item["status"] for item in body["items"]} == {"draft", "published"}


def test_admin_tour_listing_requires_staff_role(catalog_context) -> None:
    client, _, _ = catalog_context
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(
        roles=[Role(code="CUSTOMER", description="Customer")]
    )

    response = client.get("/api/v1/admin/tours")

    assert response.status_code == 403


def test_public_tour_detail_has_open_departures(catalog_context) -> None:
    client, _, published_id = catalog_context

    response = client.get(f"/api/v1/tours/{published_id}")

    assert response.status_code == 200
    body = response.json()
    assert body["slug"] == "da-lat"
    assert len(body["departures"]) == 1
    assert body["departures"][0]["available_seats"] == 20


def test_admin_can_create_tour(catalog_context) -> None:
    client, _, _ = catalog_context

    response = client.post(
        "/api/v1/tours",
        json={
            "title": "Ha Long",
            "slug": "ha-long",
            "description": "Ha Long tour",
            "duration_days": 2,
            "destination": "Ha Long",
            "status": "published",
        },
    )

    assert response.status_code == 201
    assert response.json()["slug"] == "ha-long"


def test_admin_can_update_tour(catalog_context) -> None:
    client, _, published_id = catalog_context

    response = client.patch(
        f"/api/v1/tours/{published_id}",
        json={"title": "Updated Da Lat"},
    )

    assert response.status_code == 200
    assert response.json()["title"] == "Updated Da Lat"
    assert response.json()["slug"] == "da-lat"


def test_duplicate_slug_is_rejected(catalog_context) -> None:
    client, _, _ = catalog_context

    response = client.post(
        "/api/v1/tours",
        json={
            "title": "Duplicate",
            "slug": "da-lat",
            "duration_days": 2,
            "destination": "Da Lat",
            "status": "published",
        },
    )

    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "SLUG_EXISTS"


def test_public_search_requires_one_departure_to_match_all_departure_filters(
    catalog_context,
) -> None:
    client, engine, _ = catalog_context
    _add_tour(
        engine,
        title="Split departure match",
        slug="split-departure-match",
        destination="Coast",
        duration_days=5,
        description="A beach escape",
        departures=[
            {
                "start_date": date(2026, 6, 1),
                "end_date": date(2026, 6, 5),
                "capacity": 4,
                "available_seats": 4,
                "price": "500000.00",
            },
            {
                "start_date": date(2026, 12, 10),
                "end_date": date(2026, 12, 14),
                "capacity": 8,
                "available_seats": 8,
                "price": "800000.00",
            },
        ],
    )
    _add_tour(
        engine,
        title="Coastal holiday",
        slug="coastal-holiday",
        destination="Coast",
        duration_days=5,
        description="A beach escape",
        departures=[
            {
                "start_date": date(2026, 12, 12),
                "end_date": date(2026, 12, 16),
                "capacity": 5,
                "available_seats": 5,
                "price": "700000.00",
            },
        ],
    )
    _add_tour(
        engine,
        title="Hidden coastal holiday",
        slug="hidden-coastal-holiday",
        destination="Coast",
        duration_days=5,
        description="A beach escape",
        status="draft",
        departures=[
            {
                "start_date": date(2026, 12, 12),
                "end_date": date(2026, 12, 16),
                "capacity": 5,
                "available_seats": 5,
                "price": "700000.00",
            },
        ],
    )
    _add_tour(
        engine,
        title="Cancelled coastal holiday",
        slug="cancelled-coastal-holiday",
        destination="Coast",
        duration_days=5,
        description="A beach escape",
        departures=[
            {
                "start_date": date(2026, 12, 12),
                "end_date": date(2026, 12, 16),
                "capacity": 5,
                "available_seats": 5,
                "price": "700000.00",
                "status": "cancelled",
            },
        ],
    )

    response = client.get(
        "/api/v1/tours",
        params={
            "keyword": "beach",
            "destination": "Coast",
            "min_price": "600000",
            "max_price": "750000",
            "departure_from": "2026-12-01",
            "departure_to": "2026-12-31",
            "min_duration": 5,
            "max_duration": 5,
            "traveler_count": 5,
            "available_only": "true",
            "currency": "VND",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["items"][0]["slug"] == "coastal-holiday"
    assert body["items"][0]["starting_prices"] == [
        {"currency": "VND", "amount": "700000.00"}
    ]
    assert body["items"][0]["next_departure"]["start_date"] == "2026-12-12"


def test_public_search_sorts_by_currency_price_and_paginates(catalog_context) -> None:
    client, engine, _ = catalog_context
    _add_tour(
        engine,
        title="Beach tour A",
        slug="beach-tour-a",
        destination="Coast",
        duration_days=3,
        description="A sunny trip",
        departures=[
            {
                "start_date": date(2026, 7, 1),
                "end_date": date(2026, 7, 3),
                "capacity": 5,
                "available_seats": 5,
                "price": "200.00",
            },
        ],
    )
    _add_tour(
        engine,
        title="Beach tour B",
        slug="beach-tour-b",
        destination="Coast",
        duration_days=3,
        description="A sunny trip",
        departures=[
            {
                "start_date": date(2026, 8, 1),
                "end_date": date(2026, 8, 3),
                "capacity": 5,
                "available_seats": 5,
                "price": "100.00",
            },
        ],
    )

    first_page = client.get(
        "/api/v1/tours",
        params={
            "keyword": "beach",
            "currency": "VND",
            "sort": "price_asc",
            "size": 1,
        },
    )
    second_page = client.get(
        "/api/v1/tours",
        params={
            "keyword": "beach",
            "currency": "VND",
            "sort": "price_asc",
            "size": 1,
            "page": 2,
        },
    )

    assert first_page.status_code == second_page.status_code == 200
    assert first_page.json()["items"][0]["slug"] == "beach-tour-b"
    assert first_page.json()["total"] == 2
    assert first_page.json()["pages"] == 2
    assert second_page.json()["items"][0]["slug"] == "beach-tour-a"

    earliest = client.get(
        "/api/v1/tours",
        params={"keyword": "beach", "sort": "earliest_departure"},
    )
    assert earliest.status_code == 200
    assert earliest.json()["items"][0]["slug"] == "beach-tour-a"


def test_unfiltered_search_keeps_starting_prices_separate_by_currency(
    catalog_context,
) -> None:
    client, engine, published_id = catalog_context
    with Session(engine) as session:
        session.add(
            TourDeparture(
                tour_id=published_id,
                start_date=date(2026, 11, 1),
                end_date=date(2026, 11, 3),
                capacity=10,
                available_seats=10,
                price=Decimal("100.00"),
                currency="USD",
                status="open",
            )
        )
        session.commit()

    response = client.get("/api/v1/tours")

    assert response.status_code == 200
    body = response.json()
    assert body["currencies"] == ["USD", "VND"]
    assert body["items"][0]["starting_prices"] == [
        {"currency": "USD", "amount": "100.00"},
        {"currency": "VND", "amount": "3500000.00"},
    ]

@pytest.mark.parametrize(
    "params",
    [
        {"min_price": "10"},
        {"currency": "ZZZ"},
        {"currency": "VND", "min_price": "20", "max_price": "10"},
        {"departure_from": "2026-12-01", "departure_to": "2026-01-01"},
        {"min_duration": "5", "max_duration": "2"},
        {"sort": "price_asc"},
        {"traveler_count": "0"},
        {"size": "101"},
    ],
)
def test_public_search_rejects_invalid_query_parameters(
    catalog_context,
    params: dict[str, str],
) -> None:
    client, _, _ = catalog_context

    response = client.get("/api/v1/tours", params=params)

    assert response.status_code == 422


def test_search_expires_relevant_holds_without_releasing_active_holds(
    catalog_context,
) -> None:
    client, engine, _ = catalog_context
    expired_tour_id = _add_tour(
        engine,
        title="Expired hold tour",
        slug="expired-hold-tour",
        destination="Coast",
        duration_days=2,
        departures=[
            {
                "start_date": date(2026, 9, 1),
                "end_date": date(2026, 9, 2),
                "capacity": 2,
                "available_seats": 0,
                "price": "100.00",
            },
        ],
    )
    active_tour_id = _add_tour(
        engine,
        title="Active hold tour",
        slug="active-hold-tour",
        destination="Coast",
        duration_days=2,
        departures=[
            {
                "start_date": date(2026, 10, 1),
                "end_date": date(2026, 10, 2),
                "capacity": 2,
                "available_seats": 0,
                "price": "100.00",
            },
        ],
    )
    current_time = datetime.now(timezone.utc)
    with Session(engine) as session:
        expired_departure = session.query(TourDeparture).filter_by(
            tour_id=expired_tour_id
        ).one()
        active_departure = session.query(TourDeparture).filter_by(
            tour_id=active_tour_id
        ).one()
        session.add_all(
            [
                Booking(
                    reference="EXPIRED-HOLD",
                    departure_id=expired_departure.id,
                    contact_name="Guest",
                    contact_email="guest@example.test",
                    contact_phone="123",
                    passenger_count=2,
                    status="pending",
                    expires_at=current_time - timedelta(minutes=1),
                    total_amount=Decimal("200.00"),
                    currency="VND",
                ),
                Booking(
                    reference="ACTIVE-HOLD",
                    departure_id=active_departure.id,
                    contact_name="Guest",
                    contact_email="guest@example.test",
                    contact_phone="123",
                    passenger_count=2,
                    status="pending",
                    expires_at=current_time + timedelta(minutes=30),
                    total_amount=Decimal("200.00"),
                    currency="VND",
                ),
            ]
        )
        session.commit()

    response = client.get(
        "/api/v1/tours",
        params={"available_only": "true", "traveler_count": 2},
    )

    assert response.status_code == 200
    results = response.json()["items"]
    results_by_slug = {item["slug"]: item for item in results}
    assert "expired-hold-tour" in results_by_slug
    assert "active-hold-tour" not in results_by_slug
    assert results_by_slug["expired-hold-tour"]["next_departure"][
        "available_seats"
    ] == 2
    with Session(engine) as session:
        expired = session.query(Booking).filter_by(reference="EXPIRED-HOLD").one()
        active = session.query(Booking).filter_by(reference="ACTIVE-HOLD").one()
        assert expired.status == "expired"
        assert active.status == "pending"
