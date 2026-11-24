import math
from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.core.audit import record_audit_event
from app.core.permissions import Permission, assignable_roles, has_permission
from app.core.security import hash_password
from app.models.identity import Role, User
from app.schemas.users import UserCreate, UserUpdate


ROLE_DESCRIPTIONS = {
    "ADMIN": "Full business operation access and staff account management",
    "STAFF": "Operational access to assigned business workflows",
    "CUSTOMER": "Customer access to the customer's own bookings",
}


class UserManagementError(Exception):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


def list_users(
    db: Session,
    actor: User,
    page: int,
    size: int,
    search: str | None,
) -> tuple[list[User], int, int]:
    query = select(User).options(selectinload(User.roles))
    count_query = select(func.count(User.id))
    if has_permission(actor, Permission.USERS_MANAGE_ADMIN):
        scope = or_(
            User.id == actor.id,
            User.roles.any(Role.code.in_(("ADMIN", "STAFF"))),
        )
    else:
        scope = (
            User.roles.any(Role.code == "STAFF")
            & ~User.roles.any(Role.code != "STAFF")
        )
    query = query.where(scope)
    count_query = count_query.where(scope)
    if search:
        pattern = f"%{search.strip()}%"
        search_filter = User.email.ilike(pattern)
        query = query.where(search_filter)
        count_query = count_query.where(search_filter)

    query = query.order_by(User.email, User.id)
    query = query.offset((page - 1) * size).limit(size)
    items = list(db.scalars(query))
    total = int(db.scalar(count_query) or 0)
    return items, total, math.ceil(total / size) if total else 0


def get_assignable_roles(actor: User) -> list[tuple[str, str]]:
    return [
        (role_code, ROLE_DESCRIPTIONS[role_code])
        for role_code in assignable_roles(actor)
    ]


def create_user(db: Session, actor: User, payload: UserCreate) -> User:
    _require_role_assignment(actor, payload.role)
    email = str(payload.email).lower()
    if db.scalar(select(User.id).where(User.email == email)) is not None:
        raise UserManagementError("EMAIL_EXISTS", "A user with this email exists")

    role = _get_or_create_role(db, payload.role)
    user = User(
        email=email,
        password_hash=hash_password(payload.password),
        is_active=True,
        roles=[role],
    )
    db.add(user)
    db.flush()
    record_audit_event(
        db,
        actor_user_id=actor.id,
        action="user.created",
        resource_type="user",
        resource_id=user.id,
        details={"role": payload.role},
    )
    if payload.role == "CUSTOMER":
        record_audit_event(
            db,
            actor_user_id=actor.id,
            action="customer_account.created",
            resource_type="customer_account",
            resource_id=user.id,
            details={"customer_id": None, "user_id": str(user.id)},
        )
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        if db.scalar(select(User.id).where(User.email == email)) is not None:
            raise UserManagementError(
                "EMAIL_EXISTS",
                "A user with this email exists",
            ) from None
        raise exc
    return _load_user(db, user.id)


def update_user(
    db: Session,
    actor: User,
    user_id: UUID,
    payload: UserUpdate,
) -> User:
    user = _get_managed_user(db, actor, user_id)
    values = payload.model_dump(exclude_unset=True)
    current_roles = {role.code for role in user.roles}

    if "role" in values:
        _require_role_assignment(actor, values["role"])
        if user.id == actor.id and values["role"] not in current_roles:
            raise UserManagementError(
                "SELF_ROLE_CHANGE",
                "You cannot change your own role",
            )
        role = _get_or_create_role(db, values["role"])
        user.roles = [role]

    if "email" in values:
        email = str(values["email"]).lower()
        existing = db.scalar(
            select(User.id).where(User.email == email, User.id != user_id)
        )
        if existing is not None:
            raise UserManagementError(
                "EMAIL_EXISTS",
                "A user with this email exists",
            )
        user.email = email

    if "password" in values:
        user.password_hash = hash_password(values["password"])
    if "is_active" in values:
        if user.id == actor.id and values["is_active"] is False:
            raise UserManagementError(
                "SELF_DEACTIVATION",
                "You cannot deactivate your own account",
            )
        user.is_active = values["is_active"]

    record_audit_event(
        db,
        actor_user_id=actor.id,
        action="user.updated",
        resource_type="user",
        resource_id=user.id,
        details={
            "role_changed": "role" in values,
            "active_changed": "is_active" in values,
            "password_changed": "password" in values,
            "email_changed": "email" in values,
        },
    )
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        if "email" in values and db.scalar(
            select(User.id).where(User.email == str(values["email"]).lower())
        ) is not None:
            raise UserManagementError(
                "EMAIL_EXISTS",
                "A user with this email exists",
            ) from None
        raise exc
    return _load_user(db, user.id)


def _require_role_assignment(actor: User, role_code: str) -> None:
    if role_code not in assignable_roles(actor):
        raise UserManagementError(
            "ROLE_ASSIGNMENT_FORBIDDEN",
            "You cannot assign this role",
        )


def _get_managed_user(db: Session, actor: User, user_id: UUID) -> User:
    user = _load_user_or_none(db, user_id)
    if user is None:
        raise UserManagementError("USER_NOT_FOUND", "User not found")
    if user.id == actor.id:
        return user

    target_roles = {role.code for role in user.roles}
    if "SUPER_ADMIN" in target_roles:
        raise UserManagementError(
            "FORBIDDEN",
            "System administrator accounts cannot be changed here",
        )
    actor_can_manage_admins = has_permission(
        actor,
        Permission.USERS_MANAGE_ADMIN,
    )
    manageable = (
        target_roles in ({"ADMIN"}, {"STAFF"})
        if actor_can_manage_admins
        else target_roles == {"STAFF"}
    )
    if not manageable:
        raise UserManagementError("FORBIDDEN", "You cannot manage this user")
    return user


def _get_or_create_role(db: Session, role_code: str) -> Role:
    role = db.scalar(select(Role).where(Role.code == role_code))
    if role is None:
        role = Role(
            code=role_code,
            description=ROLE_DESCRIPTIONS.get(role_code, role_code.title()),
        )
        db.add(role)
        db.flush()
    return role


def _load_user(db: Session, user_id: UUID) -> User:
    user = _load_user_or_none(db, user_id)
    if user is None:
        raise UserManagementError("USER_NOT_FOUND", "User not found")
    return user


def _load_user_or_none(db: Session, user_id: UUID) -> User | None:
    return db.scalar(
        select(User)
        .where(User.id == user_id)
        .options(selectinload(User.roles))
    )
