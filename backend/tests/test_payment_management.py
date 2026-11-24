from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.core.security import create_access_token
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models.audit import AuditLog
from app.models.booking import Booking, Payment
from app.models.customer import Customer
from app.models.identity import Role, User
from app.models.tour import Tour, TourDeparture


@pytest.fixture
def payment_context():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        admin_role = Role(code="ADMIN", description="Administrator")
        staff_role = Role(code="STAFF", description="Staff")
        customer_role = Role(code="CUSTOMER", description="Customer")
        admin = User(
            email="payments-admin@example.com",
            password_hash="unused",
            is_active=True,
            roles=[admin_role],
        )
        staff = User(
            email="payments-staff@example.com",
            password_hash="unused",
            is_active=True,
            roles=[staff_role],
        )
        owner = User(
            email="payments-owner@example.com",
            password_hash="unused",
            is_active=True,
            roles=[customer_role],
        )
        other = User(
            email="payments-other@example.com",
            password_hash="unused",
            is_active=True,
            roles=[customer_role],
        )
        session.add_all([admin, staff, owner, other])
        session.flush()

        owner_customer = Customer(
            user_id=owner.id,
            full_name="Owner Customer",
            email=owner.email,
        )
        other_customer = Customer(
            user_id=other.id,
            full_name="Other Customer",
            email=other.email,
        )
        tour = Tour(
            title="Payment Test Tour",
            slug=f"payment-test-{uuid4().hex}",
            duration_days=2,
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
            available_seats=8,
            price=Decimal("1000000.00"),
            currency="VND",
            status="open",
        )
        session.add(departure)
        session.flush()

        now = datetime.now(timezone.utc)
        owner_booking = Booking(
            reference=f"TH-PAY-{uuid4().hex[:8].upper()}",
            departure_id=departure.id,
            customer_id=owner_customer.id,
            contact_name=owner_customer.full_name,
            contact_email=owner.email,
            contact_phone="0900000000",
            passenger_count=1,
            status="pending",
            expires_at=now + timedelta(minutes=30),
            total_amount=Decimal("1000000.00"),
            currency="VND",
        )
        other_booking = Booking(
            reference=f"TH-OTHER-{uuid4().hex[:8].upper()}",
            departure_id=departure.id,
            customer_id=other_customer.id,
            contact_name=other_customer.full_name,
            contact_email=other.email,
            contact_phone="0900000001",
            passenger_count=1,
            status="confirmed",
            expires_at=None,
            total_amount=Decimal("1000000.00"),
            currency="VND",
        )
        session.add_all([owner_booking, other_booking])
        session.commit()
        ids = {
            "admin": admin.id,
            "staff": staff.id,
            "owner": owner.id,
            "other": other.id,
            "owner_booking": owner_booking.id,
            "other_booking": other_booking.id,
            "departure": departure.id,
        }

    def override_db():
        with Session(engine) as session:
            yield session

    app.dependency_overrides[get_db] = override_db
    with TestClient(app) as client:
        yield client, ids, engine
    app.dependency_overrides.clear()
    engine.dispose()


def headers(user_id: UUID, idempotency_key: str | None = None) -> dict[str, str]:
    result = {"Authorization": f"Bearer {create_access_token(str(user_id))}"}
    if idempotency_key:
        result["Idempotency-Key"] = idempotency_key
    return result


def post_payment(
    client: TestClient,
    admin_id: UUID,
    booking_id: UUID,
    amount: str,
    *,
    key: str | None = None,
    status: str = "pending",
    notes: str | None = None,
    transaction_reference: str | None = None,
):
    payload: dict[str, object] = {
        "booking_id": str(booking_id),
        "amount": amount,
        "currency": "VND",
        "method": "bank_transfer",
        "status": status,
    }
    if notes is not None:
        payload["notes"] = notes
    if transaction_reference is not None:
        payload["transaction_reference"] = transaction_reference
    return client.post(
        "/api/v1/payments",
        json=payload,
        headers=headers(admin_id, key or f"payment-{uuid4().hex}"),
    )


