from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.core.security import create_access_token
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models.booking import (
    Booking,
    BookingCustomer,
    BookingStatusHistory,
    Payment,
)
from app.models.customer import Customer
from app.models.identity import Role, User
from app.models.tour import Tour, TourDeparture


@pytest.fixture
def customer_history_context():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        customer_role = Role(code="CUSTOMER", description="Customer")
        admin_role = Role(code="ADMIN", description="Administrator")
        staff_role = Role(code="STAFF", description="Staff")
        owner = User(
            email="owner@example.com",
            password_hash="unused",
            is_active=True,
            roles=[customer_role],
        )
        other = User(
            email="other@example.com",
            password_hash="unused",
            is_active=True,
            roles=[customer_role],
        )
        admin = User(
            email="admin@example.com",
            password_hash="unused",
            is_active=True,
            roles=[admin_role],
        )
        staff = User(
            email="staff@example.com",
            password_hash="unused",
            is_active=True,
            roles=[staff_role],
        )
        session.add_all([owner, other, admin, staff])
        session.flush()

        owner_customer = Customer(
            user_id=owner.id,
            full_name="Owner Customer",
            email="owner@example.com",
        )
        other_customer = Customer(
            user_id=other.id,
            full_name="Other Customer",
            email="other@example.com",
        )
        tour = Tour(
            title="Customer History Tour",
            slug=f"customer-history-{uuid4().hex}",
            duration_days=3,
            destination="Da Lat",
            status="published",
        )
        session.add_all([owner_customer, other_customer, tour])
        session.flush()
        departure = TourDeparture(
            tour_id=tour.id,
            start_date=date.today() + timedelta(days=10),
            end_date=date.today() + timedelta(days=12),
            capacity=10,
            available_seats=7,
            price=Decimal("1250000.00"),
            currency="VND",
            status="open",
        )
        session.add(departure)
        session.flush()

        owner_booking = Booking(
            reference="TH-OWNER-001",
            departure_id=departure.id,
            customer_id=owner_customer.id,
            contact_name="Owner Customer",
            contact_email="owner@example.com",
            contact_phone="0900000000",
            passenger_count=2,
            status="confirmed",
            expires_at=None,
            total_amount=Decimal("2500000.00"),
            currency="VND",
            notes="Private internal note",
        )
        other_booking = Booking(
            reference="TH-OTHER-001",
            departure_id=departure.id,
            customer_id=other_customer.id,
            contact_name="Other Customer",
            contact_email="other@example.com",
            contact_phone="0900000001",
            passenger_count=1,
            status="confirmed",
            total_amount=Decimal("1250000.00"),
            currency="VND",
        )
        guest_booking = Booking(
            reference="TH-GUEST-001",
            departure_id=departure.id,
            customer_id=None,
            contact_name="Guest",
            contact_email="guest@example.com",
            contact_phone="0900000002",
            passenger_count=1,
            status="pending",
            total_amount=Decimal("1250000.00"),
            currency="VND",
        )
        session.add_all([owner_booking, other_booking, guest_booking])
        session.flush()
        session.add_all(
            [
                BookingCustomer(
                    booking_id=owner_booking.id,
                    full_name="Passenger One",
                    traveler_type="adult",
                ),
                BookingCustomer(
                    booking_id=owner_booking.id,
                    full_name="Passenger Two",
                    traveler_type="child",
                ),
                BookingStatusHistory(
                    booking_id=owner_booking.id,
                    old_status=None,
                    new_status="pending",
                    changed_at=datetime.now(timezone.utc) - timedelta(minutes=5),
                    reason="Booking created",
                ),
                BookingStatusHistory(
                    booking_id=owner_booking.id,
                    old_status="pending",
                    new_status="confirmed",
                    changed_at=datetime.now(timezone.utc),
                    reason="Staff-only note",
                ),
                Payment(
                    booking_id=owner_booking.id,
                    amount=Decimal("500000.00"),
                    currency="VND",
                    method="bank_transfer",
                    status="paid",
                    transaction_reference="TX-OWNER-001",
                    recorded_at=datetime.now(timezone.utc),
                ),
            ]
        )
        session.commit()
        ids = {
            "owner": owner.id,
            "other": other.id,
            "admin": admin.id,
            "staff": staff.id,
            "owner_booking": owner_booking.id,
            "other_booking": other_booking.id,
            "guest_booking": guest_booking.id,
            "departure": departure.id,
            "owner_customer": owner_customer.id,
        }

    def override_db():
        with Session(engine) as session:
            yield session

    app.dependency_overrides[get_db] = override_db
    with TestClient(app) as client:
        yield client, engine, ids
    app.dependency_overrides.clear()
    engine.dispose()


def headers(user_id: UUID) -> dict[str, str]:
    return {"Authorization": f"Bearer {create_access_token(str(user_id))}"}


def test_customer_history_includes_only_own_booking_and_customer_details(
    customer_history_context,
) -> None:
    client, _, ids = customer_history_context

    response = client.get(
        "/api/v1/customers/me/bookings",
        headers=headers(ids["owner"]),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    booking = body["items"][0]
    assert booking["id"] == str(ids["owner_booking"])
    assert booking["tour_title"] == "Customer History Tour"
    assert booking["departure_start_date"] == (
        date.today() + timedelta(days=10)
    ).isoformat()
    assert [item["full_name"] for item in booking["travelers"]] == [
        "Passenger One",
        "Passenger Two",
    ]
    assert [item["new_status"] for item in booking["status_history"]] == [
        "pending",
        "confirmed",
    ]
    assert booking["payments"][0]["transaction_reference"] == "TX-OWNER-001"
    assert booking["payments"][0]["status"] == "paid"
    assert "notes" not in booking
    assert "contact_email" not in booking


def test_customer_cannot_read_another_customers_or_guest_booking(
    customer_history_context,
) -> None:
    client, _, ids = customer_history_context
    auth = headers(ids["owner"])

    other = client.get(
        f"/api/v1/customers/me/bookings/{ids['other_booking']}",
        headers=auth,
    )
    guest = client.get(
        f"/api/v1/customers/me/bookings/{ids['guest_booking']}",
        headers=auth,
    )

    assert other.status_code == 404
    assert guest.status_code == 404
    assert other.json()["detail"]["code"] == "BOOKING_NOT_FOUND"
    assert guest.json()["detail"]["code"] == "BOOKING_NOT_FOUND"


def test_customer_history_requires_authentication_and_customer_role(
    customer_history_context,
) -> None:
    client, _, ids = customer_history_context

    anonymous = client.get("/api/v1/customers/me/bookings")
    admin = client.get(
        "/api/v1/customers/me/bookings",
        headers=headers(ids["admin"]),
    )
    staff = client.get(
        "/api/v1/customers/me/bookings",
        headers=headers(ids["staff"]),
    )

    assert anonymous.status_code == 401
    assert admin.status_code == 403
    assert staff.status_code == 403


def test_admin_and_staff_keep_existing_access_to_guest_booking_records(
    customer_history_context,
) -> None:
    client, _, ids = customer_history_context

    admin_response = client.get(
        "/api/v1/bookings",
        headers=headers(ids["admin"]),
    )
    staff_response = client.get(
        "/api/v1/bookings",
        headers=headers(ids["staff"]),
    )

    assert admin_response.status_code == 200
    assert staff_response.status_code == 200
    for response in (admin_response, staff_response):
        guest = next(
            booking
            for booking in response.json()["items"]
            if booking["id"] == str(ids["guest_booking"])
        )
        assert guest["customer_id"] is None
