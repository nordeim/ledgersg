# Deployment Guide — LedgerSG

**Deploy the entire application (backend + frontend) on a freshly installed
host, starting from `git clone`.** LedgerSG ships as two applications over
one PostgreSQL database plus one Redis: a Django 6 REST API (`apps/backend`),
a Next.js 16 web app (`apps/web`), PostgreSQL 16+ with a hand-written SQL
schema (the source of truth — Django migrations are permanently disabled),
and Redis (the Django cache AND the Celery broker). This revision
(2026-11-27, session 36 / P18) re-verified the guide against the current
codebase on a live sandbox (backend 914P/0F/5S, vitest 601/601, typecheck
0 errors, whole-tree eslint 0 errors / 5 parity warnings, build:server
green, the production-CSP smoke 5/5, live e2e 40P/0F/0S (40 specs), the
runtime-role smoke 13/13 as `ledgersg_app`, the mobile-nav probe 17/17) —
carrying the P17 concurrency truth forward (double-reversal / double-void /
double-reconcile refused under row locks; the 400-contract sweep; the Celery
tenant context; the `/admin/` gate; the `STORAGES` manifest migration) and
adding the P18 batch: the statutory-record locks on generate/review F5, the
unallocate/unreconcile/convert/credit-cap row locks, the header/archived
account posting gate, the remaining three Peppol task bodies under the RLS
tenant context, the on-commit dispatch coverage, the §15c completion
(admin opt-in tables) — on schema **v1.2.2** (v1.2.1 + django_session +
django_admin_log for the ENABLE_ADMIN opt-in; the API itself never touches
them).

Verified truths this guide is built on: the schema file
`apps/backend/database_schema.sql` (v1.2.2) CREATEs ROLEs inside DO blocks
so the loader must connect as a SUPERUSER; the backend suite requires
`--reuse-db --no-migrations` against a pre-initialised `test_ledgersg_dev`;
Redis on `:6379` is a hard prerequisite even for dev (the tenant middleware
membership cache); the web app reads exactly `NEXT_PUBLIC_API_URL` and
`NEXT_OUTPUT_MODE` (P2/B-4 audit; `BACKEND_URL` is reserved — P7/F-13);
money is `NUMERIC(19,4)` (§16 of the schema carries the in-place widening
migration for databases created on ≤ v1.0.2).

---

## Step-by-step overview

| Step | Section | What you end up with |
|---|---|---|
| 0 | §1 | Prerequisites checked |
| 1 | §2 | The repo cloned |
| 2 | §3 | PostgreSQL running on :5432, role + both databases created |
| 3 | §4 | The SQL schema loaded (BOTH databases) |
| 4 | §5 | Redis running on :6379 |
| 5 | §6 | Backend venv installed, `manage.py check` green |
| 6 | §7 | Backend verified: full pytest suite green |
| 7 | §8 | Backend serving on :8000 |
| 8 | §9 | Frontend installed and serving on :3000 |
| 9 | §10 | (Optional) Celery worker for async tasks |
| 10 | §11 | End-to-end verification checklist |
| 11 | §12 | Production notes (Gunicorn, secrets, cookies, backups) |
| — | §13 | Updating an existing deployment |
| — | §14 | Common issues |
| — | §15 | Pushing changes to this repository |

---

## 1. Prerequisites

- **Python 3.12+** with `venv` (on Debian/Ubuntu: `sudo apt-get install python3.12 python3.12-venv` — the bare `python3` may lack ensurepip). The canonical manifest is
  `apps/backend/pyproject.toml` (`pip install -e ".[dev]"`). The root
  `requirements.txt` is a stale second manifest — do not use it.
- **Node.js 20+** with npm. `apps/web/package-lock.json` is the lockfile.
- **A reachable PostgreSQL 16+**. The **rootless install in §3 is the
  documented and verified method** and needs no root. Any other PostgreSQL —
  system service, Docker, or a managed instance — works identically; the
  application only ever sees `DB_*` variables. The §3 script defaults its install prefix to the sandbox layout `/home/z/my-project/pg` — export `PG_BASE="$HOME/pg"` first on any other host (P18/DOC-M9; everything derives from it). One caveat: the schema file's
  DO blocks CREATE ROLEs, so the **loading role must be SUPERUSER** (the dev
  role `ledgersg` is created SUPERUSER for exactly this reason; the runtime
  application role is `ledgersg_app`, which the schema grants and RLS binds).
- **A reachable Redis 7.x or 8.x** on `:6379` (or set `REDIS_URL`; the 6.4.0 pin in pyproject is the Python client, not the server — both server majors are verified). Rootless
  method in §5.
- `git`, `curl`, and on Debian/Ubuntu `apt-get` (for the rootless
  PostgreSQL/Redis package extraction).
- Ports free: **3000** (web), **8000** (API), **5432** (PostgreSQL),
  **6379** (Redis).

## 2. Clone the repository

```bash
git clone https://github.com/nordeim/ledgersg.git
cd ledgersg
```

Nothing is read from the repo root `.env` — each app has its own audited
template (backend: 17 settings-read vars, all listed — ENABLE_ADMIN and LOG_DIR included; web: live vars +
a clearly-marked reserved section):

