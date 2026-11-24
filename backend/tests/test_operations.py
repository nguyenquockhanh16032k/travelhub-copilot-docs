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
from app.models.tour import Tour, TourDeparture


@pytest.fixture
def operations_context():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        tour = Tour(
            title="Operations Tour",
            slug="operations-tour",
            duration_days=3,
            destination="Da Lat",
            status="draft",
        )
        session.add(tour)
        session.flush()
        departure = TourDeparture(
            tour_id=tour.id,
            start_date=date.today() + timedelta(days=10),
            end_date=date.today() + timedelta(days=12),
            capacity=10,
            available_seats=10,
            price=Decimal("1000000.00"),
            currency="VND",
            status="draft",
        )
        session.add(departure)
        session.commit()
        departure_id = departure.id

    def override_db():
        with Session(engine) as session:
            yield session

    admin = SimpleNamespace(roles=[Role(code="ADMIN", description="Administrator")])
    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_current_user] = lambda: admin

    with TestClient(app) as client:
        yield client, engine, departure_id

    app.dependency_overrides.clear()
    engine.dispose()


def test_staff_can_manage_guides(operations_context) -> None:
    client, _, _ = operations_context

    created = client.post(
        "/api/v1/guides",
        json={
            "full_name": "  Alex Nguyen  ",
            "email": "alex@example.com",
            "phone": "+84123456789",
        },
    )
    assert created.status_code == 201
    guide_id = created.json()["id"]
    assert created.json()["full_name"] == "Alex Nguyen"

    listed = client.get("/api/v1/guides", params={"search": "alex"})
    assert listed.status_code == 200
    assert listed.json()["total"] == 1
    assert listed.json()["items"][0]["id"] == guide_id

    updated = client.patch(
        f"/api/v1/guides/{guide_id}",
        json={"full_name": "Alex N."},
    )
    assert updated.status_code == 200
    assert updated.json()["full_name"] == "Alex N."


def test_staff_can_manage_assignments_for_any_departure_status(
    operations_context,
) -> None:
    client, _, departure_id = operations_context
    guide_response = client.post(
        "/api/v1/guides",
        json={"full_name": "Jamie Tran"},
    )
    assert guide_response.status_code == 201
    guide_id = guide_response.json()["id"]
    base_url = f"/api/v1/departures/{departure_id}/assignments"

    created = client.post(
        base_url,
        json={"guide_id": guide_id, "role": "Lead guide", "status": "assigned"},
    )
    assert created.status_code == 201
    assignment_id = created.json()["id"]
    assert created.json()["guide"]["full_name"] == "Jamie Tran"

    listed = client.get(base_url)
    assert listed.status_code == 200
    assert listed.json()["items"][0]["id"] == assignment_id

    updated = client.patch(
        f"{base_url}/{assignment_id}",
        json={"status": "confirmed"},
    )
    assert updated.status_code == 200
    assert updated.json()["status"] == "confirmed"

    deleted = client.delete(f"{base_url}/{assignment_id}")
    assert deleted.status_code == 204
    assert client.get(base_url).json()["total"] == 0


def test_assignment_validates_references_and_non_empty_text(
    operations_context,
) -> None:
    client, _, departure_id = operations_context
    base_url = f"/api/v1/departures/{departure_id}/assignments"

    invalid = client.post(
        base_url,
        json={
            "guide_id": "00000000-0000-0000-0000-000000000001",
            "role": " ",
            "status": "assigned",
        },
    )
    assert invalid.status_code == 422

    missing_guide = client.post(
        base_url,
        json={
            "guide_id": "00000000-0000-0000-0000-000000000001",
            "role": "Guide",
            "status": "assigned",
        },
    )
    assert missing_guide.status_code == 404


def test_admin_departure_list_includes_non_public_departures(
    operations_context,
) -> None:
    client, _, _ = operations_context

    admin_list = client.get("/api/v1/admin/departures")
    public_list = client.get("/api/v1/departures")

    assert admin_list.status_code == 200
    assert admin_list.json()["total"] == 1
    assert admin_list.json()["items"][0]["tour_title"] == "Operations Tour"
    assert public_list.status_code == 200
    assert public_list.json()["total"] == 0