def test_partial_and_full_payments_have_backend_summaries_and_confirmation(
    payment_context,
) -> None:
    client, ids, engine = payment_context
    first = post_payment(
        client,
        ids["admin"],
        ids["owner_booking"],
        "400000.00",
    )
    assert first.status_code == 201
    assert first.json()["status"] == "pending"

    verified_first = client.post(
        f"/api/v1/payments/{first.json()['id']}/verify",
        headers=headers(ids["admin"]),
    )
    repeated_verify = client.post(
        f"/api/v1/payments/{first.json()['id']}/verify",
        headers=headers(ids["admin"]),
    )
    assert verified_first.status_code == 200
    assert repeated_verify.status_code == 200
    assert verified_first.json()["status"] == "paid"

    partial = client.get(
        f"/api/v1/payments?booking_id={ids['owner_booking']}",
        headers=headers(ids["admin"]),
    )
    assert partial.status_code == 200
    assert partial.json()["booking_summary"]["verified_paid_amount"] == "400000.00"
    assert partial.json()["booking_summary"]["outstanding_balance"] == "600000.00"
    assert partial.json()["booking_summary"]["payment_completion_status"] == (
        "PARTIALLY_PAID"
    )

    with Session(engine) as session:
        booking = session.get(Booking, ids["owner_booking"])
        verification_events = session.scalars(
            select(AuditLog).where(
                AuditLog.resource_id == UUID(first.json()["id"]),
                AuditLog.action == "payment.verified",
            )
        ).all()
    assert booking is not None
    assert booking.status == "pending"
    assert len(verification_events) == 1

    second = post_payment(
        client,
        ids["admin"],
        ids["owner_booking"],
        "600000.00",
    )
    assert second.status_code == 201
    fully_paid = client.post(
        f"/api/v1/payments/{second.json()['id']}/verify",
        headers=headers(ids["admin"]),
    )
    assert fully_paid.status_code == 200

    with Session(engine) as session:
        booking = session.get(Booking, ids["owner_booking"])
    assert booking is not None
    assert booking.status == "confirmed"
    assert booking.expires_at is None

    summary = client.get(
        f"/api/v1/payments?booking_id={ids['owner_booking']}",
        headers=headers(ids["admin"]),
    ).json()["booking_summary"]
    assert summary["verified_paid_amount"] == "1000000.00"
    assert summary["outstanding_balance"] == "0.00"
    assert summary["payment_completion_status"] == "FULLY_PAID"
    additional_normal = post_payment(
        client,
        ids["admin"],
        ids["owner_booking"],
        "1.00",
    )
    assert additional_normal.status_code == 409
    assert additional_normal.json()["detail"]["code"] == (
        "PAYMENT_BALANCE_SETTLED"
    )


def test_payment_creation_is_idempotent_and_rejects_changed_payload(
    payment_context,
) -> None:
    client, ids, engine = payment_context
    key = f"manual-{uuid4().hex}"
    first = post_payment(
        client,
        ids["admin"],
        ids["owner_booking"],
        "250000.00",
        key=key,
    )
    retry = post_payment(
        client,
        ids["admin"],
        ids["owner_booking"],
        "250000.00",
        key=key,
    )
    changed = post_payment(
        client,
        ids["admin"],
        ids["owner_booking"],
        "260000.00",
        key=key,
    )

    assert first.status_code == 201
    assert retry.status_code == 201
    assert retry.json()["id"] == first.json()["id"]
    assert changed.status_code == 409
    assert changed.json()["detail"]["code"] == "IDEMPOTENCY_KEY_REUSED"
    with Session(engine) as session:
        count = session.scalar(select(func.count(Payment.id)))
    assert count == 1


def test_transaction_reference_is_unique_across_payment_records(payment_context) -> None:
    client, ids, engine = payment_context
    first = post_payment(
        client,
        ids["admin"],
        ids["owner_booking"],
        "100000.00",
        transaction_reference="UNIQUE-REFERENCE-001",
    )
    duplicate = post_payment(
        client,
        ids["admin"],
        ids["owner_booking"],
        "100000.00",
        transaction_reference="UNIQUE-REFERENCE-001",
    )
    assert first.status_code == 201
    assert duplicate.status_code == 409
    assert duplicate.json()["detail"]["code"] == "TRANSACTION_REFERENCE_EXISTS"
    with Session(engine) as session:
        count = session.scalar(select(func.count(Payment.id)))
    assert count == 1


