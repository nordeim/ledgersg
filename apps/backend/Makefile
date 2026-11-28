# LedgerSG Backend Makefile

.PHONY: help install dev test test-cov lint format typecheck migrate shell celery celery-beat docker-up docker-down clean

# Default target
help:
	@echo "LedgerSG Backend - Available Commands:"
	@echo ""
	@echo "  make install      - Install dependencies"
	@echo "  make dev          - Start development server"
	@echo "  make test         - Run test suite"
	@echo "  make test-cov     - Run tests with coverage"
	@echo "  make lint         - Run ruff linter (full report)"
	@echo "  make lint-mechanical - Ruff gate: closed classes at 0, whole tree (P30+P31)"
	@echo "  make format       - Run ruff formatter"
	@echo "  make typecheck    - Run mypy"
	@echo "  make migrate      - Run Django migrations"
	@echo "  make shell        - Django shell with IPython"
	@echo "  make celery       - Start Celery worker"
	@echo "  make celery-beat  - Start Celery beat scheduler"
	@echo "  make docker-up    - Start Docker containers"
	@echo "  make docker-down  - Stop Docker containers"
	@echo "  make clean        - Remove Python cache files"
	@echo ""

# Installation
install:
	pip install -e ".[dev]"

# Development server
dev:
	python manage.py runserver

# Testing (the canonical invocation — DEPLOYMENT.md §7; bare pytest
# prompts against the dev DB)
test:
	pytest --reuse-db --no-migrations

test-cov:
	pytest --reuse-db --no-migrations --cov=apps --cov=common --cov-report=html --cov-report=term

# Linting and formatting
# make lint stays the FULL report (the semantic findings are the
# registered deferred batch); lint-mechanical is the P30/CFG-M3 +
# P31/CFG-M3 unified RATCHET — the closed classes (whitespace, import
# order, unused imports, the settings star-import contract, B904
# exception chaining) must stay at 0 across the WHOLE tree (production
# + tests). The same command runs in CI (ci.yml backend-tests) — a
# gate nobody runs is a rubber stamp.
lint:
	ruff check .

lint-mechanical:
	ruff check --select W291,W293,I001,F401,F403,F405,B904 apps common config tests

format:
	ruff format .

format-check:
	ruff format --check .

typecheck:
	mypy apps common config

# Database
# P11/M-13: the SQL-First architecture forbids migrations — the schema is
# database_schema.sql (loaded by docs/setup_pg_z.sh / DEPLOYMENT.md).
# These targets previously shipped the exact commands DEPLOYMENT.md
# warns against; they now refuse truthfully instead of silently
# contradicting the architecture.
migrate:
	@echo "ERROR: this architecture is SQL-First — the schema is loaded from database_schema.sql (see docs/DEPLOYMENT.md). Migrations are permanently disabled (managed=False mirrors)."
	@exit 1

migrations:
	@echo "ERROR: makemigrations is forbidden in this architecture — the schema is database_schema.sql (see docs/DEPLOYMENT.md)."
	@exit 1

shell:
	python manage.py shell_plus

# Celery
celery:
	celery -A config worker -l info

celery-beat:
	celery -A config beat -l info --scheduler django_celery_beat.schedulers:DatabaseScheduler

# Docker
docker-up:
	docker-compose up -d

docker-down:
	docker-compose down

docker-build:
	docker-compose build

docker-logs:
	docker-compose logs -f

# Cleanup
clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type f -name ".coverage" -delete
	rm -rf htmlcov/
	rm -rf .pytest_cache/
	rm -rf .mypy_cache/

# All checks (for CI)
check: lint format-check typecheck test
	@echo "All checks passed!"
