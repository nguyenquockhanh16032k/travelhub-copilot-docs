from datetime import date, timedelta
from decimal import Decimal
from types import SimpleNamespace
import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.api.dependencies import get_current_user, get_optional_current_user
from app.core.permissions import Permission, ROLE_PERMISSIONS
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models.audit import AuditLog
from app.models.customer import Customer
from app.models.identity import Role, User
from app.models.tour import Tour, TourDeparture


@pytest.fixture
def staff_context():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        tour = Tour(
            title="Staff tour",
            slug="staff-tour",
            duration_days=2,
            destination="Da Lat",
            status="published",
        )
        session.add(tour)
        session.flush()
        departure = TourDeparture(
            tour_id=tour.id,
            start_date=date.today() + timedelta(days=10),
            end_date=date.today() + timedelta(days=12),
            capacity=10,
            available_seats=10,
            price=Decimal("1000.00"),
            currency="VND",
            status="open",
        )
        session.add(departure)
        customer = Customer(
            full_name="Staff Customer",
            email="staff-customer@example.com",
            phone="0900000000",
        )
        session.add(customer)
        session.commit()
        departure_id = departure.id
        customer_id = customer.id

    def override_db():
        with Session(engine) as session:
            yield session

    staff = SimpleNamespace(
        id=uuid.uuid4(),
        roles=[Role(code="STAFF", description="Staff")],
    )
    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_current_user] = lambda: staff
    app.dependency_overrides[get_optional_current_user] = lambda: staff
    with TestClient(app) as client:
        yield client, departure_id, customer_id, engine
    app.dependency_overrides.clear()
    engine.dispose()


def test_staff_permission_set_matches_the_approved_policy() -> None:
    assert ROLE_PERMISSIONS["STAFF"] == frozenset(
        {
            Permission.DASHBOARD_READ,
            Permission.TOURS_READ,
            Permission.DEPARTURES_READ,
            Permission.BOOKINGS_READ,
            Permission.BOOKINGS_CREATE,
            Permission.BOOKINGS_CREATE_FOR_CUSTOMERS,
            Permission.BOOKINGS_WRITE,
            Permission.BOOKINGS_STATUS,
            Permission.CUSTOMERS_READ,
            Permission.CUSTOMERS_WRITE,
            Permission.ITINERARIES_READ,
            Permission.GUIDES_READ,
            Permission.ASSIGNMENTS_READ,
        }
    )


def test_staff_can_read_operations_but_cannot_change_tours_or_departures(
    staff_context,
) -> None:
    client, departure_id, _, _ = staff_context
    tour_list = client.get("/api/v1/admin/tours")
    departure_list = client.get("/api/v1/admin/departures")
    guides = client.get("/api/v1/guides")
    assignments = client.get(
        f"/api/v1/departures/{departure_id}/assignments"
    )
    tour_create = client.post(
        "/api/v1/tours",
        json={
            "title": "Forbidden",
            "slug": "forbidden",
            "duration_days": 1,
            "destination": "Hue",
        },
    )
    departure_update = client.patch(
        f"/api/v1/departures/{departure_id}",
        json={"capacity": 11},
    )

    assert tour_list.status_code == 200
    assert departure_list.status_code == 200
    assert guides.status_code == 200
    assert assignments.status_code == 200
    assert tour_create.status_code == 403
    assert departure_update.status_code == 403


def test_staff_cannot_manage_guides_or_assignments(staff_context) -> None:
    client, departure_id, _, _ = staff_context
    guide = client.post(
        "/api/v1/guides",
        json={"full_name": "Forbidden Guide"},
    )
    assignment = client.post(
        f"/api/v1/departures/{departure_id}/assignments",
        json={
            "guide_id": str(uuid.uuid4()),
            "role": "Guide",
            "status": "assigned",
        },
    )

    assert guide.status_code == 403
    assert assignment.status_code == 403


def test_staff_dashboard_omits_financial_values(staff_context) -> None:
    client, _, _, _ = staff_context

    response = client.get("/api/v1/dashboard/summary")

    assert response.status_code == 200
    body = response.json()
    assert "payments_by_currency" not in body
    assert "price" not in body["upcoming_departures"][0]
    assert body["upcoming_departures"][0]["available_seats"] == 10


@pytest.mark.parametrize(
    "path",
    [
        "/api/v1/admin/articles",
        "/api/v1/suppliers",
        "/api/v1/reports/expenses",
        "/api/v1/users",
    ],
)
def test_staff_is_denied_finance_content_and_user_management(
    staff_context,
    path: str,
) -> None:
    client, _, _, _ = staff_context

    response = client.get(path)

    assert response.status_code == 403


def test_staff_cannot_create_payments_or_manage_itineraries(staff_context) -> None:
    client, _, _, _ = staff_context
    payment = client.post(
        "/api/v1/payments",
        json={
            "booking_id": str(uuid.uuid4()),
            "amount": "1.00",
            "currency": "VND",
            "method": "cash",
            "status": "paid",
        },
    )
    itinerary = client.post(
        f"/api/v1/tours/{uuid.uuid4()}/itineraries",
        json={"day_number": 1, "sequence": 1, "activity": "Forbidden"},
    )

    assert payment.status_code == 403
    assert itinerary.status_code == 403


def test_staff_can_create_and_update_customer_bookings_without_financial_fields(
    staff_context,
) -> None:
    client, departure_id, customer_id, engine = staff_context
    created = client.post(
        "/api/v1/bookings",
        json={
            "departure_id": str(departure_id),
            "customer_id": str(customer_id),
            "contact_name": "Staff Customer",
            "contact_email": "staff-customer@example.com",
            "contact_phone": "0900000000",
            "travelers": [
                {"full_name": "Traveler One", "traveler_type": "adult"}
            ],
        },
    )
    assert created.status_code == 201
    booking_id = created.json()["id"]
    assert "total_amount" not in created.json()
    assert "currency" not in created.json()

    updated = client.patch(
        f"/api/v1/bookings/{booking_id}",
        json={
            "contact_phone": "0900000001",
            "travelers": [
                {"full_name": "Updated Traveler", "traveler_type": "adult"}
            ],
        },
    )
    listed = client.get("/api/v1/bookings")
    details = client.get(f"/api/v1/bookings/{booking_id}")

    assert updated.status_code == 200
    assert updated.json()["contact_phone"] == "0900000001"
    assert updated.json()["travelers"][0]["full_name"] == "Updated Traveler"
    assert "total_amount" not in listed.json()["items"][0]
    assert "total_amount" not in details.json()
    with Session(engine) as session:
        events = session.scalars(
            select(AuditLog)
            .where(AuditLog.resource_id == uuid.UUID(booking_id))
            .order_by(AuditLog.action)
        ).all()
    assert {event.action for event in events} == {
        "booking.created",
        "booking.details_updated",
    }


def test_staff_can_link_existing_customer_account(staff_context) -> None:
    client, _, _, engine = staff_context
    with Session(engine) as session:
        customer_role = Role(code="CUSTOMER", description="Customer")
        customer_user = User(
            email="linked-customer@example.com",
            password_hash="unused",
            is_active=True,
            roles=[customer_role],
        )
        session.add(customer_user)
        session.commit()
        customer_user_id = customer_user.id

    linked = client.post(
        "/api/v1/customers",
        json={
            "full_name": "Staff Linked Customer",
            "user_id": str(customer_user_id),
        },
    )

    assert linked.status_code == 201
    assert linked.json()["user_id"] == str(customer_user_id)
