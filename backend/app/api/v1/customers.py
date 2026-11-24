from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user, require_permission
from app.core.permissions import Permission
from app.db.session import get_db
from app.models.identity import User
from app.schemas.customer import (
    CustomerAccountPage,
    CustomerCreate,
    CustomerPage,
    CustomerResponse,
    CustomerUpdate,
)
from app.schemas.booking import (
    CustomerBookingPage,
    CustomerBookingResponse,
    CustomerBookingStatusResponse,
    CustomerPaymentResponse,
)
from app.services.customer_service import (
    CustomerError,
    create_customer,
    get_customer,
    list_linkable_customer_accounts,
    list_customers,
    update_customer,
)
from app.services.booking_service import payment_summary
from app.services.booking_service import (
    BookingError,
    get_customer_booking,
    list_customer_bookings,
)
from app.models.booking import Booking


router = APIRouter(prefix="/customers", tags=["customers"])
can_read_customers = require_permission(Permission.CUSTOMERS_READ)
can_write_customers = require_permission(Permission.CUSTOMERS_WRITE)


def customer_error(exc: CustomerError) -> HTTPException:
    status_code = status.HTTP_404_NOT_FOUND
    if exc.code in {"EMAIL_EXISTS", "CUSTOMER_ACCOUNT_LINKED"}:
        status_code = status.HTTP_409_CONFLICT
    elif exc.code == "CUSTOMER_ACCOUNT_REQUIRED":
        status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
    return HTTPException(
        status_code=status_code,
        detail={"code": exc.code, "message": exc.message},
    )


def customer_booking_error(exc: BookingError) -> HTTPException:
    status_code = status.HTTP_404_NOT_FOUND
    if exc.code == "CUSTOMER_PROFILE_NOT_LINKED":
        status_code = status.HTTP_403_FORBIDDEN
    return HTTPException(
        status_code=status_code,
        detail={"code": exc.code, "message": exc.message},
    )


def _customer_booking_response(booking: Booking) -> CustomerBookingResponse:
    departure = booking.departure
    paid, outstanding, _, completion_status = payment_summary(
        booking.total_amount,
        booking.payments,
    )
    return CustomerBookingResponse(
        id=booking.id,
        reference=booking.reference,
        status=booking.status,
        passenger_count=booking.passenger_count,
        total_amount=booking.total_amount,
        currency=booking.currency,
        verified_paid_amount=paid,
        outstanding_balance=outstanding,
        payment_completion_status=completion_status,
        expires_at=booking.expires_at,
        tour_title=departure.tour.title,
        destination=departure.tour.destination,
        duration_days=departure.tour.duration_days,
        departure_start_date=departure.start_date,
        departure_end_date=departure.end_date,
        departure_status=departure.status,
        travelers=booking.travelers,
        status_history=[
            CustomerBookingStatusResponse(
                old_status=item.old_status,
                new_status=item.new_status,
                changed_at=item.changed_at,
            )
            for item in sorted(
                booking.status_history,
                key=lambda item: item.changed_at,
            )
        ],
        payments=[
            CustomerPaymentResponse.model_validate(payment)
            for payment in sorted(
                booking.payments,
                key=lambda payment: payment.recorded_at,
            )
        ],
    )


def _require_customer_role(user: User) -> None:
    if not any(role.code == "CUSTOMER" for role in user.roles):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "CUSTOMER_ACCESS_REQUIRED",
                "message": "A CUSTOMER account is required",
            },
        )


@router.get("", response_model=CustomerPage)
def read_customers(
    page: int = Query(default=1, ge=1),
    size: int = Query(default=20, ge=1, le=100),
    search: str | None = Query(default=None, max_length=255),
    db: Session = Depends(get_db),
    _user: User = Depends(can_read_customers),
) -> CustomerPage:
    items, total, pages = list_customers(db, page, size, search)
    return CustomerPage(items=items, total=total, page=page, size=size, pages=pages)


@router.get("/me/bookings", response_model=CustomerBookingPage)
def read_my_bookings(
    page: int = Query(default=1, ge=1),
    size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> CustomerBookingPage:
    _require_customer_role(user)
    try:
        items, total, pages = list_customer_bookings(
            db,
            user.id,
            page,
            size,
        )
        return CustomerBookingPage(
            items=[_customer_booking_response(item) for item in items],
            total=total,
            page=page,
            size=size,
            pages=pages,
        )
    except BookingError as exc:
        raise customer_booking_error(exc) from None


@router.get(
    "/me/bookings/{booking_id}",
    response_model=CustomerBookingResponse,
)
def read_my_booking(
    booking_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> CustomerBookingResponse:
    _require_customer_role(user)
    try:
        booking = get_customer_booking(db, user.id, booking_id)
        return _customer_booking_response(booking)
    except BookingError as exc:
        raise customer_booking_error(exc) from None


@router.get("/linkable-accounts", response_model=CustomerAccountPage)
def read_linkable_customer_accounts(
    page: int = Query(default=1, ge=1),
    size: int = Query(default=100, ge=1, le=100),
    customer_id: UUID | None = Query(default=None),
    search: str | None = Query(default=None, max_length=255),
    db: Session = Depends(get_db),
    _user: User = Depends(can_write_customers),
) -> CustomerAccountPage:
    try:
        items, total, pages = list_linkable_customer_accounts(
            db,
            page,
            size,
            customer_id,
            search,
        )
        return CustomerAccountPage(
            items=items,
            total=total,
            page=page,
            size=size,
            pages=pages,
        )
    except CustomerError as exc:
        raise customer_error(exc) from None


@router.get("/{customer_id}", response_model=CustomerResponse)
def read_customer(
    customer_id: UUID,
    db: Session = Depends(get_db),
    _user: User = Depends(can_read_customers),
) -> CustomerResponse:
    try:
        return CustomerResponse.model_validate(get_customer(db, customer_id))
    except CustomerError as exc:
        raise customer_error(exc) from None


@router.post(
    "",
    response_model=CustomerResponse,
    status_code=status.HTTP_201_CREATED,
)
def post_customer(
    payload: CustomerCreate,
    db: Session = Depends(get_db),
    user: User = Depends(can_write_customers),
) -> CustomerResponse:
    try:
        return CustomerResponse.model_validate(
            create_customer(db, payload, user.id)
        )
    except CustomerError as exc:
        raise customer_error(exc) from None


@router.patch("/{customer_id}", response_model=CustomerResponse)
def patch_customer(
    customer_id: UUID,
    payload: CustomerUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(can_write_customers),
) -> CustomerResponse:
    try:
        return CustomerResponse.model_validate(
            update_customer(db, customer_id, payload, user.id)
        )
    except CustomerError as exc:
        raise customer_error(exc) from None