def test_normal_overpayment_is_rejected_and_exception_is_audited(
    payment_context,
) -> None:
    client, ids, engine = payment_context
    direct_overpayment = post_payment(
        client,
        ids["admin"],
        ids["owner_booking"],
        "1100000.00",
        status="paid",
    )
    assert direct_overpayment.status_code == 409
    assert direct_overpayment.json()["detail"]["code"] == (
        "OVERPAYMENT_EXCEPTION_REQUIRED"
    )

    first_pending = post_payment(
        client,
        ids["admin"],
        ids["owner_booking"],
        "600000.00",
    )
    pending = post_payment(
        client,
        ids["admin"],
        ids["owner_booking"],
        "600000.00",
    )
    assert first_pending.status_code == pending.status_code == 201
    first_verified = client.post(
        f"/api/v1/payments/{first_pending.json()['id']}/verify",
        headers=headers(ids["admin"]),
    )
    assert first_verified.status_code == 200
    rejected = client.post(
        f"/api/v1/payments/{pending.json()['id']}/verify",
        headers=headers(ids["admin"]),
    )
    assert rejected.status_code == 409
    assert rejected.json()["detail"]["code"] == "OVERPAYMENT_EXCEPTION_REQUIRED"

    exception = client.post(
        f"/api/v1/payments/{pending.json()['id']}/financial-exception",
        json={
            "reason": "Cash received above the booking total",
            "confirmation": True,
        },
        headers=headers(ids["admin"]),
    )
    assert exception.status_code == 200
    assert exception.json()["status"] == "paid"
    assert exception.json()["requires_resolution"] is True
    assert exception.json()["resolution_reason"] == (
        "Cash received above the booking total"
    )
    summary = client.get(
        f"/api/v1/payments?booking_id={ids['owner_booking']}",
        headers=headers(ids["admin"]),
    ).json()["booking_summary"]
    assert summary["verified_paid_amount"] == "1200000.00"
    assert summary["outstanding_balance"] == "0.00"
    assert summary["overpaid_amount"] == "200000.00"
    assert summary["payment_completion_status"] == "OVERPAID"
    exceptions = client.get(
        "/api/v1/payments?requires_resolution=true&status_filter=paid",
        headers=headers(ids["admin"]),
    )
    assert exceptions.status_code == 200
    assert [item["id"] for item in exceptions.json()["items"]] == [
        pending.json()["id"]
    ]
    with Session(engine) as session:
        booking = session.get(Booking, ids["owner_booking"])
        exception_events = session.scalars(
            select(AuditLog).where(
                AuditLog.resource_id == UUID(pending.json()["id"]),
                AuditLog.action == "payment.exception_recorded",
            )
        ).all()
    assert booking is not None
    assert booking.status == "pending"
    assert len(exception_events) == 1


def test_financial_exception_requires_explicit_confirmation(payment_context) -> None:
    client, ids, engine = payment_context
    response = client.post(
        "/api/v1/payments/exceptions",
        json={
            "booking_id": str(ids["owner_booking"]),
            "amount": "1100000.00",
            "currency": "VND",
            "method": "cash",
            "reason": "Actual overpayment received",
            "confirmation": False,
        },
        headers=headers(ids["admin"], f"confirm-{uuid4().hex}"),
    )
    assert response.status_code == 422
    with Session(engine) as session:
        count = session.scalar(select(func.count(Payment.id)))
    assert count == 0


def test_paid_receipt_for_expired_booking_is_explicit_and_does_not_restore_seats(
    payment_context,
) -> None:
    client, ids, engine = payment_context
    with Session(engine) as session:
        booking = session.get(Booking, ids["owner_booking"])
        assert booking is not None
        booking.expires_at = datetime.now(timezone.utc) - timedelta(minutes=1)
        session.commit()

    normal_record = post_payment(
        client,
        ids["admin"],
        ids["owner_booking"],
        "250000.00",
    )
    assert normal_record.status_code == 409
    assert normal_record.json()["detail"]["code"] == (
        "FINANCIAL_EXCEPTION_REQUIRED"
    )

    exception = client.post(
        "/api/v1/payments/exceptions",
        json={
            "booking_id": str(ids["owner_booking"]),
            "amount": "250000.00",
            "currency": "VND",
            "method": "cash",
            "status": "paid",
            "reason": "Late cash receipt for expired booking",
            "confirmation": True,
        },
        headers=headers(ids["admin"], f"late-{uuid4().hex}"),
    )
    assert exception.status_code == 201
    assert exception.json()["requires_resolution"] is True

    with Session(engine) as session:
        booking = session.get(Booking, ids["owner_booking"])
        departure = session.get(TourDeparture, ids["departure"])
    assert booking is not None
    assert departure is not None
    assert booking.status == "expired"
    assert departure.available_seats == 9


