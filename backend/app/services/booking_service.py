from datetime import datetime, timedelta, timezone
from decimal import Decimal
import hashlib
import json
import math
from uuid import UUID, uuid4

from sqlalchemy import Select, func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload, selectinload

from app.core.audit import record_audit_event
from app.core.business_time import business_date
from app.core.config import settings
from app.models.audit import AuditLog
from app.models.booking import (
    Booking,
    BookingCustomer,
    BookingStatusHistory,
    Payment,
)
from app.models.customer import Customer
from app.models.identity import User
from app.models.tour import Tour, TourDeparture
from app.schemas.booking import (
    BookingCreate,
    BookingUpdate,
    PaymentCompletionStatus,
    PaymentCreate,
    PaymentExceptionCreate,
    PaymentExceptionVerify,
)


class BookingError(Exception):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


def expire_pending_bookings(
    db: Session,
    now: datetime | None = None,
    departure_ids: Select[tuple[UUID]] | None = None,
) -> int:
    current_time = now or datetime.now(timezone.utc)
    query = select(Booking).where(
        Booking.status == "pending",
        Booking.expires_at.is_not(None),
        Booking.expires_at <= current_time,
    )
    if departure_ids is not None:
        query = query.where(Booking.departure_id.in_(departure_ids))
    bookings = list(
        db.scalars(
            query.options(selectinload(Booking.payments)).with_for_update()
        )
    )

    departures: dict[UUID, TourDeparture] = {}
    if bookings:
        departure_ids_to_lock = {booking.departure_id for booking in bookings}
        departures = {
            departure.id: departure
            for departure in db.scalars(
                select(TourDeparture)
                .where(TourDeparture.id.in_(departure_ids_to_lock))
                .order_by(TourDeparture.id)
                .with_for_update()
            )
        }

    expired_count = 0
    for booking in bookings:
        departure = departures.get(booking.departure_id)
        if departure is None:
            continue
        departure.available_seats += booking.passenger_count
        booking.status = "expired"
        booking.expires_at = None
        _flag_paid_payments_for_resolution(
            db,
            booking,
            "Booking hold expired before payment completion",
            actor_user_id=None,
        )
        db.add(
            BookingStatusHistory(
                booking_id=booking.id,
                old_status="pending",
                new_status="expired",
                actor_user_id=None,
                reason="Pending seat hold expired",
                changed_at=current_time,
            )
        )
        record_audit_event(
            db,
            actor_user_id=None,
            action="booking.status_changed",
            resource_type="booking",
            resource_id=booking.id,
            details={"from": "pending", "to": "expired", "reason": "expired"},
        )
        expired_count += 1

    if expired_count:
        db.commit()
    return expired_count


def list_bookings(
    db: Session,
    page: int,
    size: int,
    status_filter: str | None,
    search: str | None = None,
) -> tuple[list[Booking], int, int]:
    expire_pending_bookings(db)
    query = select(Booking).options(
        selectinload(Booking.travelers),
        selectinload(Booking.status_history),
    )
    count_query = select(func.count(Booking.id))
    if status_filter:
        if status_filter not in {
            "pending",
            "confirmed",
            "cancelled",
            "expired",
            "rejected",
            "completed",
        }:
            raise BookingError("INVALID_STATUS", "Unsupported booking status filter")
        query = query.where(Booking.status == status_filter)
        count_query = count_query.where(Booking.status == status_filter)
    if search and search.strip():
        term = f"%{search.strip()}%"
        search_filter = or_(
            Booking.reference.ilike(term),
            Booking.contact_name.ilike(term),
            Booking.contact_email.ilike(term),
        )
        query = query.where(search_filter)
        count_query = count_query.where(search_filter)
    query = query.order_by(Booking.created_at.desc()).offset((page - 1) * size).limit(size)
    items = list(db.scalars(query))
    total = int(db.scalar(count_query) or 0)
    pages = math.ceil(total / size) if total else 0
    return items, total, pages


def get_booking(db: Session, booking_id: UUID) -> Booking:
    expire_pending_bookings(db)
    booking = db.scalar(
        select(Booking)
        .where(Booking.id == booking_id)
        .options(
            selectinload(Booking.travelers),
            selectinload(Booking.status_history),
        )
    )
    if booking is None:
        raise BookingError("BOOKING_NOT_FOUND", "Booking not found")
    return booking


