#!/bin/bash
cd apps/backend && ls -l database_schema.sql

# Initialize test database
export PGPASSWORD=ledgersg_secret_to_change
dropdb -h localhost -U ledgersg test_ledgersg_dev 2>/dev/null
createdb -h localhost -U ledgersg test_ledgersg_dev
psql -h localhost -U ledgersg -d test_ledgersg_dev -f database_schema.sql

exit 0

# Run dashboard cache tests
cd /home/project/Ledger-SG/apps/backend
source /opt/venv/bin/activate
pytest apps/reporting/tests/test_dashboard_cache.py -v --tb=short --reuse-db --no-migrations

# Run all dashboard tests
pytest apps/reporting/tests/test_dashboard_service_tdd.py apps/reporting/tests/test_dashboard_cache.py -v