def test_operations_endpoints_require_staff_role(operations_context) -> None:
    client, _, departure_id = operations_context
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(
        roles=[Role(code="CUSTOMER", description="Customer")]
    )

    response = client.get(
        f"/api/v1/departures/{departure_id}/assignments",
    )

    assert response.status_code == 403


def test_staff_can_manage_suppliers_and_departure_expenses(
    operations_context,
) -> None:
    client, _, departure_id = operations_context

    supplier = client.post(
        "/api/v1/suppliers",
        json={"name": "  Alpine Transport ", "service_category": " Transport "},
    )
    assert supplier.status_code == 201
    supplier_id = supplier.json()["id"]
    assert supplier.json()["name"] == "Alpine Transport"
    assert supplier.json()["service_category"] == "Transport"

    supplier_list = client.get(
        "/api/v1/suppliers",
        params={"search": "transport"},
    )
    assert supplier_list.status_code == 200
    assert supplier_list.json()["total"] == 1

    supplier_update = client.patch(
        f"/api/v1/suppliers/{supplier_id}",
        json={"service_category": "Ground transport"},
    )
    assert supplier_update.status_code == 200
    assert supplier_update.json()["service_category"] == "Ground transport"

    base_url = f"/api/v1/departures/{departure_id}/expenses"
    expense = client.post(
        base_url,
        json={
            "supplier_id": supplier_id,
            "category": "Vehicle hire",
            "amount": "123.45",
            "currency": "usd",
            "status": "submitted",
            "note": "Airport transfer",
        },
    )
    assert expense.status_code == 201
    expense_id = expense.json()["id"]
    assert expense.json()["currency"] == "USD"
    assert expense.json()["supplier"]["id"] == supplier_id

    expense_list = client.get(base_url)
    assert expense_list.status_code == 200
    assert expense_list.json()["total"] == 1

    expense_update = client.patch(
        f"{base_url}/{expense_id}",
        json={"supplier_id": None, "status": "approved"},
    )
    assert expense_update.status_code == 200
    assert expense_update.json()["supplier_id"] is None
    assert expense_update.json()["status"] == "approved"


def test_expense_requires_positive_fixed_precision_amount(
    operations_context,
) -> None:
    client, _, departure_id = operations_context

    response = client.post(
        f"/api/v1/departures/{departure_id}/expenses",
        json={
            "category": "Transport",
            "amount": "0",
            "currency": "VND",
            "status": "submitted",
        },
    )

    assert response.status_code == 422


def test_expense_report_groups_without_combining_currency_or_status(
    operations_context,
) -> None:
    client, _, departure_id = operations_context
    expense_url = f"/api/v1/departures/{departure_id}/expenses"
    records = [
        ("12.35", "VND", "submitted"),
        ("7.65", "VND", "submitted"),
        ("10.00", "USD", "submitted"),
        ("5.00", "VND", "approved"),
    ]
    for amount, currency, status in records:
        response = client.post(
            expense_url,
            json={
                "category": "Transport",
                "amount": amount,
                "currency": currency,
                "status": status,
            },
        )
        assert response.status_code == 201

    report = client.get("/api/v1/reports/expenses")

    assert report.status_code == 200
    body = report.json()
    assert body["total"] == 3
    assert {
        (row["currency"], row["status"]): (
            row["total_amount"],
            row["expense_count"],
        )
        for row in body["items"]
    } == {
        ("VND", "submitted"): ("20.00", 2),
        ("USD", "submitted"): ("10.00", 1),
        ("VND", "approved"): ("5.00", 1),
    }


def test_expense_report_requires_staff_role(operations_context) -> None:
    client, _, _ = operations_context
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(
        roles=[Role(code="CUSTOMER", description="Customer")]
    )

    response = client.get("/api/v1/reports/expenses")

    assert response.status_code == 403