def list_customer_bookings(
    db: Session,
    user_id: UUID,
    page: int,
    size: int,
) -> tuple[list[Booking], int, int]:
    expire_pending_bookings(db)
    customer_id = db.scalar(
        select(Customer.id).where(Customer.user_id == user_id)
    )
    if customer_id is None:
        raise BookingError(
            "CUSTOMER_PROFILE_NOT_LINKED",
            "This account is not linked to a customer profile",
        )

    query = (
        select(Booking)
        .where(Booking.customer_id == customer_id)
        .options(
            joinedload(Booking.departure).joinedload(TourDeparture.tour),
            selectinload(Booking.travelers),
            selectinload(Booking.status_history),
            selectinload(Booking.payments),
        )
        .order_by(Booking.created_at.desc(), Booking.id)
        .offset((page - 1) * size)
        .limit(size)
    )
    items = list(db.scalars(query))
    total = int(
        db.scalar(
            select(func.count(Booking.id)).where(
                Booking.customer_id == customer_id
            )
        )
        or 0
    )
    return items, total, math.ceil(total / size) if total else 0


def get_customer_booking(
    db: Session,
    user_id: UUID,
    booking_id: UUID,
) -> Booking:
    expire_pending_bookings(db)
    customer_id = db.scalar(
        select(Customer.id).where(Customer.user_id == user_id)
    )
    if customer_id is None:
        raise BookingError(
            "CUSTOMER_PROFILE_NOT_LINKED",
            "This account is not linked to a customer profile",
        )
    booking = db.scalar(
        select(Booking)
        .where(
            Booking.id == booking_id,
            Booking.customer_id == customer_id,
        )
        .options(
            joinedload(Booking.departure).joinedload(TourDeparture.tour),
            selectinload(Booking.travelers),
            selectinload(Booking.status_history),
            selectinload(Booking.payments),
        )
    )
    if booking is None:
        raise BookingError("BOOKING_NOT_FOUND", "Booking not found")
    return booking


def create_booking(
    db: Session,
    payload: BookingCreate,
    actor_user_id: UUID | None = None,
    can_link_customer: bool = False,
) -> Booking:
    expire_pending_bookings(db)
    departure = db.scalar(
        select(TourDeparture)
        .where(TourDeparture.id == payload.departure_id)
        .with_for_update()
    )
    if departure is None:
        raise BookingError("DEPARTURE_NOT_FOUND", "Departure not found")
    tour = db.get(Tour, departure.tour_id)
    if (
        departure.status != "open"
        or departure.start_date < business_date()
        or tour is None
        or tour.status != "published"
    ):
        raise BookingError("DEPARTURE_NOT_BOOKABLE", "Departure is not bookable")

    passenger_count = len(payload.travelers)
    if departure.available_seats < passenger_count:
        raise BookingError("NOT_ENOUGH_SEATS", "Not enough seats available")
    customer_id = payload.customer_id
    if actor_user_id is not None:
        actor = db.scalar(
            select(User)
            .where(User.id == actor_user_id)
            .options(selectinload(User.roles))
        )
        if actor is not None and any(
            role.code == "CUSTOMER" for role in actor.roles
        ):
            linked_customer_id = db.scalar(
                select(Customer.id).where(Customer.user_id == actor_user_id)
            )
            if linked_customer_id is None:
                raise BookingError(
                    "CUSTOMER_PROFILE_NOT_LINKED",
                    "This account is not linked to a customer profile",
                )
            if customer_id is not None and customer_id != linked_customer_id:
                raise BookingError(
                    "CUSTOMER_NOT_FOUND",
                    "Customer not found",
                )
            customer_id = linked_customer_id

    if customer_id is not None:
        customer = db.get(Customer, customer_id)
        if customer is None or (
            not can_link_customer
            and (
                actor_user_id is None
                or customer.user_id != actor_user_id
            )
        ):
            raise BookingError("CUSTOMER_NOT_FOUND", "Customer not found")

    departure.available_seats -= passenger_count
    reference = f"TH-{uuid4().hex[:12].upper()}"
    total = departure.price * Decimal(passenger_count)

    booking = Booking(
        reference=reference,
        departure_id=departure.id,
        customer_id=customer_id,
        created_by_user_id=actor_user_id,
        contact_name=payload.contact_name,
        contact_email=str(payload.contact_email),
        contact_phone=payload.contact_phone,
        passenger_count=passenger_count,
        status="pending",
        expires_at=datetime.now(timezone.utc)
        + timedelta(minutes=settings.booking_pending_hold_minutes),
        total_amount=total,
        currency=departure.currency,
        notes=payload.notes,
    )
    db.add(booking)
    db.flush()

    for traveler in payload.travelers:
        db.add(
            BookingCustomer(
                booking_id=booking.id,
                full_name=traveler.full_name,
                traveler_type=traveler.traveler_type,
            )
        )

    db.add(
        BookingStatusHistory(
            booking_id=booking.id,
            old_status=None,
            new_status="pending",
            actor_user_id=actor_user_id,
            reason="Booking created",
            changed_at=datetime.now(timezone.utc),
        )
    )
    record_audit_event(
        db,
        actor_user_id=actor_user_id,
        action="booking.created",
        resource_type="booking",
        resource_id=booking.id,
        details={"passenger_count": passenger_count},
    )
    db.commit()
    db.refresh(booking)
    return booking