```bash
cp apps/backend/.env.example apps/backend/.env
cp apps/web/.env.example    apps/web/.env.local
```

Edit `apps/backend/.env` now: set `SECRET_KEY` (the production settings
refuse to boot on the placeholder — H-06 gate), `ALLOWED_HOSTS`,
`CORS_ALLOWED_ORIGINS` (must include the web origin), and the `DB_*` values
matching §3. Edit `apps/web/.env.local`: `NEXT_PUBLIC_API_URL` pointing at
the backend (browser-facing; `http://localhost:8000` for dev) and
`NEXT_OUTPUT_MODE` (`standalone` for server mode — see §9).

## 3. Install PostgreSQL (rootless — the verified path)

`docs/setup_pg_z.sh` installs PostgreSQL without root (Debian/Ubuntu:
`apt-get download postgresql-17 …` extracted with `dpkg-deb -x` into a
user-owned prefix), initialises it on `:5432` loopback-only, and starts it:

```bash
bash docs/setup_pg_z.sh
# [pg] ready: postgresql://postgres:postgres@127.0.0.1:5432/app_db
```

The script's own database (`app_db`) belongs to a sibling repo's contract —
LedgerSG creates its own role and databases (run once; SUPERUSER is
required because the schema CREATEs ROLEs in DO blocks):

```bash
PGBIN=/home/z/my-project/pg/root/usr/lib/postgresql/17/bin
"$PGBIN/psql" -h 127.0.0.1 -U postgres -d postgres -c \
  "CREATE ROLE ledgersg WITH LOGIN PASSWORD 'ledgersg_secret_to_change' SUPERUSER;"
for db in ledgersg_dev test_ledgersg_dev; do
  "$PGBIN/psql" -h 127.0.0.1 -U postgres -d postgres -c "CREATE DATABASE $db OWNER ledgersg;"
done
```

(When prompted, the postgres role's password is `postgres`. On a system
PostgreSQL, use its superuser for these two commands instead.)

Lifecycle (logs under `/home/z/my-project/pg/log/`):

```bash
"$PGBIN/pg_ctl" -D /home/z/my-project/pg/data status
# stop / restart: same command with "stop" / "restart"
```

On another host, any PostgreSQL works — keep the `DB_*` values in
`apps/backend/.env` in lockstep. See `skills/rootless-postgresql/SKILL.md`
for the full runbook (the `skills/` folder is reference material, not part
of the build).

## 4. Load the SQL schema (SQL-First — never run migrations)

The schema is the source of truth; Django models are unmanaged mirrors
(`managed = False`, `MIGRATE = False`). Load it into **both** databases —
`test_ledgersg_dev` is what the pytest suite runs against:

```bash
cd apps/backend
export PGPASSWORD=ledgersg_secret_to_change
psql -h 127.0.0.1 -U ledgersg -d ledgersg_dev     -f database_schema.sql
psql -h 127.0.0.1 -U ledgersg -d test_ledgersg_dev -f database_schema.sql
```

Verify (a fresh v1.2.2 load carries 29 domain tables + 1 view in the
seven domain schemas this query counts = 30; the token-blacklist (§15b)
and Django framework tables (§15c) live in `public` and are NOT counted
here — the count is 30 on any schema-load-only host. A database that
ever ran `manage.py migrate` historically carries extra legacy rows in
`core` and counts higher; only the 30 are required. Money at 19,4):

```bash
psql -h 127.0.0.1 -U ledgersg -d ledgersg_dev -tAc \
  "SELECT count(*) FROM information_schema.tables WHERE table_schema IN ('core','coa','gst','journal','invoicing','banking','audit');"
# 30
psql -h 127.0.0.1 -U ledgersg -d ledgersg_dev -tAc \
  "SELECT count(*) FROM information_schema.columns WHERE table_schema IN ('core','coa','gst','journal','invoicing','banking','audit') AND data_type='numeric' AND numeric_precision=19 AND numeric_scale=4;"
# 47
```

**Existing database on schema ≤ v1.0.2?** Do not re-load. Apply the §16
in-place widening block at the end of `database_schema.sql` (monetary
columns 10,4 → 19,4; idempotent — it skips when nothing remains):

```bash
psql -h 127.0.0.1 -U ledgersg -d ledgersg_dev -f - < <(sed -n '/^-- §16/,/^-- §17/p' database_schema.sql)
```

**Existing database on schema v1.1.0 (post-widening, pre-P15)?** Apply the
§17 RLS-completion block (idempotent DO blocks — safe to re-run):

```bash
cd apps/backend
psql -h 127.0.0.1 -U ledgersg -d ledgersg_dev -f - < <(sed -n '/^-- §17/,/^-- ╚══/p' database_schema.sql)
# Verify: every tenant table has row-level security enabled
psql -h 127.0.0.1 -U ledgersg -d ledgersg_dev -c \
  "SELECT n.nspname||'.'||c.relname FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname IN ('core','gst','audit','invoicing','banking','journal','coa') AND c.relkind='r' AND NOT c.relrowsecurity AND c.relname NOT IN ('app_user','currency','account_type','account_sub_type');"
# (expected: 0 rows — only the documented globals are un-scoped)
```

