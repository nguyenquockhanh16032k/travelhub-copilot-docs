import math
from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.core.audit import record_audit_event
from app.models.customer import Customer
from app.models.identity import Role, User
from app.schemas.customer import (
    CustomerAccountOption,
    CustomerCreate,
    CustomerUpdate,
)


class CustomerError(Exception):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


def _linked_customer_account(
    db: Session,
    user_id: UUID,
    *,
    customer_id: UUID | None = None,
) -> User:
    user = db.scalar(
        select(User)
        .where(User.id == user_id)
        .options(selectinload(User.roles))
        .with_for_update()
    )
    if user is None or not user.is_active or not any(
        role.code == "CUSTOMER" for role in user.roles
    ):
        raise CustomerError(
            "CUSTOMER_ACCOUNT_REQUIRED",
            "An active CUSTOMER account is required for account linking",
        )

    duplicate_link_filters = [Customer.user_id == user_id]
    if customer_id is not None:
        duplicate_link_filters.append(Customer.id != customer_id)
    linked_customer = db.scalar(
        select(Customer.id).where(*duplicate_link_filters)
    )
    if linked_customer is not None:
        raise CustomerError(
            "CUSTOMER_ACCOUNT_LINKED",
            "This customer account is already linked to another profile",
        )
    return user


def _record_account_link_change(
    db: Session,
    *,
    actor_user_id: UUID | None,
    customer_id: UUID,
    old_user_id: UUID | None,
    new_user_id: UUID | None,
) -> None:
    if old_user_id == new_user_id:
        return
    if old_user_id is not None:
        record_audit_event(
            db,
            actor_user_id=actor_user_id,
            action="customer.account_unlinked",
            resource_type="customer",
            resource_id=customer_id,
            details={
                "customer_id": str(customer_id),
                "user_id": str(old_user_id),
            },
        )
    if new_user_id is not None:
        record_audit_event(
            db,
            actor_user_id=actor_user_id,
            action="customer.account_linked",
            resource_type="customer",
            resource_id=customer_id,
            details={
                "customer_id": str(customer_id),
                "user_id": str(new_user_id),
            },
        )


def list_customers(
    db: Session,
    page: int,
    size: int,
    search: str | None,
) -> tuple[list[Customer], int, int]:
    query = select(Customer)
    count_query = select(func.count(Customer.id))
    if search:
        pattern = f"%{search}%"
        predicate = (
            Customer.full_name.ilike(pattern)
            | Customer.email.ilike(pattern)
            | Customer.phone.ilike(pattern)
        )
        query = query.where(predicate)
        count_query = count_query.where(predicate)

    query = query.order_by(Customer.created_at.desc()).offset((page - 1) * size).limit(size)
    items = list(db.scalars(query))
    total = int(db.scalar(count_query) or 0)
    pages = math.ceil(total / size) if total else 0
    return items, total, pages


def get_customer(db: Session, customer_id: UUID) -> Customer:
    customer = db.get(Customer, customer_id)
    if customer is None:
        raise CustomerError("CUSTOMER_NOT_FOUND", "Customer not found")
    return customer


def list_linkable_customer_accounts(
    db: Session,
    page: int,
    size: int,
    customer_id: UUID | None = None,
    search: str | None = None,
) -> tuple[list[CustomerAccountOption], int, int]:
    current_user_id: UUID | None = None
    if customer_id is not None:
        customer = db.get(Customer, customer_id)
        if customer is None:
            raise CustomerError("CUSTOMER_NOT_FOUND", "Customer not found")
        current_user_id = customer.user_id

    linked_elsewhere_filters = [Customer.user_id == User.id]
    if customer_id is not None:
        linked_elsewhere_filters.append(Customer.id != customer_id)
    linked_elsewhere = select(Customer.id).where(*linked_elsewhere_filters)

    account_filters = [
        User.roles.any(Role.code == "CUSTOMER"),
        ~linked_elsewhere.exists(),
    ]
    if current_user_id is not None:
        account_filters.append(
            or_(User.is_active.is_(True), User.id == current_user_id)
        )
    else:
        account_filters.append(User.is_active.is_(True))
    if search:
        account_filters.append(
            or_(
                User.email.ilike(f"%{search.strip()}%"),
                User.id == current_user_id,
            )
            if current_user_id is not None
            else User.email.ilike(f"%{search.strip()}%")
        )

    query = select(User).where(*account_filters).order_by(User.email, User.id)
    count_query = select(func.count(User.id)).where(*account_filters)
    accounts = list(db.scalars(query.offset((page - 1) * size).limit(size)))
    total = int(db.scalar(count_query) or 0)
    if current_user_id is not None and all(
        account.id != current_user_id for account in accounts
    ):
        current_account = db.get(User, current_user_id)
        if current_account is not None:
            accounts.insert(0, current_account)
    items = [
        CustomerAccountOption(id=account.id, email=account.email)
        for account in accounts
    ]
    return items, total, math.ceil(total / size) if total else 0