def change_booking_status(
    db: Session,
    booking_id: UUID,
    new_status: str,
    actor_user_id: UUID,
    reason: str | None,
    *,
    can_confirm_with_payments: bool = True,
) -> Booking:
    expire_pending_bookings(db)
    booking = db.scalar(
        select(Booking).where(Booking.id == booking_id).with_for_update()
    )
    if booking is None:
        raise BookingError("BOOKING_NOT_FOUND", "Booking not found")
    if booking.status == new_status:
        raise BookingError("INVALID_STATUS", "Booking already has this status")
    if booking.status in {"cancelled", "expired", "rejected", "completed"}:
        raise BookingError("INVALID_STATUS", "Terminal bookings cannot change")
    if new_status not in {"confirmed", "cancelled", "rejected", "completed"}:
        raise BookingError("INVALID_STATUS", "Unsupported booking status")

    if new_status == "confirmed" and booking.status == "pending":
        if not _booking_hold_is_valid(booking, datetime.now(timezone.utc)):
            raise BookingError(
                "BOOKING_HOLD_EXPIRED",
                "A pending booking can only be confirmed while its hold is valid",
            )
        paid_total = _verified_paid_total(db, booking.id)
        if paid_total > 0 and not can_confirm_with_payments:
            raise BookingError(
                "PAYMENT_PERMISSION_REQUIRED",
                "Payment permission is required to confirm a partially paid booking",
            )

    old_status = booking.status
    if new_status in {"cancelled", "rejected"}:
        departure = db.scalar(
            select(TourDeparture)
            .where(TourDeparture.id == booking.departure_id)
            .with_for_update()
        )
        if departure is None:
            raise BookingError("DEPARTURE_NOT_FOUND", "Departure not found")
        departure.available_seats += booking.passenger_count
    if new_status in {"confirmed", "cancelled", "rejected"}:
        booking.expires_at = None

    booking.status = new_status
    if new_status in {"cancelled", "rejected"}:
        _flag_paid_payments_for_resolution(
            db,
            booking,
            f"Booking was {new_status}",
            actor_user_id=actor_user_id,
        )
    db.add(
        BookingStatusHistory(
            booking_id=booking.id,
            old_status=old_status,
            new_status=new_status,
            actor_user_id=actor_user_id,
            reason=reason,
            changed_at=datetime.now(timezone.utc),
        )
    )
    record_audit_event(
        db,
        actor_user_id=actor_user_id,
        action="booking.status_changed",
        resource_type="booking",
        resource_id=booking.id,
        details={"from": old_status, "to": new_status},
    )
    db.commit()
    db.refresh(booking)
    return booking


