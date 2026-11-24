# 09 - Development Roadmap

Implement in small, reviewable increments. Do not start production deployment
until the core booking system and all MVP acceptance criteria are verified.

## Current status (audited 2026-11-24)

The local application is a working development build, not a complete business
application. The backend and admin screens cover most internal operations, and
the public site supports tour discovery and guest booking. The gaps below are
based on the current source and tests, not on planned features.

| Module | Backend API | Database model | Admin UI | Public/customer UI | Tests and remaining gaps |
| --- | --- | --- | --- | --- | --- |
| Authentication and RBAC | Central permission map protects business APIs. `ADMIN` and `SUPER_ADMIN` can provision `CUSTOMER` users; customer account creation is audited. Admin/Staff can link or unlink a customer profile to an active CUSTOMER account, with actor/customer/user audit details. Customer profile `user_id` remains unique. | Existing users, roles, refresh-token revocation and audit logs; no schema change was needed for customer history or linking. | Admin can provision CUSTOMER accounts; Admin/Staff can link an account while creating/editing a CRM profile. | Customer sign-in uses existing authentication and refresh-token APIs; no public registration or password recovery. | Backend account/linking and role tests pass. Admin test suite: 11 passed; production build passes. |
| Tour management | Public/admin lists and create/patch. Public details and search expose published tours only; search supports keyword, destination, currency-specific price, departure dates, duration, traveler count, availability, sorting and pagination. | Tour fields, slug uniqueness and status. No tour image or category model. | List includes all statuses and supports create/edit. | Home, URL-synchronized public search/listing and existing detail/booking flow. Cards show per-currency starting prices and eligible departure summaries without conversion. | Catalog API tests cover combined filters on one departure, publication/departure eligibility, hold expiry, price sorting and pagination. User tests cover query persistence, clear, loading/empty and stale-response behavior. No image/category content exists. |
| Tour departures | Public bookable list/detail; Admin/Super Admin list/create/update; Staff read-only. | Dates, capacity, available seats, fixed-precision price and status. | List, create and update for Admin/Super Admin. | Tour detail lists upcoming bookable departures and price/seats. | Catalog tests cover public filtering and detail, but do not fully cover departure CRUD and boundary cases. PostgreSQL booking-concurrency coverage is maintained separately. |
| Booking management | Create, paginated list/detail, confirm/cancel/reject, status history and customer-link checks. Capacity is reserved and released transactionally. Pending bookings hold seats for a configurable 30-minute default and expire automatically. Only full verified payment can auto-confirm a pending booking while its hold is valid; partial payments do not extend holds. Staff cannot confirm bookings with verified paid funds. | Bookings, travelers, status history and payment relation; booking creation, edits and status changes write audit events. Migration `0009` adds the pending-hold deadline. | Admin/Super Admin retain full booking operations; Staff can use operational create/edit/status actions. Payment history and balance summary are available in booking details. | Guest booking remains available. Authenticated CUSTOMER bookings use the backend-linked customer profile; no guest booking is auto-linked by email or phone. | Backend suite: 98 passed, 6 skipped, including customer history isolation, guest behavior, role access, hold expiration and payment concurrency. |
| Customer CRM and booking history | Staff/admin CRM list/search/create/read/update and audited account linking. CUSTOMER users can list and view only bookings belonging to their linked profile; detail includes departure, passengers, status history and recorded payments. | Existing unique `customers.user_id`, booking/traveler/history/payment relations; no schema migration added. | CRM account selector lists available active CUSTOMER accounts and supports link/unlink. | Customer sign-in, paginated My Bookings, upcoming/completed groupings and per-booking detail. No public registration, guest conversion or password recovery. | Backend ownership, IDOR, duplicate linking, guest booking, and Admin/Staff access tests pass. Admin: 11 tests; User: 9 tests. Both builds pass. |
| Itinerary management | Staff read-only; Admin/Super Admin CRUD. Public tour detail returns items ordered by day and sequence. | Itinerary entries with positive day/sequence and per-day uniqueness. | Select tour and create/edit/delete itinerary items for Admin/Super Admin. | Tour detail displays itinerary. | Existing API tests pass; no frontend component tests. |
| Payment management | Admin/Super Admin can list, search, filter, record and verify payments, and explicitly record reasoned financial exceptions. Booking-scoped summaries use authoritative `Decimal` calculations. Staff cannot access payment APIs. Customer payment history is ownership-scoped and read-only; internal notes, reasons and actor attribution are omitted. | Migration `0010_payment_management` adds internal notes, exception-resolution metadata and persistent idempotency fields; existing payment statuses and records are preserved. No refund ledger. | Payments page supports search, status/method/resolution filters, pagination, pending-payment recording, verification and confirmed exception recording. Booking details show payment history and financial summaries. | Customer booking detail shows recorded payment history, verified amount, outstanding balance and completion status. No payment processing or gateway. | Backend: 98 passed, 6 skipped. Admin: 11 passed and production build passed. User: 9 passed and production build passed. Isolated PostgreSQL migration downgrade/re-upgrade and concurrency run: 6 passed. Do not add deposit, refund or exception-resolution policy without approval. |
| Article/blog management | Public published-article list/detail; Admin/Super Admin list/read/create/update and category management. Staff is denied. | Articles, categories, publication status/time and SEO fields. | Article create/edit and category create for Admin/Super Admin. | No article or blog pages. | 4 API tests. Add public article pages and frontend tests. |
| Guide management | Staff read-only; Admin/Super Admin list/search/create/update; assignment writes are Admin/Super Admin only. | Guides and departure assignments. | Guide list/create/edit and assignment management for Admin/Super Admin. | Not applicable to the current public scope. | Operations tests cover workflows and authorization; Staff access is covered by the RBAC tests. |
| Supplier and expense management | Admin/Super Admin supplier and expense CRUD/report access; Staff is denied. Expense reports remain grouped without combining currencies/statuses. | Suppliers and fixed-precision tour expenses. | Supplier, expense and expense-report screens for Admin/Super Admin. | Not applicable. | Operations tests cover validation, reports and authorization; Staff denial is covered by RBAC tests. |
| Admin dashboard | Staff summary includes operational booking counts and upcoming open departures only. Admin/Super Admin additionally receive payment totals and departure prices. | Uses booking, departure and payment data. | Role-aware dashboard summary with loading/error/empty states. | Not applicable. | Dashboard and RBAC tests cover summaries, authorization and Staff financial-field omission. |
| Public user website | Public tour/departure and article APIs exist; booking request is public. Tour search is server-side and availability does not reserve seats. Customer booking history/detail endpoints require an authenticated CUSTOMER role and resolve ownership from the linked profile. | Reuses tour, departure, booking, payment and customer models; no search migration. | Not applicable. | Home, filterable URL-synchronized tour search/list, existing detail/booking flow, guest booking/confirmation, customer sign-in, booking history and detail. Blog, contact and itinerary portal remain open. | Frontend tests cover URL state, clear filters, loading/empty states, stale results and API filters. |

