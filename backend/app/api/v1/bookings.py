from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_optional_current_user, require_permission
from app.core.permissions import Permission, has_permission
from app.db.session import get_db
from app.models.booking import Booking
from app.models.identity import User
from app.schemas.booking import (
    BookingCreate,
    BookingResponse,
    BookingUpdate,
    PaymentAdminResponse,
    PaymentBookingSummary,
    PaymentCreate,
    PaymentExceptionCreate,
    PaymentExceptionVerify,
    PaymentMethod,
    PaymentPage,
    PaymentResponse,
    PaymentStatus,
    StaffBookingResponse,
    StatusChange,
)
from app.services.booking_service import (
    BookingError,
    change_booking_status,
    create_booking,
    create_financial_exception,
    create_payment,
    get_booking_payment_summary,
    get_booking,
    list_bookings,
    list_payments,
    payment_actor_attributions,
    payment_summary,
    update_booking,
    verify_payment,
    verify_payment_as_exception,
)


router = APIRouter(tags=["bookings"])
can_read_bookings = require_permission(Permission.BOOKINGS_READ)
can_update_bookings = require_permission(Permission.BOOKINGS_WRITE)
can_change_booking_status = require_permission(Permission.BOOKINGS_STATUS)
can_read_payments = require_permission(Permission.PAYMENTS_READ)
can_record_payments = require_permission(Permission.PAYMENTS_WRITE)


def _booking_response(
    booking: Booking,
    *,
    include_financials: bool,
) -> BookingResponse | StaffBookingResponse:
    response_model = BookingResponse if include_financials else StaffBookingResponse
    return response_model.model_validate(booking)


def booking_error(exc: BookingError) -> HTTPException:
    status_code = status.HTTP_409_CONFLICT
    if exc.code in {
        "DEPARTURE_NOT_FOUND",
        "CUSTOMER_NOT_FOUND",
        "BOOKING_NOT_FOUND",
        "PAYMENT_NOT_FOUND",
    }:
        status_code = status.HTTP_404_NOT_FOUND
    if exc.code == "PAYMENT_PERMISSION_REQUIRED":
        return HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "FORBIDDEN",
                "message": "This booking action is not permitted",
            },
        )
    if exc.code == "INVALID_STATUS":
        status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
    return HTTPException(
        status_code=status_code,
        detail={"code": exc.code, "message": exc.message},
    )


@router.get("/bookings")
def read_bookings(
    page: int = Query(default=1, ge=1),
    size: int = Query(default=20, ge=1, le=100),
    status_filter: str | None = Query(default=None),
    search: str | None = Query(default=None, max_length=255),
    db: Session = Depends(get_db),
    user: User = Depends(can_read_bookings),
) -> dict[str, object]:
    try:
        items, total, pages = list_bookings(
            db,
            page,
            size,
            status_filter,
            search,
        )
        return {
            "items": [
                _booking_response(
                    item,
                    include_financials=has_permission(
                        user,
                        Permission.PAYMENTS_READ,
                    ),
                ).model_dump()
                for item in items
            ],
            "total": total,
            "page": page,
            "size": size,
            "pages": pages,
        }
    except BookingError as exc:
        raise booking_error(exc) from None


@router.get(
    "/bookings/{booking_id}",
    response_model=BookingResponse | StaffBookingResponse,
)
def read_booking(
    booking_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(can_read_bookings),
) -> BookingResponse | StaffBookingResponse:
    try:
        return _booking_response(
            get_booking(db, booking_id),
            include_financials=has_permission(user, Permission.PAYMENTS_READ),
        )
    except BookingError as exc:
        raise booking_error(exc) from None


