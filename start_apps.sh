#!/bin/bash
echo "cd /home/project"
echo "git clone https://github.com/nordeim/ledgersg.git"

# export PGPASSWORD=ledgersg_secret_to_change && dropdb -h localhost -U ledgersg test_ledgersg_dev 2>&1 || echo "Database doesn't exist, continuing..."
# export PGPASSWORD=ledgersg_secret_to_change && createdb -h localhost -U ledgersg test_ledgersg_dev 2>&1
# export PGPASSWORD=ledgersg_secret_to_change && psql -h localhost -U ledgersg -d test_ledgersg_dev -f database_schema.sql 2>&1 | tail -20
#
# export PGPASSWORD=ledgersg_secret_to_change && dropdb -h localhost -U ledgersg test_ledgersg_dev 2>/dev/null; createdb -h localhost -U ledgersg test_ledgersg_dev && psql -h localhost -U ledgersg -d test_ledgersg_dev -f /home/project/Ledger-SG/database_schema.sql > /dev/null 2>&1 && echo "Test database initialized successfully"
#
# export PGPASSWORD=ledgersg_secret_to_change && psql -h localhost -U ledgersg -d test_ledgersg_dev -c "SELECT pg_get_constraintdef(oid) FROM pg_constraint WHERE conname = 'bank_account_paynow_type_check';"
# source /opt/venv/bin/activate && pytest apps/reporting/tests/test_dashboard_service_tdd.py --reuse-db --no-migrations -v 2>&1 | head -150
# source /opt/venv/bin/activate && pytest apps/reporting/tests/test_dashboard_service_tdd.py::TestEdgeCases::test_handles_empty_organisation --reuse-db --no-migrations -v 2>&1
# cd /home/project/Ledger-SG/apps/backend && export PGPASSWORD=ledgersg_secret_to_change && createdb -h localhost -U ledgersg test_ledgersg_dev 2>/dev/null || echo "DB already exists or creating..." && psql -h localhost -U ledgersg -d test_ledgersg_dev -f database_schema.sql > /dev/null 2>&1 && source /opt/venv/bin/activate && pytest tests/integration/test_organisation_settings.py::TestOrganisationSettingsView::test_get_settings_success -v --tb=short 2>&1 | tail -60

source /opt/venv/bin/activate && export PGPASSWORD=ledgersg_secret_to_change && dropdb -h localhost -U ledgersg test_ledgersg_dev 2>&1; createdb -h localhost -U ledgersg test_ledgersg_dev 2>&1; psql -h localhost -U ledgersg -d test_ledgersg_dev -f /home/project/Ledger-SG/database_schema.sql 2>&1 | tail -10

# source /opt/venv/bin/activate && python manage.py runserver 0.0.0.0:8000 > /tmp/backend.log 2>&1 &
# pkill -f "manage.py runserver" && sleep 2 && cd /home/project/Ledger-SG/apps/backend && source /opt/venv/bin/activate && python manage.py runserver 0.0.0.0:8000 > /tmp/django_server.log 2>&1 &
#
# pkill -f "runserver" && sleep 2 && source /opt/venv/bin/activate && python manage.py check --deploy 2>&1 | tail -30
# source /opt/venv/bin/activate && python manage.py check --deploy 2>&1 | tail -30
# Test CORS preflight with running server
# curl -s -X OPTIONS http://localhost:8000/api/v1/auth/me/ -i 2>&1 | head -25

cd /home/project/ledgersg/apps/backend && source /opt/venv/bin/activate && python manage.py runserver 0.0.0.0:8000

cd /home/project/ledgersg/apps/web && rm -rf .next && npm run build:server
pkill -f "node .next/standalone/server.js" 2>/dev/null; npm run build:server 2>&1

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

$ curl -X POST http://localhost:8000/api/v1/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"testpassword123"}' 2>&1 | grep -v "^  %" | python3 -m json.tool | grep -A 5 "refresh"

$ npm run build:server

> web@0.1.0 build:server
> NEXT_OUTPUT_MODE=standalone next build && cp -r .next/static .next/standalone/.next/

▲ Next.js 16.1.6 (Turbopack)
- Environments: .env.local

⚠ The "middleware" file convention is deprecated. Please use "proxy" instead. Learn more: https://nextjs.org/docs/messages/middleware-to-proxy
  Creating an optimized production build ...
✓ Compiled successfully in 13.3s
✓ Finished TypeScript in 8.9s
✓ Collecting page data using 3 workers in 576.8ms
✓ Generating static pages using 3 workers (19/19) in 626.7ms
✓ Finalizing page optimization in 3.5s

Route (app)
┌ ○ /
├ ○ /_not-found
├ ○ /banking
├ ○ /dashboard
├ ○ /invoices
├ ● /invoices/[id]
│ ├ /invoices/INV-2024-0001
│ ├ /invoices/INV-2024-0002
│ └ /invoices/INV-2024-0003
├ ● /invoices/[id]/edit
│ ├ /invoices/INV-2024-0001/edit
│ ├ /invoices/INV-2024-0002/edit
│ └ /invoices/INV-2024-0003/edit
├ ○ /invoices/new
├ ○ /ledger
├ ○ /login
├ ○ /quotes
├ ○ /reports
└ ○ /settings


ƒ Proxy (Middleware)

○  (Static)  prerendered as static content
●  (SSG)     prerendered as static HTML (uses generateStaticParams)

