#!/bin/bash
echo "cd /home/project"
echo "git clone https://github.com/nordeim/ledgersg.git"

# export PGPASSWORD=ledgersg_secret_to_change && dropdb -h localhost -U ledgersg test_ledgersg_dev 2>&1 || echo "Database doesn't exist, continuing..."
# export PGPASSWORD=ledgersg_secret_to_change && createdb -h localhost -U ledgersg test_ledgersg_dev 2>&1
# export PGPASSWORD=ledgersg_secret_to_change && psql -h localhost -U ledgersg -d test_ledgersg_dev -f database_schema.sql 2>&1 | tail -20
# export PGPASSWORD=ledgersg_secret_to_change && psql -h localhost -U ledgersg -d test_ledgersg_dev -c "SELECT pg_get_constraintdef(oid) FROM pg_constraint WHERE conname = 'bank_account_paynow_type_check';"
# source /opt/venv/bin/activate && pytest apps/reporting/tests/test_dashboard_service_tdd.py --reuse-db --no-migrations -v 2>&1 | head -150
# source /opt/venv/bin/activate && pytest apps/reporting/tests/test_dashboard_service_tdd.py::TestEdgeCases::test_handles_empty_organisation --reuse-db --no-migrations -v 2>&1

cd /home/project/ledgersg/apps/backend && source /opt/venv/bin/activate && python manage.py runserver 0.0.0.0:8000

/bin/bash -c "cd /home/project/ledgersg/apps/web && nohup node .next/standalone/server.js > /tmp/next-server.log 2>&1 &"

exit 0

##########
============================= test session starts ==============================
platform linux -- Python 3.12.3, pytest-9.0.2, pluggy-1.6.0 -- /opt/venv/bin/python3
cachedir: .pytest_cache
django: version: 6.0.2, settings: config.settings.testing (from ini)
PySide6 6.9.2 -- Qt runtime 6.9.2 -- Qt compiled 6.9.2
hypothesis profile 'default'
rootdir: /home/project/Ledger-SG/apps/backend
configfile: pytest.ini (WARNING: ignoring pytest config in pyproject.toml!)
plugins: django-4.12.0, respx-0.22.0, qt-4.5.0, hypothesis-6.148.7, Faker-40.5.1, mock-3.12.0, anyio-4.12.1, cov-7.0.0, langsmith-0.5.1, logfire-4.16.0, asyncio-0.21.2, xdist-3.8.0
asyncio: mode=Mode.STRICT
