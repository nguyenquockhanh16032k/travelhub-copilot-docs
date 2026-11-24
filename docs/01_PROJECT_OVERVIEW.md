# 01 – Project Overview

## Product
TravelHub is a web-based tour operations and travel business management platform.

## Product direction
Build an all-in-one platform with:
1. PostgreSQL database.
2. FastAPI backend.
3. Vue 3 Admin application.
4. Vue 3 public/customer application.

Admin and User applications are separate frontend projects. They share one backend API and one database. Authorization is enforced by the backend.

## Main users and roles
- `SUPER_ADMIN`: full system administration.
- `ADMIN`: manages business operations and staff permissions.
- `STAFF`: performs assigned operational tasks.
- `CUSTOMER`: browses tours and manages only their own profile and bookings.

## Core modules
- Authentication and role-based access control.
- Tour catalog and tour departures.
- Customer CRM.
- Booking and booking status history.
- Day-by-day itineraries.
- Payments, deposits, balances and refunds.
- Article/content management.
- Guides and tour assignments.
- Suppliers and tour expenses.
- Dashboard and business reports.

## Important product concepts
A Tour is a reusable product, for example “Da Lat – 3 days 2 nights”.
A Tour Departure is a specific scheduled instance of that tour, with its own dates, capacity, availability and price.
A Booking reserves seats on one departure.
A Booking may contain multiple travelers.
Payments are separate records and must be auditable.

## MVP scope
First release:
- Login and permissions.
- Tour CRUD.
- Departure CRUD and capacity.
- Customer CRUD.
- Booking create/view/update/cancel/confirm.
- Admin dashboard with basic counts.
- Public tour listing and tour detail.
- Public booking request flow.
- Docker-based local development.

Later releases:
- Online payment gateway.
- Supplier contracts and reconciliation.
- Advanced costing and profitability.
- Customer portal enhancements.
- AI itinerary assistant.
- Multi-company SaaS tenancy.

## Out of scope for MVP
Do not implement multi-tenant SaaS, complex accounting, live maps, AI features or payment gateway integration unless explicitly requested in a later task.
