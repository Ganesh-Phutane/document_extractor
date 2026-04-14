#!/bin/sh

# Exit immediately if a command fails
set -e

# 1. Wait for Database
echo "Waiting for database to be ready..."
python3 scripts/wait_for_db.py || { echo "Database wait failed"; exit 1; }

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
