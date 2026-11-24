# 05 – Admin Frontend Specification

## Stack
Vue 3, TypeScript, Vite, Vuetify, Vue Router, Pinia, Axios.

## Purpose
Internal application for authorized company staff.

## Main navigation
- Dashboard
- Tours
- Departures
- Bookings
- Customers
- Itineraries
- Payments
- Articles
- Guides
- Tour assignments
- Suppliers
- Tour expenses
- Reports
- Users and roles
- Settings

## MVP screens
1. Login.
2. Dashboard with booking counts, upcoming departures and payment totals grouped by currency and payment status. Booking value is not presented as collected payment or revenue.
3. Tour list, search, filters, create/edit/detail.
4. Departure list and capacity management.
5. Booking list, detail, status history and confirmation/cancellation actions.
6. Customer list and profile with booking history.
7. Itinerary editor for activities grouped by tour day and sequence.
8. Guide directory with contact details and optional linked user ID.
9. Tour assignments managed per departure with a required role and status.
10. Supplier directory with service categories.
11. Tour expenses recorded per departure, with an optional supplier and supporting note.
12. Article CMS for reusable categories and article create/edit workflows.
13. Expense report showing recorded totals grouped by departure, category, currency and expense status.
14. Payment list with search, status/method/resolution filters and server-side
    pagination; manual pending-payment recording; explicit verification and
    confirmed financial-exception workflows.

## UI requirements
- Responsive desktop-first layout with usable tablet behavior.
- Reusable page layout, navigation, tables, dialogs and form components.
- Consistent loading, empty, success and error states.
- Confirm destructive or irreversible actions.
- Use server-side pagination for large tables.
- Use form validation and clear field-level error messages.
- Do not hardcode API response data in production views.
- Payment details show booking total, verified amount, outstanding balance,
  overpaid amount and payment-completion status separately from booking status.
- Booking details include the paginated payment history. Display payment
  method, reference, recorded date, status, recorder/verifier attribution,
  internal notes and any manual-resolution flag/reason.
- Only ADMIN/SUPER_ADMIN can use payment actions. Recording an exception
  requires an administrative reason and explicit confirmation. Never offer
  payment editing/deletion, automatic refunds or gateway processing here.

## Security
- Hide navigation items based on role for usability.
- Treat frontend route guards as UX only; backend remains the security authority.
- Clear user state on logout and handle expired sessions safely.
- Do not store sensitive secrets in browser code.
- ADMIN/SUPER_ADMIN provision CUSTOMER login accounts. ADMIN/STAFF link or
  unlink existing customer profiles to active CUSTOMER accounts through CRM;
  the backend audits those account changes.

## Frontend structure
- `components/`: reusable UI.
- `layouts/`: admin shell and auth shell.
- `views/`: route-level pages.
- `router/`: routes and guards.
- `stores/`: Pinia stores.
- `services/`: API clients.
- `types/`: shared TypeScript contracts.
- `composables/`: reusable composition logic.
- `utils/`: formatting and helpers.