def update_booking(
    db: Session,
    booking_id: UUID,
    payload: BookingUpdate,
    actor_user_id: UUID,
) -> Booking:
    expire_pending_bookings(db)
    booking = db.scalar(
        select(Booking)
        .where(Booking.id == booking_id)
        .options(selectinload(Booking.travelers))
        .with_for_update()
    )
    if booking is None:
        raise BookingError("BOOKING_NOT_FOUND", "Booking not found")
    if booking.status not in {"pending", "confirmed"}:
        raise BookingError(
            "INVALID_BOOKING_UPDATE",
            "Only pending or confirmed bookings can be updated",
        )

    values = payload.model_dump(exclude_unset=True)
    travelers = values.pop("travelers", None)
    for field, value in values.items():
        setattr(booking, field, str(value) if field == "contact_email" else value)

    if travelers is not None:
        if len(travelers) != booking.passenger_count:
            raise BookingError(
                "PASSENGER_COUNT_CHANGE_UNSUPPORTED",
                "Traveler count cannot be changed through this operation",
            )
        for existing, updated in zip(booking.travelers, travelers):
            existing.full_name = updated["full_name"]
            existing.traveler_type = updated["traveler_type"]

    record_audit_event(
        db,
        actor_user_id=actor_user_id,
        action="booking.details_updated",
        resource_type="booking",
        resource_id=booking.id,
        details={
            "contact_changed": bool(values),
            "travelers_changed": travelers is not None,
        },
    )
    db.commit()
    return get_booking(db, booking.id)


def create_payment(
    db: Session,
    payload: PaymentCreate,
    actor_user_id: UUID | None,
    idempotency_key: str,
) -> Payment:
    idempotency_key = idempotency_key.strip()
    fingerprint = _payment_fingerprint("payment.create", payload)
    existing = _find_idempotent_payment(db, idempotency_key, fingerprint)
    if existing is not None:
        return existing

    expire_pending_bookings(db)
    booking = db.scalar(
        select(Booking)
        .where(Booking.id == payload.booking_id)
        .with_for_update()
    )
    if booking is None:
        raise BookingError("BOOKING_NOT_FOUND", "Booking not found")
    existing = _find_idempotent_payment(db, idempotency_key, fingerprint)
    if existing is not None:
        return existing
    _validate_payment_currency(booking, payload.currency)
    if booking.status in {"expired", "cancelled", "rejected"}:
        raise BookingError(
            "FINANCIAL_EXCEPTION_REQUIRED",
            "Use the financial exception workflow for an inactive booking",
        )
    if (
        booking.status == "pending"
        and booking.expires_at is not None
        and not _booking_hold_is_valid(booking, datetime.now(timezone.utc))
    ):
        raise BookingError(
            "FINANCIAL_EXCEPTION_REQUIRED",
            "Use the financial exception workflow after the booking hold expires",
        )

    paid_before = _verified_paid_total(db, booking.id)
    outstanding = max(booking.total_amount - paid_before, Decimal("0.00"))
    if payload.status == "pending":
        if outstanding == Decimal("0.00"):
            raise BookingError(
                "PAYMENT_BALANCE_SETTLED",
                "No outstanding balance remains for a normal payment",
            )
        if payload.amount > outstanding:
            raise BookingError(
                "PAYMENT_AMOUNT_EXCEEDS_BALANCE",
                "Payment amount exceeds the outstanding balance",
            )
    if payload.status == "paid":
        if payload.amount > outstanding:
            raise BookingError(
                "OVERPAYMENT_EXCEPTION_REQUIRED",
                "Use the financial exception workflow for an overpayment",
            )

    _ensure_transaction_reference_is_new(db, payload.transaction_reference)
    payment = Payment(
        booking_id=payload.booking_id,
        amount=payload.amount,
        currency=payload.currency,
        method=payload.method,
        status=payload.status,
        transaction_reference=payload.transaction_reference,
        notes=payload.notes,
        requires_resolution=False,
        idempotency_key=idempotency_key,
        idempotency_fingerprint=fingerprint,
        recorded_at=datetime.now(timezone.utc),
    )
    db.add(payment)
    db.flush()
    record_audit_event(
        db,
        actor_user_id=actor_user_id,
        action="payment.created",
        resource_type="payment",
        resource_id=payment.id,
        details={
            "status": payload.status,
            "amount": str(payload.amount),
            "currency": payload.currency,
        },
    )
    if (
        payload.status == "paid"
        and booking.status == "pending"
        and paid_before + payload.amount == booking.total_amount
        and _booking_hold_is_valid(booking, datetime.now(timezone.utc))
    ):
        _confirm_booking_after_full_payment(db, booking, actor_user_id)
    return _commit_payment(db, payment, idempotency_key, fingerprint, payload.transaction_reference)


