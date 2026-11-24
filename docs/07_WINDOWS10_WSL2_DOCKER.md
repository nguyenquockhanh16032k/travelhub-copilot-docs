# 07 – Windows 10 + WSL2 + Docker Desktop Setup

## Important compatibility check
The developer previously reported Windows build `19044` (Windows 10 21H2).
Current Docker Desktop Windows requirements specify Windows 10 22H2, build `19045`, and WSL 2 version 2.1.5 or later for the WSL backend.
Therefore, update Windows to 22H2/build 19045 before installing or relying on the current Docker Desktop release.

WSL2 itself supports older Windows 10 builds than current Docker Desktop. WSL2 compatibility does not imply Docker Desktop compatibility.

## Step 1 – Check Windows
Open PowerShell:
```powershell
winver
```
Confirm Windows 10 version 22H2 and OS build 19045.
If the machine remains on build 19044, resolve Windows update/edition eligibility first.

## Step 2 – Check WSL
```powershell
wsl --version
wsl --status
wsl --list --verbose
```
The Ubuntu distribution should show VERSION 2.
If needed:
```powershell
wsl --update
wsl --set-default-version 2
wsl --set-version Ubuntu 2
```
Use the exact distribution name returned by `wsl --list --verbose`.

If Ubuntu is not installed, install it using the supported Windows WSL installation flow. Restart Windows if requested.

## Step 3 – Install Docker Desktop
1. Install Docker Desktop for Windows from the official Docker website.
2. Select/use the WSL 2 backend.
3. Start Docker Desktop.
4. Open Settings > General and verify “Use the WSL 2 based engine”.
5. Open Settings > Resources > WSL Integration and enable the Ubuntu distribution.
6. Apply changes and restart Docker Desktop if requested.

Do not install a second Docker Engine inside Ubuntu when using Docker Desktop WSL integration. Running both can cause conflicts.

## Step 4 – Verify Docker from Ubuntu
Open Ubuntu (WSL):
```bash
docker --version
docker compose version
docker info
```
If commands are unavailable, verify Docker Desktop is running and Ubuntu integration is enabled.

## Step 5 – Store the project inside Linux filesystem
Recommended:
```bash
mkdir -p ~/projects
cd ~/projects
```
Clone the repository inside `~/projects`, not under `/mnt/c`, for better Linux filesystem performance:
```bash
git clone <YOUR_REPOSITORY_URL> travelhub
cd travelhub
```
Open the project from WSL:
```bash
code .
```
Install/use the VS Code Remote - WSL extension.

## Step 6 – Configure environment
```bash
cp .env.example .env
```
Edit `.env` and replace development secrets. Never commit `.env`.

## Step 7 – Build and start
From the repository root in Ubuntu:
```bash
docker compose config
docker compose up --build -d
docker compose ps
```

## Step 8 – Verify services
- User site: http://localhost:5173
- Admin site: http://localhost:5174
- Backend API: http://localhost:8000
- Swagger: http://localhost:8000/docs

Check logs:
```bash
docker compose logs -f
docker compose logs -f backend
```

## Step 9 – Stop and restart
```bash
docker compose down
docker compose up -d
```
To remove containers and the named database volume (DESTRUCTIVE – deletes local database data):
```bash
docker compose down -v
```
Never run `down -v` unless you intentionally want to delete the local database volume.

## Step 10 – Common commands
```bash
docker compose ps
docker compose logs -f backend
docker compose exec backend sh
docker compose exec db psql -U travelhub -d travelhub
docker compose restart backend
docker compose build backend
```

## Step 11 – Back up and verify PostgreSQL
Run these commands from the repository root in Ubuntu/WSL. The dump is written outside
the repository because it contains customer and booking data.

```bash
set -euo pipefail
umask 077
mkdir -p "$HOME/travelhub-backups"
BACKUP_FILE="$HOME/travelhub-backups/travelhub-$(date +%Y%m%d-%H%M%S).dump"

docker compose exec -T db sh -c \
  'pg_dump --format=custom --username="$POSTGRES_USER" "$POSTGRES_DB"' \
  > "$BACKUP_FILE"
test -s "$BACKUP_FILE"
docker compose exec -T db pg_restore --list - < "$BACKUP_FILE" > /dev/null
chmod 600 "$BACKUP_FILE"
printf 'Verified backup: %s\n' "$BACKUP_FILE"
```

Keep a verified copy on storage independent from the machine running Docker. Protect it
as sensitive data and define retention before automating or deleting old copies. This
manual procedure does not provide off-site storage or scheduled backups.

## Step 12 – Restore to a separate database
This is a non-destructive restore drill: it leaves the current database in place and
restores into a new database. Set `BACKUP_FILE` to the dump to restore.

```bash
set -euo pipefail
BACKUP_FILE="$HOME/travelhub-backups/travelhub-YYYYMMDD-HHMMSS.dump"
test -s "$BACKUP_FILE"
docker compose exec -T db pg_restore --list - < "$BACKUP_FILE" > /dev/null
RESTORE_DB="travelhub_restore_$(date +%Y%m%d%H%M%S)"

# Stop application writers, but keep PostgreSQL running.
docker compose stop backend admin user

docker compose exec -T db sh -c \
  'createdb --username="$POSTGRES_USER" "$1"' sh "$RESTORE_DB"
docker compose exec -T db sh -c \
  'pg_restore --exit-on-error --no-owner --no-acl --username="$POSTGRES_USER" --dbname="$1" -' \
  sh "$RESTORE_DB" < "$BACKUP_FILE"
docker compose exec -T db sh -c \
  'psql --username="$POSTGRES_USER" --dbname="$1" --command "SELECT current_database(), count(*) FROM bookings;"' \
  sh "$RESTORE_DB"
printf 'Restored database: %s\n' "$RESTORE_DB"
```

To run the application against the restored copy, edit `DATABASE_URL` in the local
`.env` to use `RESTORE_DB` as its database name, keeping the existing user, password,
and connection settings unchanged. Then run:

```bash
docker compose up -d backend admin user
docker compose ps
curl --fail http://localhost:8000/health
```

Verify the restored application data before relying on it. The original database remains
available: restore the previous database name in `.env` and run the same `docker compose
up -d` command to switch back. Do not remove the PostgreSQL volume as part of a restore;
`docker compose down -v` deletes local database data.

## Development rules
- Use Ubuntu terminal for project commands.
- Use Docker Compose to run PostgreSQL, backend and both frontends.
- Do not install project Python/Node dependencies globally on Windows.
- Keep project files in WSL Linux filesystem.
- Keep secrets in `.env`.
- Use named Docker volumes for PostgreSQL persistence.
- Use health checks and service dependencies.
- Keep database port binding local-only for development where possible.

## Official references
- Docker Desktop Windows install: https://docs.docker.com/desktop/setup/install/windows-install/
- Docker Desktop WSL2 backend: https://docs.docker.com/desktop/features/wsl/
- Docker WSL best practices: https://docs.docker.com/desktop/features/wsl/best-practices/
- Microsoft WSL manual installation: https://learn.microsoft.com/en-us/windows/wsl/install-manual
