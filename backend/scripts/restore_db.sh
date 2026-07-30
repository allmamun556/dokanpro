#!/usr/bin/env bash
# Restores a backup produced by backup_db.sh into the `db` compose service.
# DESTRUCTIVE: this replaces whatever is currently in the database. Prompts
# for confirmation before touching anything.
#
# Usage: ./backend/scripts/restore_db.sh backups/pos_db_20260730_120000.sql
set -euo pipefail

cd "$(dirname "$0")/../.."

if [ $# -ne 1 ]; then
  echo "Usage: $0 <backup-file.sql>"
  exit 1
fi

backup_file="$1"
if [ ! -f "$backup_file" ]; then
  echo "File not found: $backup_file"
  exit 1
fi

echo "This will DROP and recreate every table in the running 'db' service's pos_db database,"
echo "then restore from: $backup_file"
read -r -p "Type 'yes' to continue: " confirm
if [ "$confirm" != "yes" ]; then
  echo "Aborted."
  exit 1
fi

docker compose exec -T db psql -U pos_user -d pos_db -c "
  DROP SCHEMA public CASCADE;
  CREATE SCHEMA public;
"
docker compose exec -T db psql -U pos_user -d pos_db < "$backup_file"

echo "Restore complete."
