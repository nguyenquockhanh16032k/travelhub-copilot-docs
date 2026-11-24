import math
from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.models.operations import Supplier, TourExpense
from app.models.tour import TourDeparture
from app.schemas.supplier_expense import (
    SupplierCreate,
    SupplierUpdate,
    TourExpenseCreate,
    TourExpenseUpdate,
)


class SupplierExpenseError(Exception):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


def list_suppliers(
    db: Session,
    page: int,
    size: int,
    search: str | None,
) -> tuple[list[Supplier], int, int]:
    query = select(Supplier)
    count_query = select(func.count(Supplier.id))
    if search:
        pattern = f"%{search.strip()}%"
        filter_clause = or_(
            Supplier.name.ilike(pattern),
            Supplier.service_category.ilike(pattern),
        )
        query = query.where(filter_clause)
        count_query = count_query.where(filter_clause)
    query = query.order_by(Supplier.name, Supplier.id)
    items = list(db.scalars(query.offset((page - 1) * size).limit(size)))
    total = int(db.scalar(count_query) or 0)
    return items, total, math.ceil(total / size) if total else 0


def create_supplier(db: Session, payload: SupplierCreate) -> Supplier:
    supplier = Supplier(**payload.model_dump())
    db.add(supplier)
    db.commit()
    db.refresh(supplier)
    return supplier


def update_supplier(
    db: Session,
    supplier_id: UUID,
    payload: SupplierUpdate,
) -> Supplier:
    supplier = db.get(Supplier, supplier_id)
    if supplier is None:
        raise SupplierExpenseError("SUPPLIER_NOT_FOUND", "Supplier not found")
    values = payload.model_dump(exclude_unset=True)
    for required_field in ("name", "service_category"):
        if required_field in values and values[required_field] is None:
            raise SupplierExpenseError(
                "INVALID_SUPPLIER",
                f"{required_field} cannot be null",
            )
    for field, value in values.items():
        setattr(supplier, field, value)
    db.commit()
    db.refresh(supplier)
    return supplier


def list_expenses(
    db: Session,
    departure_id: UUID,
    page: int,
    size: int,
) -> tuple[list[TourExpense], int, int]:
    _require_departure(db, departure_id)
    query = (
        select(TourExpense)
        .where(TourExpense.departure_id == departure_id)
        .options(selectinload(TourExpense.supplier))
        .order_by(TourExpense.created_at.desc(), TourExpense.id)
    )
    count_query = select(func.count(TourExpense.id)).where(
        TourExpense.departure_id == departure_id
    )
    items = list(db.scalars(query.offset((page - 1) * size).limit(size)))
    total = int(db.scalar(count_query) or 0)
    return items, total, math.ceil(total / size) if total else 0


def create_expense(
    db: Session,
    departure_id: UUID,
    payload: TourExpenseCreate,
) -> TourExpense:
    _require_departure(db, departure_id)
    _validate_supplier(db, payload.supplier_id)
    expense = TourExpense(
        departure_id=departure_id,
        **payload.model_dump(),
    )
    db.add(expense)
    db.commit()
    return _load_expense(db, departure_id, expense.id)


def update_expense(
    db: Session,
    departure_id: UUID,
    expense_id: UUID,
    payload: TourExpenseUpdate,
) -> TourExpense:
    expense = _get_expense(db, departure_id, expense_id)
    values = payload.model_dump(exclude_unset=True)
    for required_field in ("category", "amount", "currency", "status"):
        if required_field in values and values[required_field] is None:
            raise SupplierExpenseError(
                "INVALID_EXPENSE",
                f"{required_field} cannot be null",
            )
    if "supplier_id" in values:
        _validate_supplier(db, values["supplier_id"])
    for field, value in values.items():
        setattr(expense, field, value)
    db.commit()
    return _load_expense(db, departure_id, expense_id)


def _require_departure(db: Session, departure_id: UUID) -> None:
    if db.get(TourDeparture, departure_id) is None:
        raise SupplierExpenseError("DEPARTURE_NOT_FOUND", "Departure not found")


def _validate_supplier(db: Session, supplier_id: UUID | None) -> None:
    if supplier_id is not None and db.get(Supplier, supplier_id) is None:
        raise SupplierExpenseError("SUPPLIER_NOT_FOUND", "Supplier not found")


def _get_expense(
    db: Session,
    departure_id: UUID,
    expense_id: UUID,
) -> TourExpense:
    expense = db.scalar(
        select(TourExpense).where(
            TourExpense.id == expense_id,
            TourExpense.departure_id == departure_id,
        )
    )
    if expense is None:
        raise SupplierExpenseError("EXPENSE_NOT_FOUND", "Expense not found")
    return expense


def _load_expense(
    db: Session,
    departure_id: UUID,
    expense_id: UUID,
) -> TourExpense:
    expense = db.scalar(
        select(TourExpense)
        .where(
            TourExpense.id == expense_id,
            TourExpense.departure_id == departure_id,
        )
        .options(selectinload(TourExpense.supplier))
    )
    if expense is None:
        raise SupplierExpenseError("EXPENSE_NOT_FOUND", "Expense not found")
    return expense
