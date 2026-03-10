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

---

# Check Redis via docker exec
$ docker exec ledgersg_redis redis-cli ping
PONG

---

$ curl -s -X POST "http://localhost:8000/api/v1/auth/login/" \
  -H "Content-Type: application/json" \
  -d '{"email": "admin@ledgersg.sg", "password": "admin123"}' 2>&1 | head -c 500

---

# Check existing users in database
$ docker exec -e PGPASSWORD=ledgersg_secret_to_change ledgersg_db psql -U ledgersg -d ledgersg_dev -c "SELECT id, email, is_superuser FROM core.app_user LIMIT 5;" 2>&1
id                  |       email       | is_superuser
--------------------------------------+-------------------+--------------
 ee2cdc44-503f-4864-9a36-005df148e650 | test@example.com  | f
 02e2e395-0adb-4ffd-8bf9-faef7aa51e1c | noorg@example.com | f
(2 rows)
# List core schema tables
$ docker exec -e PGPASSWORD=ledgersg_secret_to_change ledgersg_db psql -U ledgersg -d ledgersg_dev -c "\dt core.*" 2>&1 | head -20
List of relations
 Schema |         Name         | Type  |  Owner
--------+----------------------+-------+----------
 core   | app_user             | table | ledgersg
 core   | currency             | table | ledgersg
 core   | document_sequence    | table | ledgersg
 core   | exchange_rate        | table | ledgersg
 core   | fiscal_period        | table | ledgersg
 core   | fiscal_year          | table | ledgersg
 core   | organisation         | table | ledgersg
 core   | organisation_setting | table | ledgersg
 core   | role                 | table | ledgersg
 core   | user_organisation    | table | ledgersg
(10 rows)
Click to collapse
Thinking: Good, there are existing users. Let me check if the test user password is set properly or if I need to create a new user with a known password. Let me also check if tax codes exist
# Check existing tax codes
$ docker exec -e PGPASSWORD=ledgersg_secret_to_change ledgersg_db psql -U ledgersg -d ledgersg_dev -c "SELECT id, code, name, rate FROM coa.tax_code ORDER BY code;" 2>&1
ERROR:  relation "coa.tax_code" does not exist
LINE 1: SELECT id, code, name, rate FROM coa.tax_code ORDER BY code;
                                         ^
# Check account types
$ docker exec -e PGPASSWORD=ledgersg_secret_to_change ledgersg_db psql -U ledgersg -d ledgersg_dev -c "SELECT id, code, name FROM coa.account_type ORDER BY code;" 2>&1
id |     code      |        name
----+---------------+--------------------
  1 | ASSET         | Asset
  5 | COGS          | Cost of Goods Sold
  3 | EQUITY        | Equity
  6 | EXPENSE       | Expense
  2 | LIABILITY     | Liability
  8 | OTHER_EXPENSE | Other Expense
  7 | OTHER_INCOME  | Other Income
  4 | REVENUE       | Revenue

  ---
  
  # List all schemas
$ docker exec -e PGPASSWORD=ledgersg_secret_to_change ledgersg_db psql -U ledgersg -d ledgersg_dev -c "\dn" 2>&1
List of schemas
   Name    |       Owner       
-----------+-------------------
 audit     | ledgersg
 banking   | ledgersg
 coa       | ledgersg
 core      | ledgersg
 gst       | ledgersg
 invoicing | ledgersg
 journal   | ledgersg
…
Click to expand
# List GST schema tables
$ docker exec -e PGPASSWORD=ledgersg_secret_to_change ledgersg_db psql -U ledgersg -d ledgersg_dev -c "\dt gst.*" 2>&1
List of relations
 Schema |          Name           | Type  |  Owner   
--------+-------------------------+-------+----------
 gst    | peppol_transmission_log | table | ledgersg
 gst    | return                  | table | ledgersg
 gst    | tax_code                | table | ledgersg
 gst    | threshold_snapshot      | table | ledgersg
(4 rows) …

# Check test user password hash
$ docker exec -e PGPASSWORD=ledgersg_secret_to_change ledgersg_db psql -U ledgersg -d ledgersg_dev -c "SELECT id, email, password FROM core.app_user WHERE email='test@example.com';" 2>&1
id                  |      email       |                                         password
--------------------------------------+------------------+-------------------------------------------------------------------------------------------
 ee2cdc44-503f-4864-9a36-005df148e650 | test@example.com | pbkdf2_sha256$1200000$zcRARKkJC4v6g1hXSJtBYs$OS6dVCw3fD4E/lBYHAz9wB6hDs5JdofQnzjuiM9/WvI=
(1 row)

$ docker exec -e PGPASSWORD=ledgersg_secret_to_change ledgersg_db psql -U ledgersg -d ledgersg_dev -c "\d gst.tax_code" 2>&1
Table "gst.tax_code"
      Column       |           Type           | Collation | Nullable |      Default       
-------------------+--------------------------+-----------+----------+--------------------
 id                | uuid                     |           | not null | gen_random_uuid()
 org_id            | uuid                     |           |          | 
 code              | character varying(10)    |           | not null | 
 name              | character varying(150)   |           |          | 
 description       | character varying(150)   |           | not null | 
 rate              | numeric(5,4)             |           | not null | 
 is_gst_charged    | boolean                  |           | not null | true
