import math
from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.models.identity import User
from app.models.operations import Guide, TourAssignment
from app.models.tour import TourDeparture
from app.schemas.operations import (
    GuideCreate,
    GuideUpdate,
    TourAssignmentCreate,
    TourAssignmentUpdate,
)


class OperationsError(Exception):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


def list_guides(
    db: Session,
    page: int,
    size: int,
    search: str | None,
) -> tuple[list[Guide], int, int]:
    query = select(Guide)
    count_query = select(func.count(Guide.id))
    if search:
        pattern = f"%{search.strip()}%"
        filter_clause = or_(
            Guide.full_name.ilike(pattern),
            Guide.email.ilike(pattern),
            Guide.phone.ilike(pattern),
        )
        query = query.where(filter_clause)
        count_query = count_query.where(filter_clause)
    query = query.order_by(Guide.full_name, Guide.id)
    query = query.offset((page - 1) * size).limit(size)
    items = list(db.scalars(query))
    total = int(db.scalar(count_query) or 0)
    return items, total, math.ceil(total / size) if total else 0


def create_guide(db: Session, payload: GuideCreate) -> Guide:
    _validate_user(db, payload.user_id)
    guide = Guide(**payload.model_dump())
    db.add(guide)
    db.commit()
    db.refresh(guide)
    return guide


def update_guide(db: Session, guide_id: UUID, payload: GuideUpdate) -> Guide:
    guide = db.get(Guide, guide_id)
    if guide is None:
        raise OperationsError("GUIDE_NOT_FOUND", "Guide not found")

    values = payload.model_dump(exclude_unset=True)
    if "full_name" in values and values["full_name"] is None:
        raise OperationsError("INVALID_GUIDE", "full_name cannot be null")
    if "user_id" in values:
        _validate_user(db, values["user_id"])

    for field, value in values.items():
        setattr(guide, field, value)
    db.commit()
    db.refresh(guide)
    return guide


def _validate_user(db: Session, user_id: UUID | None) -> None:
    if user_id is not None and db.get(User, user_id) is None:
        raise OperationsError("USER_NOT_FOUND", "Linked user not found")


def list_assignments(
    db: Session,
    departure_id: UUID,
    page: int,
    size: int,
) -> tuple[list[TourAssignment], int, int]:
    _require_departure(db, departure_id)
    query = (
        select(TourAssignment)
        .where(TourAssignment.departure_id == departure_id)
        .options(selectinload(TourAssignment.guide))
        .order_by(TourAssignment.created_at, TourAssignment.id)
    )
    count_query = select(func.count(TourAssignment.id)).where(
        TourAssignment.departure_id == departure_id
    )
    items = list(db.scalars(query.offset((page - 1) * size).limit(size)))
    total = int(db.scalar(count_query) or 0)
    return items, total, math.ceil(total / size) if total else 0


def create_assignment(
    db: Session,
    departure_id: UUID,
    payload: TourAssignmentCreate,
) -> TourAssignment:
    _require_departure(db, departure_id)
    _require_guide(db, payload.guide_id)
    assignment = TourAssignment(
        departure_id=departure_id,
        **payload.model_dump(),
    )
    db.add(assignment)
    db.commit()
    return _load_assignment(db, departure_id, assignment.id)


def update_assignment(
    db: Session,
    departure_id: UUID,
    assignment_id: UUID,
    payload: TourAssignmentUpdate,
) -> TourAssignment:
    assignment = _get_assignment(db, departure_id, assignment_id)
    values = payload.model_dump(exclude_unset=True)
    for required_field in ("guide_id", "role", "status"):
        if required_field in values and values[required_field] is None:
            raise OperationsError(
                "INVALID_ASSIGNMENT",
                f"{required_field} cannot be null",
            )
    if "guide_id" in values:
        _require_guide(db, values["guide_id"])
    for field, value in values.items():
        setattr(assignment, field, value)
    db.commit()
    return _load_assignment(db, departure_id, assignment_id)


def delete_assignment(
    db: Session,
    departure_id: UUID,
    assignment_id: UUID,
) -> None:
    assignment = _get_assignment(db, departure_id, assignment_id)
    db.delete(assignment)
    db.commit()


def _require_departure(db: Session, departure_id: UUID) -> None:
    if db.get(TourDeparture, departure_id) is None:
        raise OperationsError("DEPARTURE_NOT_FOUND", "Departure not found")


def _require_guide(db: Session, guide_id: UUID) -> None:
    if db.get(Guide, guide_id) is None:
        raise OperationsError("GUIDE_NOT_FOUND", "Guide not found")


def _get_assignment(
    db: Session,
    departure_id: UUID,
    assignment_id: UUID,
) -> TourAssignment:
    assignment = db.scalar(
        select(TourAssignment).where(
            TourAssignment.id == assignment_id,
            TourAssignment.departure_id == departure_id,
        )
    )
    if assignment is None:
        raise OperationsError("ASSIGNMENT_NOT_FOUND", "Assignment not found")
    return assignment


def _load_assignment(
    db: Session,
    departure_id: UUID,
    assignment_id: UUID,
) -> TourAssignment:
    assignment = db.scalar(
        select(TourAssignment)
        .where(
            TourAssignment.id == assignment_id,
            TourAssignment.departure_id == departure_id,
        )
        .options(selectinload(TourAssignment.guide))
    )
    if assignment is None:
        raise OperationsError("ASSIGNMENT_NOT_FOUND", "Assignment not found")
    return assignment
