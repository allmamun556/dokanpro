#!/bin/sh
# Production start script. Kept as a real file (not an inline shell string in
# Render's "Docker Command" field) because that field's quoting/splitting
# behavior mangled a multi-command `sh -c "... && ... && ..."` one-liner —
# the whole string ended up passed as a single, nonexistent command name.
# A script file sidesteps that entirely: no quotes, no &&, one plain token.
set -e

alembic upgrade head
python -m app.seed
exec uvicorn app.main:app --host 0.0.0.0 --port "$PORT"
