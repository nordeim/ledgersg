# LedgerSG — Remediation Plan (P1 Sprint: Green Suite & Contract Truth)

**Date:** 2026-11-21 (session 3)
**Base commit:** `342d16fb` (main)
**Source:** this session's audit (below) + deferred-debt register of `docs/REMEDIATION_PLAN_2026-11-21.md` §4
**Execution mode:** Mode B/D — TDD (RED → GREEN → REFACTOR), surgical fixes
**Plan validated against:** live codebase + PostgreSQL 17 (rootless, schema v1.0.2 loaded) + Redis 8, baseline reproduced at **26 failed / 465 passed / 5 skipped** (matches the documented post-P0 baseline exactly); invariants 12 passed; security 32 passed / 3 skipped; frontend 321/321.

---

## 0. Audit Summary (what this plan is built on)

Every finding below was independently reproduced against source in this environment.
Severity taxonomy: Critical / High / Medium / Low / Info. Counts: **0 Critical, 5 High, 3 Medium, 3 Low, 1 Info.**

### Findings register

| ID | Severity | Location | Finding | Evidence |
|---|---|---|---|---|
| A-1 | High | `tests/test_api_endpoints.py:88-92` | `test_organisation` fixture creates `UserOrganisation` WITHOUT `accepted_at`; `TenantContextMiddleware._verify_org_membership` requires `accepted_at__isnull=False` → 403 on every org-scoped request. This single fixture bug accounts for 25 of the 26 documented failures | Reproduced: patched fixture with `accepted_at=timezone.now()` → 22 more tests pass instantly |
| A-2 | High | `apps/invoicing/views.py:412,419,425` | `DocumentSummaryView` references phantom `InvoiceDocument.DOCUMENT_TYPE_CHOICES` (real name: `DOCUMENT_TYPES`) → AttributeError → 500 on `GET /{org}/documents/summary/`; also filters outstanding/overdue with invalid enum literal `PAID_PARTIAL` (correct: `PARTIALLY_PAID`) → silently matches nothing, understates outstanding | Reproduced post-fix experiment: `AttributeError: type object 'InvoiceDocument' has no attribute 'DOCUMENT_TYPE_CHOICES'` |
| A-3 | High | `apps/coa/services.py:463-481` | `AccountService.get_trial_balance()` LEFT JOINs the non-existent `coa.account_balance` view → ProgrammingError → 500 on `GET /{org}/accounts/trial-balance/`. (Same defect class as the `get_account_balance` fix from the P0 sprint — the trial-balance sibling was missed) | Reproduced: `relation "coa.account_balance" does not exist` |
| A-4 | Medium | `apps/invoicing/views.py:605-616` | `ValidStatusTransitionsView.get(self, request)` does not accept the `org_id` kwarg its org-scoped route passes → TypeError → 500 on `GET /{org}/documents/status-transitions/`. (Same class as the `EntryTypesView` fix, NEW-3, missed here) | Reproduced: `got an unexpected keyword argument 'org_id'` |
| A-5 | Medium | `tests/test_api_endpoints.py::test_create_organisation` | Test posts `gst_registered: true` WITHOUT `gst_reg_date`; `OrganisationSerializer` correctly rejects with 400. Test-payload bug | Reproduced: `ValidationError: GST registration date is required when GST is registered` |
| A-6 | High (packaging) | `apps/backend/pyproject.toml:36,22-59`; `config/settings/base.py:48-50` | `django_celery_beat` (line 36 commented out) and `django_ratelimit` are imported by `INSTALLED_APPS` but NOT declared in `pyproject.toml` → the documented install path (`pip install -e ".[dev]"`) yields an environment where `manage.py check` fails (`ModuleNotFoundError`). Root `requirements.txt` pins `django-celery-beat==2.8.1`, which forces a Django 5.x downgrade under Django 6.0.2; 2.9.0 supports Django 6 | Reproduced in fresh venv: two consecutive ModuleNotFoundError exits before manual installs |
| A-7 | Low (hygiene) | `.gitignore`; `apps/backend/.env`; `apps/web/.env.local` | `.gitignore` has no `.env*` rules; a real `.env` and `.env.local` are tracked in git. Current contents are dev placeholders only (no secrets leaked) but any future real value would be committed | `git ls-files` shows both tracked |
| A-8 | Low (docs) | `apps/web/.env.example` (missing); `apps/backend/.env.example` (incomplete) | README Quick Start says `cp .env.example .env.local` in `apps/web` — the file does not exist. Backend `.env.example` omits `RATELIMIT_ENABLE`, `DEBUG_TOOLBAR`, `CELERY_ALWAYS_EAGER` which settings read | Filesystem check |
| A-9 | Low (docs) | `apps/backend/database_schema.sql:6` | Header still says `Version: 1.0.1` while §15b/changelog (lines 3173, 3211, 3246) say v1.0.2 — the P0 plan's "header version → 1.0.2" item was only partially applied | grep evidence |
| A-10 | Info | root `requirements.txt` | Stale second dependency manifest (Django==6.0.3 vs pyproject 6.0.2; packages settings never import). pyproject is canonical; requirements.txt should be marked or aligned | grep evidence |