def create_financial_exception(
    db: Session,
    payload: PaymentExceptionCreate,
    actor_user_id: UUID,
    idempotency_key: str,
) -> Payment:
    idempotency_key = idempotency_key.strip()
    reason = payload.reason.strip()
    if not reason or payload.confirmation is not True:
        raise BookingError(
            "FINANCIAL_EXCEPTION_CONFIRMATION_REQUIRED",
            "A reason and explicit confirmation are required",
        )
    fingerprint = _payment_fingerprint("payment.exception.create", payload)
    existing = _find_idempotent_payment(db, idempotency_key, fingerprint)
    if existing is not None:
        return existing

    expire_pending_bookings(db)
    booking = db.scalar(
        select(Booking)
        .where(Booking.id == payload.booking_id)
        .with_for_update()
    )
    if booking is None:
        raise BookingError("BOOKING_NOT_FOUND", "Booking not found")
    existing = _find_idempotent_payment(db, idempotency_key, fingerprint)
    if existing is not None:
        return existing
    _validate_payment_currency(booking, payload.currency)
    paid_before = _verified_paid_total(db, booking.id)
    inactive_booking = booking.status in {"expired", "cancelled", "rejected"}
    overpayment = payload.amount > max(
        booking.total_amount - paid_before,
        Decimal("0"),
    )
    if not inactive_booking and not overpayment:
        raise BookingError(
            "FINANCIAL_EXCEPTION_NOT_REQUIRED",
            "Use normal payment recording when no financial exception applies",
        )

    _ensure_transaction_reference_is_new(db, payload.transaction_reference)
    exception_type = _financial_exception_type(inactive_booking, overpayment)
    payment = Payment(
        booking_id=booking.id,
        amount=payload.amount,
        currency=payload.currency,
        method=payload.method,
        status="paid",
        transaction_reference=payload.transaction_reference,
        notes=payload.notes,
        requires_resolution=True,
        resolution_reason=reason,
        idempotency_key=idempotency_key,
        idempotency_fingerprint=fingerprint,
        recorded_at=datetime.now(timezone.utc),
    )
    db.add(payment)
    db.flush()
    record_audit_event(
        db,
        actor_user_id=actor_user_id,
        action="payment.exception_recorded",
        resource_type="payment",
        resource_id=payment.id,
        details={
            "exception_type": exception_type,
            "reason": reason,
            "amount": str(payload.amount),
            "currency": payload.currency,
            "booking_id": str(booking.id),
        },
    )
    return _commit_payment(db, payment, idempotency_key, fingerprint, payload.transaction_reference)


def verify_payment(
    db: Session,
    payment_id: UUID,
    actor_user_id: UUID | None,
) -> Payment:
    payment, booking = _lock_payment_and_booking(db, payment_id)
    if payment.status == "paid":
        return payment
    if payment.status != "pending":
        raise BookingError(
            "PAYMENT_NOT_VERIFIABLE",
            "Only pending payments can be verified",
        )
    _validate_payment_currency(booking, payment.currency)
    if booking.status in {"expired", "cancelled", "rejected"}:
        raise BookingError(
            "FINANCIAL_EXCEPTION_REQUIRED",
            "Use the financial exception workflow for an inactive booking",
        )
    if (
        booking.status == "pending"
        and booking.expires_at is not None
        and not _booking_hold_is_valid(booking, datetime.now(timezone.utc))
    ):
        raise BookingError(
            "FINANCIAL_EXCEPTION_REQUIRED",
            "Use the financial exception workflow after the booking hold expires",
        )

    paid_before = _verified_paid_total(db, booking.id)
    outstanding = max(booking.total_amount - paid_before, Decimal("0"))
    if payment.amount > outstanding:
        raise BookingError(
            "OVERPAYMENT_EXCEPTION_REQUIRED",
            "Use the financial exception workflow for an overpayment",
        )

    payment.status = "paid"
    record_audit_event(
        db,
        actor_user_id=actor_user_id,
        action="payment.verified",
        resource_type="payment",
        resource_id=payment.id,
        details={
            "amount": str(payment.amount),
            "currency": payment.currency,
            "booking_id": str(booking.id),
        },
    )
    if (
        booking.status == "pending"
        and paid_before + payment.amount == booking.total_amount
        and _booking_hold_is_valid(booking, datetime.now(timezone.utc))
    ):
        _confirm_booking_after_full_payment(db, booking, actor_user_id)
    db.commit()
    db.refresh(payment)
    return payment