def test_cancelling_paid_partial_booking_flags_funds_without_refund(
    payment_context,
) -> None:
    client, ids, engine = payment_context
    payment = post_payment(
        client,
        ids["admin"],
        ids["owner_booking"],
        "300000.00",
        status="paid",
    )
    assert payment.status_code == 201
    cancelled = client.post(
        f"/api/v1/bookings/{ids['owner_booking']}/cancel",
        json={"reason": "Customer cancellation request"},
        headers=headers(ids["admin"]),
    )
    assert cancelled.status_code == 200
    with Session(engine) as session:
        booking = session.get(Booking, ids["owner_booking"])
        departure = session.get(TourDeparture, ids["departure"])
        recorded = session.get(Payment, UUID(payment.json()["id"]))
    assert booking is not None
    assert departure is not None
    assert recorded is not None
    assert booking.status == "cancelled"
    assert departure.available_seats == 9
    assert recorded.status == "paid"
    assert recorded.requires_resolution is True
    assert recorded.resolution_reason == "Booking was cancelled"


def test_expiring_partially_paid_booking_flags_existing_paid_records(
    payment_context,
) -> None:
    client, ids, engine = payment_context
    payment = post_payment(
        client,
        ids["admin"],
        ids["owner_booking"],
        "300000.00",
        status="paid",
    )
    assert payment.status_code == 201

    with Session(engine) as session:
        booking = session.get(Booking, ids["owner_booking"])
        assert booking is not None
        booking.expires_at = datetime.now(timezone.utc) - timedelta(minutes=1)
        session.commit()

    listed = client.get(
        f"/api/v1/payments?booking_id={ids['owner_booking']}",
        headers=headers(ids["admin"]),
    )
    assert listed.status_code == 200
    item = listed.json()["items"][0]
    assert item["requires_resolution"] is True
    assert item["status"] == "paid"
    assert item["booking_status"] == "expired"
    assert item["resolution_reason"] == (
        "Booking hold expired before payment completion"
    )


def test_admin_payment_access_customer_isolation_and_internal_note_protection(
    payment_context,
) -> None:
    client, ids, _ = payment_context
    payment = post_payment(
        client,
        ids["admin"],
        ids["owner_booking"],
        "200000.00",
        status="paid",
        notes="Internal reconciliation note",
    )
    assert payment.status_code == 201

    admin_list = client.get(
        "/api/v1/payments",
        headers=headers(ids["admin"]),
    )
    staff_list = client.get(
        "/api/v1/payments",
        headers=headers(ids["staff"]),
    )
    customer_list = client.get(
        "/api/v1/payments",
        headers=headers(ids["owner"]),
    )
    staff_create = post_payment(
        client,
        ids["staff"],
        ids["owner_booking"],
        "100.00",
    )
    own_history = client.get(
        f"/api/v1/customers/me/bookings/{ids['owner_booking']}",
        headers=headers(ids["owner"]),
    )
    foreign_history = client.get(
        f"/api/v1/customers/me/bookings/{ids['other_booking']}",
        headers=headers(ids["owner"]),
    )

    assert admin_list.status_code == 200
    assert admin_list.json()["items"][0]["notes"] == "Internal reconciliation note"
    assert admin_list.json()["items"][0]["recorded_by"] == (
        "payments-admin@example.com"
    )
    assert admin_list.json()["items"][0]["verified_by"] == (
        "payments-admin@example.com"
    )
    assert staff_list.status_code == 403
    assert customer_list.status_code == 403
    assert staff_create.status_code == 403
    assert own_history.status_code == 200
    own_booking = own_history.json()
    assert own_booking["verified_paid_amount"] == "200000.00"
    assert own_booking["outstanding_balance"] == "800000.00"
    assert own_booking["payment_completion_status"] == "PARTIALLY_PAID"
    assert own_booking["payments"][0]["status"] == "paid"
    assert "notes" not in own_booking["payments"][0]
    assert "requires_resolution" not in own_booking["payments"][0]
    assert "resolution_reason" not in own_booking["payments"][0]
    assert "recorded_by" not in own_booking["payments"][0]
    assert foreign_history.status_code == 404


