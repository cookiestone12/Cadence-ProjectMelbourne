# Reference Dockerfile for Cadence — proves the app is
# containerizable for a future move off Replit (ECS Fargate, Cloud
# Run, etc). NOT used by the current Replit deployment.
#
# Multi-stage:
#   1) frontend-build  — node:20 + Vite, produces /app/frontend/dist
#   2) production      — python:3.11 + FastAPI/Gunicorn, copies the
#      built frontend bundle and runs run_backend.sh (which executes
#      backend/db_setup.py for migrations + backstop, then exec's
#      uvicorn).
#
# Build:   docker build -t cadence:latest .
# Run:     docker run --rm -p 8000:8000 \
#            -e DATABASE_URL=postgresql://... \
#            -e SESSION_SECRET=... \
#            -e APP_ENV=production \
#            -e CORS_ORIGINS=https://app.example.com \
#            cadence:latest

FROM node:20-slim AS frontend-build
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build


FROM python:3.11-slim AS production
WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
        libpq-dev gcc bash && \
    rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt ./backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt

COPY backend/ ./backend/
COPY alembic/ ./alembic/
COPY alembic.ini ./
COPY run_backend.sh ./run_backend.sh
COPY scripts/ ./scripts/
RUN chmod +x ./run_backend.sh

COPY --from=frontend-build /app/frontend/dist ./frontend/dist

EXPOSE 8000

# run_backend.sh: set -euo pipefail; python -m backend.db_setup;
# exec uvicorn backend.main:app. The migration step is fail-fast,
# so the container will exit non-zero (and any orchestrator's health
# check will fail) if migrations don't apply cleanly.
CMD ["bash", "run_backend.sh"]
