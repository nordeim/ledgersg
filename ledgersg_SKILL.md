---
name: ledgersg
description: "Engineering skill for the LedgerSG codebase — a SQL-First, double-entry accounting platform for Singapore SMBs (Django 6 + DRF + Next.js 16 + PostgreSQL 16 RLS). Captures the architecture, the hard lessons of the 2026-11-21 P0+P1+P2+P3+P4 remediations, testing prerequisites and gates, and the debugging guide a future agent needs before touching financial code."
version: 1.4.0
last_updated: 2026-11-21
project_state: "P4 remediated; all gates green — 534 backend tests (0 failed, 5 skipped), frontend 354 vitest + 16 e2e (9 default / 7 backend-gated), typecheck 0 errors; schema v1.1.0 with NUMERIC(19,4) money; cross-reload session persistence shipped (HttpOnly refresh cookie + session_hint evidence gate)"
---

# LedgerSG — Engineering Skill

> Distilled from the codebase, the 2026-11-21 audit + P0 remediation sprint
> (`LedgerSG_Code_Review_Audit_Report_2026-11-21.md`, `docs/REMEDIATION_2026-11-21_REPORT.md`),
> the session-3 P1 sprint (`docs/REMEDIATION_PLAN_2026-11-21_P1.md`,
> `docs/REMEDIATION_2026-11-21_P1_REPORT.md`), the session-5 P2 sprint
> (`docs/REMEDIATION_PLAN_2026-11-21_P2.md`, `docs/REMEDIATION_2026-11-21_P2_REPORT.md`),
> and the session-7 P3 sprint (`docs/REMEDIATION_PLAN_2026-11-21_P3.md`,
> `docs/REMEDIATION_2026-11-21_P3_REPORT.md`), and the session-9 P4 sprint
> (`docs/REMEDIATION_PLAN_2026-11-21_P4.md`,
> `docs/REMEDIATION_2026-11-21_P4_REPORT.md`).
> Every claim below is verifiable against a file path or a runnable command.

---

## 1. Project Identity & Philosophy

LedgerSG is a **double-entry accounting platform for Singapore SMBs** with IRAS GST
compliance (F5 returns, InvoiceNow/Peppol PINT-SG, BCRS). Three non-negotiables:

1. **SQL-First**: `apps/backend/database_schema.sql` is the source of truth. All models
   are `managed = False`. NEVER run `makemigrations`. Schema changes = hand-written DDL
   patch + version bump + model alignment + conformance gate green.
2. **Money is `NUMERIC(19,4)`** (schema v1.1.0) — no floats, ever. All Python money math goes through
   `common.decimal_utils.money()`.
3. **Corrections are reversals**: journal entries are immutable; a void is a reversing
   entry, never an update.

## 2. Tech Stack (locked versions)

| Layer | Tech | Version |
|---|---|---|
| Backend | Django / DRF / simplejwt | 6.0.2 / 3.16.1 / 5.5.1 (+ token_blacklist app, schema §15b) |
| DB | PostgreSQL (rootless dev via `docs/setup_pg_z.sh`) | 16+ (dev: 17) |
| Cache/queue | Redis + Celery | 6.4 / 5.6 |
| Frontend | Next.js App Router / React / Tailwind / Shadcn | 16.1.6 / 19.2 / 4.0 |
| Tests | pytest-django (`--reuse-db --no-migrations`) / Vitest + RTL | 9.x / 4.x |
| Lint | ruff (`target-version py312`, line-length 100) | 0.15.x |

## 3. Environment Bootstrap (exact, verified)

