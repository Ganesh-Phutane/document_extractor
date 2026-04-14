#!/bin/sh
set -e

echo "Starting Document Extractor Platform..."

# 1. Navigate to backend directory
cd /app/backend

# 2. Wait for Database
echo "Waiting for database to be ready..."
python3 scripts/wait_for_db.py || { echo "Database wait failed"; exit 1; }

# 3. Run Database Migrations (Alembic)
echo "Running database migrations (Alembic)..."
alembic upgrade head || { echo "Alembic migration failed"; exit 1; }

# 4. Run Template Seeding
echo "Seeding default templates..."
python3 scripts/seed_templates.py || { echo "Template seeding failed"; }

# 5. Start Backend (Gunicorn with Uvicorn workers)
echo "Starting backend service with Gunicorn on 127.0.0.1:8000..."
gunicorn main:app \
  --workers 4 \
  --worker-class uvicorn.workers.UvicornWorker \
  --bind 127.0.0.1:8000 \
  --access-logfile - \
  --error-logfile - &
BACKEND_PID=$!

# 6. Start Nginx (as the foreground process)
echo "Starting Nginx frontend proxy on Port 80..."

# Helper to stop everything
stop_all() {
    echo "Stopping services..."
    kill -TERM "$BACKEND_PID"
    exit 0
}

# Trap signals (Use TERM and INT for broad shell compatibility)
trap stop_all TERM INT

nginx -g "daemon off;"