**Existing database on schema v1.2.0 (pre-P17)?** Apply the §15c block
(idempotent `CREATE TABLE IF NOT EXISTS` — safe even on databases that
already carry some of these tables):

```bash
cd apps/backend
psql -h 127.0.0.1 -U ledgersg -d ledgersg_dev -f - < <(sed -n '/^-- §15c/,/^-- §16/p' database_schema.sql)
```

The §15c tables let the pytest suite run transactional test classes — the
teardown flush needs `django_session` / `django_admin_log` /
`django_content_type` (the P17 fresh-host gap: on a schema-only v1.2.0
database every transactional teardown errored out).

**Never run `python manage.py makemigrations`** — schema changes are
hand-written DDL patches + version bump + model alignment, gated by
`tests/invariants/test_schema_conformance.py`.

## 5. Install Redis (rootless)

The backend 500s every org-scoped request with `tenant_context_error`
without Redis (the membership cache). Rootless install on Debian/Ubuntu:

```bash
mkdir -p ~/redis/deb ~/redis/root && cd ~/redis/deb
apt-get download redis-server redis-tools liblzf1
for f in *.deb; do dpkg-deb -x "$f" ~/redis/root/; done
export LD_LIBRARY_PATH=~/redis/root/usr/lib/x86_64-linux-gnu
~/redis/root/usr/bin/redis-server --daemonize yes --port 6379 \
  --dir ~/redis --save '' --appendonly no
~/redis/root/usr/bin/redis-cli -p 6379 ping   # PONG
```

(`liblzf1` is required by the extracted redis binaries. A system
`redis-server` or a managed Redis is equally fine — point `REDIS_URL` at it.)

## 6. Backend install

```bash
cd apps/backend
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
python manage.py check     # 0 errors (1 known django_ratelimit W001)
```

## 7. Backend verification (the suite must be green)

```bash
export DB_NAME=test_ledgersg_dev DB_USER=ledgersg DB_PASSWORD=ledgersg_secret_to_change \
       DB_HOST=127.0.0.1 DB_PORT=5432
pytest --reuse-db --no-migrations -q
# expected (post-2026-11-27 P18): 914 passed, 0 failed, 5 skipped
pytest tests/invariants -q    # 34 passed (conformance, capacity, balances,
                              # filed-return immutability, GST lock, RLS)
pytest tests/security -q      # 83 passed, 3 skipped (RLS, tokens, cookies,
                              # posture gates incl. the service-key gate)
```

(The `DB_NAME` export overrides `apps/backend/.env` — which points at the
dev database — so the runner targets the pre-initialised `test_ledgersg_dev`
instead of prompting to destroy `ledgersg_dev`. And note: `manage.py test` is
NOT this repo's runner — the custom SchemaTestRunner it would use targets
`DB_NAME` too; always drive the suite with pytest as above.)

## 8. Run the backend

Development:

```bash
python manage.py runserver 127.0.0.1:8000
curl http://127.0.0.1:8000/api/v1/health/
# {"status": "healthy", "database": "connected", "version": "1.0.0"}
```

Production serves with Gunicorn (the `production` settings module). Three
requirements: the **`LOG_DIR` directory must exist and be writable by
the service user** before the boot (the file handler logs there — see
`apps/backend/.env.example`), `SECRET_KEY` must be real (§12), and
**static files must be collected before the first boot** — production
uses WhiteNoise's `CompressedManifestStaticFilesStorage` (P17/BE-L4),
which requires the `staticfiles/` manifest; without `collectstatic`
every static URL 404s and HTML surfaces that reference `{% static %}`
(the browsable API, `/admin/` under `ENABLE_ADMIN`) raise
"Missing staticfiles manifest entry":

```bash
sudo mkdir -p /var/log/ledgersg && sudo chown $SERVICE_USER /var/log/ledgersg
# or set LOG_DIR in .env to a directory you own
# Collect static files (idempotent; safe to re-run after upgrades):
DJANGO_SETTINGS_MODULE=config.settings.production \
python manage.py collectstatic --noinput
DJANGO_SETTINGS_MODULE=config.settings.production \
gunicorn config.wsgi:application --bind 127.0.0.1:8000 --workers 3
```

## 9. Frontend install and run

```bash
cd apps/web
npm install
npx playwright install chromium   # once per environment (e2e suites)
# (on a bare Debian/Ubuntu host: npx playwright install --with-deps chromium
#  installs the system libraries headless chromium needs)
```

Development server (hot reload; expects the backend on :8000):

```bash
npm run dev          # http://localhost:3000
```

Production server build (standalone — the ONLY supported build since
P10/M-12; the static-export mode was retired because API-driven detail
routes cannot prerender):

```bash
npm run build:server         # NEXT_OUTPUT_MODE=standalone + static copy
npm run start                # node .next/standalone/server.js
```

**P16/FE-C1 — the production-CSP smoke (run after every production build).**
The production CSP is per-request nonce-based (`src/proxy.ts` +
`src/lib/csp.ts`); the dev-mode test suite cannot cover the production
branch (dev CSP allows `unsafe-inline`). The smoke builds nothing itself —
it boots the standalone output on a scratch port and asserts the served
nonce, hydration and zero CSP violations:

