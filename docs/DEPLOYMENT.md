# Deployment Guide — LedgerSG

LedgerSG ships as **two applications over one PostgreSQL database plus one
Redis**: a Django 6 REST API (`apps/backend`), a Next.js 16 web app
(`apps/web`), PostgreSQL 16+ with a hand-written SQL schema (the source of
truth — Django migrations are permanently disabled), and Redis (the Django
cache AND the Celery broker). This revision (2026-11-21, session 9) is
written from the operator's `docs/sample_DEPLOYMENT.md` layout with **every
claim re-verified against this codebase** — commands below were executed
end-to-end on a fresh environment during the P3 sprint (schema v1.1.0) and
re-spot-executed during the P4 sprint (cookie auth + reload persistence).

Verified truths this guide is built on: the schema file
`apps/backend/database_schema.sql` (v1.1.0) CREATEs ROLEs inside DO blocks
so the loader must connect as a SUPERUSER; the backend suite requires
`--reuse-db --no-migrations` against a pre-initialised `test_ledgersg_dev`;
Redis on `:6379` is a hard prerequisite even for dev (the tenant middleware
membership cache); the web app reads exactly `NEXT_PUBLIC_API_URL`,
`BACKEND_URL`, `NEXT_OUTPUT_MODE` (P2/B-4 audit); money is
`NUMERIC(19,4)` (v1.1.0 — §16 of the schema carries the in-place widening
migration for databases created on ≤ v1.0.2).

## 1. Supported shape

- **Backend**: Django 6.0.2 + DRF 3.16 + Celery 5.6, 88+ REST endpoints
  under `/api/v1/` (auth is `/api/v1/auth/*`; org-scoped APIs are
  `/api/v1/{org_id}/<module>/…`). JWT access tokens (15 min) live in the
  api-client's module memory; refresh tokens (7 days) are returned in the
  login response body (API clients) AND set as an **HttpOnly cookie**
  (`Path=/api/v1/auth/`, SameSite=Lax, Secure=!DEBUG) that the browser
  replays on `POST /api/v1/auth/refresh/` — cross-reload session
  persistence is the verified behavior (P4): login/register set the cookie,
  refresh rotates it (old value blacklisted), logout/change-password expire
  it (and blacklist). A non-secret, JS-readable `session_hint` marker cookie
  rides alongside so the web client only attempts refreshes when a session
  actually exists; anonymous 401s (bad credentials) propagate to the
  caller. API clients using the body flow are unaffected.
- **Frontend**: Next.js 16.1.6 App Router (12 pages), React 19, Tailwind 4,
  Shadcn/Radix. Build modes: `standalone` (server mode, backend
  integration) and `export` (static CDN bundle without API integration).
- **Database**: PostgreSQL 16+ (dev-verified on rootless 17). 7 domain
  schemas (`core`, `coa`, `gst`, `journal`, `invoicing`, `banking`,
  `audit`), 30 domain tables + 2 token-blacklist tables, RLS on every
  table via `app.current_org_id`.
- **Redis 6.4+**: Django cache (membership cache, rate limiting) and Celery
  broker/result backend. Required for the backend to serve org-scoped
  requests at all.
- Ports: 3000 (web), 8000 (API), 5432 (PostgreSQL), 6379 (Redis).

## 2. Prerequisites

- **Python 3.12+** with `venv`. The canonical manifest is
  `apps/backend/pyproject.toml` (`pip install -e ".[dev]"`). The root
  `requirements.txt` is a stale second manifest — do not use it.
- **Node.js 20+** with npm. `apps/web/package-lock.json` is the lockfile.
- **A reachable PostgreSQL 16+**. The **rootless install in §4 is the
  documented and verified method**. Any other PostgreSQL — system service,
  Docker, or a managed instance — works identically; the application only
  ever sees `DB_*` variables. One caveat: the schema file's DO blocks
  CREATE ROLEs, so the **loading role must be SUPERUSER** (the dev role
  `ledgersg` is created SUPERUSER for exactly this reason; the runtime
  application role is `ledgersg_app`, which §15 of the schema grants and
  RLS binds).
- **A reachable Redis 6.4+** on `:6379` (or set `REDIS_URL`). Rootless
  method in §5.
