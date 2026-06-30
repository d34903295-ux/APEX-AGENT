# syntax=docker/dockerfile:1
FROM python:3.11-slim AS base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# System deps (build tools for numpy/scipy/xgboost wheels fallback)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential curl ca-certificates \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

COPY . .

# Non-root user
RUN useradd -m apex && chown -R apex:apex /app
USER apex

# Default entrypoint = the all-in-one orchestrator (single host).
# docker-compose overrides "command" to run individual microservices.
CMD ["python", "-m", "apex.main"]
