# 10 – Copilot Prompts

Use one prompt at a time. Review generated changes before continuing.

## Prompt 0 – Inspect repository
Read `.github/copilot-instructions.md` and `docs/00_DOCUMENTATION_INDEX.md`.
Inspect the repository without modifying files. Report existing structure, missing files, risks and a proposed implementation plan. Do not generate code yet.

## Prompt 1 – Initialize project
Read docs 01, 02, 07 and 08.
Create the monorepo skeleton, FastAPI backend, Vue 3 TypeScript Admin app, Vue 3 TypeScript User app, Dockerfiles, `.env.example`, `.gitignore`, README and Docker Compose.
Do not implement business modules yet. Ensure all services can start with Docker Compose. Explain every created file and give exact WSL commands.

## Prompt 2 – Database foundation
Read docs 02, 03, 08 and 09.
Implement SQLAlchemy 2.x base, PostgreSQL session, Alembic and initial models for users, roles, user_roles, tours, tour_departures and customers. Add constraints, indexes and development seed data. Do not implement unrelated modules. Add tests and migration instructions.

## Prompt 3 – Backend authentication
Read docs 03, 04 and 08.
Implement registration policy as specified, login, token handling, current-user endpoint and backend role authorization. Hash passwords securely. Add tests for invalid credentials, expired tokens and role access. Do not rely on frontend checks for security.

## Prompt 4 – Tours and departures
Read docs 03 and 04.
Implement tour and departure CRUD, validation, pagination, filters and tests. Keep tour product separate from scheduled departure. Add migration if needed.

## Prompt 5 – Booking workflow
Read docs 03 and 04.
Implement booking creation, passenger records, confirmation, cancellation and status history. Prevent overbooking with a database transaction and concurrency-safe locking. Add tests including two concurrent requests for the last available seats. Do not invent cancellation fees or refund rules.

## Prompt 6 – Admin frontend foundation
Read docs 02, 05 and 08.
Implement Admin Vue layout, navigation, login, typed Axios client, Pinia auth store and protected routes. Integrate only with existing backend endpoints. Do not mock successful API behavior.

## Prompt 7 – Admin core screens
Read docs 04 and 05.
Implement tour, departure, customer and booking screens. Include loading, empty, error and success states, validation and pagination. Reuse components.

## Prompt 8 – User website
Read docs 02, 04, 06 and 08.
Implement homepage, public tour listing, tour detail, departure selection and booking form. Show only published/bookable data. Never show internal supplier costs or staff notes. Do not claim booking confirmation before backend response.

## Prompt 9 – Integration review
Review the whole repository against docs 01–09. Do not rewrite the project. Identify broken API contracts, missing authorization, database risks, missing tests, TypeScript errors and Docker issues. Fix only issues approved by the developer.

## Rules for every task
- Inspect existing files first.
- State the files you plan to create/change.
- Do not overwrite working code without explaining why.
- Do not generate the whole project in one response.
- Run relevant tests/checks.
- Report exact commands and results.
