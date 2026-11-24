import os
from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from threading import Barrier
from uuid import UUID, uuid4

import pytest
from sqlalchemy import create_engine, func, select, text
from sqlalchemy.engine import Engine, make_url
from sqlalchemy.orm import Session

from app.db.base import Base
from app.models.audit import AuditLog
from app.models.booking import Booking, Payment
from app.models.tour import Tour, TourDeparture
from app.schemas.booking import BookingCreate, PaymentCreate, TravelerInput
from app.services.booking_service import (
    BookingError,
    create_booking,
    create_payment,
    expire_pending_bookings,
    verify_payment,
)


@pytest.fixture
def postgres_engine() -> Iterator[Engine]:
    database_url = os.environ.get("TEST_DATABASE_URL")
    if not database_url:
        pytest.skip("Set TEST_DATABASE_URL to run the PostgreSQL integration test")

    url = make_url(database_url)
    if url.get_backend_name() != "postgresql":
        pytest.fail("TEST_DATABASE_URL must use PostgreSQL")
    if not url.database or not url.database.lower().endswith("_test"):
        pytest.fail("TEST_DATABASE_URL database name must end with '_test'")

    schema_name = f"booking_it_{uuid4().hex}"
    admin_engine = create_engine(url, pool_pre_ping=True)
    with admin_engine.begin() as connection:
        connection.execute(text(f'CREATE SCHEMA "{schema_name}"'))

    engine = create_engine(
        url,
        pool_pre_ping=True,
        connect_args={"options": f"-csearch_path={schema_name}"},
    )
    try:
        Base.metadata.create_all(engine)
        yield engine
    finally:
        engine.dispose()
        with admin_engine.begin() as connection:
            connection.execute(text(f'DROP SCHEMA "{schema_name}" CASCADE'))
        admin_engine.dispose()


def test_concurrent_bookings_cannot_overbook_final_seat(
    postgres_engine: Engine,
) -> None:
    with Session(postgres_engine) as session:
        tour = Tour(
            title="Concurrent Booking Tour",
            slug=f"concurrent-booking-{uuid4().hex}",
            duration_days=1,
            destination="Can Tho",
            status="published",
        )
        session.add(tour)
        session.flush()
        departure = TourDeparture(
            tour_id=tour.id,
            start_date=date.today() + timedelta(days=10),
            end_date=date.today() + timedelta(days=11),
            capacity=1,
            available_seats=1,
            price=Decimal("1000000.00"),
            currency="VND",
            status="open",
        )
        session.add(departure)
        session.commit()
        departure_id = departure.id

    barrier = Barrier(2)

    def attempt_booking() -> str:
        with Session(postgres_engine) as session:
            payload = BookingCreate(
                departure_id=departure_id,
                contact_name="Guest",
                contact_email="guest@example.com",
                contact_phone="0900000000",
                travelers=[
                    TravelerInput(full_name="Guest One", traveler_type="adult")
                ],
            )
            barrier.wait(timeout=10)
            try:
                create_booking(session, payload)
            except BookingError as exc:
                return exc.code
            return "BOOKED"

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(lambda _: attempt_booking(), range(2)))

    assert results.count("BOOKED") == 1
    assert results.count("NOT_ENOUGH_SEATS") == 1

    with Session(postgres_engine) as session:
        departure = session.get(TourDeparture, departure_id)
        booking_count = session.scalar(select(func.count(Booking.id)))

    assert departure is not None
    assert departure.available_seats == 0
    assert booking_count == 1


