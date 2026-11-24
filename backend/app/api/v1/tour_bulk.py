"""Admin tour bulk CSV/XLSX import and export endpoints."""
from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.api.dependencies import require_permission
from app.core.permissions import Permission
from app.db.session import get_db
from app.models.identity import User
from app.services.tour_bulk_service import BulkTourError, export_tours, import_tours

router = APIRouter(prefix="/admin/tours/bulk", tags=["tour bulk"])
can_read = require_permission(Permission.TOURS_READ)
can_write = require_permission(Permission.TOURS_WRITE)


@router.get("/export")
def download_tours(
    format: str = Query(default="xlsx", pattern="^(csv|xlsx)$"),
    template: bool = False,
    db: Session = Depends(get_db),
    _user: User = Depends(can_read),
) -> Response:
    try:
        content, media_type = export_tours(db, format, template)
    except BulkTourError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from None
    file_name = f"travelhub_tours_{'template' if template else 'export'}.{format}"
    return Response(
        content=content, media_type=media_type,
        headers={
            "Content-Disposition": f'attachment; filename="{file_name}"',
            "Cache-Control": "no-store",
            "X-Content-Type-Options": "nosniff",
        },
    )


@router.post("/import")
async def upload_tours(
    file: UploadFile = File(...),
    preview: bool = Query(default=True),
    db: Session = Depends(get_db),
    user: User = Depends(can_write),
) -> dict:
    try:
        # Read no more than the permitted input size plus one byte.
        raw = await file.read(2 * 1024 * 1024 + 1)
        return import_tours(db, raw, file.filename or "", user.id, preview)
    except BulkTourError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from None
    finally:
        await file.close()
