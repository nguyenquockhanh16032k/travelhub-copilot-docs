# TravelHub – Copilot Documentation Pack

Project documentation and AI instructions for building TravelHub.

## Target development environment
- Windows 10 22H2 (build 19045) recommended for Docker Desktop.
- WSL 2 + Ubuntu.
- Docker Desktop using the WSL 2 backend.
- Docker Compose V2.
- VS Code + Remote - WSL extension + GitHub Copilot.

> Important: the user's previously reported Windows build was 19044 (Windows 10 21H2).
> Current Docker Desktop requirements specify Windows 10 22H2 build 19045. Update Windows
> before relying on Docker Desktop. WSL2 support by itself does not guarantee Docker Desktop
> compatibility.

## Documentation map
| File | Purpose |
|---|---|
| docs/00_DOCUMENTATION_INDEX.md | Reading order and document ownership |
| docs/01_PROJECT_OVERVIEW.md | Product scope and business goals |
| docs/02_ARCHITECTURE.md | System architecture and service boundaries |
| docs/03_DATABASE_DESIGN.md | Entities, relationships and database rules |
| docs/04_BACKEND_SPEC.md | FastAPI requirements |
| docs/05_ADMIN_SPEC.md | Admin application requirements |
| docs/06_USER_SPEC.md | Public/customer website requirements |
| docs/07_WINDOWS10_WSL2_DOCKER.md | Windows 10, WSL2 and Docker workflow |
| docs/08_CODING_STANDARDS.md | Coding and quality standards |
| docs/09_DEVELOPMENT_ROADMAP.md | Implementation sequence |
| docs/10_COPILOT_PROMPTS.md | Prompts for incremental generation |
| docs/11_PRODUCTION_DEPLOYMENT.md | Future Linux VPS deployment guide |
| docs/12_IMPORT_EXPORT_USER_GUIDE.md | Hướng dẫn Excel/CSV Tour |
| docs/13_TRAVELHUB_USER_MANUAL_VI.md | Sổ tay sử dụng TravelHub bằng tiếng Việt |
| .github/copilot-instructions.md | Persistent instructions for Copilot |
| docker-compose.yml | Local development service orchestration |
| .env.example | Environment variable template |

## Start here
1. Read `docs/00_DOCUMENTATION_INDEX.md`.
2. Check Windows and WSL prerequisites in `docs/07_WINDOWS10_WSL2_DOCKER.md`.
3. Open this repository in VS Code using the WSL Ubuntu environment.
4. Ask Copilot to inspect the repository and read `.github/copilot-instructions.md`.
5. Implement one phase at a time using `docs/10_COPILOT_PROMPTS.md`.

Do not ask Copilot to generate the entire product in one prompt.

The production Docker setup is separate from local development. See
[docs/11_PRODUCTION_DEPLOYMENT.md](./docs/11_PRODUCTION_DEPLOYMENT.md); it uses placeholder
domains and requires configured DNS and TLS certificates before deployment.

## Phase 0 local commands

Copy the environment template and replace development values:

```bash
cp .env.example .env
```

Start the skeleton stack:

```bash
docker compose config
docker compose up --build -d
docker compose ps
```

Local endpoints:

- User: http://localhost:5173
- Admin: http://localhost:5174
- API: http://localhost:8000
- Health: http://localhost:8000/health
- Swagger: http://localhost:8000/docs

Stop containers without deleting local PostgreSQL data:

```bash
docker compose down
```

For a verified database backup and a non-destructive restore drill, follow
[the backup and restore procedure in the WSL2/Docker guide](./docs/07_WINDOWS10_WSL2_DOCKER.md).

Run migrations and development seed data:

```bash
docker compose exec backend alembic upgrade head
docker compose exec backend python -m database.seeds.seed
```

Set `SEED_SUPER_ADMIN_EMAIL` and `SEED_SUPER_ADMIN_PASSWORD` in `.env` before
seeding. Seeded credentials are development-only and must never be used in production.

## PostgreSQL concurrency integration test

The regular backend test suite uses SQLite. To test PostgreSQL row locking against two
simultaneous booking requests, use the isolated test Compose file. It has no published
database port or persistent volume and does not use the development or production database.
It first applies all Alembic migrations to a fresh PostgreSQL database, then runs the
concurrency test.

```bash
set +e
dc() {
  docker compose --project-name travelhub-integration-tests \
    -f docker-compose.test.yml "$@"
}
dc up --build --abort-on-container-exit --exit-code-from test-runner
test_status=$?
dc down
cleanup_status=$?
if [ "$test_status" -ne 0 ]; then
  exit "$test_status"
fi
exit "$cleanup_status"
```

The test creates and removes a uniquely named schema inside the disposable
`travelhub_integration_test` database. `docker compose down` removes the test containers;
it does not remove any named database volume.

## Authentication API

Phase 2 provides these versioned endpoints:

- `POST /api/v1/auth/login`
- `POST /api/v1/auth/refresh`
- `POST /api/v1/auth/logout`
- `GET /api/v1/auth/me`

Refresh tokens are rotated and database-backed. Logout revokes the supplied refresh
token; access tokens expire according to `JWT_ACCESS_TOKEN_EXPIRE_MINUTES`.

## Catalog and customer API

Version 1 provides:

- `GET /api/v1/tours`
- `GET /api/v1/tours/{tour_id}`
- `POST/PATCH /api/v1/tours`
- `GET /api/v1/departures`
- `GET /api/v1/departures/{departure_id}`
- `POST/PATCH /api/v1/departures`
- `GET/POST /api/v1/customers`
- `GET/PATCH /api/v1/customers/{customer_id}`

Tour mutations and all customer operations require `SUPER_ADMIN` or `ADMIN`.

## Booking and payment API

Version 1 provides:

- `POST /api/v1/bookings` for guest or account booking requests
- `GET /api/v1/bookings`
- `GET /api/v1/bookings/{booking_id}`
- `POST /api/v1/bookings/{booking_id}/confirm`
- `POST /api/v1/bookings/{booking_id}/cancel`
- `POST /api/v1/payments`

Booking creation reserves seats in a database transaction. Canceling a booking releases
its reserved seats. Cancellation does not infer refund amounts. Payments are separate
records and do not reduce or replace the booking total.

## Admin frontend foundation

The Admin application provides:

- Protected Vue Router routes for Super Admin and Admin roles
- Login and session restoration
- Access-token requests and refresh-token rotation
- Logout and session-expired handling
- Admin navigation shell and dashboard
- A paginated Tour list with creation dialog

Frontend route guards improve navigation usability but are not a security boundary.
All mutations remain authorized by the FastAPI backend.

## Tour import/export (feature branch)

The Admin Tours screen supports CSV/XLSX tour export, blank templates and a two-step preview/confirm import. Imports are create-only and draft-only; they never change existing tours, bookings or payments. See [Hướng dẫn Import/Export](./docs/12_IMPORT_EXPORT_USER_GUIDE.md) for the complete Vietnamese operator manual. Full tests/build are pending; do not enable in production before verification.

Import/Export is pending PR-specific CI; see the pull request checks before merging.

## Public thử nghiệm qua Cloudflare Tunnel trên PC

Xem [hướng dẫn Cloudflare Tunnel](./docs/14_PC_CLOUDFLARE_TUNNEL.md). Chỉ Website User và same-origin API được công khai; Cloudflare Access phải bảo vệ hostname khi còn giai đoạn thử nghiệm. Không mở Admin hoặc PostgreSQL ra Internet.
