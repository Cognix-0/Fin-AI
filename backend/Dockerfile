# -----------------------------------------------------------------------------
# Base Stage
# -----------------------------------------------------------------------------
FROM python:3.12-slim AS base

# Prevent Python from writing .pyc files and enable unbuffered logging
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PORT=8000 \
    UPLOAD_DIR=/app/uploads \
    RUN_MIGRATIONS=true

WORKDIR /app

# Install system dependencies (curl for health check / minimal network tooling)
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

# Create a non-root user for security
RUN groupadd -g 1001 appgroup && \
    useradd -u 1001 -g appgroup -m -s /bin/bash appuser

# -----------------------------------------------------------------------------
# Dependencies Stage (cached unless requirements.txt changes)
# -----------------------------------------------------------------------------
COPY requirements.txt .
RUN pip install --upgrade pip \
    && pip install -r requirements.txt

# -----------------------------------------------------------------------------
# Application Source
# -----------------------------------------------------------------------------
COPY --chown=appuser:appgroup . .

# Receipt storage. Mount a volume here so uploads survive container rebuilds;
# creating it in the image means a fresh named volume inherits the right owner.
RUN mkdir -p /app/uploads/receipts && chown -R appuser:appgroup /app/uploads
VOLUME ["/app/uploads"]

# Switch to non-root user
USER appuser

EXPOSE 8000

# Readiness: only healthy once the database is reachable
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD curl -fsS http://localhost:${PORT}/api/v1/health/ready || exit 1

# Apply pending migrations (set RUN_MIGRATIONS=false when running several
# replicas and migrating from a separate job), then start the API.
CMD ["sh", "-c", "if [ \"$RUN_MIGRATIONS\" = \"true\" ]; then alembic upgrade head; fi && exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT} --proxy-headers --forwarded-allow-ips='*'"]