def _create_payment_booking(engine: Engine) -> tuple[UUID, UUID]:
    with Session(engine) as session:
        tour = Tour(
            title="Concurrent Payment Tour",
            slug=f"concurrent-payment-{uuid4().hex}",
            duration_days=1,
            destination="Da Lat",
            status="published",
        )
        session.add(tour)
        session.flush()
        departure = TourDeparture(
            tour_id=tour.id,
            start_date=date.today() + timedelta(days=10),
            end_date=date.today() + timedelta(days=11),
            capacity=1,
            available_seats=0,
            price=Decimal("1000000.00"),
            currency="VND",
            status="open",
        )
        session.add(departure)
        session.flush()
        booking = Booking(
            reference=f"TH-PAY-{uuid4().hex[:12].upper()}",
            departure_id=departure.id,
            contact_name="Payment Guest",
            contact_email="payment-guest@example.com",
            contact_phone="0900000000",
            passenger_count=1,
            status="pending",
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=10),
            total_amount=Decimal("1000000.00"),
            currency="VND",
        )
        session.add(booking)
        session.commit()
        return booking.id, departure.id


def test_concurrent_payments_cannot_overpay_one_booking(
    postgres_engine: Engine,
) -> None:
    booking_id, departure_id = _create_payment_booking(postgres_engine)
    barrier = Barrier(2)

    def attempt_payment(index: int) -> str:
        with Session(postgres_engine) as session:
            payload = PaymentCreate(
                booking_id=booking_id,
                amount=Decimal("700000.00"),
                currency="VND",
                method="cash",
                status="paid",
                transaction_reference=f"CONCURRENT-PAY-{index}",
            )
            barrier.wait(timeout=10)
            try:
                create_payment(
                    session,
                    payload,
                    None,
                    f"concurrent-payment-key-{index}",
                )
            except BookingError as exc:
                return exc.code
            return "RECORDED"

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(attempt_payment, range(2)))

    assert results.count("RECORDED") == 1
    assert results.count("OVERPAYMENT_EXCEPTION_REQUIRED") == 1
    with Session(postgres_engine) as session:
        paid_total = session.scalar(
            select(func.coalesce(func.sum(Payment.amount), Decimal("0"))).where(
                Payment.booking_id == booking_id,
                Payment.status == "paid",
            )
        )
        booking = session.get(Booking, booking_id)
        departure = session.get(TourDeparture, departure_id)
    assert paid_total == Decimal("700000.00")
    assert booking is not None
    assert booking.status == "pending"
    assert departure is not None
    assert departure.available_seats == 0


def test_concurrent_payment_verification_serializes_balance_checks(
    postgres_engine: Engine,
) -> None:
    booking_id, _ = _create_payment_booking(postgres_engine)
    payment_ids: list[UUID] = []
    with Session(postgres_engine) as session:
        for index in range(2):
            payment = create_payment(
                session,
                PaymentCreate(
                    booking_id=booking_id,
                    amount=Decimal("600000.00"),
                    currency="VND",
                    method="cash",
                    status="pending",
                ),
                None,
                f"pending-verification-key-{index}",
            )
            payment_ids.append(payment.id)

    barrier = Barrier(2)

    def attempt_verification(payment_id: UUID) -> str:
        with Session(postgres_engine) as session:
            barrier.wait(timeout=10)
            try:
                verify_payment(session, payment_id, None)
            except BookingError as exc:
                return exc.code
            return "VERIFIED"

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(attempt_verification, payment_ids))

    assert results.count("VERIFIED") == 1
    assert results.count("OVERPAYMENT_EXCEPTION_REQUIRED") == 1
    with Session(postgres_engine) as session:
        paid_total = session.scalar(
            select(func.coalesce(func.sum(Payment.amount), Decimal("0"))).where(
                Payment.booking_id == booking_id,
                Payment.status == "paid",
            )
        )
    assert paid_total == Decimal("600000.00")


