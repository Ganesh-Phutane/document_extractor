# Stage 1: Build the React application
FROM node:20-alpine AS frontend-build

WORKDIR /app/frontend

# Install frontend dependencies
COPY frontend/package.json frontend/package-lock.json ./
RUN npm install

# Copy frontend source code and build
COPY frontend/ ./
# Inject VITE_API_URL for production (relative to current host)
ENV VITE_API_URL=/api
RUN npm run build

# Stage 2: Build the final production image
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1
ENV DEBIAN_FRONTEND noninteractive

# Install system dependencies + Nginx + SSL Certs + PostgreSQL
RUN apt-get update && apt-get install -y --no-install-recommends \
    nginx \
    curl \
    ca-certificates \
    libpq-dev \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Copy Azure CA certificate
COPY azure-ca.pem /app/azure-ca.pem

# Set work directory
WORKDIR /app

# Install Python dependencies
COPY backend/requirements.txt ./backend/
RUN pip install --no-cache-dir -r ./backend/requirements.txt
RUN pip install --no-cache-dir gunicorn uvicorn[standard]

# Copy backend source code
COPY backend/ ./backend/

# Copy frontend build output to Nginx directory
COPY --from=frontend-build /app/frontend/dist /usr/share/nginx/html

# Copy Nginx configuration
COPY nginx.conf /etc/nginx/sites-available/default
# Or replace the default if it exists
RUN ln -sf /etc/nginx/sites-available/default /etc/nginx/sites-enabled/default

# Copy and prepare entrypoint script
COPY entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

# Expose port (Azure App Service for Containers listens on 80 by default)
EXPOSE 80

# Use entrypoint script to handle migrations, seeding, and startup
ENTRYPOINT ["/app/entrypoint.sh"]