- `git`, `curl`, and on Debian/Ubuntu `apt-get` (for the rootless
  PostgreSQL/Redis package extraction).

## 3. Install and configure

```bash
git clone https://github.com/nordeim/ledgersg.git
cd ledgersg
```

Nothing is read from the repo root `.env` — each app has its own template,
and both were audited variable-by-variable against the code (P2/B-4,
P3/D-4):

```bash
cp apps/backend/.env.example apps/backend/.env   # 15 settings-read vars, all listed
cp apps/web/.env.example apps/web/.env.local     # NEXT_PUBLIC_API_URL, BACKEND_URL, NEXT_OUTPUT_MODE
```

Edit `apps/backend/.env`: set `SECRET_KEY` (the production settings refuse
to boot on the placeholder — H-06 gate), `ALLOWED_HOSTS`,
`CORS_ALLOWED_ORIGINS` (must include the web origin), and the `DB_*`
values matching §4. The web `.env.local` needs `NEXT_PUBLIC_API_URL`
pointing at the backend (browser-facing) and `BACKEND_URL` for
server-side rendering calls.

## 4. Database installation — rootless PostgreSQL (primary method)

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

Stop / status (logs under `/home/z/my-project/pg/log/`):

```bash
"$PGBIN/pg_ctl" -D /home/z/my-project/pg/data status
# stop: same command with "stop" (or "restart")
```

On another host, any PostgreSQL works — keep the `DB_*` values in
`apps/backend/.env` in lockstep. See `skills/rootless-postgresql/SKILL.md`
for the full runbook (the `skills/` folder is reference material, not part
of the build).

### 4b. Load the schema (SQL-First — never run migrations)

The schema is the source of truth; Django models are unmanaged mirrors
(`managed = False`, `MIGRATE = False`). Load it into **both** databases:

```bash
cd apps/backend
export PGPASSWORD=ledgersg_secret_to_change
psql -h 127.0.0.1 -U ledgersg -d ledgersg_dev     -f database_schema.sql
psql -h 127.0.0.1 -U ledgersg -d test_ledgersg_dev -f database_schema.sql
```

`test_ledgersg_dev` is what the pytest suite runs against
(`--reuse-db --no-migrations`) — without it every backend test fails with
`relation "core.app_user" does not exist`.

**Existing database on schema ≤ v1.0.2?** Do not re-load. Apply the §16
in-place widening block at the end of `database_schema.sql` (monetary
columns 10,4 → 19,4; idempotent — it skips when nothing remains):

```bash
psql -h 127.0.0.1 -U ledgersg -d ledgersg_dev -f - < <(sed -n '/^-- §16/,/^-- v1.1.0/p' database_schema.sql)
# verify: must return 0
psql -h 127.0.0.1 -U ledgersg -d ledgersg_dev -tAc \
  "SELECT count(*) FROM information_schema.columns WHERE table_schema IN ('core','coa','gst','journal','invoicing','banking','audit') AND data_type='numeric' AND numeric_precision=10 AND numeric_scale=4;"
```

**Never run `python manage.py makemigrations`** — schema changes are
hand-written DDL patches + version bump + model alignment, gated by
`tests/invariants/test_schema_conformance.py` (which also asserts numeric
precision since v1.1.0).

## 5. Redis installation (rootless)

The backend 500s every org-scoped request with `tenant_context_error`
without Redis (the membership cache). Rootless install on Debian/Ubuntu:

```bash
mkdir -p ~/redis/deb ~/redis/root && cd ~/redis/deb
apt-get download redis-server redis-tools
for f in *.deb; do dpkg-deb -x "$f" ~/redis/root/; done
export LD_LIBRARY_PATH=~/redis/root/usr/lib/x86_64-linux-gnu
~/redis/root/usr/bin/redis-server --daemonize yes --port 6379 \
  --dir ~/redis --save '' --appendonly no
~/redis/root/usr/bin/redis-cli -p 6379 ping   # PONG
```

(A system `redis-server` or a managed Redis is equally fine — point
`REDIS_URL` at it.)

## 6. Backend setup

```bash
cd apps/backend
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
python manage.py check     # 0 errors (1 known django_ratelimit W001)
```

