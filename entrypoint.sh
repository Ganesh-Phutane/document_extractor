#!/bin/sh
set -e

echo "Starting Document Extractor Platform..."

# 1. Run Database Migrations (Alembic)
echo "Running database migrations (Alembic)..."
cd /app/backend
alembic upgrade head || { echo "Alembic migration failed"; exit 1; }

# 2. Run Template Seeding
echo "Seeding default templates..."
python3 scripts/seed_templates.py || { echo "Template seeding failed"; }

# 3. Start Backend (Gunicorn with Uvicorn worker)
echo "Starting backend service on 127.0.0.1:8000..."
gunicorn main:app \
  --bind 127.0.0.1:8000 \
  --worker-class uvicorn.workers.UvicornWorker \
  --workers 4 \
  --timeout 600 &

# 4. Start Nginx (as the foreground process)
echo "Starting Nginx frontend proxy on Port 80..."
nginx -g "daemon off;"
