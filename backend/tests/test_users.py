from uuid import UUID
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.api.dependencies import get_current_user
from app.core.security import verify_password
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models.audit import AuditLog
from app.models.identity import Role, User


@pytest.fixture
def user_management_context():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        roles = {
            code: Role(code=code, description=code.title())
            for code in ("SUPER_ADMIN", "ADMIN", "STAFF")
        }
        super_admin = User(
            email="super@example.com",
            password_hash="not-used",
            is_active=True,
            roles=[roles["SUPER_ADMIN"]],
        )
        admin = User(
            email="admin@example.com",
            password_hash="not-used",
            is_active=True,
            roles=[roles["ADMIN"]],
        )
        existing_staff = User(
            email="staff@example.com",
            password_hash="not-used",
            is_active=True,
            roles=[roles["STAFF"]],
        )
        session.add_all([super_admin, admin, existing_staff])
        session.commit()
        actor_records = {
            code: SimpleNamespace(
                id=user.id,
                email=user.email,
                roles=[SimpleNamespace(code=code)],
            )
            for code, user in (
                ("SUPER_ADMIN", super_admin),
                ("ADMIN", admin),
                ("STAFF", existing_staff),
            )
        }

    current_actor = {"user": actor_records["ADMIN"]}

    def override_db():
        with Session(engine) as session:
            yield session

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_current_user] = lambda: current_actor["user"]
    with TestClient(app) as client:
        yield client, engine, current_actor, actor_records

    app.dependency_overrides.clear()
    engine.dispose()


def test_admin_can_create_staff_with_a_hashed_password_and_audit_event(
    user_management_context,
) -> None:
    client, engine, _, actor_records = user_management_context

    response = client.post(
        "/api/v1/users",
        json={
            "email": "new-staff@example.com",
            "password": "secure-password",
            "role": "STAFF",
        },
    )

    assert response.status_code == 201
    assert response.json()["roles"] == ["STAFF"]
    with Session(engine) as session:
        created = session.scalar(
            select(User).where(User.email == "new-staff@example.com")
        )
        audit = session.scalar(
            select(AuditLog).where(
                AuditLog.resource_id == UUID(response.json()["id"])
            )
        )
        assert created is not None
        assert verify_password("secure-password", created.password_hash)
        assert audit is not None
        assert audit.actor_user_id == actor_records["ADMIN"].id
        assert audit.action == "user.created"
        assert audit.details == {"role": "STAFF"}


def test_admin_can_provision_customer_account_with_audit_event(
    user_management_context,
) -> None:
    client, engine, _, actor_records = user_management_context

    response = client.post(
        "/api/v1/users",
        json={
            "email": "customer@example.com",
            "password": "secure-password",
            "role": "CUSTOMER",
        },
    )

    assert response.status_code == 201
    assert response.json()["roles"] == ["CUSTOMER"]
    with Session(engine) as session:
        created = session.scalar(
            select(User).where(User.email == "customer@example.com")
        )
        events = session.scalars(
            select(AuditLog).where(
                AuditLog.resource_id == UUID(response.json()["id"])
            )
        ).all()
        assert created is not None
        assert verify_password("secure-password", created.password_hash)
        assert {event.action for event in events} == {
            "user.created",
            "customer_account.created",
        }
        account_event = next(
            event for event in events if event.action == "customer_account.created"
        )
        assert account_event.actor_user_id == actor_records["ADMIN"].id
        assert account_event.details == {
            "customer_id": None,
            "user_id": str(created.id),
        }


def test_admin_can_only_manage_staff_accounts(user_management_context) -> None:
    client, _, _, actor_records = user_management_context
    admin_id = str(actor_records["ADMIN"].id)

    forbidden_role = client.post(
        "/api/v1/users",
        json={
            "email": "new-admin@example.com",
            "password": "secure-password",
            "role": "ADMIN",
        },
    )
    change_self = client.patch(
        f"/api/v1/users/{admin_id}",
        json={"role": "STAFF"},
    )

    assert forbidden_role.status_code == 403
    assert change_self.status_code == 403
    assert change_self.json()["detail"]["code"] == "SELF_ROLE_CHANGE"


def test_staff_cannot_access_user_management(user_management_context) -> None:
    client, _, current_actor, actor_records = user_management_context
    current_actor["user"] = actor_records["STAFF"]

    users = client.get("/api/v1/users")
    roles = client.get("/api/v1/users/roles")
    create_customer = client.post(
        "/api/v1/users",
        json={
            "email": "not-allowed@example.com",
            "password": "secure-password",
            "role": "CUSTOMER",
        },
    )

    assert users.status_code == 403
    assert roles.status_code == 403
    assert create_customer.status_code == 403


def test_admin_user_listing_is_scoped_to_staff(user_management_context) -> None:
    client, _, _, _ = user_management_context

    response = client.get("/api/v1/users")

    assert response.status_code == 200
    assert [item["email"] for item in response.json()["items"]] == [
        "staff@example.com"
    ]
    assert [item["code"] for item in client.get("/api/v1/users/roles").json()] == [
        "STAFF",
        "CUSTOMER",
    ]


def test_super_admin_can_manage_admins_but_cannot_assign_super_admin(
    user_management_context,
) -> None:
    client, _, current_actor, actor_records = user_management_context
    current_actor["user"] = actor_records["SUPER_ADMIN"]

    create_admin = client.post(
        "/api/v1/users",
        json={
            "email": "new-admin@example.com",
            "password": "secure-password",
            "role": "ADMIN",
        },
    )
    create_super_admin = client.post(
        "/api/v1/users",
        json={
            "email": "another-super@example.com",
            "password": "secure-password",
            "role": "SUPER_ADMIN",
        },
    )

    assert create_admin.status_code == 201
    assert create_super_admin.status_code == 403


def test_user_update_is_audited_and_self_deactivation_is_forbidden(
    user_management_context,
) -> None:
    client, engine, _, actor_records = user_management_context
    staff_id = (
        next(
            user.id
            for user in actor_records.values()
            if user.email == "staff@example.com"
        )
    )

    updated = client.patch(
        f"/api/v1/users/{staff_id}",
        json={"email": "renamed-staff@example.com", "is_active": False},
    )
    self_deactivation = client.patch(
        f"/api/v1/users/{actor_records['ADMIN'].id}",
        json={"is_active": False},
    )

    assert updated.status_code == 200
    assert updated.json()["email"] == "renamed-staff@example.com"
    assert updated.json()["is_active"] is False
    assert self_deactivation.status_code == 403
    with Session(engine) as session:
        event = session.scalar(
            select(AuditLog).where(
                AuditLog.resource_id == staff_id,
                AuditLog.action == "user.updated",
            )
        )
        assert event is not None
        assert event.details == {
            "role_changed": False,
            "active_changed": True,
            "password_changed": False,
            "email_changed": True,
        }
