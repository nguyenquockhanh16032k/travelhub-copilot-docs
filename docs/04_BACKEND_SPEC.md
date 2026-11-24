# 04 – Backend Specification

## Stack
Python 3.12+, FastAPI, SQLAlchemy 2.x, Pydantic, Alembic, PostgreSQL, Pytest.

## Layer responsibilities
- `api/v1`: HTTP endpoints, dependencies, status codes.
- `schemas`: Pydantic request and response models.
- `services`: business rules and orchestration.
- `repositories`: database queries and persistence.
- `models`: SQLAlchemy entities.
- `core`: settings, security, logging and permissions.
- `db`: engine, session and migration integration.

## Required initial modules
1. Auth: login, refresh, current user, logout/revocation strategy.
2. Users and roles.
3. Tours.
4. Tour departures.
5. Customers.
6. Bookings.
7. Payments.
8. Itineraries.
9. Articles.
10. Operations and reports.

## API conventions
Prefix: `/api/v1`.

Examples:
- `POST /auth/login`
- `POST /auth/refresh`
- `GET /auth/me`
- `GET /tours`
- `GET /admin/tours` (staff only; includes tours in every status)
- `GET /tours/{tour_id}`
- `POST /tours`
- `GET /departures`
- `POST /departures`
- `GET /bookings`
- `POST /bookings`
- `POST /bookings/{booking_id}/confirm`
- `POST /bookings/{booking_id}/cancel`
- `GET /customers`
- `GET /customers/me/bookings` (authenticated CUSTOMER; paginated)
- `GET /customers/me/bookings/{booking_id}` (authenticated CUSTOMER; own profile only)
- `GET /customers/linkable-accounts` (staff only; paginated CUSTOMER accounts)
- `POST /payments`
- `GET /payments` (ADMIN/SUPER_ADMIN; filtered and paginated)
- `POST /payments/exceptions` (ADMIN/SUPER_ADMIN; confirmed financial exception)
- `POST /payments/{payment_id}/verify` (ADMIN/SUPER_ADMIN)
- `POST /payments/{payment_id}/financial-exception` (ADMIN/SUPER_ADMIN)
- `GET /dashboard/summary` (staff only)
- `GET /tours/{tour_id}/itineraries` (staff only)
- `POST /tours/{tour_id}/itineraries` (staff only)
- `PATCH /tours/{tour_id}/itineraries/{itinerary_id}` (staff only)
- `DELETE /tours/{tour_id}/itineraries/{itinerary_id}` (staff only)
- `GET /admin/departures` (staff only; includes departures for tours in every status)
- `GET /guides` and `POST /guides` (staff only; paginated list supports name/contact search)
- `PATCH /guides/{guide_id}` (staff only)
- `GET /departures/{departure_id}/assignments` (staff only; paginated)
- `POST /departures/{departure_id}/assignments` (staff only)
- `PATCH /departures/{departure_id}/assignments/{assignment_id}` (staff only)
- `DELETE /departures/{departure_id}/assignments/{assignment_id}` (staff only)
- `GET /suppliers` (staff only; paginated and searchable)
- `POST /suppliers` and `PATCH /suppliers/{supplier_id}` (staff only)
- `GET /departures/{departure_id}/expenses` (staff only; paginated)
- `POST /departures/{departure_id}/expenses` and `PATCH /departures/{departure_id}/expenses/{expense_id}` (staff only)
- `GET /categories` (public)
- `POST /categories` and `PATCH /categories/{category_id}` (staff only)
- `GET /articles` and `GET /articles/{slug}` (published articles only)
- `GET /admin/articles` and `GET /admin/articles/{article_id}` (staff only)
- `POST /articles` and `PATCH /articles/{article_id}` (staff only)
- `GET /reports/expenses` (staff only; paginated totals grouped by departure, category, currency and expense status)

Use pagination for collection endpoints. Validate sorting and filtering fields against allowlists. Use consistent error response structures.

## Public tour search

`GET /tours` is the single public tour discovery endpoint. It returns published
tours and pagination metadata (`items`, `total`, `page`, `size`, `pages`), plus
the eligible currency codes available for the active non-price filters. Search
parameters are:

- `keyword` and `destination` (case-insensitive substring matches).
- `min_price`, `max_price`, and `currency`.
- Inclusive `departure_from` and `departure_to` dates.
- `min_duration` and `max_duration` in days.
- `traveler_count` and `available_only`.
- `sort` and server-side `page`/`size` (`size` is capped at 100).

Every departure-level criterion is applied to the same departure row. A
departure is eligible when its tour is published, its status is `open`, its
start date is on or after the configured business date, and it has sufficient
available seats. Price filters and price sorting require an uppercase ISO 4217
`currency`; prices are never compared or converted across currencies. With no
currency selection, results retain one lowest starting price per currency.
The displayed starting prices and next departure are calculated from
departures matching the active filters. Availability is a search-time view,
not a reservation or guarantee; booking creation remains authoritative.

Search expires only expired pending holds associated with candidate departures
before calculating seat availability. It does not run a global expiration
sweep, reserve seats, reactivate bookings, or expose booking/customer data.
`BUSINESS_TIMEZONE` controls date-only eligibility for search, public departure
views, tour detail and booking creation; it defaults to
`Asia/Ho_Chi_Minh` and must be a valid IANA timezone. Holds, payments and audit
timestamps remain UTC instants. No schema or index migration is currently
required; revisit indexing based on production-like query plans and data volume.

