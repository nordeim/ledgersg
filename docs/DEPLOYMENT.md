# Deployment Guide — LedgerSG

**Deploy the entire application (backend + frontend) on a freshly installed
host, starting from `git clone`.** LedgerSG ships as two applications over
one PostgreSQL database plus one Redis: a Django 6 REST API (`apps/backend`),
a Next.js 16 web app (`apps/web`), PostgreSQL 16+ with a hand-written SQL
schema (the source of truth — Django migrations are permanently disabled),
and Redis (the Django cache AND the Celery broker). This revision
(2026-11-22, session 14 / P7) re-verified every command against the current
codebase (backend 624P/0F/5S, vitest 398/398, e2e 21/21 full).

Verified truths this guide is built on: the schema file
`apps/backend/database_schema.sql` (v1.1.0) CREATEs ROLEs inside DO blocks
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

- **Python 3.12+** with `venv`. The canonical manifest is
  `apps/backend/pyproject.toml` (`pip install -e ".[dev]"`). The root
  `requirements.txt` is a stale second manifest — do not use it.
- **Node.js 20+** with npm. `apps/web/package-lock.json` is the lockfile.
- **A reachable PostgreSQL 16+**. The **rootless install in §3 is the
  documented and verified method** and needs no root. Any other PostgreSQL —
  system service, Docker, or a managed instance — works identically; the
  application only ever sees `DB_*` variables. One caveat: the schema file's
  DO blocks CREATE ROLEs, so the **loading role must be SUPERUSER** (the dev
  role `ledgersg` is created SUPERUSER for exactly this reason; the runtime
  application role is `ledgersg_app`, which the schema grants and RLS binds).