Sanity: with PostgreSQL + Redis up and the schema loaded, the suite must
be green:

```bash
export DB_NAME=test_ledgersg_dev DB_USER=ledgersg DB_PASSWORD=ledgersg_secret_to_change \
       DB_HOST=127.0.0.1 DB_PORT=5432
pytest --reuse-db --no-migrations -q
# expected (post-2026-11-21 P4): 534 passed, 0 failed, 5 skipped
```

Run the API (development):

```bash
python manage.py runserver 127.0.0.1:8000
curl http://127.0.0.1:8000/api/v1/health/
# {"status": "healthy", "database": "connected", "version": "1.0.0"}
```

Production serves with Gunicorn (the `service` settings module):

```bash
DJANGO_SETTINGS_MODULE=config.settings.production \
gunicorn config.wsgi:application --bind 127.0.0.1:8000 --workers 3
```

Celery worker (async tasks — PDF generation, InvoiceNow transmission; set
`CELERY_ALWAYS_EAGER=true` in dev to run tasks inline instead):

```bash
celery -A config worker -l info
```

## 7. Frontend setup

```bash
cd apps/web
npm install
```

Development server (hot reload; expects the backend on :8000):

```bash
npm run dev          # http://localhost:3000
```

Production server build (standalone, with API integration):

```bash
npm run build:server         # NEXT_OUTPUT_MODE=standalone + static copy
npm run start                # node .next/standalone/server.js
```

Static CDN build (no API integration — pages that need the backend
degrade):

```bash
npm run build && npm run serve
```

## 8. Verification checklist

```bash
# Backend gates (from apps/backend with the venv active + DB_* exported)
pytest --reuse-db --no-migrations -q        # 534 passed, 0 failed, 5 skipped
pytest tests/invariants -q                  # 20 passed (incl. schema conformance + capacity)
pytest tests/security -q                    # 47 passed, 3 skipped (incl. refresh-cookie + hint contracts)
DJANGO_SETTINGS_MODULE=config.settings.testing python manage.py check

# Frontend gates (from apps/web)
npm run typecheck                           # 0 errors
npm test                                    # 354 vitest tests
npm run test:e2e                            # green without a backend (gated specs skip)
npx playwright install chromium             # once per environment
npm run test:e2e:full                       # 16/16 — needs backend :8000 + Redis;
                                            # the dev login budget is 60/min per IP

# Live smoke (both dev servers running)
curl http://127.0.0.1:8000/api/v1/health/   # {"status": "healthy", ...}
curl -s -o /dev/null -w "%{http_code}\n" http://localhost:3000/login   # 200

# Session-persistence smoke (P4) — login sets both cookies, refresh works
# via the cookie, and a browser reload stays authenticated:
curl -s -c /tmp/cj.txt -X POST http://127.0.0.1:8000/api/v1/auth/login/ \
  -H 'Content-Type: application/json' \
  -d '{"email":"demo@ledgersg.sg","password":"demo1234"}' -o /dev/null -w '%{http_code}\n'
# 200 — and /tmp/cj.txt contains refresh_token (HttpOnly path cookie) + session_hint
curl -s -b /tmp/cj.txt -X POST http://127.0.0.1:8000/api/v1/auth/refresh/ \
  -H 'Content-Type: application/json' -d '{}' -o /dev/null -w '%{http_code}\n'
# 200 — the cookie alone refreshes (rotation re-sets it)
# Browser check: log in at http://localhost:3000, press F5 — you must stay
# on /dashboard (the reload-persistence acceptance test, e2e/session.spec.ts)
```

The full e2e run performs ~11 logins per invocation. The dev settings budget
60/min per IP (`LOGIN_RATELIMIT_IP`, P4) — production keeps the documented
10/min-per-IP default (`config.settings.base`); if a dev run fails on login
429s, flush the rate window (`redis-cli -n 0 FLUSHDB` on the dev cache) or
wait a minute.

## 9. Production notes

- **SECRET_KEY**: `config.settings.production` refuses the placeholder
  value (H-06). Generate one: `python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"`.
- **CORS**: `CORS_ALLOWED_ORIGINS` must list the exact web origin(s)
  (scheme + host + port). The preflight path skips JWT (OPTIONS) via
  `CORSJWTAuthentication`.
