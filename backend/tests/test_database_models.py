from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.base import Base
from app.models import Customer, Role, Tour, TourDeparture, User


@pytest.fixture
def db_session():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session
    engine.dispose()


def test_tour_and_departure_relationship(db_session: Session) -> None:
    tour = Tour(
        title="Da Lat - 3 days",
        slug="da-lat-3-days",
        duration_days=3,
        destination="Da Lat",
        status="published",
    )
    departure = TourDeparture(
        start_date=date(2026, 12, 1),
        end_date=date(2026, 12, 3),
        capacity=20,
        available_seats=20,
        price=Decimal("3500000.00"),
        currency="VND",
        status="open",
    )
    tour.departures.append(departure)
    db_session.add(tour)
    db_session.commit()

    loaded = db_session.scalar(select(Tour).where(Tour.slug == "da-lat-3-days"))
    assert loaded is not None
    assert loaded.departures == [departure]


def test_departure_rejects_available_seats_above_capacity(
    db_session: Session,
) -> None:
    tour = Tour(
        title="Invalid departure",
        slug="invalid-departure",
        duration_days=1,
        destination="Nha Trang",
        status="draft",
    )
    db_session.add(tour)
    db_session.flush()

    db_session.add(
        TourDeparture(
            tour_id=tour.id,
            start_date=date(2026, 12, 1),
            end_date=date(2026, 12, 2),
            capacity=10,
            available_seats=11,
            price=Decimal("1000000.00"),
            currency="VND",
            status="open",
        )
    )

    with pytest.raises(IntegrityError):
        db_session.commit()


def test_role_is_unique_and_customer_email_is_unique(db_session: Session) -> None:
    db_session.add(Role(code="STAFF", description="Operations staff"))
    db_session.add(
        Customer(full_name="Guest One", email="guest@example.com")
    )
    db_session.commit()

    db_session.add(Role(code="STAFF", description="Duplicate"))
    with pytest.raises(IntegrityError):
        db_session.commit()