@router.post(
    "/bookings",
    response_model=BookingResponse | StaffBookingResponse,
    status_code=status.HTTP_201_CREATED,
)
def post_booking(
    payload: BookingCreate,
    db: Session = Depends(get_db),
    user: User | None = Depends(get_optional_current_user),
) -> BookingResponse | StaffBookingResponse:
    try:
        can_link_customer = user is not None and has_permission(
            user,
            Permission.BOOKINGS_CREATE_FOR_CUSTOMERS,
        )
        booking = create_booking(
            db,
            payload,
            actor_user_id=user.id if user else None,
            can_link_customer=can_link_customer,
        )
        include_financials = (
            user is None or has_permission(user, Permission.PAYMENTS_READ)
        )
        return _booking_response(
            booking,
            include_financials=include_financials,
        )
    except BookingError as exc:
        raise booking_error(exc) from None


@router.post(
    "/bookings/{booking_id}/confirm",
    response_model=BookingResponse | StaffBookingResponse,
)
def confirm_booking(
    booking_id: UUID,
    payload: StatusChange,
    db: Session = Depends(get_db),
    user: User = Depends(can_change_booking_status),
) -> BookingResponse | StaffBookingResponse:
    try:
        booking = change_booking_status(
            db,
            booking_id,
            "confirmed",
            user.id,
            payload.reason,
            can_confirm_with_payments=has_permission(
                user,
                Permission.PAYMENTS_WRITE,
            ),
        )
        return _booking_response(
            booking,
            include_financials=has_permission(user, Permission.PAYMENTS_READ),
        )
    except BookingError as exc:
        raise booking_error(exc) from None


@router.post(
    "/bookings/{booking_id}/cancel",
    response_model=BookingResponse | StaffBookingResponse,
)
def cancel_booking(
    booking_id: UUID,
    payload: StatusChange,
    db: Session = Depends(get_db),
    user: User = Depends(can_change_booking_status),
) -> BookingResponse | StaffBookingResponse:
    try:
        booking = change_booking_status(
            db,
            booking_id,
            "cancelled",
            user.id,
            payload.reason,
        )
        return _booking_response(
            booking,
            include_financials=has_permission(user, Permission.PAYMENTS_READ),
        )
    except BookingError as exc:
        raise booking_error(exc) from None


@router.post(
    "/bookings/{booking_id}/reject",
    response_model=BookingResponse | StaffBookingResponse,
)
def reject_booking(
    booking_id: UUID,
    payload: StatusChange,
    db: Session = Depends(get_db),
    user: User = Depends(can_change_booking_status),
) -> BookingResponse | StaffBookingResponse:
    try:
        booking = change_booking_status(
            db,
            booking_id,
            "rejected",
            user.id,
            payload.reason,
        )
        return _booking_response(
            booking,
            include_financials=has_permission(user, Permission.PAYMENTS_READ),
        )
    except BookingError as exc:
        raise booking_error(exc) from None


@router.get("/payments", response_model=PaymentPage)
def read_payments(
    page: int = Query(default=1, ge=1),
    size: int = Query(default=20, ge=1, le=100),
    status_filter: PaymentStatus | None = Query(default=None),
    method_filter: PaymentMethod | None = Query(default=None),
    search: str | None = Query(default=None, max_length=255),
    booking_id: UUID | None = Query(default=None),
    requires_resolution: bool | None = Query(default=None),
    db: Session = Depends(get_db),
    _user: User = Depends(can_read_payments),
) -> PaymentPage:
    try:
        items, total, pages = list_payments(
            db,
            page,
            size,
            status_filter,
            method_filter,
            search,
            booking_id,
            requires_resolution,
        )
        attributions = payment_actor_attributions(db, items)
        response_items: list[PaymentAdminResponse] = []
        for payment in items:
            paid, outstanding, overpaid, completion_status = payment_summary(
                payment.booking.total_amount,
                payment.booking.payments,
            )
            recorded_by, verified_by = attributions.get(
                payment.id,
                (None, None),
            )
            response_items.append(
                PaymentAdminResponse(
                    **PaymentResponse.model_validate(payment).model_dump(),
                    booking_reference=payment.booking.reference,
                    booking_status=payment.booking.status,
                    booking_total=payment.booking.total_amount,
                    verified_paid_amount=paid,
                    outstanding_balance=outstanding,
                    overpaid_amount=overpaid,
                    payment_completion_status=completion_status,
                    recorded_by=recorded_by,
                    verified_by=verified_by,
                )
            )
        booking_summary = None
        if booking_id is not None:
            booking, summary = get_booking_payment_summary(db, booking_id)
            paid, outstanding, overpaid, completion_status = summary
            booking_summary = PaymentBookingSummary(
                booking_id=booking.id,
                booking_reference=booking.reference,
                booking_status=booking.status,
                booking_total=booking.total_amount,
                currency=booking.currency,
                verified_paid_amount=paid,
                outstanding_balance=outstanding,
                overpaid_amount=overpaid,
                payment_completion_status=completion_status,
            )
        return PaymentPage(
            items=response_items,
            total=total,
            page=page,
            size=size,
            pages=pages,
            booking_summary=booking_summary,
        )
    except BookingError as exc:
        raise booking_error(exc) from None