```bash
# from the repo root, after `npm run build:server` in apps/web:
node scripts/prod-csp-smoke.js   # 5/5 checks (nonce, no unsafe-inline,
                                 # hydration, zero violations, shell renders)
```

Frontend gates (run before every push):

```bash
npm run typecheck           # 0 errors
npm test                    # 601 vitest tests
npm run test:coverage       # green at the honest measured-floor ratchet
npm run build:server        # the only build mode
npm run test:e2e            # green without a backend (gated specs skip)
```

The full live gate (`npm run test:e2e:full`) additionally needs the dev DB
bootstrapped with a demo user, organisation, contact and posted accounting
activity (the banking + P11 specs' dependency). The e2e specs read
`E2E_DEMO_EMAIL` / `E2E_DEMO_PASSWORD` (defaults `demo@ledgersg.sg` /
`demo1234` — override with a 12+ char password to satisfy the register floor).
Bootstrap through the public API (idempotent — reuse what exists), then run
the suite serially:

```bash
export E2E_API_URL=http://127.0.0.1:8000 E2E_DEMO_EMAIL=demo@ledgersg.sg \
       E2E_DEMO_PASSWORD=demo1234pass
# 1) register/login the demo user:  POST /api/v1/auth/register/
#    {"full_name":"Demo User","email":"demo@ledgersg.sg","password":"demo1234pass"}
#    (201 with tokens; 200 login if the user already exists)
# 2) create the demo org with the token:  POST /api/v1/organisations/
#    {"name":"Ledger Demo Pte Ltd","uen":"202612345D","entity_type":"PRIVATE_LIMITED",
#     "gst_registered":true,"gst_reg_number":"M9034567K","gst_reg_date":"2026-01-01",
#     "fy_start_month":1,"base_currency":"SGD"}   (seeds CoA + fiscal year + tax codes)
# 3) create a contact (the P11 contacts specs' prefill substrate):
#    POST /api/v1/{org}/invoicing/contacts/  {"name":"Demo Trading Pte Ltd", ...}
#    then PATCH the detail with a truthful profile
#    (uen, gst_reg_number, peppol_id — the edit dialog prefills from DETAIL)
# 4) post one invoice and one credit note (the C-1/F5 truth substrate):
#    POST /api/v1/{org}/invoicing/documents/  with  document_type SALES_INVOICE
#    and SALES_CREDIT_NOTE (a credit note additionally carries
#    "related_document_id": <the invoice's id> — the P11 linkage contract;
#    issue_date inside an open fiscal period; lines
#    reference a REVENUE account id and optionally the SR tax code), then
#    POST …/documents/{id}/approve/  for each (posts the journal entries —
#    the credit note's are direction-reversed, P11/C-1)
# 5) compute an F5 return:  POST /api/v1/{org}/gst/returns/
#    {"filing_frequency":"MONTHLY","start_date":"<month>-01","periods":1}
#    then POST /api/v1/{org}/gst/returns/{id}/?force=true
npm run test:e2e:full       # 40 specs: 11 always + 29 backend-gated
                           # (40/40 live-green, P13)
```

(The p11 spec's `ensureDemoActivity` performs steps 3–5 idempotently itself
— a fresh DB self-bootstraps on the first run.)

## 10. (Optional) Celery worker — async tasks

PDF generation, invoice email delivery and InvoiceNow transmission run as
Celery tasks. Development can run them inline (`CELERY_ALWAYS_EAGER=true`
is the dev default); otherwise start a worker:

```bash
cd apps/backend && source .venv/bin/activate
celery -A config worker -l info
```

## 11. End-to-end verification checklist

```bash
# 1. Backend health
curl http://127.0.0.1:8000/api/v1/health/
# {"status": "healthy", "database": "connected", ...}

# 2. Frontend up
curl -s -o /dev/null -w "%{http_code}\n" http://localhost:3000/login/  # 200 (the canonical URL —
# next.config.ts sets trailingSlash: true, so /login 308-redirects to /login/;
# curl without -L would print 308)

# 3. Login sets BOTH cookies (P4 flow) — refresh works via the cookie alone
curl -s -c /tmp/cj.txt -X POST http://127.0.0.1:8000/api/v1/auth/login/ \
  -H 'Content-Type: application/json' \
  -d '{"email":"demo@ledgersg.sg","password":"demo1234pass"}' -o /dev/null -w '%{http_code}\n'
# 200 — /tmp/cj.txt contains refresh_token (HttpOnly) + session_hint
curl -s -b /tmp/cj.txt -X POST http://127.0.0.1:8000/api/v1/auth/refresh/ \
  -H 'Content-Type: application/json' -d '{}' -o /dev/null -w '%{http_code}\n'
# 200 — the cookie alone refreshes (rotation re-sets it)

# 3b. Bearer token + the default org id for the API spot checks below
#     (JWT-only endpoints — the cookie jar is for the refresh flow only):
TOKEN=$(curl -s -X POST http://127.0.0.1:8000/api/v1/auth/login/ \
  -H 'Content-Type: application/json' \
  -d '{"email":"demo@ledgersg.sg","password":"demo1234pass"}' \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['tokens']['access'])")
export ORG_ID=$(curl -s -H "Authorization: Bearer $TOKEN" \
  http://127.0.0.1:8000/api/v1/auth/organisations/ \
  | python3 -c "import sys,json; print(json.load(sys.stdin)[0]['org']['id'])")
echo "org: $ORG_ID"

# 4. Browser: log in at http://localhost:3000, press F5 — you must stay on
#    /dashboard (the reload-persistence acceptance test, e2e/session.spec.ts)

# 5. P7 API-truth spot checks
#    - fiscal periods route (was 404 pre-P7):
curl -s -o /dev/null -w '%{http_code}\n' -H "Authorization: Bearer $TOKEN" \
  "http://127.0.0.1:8000/api/v1/$ORG_ID/fiscal-periods/"   # 200 (with auth)
#    - malformed query params are 400s, not 500s:
curl -s -o /dev/null -w '%{http_code}\n' -H "Authorization: Bearer $TOKEN" \
  "http://127.0.0.1:8000/api/v1/$ORG_ID/journal-entries/entries/?date_from=garbage"  # 400

# 6. P8 reporting-truth spot checks
#    - financial reports (the route is single-prefixed /reports/financial/):
curl -s -o /dev/null -w '%{http_code}\n' -H "Authorization: Bearer $TOKEN" \
  "http://127.0.0.1:8000/api/v1/$ORG_ID/reports/financial/?report_type=trial_balance&as_at_date=2026-12-31"  # 200
#    - aged receivables buckets:
curl -s -o /dev/null -w '%{http_code}\n' -H "Authorization: Bearer $TOKEN" \
  "http://127.0.0.1:8000/api/v1/$ORG_ID/reports/aged/?type=receivables"   # 200
#    - quotes list via the type filter key the backend reads:
curl -s -o /dev/null -w '%{http_code}\n' -H "Authorization: Bearer $TOKEN" \
  "http://127.0.0.1:8000/api/v1/$ORG_ID/invoicing/documents/?type=SALES_QUOTE"  # 200

# 7. Browser (P8): open /reports — the tabs (Trial Balance / P&L / Balance
#    Sheet / GST F5 / Aged AR-AP) render real statements (rows or an
#    explicit empty state); open /quotes — the list, New Quote form and
#    the quote detail (QUOTATION framing + Convert) are live.

# 8. P9 onboarding + banking spot checks
#    - the seeded bank accounts are filterable (children of the 1000 header):
curl -s -o /dev/null -w '%{http_code}\n' -H "Authorization: Bearer $TOKEN" \
  "http://127.0.0.1:8000/api/v1/$ORG_ID/accounts/?is_bank=true"        # 200 (results non-empty)
#    - the aged report honours its as-at date (docs issued after it are excluded)
#    - InvoiceNow refuses non-invoice types (a converted quote is APPROVED
#      but must not transmit as a UBL Invoice):
#      POST /invoicing/documents/{quote_id}/send-invoicenow/ -> 400 naming the type
#    - the bank-account create accepts null PayNow (the no-PayNow wire value):
#      POST /banking/bank-accounts/ with "paynow_type": null -> 201
#    - Browser (P9): /settings/organisations/new renders the create form
#      (the onboarding dead-end closer); /banking — the Add Account dialog
#      opens with bank-type GL options; Receive Payment picks contacts
#      through the searchable picker and lists the contact's open invoices
#      for allocation; the dashboard shows only real figures.

# 9. P10 self-serve + compliance spot checks
#    - duplicate organisation UEN is a clean 400 (was an IntegrityError 500):
#      POST /api/v1/organisations/ with an existing UEN -> 400 {"uen": [...]}
#    - a rate-limited request returns the 429 contract (not a raw 403):
#      burst past a limit -> 429 {"error":{"code":"rate_limit_exceeded",
#      "details":{"retry_after":60}}} with a Retry-After header
#    - the fiscal-period open endpoint (P10/M-8):
#      POST /api/v1/$ORG_ID/fiscal-periods/{period_id}/open/ -> 200 (manager)
#    - the GST F5 review route (P10/H-3):
#      POST /api/v1/$ORG_ID/gst/returns/{return_id}/review/ -> 200 (manager)
#    - Browser (P10): /register — a fresh visitor can self-serve (register →
#      org creation → dashboard; the anonymous 401 never bounces them);
#      /contacts — search, edit, deactivate; /invoices/new — the Customer
#      picker defaults to existing contacts (no contact row created);
#      /reports GST F5 tab — create periods, compute, review, file, amend +
#      the next-filing deadline banner; /settings — change password + the
#      InvoiceNow card + fiscal open/close; /banking Accounts — per-row Edit
#      + deactivate; Payments — per-payment allocation rows with a toggle.

# 10. P11 accounting-truth spot checks
#    - a credit note posts REVERSED journal lines (P11/C-1): after approving
#      one SALES_INVOICE and one SALES_CREDIT_NOTE, the ledger shows the
#      invoice's AR-debit/revenue-credit/gst-credit and the credit note's
#      AR-CREDIT/revenue-debit/gst-debit — mirror images:
#      GET /api/v1/$ORG_ID/journal-entries/entries/  (or /ledger in the UI)
#    - the F5 boxes net credit notes (P11/H-3): with a 2500.00 SR-9% invoice
#      and a 750.00 SR-9% credit note in the period, Box 1 = 1750.00 and
#      Box 6 output tax = 157.50 — the credit note NETS, never adds.
#    - the F5 boxes panel renders REAL values (P11/H-2): /reports → GST F5
#      tab → View boxes — monetary values, never the pre-P11 "—" row
#    - the dashboard GST payable is REAL (P11/H-4): equals the F5 net GST
#      (e.g. "SGD 315.00"), never the pre-P11 hardcoded 0.00; single
#      currency prefixes (no "S$ SGD …" doubling)
#    - the contacts edit round-trip tells the truth (P11/H-1 + M-4):
#      /contacts → Edit — the dialog PREFILLS uen / GST Registration No /
#      Peppol ID from the detail endpoint, and a save PERSISTS them (a
#      saved dialog never silently wipes those fields)
#    - garbage path UUIDs 404 at the routing layer (P11/M-6):
#      GET /api/v1/$ORG_ID/invoicing/documents/not-a-uuid/ -> 404 (not 500)
#    - the org settings PATCH accepts choice fields and 400s garbage
#      (P11/M-5): PATCH base_currency="garbage" -> 400; timezone="Asia/Singapore" -> 200
#    - garbage env combinations boot cleanly (P11/H-5):
#      DEBUG=true + DEBUG_TOOLBAR=false starts and serves (no ImportError)
```

The full e2e run performs ~30 logins/refreshes. The dev settings budgets
(`LOGIN_RATELIMIT_IP` 60/min, `LOGIN_RATELIMIT_USER` 120/min,
`REFRESH_RATELIMIT_IP` 240/min — the P10 pass raised the per-user login
budget after the suite's tail tripped the base 30/min; P11 added
`REGISTER_RATELIMIT_IP` 120/hour after re-runs of the suite exhausted the
hardcoded 5/hour register literal) cover it; production keeps 10/min IP +
30/min user + 20/min refresh + 5/hour register. A rate-limited request now
returns the documented 429 `rate_limit_exceeded` contract (P10 — previously
a raw 403 "You do not have permission…", indistinguishable from an authz
failure). If a dev run fails only on login/refresh 429s, flush the dev cache
(`redis-cli -n 0 FLUSHDB`) or wait out the window.

## 12. Production notes

- **SECRET_KEY**: `config.settings.production` refuses the placeholder
  (H-06). Generate one:
  `python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"`.
- **LOG_DIR (P11/C-2)**: the production settings build the file-handler log
  path from `LOG_DIR` (default `/var/log/ledgersg`) with copy-on-write
  LOGGING — create the directory before boot (§8). A missing directory is
  the one documented production-boot crash of the P11 audit.
- **Cache backend**: production uses the **builtin
  `django.core.cache.backends.redis.RedisCache`** (P11/C-2 — production
  previously declared `django_redis`, a dependency production never
  installs, so every cache touch crashed the boot). The builtin backend is
  served by the same `REDIS_URL`.
- **CORS**: `CORS_ALLOWED_ORIGINS` must list the exact web origin(s)
  (scheme + host + port). The preflight path skips JWT (OPTIONS) via
  `CORSJWTAuthentication`.
- **RLS**: the runtime DB role is `ledgersg_app` (schema §15 grants; every
  table has `FORCE ROW LEVEL SECURITY` keyed on `app.current_org_id`).
  The dev role `ledgersg` is SUPERUSER only because the schema loader
  needs it — do not use it as the runtime role in production.
- **Rate limiting** is ON by default (`RATELIMIT_ENABLE=true`); login and
  refresh rates are settings knobs — production defaults 10/min per IP
  (login), 30/min per user, 20/min (refresh). Blocked requests return the
  429 `rate_limit_exceeded` contract with a `Retry-After` header (P10).
- **Session cookies (P4)**: the refresh cookie is `SameSite=Lax`, correct
  when web + API share a site. For a **cross-site production topology**
  (web on `app.example.com`, API on `api.example.com`), cookies must be
  `SameSite=None; Secure` — a one-line change in
  `apps/backend/apps/core/views/_refresh_cookie.py` plus HTTPS on both
  origins. The body-based refresh flow keeps working for API clients.
- **API error contract (P7)**: business errors return
  `{"error": {"code", "message", "details"}}` with the mapped status code
  (the custom exception handler is active and posture-gated); the web
  client surfaces `error.message` directly in toasts.
- **Money precision** is `NUMERIC(19,4)` — all Python money math goes
  through `common.decimal_utils.money()` (rejects floats).
- **Audit trail** (`audit.event_log`) is append-only with no UPDATE/DELETE
  grants to the application role (IRAS 5-year retention).
- **Backups**: standard `pg_dump` of the database is sufficient (schema +
  data + RLS policies all live in SQL).

### 12.1 Process management (systemd)

Nothing in this repo ships process units; a bare `runserver`/`npm start`
dies with its terminal. On a fresh host use systemd units (templates —
adjust users/paths):

```ini
# /etc/systemd/system/ledgersg-backend.service
[Unit]
Description=LedgerSG API (gunicorn)
After=network.target postgresql.service redis.service

[Service]
User=ledgersg
WorkingDirectory=/opt/ledgersg/apps/backend
EnvironmentFile=/opt/ledgersg/apps/backend/.env
# The manifest storage needs staticfiles/ present before every boot
# (idempotent; P18/DOC-M1 — mirrors the §8 manual step):
ExecStartPre=/opt/ledgersg/apps/backend/.venv/bin/python manage.py collectstatic --noinput
ExecStart=/opt/ledgersg/apps/backend/.venv/bin/gunicorn config.wsgi:application \
    --bind 127.0.0.1:8000 --workers 3 --timeout 60
Restart=always

[Install]
WantedBy=multi-user.target
```

```ini
# /etc/systemd/system/ledgersg-web.service
[Unit]
Description=LedgerSG web (Next.js standalone)
After=network.target ledgersg-backend.service

[Service]
User=ledgersg
WorkingDirectory=/opt/ledgersg/apps/web
Environment=NODE_ENV=production PORT=3000
EnvironmentFile=/opt/ledgersg/apps/web/.env.local
ExecStart=/usr/bin/node .next/standalone/server.js
Restart=always

[Install]
WantedBy=multi-user.target
```

Plus a Celery unit (`celery -A config worker`) if asynchronous InvoiceNow
transmission is used. Enable with `systemctl enable --now <unit>`.

### 12.2 Reverse proxy and TLS (nginx)

`config.settings.production` forces `SECURE_SSL_REDIRECT=True`, HSTS and
`SECURE_PROXY_SSL_HEADER` — the API MUST sit behind a TLS-terminating
proxy or it redirect-loops. Minimal nginx shape:

```nginx
server {
    listen 443 ssl http2;
    server_name api.ledgersg.sg;           # your API host
    ssl_certificate     /etc/letsencrypt/live/api.ledgersg.sg/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/api.ledgersg.sg/privkey.pem;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-Proto https;   # SECURE_PROXY_SSL_HEADER
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
}
# a twin server block proxies 127.0.0.1:3000 for the web host
```

Issue certificates with certbot (`certbot --nginx -d api.ledgersg.sg`).
Port 80 should redirect to 443 (Django also redirects at the app layer).

### 12.3 The runtime DB role's password

`database_schema.sql` creates `ledgersg_app` with the placeholder password
`CHANGE_ME_IN_PRODUCTION`. Before production traffic:

```bash
"$PGBIN/psql" -h 127.0.0.1 -U postgres -d <your-production-db> \
    -c "ALTER ROLE ledgersg_app PASSWORD '<a-real-secret>';"
```

then set `DB_USER=ledgersg_app` + that password in the backend `.env`
(the dev role `ledgersg` keeps its SUPERUSER for schema loads only).

**Verify the runtime role before traffic** (P14/C-1 + H-7 — the whole gate
previously ran as SUPERUSER, which bypasses RLS). Start a second backend
as the app role and walk the full onboarding path:

```bash
cd apps/backend && source .venv/bin/activate
DB_NAME=ledgersg_dev DB_USER=ledgersg_app DB_PASSWORD=<a-real-secret> \
DB_HOST=127.0.0.1 DB_PORT=5432 DJANGO_SETTINGS_MODULE=config.settings.development \
python manage.py runserver 127.0.0.1:8001 --noreload &
python ../../scripts/rls_smoke.py --base http://127.0.0.1:8001
# expected: "13/13 steps green as ledgersg_app" — register → create org
# (201 — the C-1 regression) → contact → invoice → approve (journal posts
# under RLS) → bank account → payment+allocation → F5 compute
```

### 12.4 Email (SMTP)

Invoice email delivery is a Celery task; production otherwise inherits
Django's default SMTP backend with no host. Configure an SMTP relay via
`EMAIL_HOST`/`EMAIL_HOST_USER`/`EMAIL_HOST_PASSWORD` environment additions
(extend `config/settings/production.py` when you wire them) — or leave
email tasks unwired and rely on the UI/Peppol channels.

### Optional: the Docker route

`apps/backend/Dockerfile` (backend) and `apps/backend/docker-compose.yml`
(backend + PostgreSQL + Redis) ship a container path fixed in P11 (H-6/H-7:
pinned installs, the gunicorn CMD so the container serves instead of
sleeping, compose credentials wired, and the removed-at-boot migrate step —
migrations are permanently disabled in this codebase, the schema loads via
`database_schema.sql`).

```bash
cd apps/backend              # the compose file lives here, not at the repo root
docker compose up -d          # backend on :8000 + postgres + redis
```

**Validated statically, not built in this environment** — the Dockerfile
and compose YAML were linted against the repo's own contracts (entrypoint,
env wiring, service dependencies) but no image was built or booted here.
The §1–§9 native path above is the fully verified one.

