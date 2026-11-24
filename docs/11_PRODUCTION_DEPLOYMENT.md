# 11 – Production Deployment Preparation

This is a configurable starting point for a future Linux VPS deployment. No VPS,
production DNS, or TLS certificates are currently configured. Replace every placeholder
and complete the pre-deployment checks before exposing the services publicly.

The local development stack remains `docker-compose.yml`; do not use the production file
for everyday local development.

## Production topology

`docker-compose.prod.yml` runs:

- PostgreSQL on a private Compose network with a persistent named volume and no published port.
- FastAPI in a non-root container, with no source bind mounts or reload server.
- One Nginx gateway that serves the built customer and admin Vue apps on separate domains,
  proxies `/api/` to FastAPI, and redirects HTTP to HTTPS.

The gateway publishes ports 80 and 443. The API container is reachable only from the
gateway and database networks. The database is reachable only from the backend.
Interactive API documentation and OpenAPI paths are not routed by Nginx.

## Before deployment

1. Prepare a supported Linux VPS with Docker Engine and Docker Compose V2.
2. Register and configure DNS for `USER_DOMAIN`, `ADMIN_DOMAIN`, and `API_DOMAIN` to
   resolve to the VPS.
3. Allow inbound TCP ports 80 and 443 in the VPS firewall. Do not expose PostgreSQL
   port 5432 or the backend port 8000 publicly.
4. Obtain valid TLS certificates for all three hostnames. Certificate issuance and
   renewal are intentionally not automated by this project.
5. Confirm that the PostgreSQL backup and restore procedure in
   [the WSL2/Docker guide](./07_WINDOWS10_WSL2_DOCKER.md) is understood and tested.

## Configure placeholders and secrets

Create a separate production environment file:

```bash
cp .env.production.example .env.production
```

Edit `.env.production` and replace all sample values:

- Set `USER_DOMAIN`, `ADMIN_DOMAIN`, and `API_DOMAIN` to the real hostnames.
- Set `VITE_API_BASE_URL` to `https://<API_DOMAIN>/api/v1`.
- Set `CORS_ORIGINS` to the exact HTTPS origins of the customer and admin sites.
- Set a unique `JWT_SECRET_KEY` with at least 32 characters. For example, generate one
  with `python3 -c 'import secrets; print(secrets.token_urlsafe(48))'`.
- Set a strong PostgreSQL password and use the same value in `POSTGRES_PASSWORD` and
  `DATABASE_URL`. Use a URL-safe value or percent-encode reserved characters in
  `DATABASE_URL`.
- Set `TLS_CERTS_DIR` to the directory containing the certificate files. The default is
  `./deploy/certs`.

The example secret values are deliberately invalid for production. The application
rejects the example JWT signing key when `ENVIRONMENT=production`. Never commit
`.env.production` or certificate private keys.

Place the certificates in this structure under `TLS_CERTS_DIR`:

```text
USER_DOMAIN/fullchain.pem
USER_DOMAIN/privkey.pem
ADMIN_DOMAIN/fullchain.pem
ADMIN_DOMAIN/privkey.pem
API_DOMAIN/fullchain.pem
API_DOMAIN/privkey.pem
```

The Nginx container requires these files at startup. The certificate directory is mounted
read-only and is ignored by Git by default.

## Build, migrate, and start

Run from the repository root on the VPS. Use the same Compose project name, env file, and
production Compose file for every command so production resources remain separate from
the local development stack. Keep the same shell session open for the following commands
so the `dc` helper remains defined; otherwise, define it again.

```bash
set -euo pipefail
dc() {
  docker compose --project-name travelhub-prod \
    --env-file .env.production \
    -f docker-compose.prod.yml "$@"
}

dc config --quiet
dc build --pull
dc up -d db
dc run --rm backend alembic upgrade head
dc up -d
dc ps
```

Do not run the development seed script in production. Review the migration result before
starting the public gateway. Check health and logs:

```bash
set -euo pipefail
dc ps
dc logs --tail=100 backend web db
API_DOMAIN="$(sed -n 's/^API_DOMAIN=//p' .env.production)"
curl --fail "https://${API_DOMAIN}/health"
```

The frontends bake `VITE_API_BASE_URL` into their static assets at build time. Rebuild
the `web` image after changing that value. Restarting a container alone does not update
the built frontend configuration.

## Updates and operations

Back up the database before schema or application updates. Build the new images, apply
Alembic migrations with `dc run --rm backend alembic upgrade head`, then restart the
services with `dc up -d`. Check health and logs before considering an update complete.

This single-host Compose setup does not provide high availability, automated certificate
renewal, scheduled/off-site backups, or zero-downtime deployments. Plan and test those
operational requirements before using it for production data. Never use `docker compose
down -v` as an update or restore step; it deletes the database volume.
