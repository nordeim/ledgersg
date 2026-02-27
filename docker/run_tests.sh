#!/bin/bash
# File: /app/scripts/run_tests.sh

set -e

echo "🧪 Setting up test database..."

export PGPASSWORD=ledgersg_secret_to_change

# Drop test database if exists
dropdb -h localhost -U ledgersg test_ledgersg_dev 2>/dev/null || true

# Create test database
createdb -h localhost -U ledgersg test_ledgersg_dev

# Load schema
psql -h localhost -U ledgersg -d test_ledgersg_dev -f /app/database_schema.sql

echo "✓ Test database ready"

# Run tests
cd /app/apps/backend
pytest --reuse-db --no-migrations
