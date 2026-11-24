from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.dependencies import require_permission
from app.core.permissions import Permission
from app.db.session import get_db
from app.models.identity import User
from app.schemas.supplier_expense import (
    SupplierCreate,
    SupplierPage,
    SupplierResponse,
    SupplierUpdate,
    TourExpenseCreate,
    TourExpensePage,
    TourExpenseResponse,
    TourExpenseUpdate,
)
from app.services.supplier_expense_service import (
    SupplierExpenseError,
    create_expense,
    create_supplier,
    list_expenses,
    list_suppliers,
    update_expense,
    update_supplier,
)


router = APIRouter(tags=["suppliers and expenses"])
can_read_suppliers = require_permission(Permission.SUPPLIERS_READ)
can_write_suppliers = require_permission(Permission.SUPPLIERS_WRITE)
can_read_expenses = require_permission(Permission.EXPENSES_READ)
can_write_expenses = require_permission(Permission.EXPENSES_WRITE)


def supplier_expense_error(exc: SupplierExpenseError) -> HTTPException:
    status_code = status.HTTP_404_NOT_FOUND
    if exc.code in {"INVALID_SUPPLIER", "INVALID_EXPENSE"}:
        status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
    return HTTPException(
        status_code=status_code,
        detail={"code": exc.code, "message": exc.message},
    )


@router.get("/suppliers", response_model=SupplierPage)
def read_suppliers(
    page: int = Query(default=1, ge=1),
    size: int = Query(default=20, ge=1, le=100),
    search: str | None = Query(default=None, max_length=255),
    db: Session = Depends(get_db),
    _user: User = Depends(can_read_suppliers),
) -> SupplierPage:
    items, total, pages = list_suppliers(db, page, size, search)
    return SupplierPage(
        items=[SupplierResponse.model_validate(item) for item in items],
        total=total,
        page=page,
        size=size,
        pages=pages,
    )


@router.post(
    "/suppliers",
    response_model=SupplierResponse,
    status_code=status.HTTP_201_CREATED,
)
def post_supplier(
    payload: SupplierCreate,
    db: Session = Depends(get_db),
    _user: User = Depends(can_write_suppliers),
) -> SupplierResponse:
    return SupplierResponse.model_validate(create_supplier(db, payload))


@router.patch("/suppliers/{supplier_id}", response_model=SupplierResponse)
def patch_supplier(
    supplier_id: UUID,
    payload: SupplierUpdate,
    db: Session = Depends(get_db),
    _user: User = Depends(can_write_suppliers),
) -> SupplierResponse:
    try:
        return SupplierResponse.model_validate(
            update_supplier(db, supplier_id, payload)
        )
    except SupplierExpenseError as exc:
        raise supplier_expense_error(exc) from None


@router.get(
    "/departures/{departure_id}/expenses",
    response_model=TourExpensePage,
)
def read_expenses(
    departure_id: UUID,
    page: int = Query(default=1, ge=1),
    size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    _user: User = Depends(can_read_expenses),
) -> TourExpensePage:
    try:
        items, total, pages = list_expenses(db, departure_id, page, size)
        return TourExpensePage(
            items=[
                TourExpenseResponse.model_validate(item)
                for item in items
            ],
            total=total,
            page=page,
            size=size,
            pages=pages,
        )
    except SupplierExpenseError as exc:
        raise supplier_expense_error(exc) from None


@router.post(
    "/departures/{departure_id}/expenses",
    response_model=TourExpenseResponse,
    status_code=status.HTTP_201_CREATED,
)
def post_expense(
    departure_id: UUID,
    payload: TourExpenseCreate,
    db: Session = Depends(get_db),
    _user: User = Depends(can_write_expenses),
) -> TourExpenseResponse:
    try:
        return TourExpenseResponse.model_validate(
            create_expense(db, departure_id, payload)
        )
    except SupplierExpenseError as exc:
        raise supplier_expense_error(exc) from None


@router.patch(
    "/departures/{departure_id}/expenses/{expense_id}",
    response_model=TourExpenseResponse,
)
def patch_expense(
    departure_id: UUID,
    expense_id: UUID,
    payload: TourExpenseUpdate,
    db: Session = Depends(get_db),
    _user: User = Depends(can_write_expenses),
) -> TourExpenseResponse:
    try:
        return TourExpenseResponse.model_validate(
            update_expense(db, departure_id, expense_id, payload)
        )
    except SupplierExpenseError as exc:
        raise supplier_expense_error(exc) from None
