# LedgerSG — Remediation Report (P1 Sprint: Green Suite & Contract Truth)

**Date:** 2026-11-21 (session 3)
**Base commit:** `342d16fb` (main)
**Plan:** `docs/REMEDIATION_PLAN_2026-11-21_P1.md`
**Method:** TDD (RED → GREEN → REFACTOR); every production-code fix has a regression test that failed before the fix and passes after (fixture-only fixes have the 26 baseline failures as their RED evidence).

---

## 1. Verification Ledger (executed evidence)

Environment: rootless PostgreSQL 17 (`docs/setup_pg_z.sh` + `skills/rootless-postgresql`), Redis 8.0.2, Python 3.12 venv, schema v1.0.2 loaded in `ledgersg_dev` and `test_ledgersg_dev`.

| # | Check | Command | Result |
|---|---|---|---|
| 1 | Baseline (pre-remediation, this session) | `pytest --reuse-db --no-migrations -q` | **26 failed, 465 passed, 5 skipped** (matches documented post-P0 baseline exactly) |
| 2 | Full suite (post-remediation) | same | **0 failed, 499 passed, 5 skipped** — the suite is fully green for the first time; +34 passing (26 fixed + 8 new regression tests) |
| 3 | Invariant gates | `pytest tests/invariants -q` | **15 passed** (was 12; +3 CoA trial-balance assertions) |
| 4 | Security gates | `pytest tests/security -q` | **32 passed, 3 skipped** (unchanged — no security regression) |
| 5 | Django system check | `DJANGO_SETTINGS_MODULE=config.settings.testing python manage.py check` | 0 errors, 1 pre-existing warning (`django_ratelimit.W001`) |
| 6 | Clean-venv packaging (A-6) | fresh venv → `pip install -e ".[dev]"` → `manage.py check` | **succeeds**; Django stays 6.0.2 (no downgrade); previously failed with `ModuleNotFoundError: django_celery_beat` then `django_ratelimit` |
| 7 | Lint (new files) | `ruff check tests/integration/test_document_summary.py` | clean; touched legacy files carry pre-existing debt only (210 → 208 findings on those files) |
| 8 | Enum sweep | `grep -rn "PAID_PARTIAL" apps/` | no code hits (comment references only) |
| 9 | Frontend suite | `cd apps/web && npm test` | **321 passed (24 files)** — unchanged, no regression |
| 10 | `.env` ignore test | `cp .env.example` copies + `git status` | copies are ignored; tracked copies removed from the index |

Confidence labels: every row above is **Verified** (executed in this environment).

---

## 2. What Was Fixed