```bash
# 1. Rootless PostgreSQL on :5432 (superuser postgres/postgres)
bash docs/setup_pg_z.sh
PGBIN=/home/z/my-project/pg/root/usr/lib/postgresql/17/bin
"$PGBIN/psql" -h /home/z/my-project/pg/data -U postgres -d postgres -c \
  "CREATE ROLE ledgersg WITH LOGIN PASSWORD 'ledgersg_secret_to_change' SUPERUSER;"
# (SUPERUSER is required to load the schema: it CREATEs ROLEs in DO blocks.
#  The application role in production is ledgersg_app — see §6 RLS.)

# 2. Databases + schema (BOTH dev and test)
for db in ledgersg_dev test_ledgersg_dev; do
  "$PGBIN/psql" -h ... -U postgres -d postgres -c "CREATE DATABASE $db OWNER ledgersg;"
done
export PGPASSWORD=ledgersg_secret_to_change
psql -h 127.0.0.1 -U ledgersg -d ledgersg_dev     -f apps/backend/database_schema.sql
psql -h 127.0.0.1 -U ledgersg -d test_ledgersg_dev -f apps/backend/database_schema.sql

# 3. Redis on :6379 (REQUIRED — see Anti-Pattern #1)
# 4. Backend deps
cd apps/backend && python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
```

## 4. Test Workflow (the only correct invocation)

```bash
cd apps/backend
export DB_NAME=test_ledgersg_dev DB_USER=ledgersg DB_PASSWORD=ledgersg_secret_to_change \
       DB_HOST=127.0.0.1 DB_PORT=5432
pytest --reuse-db --no-migrations -q
# Current state (2026-11-21, post-P4): 0 failed, 534 passed, 5 skipped — SUITE GREEN
pytest tests/invariants -q   # 20 gates: atomic rollback, void net-zero, F5 tie-out,
                             # schema conformance (incl. numeric precision), journal
                             # balances, CoA trial balance, monetary capacity
pytest tests/security -q     # 47: RLS transaction isolation, token lifecycle, settings
                             # gates, refresh-cookie + session_hint contracts
```

Frontend gates (`apps/web`): `npm test` (354 vitest), `npm run typecheck` (tsc, 0
errors), `npm run test:e2e` (playwright; 9 tests green without a backend —
backend-gated specs skip with reasons), `npm run test:e2e:full` (all 16 — needs
the Django backend on :8000 + Redis; `npx playwright install chromium` first).
`PLAYWRIGHT_PROJECTS=all` opts into the 5-browser matrix.

Gates before any PR: `manage.py check` (0 errors), invariants green, security green,
full suite no worse than the documented baseline, `ruff check` clean on touched files.

## 5. Backend Architecture Map

```
Request → SecurityMiddleware → CORS → CSP → WhiteNoise → Session → Common → CSRF
        → AuthenticationMiddleware
        → TenantContextMiddleware   ← org extraction, membership check, RLS transaction
        → AuditContextMiddleware    ← app.client_ip/user_agent/request_path
        → view (thin, @wrap_response)
              → services/ (ALL business logic; transaction.atomic() here)
                    → unmanaged models → 7 PG schemas (RLS enforced)
```

**URL layout**: org-scoped APIs are `/api/v1/{org_id}/<module>/…`, mounted from
`config/urls.py` `org_scoped_urlpatterns`. Auth is `/api/v1/auth/*`. IMPORTANT: the ACTIVE
core URL config is the `apps/core/urls/` PACKAGE (`__init__.py` + `auth.py` + …), NOT the
shadowed `apps/core/urls.py` module — new routes go in the package files.

**Key files**: `common/views.py` (wrap_response), `common/middleware/tenant_context.py`
(RLS), `apps/journal/services/journal_service.py` (GL), `apps/gst/services/*` (F5),
`apps/invoicing/services/document_service.py` (lifecycle), `apps/core/services/auth_service.py` (JWT).

## 6. Database Invariants (enforced by CHECKs — never fight them)

| Constraint | Rule |
|---|---|
| `journal` balance trigger | Σ debits == Σ credits per entry (deferred to commit) |
| `chk_reversal_consistency` | `is_reversed` and `reversed_by_id` flip TOGETHER |
| `chk_void_reason` | `voided_at` set ⇒ `void_reason` non-empty |
| `chk_box4_total` | `box4 = box1+box2+box3` (unless DRAFT) |
| `chk_box8_net` | `box8 = box6_output_tax − box7_input_tax_claimable` |
| `return_status_check` | status ∈ {DRAFT, COMPUTED, REVIEWED, FILED, AMENDED} |
| doc_status enum | DRAFT, APPROVED, SENT, PARTIALLY_PAID, PAID, OVERDUE, VOID |
| RLS | `USING (org_id = core.current_org_id())`, FORCE; `ledgersg_app` is bound by it |
| token_blacklist §15b | outstandingtoken/blacklistedtoken (public schema, no RLS) |

