import math

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.operations import TourExpense
from app.models.tour import Tour, TourDeparture
from app.schemas.reports import ExpenseReportRow


def get_expense_report(
    db: Session,
    page: int,
    size: int,
) -> tuple[list[ExpenseReportRow], int, int]:
    grouped = (
        select(
            TourExpense.departure_id.label("departure_id"),
            Tour.title.label("tour_title"),
            TourDeparture.start_date.label("departure_start_date"),
            TourExpense.category.label("category"),
            TourExpense.currency.label("currency"),
            TourExpense.status.label("status"),
            func.sum(TourExpense.amount).label("total_amount"),
            func.count(TourExpense.id).label("expense_count"),
        )
        .join(TourDeparture, TourDeparture.id == TourExpense.departure_id)
        .join(Tour, Tour.id == TourDeparture.tour_id)
        .group_by(
            TourExpense.departure_id,
            Tour.title,
            TourDeparture.start_date,
            TourExpense.category,
            TourExpense.currency,
            TourExpense.status,
        )
        .subquery()
    )
    query = (
        select(grouped)
        .order_by(
            grouped.c.departure_start_date,
            grouped.c.tour_title,
            grouped.c.category,
            grouped.c.currency,
            grouped.c.status,
        )
        .offset((page - 1) * size)
        .limit(size)
    )
    rows = db.execute(query)
    items = [
        ExpenseReportRow.model_validate(dict(row._mapping))
        for row in rows
    ]
    total = int(db.scalar(select(func.count()).select_from(grouped)) or 0)
    pages = math.ceil(total / size) if total else 0
    return items, total, pages
