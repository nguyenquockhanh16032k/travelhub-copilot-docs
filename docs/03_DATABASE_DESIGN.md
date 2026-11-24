# 03 – Database Design

## Database
PostgreSQL. Use SQLAlchemy 2.x models and Alembic migrations.

## Initial entities
### Identity and access
- `users`: login identity, password hash, email, active status.
- `roles`: role code and description.
- `user_roles`: many-to-many user-role association.

### CRM
- `customers`: customer profile and contact details.
- Keep customer profile separate from login user. A customer may book as a guest; an account can optionally be linked later.

### Tours
- `tours`: reusable tour product, title, slug, description, duration, destination, status.
- `tour_departures`: one scheduled departure with start/end date, capacity, available seats or booked-seat calculation, price and status.
- `tour_images`: image metadata and sort order.
- `tour_itineraries`: day number, sequence, activity, time, location and description. Day and sequence numbers start at 1; each sequence is unique within a tour day.

### Booking and payment
- `bookings`: booking reference, departure, booking contact, status, totals and notes.
- `booking_customers`: travelers associated with a booking, including traveler type and required traveler details.
- `booking_status_history`: old status, new status, actor, timestamp and reason.
- `payments`: amount, currency, method, status, transaction reference, internal
  notes, resolution-required flag/reason, persistent idempotency key and
  request fingerprint, and timestamps.
- Payment statuses remain `pending`, `paid`, `failed` and `refunded`.
  `requires_resolution` is independent of payment status and marks actual
  receipts requiring administrative follow-up.
- Idempotency keys are unique for new requests; historical payment rows may
  have no key. Transaction references remain unique when provided.
- Add refund records or a clear refund ledger before implementing real refunds.

### Content
- `articles`: title, slug, body, cover image, status, SEO fields, author and publication time. Status values are draft, published or archived.
- `categories`: reusable content categories.

### Operations
- `guides`: full name and optional email/phone contact details; optionally link to a user account.
- `tour_assignments`: departure, guide, free-text assignment role and status. Role and status are required; the system does not impose an undocumented vocabulary.
- `suppliers`: supplier name and service category.
- `tour_expenses`: departure, supplier (optional), expense category, fixed-precision amount and currency, free-text status and optional supporting note.

## Core relationships
- One tour has many departures.
- One tour has many itinerary items.
- One departure has many bookings.
- One booking belongs to one departure.
- One booking has many travelers.
- One booking has many payment records.
- One user can create many bookings.
- One departure can have multiple guide assignments.
- One departure can have many expenses.

## Data rules
- Use UUID primary keys.
- Use `NUMERIC(14,2)` or an appropriate fixed precision for money; never float/double for money.
- Store timestamps in UTC using timezone-aware types.
- Add `created_at` and `updated_at` to business tables.
- Use foreign keys and indexes for common lookup fields.
- Use unique constraints for email (where required), tour slug and booking reference.
- Use Alembic migrations; do not edit production schema manually.
- Prefer archive/soft-delete for records with financial or audit history.
- Do not store card numbers or sensitive payment credentials.
- Keep payment notes and exception reasons internal to authorized payment
  administrators; customer responses must omit them.

## Booking capacity integrity
Prevent overbooking using a database transaction and row-level locking or another concurrency-safe strategy.
Do not rely only on a frontend availability check.
Define one source of truth for reserved seats and release seats when cancellation is valid.
Write tests for two concurrent booking requests competing for the final seats.

## Payment integrity
- Store and calculate money with `NUMERIC(14,2)`/`Decimal`; never use floats.
- A `paid` payment is verified receipt. Only `paid` rows contribute to the
  booking's verified amount; pending, failed and refunded rows do not.
- Derive unpaid/partial/full/overpaid completion and outstanding/overpaid
  amounts from the booking total and its verified payment rows. These are
  summaries, not additional payment statuses.
- Normal payments cannot exceed the current outstanding amount. Revalidate
  pending payments during verification because another payment may have been
  verified since they were recorded.
- Financial exceptions persist as a paid payment plus the separate
  `requires_resolution` flag and an internal reason. Do not change the payment
  status vocabulary to represent exceptions.
- Lock the booking before payment writes/verifications so concurrent payments
  cannot exceed the total and payment verification serializes with hold expiry.
- Do not rewrite or delete historical financial rows. Do not automatically
  refund, transfer overpayments, reactivate expired bookings or allocate seats
  through an exception workflow.
- No deposit threshold or allocation rule is defined; deposits, installments,
  refunds and exception resolution require a separately approved policy.

## Seed data
Create development-only seed data:
- one SUPER_ADMIN user with credentials documented only in local setup instructions;
- sample tours and departures;
- sample customers and bookings.
Never use default development credentials in production.