## 13. Updating an existing deployment

```bash
git pull
cd apps/backend && source .venv/bin/activate && pip install -e ".[dev]"
# schema changed? apply the versioned section from database_schema.sql (§4)
# to BOTH ledgersg_dev and test_ledgersg_dev — never re-load over live data
#   ≤ v1.0.2 → apply §16 (the NUMERIC(19,4) widening)
#   v1.1.0   → apply §17 (the RLS completion, v1.2.0)
#   v1.2.0   → apply §15c (the Django framework tables, v1.2.1)
#   v1.2.1   → apply the §15c v1.2.2 completion (django_session +
#              django_admin_log — only needed if you plan to enable
#              /admin/ via ENABLE_ADMIN; the API never touches them)
cd ../web && npm install
npm run build:server       # cold build for production
node ../../scripts/prod-csp-smoke.js   # P16: the CSP/hydration smoke gate
# restart gunicorn / node / celery
```

Then re-run the §7/§11 checklists; the invariant gates
(`pytest tests/invariants -q`) are the fastest signal that schema, models
and code still agree.

## 14. Common issues

| Symptom | Cause | Fix |
|---|---|---|
| `relation "core.app_user" does not exist` | Schema not loaded into the DB the app points at | §4 `psql -f database_schema.sql` into BOTH databases |
| 500 `tenant_context_error` on every org URL | Redis down (membership cache) | Start Redis on :6379 (§5); read the middleware log line |
| `numeric field overflow` on a ≥ S$1M amount | Database still on schema ≤ v1.0.2 (10,4 columns) | Apply the §16 widening block (§4) |
| `ModuleNotFoundError: django_celery_beat` in a fresh venv | Installing from the root `requirements.txt` | Install from `pyproject.toml`: `pip install -e ".[dev]"` |
| 403 on EVERY org-scoped URL | `UserOrganisation.accepted_at` is NULL (pending invitation) | Accept the membership (or set `accepted_at`) |
| Endpoint 404 that "exists" in a urls.py | Route defined in the shadowed `apps/core/urls.py` module | Register in the `apps/core/urls/` PACKAGE (P7/F-4) |
| In-view permission errors surface as 500 | Custom exception handler not active | Check `EXCEPTION_HANDLER` (not `DEFAULT_EXCEPTION_HANDLER`) in REST_FRAMEWORK (P7/F-19) |
| Dashboard "Loading..." stuck in production build | Missing static files in standalone output | `npm run build:server` (auto-copies `.next/static`) |
| Login silently does nothing | Password shorter than 12 chars — the native `minLength` on the register/change-password forms blocks the submit (the backend floor since the P10 audit: `AUTH_PASSWORD_VALIDATORS` `min_length: 12`) | Use a 12+ character password |
| e2e `Executable doesn't exist` | Declared browsers not installed | `npx playwright install chromium` |
| e2e full-run login/refresh 429s | Dev rate window spent | Dev budgets 60/120/240 per min (login IP / login user / refresh); flush the dev Redis cache or wait |
| e2e full-run register 429 (spec stuck on /register) | Repeated full-suite runs exhausted the 5/hour register budget (P11 turned it into the `REGISTER_RATELIMIT_IP` knob) | Development raises it to 120/hour — restart the backend after a settings change; or flush the dev cache |
| Second organisation without a UEN → 500 | `core.organisation.uen` is VARCHAR UNIQUE — two blank (`''`) UENs collide at the DB (multiple NULLs would not); the P10 serializer guard skips blanks, so the DB constraint itself fires | Known deferred debt (needs the null-vs-blank schema decision); give the org a UEN for now |
| GST computed at the wrong rate | Document date outside the code's effective window | Pass `document_date` inside the row's window (P2 contract) |
| `psql ... liblzf.so.1: cannot open shared object file` | Redis extraction missing liblzf | `apt-get download liblzf1` + extract (§5) |

