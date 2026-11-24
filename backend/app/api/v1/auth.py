from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.db.session import get_db
from app.models.identity import User
from app.schemas.auth import (
    LoginRequest,
    LogoutRequest,
    RefreshRequest,
    TokenResponse,
    UserResponse,
)
from app.services.auth_service import (
    AuthenticationError,
    authenticate,
    refresh_tokens,
    revoke_refresh_token,
)


router = APIRouter(prefix="/auth", tags=["auth"])


def _auth_error(message: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail={"code": "AUTHENTICATION_FAILED", "message": message},
    )


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> TokenResponse:
    try:
        return authenticate(db, payload.email, payload.password)
    except AuthenticationError as exc:
        raise _auth_error(str(exc)) from None


@router.post("/refresh", response_model=TokenResponse)
def refresh(payload: RefreshRequest, db: Session = Depends(get_db)) -> TokenResponse:
    try:
        return refresh_tokens(db, payload.refresh_token)
    except AuthenticationError as exc:
        raise _auth_error(str(exc)) from None


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(payload: LogoutRequest, db: Session = Depends(get_db)) -> None:
    try:
        revoke_refresh_token(db, payload.refresh_token)
    except AuthenticationError as exc:
        raise _auth_error(str(exc)) from None


@router.get("/me", response_model=UserResponse)
def me(user: User = Depends(get_current_user)) -> dict[str, object]:
    return {
        "id": user.id,
        "email": user.email,
        "is_active": user.is_active,
        "roles": [role.code for role in user.roles],
    }
