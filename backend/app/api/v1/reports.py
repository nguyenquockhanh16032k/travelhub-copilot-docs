from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.dependencies import require_permission
from app.core.permissions import Permission
from app.db.session import get_db
from app.models.identity import User
from app.schemas.reports import ExpenseReportPage
from app.services.report_service import get_expense_report


router = APIRouter(prefix="/reports", tags=["reports"])
can_read_reports = require_permission(Permission.REPORTS_READ)


@router.get("/expenses", response_model=ExpenseReportPage)
def read_expense_report(
    page: int = Query(default=1, ge=1),
    size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    _user: User = Depends(can_read_reports),
) -> ExpenseReportPage:
    items, total, pages = get_expense_report(db, page, size)
    return ExpenseReportPage(
        items=items,
        total=total,
        page=page,
        size=size,
        pages=pages,
    )