def test_concurrent_duplicate_payment_request_creates_one_record(
    postgres_engine: Engine,
) -> None:
    booking_id, _ = _create_payment_booking(postgres_engine)
    barrier = Barrier(2)

    def create_duplicate() -> UUID:
        with Session(postgres_engine) as session:
            payload = PaymentCreate(
                booking_id=booking_id,
                amount=Decimal("100000.00"),
                currency="VND",
                method="cash",
                status="pending",
            )
            barrier.wait(timeout=10)
            payment = create_payment(
                session,
                payload,
                None,
                "concurrent-duplicate-idempotency-key",
            )
            return payment.id

    with ThreadPoolExecutor(max_workers=2) as executor:
        payment_ids = list(executor.map(lambda _: create_duplicate(), range(2)))

    assert payment_ids[0] == payment_ids[1]
    with Session(postgres_engine) as session:
        count = session.scalar(
            select(func.count(Payment.id)).where(
                Payment.idempotency_key == "concurrent-duplicate-idempotency-key"
            )
        )
    assert count == 1


def test_concurrent_duplicate_verification_is_audited_once(
    postgres_engine: Engine,
) -> None:
    booking_id, _ = _create_payment_booking(postgres_engine)
    with Session(postgres_engine) as session:
        payment = create_payment(
            session,
            PaymentCreate(
                booking_id=booking_id,
                amount=Decimal("1000000.00"),
                currency="VND",
                method="cash",
                status="pending",
            ),
            None,
            "duplicate-verification-payment-key",
        )
        payment_id = payment.id
    barrier = Barrier(2)

    def verify_duplicate() -> str:
        with Session(postgres_engine) as session:
            barrier.wait(timeout=10)
            try:
                verify_payment(session, payment_id, None)
            except BookingError as exc:
                return exc.code
            return "VERIFIED"

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(lambda _: verify_duplicate(), range(2)))

    assert results == ["VERIFIED", "VERIFIED"]
    with Session(postgres_engine) as session:
        verification_count = session.scalar(
            select(func.count(AuditLog.id)).where(
                AuditLog.resource_id == payment_id,
                AuditLog.action == "payment.verified",
            )
        )
    assert verification_count == 1


def test_payment_verification_racing_expiration_never_reactivates_or_reallocates(
    postgres_engine: Engine,
) -> None:
    booking_id, departure_id = _create_payment_booking(postgres_engine)
    with Session(postgres_engine) as session:
        payment = create_payment(
            session,
            PaymentCreate(
                booking_id=booking_id,
                amount=Decimal("1000000.00"),
                currency="VND",
                method="cash",
                status="pending",
            ),
            None,
            "expiration-race-payment-key",
        )
        payment_id = payment.id
        booking = session.get(Booking, booking_id)
        assert booking is not None
        expires_at = booking.expires_at

    assert expires_at is not None
    barrier = Barrier(2)

    def verify() -> str:
        with Session(postgres_engine) as session:
            barrier.wait(timeout=10)
            try:
                verify_payment(session, payment_id, None)
            except BookingError as exc:
                return exc.code
            return "VERIFIED"

    def expire() -> str:
        with Session(postgres_engine) as session:
            barrier.wait(timeout=10)
            return str(
                expire_pending_bookings(
                    session,
                    now=expires_at + timedelta(minutes=1),
                )
            )

    with ThreadPoolExecutor(max_workers=2) as executor:
        verify_future = executor.submit(verify)
        expire_future = executor.submit(expire)
        verification_result = verify_future.result()
        expiration_result = expire_future.result()

    assert verification_result in {"VERIFIED", "FINANCIAL_EXCEPTION_REQUIRED"}
    assert expiration_result in {"0", "1"}
    with Session(postgres_engine) as session:
        booking = session.get(Booking, booking_id)
        payment = session.get(Payment, payment_id)
        departure = session.get(TourDeparture, departure_id)
    assert booking is not None
    assert payment is not None
    assert departure is not None
    if verification_result == "VERIFIED":
        assert booking.status == "confirmed"
        assert payment.status == "paid"
        assert departure.available_seats == 0
    else:
        assert booking.status == "expired"
        assert payment.status == "pending"
        assert departure.available_seats == 1