…

# Try login with common test password
$ curl -s -X POST "http://localhost:8000/api/v1/auth/login/" \
  -H "Content-Type: application/json" \
  -d '{"email": "test@example.com", "password": "testpass123"}' 2>&1
{"error":{"code":"validation_error","message":"Invalid email or password."}}

---

# Test login with reset password
$ curl -s -X POST "http://localhost:8000/api/v1/auth/login/" \
  -H "Content-Type: application/json" \
  -d '{"email": "test@example.com", "password": "testpass123"}' | jq '.' 2>&1
{
  "user": {
    "id": "ee2cdc44-503f-4864-9a36-005df148e650",
    "email": "test@example.com",
    "full_name": "Test User",
    "phone": "",
    "created_at": "2026-03-08T00:51:16.075645+08:00"
  },
  "tokens": {
    "access": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoiYWNjZXNzIiwiZXhwIjoxNzcyOTQwNTkzLCJpYXQiOjE3NzI5MzY5OTMsImp0aSI6ImI1OGZiZWZjZTlmYzRiYTliM2YzZTQ5YWYzZTJhZjAyIiwidXNlcl9pZCI6ImVlMmNkYzQ0LTUwM2YtNDg2NC05YTM2LTAwNWRmMTQ4ZTY1MCIsImRlZmF1bHRfb3JnX2lkIjoiNjVhYmJjZDYtNjEyOS00MWVmLTgyZWQtOWU4NGEzNDQyYzdmIiwiZGVmYXVsdF9vcmdfbmFtZSI6IlRlc3QgT3JnYW5pc2F0aW9uIn0.A5MKTg_aGm5Mjg2aqesus_GTJigu07Au2DiDWDM_Dn0",
…
Click to expand
Thinking: Excellent! Login works. Now I have a valid access token. Let me extract the token and test some of the workflow steps. Let me also note the organisation ID from the token: `65abbcd6-6129-41ef-82ed-9e84a3442c7
# Set token and org ID for testing
$ export TOKEN="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoiYWNjZXNzIiwiZXhwIjoxNzcyOTQwNTkzLCJpYXQiOjE3NzI5MzY5OTMsImp0aSI6ImI1OGZiZWZjZTlmYzRiYTliM2YzZTQ5YWYzZTJhZjAyIiwidXNlcl9pZCI6ImVlMmNkYzQ0LTUwM2YtNDg2NC05YTM2LTAwNWRmMTQ4ZTY1MCIsImRlZmF1bHRfb3JnX2lkIjoiNjVhYmJjZDYtNjEyOS00MWVmLTgyZWQtOWU4NGEzNDQyYzdmIiwiZGVmYXVsdF9vcmdfbmFtZSI6IlRlc3QgT3JnYW5pc2F0aW9uIn0.A5MKTg_aGm5Mjg2aqesus_GTJigu07Au2DiDWDM_Dn0" && export ORG_ID="65abbcd6-6129-41ef-82ed-9e84a3442c7f" && echo "Token and Org ID set"
Token and Org ID set

---

# Check Django server output for actual errors
$ ps aux | grep "manage.py" | grep -v grep | awk '{print $2}' | xargs kill -HUP 2>/dev/null; sleep 1; cd /home/project/Ledger-SG/apps/backend && source /opt/venv/bin/activate && timeout 10 python manage.py runserver 0.0.0.0:8000 2>&1 | tail -50 &

---

# Verify Django is running
$ curl -s http://localhost:8000/api/v1/health/ 2>&1
{"status": "healthy", "database": "connected", "version": "1.0.0"}
# Get fresh auth token
$ curl -s -X POST "http://localhost:8000/api/v1/auth/login/" \
  -H "Content-Type: application/json" \
  -d '{"email": "test@example.com", "password": "testpass123"}' | jq -r '.tokens.access' 2>/dev/null
eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoiYWNjZXNzIiwiZXhwIjoxNzcyOTQ5ODE3LCJpYXQiOjE3NzI5NDYyMTcsImp0aSI6IjMzNmFkMWU5MjBlYTQxYzk4YWYxMDYzMzIxMmFjODU1IiwidXNlcl9pZCI6ImVlMmNkYzQ0LTUwM2YtNDg2NC05YTM2LTAwNWRmMTQ4ZTY1MCIsImRlZmF1bHRfb3JnX2lkIjoiNjVhYmJjZDYtNjEyOS00MWVmLTgyZWQtOWU4NGEzNDQyYzdmIiwiZGVmYXVsdF9vcmdfbmFtZSI6IlRlc3QgT3JnYW5pc2F0aW9uIn0.3k6SSn82QZj3yftMGM19st2VjXIzVh42uZbf1EQASxU

---

# Run all auth tests from web directory
$ cd /home/project/Ledger-SG/apps/web && npm test -- src/lib/__tests__/api-client-auth.test.ts --reporter=verbose 2>&1

---

# Run organisations architecture tests from web directory
$ cd /home/project/Ledger-SG/apps/web && npm test -- src/lib/__tests__/api-client-organisations.test.ts --reporter=verbose 2>&1

