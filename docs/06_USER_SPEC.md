# 06 – Public and Customer Frontend Specification

## Stack
Vue 3, TypeScript, Vite, Vuetify, Vue Router, Pinia, Axios.

## Purpose
Public-facing website where visitors discover tours and submit bookings.

## Main pages
- Homepage.
- Tour listing.
- Tour detail.
- Search and filters.
- Booking form.
- Booking confirmation page.
- Login/register (optional for MVP if guest booking is supported).
- Customer profile.
- My bookings.
- My payments.
- My itinerary.
- Travel articles/blog.
- Contact page.

## Tour listing
The public tour listing supports keyword, destination, currency-specific price
range, departure date range, duration range, traveler count, availability,
sorting and server-side pagination. Filters, sorting and page are synchronized
with URL query parameters so search can be bookmarked and browser navigation
restores the prior state. Keyword requests are debounced and stale responses
must not replace newer results.

Only published tours are returned. Departure-level criteria must match one
eligible departure; an available departure is open, not past the configured
business date and has enough seats for the requested travelers. Search does
not reserve seats, and availability may change before booking. Cards use
backend-provided tour data, show starting prices separately by currency, and
show the next matching eligible departure. Price comparisons require a
selected ISO currency; no currency conversion is presented. VND may be shown
as the preferred currency option, but is not preselected and does not limit an
unfiltered result.

Tours currently have no image or category fields, so the listing must not
fabricate either. The detail and booking flow remains the existing flow.

## Tour detail
Display tour description, images, duration, itinerary, included/excluded services, departure dates, remaining capacity where appropriate and price.

## Booking flow
1. Select a departure.
2. Enter contact details.
3. Enter traveler details and passenger counts.
4. Review booking summary.
5. Submit booking request.
6. Show booking reference and next steps.

Do not claim a booking is confirmed until the backend confirms it.
Do not collect card details directly unless a compliant payment provider integration is implemented.

## Customer privacy
- A customer must only see their own bookings and personal information.
- An authenticated CUSTOMER can view bookings linked to the profile assigned
  to their account, including booking detail, passenger information, status
  history, booking total, verified payment amount, outstanding balance,
  payment-completion status and recorded payment history. Payment completion is
  separate from booking confirmation. The backend derives the profile from the
  authenticated user; the client never selects a customer ID.
- Customer accounts are provisioned by ADMIN/SUPER_ADMIN and linked to existing
  customer profiles by authorized staff. Public registration, password
  recovery, guest-to-account conversion and payment processing are not part of
  this phase.
- Guest booking lookup must use a secure, unguessable reference plus an additional verification mechanism.
- Do not expose internal notes, supplier costs, staff data or admin-only fields.
- Customer payment history is read-only and contains no internal payment notes,
  administrative exception reasons, resolution flags or recorder/verifier
  attribution.
- Validate all displayed content from API responses.