def test_staff_cannot_confirm_partially_paid_booking_but_admin_can(
    payment_context,
) -> None:
    client, ids, _ = payment_context
    payment = post_payment(
        client,
        ids["admin"],
        ids["owner_booking"],
        "300000.00",
        status="paid",
    )
    assert payment.status_code == 201

    staff_confirmation = client.post(
        f"/api/v1/bookings/{ids['owner_booking']}/confirm",
        json={"reason": "Staff confirmation"},
        headers=headers(ids["staff"]),
    )
    admin_confirmation = client.post(
        f"/api/v1/bookings/{ids['owner_booking']}/confirm",
        json={"reason": "Approved partial payment"},
        headers=headers(ids["admin"]),
    )

    assert staff_confirmation.status_code == 403
    assert staff_confirmation.json()["detail"]["code"] == "FORBIDDEN"
    assert admin_confirmation.status_code == 200
    assert admin_confirmation.json()["status"] == "confirmed"


def test_staff_cannot_confirm_booking_with_resolution_required_payment(
    payment_context,
) -> None:
    client, ids, _ = payment_context
    exception = client.post(
        "/api/v1/payments/exceptions",
        json={
            "booking_id": str(ids["owner_booking"]),
            "amount": "1100000.00",
            "currency": "VND",
            "method": "cash",
            "reason": "Overpayment awaiting resolution",
            "confirmation": True,
        },
        headers=headers(ids["admin"], f"exception-{uuid4().hex}"),
    )
    assert exception.status_code == 201
    assert exception.json()["requires_resolution"] is True

    staff_confirmation = client.post(
        f"/api/v1/bookings/{ids['owner_booking']}/confirm",
        json={"reason": "Staff confirmation"},
        headers=headers(ids["staff"]),
    )

    assert staff_confirmation.status_code == 403
    assert staff_confirmation.json()["detail"]["code"] == "FORBIDDEN"


@pytest.mark.parametrize("amount", ["0.00", "-1.00", "1.001"])
def test_payment_amount_requires_positive_two_decimal_precision(
    payment_context,
    amount: str,
) -> None:
    client, ids, _ = payment_context
    response = post_payment(
        client,
        ids["admin"],
        ids["owner_booking"],
        amount,
    )
    assert response.status_code == 422


def test_staff_cannot_verify_or_record_financial_exceptions(payment_context) -> None:
    client, ids, _ = payment_context
    payment = post_payment(
        client,
        ids["admin"],
        ids["owner_booking"],
        "100000.00",
    )
    assert payment.status_code == 201

    verification = client.post(
        f"/api/v1/payments/{payment.json()['id']}/verify",
        headers=headers(ids["staff"]),
    )
    exception = client.post(
        "/api/v1/payments/exceptions",
        json={
            "booking_id": str(ids["owner_booking"]),
            "amount": "1100000.00",
            "currency": "VND",
            "method": "cash",
            "reason": "Not permitted for staff",
            "confirmation": True,
        },
        headers=headers(ids["staff"], f"staff-exception-{uuid4().hex}"),
    )
    exception_verification = client.post(
        f"/api/v1/payments/{payment.json()['id']}/financial-exception",
        json={
            "reason": "Not permitted for staff",
            "confirmation": True,
        },
        headers=headers(ids["staff"]),
    )

    assert verification.status_code == 403
    assert exception.status_code == 403
    assert exception_verification.status_code == 403


def test_payment_list_supports_search_filter_and_pagination(payment_context) -> None:
    client, ids, _ = payment_context
    first = post_payment(
        client,
        ids["admin"],
        ids["owner_booking"],
        "100000.00",
        transaction_reference="SEARCH-TX-1",
    )
    second = post_payment(
        client,
        ids["admin"],
        ids["other_booking"],
        "200000.00",
        transaction_reference="SEARCH-TX-2",
    )
    assert first.status_code == second.status_code == 201

    response = client.get(
        "/api/v1/payments?page=1&size=1&method_filter=bank_transfer&search=SEARCH-TX",
        headers=headers(ids["admin"]),
    )
    assert response.status_code == 200
    assert response.json()["total"] == 2
    assert len(response.json()["items"]) == 1
    assert response.json()["pages"] == 2