### Verified-good (no action needed)

- All P0 remediation fixes verified in source (C-01…C-04, H-01, H-05/06/07): wrap_response re-raise, RLS `SET LOCAL` inside request transaction, void reversal + `void_reason`, F5 on real tables with IRAS boxes.
- Test baseline reproduces exactly (26F/465P/5S); `pytest tests/invariants` 12 passed; `pytest tests/security` 32P/3S; frontend Vitest 321/321 (24 files).
- Editable install `pip install -e ".[dev]"` succeeds (NEW-1 holds).
- `audit_runner.py` standard-mode "criticals" are all test-fixture/docstring false positives (dummy passwords like `testpass123`, docstring example keys) — verified individually; no genuine hardcoded secrets.

### Skill guidance applied

Per `skills/skills-catalog.md`: `code-review-and-audit` (tiered pipeline; `audit_runner.py` standard mode + manual Phase-3 verification of every scanner finding), `code-quality-standards` (severity discipline), `diagnosing-bugs` (root-cause loop on the 26 failures — fixture experiment isolated the true cause), `writing-plans` + `planning-and-task-breakdown` (this document's bite-sized TDD tasks), `tdd`/`test-driven-development` (RED→GREEN per task), `verification-and-review-protocol` (evidence ledger in the report).

---

## 1. Execution Scope Decision

Goal: **a fully green backend suite (0 failed / 491 passed / 5 skipped), correct document-summary + trial-balance + status-transitions endpoints, and a reproducible documented install path.** Everything else from the P0 deferred register (H-02/03/04/08/10/11/13, M-02…M-16, L-*, I-*) remains deferred — re-registered in §4.

Guiding rule (Decision Priority Hierarchy): correctness & safety > security > reliability > maintainability. Every production-code fix ships with a regression test written first; fixture-only fixes have the failing tests as their RED evidence.

---

## 2. Task Breakdown (ordered, vertical slices)

### Task 1 (A-1, A-5): Fix the `test_api_endpoints.py` fixture architecture

**Problem.** 25 of 26 failures are one fixture bug (`accepted_at` never set on `UserOrganisation`); 1 is a test payload bug (`gst_registered` without `gst_reg_date`).

**Fix.**
1. `tests/test_api_endpoints.py` `test_organisation` fixture: add `accepted_at=timezone.now()` to the `UserOrganisation.objects.create(...)` call; import `from django.utils import timezone`.
2. `test_create_organisation`: add `"gst_reg_date": "2024-01-01"` to the POST payload (serialiser contract: required when `gst_registered`).

**TDD.** RED = the 26 baseline failures (already failing). GREEN = re-run `pytest tests/test_api_endpoints.py --reuse-db --no-migrations` → expect 4 remaining failures (A-2, A-3, A-4 — the real bugs this fixture debt was masking).

**Done when:** failure count drops 26 → 4, all remaining failures are the named production bugs.

**Files:** `tests/test_api_endpoints.py`. **Dependencies:** none.

---

### Task 2 (A-2): Fix `DocumentSummaryView` (phantom attr + invalid enum)

**Problem.** `apps/invoicing/views.py` `DocumentSummaryView.get()`:
- line 412: `InvoiceDocument.DOCUMENT_TYPE_CHOICES` → phantom attribute (real: `DOCUMENT_TYPES`);
- lines 419, 425: `status__in=["APPROVED", "PAID_PARTIAL"]` → `PAID_PARTIAL` is not a `doc_status` enum value (correct: `PARTIALLY_PAID`); outstanding and overdue totals are silently zero.

**Fix.**
1. Replace `DOCUMENT_TYPE_CHOICES` → `DOCUMENT_TYPES`.
2. Replace both `PAID_PARTIAL` literals with the enum-correct set. **Decision (validated against `dashboard_service._get_receivables_metrics`):** outstanding = every post-approval, not-fully-paid state → `["APPROVED", "SENT", "PARTIALLY_PAID", "OVERDUE"]`; overdue = same set plus `due_date < today`. This is a superset of both the original intent (APPROVED + partially-paid) and the dashboard's receivables set (SENT/PARTIALLY_PAID/OVERDUE), and contains no invalid enum literals.
3. Sweep `apps/invoicing/services/contact_service.py:239` — same invalid literal in `deactivate_contact` open-invoice guard (a contact with a `PARTIALLY_PAID` invoice could be deactivated today) → `PARTIALLY_PAID`.

**TDD.**
- RED: `tests/test_api_endpoints.py::TestInvoicingAPI::test_get_document_summary` (already failing with AttributeError once Task 1 lands).
- RED (new regression test for the enum fix): create one `PARTIALLY_PAID` + one `APPROVED` document via the service, call the summary endpoint, assert `total_outstanding == sum(approved + partially_paid totals)` and `overdue_count` respects `due_date < today`. Place in `tests/integration/test_document_summary.py` (new) so it survives independent of the endpoint-suite fixture pass.
- GREEN: implement; run both.

**Done when:** summary endpoint returns 200 with correct totals; `grep -rn "PAID_PARTIAL" apps/` returns nothing.

**Files:** `apps/invoicing/views.py`, `apps/invoicing/services/contact_service.py`, `tests/integration/test_document_summary.py` (new). **Dependencies:** Task 1 (to see the real failure).

---

### Task 3 (A-3): Fix CoA trial balance (phantom `coa.account_balance` view)

**Problem.** `AccountService.get_trial_balance()` (`apps/coa/services.py:452+`) LEFT JOINs `coa.account_balance`, which does not exist in the schema (only `coa.account`, `account_type`, `account_sub_type`). Every call raises ProgrammingError → 500.

**Fix.** Rewrite the query to aggregate from `journal.line` joined to `journal.entry` — mirroring the pattern the P0 sprint applied to `get_account_balance()` (`apps/coa/services.py:362` comment documents that fix). Validated against `information_schema`: `journal.line(account_id, debit, credit)`, `journal.entry(org_id, fiscal_year_id)`:

```sql
SELECT a.id, a.code, a.name, a.account_type::text,
       COALESCE(SUM(l.debit), 0)  AS total_debit,
       COALESCE(SUM(l.credit), 0) AS total_credit,
       COALESCE(SUM(l.debit) - SUM(l.credit), 0) AS balance
FROM coa.account a
LEFT JOIN journal.line l  ON l.account_id = a.id
LEFT JOIN journal.entry e ON e.id = l.entry_id AND e.org_id = a.org_id
WHERE a.org_id = %s AND a.is_active = true
GROUP BY a.id, a.code, a.name, a.account_type
ORDER BY a.code
```

Honour the optional `fiscal_year_id` filter (view passes it as a query param, already UUID-cast) with `AND e.fiscal_year_id = %s` appended to the WHERE clause when provided — `journal.entry.fiscal_year_id` exists (validated), no extra join needed.

**TDD.**
- RED: `tests/test_api_endpoints.py::TestChartOfAccountsAPI::test_get_trial_balance` (failing with `relation "coa.account_balance" does not exist`).
- RED (new deeper regression): extend `tests/invariants/test_journal_balance_queries.py` with a direct `AccountService.get_trial_balance()` assertion — post a balanced two-line entry, assert per-account debit/credit and that debits == credits across the report. Keeps the invariant even if the endpoint test is refactored later.
- GREEN: implement; run both.

**Done when:** trial balance endpoint 200s; direct service call returns correct sums; invariant suite green.

**Files:** `apps/coa/services.py`, `tests/invariants/test_journal_balance_queries.py`. **Dependencies:** Task 1.

---

### Task 4 (A-4): Fix `ValidStatusTransitionsView` signature

**Problem.** Org-scoped route `documents/status-transitions/` passes `org_id` kwarg; the view signature `get(self, request)` raises TypeError.

**Fix.** `def get(self, request, org_id: str) -> Response:` (mirrors `EntryTypesView` fix from NEW-3).

**TDD.** RED: `test_get_status_transitions` (failing with TypeError). GREEN: signature change; run test.

**Done when:** endpoint returns the `STATUS_TRANSITIONS` map with 200.

**Files:** `apps/invoicing/views.py`. **Dependencies:** Task 1.

---

### Task 5 (A-6): Make the documented install path complete

**Problem.** Fresh `pip install -e ".[dev]"` + `manage.py check` fails: `django_celery_beat` and `django_ratelimit` are imported by settings but undeclared.

**Fix.** In `apps/backend/pyproject.toml` dependencies:
- uncomment/replace the beat pin with `"django-celery-beat==2.9.0",` (2.9.0 supports Django 6; 2.8.1 pins Django<6 and downgrades the venv);
- add `"django-ratelimit>=4.1,<5",`.

**TDD / verification.**
- RED (environment-level, already reproduced this session): fresh venv → `manage.py check` exits non-zero with ModuleNotFoundError.
- GREEN: rebuild a clean venv from the updated pyproject (`python -m venv /tmp/verify_venv && pip install -e ".[dev]"`), run `DJANGO_SETTINGS_MODULE=config.settings.testing python manage.py check` → 0 errors (1 known W001).
- Cross-check installed Django version is 6.0.2 (not downgraded).

**Done when:** the documented install path produces a check-clean environment without manual pip installs.

**Files:** `apps/backend/pyproject.toml`. **Dependencies:** none (parallel-safe).

---

### Task 6 (A-7, A-8): `.env.example` files + git hygiene

**Problem.** README references `apps/web/.env.example` which doesn't exist; backend `.env.example` misses three variables the code reads; `.env` / `.env.local` are tracked with no `.gitignore` protection.

**Fix.**
1. Create `apps/web/.env.example` matching what the frontend actually reads (`next.config.ts`, `src/lib/api-client.ts`, providers): `NEXT_PUBLIC_API_URL`, `NEXT_OUTPUT_MODE`, `NEXT_PUBLIC_TOKEN_REFRESH_INTERVAL`, feature flags (`NEXT_PUBLIC_ENABLE_PEPPOL/GST_F5/BCRS`), external service URLs, devtools flags, log level — values mirroring the committed dev `.env.local`.
2. Extend `apps/backend/.env.example` with `RATELIMIT_ENABLE=true`, `DEBUG_TOOLBAR=true`, `CELERY_ALWAYS_EAGER=true` (+ comment that testing.py forces RATELIMIT_ENABLE=false).
3. `.gitignore`: add `.env`, `.env.local`, `.env.*.local` rules; `git rm --cached apps/backend/.env apps/web/.env.local` so the tracked copies stop being updated (the `.env.example` files become the canonical dev templates; local copies remain on disk for the dev server).

**Verification.** `git status` shows the two env files staged as deleted-from-index only; a fresh `cp apps/backend/.env.example apps/backend/.env` + `cp apps/web/.env.example apps/web/.env.local` leaves `git status` clean (ignored).

**Files:** `apps/web/.env.example` (new), `apps/backend/.env.example`, `.gitignore`, git index. **Dependencies:** none.

---

### Task 7 (A-9): Schema header version alignment

**Fix.** `apps/backend/database_schema.sql` line 6: `Version: 1.0.1` → `Version: 1.0.2` (matches §15b and the changelog). No DDL change — header comment only, both databases already carry the v1.0.2 objects.

**Files:** `apps/backend/database_schema.sql`. **Dependencies:** none.

---

### Task 8: Full verification gate + documentation alignment

**Gate (all must pass):**
```bash
pytest --reuse-db --no-migrations -q          # 0 failed, 491 passed, 5 skipped
pytest tests/invariants -q                    # 13 passed (new TB assertions)
pytest tests/security -q                      # 32 passed, 3 skipped
DJANGO_SETTINGS_MODULE=config.settings.testing python manage.py check
ruff check <files touched>                    # clean
cd ../web && npm test                         # 321 passed
```

**Docs to update (claims to match code, nothing more):**
1. `README.md` — expected backend output → `491 passed, 0 failed, 5 skipped`; note the fixture pass; quick-start env steps now reference the real `.env.example` files.
2. `CLAUDE.md` — status row: backend tests `491 passing (suite fully green)`; add A-2/A-3/A-4 to the milestone table.
3. `AGENTS.md` — append the session-3 lessons (fixture `accepted_at` contract; enum vocabulary sweep; phantom-view sweep; packaging completeness).
4. `Project_Architecture_Document.md` — no structural change; leave as is (middleware/box tables already correct).
5. `docs/REMEDIATION_2026-11-21_P1_REPORT.md` (new) — verification ledger for this sprint.
6. `ledgersg_SKILL.md` — refresh via `skills/distill-codebase-skill` + `skills/to-distill-project-into-skill` (project_state, new debugging rows, updated test counts).

---

### Task 9: Screenshots, worklog, session log, commit & push

1. Start backend (`runserver`, development settings, dev DB) + frontend (`npm run dev`); capture screenshots of the running remediated app into `docs/screenshots/` (login page, dashboard, at least one data page) — via Playwright/agent-browser headless capture.
2. Update `worklog.md` (repo root) with this session's record.
3. Update `docs/session_3.md`-style session log (following `session_1.md`/`session_2.md` convention — this session's log).
4. Conventional commits on `main` (see §5), push via `docs/ssh_git_wrapper_v3.py` per `docs/how-to-git-push-using-ssh-wrapper_SKILL.md`.

---

## 3. Verification Gate (definition of done for the sprint)

All commands run with `DB_NAME=test_ledgersg_dev DB_USER=ledgersg DB_PASSWORD=ledgersg_secret_to_change DB_HOST=127.0.0.1 DB_PORT=5432`, Redis on :6379:

| # | Check | Expected |
|---|---|---|
| 1 | `pytest --reuse-db --no-migrations -q` | **0 failed, 491 passed, 5 skipped** |
| 2 | `pytest tests/invariants -q` | 13 passed |
| 3 | `pytest tests/security -q` | 32 passed, 3 skipped |
| 4 | `manage.py check` (testing settings) | 0 errors, 1 known W001 |
| 5 | Clean-venv install from updated pyproject + `manage.py check` | succeeds, Django stays 6.0.2 |
| 6 | `ruff check` on touched files | clean |
| 7 | `cd apps/web && npm test` | 321 passed |
| 8 | `grep -rn "PAID_PARTIAL" apps/` | empty |
| 9 | Screenshots exist in `docs/screenshots/` | non-empty images |
| 10 | `.env.example` copy test | fresh copies are git-ignored |

Claims labelled **Verified** (executed) / **Reasoned** / **Assumed** in the report.

---

## 4. Deferred Debt Register (explicit, not silent)

Carried forward unchanged from `docs/REMEDIATION_PLAN_2026-11-21.md` §4 unless touched here:

| Item | Status |
|---|---|
| H-02 base-currency reporting / retained earnings / BS assertion | Deferred (design work) |
| H-03 widen 80 `NUMERIC(10,4)` columns to `NUMERIC(19,4)` | Deferred (schema-wide versioned patch) |
| H-04 GST rate history resolution by document date | Deferred (line-snapshot semantics) |
| H-08 wire `send-invoicenow` to real `TransmissionService` | Deferred (adapter contract) |
| H-09 (rest) Reg-11 tax-invoice labelling | Deferred |
| H-10 Schematron fail-closed validation | Deferred |
| H-11 fiscal close controls | Deferred |
| H-13 reproducible container build | Deferred |
| M-02…M-16, L-01…L-10, I-01…I-08 | Deferred per audit roadmap |
| GST payment tracking (`pay_return`) | Intentionally raises until schema extension |
| Repo-wide ruff debt (1,311 findings, 963 auto-fixable — measured this session) | Pre-existing; touched files stay lint-clean |
| A-10 stale root `requirements.txt` | Deferred (pyproject is canonical; aligning/removing the second manifest is a coordination decision for the repo owner) |

---

## 5. Commit Plan (conventional commits, single branch `main`)

1. `fix(tests): set accepted_at on org fixture; complete create-org payload (A-1, A-5)`
2. `fix(invoicing): document summary — real type choices, PARTIALLY_PAID enum (A-2)`
3. `fix(coa): trial balance aggregates journal.line, not the phantom view (A-3)`
4. `fix(invoicing): accept org_id kwarg on status-transitions view (A-4)`
5. `build(pyproject): declare django-celery-beat 2.9.0 + django-ratelimit (A-6)`
6. `chore(env): add web .env.example, complete backend example, ignore .env files (A-7, A-8)`
7. `docs(schema): header version 1.0.2 (A-9)`
8. `docs: align docs with green suite; add P1 remediation report; refresh ledgersg_SKILL.md`
9. `docs(worklog): session 3 worklog + screenshots`
