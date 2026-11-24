# 02 – Technical Architecture

## Architecture style
Use a monorepo with independently buildable applications and Docker services.

```text
Browser
  |                         |
  v                         v
User Vue app             Admin Vue app
  |                         |
  +-----------+-------------+
              |
        REST API /api/v1
              |
          FastAPI
              |
      Service / Repository
              |
         PostgreSQL
```

## Technology stack
- Database: PostgreSQL.
- Backend: Python 3.12+, FastAPI, Pydantic, SQLAlchemy 2.x, Alembic.
- Frontends: Vue 3, TypeScript, Vite, Vue Router, Pinia, Axios.
- UI: Vuetify (use one consistent UI library).
- Testing: Pytest, Vitest, Vue Test Utils.
- Runtime: Docker Desktop with WSL2 backend and Docker Compose V2.
- API documentation: generated OpenAPI/Swagger.

## Repository layout
```text
travelhub/
├── backend/
│   ├── app/
│   │   ├── api/v1/
│   │   ├── core/
│   │   ├── db/
│   │   ├── models/
│   │   ├── schemas/
│   │   ├── repositories/
│   │   ├── services/
│   │   └── main.py
│   ├── tests/
│   ├── alembic/
│   ├── Dockerfile
│   └── requirements.txt
├── frontend-admin/
│   ├── src/
│   ├── Dockerfile
│   └── package.json
├── frontend-user/
│   ├── src/
│   ├── Dockerfile
│   └── package.json
├── database/
│   └── seeds/
├── docs/
├── .github/
├── docker-compose.yml
├── .env.example
├── .gitignore
└── README.md
```

## Docker services and local ports
- `db`: PostgreSQL, host port 5432.
- `backend`: FastAPI, host port 8000.
- `admin`: Vue/Vite development server, host port 5174.
- `user`: Vue/Vite development server, host port 5173.

Local URLs:
- User: http://localhost:5173
- Admin: http://localhost:5174
- API: http://localhost:8000
- Swagger: http://localhost:8000/docs

## Service communication
Inside Docker Compose, backend connects to PostgreSQL using hostname `db`, not `localhost`.
Backend database URL must use the Compose service name, for example:
`postgresql+psycopg://travelhub:CHANGE_ME@db:5432/travelhub`.

Browser-facing frontend API base URL in local development is `http://localhost:8000/api/v1`.
Do not expose internal database credentials to frontend containers.

## Configuration
- Keep secrets in `.env`, never commit `.env`.
- Commit `.env.example` with safe placeholders.
- Use explicit environment variables for database URL, JWT settings and CORS origins.
- Use separate development and production configurations.
- Do not use development servers as production deployment servers.
- The production Compose file is separate from local development and routes the public
  frontend domains and API through an HTTPS Nginx gateway.

## Architecture rules
- Frontends must not connect directly to PostgreSQL.
- All business rules live in backend services.
- API routes handle HTTP concerns and delegate to services.
- Repositories handle persistence queries.
- Schemas validate request and response data.
- Backend authorization is mandatory even if frontend routes are hidden.
