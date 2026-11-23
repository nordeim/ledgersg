# LedgerSG API Dockerfile — production image
#
# P11/H-6: rebuilt from pyproject.toml. The old image hand-listed unpinned
# dependencies and MISSED django-csp and django-ratelimit — both imported by
# INSTALLED_APPS/MIDDLEWARE — so the image could not boot Django
# (ModuleNotFoundError at startup). Installing the project itself
# (`pip install -e .`) makes every settings-level dependency present by
# construction and keeps the pin set identical to the venv/CI installs.
#
# The HuggingFace-Space kitchen-sink layers (in-container PostgreSQL/Redis,
# Node 24, bun/uv, Playwright browsers, FastAPI/SQLAlchemy installs, sudo)
# are gone — the compose file provides PostgreSQL and Redis as services.
#
# NOTE (P11 validation honesty): no Docker daemon exists in the build
# environment where this was written — this image is STATICALLY validated
# (the dependency set cross-checked against pyproject/INSTALLED_APPS/
# MIDDLEWARE and the healthcheck route against config/urls.py); it has not
# been built and booted here. Building it on a Docker host is the
# registered follow-up (see docs/REMEDIATION_2026-11-23_P11_REPORT.md).
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    DEBIAN_FRONTEND=noninteractive \
    LOG_DIR=/var/log/ledgersg

# weasyprint's native stack (pango/harfbuzz) + libpq + healthcheck tools
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        libpq-dev \
        libpango-1.0-0 \
        libpangoft2-1.0-0 \
        libharfbuzz0b \
        libffi-dev \
        libjpeg-dev \
        libopenjp2-7-dev \
        curl \
        ca-certificates \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# The pinned dependency set from the manifest — the single source of truth
# shared by the local venv (`uv sync`), CI (`pip install -e ".[dev]"`) and
# this image.
COPY . /app
RUN pip install --upgrade pip && pip install -e .

# Non-root runtime user; the LOG_DIR the production settings' file handler
# writes to (P11/C-2: the deployer's mkdir step, built into the image).
RUN groupadd -g 1000 ledgersg \
    && useradd -m -u 1000 -g ledgersg ledgersg \
    && mkdir -p ${LOG_DIR} \
    && chown -R ledgersg:ledgersg ${LOG_DIR} /app

USER ledgersg

# The container speaks HTTP on 8000 (compose maps 8000:8000; the old file
# exposed the HF-Space port 7860 that nothing in this stack listens on).
EXPOSE 8000

# The real health endpoint (config/urls.py health_check — DB ping included).
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -fsS http://localhost:8000/api/v1/health/ || exit 1

# Production WSGI entrypoint. The old file's gunicorn line was COMMENTED
# OUT — the image booted into an interactive bash session instead.
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "4", "--threads", "4", "config.wsgi:application"]