## 7. GST F5 Box Convention (IRAS; drive from tax_code columns)

Box 1/2/3 supplies (net) ← `f5_supply_box`; Box 4 = 1+2+3; Box 5 taxable purchases ←
`f5_purchase_box`; Box 6 output tax ← `f5_tax_box=6`; Box 7 input tax ← `f5_tax_box=7`
AND `is_claimable`; Box 8 = 6−7; Box 13 revenue; Box 14 ← `is_reverse_charge`.
Sales vs purchase split on `document_type::text LIKE 'PURCHASE%'`. Statuses counted:
APPROVED, SENT, PARTIALLY_PAID, PAID, OVERDUE. Excluded: DRAFT, VOID, BCRS lines.

## 8. Anti-Patterns & Common Bugs (each one shipped a real defect)

1. **Redis-less test runs** → every org-scoped request 500s `tenant_context_error`
   (membership cache). Redis on :6379 is a hard prerequisite.
2. **`SET LOCAL` outside a transaction** → discarded before the view runs; RLS inert.
   Middleware must open `transaction.atomic()` and call `get_response()` inside it
   (`tests/security/test_rls_transaction_isolation.py` proves it under autocommit).
3. **Catching `Exception` in views/decorators** → returns a 500 Response inside
   ATOMIC_REQUESTS → Django COMMITS partial state. Re-raise instead.
4. **Phantom model attributes** — Python happily `obj.foo = x` on any attr; `save()`
   silently discards. Every field write must match a `db_column` (conformance gate).
5. **Wrong enum literals** (`PAID_PARTIAL`, `AMENDING`, `PAID`, `INVOICE`) →
   `invalid input value for enum` / CHECK violation at flush time.
6. **Posting journal entries outside the atomic block** → approved doc with no GL entry.
7. **`pytest.mark.django_db` masks RLS bugs** — the wrapping transaction makes bare
   `SET LOCAL` look fine. Use `TransactionTestCase` for transaction-scoping proofs.
8. **Second definition of a method silently wins** — duplicate `_reverse_journal_entry`
   made the live one a `pass` placeholder. Never define a method twice in a class.
9. **`hasattr` mass assignment** on request-supplied dicts — allow-list field names
   explicitly (F5 boxes: `OVERRIDABLE_BOX_FIELDS`).
10. **Assuming a DB view/table exists** (`coa.account_balance`) — verify against
    `information_schema`; the schema is the only truth.
11. **Missing `user_id` on journal creates** — `posted_by` is NOT NULL.
12. **`date.today()` in posting paths** — the fiscal period for today may be closed;
    fall back to the original entry's date.
13. **`UserOrganisation` without `accepted_at`** — the tenant middleware filters on
    `accepted_at__isnull=False`; a pending invitation 403s every org-scoped request.
    Every fixture that creates a membership must set it (the root `tests/conftest.py`
    does; a shadowed local fixture in `tests/test_api_endpoints.py` did not and cost
    25 red tests). Prefer consuming root conftest fixtures over redefining them.
14. **Red suites hide real bugs** — the 26 "known fixture debt" failures masked three
    production defects (document-summary phantom attrs + invalid enum, CoA trial
    balance on a phantom view, missing `org_id` kwarg). Never normalise a red suite.
15. **Invalid enum literals travel in groups** — `PAID_PARTIAL` (vs `PARTIALLY_PAID`)
    appeared in three places; `pte_ltd` (vs `PRIVATE_LIMITED`) in another. When you
    find one wrong literal, sweep the codebase for it and for its siblings.
