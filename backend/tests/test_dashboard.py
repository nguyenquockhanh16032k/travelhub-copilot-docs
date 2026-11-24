from datetime import date, datetime, timedelta, timezone
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
from app.models.booking import Booking, Payment
from app.models.identity import Role
from app.models.tour import Tour, TourDeparture


@pytest.fixture
def dashboard_context():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        published_tour = Tour(
            title="Published tour",
            slug="published-tour",
            duration_days=2,
            destination="Da Lat",
            status="published",
        )
        draft_tour = Tour(
            title="Draft tour",
            slug="draft-tour",
            duration_days=2,
            destination="Hue",
            status="draft",
        )
        session.add_all([published_tour, draft_tour])
        session.flush()

        upcoming = TourDeparture(
            tour_id=published_tour.id,
            start_date=date.today() + timedelta(days=10),
            end_date=date.today() + timedelta(days=12),
            capacity=12,
            available_seats=10,
            price=Decimal("2500000.00"),
            currency="VND",
            status="open",
        )
        hidden_draft_departure = TourDeparture(
            tour_id=draft_tour.id,
            start_date=date.today() + timedelta(days=5),
            end_date=date.today() + timedelta(days=7),
            capacity=10,
            available_seats=10,
            price=Decimal("1000.00"),
            currency="VND",
            status="open",
        )
        past_departure = TourDeparture(
            tour_id=published_tour.id,
            start_date=date.today() - timedelta(days=5),
            end_date=date.today() - timedelta(days=3),
            capacity=10,
            available_seats=10,
            price=Decimal("1000.00"),
            currency="VND",
            status="open",
        )
        session.add_all([upcoming, hidden_draft_departure, past_departure])
        session.flush()

        pending_booking = Booking(
            reference="TH-PENDING",
            departure_id=upcoming.id,
            contact_name="Pending Guest",
            contact_email="pending@example.com",
            contact_phone="0900000001",
            passenger_count=1,
            status="pending",
            total_amount=Decimal("2500000.00"),
            currency="VND",
        )
        cancelled_booking = Booking(
            reference="TH-CANCELLED",
            departure_id=upcoming.id,
            contact_name="Cancelled Guest",
            contact_email="cancelled@example.com",
            contact_phone="0900000002",
            passenger_count=1,
            status="cancelled",
            total_amount=Decimal("2500000.00"),
            currency="VND",
        )
        session.add_all([pending_booking, cancelled_booking])
        session.flush()
        session.add_all(
            [
                Payment(
                    booking_id=pending_booking.id,
                    amount=Decimal("500000.00"),
                    currency="VND",
                    method="cash",
                    status="paid",
                    recorded_at=datetime.now(timezone.utc),
                ),
                Payment(
                    booking_id=pending_booking.id,
                    amount=Decimal("200000.00"),
                    currency="VND",
                    method="bank_transfer",
                    status="pending",
                    recorded_at=datetime.now(timezone.utc),
                ),
                Payment(
                    booking_id=cancelled_booking.id,
                    amount=Decimal("300000.00"),
                    currency="VND",
                    method="cash",
                    status="refunded",
                    recorded_at=datetime.now(timezone.utc),
                ),
            ]
        )
        session.commit()

    def override_db():
        with Session(engine) as session:
            yield session

    admin = SimpleNamespace(
        roles=[Role(code="ADMIN", description="Administrator")]
    )
    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_current_user] = lambda: admin

    with TestClient(app) as client:
        yield client

    app.dependency_overrides.clear()
    engine.dispose()


def test_dashboard_summary_reports_bookings_departures_and_payment_statuses(
    dashboard_context,
) -> None:
    response = dashboard_context.get("/api/v1/dashboard/summary")

    assert response.status_code == 200
    body = response.json()
    assert body["booking_count"] == 2
    assert body["pending_booking_count"] == 1
    assert len(body["upcoming_departures"]) == 1
    assert body["upcoming_departures"][0]["tour_title"] == "Published tour"
    assert body["payments_by_currency"] == [
        {
            "currency": "VND",
            "paid_amount": "500000.00",
            "pending_amount": "200000.00",
        }
    ]


def test_dashboard_summary_requires_staff_role(dashboard_context) -> None:
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(
        roles=[Role(code="CUSTOMER", description="Customer")]
    )

    response = dashboard_context.get("/api/v1/dashboard/summary")

    assert response.status_code == 403
