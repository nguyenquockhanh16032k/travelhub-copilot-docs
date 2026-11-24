# 00 – Documentation Index

## Purpose
This index tells developers and GitHub Copilot which document is authoritative for each topic.

## Reading order
1. `01_PROJECT_OVERVIEW.md` – what the product does.
2. `02_ARCHITECTURE.md` – how applications and services communicate.
3. `03_DATABASE_DESIGN.md` – data entities and business relationships.
4. `04_BACKEND_SPEC.md` – API and business logic.
5. `05_ADMIN_SPEC.md` – internal staff application.
6. `06_USER_SPEC.md` – public customer website.
7. `07_WINDOWS10_WSL2_DOCKER.md` – local development and runtime.
8. `08_CODING_STANDARDS.md` – mandatory implementation conventions.
9. `09_DEVELOPMENT_ROADMAP.md` – implementation order.
10. `10_COPILOT_PROMPTS.md` – task-specific prompts.
11. `11_PRODUCTION_DEPLOYMENT.md` – future Linux VPS deployment using Docker Compose.

## Source of truth
- Product scope: `01_PROJECT_OVERVIEW.md`
- Architecture: `02_ARCHITECTURE.md`
- Data model: `03_DATABASE_DESIGN.md`
- API behavior: `04_BACKEND_SPEC.md`
- UI behavior: `05_ADMIN_SPEC.md` and `06_USER_SPEC.md`
- Runtime and commands: `07_WINDOWS10_WSL2_DOCKER.md`
- Production deployment: `11_PRODUCTION_DEPLOYMENT.md`
- Code quality: `08_CODING_STANDARDS.md`

If two documents conflict, do not silently choose one. Report the conflict and ask the developer to decide.

## Copilot workflow
Before changing code:
- Inspect the existing repository.
- Read this index and the relevant specifications.
- Summarize the intended changes.
- Identify dependencies and affected files.

After changing code:
- Run relevant tests and checks.
- Update API or database documentation if contracts changed.
- Summarize changed files and exact verification commands.