def verify_payment_as_exception(
    db: Session,
    payment_id: UUID,
    payload: PaymentExceptionVerify,
    actor_user_id: UUID | None,
) -> Payment:
    reason = payload.reason.strip()
    if not reason or payload.confirmation is not True:
        raise BookingError(
            "FINANCIAL_EXCEPTION_CONFIRMATION_REQUIRED",
            "A reason and explicit confirmation are required",
        )
    payment, booking = _lock_payment_and_booking(db, payment_id)
    if payment.status == "paid" and payment.requires_resolution:
        return payment
    if payment.status != "pending":
        raise BookingError(
            "PAYMENT_NOT_EXCEPTION_ELIGIBLE",
            "Only pending payments can be recorded as financial exceptions",
        )

    paid_before = _verified_paid_total(db, booking.id)
    inactive_booking = booking.status in {"expired", "cancelled", "rejected"}
    overpayment = payment.amount > max(
        booking.total_amount - paid_before,
        Decimal("0"),
    )
    if not inactive_booking and not overpayment:
        raise BookingError(
            "FINANCIAL_EXCEPTION_NOT_REQUIRED",
            "Use normal payment verification when no financial exception applies",
        )

    payment.status = "paid"
    payment.requires_resolution = True
    payment.resolution_reason = reason
    record_audit_event(
        db,
        actor_user_id=actor_user_id,
        action="payment.exception_recorded",
        resource_type="payment",
        resource_id=payment.id,
        details={
            "exception_type": _financial_exception_type(inactive_booking, overpayment),
            "reason": reason,
            "amount": str(payment.amount),
            "currency": payment.currency,
            "booking_id": str(booking.id),
            "verification": True,
        },
    )
    db.commit()
    db.refresh(payment)
    return payment


def list_payments(
    db: Session,
    page: int,
    size: int,
    status_filter: str | None = None,
    method_filter: str | None = None,
    search: str | None = None,
    booking_id: UUID | None = None,
    requires_resolution: bool | None = None,
) -> tuple[list[Payment], int, int]:
    expire_pending_bookings(db)
    query = (
        select(Payment)
        .join(Payment.booking)
        .options(
            joinedload(Payment.booking).selectinload(Booking.payments),
        )
    )
    count_query = select(func.count(Payment.id)).join(Payment.booking)
    if status_filter:
        query = query.where(Payment.status == status_filter)
        count_query = count_query.where(Payment.status == status_filter)
    if method_filter:
        query = query.where(Payment.method == method_filter)
        count_query = count_query.where(Payment.method == method_filter)
    if booking_id:
        query = query.where(Payment.booking_id == booking_id)
        count_query = count_query.where(Payment.booking_id == booking_id)
    if requires_resolution is not None:
        query = query.where(Payment.requires_resolution.is_(requires_resolution))
        count_query = count_query.where(
            Payment.requires_resolution.is_(requires_resolution)
        )
    if search and search.strip():
        term = f"%{search.strip()}%"
        search_filter = or_(
            Payment.transaction_reference.ilike(term),
            Booking.reference.ilike(term),
            Booking.contact_name.ilike(term),
            Booking.contact_email.ilike(term),
        )
        query = query.where(search_filter)
        count_query = count_query.where(search_filter)

    items = list(
        db.scalars(
            query.order_by(Payment.recorded_at.desc(), Payment.id)
            .offset((page - 1) * size)
            .limit(size)
        )
    )
    total = int(db.scalar(count_query) or 0)
    return items, total, math.ceil(total / size) if total else 0


