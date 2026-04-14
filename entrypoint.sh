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

# 2. Run Template Seeding
echo "Seeding default templates..."
python3 scripts/seed_templates.py || { echo "Template seeding failed"; }

# 4. Start Backend (Uvicorn)
echo "Starting backend service on 127.0.0.1:8000..."
uvicorn main:app \
  --host 127.0.0.1 \
  --port 8000 \
  --proxy-headers \
  --forwarded-allow-ips='*' &

# 5. Start Nginx (as the foreground process)
echo "Starting Nginx frontend proxy on Port 80..."
nginx -g "daemon off;"
