from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.db.base import Base
from app.models.booking import Booking
from app.models.tour import Tour, TourDeparture
from app.schemas.booking import (
    BookingCreate,
    BookingResponse,
    PaymentCreate,
    TravelerInput,
)
from app.services.booking_service import (
    BookingError,
    change_booking_status,
    create_booking,
    create_payment,
    expire_pending_bookings,
)


@pytest.fixture
def booking_context():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        tour = Tour(
            title="Final Seat Tour",
            slug="final-seat-tour",
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
        yield session, departure.id
    engine.dispose()


def traveler_payload(departure_id):
    return BookingCreate(
        departure_id=departure_id,
        contact_name="Guest",
        contact_email="guest@example.com",
        contact_phone="0900000000",
        travelers=[
            TravelerInput(full_name="Guest One", traveler_type="adult")
        ],
    )


def test_competing_booking_for_final_seat(booking_context) -> None:
    session, departure_id = booking_context
    first = create_booking(session, traveler_payload(departure_id))
    assert first.passenger_count == 1

    with pytest.raises(BookingError) as exc:
        create_booking(session, traveler_payload(departure_id))
    assert exc.value.code == "NOT_ENOUGH_SEATS"


def test_past_departure_cannot_be_booked(booking_context) -> None:
    session, departure_id = booking_context
    departure = session.get(TourDeparture, departure_id)
    assert departure is not None
    departure.start_date = date.today() - timedelta(days=1)
    session.commit()

    with pytest.raises(BookingError) as exc:
        create_booking(session, traveler_payload(departure_id))

    assert exc.value.code == "DEPARTURE_NOT_BOOKABLE"
    assert departure.available_seats == 1


def test_cancel_releases_seats_and_records_history(booking_context) -> None:
    session, departure_id = booking_context
    booking = create_booking(session, traveler_payload(departure_id))

    updated = change_booking_status(
        session,
        booking.id,
        "cancelled",
        uuid4(),
        "Customer requested cancellation",
    )

    assert updated.status == "cancelled"
    departure = session.get(TourDeparture, departure_id)
    assert departure.available_seats == 1
    assert len(updated.status_history) == 2
    response = BookingResponse.model_validate(updated)
    assert {item.new_status for item in response.status_history} == {
        "pending",
        "cancelled",
    }


def test_payment_is_separate_record(booking_context) -> None:
    session, departure_id = booking_context
    booking = create_booking(session, traveler_payload(departure_id))

    payment = create_payment(
        session,
        PaymentCreate(
            booking_id=booking.id,
            amount=Decimal("500000.00"),
            currency="VND",
            method="bank_transfer",
            status="paid",
            transaction_reference="TX-001",
        ),
        uuid4(),
        "service-payment-001",
    )

    assert payment.booking_id == booking.id
    assert payment.amount == Decimal("500000.00")
    session.refresh(booking)
    assert booking.status == "pending"


def test_pending_booking_expires_and_releases_seat_once(booking_context) -> None:
    session, departure_id = booking_context
    booking = create_booking(session, traveler_payload(departure_id))
    booking.expires_at = datetime.now(timezone.utc) - timedelta(minutes=1)
    session.commit()

    assert expire_pending_bookings(session) == 1
    assert expire_pending_bookings(session) == 0

    session.refresh(booking)
    departure = session.get(TourDeparture, departure_id)
    assert booking.status == "expired"
    assert booking.expires_at is None
    assert departure is not None
    assert departure.available_seats == 1
    assert len(booking.status_history) == 2


def test_rejected_booking_releases_seats(booking_context) -> None:
    session, departure_id = booking_context
    booking = create_booking(session, traveler_payload(departure_id))

    updated = change_booking_status(
        session,
        booking.id,
        "rejected",
        uuid4(),
        "Booking rejected",
    )

    assert updated.status == "rejected"
    departure = session.get(TourDeparture, departure_id)
    assert departure is not None
    assert departure.available_seats == 1


def test_paid_payment_confirms_pending_booking(booking_context) -> None:
    session, departure_id = booking_context
    booking = create_booking(session, traveler_payload(departure_id))

    create_payment(
        session,
        PaymentCreate(
            booking_id=booking.id,
            amount=Decimal("1000000.00"),
            currency="VND",
            method="cash",
            status="paid",
        ),
        uuid4(),
        "service-payment-002",
    )

    session.refresh(booking)
    assert booking.status == "confirmed"
    assert booking.expires_at is None
    assert len(booking.status_history) == 2


def test_paid_payment_after_expiration_is_rejected(booking_context) -> None:
    session, departure_id = booking_context
    booking = create_booking(session, traveler_payload(departure_id))
    booking.expires_at = datetime.now(timezone.utc) - timedelta(minutes=1)
    session.commit()
    expire_pending_bookings(session)

    with pytest.raises(BookingError) as exc:
        create_payment(
            session,
            PaymentCreate(
                booking_id=booking.id,
                amount=Decimal("500000.00"),
                currency="VND",
                method="cash",
                status="paid",
            ),
            uuid4(),
            "service-payment-003",
        )

    assert exc.value.code == "FINANCIAL_EXCEPTION_REQUIRED"
