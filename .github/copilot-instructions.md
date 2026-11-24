# TravelHub – GitHub Copilot Instructions

You are contributing to TravelHub. Read `docs/00_DOCUMENTATION_INDEX.md` and the relevant specifications before coding.

## Fixed architecture
- PostgreSQL database.
- FastAPI backend (Python).
- Vue 3 + TypeScript Admin frontend.
- Vue 3 + TypeScript Customer frontend.
- Docker Compose for local runtime.
- Target developer environment: Windows 10 22H2 + WSL2 Ubuntu + Docker Desktop WSL2 backend.
- Both frontends use the same versioned REST API. Neither frontend connects directly to PostgreSQL.

## Mandatory workflow
1. Inspect existing files before modifying them.
2. Read relevant documentation.
3. Summarize the proposed changes and affected files.
4. Implement one feature/module at a time.
5. Preserve existing working behavior.
6. Add/update tests.
7. Run relevant tests, type checks and builds.
8. Update documentation when contracts change.
9. Summarize changed files and verification results.

## Backend rules
- FastAPI, Pydantic, SQLAlchemy 2.x and Alembic.
- Thin API route handlers.
- Business rules in service layer.
- Database access in repositories or clearly separated data-access functions.
- Type hints and input validation.
- Backend authorization on every protected operation.
- Use transactions for multi-step workflows.
- Never use floating-point types for money.

## Frontend rules
- Vue 3 Composition API with `<script setup lang="ts">`.
- TypeScript strict mode.
- Axios client centralized in services.
- Pinia for shared state.
- Reusable components and composables.
- Handle loading, empty, error and success states.
- Frontend route guards are not a security boundary.

## Business invariants
- One tour can have many departures.
- A booking belongs to one departure.
- A departure has finite capacity.
- Prevent overbooking atomically in the backend/database.
- Customers can access only their own data.
- Booking status changes are auditable.
- Payments are separate auditable records.
- Do not treat booking total as cash received.
- Do not invent refund/cancellation policy.

## Docker and WSL rules
- Use Docker Compose V2 (`docker compose`, not legacy `docker-compose`).
- Assume commands are run from Ubuntu WSL terminal unless stated otherwise.
- Backend connects to database using Compose hostname `db`, never `localhost`.
- Keep `.env` out of Git; maintain `.env.example`.
- Use named volumes for PostgreSQL.
- Never run `docker compose down -v` without warning that it deletes local database data.
- Do not install a second Docker Engine inside Ubuntu when Docker Desktop WSL integration is used.
- Prefer project files in the WSL Linux filesystem, e.g. `~/projects/travelhub`, not `/mnt/c/...`.

## Compatibility warning
The developer previously reported Windows build 19044. Current Docker Desktop requirements specify Windows 10 22H2/build 19045. Do not assume Docker Desktop is supported until Windows and WSL prerequisites are verified. Refer to `docs/07_WINDOWS10_WSL2_DOCKER.md`.

## Do not
- Generate the entire application in one prompt.
- Invent API endpoints or database fields without checking specifications.
- Replace the chosen stack without approval.
- Hardcode secrets or credentials.
- Modify unrelated modules.
- Claim a feature is complete without tests/checks.