## Prioritized implementation backlog

### Approved STAFF access policy

The Staff role is limited to viewing tours and departures; operating bookings
and customer records; and viewing itineraries, guides and tour assignments.
Staff cannot change tours, departures, itineraries, guides or assignments, and
cannot access articles, payments, suppliers, expenses, reports, user
management or system settings. Booking responses and dashboard summaries omit
financial values for Staff. Backend permissions enforce this policy; the Admin
frontend mirrors it for navigation and action visibility.

### P0 - Critical

1. **DONE - Complete tour management.** Admin tour create/list worked, but edit
   was missing despite an existing backend patch endpoint. The Admin edit
   workflow and focused service/API tests are implemented in this increment.
2. **DONE - Define and implement RBAC/user administration.** The approved Staff
   policy is enforced by centralized backend permissions; Admin and Super
   Admin account-management scope is enforced in the API; audit events and the
   Admin user-management screen are implemented. PostgreSQL migrations through
   `0009` and isolated booking concurrency verification passed on 2026-11-24.
3. **DONE - Set the pending-booking seat-hold and cancellation rules.** Approved
   policy is implemented: pending bookings hold seats for a configurable
   30-minute default; confirmation retains held seats, cancellation and rejection
   release them, and automatic expiration releases only still-pending holds.
   Status changes are audited, expiration processing is duplicate-safe, and only
   full verified payments can auto-confirm while the hold is valid. Payments
   against inactive bookings require an explicit financial exception.
4. **Verify MVP booking acceptance end-to-end.** Unit/API tests cover capacity,
   booking transitions/audit history, Staff booking operations, financial-field
   omission, Admin processing and customer-owned history. Migration rollback,
   re-upgrade and PostgreSQL concurrency tests passed against an isolated
   database. Remaining MVP acceptance work is tracked in P1; do not use booking
   totals as collected cash.

### P1 - Required MVP completion

1. **DONE - Implement Payment Management.** Admin/Super Admin payment listing,
   pending-payment recording, verification, reasoned financial exceptions,
   booking history and authoritative balance summaries are implemented.
   Customer payment history is read-only and ownership-scoped. No gateway,
   refunds or exception-resolution workflow is included.
2. Add a richer Admin customer detail view.
3. **DONE - Complete public tour search and filtering.** Keyword, destination,
   currency-specific price, date range, duration, traveler-count and
   availability criteria are combined against one departure, with server-side
   sorting/pagination and URL-synchronized customer filters. No migration or
   currency conversion was added. Search availability remains a snapshot; the
   booking transaction remains authoritative.
