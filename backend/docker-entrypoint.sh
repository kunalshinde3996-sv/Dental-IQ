#!/bin/sh
# Apply database migrations, then start the API. Fails fast if migrations fail.
set -e
echo "Applying database migrations (alembic upgrade head)..."
alembic upgrade head
echo "Starting Dental-IQ API (APP_ENV=${APP_ENV:-development})..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers "${UVICORN_WORKERS:-1}"