16. **Unordered `.first()` over history rows** — `gst.tax_code` stores rate HISTORY
    (SR: 0.07/0.08/0.09 by `effective_from`); `.first()` returned the 2007 row today.
    Always resolve by effective date: `get_tax_code_by_code(org, code, as_of=…)`
    (org rows shadow system rows; latest `effective_from` wins; NULL `effective_to`
    = open-ended). `add_line` fails closed on codes not in force on the document's
    `issue_date`.
17. **Silent fallbacks on money paths** — the GST calculate endpoint used to answer
    9% when a code was unknown. On compliance calculations, 404 the unknown, never
    guess a plausible rate.
18. **Untested branches rot invisibly** — `POST /gst/tax-codes/` 500'd on EVERY call
    (phantom `box_mapping` kwarg → `TypeError`) while the suite was green, because
    only the `rate` branch of calculate and no create was tested. The same branch
    also hid `UUID(org_id)` re-wrap and `UnboundLocalError: Decimal` (function-local
    import in the sibling branch) crashes. Test both branches of every conditional
    API path.
19. **Runtime-green ≠ type-green** — vitest injects globals at runtime, so 321 passing
    tests coexisted with 25 `tsc` errors (jest-style `jest.Mock`, un-imported
    `beforeEach`, incomplete fixtures). `npm run typecheck` is a gate; when testing
    zod defaults use the `z.input` type, and build full payloads for mutations
    typed with `z.infer`.
20. **Playwright configs must match installed browsers** — declaring 5 projects when
    only chromium is installed makes `test:e2e` fail on 24/30 tests before any
    assertion. Chromium-only default + `PLAYWRIGHT_PROJECTS=all` opt-in; axe scans
    must await the auth-redirect chain (`toHaveURL(/login/)`) before `.analyze()`.
21. **Money width is a business-model contract** — `NUMERIC(10,4)` capped at
    S$999,999.9999, below the S$1M GST registration threshold (P3/C-1). All
    money is `NUMERIC(19,4)` since schema v1.1.0; the conformance gate asserts
    DecimalField precision against `information_schema` (it caught
    `JournalLine.exchange_rate` over-declaring 19,6 vs the real 12,6 on its
    first run — schema is truth; align the model DOWN).
22. **Generated columns block their inputs' ALTERs** — `amount_due` is
    `GENERATED ALWAYS AS (total_amount - amount_paid) STORED`; widening its
    inputs requires drop generated → alter → re-add with the identical
    expression (schema §16 ships this as an idempotent in-place migration —
    count-then-skip guard; never re-load the schema over live data).
23. **Dead hooks signal unfinished wiring** — `useCreateInvoice` existed with
    zero importers while the form's onSubmit was a `console.log` stub (P3/D-1).
    When adding a hook, grep for its intended caller; when a form needs an
    API, write a PURE payload adapter (`src/lib/invoice-submit.ts`) that maps
    form state to the backend contract and drops client-computed preview
    fields — the server recalculates authoritatively and owns numbering
    (`document_sequence`), so the local `invoice_number` is display-only.
24. **One auth path for every transport** — anything needing the token goes
    through the api-client (`fetchWithAuth` + `api.blob()`); a second reader
    (the old `localStorage.getItem("accessToken")` in `useInvoicePDF`)
    violated the zero-JWT-exposure mandate AND read a location that is never
    written (token lives in module memory) → `Bearer null` → 401 (P3/D-2).
25. **Sessions are memory-only; e2e must walk the real path** — the backend
    returns tokens in the login body and sets no cookie, so a `page.goto`
    after login drops the session. Authed specs: UI login → dashboard →
    sidebar `<Link>` → target, all client-side. Native validation is enforced
    in headless chromium (an 8-char `minLength` silently blocks short
    passwords — no event fires); the login rate limit (10/min per IP)
    accumulates across dev iterations (flush Redis when a full run fails only
    on login). Backend-dependent specs read `E2E_API_URL` and skip when unset
    — the default suite stays green on a fresh clone (P3/D-5).

## 9. Debugging Guide

