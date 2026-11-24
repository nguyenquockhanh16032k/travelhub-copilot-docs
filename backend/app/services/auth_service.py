from datetime import datetime, timezone
from uuid import UUID

from jose import JWTError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    verify_password,
)
from app.models.identity import RefreshToken, User
from app.schemas.auth import TokenResponse


class AuthenticationError(Exception):
    pass


def _issue_token_pair(db: Session, user: User) -> tuple[TokenResponse, str]:
    access_token = create_access_token(str(user.id))
    refresh_token, jti, expires_at = create_refresh_token(str(user.id))
    db.add(
        RefreshToken(
            user_id=user.id,
            jti=jti,
            expires_at=expires_at,
        )
    )
    db.commit()
    return (
        TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
        ),
        jti,
    )


def authenticate(db: Session, email: str, password: str) -> TokenResponse:
    user = db.scalar(select(User).where(User.email == email.lower()))
    if user is None or not user.is_active:
        raise AuthenticationError("Invalid email or password")
    if not verify_password(password, user.password_hash):
        raise AuthenticationError("Invalid email or password")

    tokens, _ = _issue_token_pair(db, user)
    return tokens


def refresh_tokens(db: Session, refresh_token: str) -> TokenResponse:
    try:
        payload = decode_token(refresh_token)
    except JWTError:
        raise AuthenticationError("Refresh token is invalid or expired") from None

    if payload.get("type") != "refresh":
        raise AuthenticationError("A refresh token is required")

    jti = payload.get("jti")
    subject = payload.get("sub")
    if not isinstance(jti, str) or not isinstance(subject, str):
        raise AuthenticationError("Refresh token is invalid")

    try:
        user_id = UUID(subject)
    except ValueError:
        raise AuthenticationError("Refresh token is invalid") from None

    stored = db.scalar(
        select(RefreshToken).where(
            RefreshToken.jti == jti,
            RefreshToken.user_id == user_id,
        ).with_for_update()
    )
    if stored is None or stored.revoked_at is not None:
        raise AuthenticationError("Refresh token has been revoked")

    expires_at = stored.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at <= datetime.now(timezone.utc):
        raise AuthenticationError("Refresh token is invalid or expired")

    user = db.get(User, user_id)
    if user is None or not user.is_active:
        raise AuthenticationError("User account is unavailable")

    stored.revoked_at = datetime.now(timezone.utc)
    db.flush()
    tokens, _ = _issue_token_pair(db, user)
    return tokens


def revoke_refresh_token(db: Session, refresh_token: str) -> None:
    try:
        payload = decode_token(refresh_token)
    except JWTError:
        raise AuthenticationError("Refresh token is invalid or expired") from None

    if payload.get("type") != "refresh":
        raise AuthenticationError("A refresh token is required")

    jti = payload.get("jti")
    if not isinstance(jti, str):
        raise AuthenticationError("Refresh token is invalid")

    stored = db.scalar(select(RefreshToken).where(RefreshToken.jti == jti))
    if stored is None:
        raise AuthenticationError("Refresh token is invalid")
    if stored.revoked_at is None:
        stored.revoked_at = datetime.now(timezone.utc)
        db.commit()
