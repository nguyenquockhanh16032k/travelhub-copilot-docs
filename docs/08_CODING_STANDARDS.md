# 08 – Coding Standards

## General
- Inspect before editing.
- Implement one module at a time.
- Keep changes focused and explain them.
- Do not silently change architecture or API contracts.
- Never commit secrets.
- Do not invent unrequested business rules.

## Python
- Follow PEP 8.
- Use type hints.
- Use SQLAlchemy 2.x style.
- Use Pydantic schemas at API boundaries.
- Keep route handlers thin.
- Put business logic in services.
- Put persistence queries in repositories where repository abstraction is used.
- Use structured logging and meaningful exceptions.
- Add Pytest tests for business logic and authorization.

## TypeScript and Vue
- Use Vue 3 Composition API and `<script setup lang="ts">`.
- Enable TypeScript strict mode.
- Use typed API responses.
- Keep API calls in service modules.
- Use Pinia only for shared state.
- Use reusable components and composables.
- Avoid `any`; explain any unavoidable use.
- Handle loading, empty, error and success states.

## Database
- All schema changes through Alembic.
- Use constraints and indexes deliberately.
- Money uses fixed-precision decimal types.
- Use transactions for multi-step business operations.
- Add tests for race conditions in seat allocation.
- Preserve audit/financial history.

## API
- Prefix routes with `/api/v1`.
- Use correct HTTP methods and status codes.
- Paginate collection endpoints.
- Validate filters and sort fields.
- Return consistent error formats.
- Document behavior in OpenAPI.

## Quality gate
A task is complete only when:
1. Implementation exists.
2. Validation and authorization exist.
3. Migration exists if schema changed.
4. Tests are added and pass.
5. Frontend/backend contracts agree.
6. Type checks/build pass where applicable.
7. Documentation is updated.
8. Existing features remain functional.
