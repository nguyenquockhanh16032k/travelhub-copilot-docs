from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from jose import jwt
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.api.dependencies import get_current_user, require_permission
from app.core.config import settings
from app.core.permissions import Permission
from app.core.security import ALGORITHM, hash_password
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models.identity import Role, User


@pytest.fixture
def auth_context():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        admin_role = Role(code="ADMIN", description="Administrator")
        customer_role = Role(code="CUSTOMER", description="Customer")
        admin = User(
            email="admin@example.com",
            password_hash=hash_password("secure-password"),
            is_active=True,
        )
        admin.roles.append(admin_role)
        customer = User(
            email="customer@example.com",
            password_hash=hash_password("secure-password"),
            is_active=True,
        )
        customer.roles.append(customer_role)
        session.add_all([admin, customer])
        session.commit()
        session.refresh(admin)
        session.refresh(customer)
        admin_id = admin.id
        customer_id = customer.id

    def override_db():
        with Session(engine) as session:
            yield session

    app.dependency_overrides[get_db] = override_db
    with TestClient(app) as client:
        yield client, engine, admin_id, customer_id

    app.dependency_overrides.clear()
    engine.dispose()


def test_login_and_current_user(auth_context) -> None:
    client, _, _, _ = auth_context

    response = client.post(
        "/api/v1/auth/login",
        json={"email": "admin@example.com", "password": "secure-password"},
    )

    assert response.status_code == 200
    tokens = response.json()
    assert tokens["token_type"] == "bearer"
    assert tokens["access_token"]
    assert tokens["refresh_token"]

    me_response = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {tokens['access_token']}"},
    )
    assert me_response.status_code == 200
    assert me_response.json()["email"] == "admin@example.com"
    assert me_response.json()["roles"] == ["ADMIN"]


def test_invalid_credentials(auth_context) -> None:
    client, _, _, _ = auth_context

    response = client.post(
        "/api/v1/auth/login",
        json={"email": "admin@example.com", "password": "wrong-password"},
    )

    assert response.status_code == 401
    assert response.json()["detail"]["code"] == "AUTHENTICATION_FAILED"


def test_expired_access_token(auth_context) -> None:
    client, _, admin_id, _ = auth_context
    expired = jwt.encode(
        {
            "sub": str(admin_id),
            "exp": datetime.now(timezone.utc) - timedelta(minutes=1),
            "type": "access",
        },
        settings.jwt_secret_key,
        algorithm=ALGORITHM,
    )

    response = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {expired}"},
    )

    assert response.status_code == 401
    assert response.json()["detail"]["code"] == "INVALID_TOKEN"


def test_refresh_rotation_and_logout(auth_context) -> None:
    client, _, _, _ = auth_context
    login = client.post(
        "/api/v1/auth/login",
        json={"email": "customer@example.com", "password": "secure-password"},
    )
    original_refresh = login.json()["refresh_token"]

    refreshed = client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": original_refresh},
    )
    assert refreshed.status_code == 200
    rotated_refresh = refreshed.json()["refresh_token"]

    reused = client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": original_refresh},
    )
    assert reused.status_code == 401

    logout = client.post(
        "/api/v1/auth/logout",
        json={"refresh_token": rotated_refresh},
    )
    assert logout.status_code == 204

    reused_after_logout = client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": rotated_refresh},
    )
    assert reused_after_logout.status_code == 401


def test_permission_dependency_allows_admin_staff_and_rejects_customer(
    auth_context,
) -> None:
    client, _, admin_id, customer_id = auth_context

    with Session(auth_context[1]) as session:
        admin = session.get(User, admin_id)
        customer = session.get(User, customer_id)

        booking_read_permission = require_permission(Permission.BOOKINGS_READ)
        payment_permission = require_permission(Permission.PAYMENTS_WRITE)
        staff = SimpleNamespace(roles=[Role(code="STAFF")])

        assert booking_read_permission(admin) is admin
        assert payment_permission(admin) is admin
        assert booking_read_permission(staff) is staff

        with pytest.raises(Exception) as exc:
            payment_permission(staff)
        assert getattr(exc.value, "status_code", None) == 403
        with pytest.raises(Exception) as customer_exc:
            booking_read_permission(customer)
        assert getattr(customer_exc.value, "status_code", None) == 403