| Symptom | Cause | Fix |
|---|---|---|
| 500 `tenant_context_error` on every org URL | Redis down or middleware exception | Start Redis :6379; read the middleware log line |
| `FieldError: Cannot resolve keyword 'journal_entry'` | Wrong FK name (it's `entry`) | `entry__org_id`, `entry__entry_date`; no `is_posted` |
| `relation "invoicing.invoice" does not exist` | Querying a table that isn't in the schema | Use `invoicing.document` / `document_line` |
| `numeric field overflow` | DB still on ≤ v1.0.2 (NUMERIC(10,4) money) | Apply schema §16 in-place widening (idempotent); both DBs — fixed everywhere as of v1.1.0 |
| `No open fiscal period found for date …` | Posting dated outside open periods | Date the document inside an open period (fixtures: Jan 2024) |
| `No document sequence configured for org … type X` | Org fixture lacks the sequence | conftest now seeds all types; extend if you add one |
| Test 404s on a route you "added" | Added to shadowed `apps/core/urls.py` | Add to the `apps/core/urls/` package module instead |
| 403 on EVERY org-scoped URL in a test | Fixture created `UserOrganisation` without `accepted_at` | Set `accepted_at=timezone.now()` in the fixture (root conftest already does) |
| 500 on `/{org}/documents/summary/` | Phantom attrs: `DOCUMENT_TYPE_CHOICES`, `total`; invalid `PAID_PARTIAL` literal | Use `DOCUMENT_TYPES`, `total_incl`, enum-correct outstanding set |
| 500 on `/{org}/accounts/trial-balance/` | `get_trial_balance` joined phantom `coa.account_balance` | Aggregates `journal.line` JOIN `journal.entry` (fixed; keep it that way) |
| 500 TypeError `unexpected keyword argument 'org_id'` | View signature missing the kwarg its org-scoped route passes | Add `org_id: str` to the view signature |
| `ModuleNotFoundError: django_celery_beat` / `django_ratelimit` after fresh install | Settings import apps not declared in `pyproject.toml` | Both declared since P1 (beat 2.9.0 — 2.8.1 pins Django<6); pyproject is canonical, NOT root `requirements.txt` |
| `UndefinedColumn "updated_at"` on ExchangeRate | BaseModel injects it; table lacks it | Don't inherit BaseModel for tables without timestamps |
| Void 500s on `chk_void_reason` | Reason not persisted | `void_document()` does now; keep it that way |
| GST computed at the WRONG rate (7% not 9%) | Unordered `.first()` over rate-history rows | `get_tax_code_by_code(org, code, as_of=document_date)`; `gst/calculate/` takes `tax_code` + `document_date` |
| 500 `TypeError … unexpected keyword arguments: 'box_mapping'` on POST /gst/tax-codes/ | View forwarded a field that exists on neither serializer nor model | Fixed in P2; when adding serializer fields, forward the REAL model fields (f5_*) |
| 404 `Tax code 'X' is not in force on the requested date` | Fail-closed resolution (P2 contract) | Pass `document_date` matching the row's effective window, or use an explicit `rate` |
| `UnboundLocalError: Decimal` in a view branch | `from decimal import Decimal` imported inside the SIBLING branch | Imports are module-level in `apps/gst/views.py`; never function-local-import into one branch of a conditional |
| Playwright `Executable doesn't exist` | Declared browser projects not installed | `npx playwright install chromium`, or stay on the chromium default; `PLAYWRIGHT_PROJECTS=all` needs the full install |
| e2e axe scan flaky on `/` | Scan raced the `/` → `/dashboard` → `/login` redirect chain | `await expect(page).toHaveURL(/\/login/)` before `.analyze()` (fixed in `e2e/navigation.spec.ts`) |
| `numeric field overflow … less than 10^6` | DB still on ≤ v1.0.2 (NUMERIC(10,4) money) | Apply schema §16 in-place widening (idempotent); both DBs |
| Login button does nothing (no error, no request) | Native `minLength={8}` on the password input blocks the submit in chromium | Use an 8+ char password |
| e2e authed test lands back on /login | Pre-P4: memory-only session (no refresh cookie, `&& accessToken` gate) | Fixed in P4 — reload/goto now survives via the HttpOnly refresh cookie; if it recurs, check `session_hint` evidence and the backend cookie path |
| e2e full run fails only on login (429) | ~11 logins/run vs the login rate limit | Dev settings now budget 60/min IP (`LOGIN_RATELIMIT_IP`); production keeps 10/min — flush Redis (`redis-cli -n 0 FLUSHDB`) on dev if a window is already spent |
| jsdom: `target.hasPointerCapture is not a function` | Radix Select needs pointer-capture APIs jsdom lacks | Setup polyfills in `src/__tests__/setup.ts`; drive selection via `{ArrowDown}{Enter}` |
| `cannot alter type of a column used by a generated column` | `amount_due` is GENERATED off total_amount/amount_paid | Drop generated → alter inputs → re-add identical expression (schema §16) |
| Session lost on every page reload (pre-P4) | Three-link chain: no cookie backend, discarded refresh token, `&& accessToken` refresh gate | P4 cookie flow: login sets HttpOnly refresh cookie + `session_hint`; cold-401 refresh retries (`apps/core/views/_refresh_cookie.py`) |
| Login form shows "Session expired" instead of the credential error | api-client refreshed on an anonymous 401 and hard-redirected | Evidence gate: refresh only with an in-memory token OR the `session_hint` cookie; anonymous 401s propagate to the caller |
| Refresh endpoint 429s during a UI test run | Pointless refreshes on anonymous 401s (pre-refinement) | Same evidence gate; the backend also expires both cookies on a failed cookie-refresh so dead evidence can't linger |

## 10. Pre-Ship Checklist

```bash
pytest tests/invariants -q && pytest tests/security -q      # must be green
pytest --reuse-db --no-migrations -q | tail -1               # ≥ documented baseline
DJANGO_SETTINGS_MODULE=config.settings.testing python manage.py check
ruff check <files you touched>
# schema touched? → bump database_schema.sql version, update BOTH DBs, keep the
# conformance gate green, align models, document in the changelog section
```

Plus: no floats for money; enums from the vocabulary (never literals); every service
write inside `transaction.atomic()`; new tests RED before the fix.

## 11. Lessons Learnt (2026-11-21 sprints)

1. A green test suite can mask RLS failure when the test harness itself provides the
   transaction production lacks — test the *mechanism* under production semantics.
2. Hand-maintained model mirrors drift silently; an introspection gate turns drift into
   a test failure (it caught ExchangeRate and OrganisationSetting immediately).
3. "Documented as complete" ≠ complete — the void-reversal, RLS, F5 and InvoiceNow
   claims all diverged from code. Validate claims against executable evidence.
4. TDD on fixes is cheap: each Critical fix here is one fixture + assertions that
   failed pre-fix and pass post-fix.
5. Schema CHECK constraints are a gift: encode the box identities and reversal rules
   in DDL, then the application cannot silently violate them.
6. Fixture debt is not neutral: 25 of 26 "known" failures were one missing
   `accepted_at`, and the red noise hid three live endpoint bugs. Fix red suites
   before adding features on top of them.
7. A clean-venv install is a packaging test: settings-imported packages MUST be
   declared in the canonical manifest, and version pins must respect the framework
   major (beat 2.8.1 vs Django 6).
8. Rate data is temporal: "the SR rate" does not exist — only "the SR rate in
   force on date X". Every rate lookup needs a date, and every rate snapshot
   (document line) must validate its row against the document's own date (P2/H-04).
9. Endpoints rot in their untested branches: a green suite with zero coverage on
   the `tax_code` branch of calculate and on create-tax-code hid three distinct
   crashes in one view file (P2/B-7).
10. Test toolchains drift: vitest runs Jest-typed test files fine at runtime while
    `tsc` is red — keep a typecheck gate or the drift compounds (P2/B-5: 25 errors
    accumulated silently).
11. Capacity is a contract: a monetary column that cannot hold the business
    model's real numbers (S$1M GST threshold) is a Critical defect even when
    every current row fits. Encode the ceiling in a gate
    (`test_numeric_capacity.py`), not in tribal knowledge (P3/C-1).
12. Fully-implemented dead code (useCreateInvoice with zero importers) is the
    signature of an unfinished wiring step — grep for callers before writing
    a parallel implementation (P3/D-1).
13. A comment describing nonexistent behavior ("refresh token: HttpOnly cookie"
    with no cookie code behind it) is a defect detector — and a cross-layer
    symptom can be a three-link chain where fixing any single link changes
    nothing (P4/E-1). Write the reload-e2e acceptance test, not just unit
    tests, for session behavior.
14. "Obvious" auth fixes need an anonymous-state regression test: refreshing
    on every 401 flooded the refresh rate limit and swallowed the login form's
    own error — the e2e run caught what unit tests blessed (P4/E-1
    refinement). The 401 handler is a state machine: evidence (in-memory token
    or `session_hint` cookie) gates the refresh; dead evidence must be expired
    server-side.

## 12. Quick Reference Card

| Thing | Where |
|---|---|
| Schema (truth) | `apps/backend/database_schema.sql` (v1.1.0) |
| RLS middleware | `common/middleware/tenant_context.py` |
| wrap_response | `common/views.py` |
| money() | `common/decimal_utils.py` |
| GL service | `apps/journal/services/journal_service.py` |
| F5 pipeline | `apps/gst/services/{calculation_service,return_service}.py` |
| Document lifecycle | `apps/invoicing/services/document_service.py` |
| Auth/JWT | `apps/core/services/auth_service.py`, `apps/core/urls/auth.py` |
| Invariant gates | `tests/invariants/` |
| Security gates | `tests/security/` |
| Fixtures | `tests/conftest.py` (org seeds ALL document sequences; memberships carry `accepted_at`) |
| PG setup | `docs/setup_pg_z.sh` + `skills/rootless-postgresql/SKILL.md` |
| Deferred debt | `docs/REMEDIATION_PLAN_2026-11-21.md` §4 + `_P1.md` §4 + `_P2.md` §4 + `_P3.md` §4 |
| P0 remediation report | `docs/REMEDIATION_2026-11-21_REPORT.md` |
| P1 remediation report | `docs/REMEDIATION_2026-11-21_P1_REPORT.md` |
| P2 remediation report | `docs/REMEDIATION_2026-11-21_P2_REPORT.md` |
| P3 remediation report | `docs/REMEDIATION_2026-11-21_P3_REPORT.md` |
| Audit report | `LedgerSG_Code_Review_Audit_Report_2026-11-21.md` |
| Env templates | root `.env.example` (combined index) → `apps/backend/.env.example` + `apps/web/.env.example`; `.gitignore` lists `.env*`, but the two local dev `.env`s are already tracked by earlier repo history (`git ls-files | rg '\.env'`) |
| Session cookies | login/register/refresh set + rotate; logout/change-password/failed-cookie-refresh expire — `apps/backend/apps/core/views/_refresh_cookie.py`; gate = `tests/security/test_refresh_cookie.py` |
| Rate resolution | `TaxCodeService.get_tax_code_by_code(org, code, as_of)` / `is_effective(tc, date)` — `apps/gst/services/tax_code_service.py` |
| Money capacity | All money `NUMERIC(19,4)` since schema v1.1.0; §16 = in-place widening migration; gate = `tests/invariants/test_numeric_capacity.py` |
| Invoice form adapter | `src/lib/invoice-submit.ts` (form state → contact+document payloads) — `src/hooks/use-tax-codes.ts`, `src/hooks/use-accounts.ts` |
| Authed e2e pattern | UI login → sidebar Links (client-side only); `E2E_API_URL` gating — `apps/web/e2e/invoices.spec.ts`; session persistence (reload survival) — `apps/web/e2e/session.spec.ts` |
| Deployment guide | `docs/DEPLOYMENT.md` (fresh-host, rootless PG + §16 migration + Redis + gates) |
| P4 plan/report | `docs/REMEDIATION_PLAN_2026-11-21_P4.md` / `docs/REMEDIATION_2026-11-21_P4_REPORT.md` |