@router.post(
    "/payments",
    response_model=PaymentResponse,
    status_code=status.HTTP_201_CREATED,
)
def post_payment(
    payload: PaymentCreate,
    db: Session = Depends(get_db),
    idempotency_key: str | None = Header(
        default=None,
        min_length=1,
        max_length=128,
        alias="Idempotency-Key",
    ),
    user: User = Depends(can_record_payments),
) -> PaymentResponse:
    if idempotency_key is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "code": "IDEMPOTENCY_KEY_REQUIRED",
                "message": "Idempotency-Key header is required",
            },
        )
    try:
        return PaymentResponse.model_validate(
            create_payment(db, payload, user.id, idempotency_key)
        )
    except BookingError as exc:
        raise booking_error(exc) from None


@router.post(
    "/payments/exceptions",
    response_model=PaymentResponse,
    status_code=status.HTTP_201_CREATED,
)
def post_payment_exception(
    payload: PaymentExceptionCreate,
    db: Session = Depends(get_db),
    idempotency_key: str | None = Header(
        default=None,
        min_length=1,
        max_length=128,
        alias="Idempotency-Key",
    ),
    user: User = Depends(can_record_payments),
) -> PaymentResponse:
    if idempotency_key is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "code": "IDEMPOTENCY_KEY_REQUIRED",
                "message": "Idempotency-Key header is required",
            },
        )
    try:
        return PaymentResponse.model_validate(
            create_financial_exception(db, payload, user.id, idempotency_key)
        )
    except BookingError as exc:
        raise booking_error(exc) from None


@router.post(
    "/payments/{payment_id}/verify",
    response_model=PaymentResponse,
)
def post_payment_verification(
    payment_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(can_record_payments),
) -> PaymentResponse:
    try:
        return PaymentResponse.model_validate(
            verify_payment(db, payment_id, user.id)
        )
    except BookingError as exc:
        raise booking_error(exc) from None


@router.post(
    "/payments/{payment_id}/financial-exception",
    response_model=PaymentResponse,
)
def post_payment_verification_exception(
    payment_id: UUID,
    payload: PaymentExceptionVerify,
    db: Session = Depends(get_db),
    user: User = Depends(can_record_payments),
) -> PaymentResponse:
    try:
        return PaymentResponse.model_validate(
            verify_payment_as_exception(db, payment_id, payload, user.id)
        )
    except BookingError as exc:
        raise booking_error(exc) from None


@router.patch(
    "/bookings/{booking_id}",
    response_model=BookingResponse | StaffBookingResponse,
)
def patch_booking(
    booking_id: UUID,
    payload: BookingUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(can_update_bookings),
) -> BookingResponse | StaffBookingResponse:
    try:
        return _booking_response(
            update_booking(db, booking_id, payload, user.id),
            include_financials=has_permission(user, Permission.PAYMENTS_READ),
        )
    except BookingError as exc:
        raise booking_error(exc) from None