Booking responses include traveler details and the auditable status history.
Customer history resolves `customers.user_id` from the authenticated CUSTOMER
user; the client cannot select a customer ID. Detail responses include tour
departure information, travelers, status transitions and recorded payment
rows, and omit internal notes and booking contact fields. Guest bookings remain
unlinked unless staff explicitly link an existing customer profile; do not
match or link bookings by email or phone.
Only ADMIN/SUPER_ADMIN can provision CUSTOMER login users. ADMIN/STAFF can link
or unlink existing customer profiles to active CUSTOMER accounts. The existing
unique `customers.user_id` constraint enforces one-to-one linking; account
creation and link changes are audited.
The dashboard summary reports booking counts, upcoming open departures, and payment totals grouped by currency and payment status. It does not interpret booking values as payments or revenue.
Public `GET /tours/{tour_id}` responses include itinerary items ordered by day number and sequence. Itinerary sequence values are unique within each tour day, and the same items are editable only by staff.
Guide assignment roles and statuses are required free-text values because the product specifications do not define allowed enumerations. Public departure listing remains limited to published tours with open departures; the separate admin list includes all statuses.
Expense category and status are required free-text values because no enumerations are specified. Expense amounts use fixed-precision decimals and include a currency code; they are internal operational costs and are not reported as payments or revenue.
Article publication status uses draft, published or archived. Only published articles appear in public article endpoints. Publishing sets publication time; archiving removes publication time from public visibility.
The expense report summarizes recorded expense rows without interpreting free-text statuses as payment or recognition states. Totals remain separate by currency; they are not revenue or cash-payment figures.

## Payment workflow

Payment and booking status are independent. `paid` means verified receipt, not
that a booking is fully paid or confirmed. Keep the existing payment statuses:
`pending`, `paid`, `failed` and `refunded`.

All payment amounts, totals and balances use `Decimal`/`NUMERIC(14,2)`. For a
booking, calculate:

- `verified_paid_amount` as the sum of its `paid` payment rows.
- `outstanding_balance` as `max(booking_total - verified_paid_amount, 0)`.
- `overpaid_amount` as `max(verified_paid_amount - booking_total, 0)`.
- `payment_completion_status` as `UNPAID`, `PARTIALLY_PAID`, `FULLY_PAID` or
  `OVERPAID`, derived from those values rather than stored as a payment status.

Normal payment creation requires a persistent `Idempotency-Key` header and
rejects reuse with a different request payload. A pending payment does not
reduce the outstanding balance; normal verification rechecks the balance while
holding a lock on the booking. Verification is idempotent. Transaction
references remain unique when provided.

Normal payment creation and verification reject amounts that exceed the current
outstanding balance. New normal payments are blocked when no balance remains.
Multiple partial payments are allowed. A partial paid payment does not
automatically confirm a pending booking. A fully paid pending booking may be
confirmed automatically only while its seat-hold deadline remains valid.
ADMIN/SUPER_ADMIN may explicitly confirm a partially paid booking while its
hold remains valid; STAFF cannot perform that confirmation. Partial payments
never extend the hold. Confirmed bookings may accept additional payments.

For money actually received against an expired, cancelled or rejected booking,
or in excess of the outstanding balance, ADMIN/SUPER_ADMIN may use the explicit
financial-exception workflow. It requires an administrative reason and explicit
confirmation, records the full amount as `paid`, and sets `requires_resolution`
with an internal reason. It preserves the booking status and seat allocation;
it never reactivates a booking, reserves seats, automatically refunds money or
transfers excess to another booking. Existing paid amounts are flagged for
manual resolution when a partially paid booking expires, is cancelled or is
rejected. No exception-resolution or refund operation is implemented.

Payment creation, verification and exception events are audited with the
responsible user. Admin payment responses may include internal notes, exception
reasons, and recorder/verifier attribution. CUSTOMER responses are scoped to
the authenticated user's linked customer profile and omit those internal
fields. STAFF cannot list, create, verify or manage payment exceptions.
Configurable deposit thresholds, installment allocation, refund policy and
exception resolution remain future policy decisions.

## Security
- Hash passwords using a maintained password hashing algorithm/library.
- Keep JWT signing secrets in environment variables.
- Production startup rejects the example JWT secret and requires a unique signing key of at least 32 characters.
- Set token expiry and refresh strategy.
- Enforce role and resource-level authorization on every protected endpoint.
- A CUSTOMER can access only bookings attached to the profile linked to their
  authenticated user; foreign booking IDs return not found.
- Validate upload type, size and storage location.
- Configure CORS explicitly.
- Never log passwords, access tokens or payment secrets.

## Booking business logic
- A booking must reference an existing published tour departure that is open and has not started.
- Validate passenger count and departure capacity.
- Reserve capacity atomically.
- Record every status transition.
- Cancellation policy must be explicit and configurable; do not invent refund amounts.
- Payment records are immutable financial events; corrections should use reversal/refund records, not silent edits.
- Distinguish booking value, collected payment and recognized revenue in reports.

## Quality requirements
- Type hints for public functions.
- Pydantic validation for all external input.
- Unit tests for services.
- Integration tests for database-dependent workflows.
- Test authorization boundaries.
- Test overbooking concurrency against PostgreSQL using
  `docker-compose.test.yml` and the documented integration-test command.
- Generate and inspect OpenAPI documentation.
