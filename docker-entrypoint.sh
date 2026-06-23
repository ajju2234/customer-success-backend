#!/bin/sh
set -e

# Apply DB migrations, then start the API server.
echo "Running database migrations…"
alembic upgrade head

# Cloud platforms (Railway/Render) inject $PORT; fall back to 8000 locally.
PORT="${PORT:-8000}"
echo "Starting API on :${PORT}"
exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT}"
