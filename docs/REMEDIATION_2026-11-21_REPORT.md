# LedgerSG — Remediation Report (P0 Sprint)

**Date:** 2026-11-21
**Base commit:** `d7835238` (main)
**Plan:** `docs/REMEDIATION_PLAN_2026-11-21.md`
**Source audit:** `LedgerSG_Code_Review_Audit_Report_2026-11-21.md`
**Method:** TDD (RED → GREEN → REFACTOR); every fix below has a regression test that failed before the fix and passes after.

---

## 1. Verification Ledger (executed evidence)

Environment: rootless PostgreSQL 17 (`docs/setup_pg_z.sh` + `skills/rootless-postgresql`), Redis 8, Python 3.12 venv, schema v1.0.2 loaded in `ledgersg_dev` and `test_ledgersg_dev` (30 domain tables + 2 blacklist tables).

| # | Check | Command | Result |
|---|---|---|---|
| 1 | Test baseline (pre-remediation) | `pytest --reuse-db --no-migrations -q` | **67 failed, 393 passed, 8 skipped** (matches README's documented baseline exactly) |
| 2 | Test suite (post-remediation) | same | **26 failed, 465 passed, 5 skipped** — +72 passing; all 26 remaining are the pre-existing `tests/test_api_endpoints.py` fixture-isolation debt (same 26 as baseline) |
| 3 | New invariant gates | `pytest tests/invariants -q` | **10 passed** (atomic rollback, void reversal + reason + net-GL, F5 tie-out, schema conformance, journal balances) |
| 4 | Security gates | `pytest tests/security -q` | **32 passed, 3 skipped** (RLS transaction isolation incl. TransactionTestCase + app-role row filter, token rotation/blacklist, settings gates) |
| 5 | Django system check | `DJANGO_SETTINGS_MODULE=config.settings.testing python manage.py check` | 0 errors, 1 pre-existing warning (`django_ratelimit.W001`) |
| 6 | Packaging | `pip install -e ".[dev]"` | **succeeds** (previously failed: missing hatch wheel config) |
| 7 | Lint (files touched by this sprint) | `ruff check <touched files>` | **All checks passed** (repo-wide lint debt documented as deferred) |

Confidence labels: all rows above are **Verified** (executed in this environment). No claim below relies on an unexecuted check.

---

## 2. What Was Fixed

### C-04 — Partial commits inside ATOMIC_REQUESTS
- `common/views.py`: `wrap_response` re-raises unexpected exceptions (logged with exc_info) so the atomic request wrapper rolls back; typed 400/404/409 mappings unchanged.
- `document_service.approve_document()`: journal posting + Peppol queueing moved INSIDE the `transaction.atomic()` block.
- Tests: `tests/invariants/test_atomic_rollback.py` (forced posting failure leaves status `DRAFT`, no journal entry; decorator propagates `RuntimeError`).

### C-02 — Void did not reverse the GL
- Deleted the duplicate placeholder `_reverse_journal_entry` (second definition, body `pass`); the single remaining definition calls `JournalService.void_document_entry()`.
- `void_document()` now persists `void_reason` (DB CHECK `chk_void_reason`); voidable set corrected to enum values (`PARTIALLY_PAID`, not `PAID_PARTIAL`).
- `create_reversal()` sets `is_reversed = True` together with `reversed_by` (CHECK `chk_reversal_consistency`).
- `void_document_entry()` picks a reversal date in an OPEN period (today, else the original entry's date).
- Reversal call sites pass `user_id` (`journal.entry.posted_by` is NOT NULL).
- Tests: `test_invoice_operations.py` un-skipped and extended (reversal inverts every line; reason persisted; PARTIALLY_PAID voidable; DRAFT not voidable).

### C-03 — RLS context discarded before views ran
- `TenantContextMiddleware` now opens the request transaction ITSELF: `SET LOCAL app.current_org_id/user_id` execute inside `transaction.atomic()` and `get_response(request)` runs in the same transaction (Django's `make_view_atomic` nests as a savepoint inside it). Unauthenticated branch fails closed the same way.
- `AuditContextMiddleware` applies the same pattern for `app.client_ip/user_agent/request_path` (its own atomic for non-org-scoped API paths; savepoint when nested).
- Tests: `tests/security/test_rls_transaction_isolation.py` — `TransactionTestCase` (production autocommit semantics) proves the setting is live INSIDE the view; cross-org 403; unauthenticated deny-all; and an app-role (`ledgersg_app`) connection proves RLS actually filters rows (1 row with context, 0 without).
- Removed the middleware's generic `except Exception → 500 tenant_context_error` swallow (now consistent with C-04 discipline).

### H-01 — Trial balance / account balance FieldError
- `journal_service.get_account_balance()` / `get_trial_balance()`: `journal_entry__*` → `entry__*`; dropped the non-existent `is_posted` predicate; trial balance now one grouped query (N+1 fixed).
- Tests: `tests/invariants/test_journal_balance_queries.py` (sums, date cutoff, TB balances).

### C-01 + H-14 + H-12 — GST F5 pipeline rebuilt
- `get_f5_box_amounts()` rewritten against `invoicing.document`/`document_line` joined to `gst.tax_code`, driven **exclusively** by `f5_supply_box`/`f5_purchase_box`/`f5_tax_box` + `is_claimable` + `is_reverse_charge`; sales vs purchase split on `document_type`; statuses from the real enum; BCRS lines excluded.
- IRAS/schema box convention adopted everywhere: Box 5 = taxable purchases, Box 6 = output tax, Box 7 = input tax claimable, Box 8 = 6−7, Box 4 = 1+2+3 (matches DB CHECKs `chk_box8_net`, `chk_box4_total`).
- `return_service`: real fields only (`filing_due_date`, `iras_confirmation`); explicit field writes with `save()`; status machine `DRAFT→COMPUTED→REVIEWED→FILED→AMENDED` (allowed set); `file_return` uses a strict box allow-list (rejects unknown keys with 400) and recomputes Boxes 4/8 server-side; `amend_return` records the reason in `notes` (no column exists — documented); `pay_return` refuses to fabricate payment evidence (no columns — deferred schema extension).
- Serializers fixed (`filing_due_date`, `return_type`, real box names); `get_f5_json`/`get_upcoming_deadlines` de-phantomed; list/create views aligned (`count` on create).
- Tests: `tests/invariants/test_f5_tieout.py` — fixture-driven tie-out on PERSISTED values: Box 7 excludes TX-E; VOID/DRAFT/BCRS excluded; identities hold; state machine persists; serializers read `.data` cleanly.

### M-01 / I-01 — Schema–model conformance gate
- New `tests/invariants/test_schema_conformance.py`: introspects `information_schema.columns`, asserts every declared `(db_table, db_column)` of all domain models exists with a compatible type (451 columns checked).
- The gate immediately caught two genuinely drifted models, now fixed:
  - `ExchangeRate` — rewritten to the real `core.exchange_rate` columns (org-scoped, natural-key `currency_code`, `rate_date`, no `updated_at`).
  - `OrganisationSetting` — rewritten to real columns (`setting_key`, JSONB `setting_value`, `description`; dropped phantom `value_type`/`category`/`is_encrypted`).

### H-05 (core) — Refresh-token lifecycle
- `token_blacklist` app installed; its two tables added to `database_schema.sql` §15b as hand-written DDL (SQL-First; v1.0.2) and granted to `ledgersg_app`; applied to both databases.
- `refresh_access_token()` now ROTATES (mints a new refresh token, blacklists the predecessor, preserves org claims) and rejects blacklisted tokens; `access_expires` is timezone-aware and derived from `SIMPLE_JWT["ACCESS_TOKEN_LIFETIME"]`.
- `logout_user()` blacklists (now effective) and logs instead of `pass`; `change_password()` revokes all outstanding refresh tokens.
- Tests: `tests/security/test_token_lifecycle.py` (rotation, old-token rejection, logout, password-change revocation, tz-aware expiry).

### H-06 / H-07 — Startup and rate-limit defaults
- `production.py` raises `ImproperlyConfigured` for default/short (`<50` char) SECRET_KEYs.
- `RATELIMIT_ENABLE` defaults to `True` (base); explicitly `False` in testing.
- Tests: `tests/security/test_settings_gates.py`.

### H-09 (partial) — PDF/e-mail invoice number
- `sequence_number` (non-existent attr) → `document_number` in the PDF template, e-mail tasks and the PDF view. Full Reg-11 tax-invoice labelling remains deferred.

### NEW-1 / NEW-2 — Packaging
- `pyproject.toml`: `[tool.hatch.build.targets.wheel] packages` added (editable install works); `requests` declared (Storecove adapter dependency).

### NEW-3 / NEW-4 — Contract & environment alignment
- `set-default-org/` registered in the ACTIVE url package (`apps/core/urls/auth.py`) — it existed only in the shadowed `apps/core/urls.py`, so the endpoint 404'd.
- `EntryTypesView` / GST calculate views accept the `org_id` kwarg their org-scoped routes pass.
- Stale test contracts aligned to the served/documented ones: auth (`/me/`, `refresh`, `tokens.access`, nested org list, `old_password`), GST (org-scoped URLs, 2dp formatting, `box_mapping`), Peppol views (real DB-backed response shape), journal types URL.
- `tests/conftest.py` org fixture now seeds DocumentSequences for all sales/purchase document types (the DB function raises for unconfigured types).
- `AccountService.create_account` no longer passes phantom columns; `AccountDetailSerializer` uses real fields; `get_account_balance` aggregates `journal.line` instead of the non-existent `coa.account_balance` view.

---

## 3. Deferred Debt Register (explicit — nothing silently dropped)

| Item | Status |
|---|---|
| `tests/test_api_endpoints.py` — 26 fixture-isolation failures (auth_client + RLS interplay) | Pre-existing documented debt; needs a fixture-architecture pass |
| H-02 — base-currency reporting, retained earnings, BS assertion, reporting trial balance | Deferred (design work) |
| H-03 — widen 80 `NUMERIC(10,4)` columns to `NUMERIC(19,4)` | Deferred (schema-wide versioned patch) |
| H-04 — GST rate history resolution by document date | Deferred (line-snapshot semantics) |
| H-08 — wire `send-invoicenow` to real `TransmissionService` | Deferred (endpoint returns 501-style "not configured" per audit; test skip documented) |
| H-09 (rest) — `is_tax_invoice`/`tax_invoice_label` population + Reg-11 compliance test | Deferred |
| H-10 — Schematron fail-closed validation, hardened XML parser | Deferred |
| H-11 — fiscal close permissions/validation/closing entries | Deferred |
| H-13 — reproducible container build | Deferred |
| M-02…M-16, L-01…L-10, I-01…I-08 | Deferred per audit roadmap (see audit §12 P1/P2) |
| GST payment tracking (`pay_return`) | Intentionally raises until schema extension lands |
| Repo-wide ruff debt (~1.8k findings, mostly whitespace/import order) | Pre-existing; touched files are lint-clean |

---

## 4. How to Verify (reproduction commands)

```bash
# Prerequisites: PG on :5432 (schema loaded), Redis on :6379
source <venv>/bin/activate
cd apps/backend
export DB_NAME=test_ledgersg_dev DB_USER=ledgersg DB_PASSWORD=ledgersg_secret_to_change \
       DB_HOST=127.0.0.1 DB_PORT=5432

pytest tests/invariants -q                    # 10 passed
pytest tests/security -q                      # 32 passed, 3 skipped
pytest --reuse-db --no-migrations -q          # 26 failed (documented debt), 465 passed, 5 skipped
DJANGO_SETTINGS_MODULE=config.settings.testing python manage.py check
pip install -e ".[dev]"                       # succeeds
```

**Labels:** everything in §1 is Verified (executed). §2 statements are Verified for the described code state at commit time of this report.
