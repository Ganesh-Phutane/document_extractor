#!/bin/sh

# Exit immediately if a command fails
set -e

# Wait for MySQL to be ready if the DB host is provided and netcat is available
if [ -n "$DATABASE_HOST" ]; then
    echo "Waiting for MySQL at $DATABASE_HOST:3306..."
    while ! nc -z $DATABASE_HOST 3306; do
      echo "MySQL is unavailable - sleeping"
      sleep 1
    done
    echo "MySQL is up - executing command"
fi

# Run migrations
echo "Running alembic migrations..."
alembic upgrade head

# Seed default templates (idempotent: checks for existence internally)
echo "Seeding default templates..."
python scripts/seed_templates.py

# Start server
# Using uvicorn directly for development/small production
# For high traffic, consider gunicorn with workers
echo "Starting FastAPI server..."
exec uvicorn main:app --host 0.0.0.0 --port 8000 --proxy-headers --forwarded-allow-ips='*'
