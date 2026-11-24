import os
import uuid
from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import select
from passlib.context import CryptContext

from app.db.base import Base
from app.db.session import engine, SessionLocal
from app.models import Customer, Role, Tour, TourDeparture, User


password_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def seed() -> None:
    if os.getenv("ENVIRONMENT", "development").lower() == "production":
        raise RuntimeError("Development seed data cannot be loaded in production")

    Base.metadata.create_all(bind=engine)

    super_admin_email = os.getenv("SEED_SUPER_ADMIN_EMAIL")
    super_admin_password = os.getenv("SEED_SUPER_ADMIN_PASSWORD")
    if not super_admin_email or not super_admin_password:
        raise RuntimeError(
            "Set SEED_SUPER_ADMIN_EMAIL and SEED_SUPER_ADMIN_PASSWORD before seeding"
        )

    with SessionLocal() as session:
        super_admin_role = session.scalar(
            select(Role).where(Role.code == "SUPER_ADMIN")
        )
        if super_admin_role is None:
            super_admin_role = Role(
                id=uuid.uuid4(),
                code="SUPER_ADMIN",
                description="Full system administration",
            )
            session.add(super_admin_role)

        super_admin = session.scalar(
            select(User).where(User.email == super_admin_email)
        )
        if super_admin is None:
            super_admin = User(
                id=uuid.uuid4(),
                email=super_admin_email,
                password_hash=password_context.hash(super_admin_password),
                is_active=True,
            )
            super_admin.roles.append(super_admin_role)
            session.add(super_admin)

        tour = session.scalar(select(Tour).where(Tour.slug == "da-lat-3-days"))
        if tour is None:
            tour = Tour(
                id=uuid.uuid4(),
                title="Da Lat - 3 days 2 nights",
                slug="da-lat-3-days",
                description="A sample development tour.",
                duration_days=3,
                destination="Da Lat",
                status="published",
            )
            session.add(tour)
            session.flush()

            departure = TourDeparture(
                id=uuid.uuid4(),
                tour_id=tour.id,
                start_date=date.today() + timedelta(days=30),
                end_date=date.today() + timedelta(days=32),
                capacity=20,
                available_seats=20,
                price=Decimal("3500000.00"),
                currency="VND",
                status="open",
            )
            session.add(departure)

        if session.scalar(select(Customer).where(Customer.email == "guest@example.com")) is None:
            session.add(
                Customer(
                    id=uuid.uuid4(),
                    full_name="Sample Guest",
                    email="guest@example.com",
                    phone="+84 000 000 000",
                    address="Da Lat, Vietnam",
                )
            )

        session.commit()


if __name__ == "__main__":
    seed()
