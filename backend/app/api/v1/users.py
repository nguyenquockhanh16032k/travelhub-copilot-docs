from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.dependencies import require_permission
from app.core.permissions import Permission
from app.db.session import get_db
from app.models.identity import User
from app.schemas.users import (
    AssignableRoleResponse,
    UserCreate,
    UserPage,
    UserResponse,
    UserUpdate,
)
from app.services.user_service import (
    UserManagementError,
    create_user,
    get_assignable_roles,
    list_users,
    update_user,
)


router = APIRouter(prefix="/users", tags=["users"])
can_read_users = require_permission(Permission.USERS_READ)
can_manage_staff = require_permission(Permission.USERS_MANAGE_STAFF)


def user_error(exc: UserManagementError) -> HTTPException:
    status_code = status.HTTP_404_NOT_FOUND
    if exc.code in {
        "ROLE_ASSIGNMENT_FORBIDDEN",
        "SELF_ROLE_CHANGE",
        "SELF_DEACTIVATION",
        "FORBIDDEN",
    }:
        status_code = status.HTTP_403_FORBIDDEN
    elif exc.code == "EMAIL_EXISTS":
        status_code = status.HTTP_409_CONFLICT
    return HTTPException(
        status_code=status_code,
        detail={"code": exc.code, "message": exc.message},
    )


def _response(user: User) -> UserResponse:
    return UserResponse(
        id=user.id,
        email=user.email,
        is_active=user.is_active,
        roles=sorted(role.code for role in user.roles),
        created_at=user.created_at,
    )


@router.get("/roles", response_model=list[AssignableRoleResponse])
def read_assignable_roles(
    user: User = Depends(can_read_users),
) -> list[AssignableRoleResponse]:
    return [
        AssignableRoleResponse(code=code, description=description)
        for code, description in get_assignable_roles(user)
    ]


@router.get("", response_model=UserPage)
def read_users(
    page: int = Query(default=1, ge=1),
    size: int = Query(default=20, ge=1, le=100),
    search: str | None = Query(default=None, max_length=255),
    db: Session = Depends(get_db),
    actor: User = Depends(can_read_users),
) -> UserPage:
    items, total, pages = list_users(db, actor, page, size, search)
    return UserPage(
        items=[_response(user) for user in items],
        total=total,
        page=page,
        size=size,
        pages=pages,
    )


@router.post("", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def post_user(
    payload: UserCreate,
    db: Session = Depends(get_db),
    actor: User = Depends(can_manage_staff),
) -> UserResponse:
    try:
        return _response(create_user(db, actor, payload))
    except UserManagementError as exc:
        raise user_error(exc) from None


@router.patch("/{user_id}", response_model=UserResponse)
def patch_user(
    user_id: UUID,
    payload: UserUpdate,
    db: Session = Depends(get_db),
    actor: User = Depends(can_manage_staff),
) -> UserResponse:
    try:
        return _response(update_user(db, actor, user_id, payload))
    except UserManagementError as exc:
        raise user_error(exc) from None