- **RLS**: the runtime DB role is `ledgersg_app` (schema §15 grants; every
  table has `FORCE ROW LEVEL SECURITY` keyed on `app.current_org_id`).
  The dev role `ledgersg` is SUPERUSER only because the schema loader
  needs it — do not use it as the runtime role in production.
- **Rate limiting** is ON by default (`RATELIMIT_ENABLE=true`); login rates
  are settings knobs (`LOGIN_RATELIMIT_IP` / `LOGIN_RATELIMIT_USER` —
  production defaults 10/min per IP and 30/min per user; refresh 20/min).
- **Session cookies (P4)**: the refresh cookie is `SameSite=Lax`, which is
  correct when the web app and the API share a site (e.g. both behind one
  domain, or the localhost dev pair). For a **cross-site production
  topology** (web on `app.example.com`, API on `api.example.com` — different
  sites), cookies must be `SameSite=None; Secure` — a one-line change in
  `apps/backend/apps/core/views/_refresh_cookie.py` (both cookies) plus
  HTTPS on both origins. The body-based refresh flow keeps working for
  non-browser API clients either way.
- **Money precision** is `NUMERIC(19,4)` — all Python money math goes
  through `common.decimal_utils.money()` (rejects floats). Never widen or
  narrow precision without the schema conformance + capacity gates green.
- **Audit trail** (`audit.event_log`) is append-only with no UPDATE/DELETE
  grants to the application role (IRAS 5-year retention).
- **Backups**: standard `pg_dump` of the database is sufficient (schema +
  data + RLS policies all live in SQL). The §16 migration pattern shows
  how versioned in-place patches are shipped.

## 10. Common issues

| Symptom | Cause | Fix |
|---|---|---|
| `relation "core.app_user" does not exist` | Schema not loaded into the DB the app points at | §4b `psql -f database_schema.sql` into BOTH databases |
| 500 `tenant_context_error` on every org URL | Redis down (membership cache) | Start Redis on :6379 (§5); read the middleware log line |
| `numeric field overflow` on a ≥ S$1M amount | Database still on schema ≤ v1.0.2 (10,4 columns) | Apply the §16 widening block (§4b) |
| `ModuleNotFoundError: django_celery_beat` in a fresh venv | Installing from the root `requirements.txt` | Install from `pyproject.toml`: `pip install -e ".[dev]"` |
| 403 on EVERY org-scoped URL | `UserOrganisation.accepted_at` is NULL (pending invitation) | Accept the membership (or set `accepted_at`); the tenant middleware filters on it |
| Dashboard "Loading..." stuck in production build | Missing static files in standalone output | `npm run build:server` (auto-copies `.next/static`) |
| Login silently does nothing | Password shorter than 8 chars — native `minLength` blocks the submit | Use an 8+ character password |
| e2e `Executable doesn't exist` | Declared browsers not installed | `npx playwright install chromium` (default suite needs chromium only) |
| e2e full-run login 429s | Dev rate window already spent (the run issues ~11 logins) | Dev budget is 60/min IP (`LOGIN_RATELIMIT_IP`); flush the dev Redis cache (`redis-cli -n 0 FLUSHDB`) or wait out the window |
| GST computed at the wrong rate | Rate lookups are date-aware since P2 — the document date must fall inside the code's effective window | Pass `document_date`, or use the row in force on that date |

## 11. Updating an existing deployment

```bash
git pull
cd apps/backend && source .venv/bin/activate && pip install -e ".[dev]"
# schema changed? apply the versioned section from database_schema.sql (see §4b),
# to BOTH ledgersg_dev and test_ledgersg_dev — never re-load over live data
cd ../web && npm install
npm run build:server       # cold build for production
# restart gunicorn / node / celery
```

Then re-run the §8 checklist; the invariant gates
(`pytest tests/invariants -q`) are the fastest signal that schema, models
and code still agree.

## 12. Pushing changes to this repository

No hosted CI — the local gate (§8) is the only gate. Run it green, commit
to `main` (no feature branches), then push with the SSH wrapper so the
deploy key never touches the tree:

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
`PATH`). `.gitignore` rejects `.env`, `.env.local`, `*.key`.
