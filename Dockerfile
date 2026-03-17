# Stage 1: Build frontend static export
FROM node:22-slim AS frontend-build

WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ .
RUN npm run build

# Stage 2: Production image with Python backend + static frontend
FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

# Install Python dependencies (layer caching: deps before app code)
COPY backend/pyproject.toml backend/uv.lock ./
RUN uv sync --frozen --no-dev

# Copy backend application code
COPY backend/app/ /app/app/

# Copy frontend static export from build stage
COPY --from=frontend-build /app/frontend/out /app/static

# Create database directory
RUN mkdir -p /app/db

EXPOSE 8000

ENV PYTHONUNBUFFERED=1

CMD ["/app/.venv/bin/uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
