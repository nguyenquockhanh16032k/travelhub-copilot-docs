import uuid
from types import SimpleNamespace
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.api.dependencies import get_current_user
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models.audit import AuditLog
from app.models.identity import Role, User


@pytest.fixture
def customer_context():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)

    def override_db():
        with Session(engine) as session:
            yield session

    admin = SimpleNamespace(
        id=uuid.uuid4(),
        roles=[Role(code="ADMIN", description="Administrator")]
    )
    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_current_user] = lambda: admin

    with TestClient(app) as client:
        yield client, engine

    app.dependency_overrides.clear()
    engine.dispose()


def test_create_and_list_customer(customer_context) -> None:
    client, engine = customer_context

    created = client.post(
        "/api/v1/customers",
        json={
            "full_name": "Nguyen Van A",
            "email": "nguyen@example.com",
            "phone": "0900000000",
            "address": "Ho Chi Minh City",
        },
    )
    assert created.status_code == 201
    customer_id = created.json()["id"]

    updated = client.patch(
        f"/api/v1/customers/{customer_id}",
        json={"full_name": "Nguyen Van A Updated"},
    )
    assert updated.status_code == 200

    listed = client.get("/api/v1/customers", params={"search": "Nguyen"})
    assert listed.status_code == 200
    body = listed.json()
    assert body["total"] == 1
    assert body["items"][0]["email"] == "nguyen@example.com"
    with Session(engine) as session:
        events = session.scalars(
            select(AuditLog)
            .where(AuditLog.resource_id == uuid.UUID(customer_id))
            .order_by(AuditLog.action)
        ).all()
    assert {event.action for event in events} == {
        "customer.created",
        "customer.updated",
    }


def test_duplicate_customer_email_is_rejected(customer_context) -> None:
    client, _ = customer_context
    payload = {
        "full_name": "Guest",
        "email": "guest@example.com",
    }

    assert client.post("/api/v1/customers", json=payload).status_code == 201
    duplicate = client.post("/api/v1/customers", json=payload)

    assert duplicate.status_code == 409
    assert duplicate.json()["detail"]["code"] == "EMAIL_EXISTS"


def _create_customer_user(engine, email: str, role_code: str = "CUSTOMER") -> UUID:
    with Session(engine) as session:
        role = session.scalar(select(Role).where(Role.code == role_code))
        if role is None:
            role = Role(code=role_code, description=role_code.title())
        user = User(
            email=email,
            password_hash="unused",
            is_active=True,
            roles=[role],
        )
        session.add(user)
        session.commit()
        return user.id


def test_customer_account_link_and_unlink_are_audited(customer_context) -> None:
    client, engine = customer_context
    user_id = _create_customer_user(engine, "customer-account@example.com")

    created = client.post(
        "/api/v1/customers",
        json={
            "full_name": "Linked Customer",
            "email": "linked@example.com",
            "user_id": str(user_id),
        },
    )
    assert created.status_code == 201
    customer_id = UUID(created.json()["id"])

    unlinked = client.patch(
        f"/api/v1/customers/{customer_id}",
        json={"user_id": None},
    )
    assert unlinked.status_code == 200
    assert unlinked.json()["user_id"] is None

    with Session(engine) as session:
        events = session.scalars(
            select(AuditLog)
            .where(
                AuditLog.resource_id == customer_id,
                AuditLog.action.in_(
                    ("customer.account_linked", "customer.account_unlinked")
                ),
            )
            .order_by(AuditLog.created_at)
        ).all()
    assert [event.action for event in events] == [
        "customer.account_linked",
        "customer.account_unlinked",
    ]
    assert all(event.actor_user_id is not None for event in events)
    assert events[0].details == {
        "customer_id": str(customer_id),
        "user_id": str(user_id),
    }
    assert events[1].details == events[0].details
    assert all(event.created_at is not None for event in events)


def test_customer_account_cannot_be_linked_to_two_profiles(customer_context) -> None:
    client, engine = customer_context
    user_id = _create_customer_user(engine, "single-account@example.com")
    first = client.post(
        "/api/v1/customers",
        json={"full_name": "First", "user_id": str(user_id)},
    )
    second = client.post(
        "/api/v1/customers",
        json={"full_name": "Second"},
    )
    duplicate = client.patch(
        f"/api/v1/customers/{second.json()['id']}",
        json={"user_id": str(user_id)},
    )

    assert first.status_code == 201
    assert second.status_code == 201
    assert duplicate.status_code == 409
    assert duplicate.json()["detail"]["code"] == "CUSTOMER_ACCOUNT_LINKED"


def test_only_active_customer_role_accounts_can_be_linked(customer_context) -> None:
    client, engine = customer_context
    staff_user_id = _create_customer_user(
        engine,
        "staff-account@example.com",
        role_code="STAFF",
    )

    response = client.post(
        "/api/v1/customers",
        json={"full_name": "Invalid Link", "user_id": str(staff_user_id)},
    )

    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "CUSTOMER_ACCOUNT_REQUIRED"


def test_linkable_accounts_are_limited_to_unlinked_customer_users(
    customer_context,
) -> None:
    client, engine = customer_context
    linked_user_id = _create_customer_user(engine, "linked-account@example.com")
    available_user_id = _create_customer_user(engine, "available@example.com")
    customer = client.post(
        "/api/v1/customers",
        json={"full_name": "Already Linked", "user_id": str(linked_user_id)},
    )

    available = client.get("/api/v1/customers/linkable-accounts")
    current = client.get(
        "/api/v1/customers/linkable-accounts",
        params={"customer_id": customer.json()["id"]},
    )

    assert available.status_code == 200
    assert [item["id"] for item in available.json()["items"]] == [
        str(available_user_id)
    ]
    assert current.status_code == 200
    assert {item["id"] for item in current.json()["items"]} == {
        str(linked_user_id),
        str(available_user_id),
    }