4. Add public article/blog listing and detail pages backed by published-only
   endpoints.
5. Add integration tests for departure CRUD and page/component tests for the
   highest-risk booking screens. Payment API authorization, booking payment
   display and payment concurrency now have coverage.
6. Resolve operational abuse controls for login and unauthenticated booking
   requests before exposing the service publicly.

### P2 - Advanced or policy-dependent

1. Customer account portal enhancements: profile and itinerary. Own booking history and recorded payment status are implemented for linked CUSTOMER accounts.
   Guest lookup must use a secure reference plus an additional verification
   mechanism if introduced.
2. Online payment gateway integration and refunds. Define an auditable refund
   ledger and business policy first; never collect card details directly.
   Deposit thresholds, installment allocation, exception resolution and late
   payment handling policies also require separate approval.
3. Tour image upload/storage and included/excluded service content.
4. Advanced reports, including any revenue recognition. Revenue is not
   derivable from booking totals or payment records without a product policy.
5. Email notifications, advanced CRM, and other enhancements not required for
   the currently documented MVP.

## Phase progress

- **Phase 0 - Environment and skeleton:** Compose-based local development,
  backend and both frontends exist. Verify the supported Windows/WSL/Docker
  prerequisites on the target machine before relying on Docker Desktop support.
- **Phase 1 - Database foundation:** SQLAlchemy models and Alembic migrations
  now include additive migrations `0008_audit_logs` and
  `0010_payment_management`. On 2026-11-24, all migrations
  through migration `0010_payment_management` were applied successfully
  against a fresh isolated tmpfs PostgreSQL 16 test database; migrations
  `0010`, `0009` and `0008` were downgraded to `0007_articles_categories` and
  re-upgraded to head successfully. Six isolated PostgreSQL concurrency tests
  passed. The existing development database was not used.
- **Phase 2 - Backend foundation:** Health, authentication, centralized
  permission checks, user/role administration and audit logging are
  implemented.
- **Phase 3 - Core business APIs:** Tours, departures, customers, bookings,
  status history and payment management exist. Staff booking and CRM
  permissions are implemented. Migration `0009` adds configurable pending
  booking holds and expiration; linked-customer booking history and profile
  account linking are implemented without a schema change. Migration `0010`
  adds payment idempotency and financial-exception metadata. Public tour
  search reuses the existing models and seat accounting; no search migration
  was required. `BUSINESS_TIMEZONE` centralizes date-only tour eligibility and
  is validated as an IANA timezone; UTC hold/payment/audit timestamps are
  unchanged. Backend suite: 113 passed, 6 skipped. All six skips are the
  optional `test_postgres_booking_concurrency.py` cases, which require
  `TEST_DATABASE_URL`; this phase's isolated PostgreSQL rerun was unavailable
  because Docker is not installed in the current environment.
- **Phase 4 - Admin frontend:** Core Admin screens, tour editing, and user/role
  management are implemented. Staff navigation and actions are permission
  gated. Admin can provision CUSTOMER accounts and staff can link/unlink
  profiles. Payment management and booking-level payment history are
  implemented for Admin/Super Admin. The Admin Vitest suite passes: 11 tests.
  The production build passes.
- **Phase 5 - User frontend:** Public tour discovery and guest booking work.
  Linked CUSTOMER account sign-in, own booking list/detail and recorded payment
  history and summary views are implemented. Tour discovery now supports
  URL-persistent filters, sorting, pagination, currency-specific starting
  prices and eligible departure summaries. Public article presentation and
  itinerary portal remain open. The User Vitest suite passes: 16 tests and the
  production build passes. No public registration, password recovery or guest
  booking conversion is provided.
- **Phase 6 - Operations and content:** Itineraries, guides, assignments,
  suppliers, expenses and Admin article CMS exist. Public article presentation
  remains open.
- **Phase 7 - Reporting and hardening:** Dashboard/expense reports, security
  hardening and backup/restore procedure exist. Final payment-module
  verification: backend `98 passed, 6 skipped`; Admin `11 passed` with
  production build; User `9 passed` with production build; isolated PostgreSQL
  migration downgrade/re-upgrade and concurrency tests `6 passed`. The isolated
  test stack is separate from the development database, and no existing
  development or production database was modified. Login/booking abuse controls
  and remaining product policies are open.
  Production Compose and deployment documentation are templates only.

Production deployment is intentionally blocked until the core booking system,
all MVP acceptance criteria and deployment prerequisites are verified. No
production services have been started. See
[11_PRODUCTION_DEPLOYMENT.md](./11_PRODUCTION_DEPLOYMENT.md) for the future
deployment prerequisites and
[07_WINDOWS10_WSL2_DOCKER.md](./07_WINDOWS10_WSL2_DOCKER.md) for local runtime
and backup/restore guidance.
