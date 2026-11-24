from datetime import date, timedelta
from decimal import Decimal
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.core.security import create_access_token, hash_password
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models.booking import Booking
from app.models.customer import Customer
from app.models.identity import Role, User
from app.models.tour import Tour, TourDeparture


@pytest.fixture
def booking_api_context():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        customer_role = Role(code="CUSTOMER", description="Customer")
        admin_role = Role(code="ADMIN", description="Administrator")
        customer_user = User(
            email="customer@example.com",
            password_hash="unused",
            is_active=True,
        )
        customer_user.roles.append(customer_role)
        other_user = User(
            email="other@example.com",
            password_hash="unused",
            is_active=True,
        )
        other_user.roles.append(customer_role)
        admin_user = User(
            email="admin@example.com",
            password_hash=hash_password("secure-password"),
            is_active=True,
        )
        admin_user.roles.append(admin_role)
        session.add_all([customer_user, other_user, admin_user])
        session.flush()

        customer = Customer(
            user_id=customer_user.id,
            full_name="Customer One",
            email="customer@example.com",
        )
        other_customer = Customer(
            user_id=other_user.id,
            full_name="Customer Two",
            email="other@example.com",
        )
        tour = Tour(
            title="Authorization Tour",
            slug="authorization-tour",
            duration_days=1,
            destination="Can Tho",
            status="published",
        )
        session.add_all([customer, other_customer, tour])
        session.flush()
        departure = TourDeparture(
            tour_id=tour.id,
            start_date=date.today() + timedelta(days=10),
            end_date=date.today() + timedelta(days=11),
            capacity=5,
            available_seats=5,
            price=Decimal("1000000.00"),
            currency="VND",
            status="open",
        )
        session.add(departure)
        session.commit()

        user_ids = {
            "customer": customer_user.id,
            "other": other_user.id,
            "admin": admin_user.id,
        }
        customer_ids = {
            "customer": customer.id,
            "other": other_customer.id,
        }
        departure_id = departure.id

    def override_db():
        with Session(engine) as session:
            yield session

    app.dependency_overrides[get_db] = override_db
    with TestClient(app) as client:
        yield client, user_ids, customer_ids, departure_id, engine

    app.dependency_overrides.clear()
    engine.dispose()


def booking_payload(
    departure_id: UUID,
    customer_id: UUID | None = None,
) -> dict[str, object]:
    payload: dict[str, object] = {
        "departure_id": str(departure_id),
        "contact_name": "Guest",
        "contact_email": "guest@example.com",
        "contact_phone": "0900000000",
        "travelers": [{"full_name": "Guest One", "traveler_type": "adult"}],
    }
    if customer_id is not None:
        payload["customer_id"] = str(customer_id)
    return payload


def auth_headers(user_id: UUID) -> dict[str, str]:
    return {"Authorization": f"Bearer {create_access_token(str(user_id))}"}


def test_guest_can_create_unlinked_booking(booking_api_context) -> None:
    client, _, _, departure_id, _ = booking_api_context
    payload = booking_payload(departure_id)
    payload["contact_email"] = "customer@example.com"

    response = client.post(
        "/api/v1/bookings",
        json=payload,
    )

    assert response.status_code == 201
    assert response.json()["customer_id"] is None


def test_guest_cannot_link_booking_to_customer(booking_api_context) -> None:
    client, _, customer_ids, departure_id, _ = booking_api_context

    response = client.post(
        "/api/v1/bookings",
        json=booking_payload(departure_id, customer_ids["customer"]),
    )

    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "CUSTOMER_NOT_FOUND"


def test_customer_can_link_own_booking(booking_api_context) -> None:
    client, user_ids, customer_ids, departure_id, _ = booking_api_context

    response = client.post(
        "/api/v1/bookings",
        json=booking_payload(departure_id, customer_ids["customer"]),
        headers=auth_headers(user_ids["customer"]),
    )

    assert response.status_code == 201
    assert response.json()["customer_id"] == str(customer_ids["customer"])


def test_customer_booking_uses_backend_linked_profile_without_customer_id(
    booking_api_context,
) -> None:
    client, user_ids, customer_ids, departure_id, _ = booking_api_context

    response = client.post(
        "/api/v1/bookings",
        json=booking_payload(departure_id),
        headers=auth_headers(user_ids["customer"]),
    )

    assert response.status_code == 201
    assert response.json()["customer_id"] == str(customer_ids["customer"])


def test_customer_cannot_link_another_customers_booking(
    booking_api_context,
) -> None:
    client, user_ids, customer_ids, departure_id, _ = booking_api_context

    response = client.post(
        "/api/v1/bookings",
        json=booking_payload(departure_id, customer_ids["other"]),
        headers=auth_headers(user_ids["customer"]),
    )

    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "CUSTOMER_NOT_FOUND"


def test_staff_can_link_booking_to_customer(booking_api_context) -> None:
    client, user_ids, customer_ids, departure_id, _ = booking_api_context

    response = client.post(
        "/api/v1/bookings",
        json=booking_payload(departure_id, customer_ids["customer"]),
        headers=auth_headers(user_ids["admin"]),
    )

    assert response.status_code == 201
    assert response.json()["customer_id"] == str(customer_ids["customer"])
    with Session(booking_api_context[4]) as session:
        booking = session.get(Booking, UUID(response.json()["id"]))
        assert booking is not None
        assert booking.created_by_user_id == user_ids["admin"]


def test_guest_booking_staff_confirmation_and_payment_workflow(
    booking_api_context,
) -> None:
    client, _, _, departure_id, _ = booking_api_context

    login = client.post(
        "/api/v1/auth/login",
        json={
            "email": "admin@example.com",
            "password": "secure-password",
        },
    )
    assert login.status_code == 200
    headers = {
        "Authorization": f"Bearer {login.json()['access_token']}",
    }

    created = client.post(
        "/api/v1/bookings",
        json=booking_payload(departure_id),
    )
    assert created.status_code == 201
    booking = created.json()
    assert booking["status"] == "pending"
    assert [item["new_status"] for item in booking["status_history"]] == ["pending"]

    departure = client.get(f"/api/v1/departures/{departure_id}")
    assert departure.status_code == 200
    assert departure.json()["available_seats"] == 4

    confirmed = client.post(
        f"/api/v1/bookings/{booking['id']}/confirm",
        json={"reason": "Payment verified by staff"},
        headers=headers,
    )
    assert confirmed.status_code == 200
    assert confirmed.json()["status"] == "confirmed"
    assert [
        item["new_status"] for item in confirmed.json()["status_history"]
    ] == ["pending", "confirmed"]

    payment = client.post(
        "/api/v1/payments",
        json={
            "booking_id": booking["id"],
            "amount": "250000.00",
            "currency": "VND",
            "method": "bank_transfer",
            "status": "paid",
            "transaction_reference": "INTEGRATION-TX-001",
        },
        headers={
            **headers,
            "Idempotency-Key": "api-payment-workflow-001",
        },
    )
    assert payment.status_code == 201
    assert payment.json()["booking_id"] == booking["id"]
    assert payment.json()["amount"] == "250000.00"

    dashboard = client.get("/api/v1/dashboard/summary", headers=headers)
    assert dashboard.status_code == 200
    summary = dashboard.json()
    assert summary["booking_count"] == 1
    assert summary["pending_booking_count"] == 0
    assert summary["payments_by_currency"] == [
        {
            "currency": "VND",
            "paid_amount": "250000.00",
            "pending_amount": "0.00",
        }
    ]