## 15. Pushing changes to this repository

GitHub Actions CI (`.github/workflows/ci.yml`) runs the backend suite
against a schema-initialized PostgreSQL 16 service container and the
frontend typecheck/test/build — the DB password is generated per run
(no credential is committed; `config/settings/testing.py` reads `DB_*`
from the environment) plus the always-green no-backend e2e subset
(P18/CFG-L1 — the webServer self-boots the frontend; chromium only).
Still run the local §7/§11 gates and the LIVE e2e suite (`npm run
test:e2e:full`) before pushing: CI cannot run the backend-gated 29
specs (they mutate shared backend state). Commit to `main` (no feature branches), then
push with the SSH wrapper so the deploy key never touches the tree:

```bash
# key -> a 0600 file OUTSIDE the repo (e.g. /tmp/deploy.key)
python3 docs/ssh_git_wrapper_v3.py --key-file /tmp/deploy.key \
  --remote git@github.com:nordeim/ledgersg.git
```

**The `--remote` override is mandatory** (the wrapper's default remote
points at a different repo). The wrapper verifies the remote ref equals
local HEAD after the push and shreds its temp key copy; shred your key file
afterwards. Full instructions:
`docs/how-to-git-push-using-ssh-wrapper_SKILL.md` (for sandboxes without
an OpenSSH binary it also documents the paramiko `ssh` shim to put on
PATH). `.gitignore` rejects `.env`, `.env.local`, `*.key`.