def create_customer(
    db: Session,
    payload: CustomerCreate,
    actor_user_id: UUID | None = None,
) -> Customer:
    email = str(payload.email).lower() if payload.email else None
    if email and db.scalar(select(Customer).where(Customer.email == email)) is not None:
        raise CustomerError("EMAIL_EXISTS", "A customer with this email already exists")
    if payload.user_id is not None:
        _linked_customer_account(db, payload.user_id)

    customer = Customer(
        full_name=payload.full_name,
        email=email,
        phone=payload.phone,
        address=payload.address,
        user_id=payload.user_id,
    )
    try:
        db.add(customer)
        db.flush()
        record_audit_event(
            db,
            actor_user_id=actor_user_id,
            action="customer.created",
            resource_type="customer",
            resource_id=customer.id,
        )
        _record_account_link_change(
            db,
            actor_user_id=actor_user_id,
            customer_id=customer.id,
            old_user_id=None,
            new_user_id=customer.user_id,
        )
        db.commit()
    except IntegrityError:
        db.rollback()
        if payload.user_id is not None and db.scalar(
            select(Customer.id).where(Customer.user_id == payload.user_id)
        ) is not None:
            raise CustomerError(
                "CUSTOMER_ACCOUNT_LINKED",
                "This customer account is already linked to another profile",
            ) from None
        raise
    db.refresh(customer)
    return customer


def update_customer(
    db: Session,
    customer_id: UUID,
    payload: CustomerUpdate,
    actor_user_id: UUID | None = None,
) -> Customer:
    customer = db.scalar(
        select(Customer)
        .where(Customer.id == customer_id)
        .with_for_update()
    )
    if customer is None:
        raise CustomerError("CUSTOMER_NOT_FOUND", "Customer not found")

    values = payload.model_dump(exclude_unset=True)
    if "email" in values and values["email"] is not None:
        email = str(values["email"]).lower()
        existing = db.scalar(
            select(Customer).where(
                Customer.email == email,
                Customer.id != customer_id,
            )
        )
        if existing is not None:
            raise CustomerError("EMAIL_EXISTS", "A customer with this email already exists")
        values["email"] = email
    old_user_id = customer.user_id
    if "user_id" in values and values["user_id"] is not None:
        _linked_customer_account(
            db,
            values["user_id"],
            customer_id=customer.id,
        )

    for field, value in values.items():
        setattr(customer, field, value)
    record_audit_event(
        db,
        actor_user_id=actor_user_id,
        action="customer.updated",
        resource_type="customer",
        resource_id=customer.id,
        details={"fields": sorted(values)},
    )
    _record_account_link_change(
        db,
        actor_user_id=actor_user_id,
        customer_id=customer.id,
        old_user_id=old_user_id,
        new_user_id=customer.user_id,
    )
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        new_user_id = values.get("user_id")
        if new_user_id is not None and db.scalar(
            select(Customer.id).where(
                Customer.user_id == new_user_id,
                Customer.id != customer_id,
            )
        ) is not None:
            raise CustomerError(
                "CUSTOMER_ACCOUNT_LINKED",
                "This customer account is already linked to another profile",
            ) from None
        raise
    db.refresh(customer)
    return customer
