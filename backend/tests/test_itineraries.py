from datetime import date, timedelta
from decimal import Decimal
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.api.dependencies import get_current_user
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models.identity import Role
from app.models.itinerary import TourItinerary
from app.models.tour import Tour, TourDeparture


@pytest.fixture
def itinerary_context():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        tour = Tour(
            title="Itinerary Tour",
            slug="itinerary-tour",
            duration_days=2,
            destination="Da Lat",
            status="published",
        )
        session.add(tour)
        session.flush()
        departure = TourDeparture(
            tour_id=tour.id,
            start_date=date.today() + timedelta(days=10),
            end_date=date.today() + timedelta(days=11),
            capacity=10,
            available_seats=10,
            price=Decimal("1000000.00"),
            currency="VND",
            status="open",
        )
        session.add_all(
            [
                departure,
                TourItinerary(
                    tour_id=tour.id,
                    day_number=1,
                    sequence=2,
                    activity="Afternoon visit",
                ),
                TourItinerary(
                    tour_id=tour.id,
                    day_number=1,
                    sequence=1,
                    activity="Morning arrival",
                ),
            ]
        )
        session.commit()
        tour_id = tour.id

    def override_db():
        with Session(engine) as session:
            yield session

    admin = SimpleNamespace(
        roles=[Role(code="ADMIN", description="Administrator")]
    )
    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_current_user] = lambda: admin

    with TestClient(app) as client:
        yield client, engine, tour_id

    app.dependency_overrides.clear()
    engine.dispose()


def test_public_tour_detail_includes_itinerary_in_day_order(itinerary_context) -> None:
    client, _, tour_id = itinerary_context

    response = client.get(f"/api/v1/tours/{tour_id}")

    assert response.status_code == 200
    assert [item["activity"] for item in response.json()["itinerary"]] == [
        "Morning arrival",
        "Afternoon visit",
    ]


def test_staff_can_manage_ordered_itinerary_items(itinerary_context) -> None:
    client, _, tour_id = itinerary_context
    base_url = f"/api/v1/tours/{tour_id}/itineraries"

    listed = client.get(base_url)
    assert listed.status_code == 200
    assert [item["sequence"] for item in listed.json()] == [1, 2]

    created = client.post(
        base_url,
        json={
            "day_number": 1,
            "sequence": 3,
            "activity": "Evening meal",
            "time": "18:00",
            "location": "Da Lat",
            "description": None,
        },
    )
    assert created.status_code == 201
    itinerary_id = created.json()["id"]

    duplicate = client.post(
        base_url,
        json={
            "day_number": 1,
            "sequence": 2,
            "activity": "Duplicate position",
        },
    )
    assert duplicate.status_code == 409

    conflicting_update = client.patch(
        f"{base_url}/{itinerary_id}",
        json={"sequence": 2},
    )
    assert conflicting_update.status_code == 409

    updated = client.patch(
        f"{base_url}/{itinerary_id}",
        json={"sequence": 4},
    )
    assert updated.status_code == 200
    assert updated.json()["sequence"] == 4

    deleted = client.delete(f"{base_url}/{itinerary_id}")
    assert deleted.status_code == 204


def test_itinerary_management_requires_staff_role(itinerary_context) -> None:
    client, _, tour_id = itinerary_context
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(
        roles=[Role(code="CUSTOMER", description="Customer")]
    )

    response = client.get(f"/api/v1/tours/{tour_id}/itineraries")

    assert response.status_code == 403
