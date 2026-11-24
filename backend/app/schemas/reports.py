from datetime import date
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel


class ExpenseReportRow(BaseModel):
    departure_id: UUID
    tour_title: str
    departure_start_date: date
    category: str
    currency: str
    status: str
    total_amount: Decimal
    expense_count: int


class ExpenseReportPage(BaseModel):
    items: list[ExpenseReportRow]
    total: int
    page: int
    size: int
    pages: int
