from decimal import Decimal
from typing import Any

from sqlalchemy import case, func, select
from sqlalchemy.engine import Result, Row
from sqlalchemy.orm import Session

from app.core.business_time import business_date
from app.models.booking import Booking, Payment
from app.models.tour import Tour, TourDeparture
from app.schemas.dashboard import (
    DashboardSummary,
    OperationalDashboardSummary,
    OperationalDepartureSummary,
    PaymentCurrencySummary,
    UpcomingDepartureSummary,
)


def get_dashboard_summary(db: Session) -> DashboardSummary:
    booking_count, pending_booking_count, departure_rows = _get_operational_data(db)
    upcoming_departures = [
        UpcomingDepartureSummary(
            id=row.id,
            tour_title=row.title,
            start_date=row.start_date,
            end_date=row.end_date,
            available_seats=row.available_seats,
            price=row.price,
            currency=row.currency,
        )
        for row in departure_rows
    ]

    paid_amount = func.sum(
        case((Payment.status == "paid", Payment.amount), else_=Decimal("0.00"))
    )
    pending_amount = func.sum(
        case((Payment.status == "pending", Payment.amount), else_=Decimal("0.00"))
    )
    payment_rows = db.execute(
        select(Payment.currency, paid_amount, pending_amount)
        .where(Payment.status.in_(("paid", "pending")))
        .group_by(Payment.currency)
        .order_by(Payment.currency.asc())
    )
    payments_by_currency = [
        PaymentCurrencySummary(
            currency=row.currency,
            paid_amount=row[1] or Decimal("0.00"),
            pending_amount=row[2] or Decimal("0.00"),
        )
        for row in payment_rows
    ]

    return DashboardSummary(
        booking_count=booking_count,
        pending_booking_count=pending_booking_count,
        upcoming_departures=upcoming_departures,
        payments_by_currency=payments_by_currency,
    )


def get_operational_dashboard_summary(
    db: Session,
) -> OperationalDashboardSummary:
    booking_count, pending_booking_count, departure_rows = _get_operational_data(
        db,
        include_prices=False,
    )
    return OperationalDashboardSummary(
        booking_count=booking_count,
        pending_booking_count=pending_booking_count,
        upcoming_departures=[
            OperationalDepartureSummary(
                id=row.id,
                tour_title=row.title,
                start_date=row.start_date,
                end_date=row.end_date,
                available_seats=row.available_seats,
            )
            for row in departure_rows
        ],
    )


def _get_operational_data(
    db: Session,
    *,
    include_prices: bool = True,
) -> tuple[int, int, Result[Row[Any]]]:
    booking_count = int(db.scalar(select(func.count(Booking.id))) or 0)
    pending_booking_count = int(
        db.scalar(
            select(func.count(Booking.id)).where(Booking.status == "pending")
        )
        or 0
    )
    departure_columns = [
        TourDeparture.id,
        Tour.title,
        TourDeparture.start_date,
        TourDeparture.end_date,
        TourDeparture.available_seats,
    ]
    if include_prices:
        departure_columns.extend([TourDeparture.price, TourDeparture.currency])
    departure_rows = db.execute(
        select(*departure_columns)
        .join(Tour, Tour.id == TourDeparture.tour_id)
        .where(
            Tour.status == "published",
            TourDeparture.status == "open",
            TourDeparture.start_date >= business_date(),
        )
        .order_by(TourDeparture.start_date.asc())
        .limit(5)
    )
    return booking_count, pending_booking_count, departure_rows
