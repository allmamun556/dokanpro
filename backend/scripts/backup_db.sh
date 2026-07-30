#!/usr/bin/env bash
# Dumps the Postgres database running in the `db` compose service to a
# timestamped .sql file under backups/. Manual/cron-triggered only — not
# scheduled or shipped off-site (that's a hosting-dependent follow-up; most
# managed Postgres hosts include automated backups for free).
#
# Usage: ./backend/scripts/backup_db.sh   (run from the repo root)
set -euo pipefail

cd "$(dirname "$0")/../.."

mkdir -p backups
timestamp="$(date +%Y%m%d_%H%M%S)"
outfile="backups/pos_db_${timestamp}.sql"

docker compose exec -T db pg_dump -U pos_user pos_db > "$outfile"

echo "Backup written to $outfile"