def get_booking_payment_summary(
    db: Session,
    booking_id: UUID,
) -> tuple[Booking, tuple[Decimal, Decimal, Decimal, PaymentCompletionStatus]]:
    expire_pending_bookings(db)
    booking = db.scalar(
        select(Booking)
        .where(Booking.id == booking_id)
        .options(selectinload(Booking.payments))
    )
    if booking is None:
        raise BookingError("BOOKING_NOT_FOUND", "Booking not found")
    return booking, payment_summary(booking.total_amount, booking.payments)


def payment_summary(
    total_amount: Decimal,
    payments: list[Payment],
) -> tuple[Decimal, Decimal, Decimal, PaymentCompletionStatus]:
    paid_total = sum(
        (payment.amount for payment in payments if payment.status == "paid"),
        Decimal("0.00"),
    )
    outstanding = max(total_amount - paid_total, Decimal("0.00")).quantize(
        Decimal("0.01")
    )
    overpaid = max(paid_total - total_amount, Decimal("0.00")).quantize(
        Decimal("0.01")
    )
    if paid_total == 0:
        completion_status: PaymentCompletionStatus = "UNPAID"
    elif paid_total < total_amount:
        completion_status = "PARTIALLY_PAID"
    elif paid_total == total_amount:
        completion_status = "FULLY_PAID"
    else:
        completion_status = "OVERPAID"
    return paid_total, outstanding, overpaid, completion_status


def payment_actor_attributions(
    db: Session,
    payments: list[Payment],
) -> dict[UUID, tuple[str | None, str | None]]:
    payment_ids = [payment.id for payment in payments]
    if not payment_ids:
        return {}
    events = db.execute(
        select(
            AuditLog.resource_id,
            AuditLog.action,
            AuditLog.actor_user_id,
            User.email,
        )
        .outerjoin(User, User.id == AuditLog.actor_user_id)
        .where(
            AuditLog.resource_type == "payment",
            AuditLog.resource_id.in_(payment_ids),
            AuditLog.action.in_(
                {
                    "payment.created",
                    "payment.verified",
                    "payment.exception_recorded",
                }
            ),
        )
        .order_by(AuditLog.created_at)
    ).all()
    attributions: dict[UUID, list[str | None]] = {
        payment_id: [None, None] for payment_id in payment_ids
    }
    payment_statuses = {payment.id: payment.status for payment in payments}
    for resource_id, action, actor_user_id, email in events:
        if resource_id is None:
            continue
        display = email or (str(actor_user_id) if actor_user_id else None)
        values = attributions[resource_id]
        if action in {"payment.created", "payment.exception_recorded"}:
            if values[0] is None:
                values[0] = display
        if action in {"payment.verified", "payment.exception_recorded"} or (
            action == "payment.created" and payment_statuses[resource_id] == "paid"
        ):
            if values[1] is None:
                values[1] = display
    return {
        payment_id: (values[0], values[1])
        for payment_id, values in attributions.items()
    }


def _lock_payment_and_booking(
    db: Session,
    payment_id: UUID,
) -> tuple[Payment, Booking]:
    expire_pending_bookings(db)
    booking_id = db.scalar(
        select(Payment.booking_id).where(Payment.id == payment_id)
    )
    if booking_id is None:
        raise BookingError("PAYMENT_NOT_FOUND", "Payment not found")
    booking = db.scalar(
        select(Booking).where(Booking.id == booking_id).with_for_update()
    )
    if booking is None:
        raise BookingError("BOOKING_NOT_FOUND", "Booking not found")
    payment = db.scalar(
        select(Payment)
        .where(Payment.id == payment_id)
        .with_for_update()
    )
    if payment is None:
        raise BookingError("PAYMENT_NOT_FOUND", "Payment not found")
    return payment, booking


def _verified_paid_total(db: Session, booking_id: UUID) -> Decimal:
    value = db.scalar(
        select(func.coalesce(func.sum(Payment.amount), Decimal("0"))).where(
            Payment.booking_id == booking_id,
            Payment.status == "paid",
        )
    )
    return value if isinstance(value, Decimal) else Decimal(value or "0")