- **A reachable Redis 6.4+** on `:6379` (or set `REDIS_URL`). Rootless
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
template (backend: 15 settings-read vars, all listed; web: live vars +
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

Verify (30 domain tables + 2 token-blacklist tables, money at 19,4):

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
psql -h 127.0.0.1 -U ledgersg -d ledgersg_dev -f - < <(sed -n '/^-- §16/,/^-- v1.1.0/p' database_schema.sql)
```

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
python3 -m venv venv && source venv/bin/activate
pip install -e ".[dev]"
python manage.py check     # 0 errors (1 known django_ratelimit W001)
```

## 7. Backend verification (the suite must be green)

```bash
export DB_NAME=test_ledgersg_dev DB_USER=ledgersg DB_PASSWORD=ledgersg_secret_to_change \
       DB_HOST=127.0.0.1 DB_PORT=5432
pytest --reuse-db --no-migrations -q
# expected (post-2026-11-22 P7): 624 passed, 0 failed, 5 skipped
pytest tests/invariants -q    # 27 passed (schema conformance + capacity + balance)
pytest tests/security -q      # 53 passed, 3 skipped (RLS, tokens, cookies, posture gates)
```

## 8. Run the backend

Development:

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

## 9. Frontend install and run

```bash
cd apps/web
npm install
npx playwright install chromium   # once per environment (e2e suites)
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

Static CDN build (no API integration — pages that need the backend degrade):

```bash
npm run build && npm run serve
```

Frontend gates (run before every push):

```bash
npm run typecheck           # 0 errors
npm test                    # 398 vitest tests
npm run test:e2e            # green without a backend (gated specs skip)
E2E_API_URL=http://127.0.0.1:8000 npm run test:e2e:full   # 21/21 (live stack)
```

## 10. (Optional) Celery worker — async tasks

PDF generation, invoice email delivery and InvoiceNow transmission run as
Celery tasks. Development can run them inline (`CELERY_ALWAYS_EAGER=true`
is the dev default); otherwise start a worker:

```bash
cd apps/backend && source venv/bin/activate
celery -A config worker -l info
```

## 11. End-to-end verification checklist

```bash
# 1. Backend health
curl http://127.0.0.1:8000/api/v1/health/
# {"status": "healthy", "database": "connected", ...}

# 2. Frontend up
curl -s -o /dev/null -w "%{http_code}\n" http://localhost:3000/login   # 200

# 3. Login sets BOTH cookies (P4 flow) — refresh works via the cookie alone
curl -s -c /tmp/cj.txt -X POST http://127.0.0.1:8000/api/v1/auth/login/ \
  -H 'Content-Type: application/json' \
  -d '{"email":"demo@ledgersg.sg","password":"demo1234pass"}' -o /dev/null -w '%{http_code}\n'
# 200 — /tmp/cj.txt contains refresh_token (HttpOnly) + session_hint
curl -s -b /tmp/cj.txt -X POST http://127.0.0.1:8000/api/v1/auth/refresh/ \
  -H 'Content-Type: application/json' -d '{}' -o /dev/null -w '%{http_code}\n'
# 200 — the cookie alone refreshes (rotation re-sets it)

# 4. Browser: log in at http://localhost:3000, press F5 — you must stay on
#    /dashboard (the reload-persistence acceptance test, e2e/session.spec.ts)

# 5. P7 API-truth spot checks
#    - fiscal periods route (was 404 pre-P7):
curl -s -o /dev/null -w '%{http_code}\n' -b /tmp/cj2.txt \
  "http://127.0.0.1:8000/api/v1/$ORG_ID/fiscal-periods/"   # 200 (with auth)
#    - malformed query params are 400s, not 500s:
curl -s -o /dev/null -w '%{http_code}\n' -b /tmp/cj2.txt \
  "http://127.0.0.1:8000/api/v1/$ORG_ID/journal-entries/entries/?date_from=garbage"  # 400
```

The full e2e run performs ~25 logins/refreshes. The dev settings budget
(60/min IP logins, 240/min refresh — `LOGIN_RATELIMIT_IP`,
`REFRESH_RATELIMIT_IP`) covers it; production keeps 10/min + 20/min. If a
dev run fails only on login/refresh 429s, flush the dev cache
(`redis-cli -n 0 FLUSHDB`) or wait out the window.

## 12. Production notes

- **SECRET_KEY**: `config.settings.production` refuses the placeholder
  (H-06). Generate one:
  `python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"`.
- **CORS**: `CORS_ALLOWED_ORIGINS` must list the exact web origin(s)
  (scheme + host + port). The preflight path skips JWT (OPTIONS) via
  `CORSJWTAuthentication`.
- **RLS**: the runtime DB role is `ledgersg_app` (schema §15 grants; every
  table has `FORCE ROW LEVEL SECURITY` keyed on `app.current_org_id`).
  The dev role `ledgersg` is SUPERUSER only because the schema loader
  needs it — do not use it as the runtime role in production.
- **Rate limiting** is ON by default (`RATELIMIT_ENABLE=true`); login and
  refresh rates are settings knobs — production defaults 10/min per IP
  (login), 30/min per user, 20/min (refresh).
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

## 13. Updating an existing deployment

```bash
git pull
cd apps/backend && source venv/bin/activate && pip install -e ".[dev]"
# schema changed? apply the versioned section from database_schema.sql (§4),
# to BOTH ledgersg_dev and test_ledgersg_dev — never re-load over live data
cd ../web && npm install
npm run build:server       # cold build for production
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
| Login silently does nothing | Password shorter than 8 chars — native `minLength` blocks the submit | Use an 8+ character password |
| e2e `Executable doesn't exist` | Declared browsers not installed | `npx playwright install chromium` |
| e2e full-run login/refresh 429s | Dev rate window spent | Dev budgets 60/240 per min; flush the dev Redis cache or wait |
| GST computed at the wrong rate | Document date outside the code's effective window | Pass `document_date` inside the row's window (P2 contract) |
| `psql ... liblzf.so.1: cannot open shared object file` | Redis extraction missing liblzf | `apt-get download liblzf1` + extract (§5) |

## 15. Pushing changes to this repository

GitHub Actions CI (`.github/workflows/ci.yml`) runs the backend suite
against a schema-initialized PostgreSQL 16 service container and the
frontend typecheck/test/build — the DB password is generated per run
(no credential is committed; `config/settings/testing.py` reads `DB_*`
from the environment). Still run the local §7/§11 gate before pushing: CI
does not run the e2e suite. Commit to `main` (no feature branches), then
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
