from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from app.api.dependencies import require_permission
from app.core.permissions import Permission
from app.db.session import get_db
from app.models.identity import User
from app.schemas.operations import (
    GuideCreate,
    GuidePage,
    GuideResponse,
    GuideUpdate,
    TourAssignmentCreate,
    TourAssignmentPage,
    TourAssignmentResponse,
    TourAssignmentUpdate,
)
from app.services.operations_service import (
    OperationsError,
    create_assignment,
    create_guide,
    delete_assignment,
    list_assignments,
    list_guides,
    update_assignment,
    update_guide,
)


router = APIRouter(tags=["operations"])
can_read_guides = require_permission(Permission.GUIDES_READ)
can_write_guides = require_permission(Permission.GUIDES_WRITE)
can_read_assignments = require_permission(Permission.ASSIGNMENTS_READ)
can_write_assignments = require_permission(Permission.ASSIGNMENTS_WRITE)


def operations_error(exc: OperationsError) -> HTTPException:
    status_code = status.HTTP_404_NOT_FOUND
    if exc.code in {"INVALID_GUIDE", "INVALID_ASSIGNMENT"}:
        status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
    return HTTPException(
        status_code=status_code,
        detail={"code": exc.code, "message": exc.message},
    )


@router.get("/guides", response_model=GuidePage)
def read_guides(
    page: int = Query(default=1, ge=1),
    size: int = Query(default=20, ge=1, le=100),
    search: str | None = Query(default=None, max_length=255),
    db: Session = Depends(get_db),
    _user: User = Depends(can_read_guides),
) -> GuidePage:
    items, total, pages = list_guides(db, page, size, search)
    return GuidePage(
        items=[GuideResponse.model_validate(item) for item in items],
        total=total,
        page=page,
        size=size,
        pages=pages,
    )


@router.post(
    "/guides",
    response_model=GuideResponse,
    status_code=status.HTTP_201_CREATED,
)
def post_guide(
    payload: GuideCreate,
    db: Session = Depends(get_db),
    _user: User = Depends(can_write_guides),
) -> GuideResponse:
    try:
        return GuideResponse.model_validate(create_guide(db, payload))
    except OperationsError as exc:
        raise operations_error(exc) from None


@router.patch("/guides/{guide_id}", response_model=GuideResponse)
def patch_guide(
    guide_id: UUID,
    payload: GuideUpdate,
    db: Session = Depends(get_db),
    _user: User = Depends(can_write_guides),
) -> GuideResponse:
    try:
        return GuideResponse.model_validate(update_guide(db, guide_id, payload))
    except OperationsError as exc:
        raise operations_error(exc) from None


@router.get(
    "/departures/{departure_id}/assignments",
    response_model=TourAssignmentPage,
)
def read_assignments(
    departure_id: UUID,
    page: int = Query(default=1, ge=1),
    size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    _user: User = Depends(can_read_assignments),
) -> TourAssignmentPage:
    try:
        items, total, pages = list_assignments(db, departure_id, page, size)
        return TourAssignmentPage(
            items=[
                TourAssignmentResponse.model_validate(item)
                for item in items
            ],
            total=total,
            page=page,
            size=size,
            pages=pages,
        )
    except OperationsError as exc:
        raise operations_error(exc) from None


@router.post(
    "/departures/{departure_id}/assignments",
    response_model=TourAssignmentResponse,
    status_code=status.HTTP_201_CREATED,
)
def post_assignment(
    departure_id: UUID,
    payload: TourAssignmentCreate,
    db: Session = Depends(get_db),
    _user: User = Depends(can_write_assignments),
) -> TourAssignmentResponse:
    try:
        assignment = create_assignment(db, departure_id, payload)
        return TourAssignmentResponse.model_validate(assignment)
    except OperationsError as exc:
        raise operations_error(exc) from None


@router.patch(
    "/departures/{departure_id}/assignments/{assignment_id}",
    response_model=TourAssignmentResponse,
)
def patch_assignment(
    departure_id: UUID,
    assignment_id: UUID,
    payload: TourAssignmentUpdate,
    db: Session = Depends(get_db),
    _user: User = Depends(can_write_assignments),
) -> TourAssignmentResponse:
    try:
        assignment = update_assignment(
            db,
            departure_id,
            assignment_id,
            payload,
        )
        return TourAssignmentResponse.model_validate(assignment)
    except OperationsError as exc:
        raise operations_error(exc) from None


@router.delete(
    "/departures/{departure_id}/assignments/{assignment_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def remove_assignment(
    departure_id: UUID,
    assignment_id: UUID,
    db: Session = Depends(get_db),
    _user: User = Depends(can_write_assignments),
) -> Response:
    try:
        delete_assignment(db, departure_id, assignment_id)
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    except OperationsError as exc:
        raise operations_error(exc) from None