def _validate_payment_currency(booking: Booking, currency: str) -> None:
    if currency != booking.currency:
        raise BookingError(
            "PAYMENT_CURRENCY_MISMATCH",
            "Payment currency must match the booking currency",
        )


def _booking_hold_is_valid(booking: Booking, now: datetime) -> bool:
    expires_at = booking.expires_at
    if expires_at is None:
        return False
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    return expires_at > now


def _confirm_booking_after_full_payment(
    db: Session,
    booking: Booking,
    actor_user_id: UUID | None,
) -> None:
    booking.status = "confirmed"
    booking.expires_at = None
    db.add(
        BookingStatusHistory(
            booking_id=booking.id,
            old_status="pending",
            new_status="confirmed",
            actor_user_id=actor_user_id,
            reason="Fully paid",
            changed_at=datetime.now(timezone.utc),
        )
    )
    record_audit_event(
        db,
        actor_user_id=actor_user_id,
        action="booking.status_changed",
        resource_type="booking",
        resource_id=booking.id,
        details={
            "from": "pending",
            "to": "confirmed",
            "reason": "fully_paid",
        },
    )


def _flag_paid_payments_for_resolution(
    db: Session,
    booking: Booking,
    reason: str,
    actor_user_id: UUID | None,
) -> None:
    payments = list(booking.payments)
    if not payments:
        payments = list(
            db.scalars(
                select(Payment)
                .where(Payment.booking_id == booking.id)
                .with_for_update()
            )
        )
    for payment in payments:
        if payment.status != "paid" or payment.requires_resolution:
            continue
        payment.requires_resolution = True
        payment.resolution_reason = reason
        record_audit_event(
            db,
            actor_user_id=actor_user_id,
            action="payment.exception_flagged",
            resource_type="payment",
            resource_id=payment.id,
            details={
                "reason": reason,
                "booking_id": str(booking.id),
            },
        )


def _payment_fingerprint(operation: str, payload: PaymentCreate) -> str:
    values = payload.model_dump(mode="json", exclude={"confirmation"})
    values["amount"] = format(payload.amount.quantize(Decimal("0.01")), "f")
    canonical = json.dumps(
        {"operation": operation, "payload": values},
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _find_idempotent_payment(
    db: Session,
    idempotency_key: str,
    fingerprint: str,
) -> Payment | None:
    key = idempotency_key.strip()
    if not key:
        raise BookingError("IDEMPOTENCY_KEY_REQUIRED", "Idempotency key is required")
    payment = db.scalar(
        select(Payment).where(Payment.idempotency_key == key)
    )
    if payment is not None:
        if payment.idempotency_fingerprint != fingerprint:
            raise BookingError(
                "IDEMPOTENCY_KEY_REUSED",
                "Idempotency key was already used with a different request",
            )
        return payment
    return None


def _ensure_transaction_reference_is_new(
    db: Session,
    transaction_reference: str | None,
) -> None:
    if transaction_reference and db.scalar(
        select(Payment.id).where(
            Payment.transaction_reference == transaction_reference
        )
    ):
        raise BookingError(
            "TRANSACTION_REFERENCE_EXISTS",
            "Transaction reference already exists",
        )


def _financial_exception_type(inactive_booking: bool, overpayment: bool) -> str:
    if inactive_booking and overpayment:
        return "inactive_booking_and_overpayment"
    if inactive_booking:
        return "inactive_booking"
    return "overpayment"


def _commit_payment(
    db: Session,
    payment: Payment,
    idempotency_key: str,
    fingerprint: str,
    transaction_reference: str | None,
) -> Payment:
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        existing = db.scalar(
            select(Payment).where(Payment.idempotency_key == idempotency_key.strip())
        )
        if existing is not None:
            if existing.idempotency_fingerprint != fingerprint:
                raise BookingError(
                    "IDEMPOTENCY_KEY_REUSED",
                    "Idempotency key was already used with a different request",
                ) from None
            return existing
        if transaction_reference and db.scalar(
            select(Payment.id).where(
                Payment.transaction_reference == transaction_reference
            )
        ):
            raise BookingError(
                "TRANSACTION_REFERENCE_EXISTS",
                "Transaction reference already exists",
            ) from None
        raise
    db.refresh(payment)
    return payment
