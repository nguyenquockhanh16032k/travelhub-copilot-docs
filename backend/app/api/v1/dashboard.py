from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.dependencies import require_permission
from app.core.permissions import Permission, has_permission
from app.db.session import get_db
from app.models.identity import User
from app.schemas.dashboard import DashboardSummary, OperationalDashboardSummary
from app.services.dashboard_service import (
    get_dashboard_summary,
    get_operational_dashboard_summary,
)


router = APIRouter(tags=["dashboard"])
can_read_dashboard = require_permission(Permission.DASHBOARD_READ)


@router.get(
    "/dashboard/summary",
    response_model=DashboardSummary | OperationalDashboardSummary,
)
def read_dashboard_summary(
    db: Session = Depends(get_db),
    user: User = Depends(can_read_dashboard),
) -> DashboardSummary | OperationalDashboardSummary:
    if has_permission(user, Permission.PAYMENTS_READ):
        return get_dashboard_summary(db)
    return get_operational_dashboard_summary(db)