### A-1 + A-5 — The 26-failure fixture debt, eliminated
- `tests/test_api_endpoints.py` `test_organisation` fixture now sets `UserOrganisation.accepted_at` (the tenant middleware only recognises memberships with `accepted_at__isnull=False`; the local fixture shadowed the root conftest's correct one and omitted it). 25 of the 26 documented failures were this single omission.
- `test_create_organisation` payload completed: `gst_reg_date` (serialiser requires it when `gst_registered`) and `entity_type` corrected from `pte_ltd` to the DB CHECK vocabulary `PRIVATE_LIMITED` (the fixture pass unmasked this second payload bug).

### A-2 — `DocumentSummaryView` (three defects in one view)
- `InvoiceDocument.DOCUMENT_TYPE_CHOICES` (phantom attribute) → `DOCUMENT_TYPES`.
- Invalid enum literal `PAID_PARTIAL` → enum-correct outstanding set `["APPROVED", "SENT", "PARTIALLY_PAID", "OVERDUE"]` (documented decision: superset of the original intent and the dashboard's receivables set). The old literal matched nothing, so outstanding/overdue were silently zero.
- `doc.total` (phantom attribute) → `doc.total_incl`, with `sum(..., Decimal("0.00"))` so the empty-org case no longer crashes on `.quantize()`.
- Sweep: `contact_service.deactivate_contact` open-invoice guard had the same `PAID_PARTIAL` literal (a contact holding a partially-paid invoice could be deactivated) — corrected to the enum-correct set including `OVERDUE`.
- Tests: new `tests/integration/test_document_summary.py` (5 tests: 200, counts by status/type, outstanding sum, overdue, empty-org crash).

### A-3 — CoA trial balance rebuilt on real tables
- `AccountService.get_trial_balance()` previously LEFT JOINed the non-existent `coa.account_balance` view → `ProgrammingError` → 500 on `GET /{org}/accounts/trial-balance/`.
- Rewritten to aggregate `journal.line` joined to `journal.entry` (the same pattern the P0 sprint applied to `get_account_balance()`), with the optional `fiscal_year_id` filter honoured via `journal.entry.fiscal_year_id`. LEFT JOIN semantics preserved: active accounts with zero postings still appear.
- Tests: +3 invariant assertions in `tests/invariants/test_journal_balance_queries.py` (aggregation correctness, zero-posting inclusion, fiscal-year filter).

### A-4 — `ValidStatusTransitionsView` signature
- `get(self, request)` → `get(self, request, org_id: str)` (the org-scoped route passes `org_id`; the old signature raised TypeError → 500). Same fix class as the P0 sprint's `EntryTypesView`.

### A-6 — Documented install path completed
- `pyproject.toml` now declares `django-celery-beat==2.9.0` (2.9.0 supports Django 6; the stale `requirements.txt` pin 2.8.1 downgrades Django to 5.x) and `django-ratelimit>=4.1,<5` — both were imported by `config/settings/base.py` INSTALLED_APPS but undeclared.
- Verified end-to-end in a fresh venv (ledger row 6).

### A-7 + A-8 — Env hygiene
- `.gitignore` now excludes `.env`, `.env.local`, `.env.*.local`; the tracked dev copies were removed from the index (`git rm --cached`) — contents were dev placeholders only, no secrets were ever committed.
- New `apps/web/.env.example` (README referenced it; it did not exist) with every variable the frontend actually reads.
- `apps/backend/.env.example` extended with `RATELIMIT_ENABLE`, `DEBUG_TOOLBAR`, `CELERY_ALWAYS_EAGER` + Redis-is-mandatory note.

### A-9 — Schema header
- `database_schema.sql` header `Version: 1.0.1` → `1.0.2` (aligning with §15b and the changelog; comment-only, no DDL change).

---

## 3. Deferred Debt Register (explicit — nothing silently dropped)

Carried forward from `docs/REMEDIATION_PLAN_2026-11-21.md` §4, unchanged except as noted:

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
| Repo-wide ruff debt (1,311 findings measured this session; 963 auto-fixable) | Pre-existing; new/rewritten files are lint-clean |
| A-10 stale root `requirements.txt` (Django 6.0.3 pin, unused packages, beat 2.8.1 pin) | Deferred — pyproject is the canonical manifest; consolidating/removing the second manifest is a repo-owner coordination decision |
| `test_api_endpoints.py` local fixture duplication (shadows the root conftest) | Now correct, but the file could simply consume the root conftest fixtures in a future cleanup |

---

## 4. How to Verify (reproduction commands)

```bash
# Prerequisites: PG on :5432 (schema v1.0.2 loaded), Redis on :6379
cd apps/backend && source .venv/bin/activate
export DB_NAME=test_ledgersg_dev DB_USER=ledgersg DB_PASSWORD=ledgersg_secret_to_change \
       DB_HOST=127.0.0.1 DB_PORT=5432

pytest --reuse-db --no-migrations -q   # 0 failed, 499 passed, 5 skipped
pytest tests/invariants -q             # 15 passed
pytest tests/security -q               # 32 passed, 3 skipped
DJANGO_SETTINGS_MODULE=config.settings.testing python manage.py check

# Packaging (A-6) — fresh venv:
python3 -m venv /tmp/verify_venv && source /tmp/verify_venv/bin/activate
pip install -e ".[dev]" && DJANGO_SETTINGS_MODULE=config.settings.testing python manage.py check
```

**Labels:** §1 is Verified (executed). §2 statements are Verified for the described code state at commit time of this report.
