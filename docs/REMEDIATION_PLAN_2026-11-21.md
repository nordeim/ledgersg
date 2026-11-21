# LedgerSG — Remediation Plan (P0 Sprint)

**Date:** 2026-11-21
**Base commit:** `d7835238` (main)
**Source audit:** `LedgerSG_Code_Review_Audit_Report_2026-11-21.md` (Mode C, findings-only)
**Execution mode:** Mode B/D — TDD (RED → GREEN → REFACTOR), surgical fixes
**Plan validated against:** live codebase + PostgreSQL 17 (rootless) + Redis 8, test baseline reproduced at 468 collected / 393 passed / 67 failed / 8 skipped (matches documented baseline exactly)

---

## 0. Audit Validation Summary (what this plan is built on)

Every Critical finding in the audit was independently re-verified against source before planning:

| Audit ID | Claim | Validation result |
|---|---|---|
| C-01a | `get_f5_box_amounts()` queries `invoicing.invoice`/`invoice_line` (non-existent) | **Confirmed** (`calculation_service.py:232-233`); schema defines `invoicing.document`/`document_line` |
| C-01c/d | Box numbering contradicts schema/IRAS; phantom attrs `box5_output_tax` etc. | **Confirmed**; DB CHECK `chk_box8_net` enforces `box8 = box6_output_tax - box7_input_tax_claimable`; real columns are `box5_total_taxable_purchases`, `box6_output_tax`, `box7_input_tax_claimable` |
| C-01e | `create(due_date=…, filing_frequency=…, label=…)` → TypeError | **Confirmed** (`return_service.py:148-156`); model has only `filing_due_date` |
| C-01f | Serializers declare non-existent fields (`label`, `due_date`, `filing_frequency`, `amendment_reason`) | **Confirmed** (`apps/gst/serializers.py:169-200`) |
| C-01g/H-14 | Statuses `AMENDING`/`PAID` not in DB CHECK set | **Confirmed**; allowed: `DRAFT, COMPUTED, REVIEWED, FILED, AMENDED` |
| C-02 | `_reverse_journal_entry` defined twice; effective body is `pass` | **Confirmed** (`document_service.py:520` and `:809`); real `JournalService.void_document_entry()` exists and works (calls `create_reversal`) |
| C-02 | `void_document()` never sets `void_reason`; `PAID_PARTIAL` wrong enum; `chk_void_reason` requires reason | **Confirmed**; enum value is `PARTIALLY_PAID` |
| C-03 | `SET LOCAL` executed in middleware, outside view transaction | **Confirmed** (`tenant_context.py:118-121`, `audit_context.py:35-39`); Django 6 `make_view_atomic` opens the request transaction strictly inside the view |
| C-04 | `wrap_response` catches bare `Exception` → 500 inside `ATOMIC_REQUESTS` → partial commits; `approve_document` posts journal after atomic block | **Confirmed** (`common/views.py:71-83`, `document_service.py:583-585`) |
| H-01 | `journal_entry__*` lookups raise FieldError | **Confirmed** (`journal_service.py:465,469,497,501`); FK is `entry`; no `is_posted` field exists |
| H-05 | `refresh_access_token()` returns same token; `token_blacklist` not installed; logout swallows | **Confirmed** (`auth_service.py:126-136, 196-204`) |
| H-06 | Default `SECRET_KEY` accepted in production | **Confirmed** (`base.py:22`, `production.py` has no assertion) |
| H-07 | `RATELIMIT_ENABLE` defaults False; not overridden in production | **Confirmed** (`base.py:271`) |

**Independent audit findings (new, not in the report):**

| ID | Finding | Evidence |
|---|---|---|
| NEW-1 | `pip install -e ".[dev]"` fails — `pyproject.toml` has no `[tool.hatch.build.targets.wheel]` packages config (hatchling cannot infer package dir) | Build error reproduced: "Unable to determine which files to ship inside the wheel" |
| NEW-2 | `requests` imported by `ap_storecove_adapter.py:15` but absent from `pyproject.toml` dependencies | `ModuleNotFoundError: No module named 'requests'` in test run before manual install |
| NEW-3 | Auth API contract drift between views and integration tests: tests POST `refresh_token` / expect `access_token` + `/api/v1/auth/profile/`; views read `refresh` / return `tokens.access` + `/api/v1/auth/me/` | `tests/integration/test_auth_api.py:125-171` vs `apps/core/views/auth.py:95-112` and `config/urls.py` registration |
| NEW-4 | `testing.py` cache is live Redis (`redis://localhost:6379/1`) — entire suite 500s (`tenant_context_error`) without a running Redis; middleware membership cache + audit context hard-depend on it | Reproduced: 145 failures without Redis, 67 with Redis |

**Key schema facts grounding the GST rewrite** (from live DB):

- `gst.tax_code` seeds carry the authoritative IRAS F5 mapping: `SR→f5_supply_box=1, f5_tax_box=6`; `ZR→2`; `ES→3`; `TX/RS/ZP→f5_purchase_box=5, f5_tax_box=7`; `TX-E/BL/EP/OP→purchase box 5, no tax box` (blocked/denied input tax); rate history rows `0.07/0.08/0.09` with `effective_from`.
- `gst.return` CHECKs: `chk_box4_total` (box4 = 1+2+3 unless DRAFT), `chk_box8_net` (box8 = box6 − box7 unless DRAFT).
- `doc_status` enum: `DRAFT, APPROVED, SENT, PARTIALLY_PAID, PAID, OVERDUE, VOID`.
- `invoicing.document_line` has `line_amount`, `gst_amount`, `tax_code_id`, `is_bcrs_deposit`; `invoicing.document` has `document_type`, `document_date`, `status`.

---

## 1. Execution Scope Decision

The full audit contains 52 findings (4 Critical / 14 High / 16 Medium / 10 Low / 8 Info). This sprint executes **P0 (stop the bleeding) plus the low-risk security/config quick wins** — everything that restores core accounting correctness, tenant isolation, and rollback safety. Larger schema-wide work is explicitly deferred (Section 4) and documented as debt; nothing is silently dropped.

Guiding rule (Decision Priority Hierarchy): correctness & safety > security > reliability > maintainability. Every fix ships with a regression test written first.

---

## 2. Task Breakdown (ordered, vertical slices)

### Task 1 (C-04): Make `wrap_response` transaction-safe; move journal posting inside the approve atomic block

**Problem.** `wrap_response` converts every unhandled exception into a 500 *Response*. Under `ATOMIC_REQUESTS = True` Django sees a normal return and **commits** partial multi-step financial state. Compounding: `approve_document()` posts the journal entry *after* its `atomic()` block exits.

**Fix.**
1. `common/views.py`: keep typed mappings (`ValidationError`→400, `ResourceNotFound`→404, `DuplicateResource`→409); for unexpected exceptions, log with `exc_info` and **re-raise** so the surrounding atomic block rolls back. (A typed 500 body is produced by the DRF exception handler / server error page; rollback correctness outranks a pretty error body.)
2. `document_service.py approve_document()`: move `_post_journal_entry()` and `_queue_peppol_transmission()` inside the `with transaction.atomic():` block so a posting failure rolls back the `APPROVED` transition.

**TDD.**
- RED: `tests/invariants/test_atomic_rollback.py::test_approve_rolls_back_when_journal_post_fails` — monkeypatch `JournalService.post_invoice` to raise; assert document status remains `DRAFT` and no journal entry exists after the call raises.
- RED: `tests/invariants/test_atomic_rollback.py::test_wrap_response_reraises_unexpected` — a view raising `RuntimeError` propagates (assertRaises), proving the atomic block sees the exception.
- GREEN: implement; REFACTOR: none.

**Done when:** both tests pass; full suite no regression; grep shows no `except Exception` swallow in `wrap_response`.
**Files:** `common/views.py`, `apps/invoicing/services/document_service.py`, new `tests/invariants/test_atomic_rollback.py`.
**Dependencies:** none.

---

### Task 2 (C-02): Restore GL reversal on void

**Problem.** Duplicate `_reverse_journal_entry` (second is `pass`); `void_reason` never persisted; voidable status list uses `PAID_PARTIAL` (invalid enum → partially-paid invoices can never be voided); the skipped integration test `test_void_creates_reversal_entries` masks the defect.

**Fix.**
1. Delete the placeholder duplicate at `document_service.py:809-821` (keep the real one at ~520 that calls `JournalService.void_document_entry()` exactly once).
2. In `void_document()`: set `document.void_reason = reason`; change the voidable set to `["APPROVED", "SENT", "PARTIALLY_PAID"]` sourced from the enum vocabulary.
3. Un-skip `tests/integration/test_invoice_operations.py::test_void_creates_reversal_entries`.
4. Add a net-zero property test: post → void → every affected GL account nets to zero.

**TDD.**
- RED: un-skipped reversal test fails against the placeholder (`pass`) implementation.
- RED: `test_void_persists_reason` — void then re-fetch; `void_reason == reason`.
- RED: `test_void_net_zero_gl_impact` — sum of debits/credits per account after post+void equals the pre-post balance.
- GREEN: implement deletions + assignments.

**Done when:** tests pass; `grep -c "_reverse_journal_entry" document_service.py` shows exactly one definition.
**Files:** `apps/invoicing/services/document_service.py`, `tests/integration/test_invoice_operations.py`, new `tests/invariants/test_void_reversal.py`.
**Dependencies:** Task 1 (so failures roll back rather than half-commit).

---

### Task 3 (C-03): Put RLS `SET LOCAL` inside the request transaction

**Problem.** `SET LOCAL` is transaction-scoped; executed in middleware `__call__` it lands in its own autocommit statement and is gone before any view query. Either deny-all (no rows) or leak (if RLS bypassed) — and audit `user_id` resolves to NULL.

**Fix (minimal, framework-correct).**
1. `tenant_context.py`: wrap the authenticated org-scoped path in `with transaction.atomic():` that (a) executes the `SET LOCAL app.current_org_id/user_id` statements, then (b) calls `self.get_response(request)` **inside the same transaction**. Django's `make_view_atomic` wraps the view in a nested atomic (savepoint) inside ours, so `SET LOCAL` is live for every view query and the whole request commits/rolls back as one unit.
2. Same treatment for the unauthenticated branch (`SET LOCAL … = ''`) so RLS fails closed.
3. `audit_context.py`: same transaction wrapping for `app.client_ip/user_agent/request_path` (audit triggers read them).
4. Exceptions from the view must propagate (guaranteed after Task 1) so the middleware's atomic block rolls back.
5. Keep the membership verification query *before* opening the transaction (it is a read; no RLS needed).

**TDD.**
- RED: `tests/security/test_rls_transaction_isolation.py` (new, `TransactionTestCase` — no wrapping transaction, mirrors production autocommit): authenticate as org A, hit an org-A endpoint via the full middleware stack, and inside the view assert `current_setting('app.current_org_id', true) == str(org_a.id)`; then request org B's URL as org A's user and assert 403 + zero rows.
- GREEN: implement.

**Done when:** the `TransactionTestCase` passes (it cannot pass with the old code because the setting is discarded); existing `test_rls_context.py` still passes (pytest-django transactions make both work, but the new test only passes with the fix).
**Files:** `common/middleware/tenant_context.py`, `common/middleware/audit_context.py`, new `tests/security/test_rls_transaction_isolation.py`.
**Dependencies:** Task 1.

---

### Task 4 (H-01): Fix trial balance / account balance lookups

**Problem.** `JournalLine` FK is `entry` (not `journal_entry`) and no `is_posted` field exists. `get_account_balance()` and `get_trial_balance()` raise `FieldError` → 500 on `GET /journal/trial-balance/` and `/journal/accounts/{id}/balance/`.

**Fix.** Replace `journal_entry__org_id` → `entry__org_id`; `journal_entry__entry_date` → `entry__entry_date`; drop `journal_entry__is_posted=True` (posting is implied by row existence in the immutable-entry design). Also fix the N+1 loop: aggregate lines grouped by account in one query instead of per-account queries.

**TDD.**
- RED: `apps/journal/tests/test_balance_queries.py::test_get_trial_balance_returns_rows` and `::test_get_account_balance_sums_debits_credits` — create a posted entry via `JournalService`, call the methods directly, assert totals (currently raises `FieldError`).
- GREEN: implement.

**Done when:** direct service calls return correct totals; no `journal_entry__` references remain.
**Files:** `apps/journal/services/journal_service.py`, new `apps/journal/tests/test_balance_queries.py`.
**Dependencies:** none.

---

### Task 5 (C-01 + H-14): Rebuild the GST F5 pipeline against the real schema

**Problem.** Non-functional end-to-end: wrong tables, wrong box numbering, phantom attribute writes, phantom constructor kwargs, serializer fields that raise `ImproperlyConfigured`, status vocabulary that violates the DB CHECK.

**Fix.**
1. `calculation_service.get_f5_box_amounts()`: rewrite the SQL against `invoicing.document d JOIN invoicing.document_line dl ON dl.document_id = d.id JOIN gst.tax_code tc ON tc.id = dl.tax_code_id`, filtered by `d.org_id`, `d.document_date BETWEEN`, `d.status IN ('APPROVED','SENT','PARTIALLY_PAID','PAID','OVERDUE')` (VOID excluded), `dl.is_bcrs_deposit = FALSE` (or keep BCRS amounts out of boxes — they are out of scope for GST). Drive box placement **exclusively from `tc.f5_supply_box` / `tc.f5_purchase_box` / `tc.f5_tax_box`** with `tc.is_claimable` honoured for Box 7, split sales vs purchase documents on `d.document_type` prefix (`SALES_%` contributes supply/output side; `PURCHASE_%` contributes purchase/input side). Adopt the IRAS/schema convention everywhere:
   - Box 1/2/3 = std-rated/zero-rated/exempt supplies (net of GST, `line_amount`)
   - Box 4 = 1+2+3 (derived, server-side)
   - Box 5 = total taxable purchases (`line_amount` where `f5_purchase_box = 5`)
   - Box 6 = output tax due (`gst_amount` where `f5_tax_box = 6`)
   - Box 7 = input tax claimed (`gst_amount` where `f5_tax_box = 7` AND `is_claimable`)
   - Box 8 = 6 − 7 (derived)
   - Box 13 = total revenue (1+2+3)
   - Box 14 = reverse charge supplies (`tc.is_reverse_charge`)
2. `return_service.py`:
   - `create_return_periods()`: `GSTReturn.objects.create(org_id=…, period_start=…, period_end=…, filing_due_date=due_date, status="DRAFT")` — real fields only.
   - `generate_f5()`: write the real columns (`box5_total_taxable_purchases`, `box6_output_tax`, `box7_input_tax_claimable`, `box13_total_revenue`, `box14_reverse_charge_supplies`), set `status="COMPUTED"`, `computed_at=timezone.now()`. Persist via explicit field assignment and `save(update_fields=[...])`.
   - `file_return()`: allow `DRAFT/COMPUTED/REVIEWED → FILED`; set `filed_at`, `filed_by_id`, `iras_confirmation=filing_reference`; **replace the `hasattr` mass-assignment with a strict allow-list** of the 15 `boxN_*` model fields with `Decimal` coercion; reject unknown keys with 400; recompute Box 4 and Box 8 server-side and ignore client values.
   - `amend_return()`: `FILED → AMENDED` (allowed set); write `notes` for the amendment reason (no `amendment_reason` column exists — documented decision: use `notes`, defer schema extension).
   - `pay_return()`: the schema has no payment columns — **stop writing phantom attributes**; raise `ValidationError("GST payment tracking requires a schema extension (deferred)")` and keep the endpoint from silently discarding data. (Deferred debt, see Section 4.)
   - `review_return()`: `COMPUTED → REVIEWED` with `reviewed_at/reviewed_by_id`.
3. `apps/gst/serializers.py`: `GSTReturnListSerializer` fields → `id, return_type, period_start, period_end, filing_due_date, status, days_until_due, net_gst` (computed from `filing_due_date`); `GSTReturnDetailSerializer` → real fields + `boxes` map + `filing` (from `filed_at/filed_by/iras_confirmation`); drop `label`, `due_date`, `filing_frequency`, `amendment_reason`, `payment`.
4. `common/constants.py` (new): single source of truth for `DOC_STATUSES`, `VOIDABLE_STATUSES`, `GST_RETURN_STATUSES`, `FILEABLE_STATUSES` re-exporting from model TextChoices — one vocabulary module (starts M-08 remediation).

**TDD.**
- RED: `tests/invariants/test_f5_tieout.py` (new, fixture-driven): create org + chart + tax codes (SR 9%, ZR, ES, TX 9%, TX-E) + posted sales/purchase documents in a period; call `generate_f5()`; assert **persisted** values via `GSTReturn.objects.get(...)`: `box1+box2+box3 == box4`, `box6-box7 == box8`, Box 7 excludes TX-E (not claimable), BCRS line excluded, VOID document excluded, foreign-org document excluded.
- RED: serializer smoke test — `GSTReturnListSerializer(instance).data` does not raise (currently `ImproperlyConfigured`).
- RED: `test_file_return_rejects_unknown_box_keys` — 400 on `{"org_id": "..."}`.
- RED: `test_amend_return_uses_allowed_status`.
- GREEN: implement; REFACTOR: extract the box-mapping dict.

**Done when:** F5 tie-out test passes against persisted values; `GET /gst/returns/` no longer 500s; state-machine test over `DRAFT→COMPUTED→REVIEWED→FILED→AMENDED` passes.
**Files:** `apps/gst/services/calculation_service.py`, `apps/gst/services/return_service.py`, `apps/gst/serializers.py`, `common/constants.py` (new), new tests.
**Dependencies:** Task 1 (atomicity), Task 4 (journal service healthy).

---

### Task 6 (M-01 / I-01): Schema–model conformance gate

**Problem.** `managed = False` mirrors drift silently; three drift classes already materialised (C-01a, C-01d, H-01).

**Fix.** New `tests/invariants/test_schema_conformance.py`: introspect `information_schema.columns` for every concrete model (exclude Django internals, auth/celery built-ins); assert every declared `(db_table, db_column)` exists with a compatible type (`numeric` ↔ DecimalField, `uuid` ↔ UUIDField, `date`/`timestamp` ↔ Date/DateTime, `boolean` ↔ Boolean, `character varying` ↔ Char/Text). Parse the `db_table = 'schema"."table'` quoting convention.

**TDD.** RED: the test initially fails on GST phantom references (they are gone after Task 5, so write it to catch the *next* drift) — prove it works by asserting it catches a deliberately-drifted temp model in-test. GREEN: all real models pass.

**Done when:** conformance test passes and is wired into the default pytest run (invariants directory auto-collected).
**Files:** new `tests/invariants/test_schema_conformance.py`.
**Dependencies:** Task 5 (so the suite is green when the gate lands).

---

### Task 7 (H-05 core, H-06, H-07, NEW-1, NEW-2): Security & packaging quick wins

**Fixes.**
1. **H-05 core** — refresh rotation + revocation:
   - Add `rest_framework_simplejwt.token_blacklist` to `INSTALLED_APPS`.
   - Add the two blacklist tables (`outstanding_token`, `blacklisted_token`) to `database_schema.sql` as a versioned §15b patch (SQL-First: schema is truth; the app's own migrations are NOT run — DDL is hand-written to match `MIGRATE = False`), mirroring simplejwt 5.5 field definitions, owned by `ledgersg_owner`, granted to `ledgersg_app`, no RLS (tokens are user-scoped, not org-scoped).
   - `refresh_access_token()`: verify the old token is not blacklisted, mint a NEW refresh token (rotation), blacklist the predecessor, return the new pair; use `timezone.now()` + `SIMPLE_JWT["ACCESS_TOKEN_LIFETIME"]` instead of naive `datetime.now()+15min`.
   - `logout_user()`: blacklist works now (tables exist); keep graceful handling of already-blacklisted tokens but log at warning instead of bare `pass`.
   - `change_password()`: blacklist all of the user's outstanding refresh tokens.
2. **H-06** — `production.py`: fail fast when `SECRET_KEY` is a known default or shorter than 50 chars (`raise ImproperlyConfigured`).
3. **H-07** — `base.py`: `RATELIMIT_ENABLE` default `True`; `testing.py`: explicitly `False` (tests currently rely on the disabled state; flipping the default without this would make auth tests rate-limit each other).
4. **NEW-1** — `pyproject.toml`: add `[tool.hatch.build.targets.wheel] packages = ["apps", "common", "config"]` so `pip install -e ".[dev]"` works (documented install path).
5. **NEW-2** — add `requests>=2.32` to dependencies (used by the Storecove adapter).

**TDD.**
- RED: `tests/security/test_token_lifecycle.py` (new): refresh returns a *different* refresh token; the old one is rejected on second use; logout blacklists; change_password revokes existing refresh tokens.
- RED: `tests/security/test_settings_gates.py` (new): production SECRET_KEY default raises `ImproperlyConfigured` (import settings with env override).
- GREEN: implement; run `pip install -e ".[dev]"` in a clean venv to prove NEW-1.

**Done when:** token lifecycle tests pass; settings gate test passes; editable install succeeds.
**Files:** `config/settings/base.py`, `config/settings/production.py`, `config/settings/testing.py`, `apps/core/services/auth_service.py`, `apps/backend/database_schema.sql`, `pyproject.toml`, new tests.
**Dependencies:** none (parallel-safe with Tasks 4-6).

---

### Task 8 (NEW-3, NEW-4): Contract & environment alignment for the auth suite

**Problem.** Integration tests assert a contract the views never served (`/profile/`, `refresh_token`, `access_token` at top level). The backend contract (`/me/`, `refresh`, `tokens.access`) is the one the frontend consumes (`api-client.ts` handles `tokens.access`) — **the tests are the stale side**. Also, the 67-failure baseline contains these contract failures mixed with real bugs.

**Fix.**
1. Update `tests/integration/test_auth_api.py` (+ the same drift in `test_auth_org_context.py` where applicable) to the served contract: `/api/v1/auth/me/`, `{"refresh": ...}`, `response.data["tokens"]["access"]`. Login assertions updated to `tokens.access`.
2. NEW-4 (decision, documented): keep `testing.py` Redis cache (membership cache is production behaviour we want exercised) but document the prerequisite (`Redis on 6379`) in README test section — changing to locmem would stop exercising the real cache path.
3. Re-run the full suite; the remaining `tests/test_api_endpoints.py` fixture-isolation failures are pre-existing documented debt (Section 4) — not silently ignored: listed with counts and root cause.

**TDD.** Contract tests are the tests — updated to the documented contract, then must pass.

**Done when:** auth integration tests pass; full suite strictly better than the 67-failure baseline; every remaining failure accounted for in the deferred-debt register.
**Files:** `tests/integration/test_auth_api.py`, `tests/integration/test_auth_org_context.py` (if same drift), `README.md` (test prerequisites note).
**Dependencies:** Task 7 (rotation changes the refresh response shape the tests assert).

---

### Task 9: Documentation alignment

Update only what the remediation changed (no capability inflation):
1. `README.md` — test execution prerequisites (Redis), corrected backend test expectations, remediation note.
2. `CLAUDE.md` — version bump note, status correction (audit-driven; "100% security score" claims replaced by the remediated-state description).
3. `AGENTS.md` — troubleshooting additions: SET LOCAL/transaction pattern, wrap_response re-raise contract, GST box convention, conformance gate.
4. `Project_Architecture_Document.md` — middleware chain description corrected (transaction-wrapping middleware), box numbering table aligned to schema.
5. New `docs/REMEDIATION_2026-11-21_REPORT.md` — what was fixed, what was verified (with commands), deferred debt register.
6. `database_schema.sql` header version → 1.0.2 (blacklist tables added).

**Done when:** docs describe the code as it is; no claim contradicts a verifiable artefact.

---

### Task 10: `ledgersg_SKILL.md`

Distil the remediated codebase into `ledgersg_SKILL.md` at repo root using `skills/distill-codebase-skill` (reference template) + `skills/to-distill-project-into-skill` (meta-skill process): architecture map, SQL-First rules, test workflow (PG+Redis prerequisites, `--reuse-db --no-migrations`), the ten hard lessons from this remediation, verification gates.

---

## 3. Verification Gate (definition of done for the sprint)

```bash
# 0. Environment
pg (rootless 5432) + redis (6379) running; schema loaded in test_ledgersg_dev

# 1. Django system check
DJANGO_SETTINGS_MODULE=config.settings.testing python manage.py check   # 0 errors (1 known W001)

# 2. Full suite (must be strictly better than baseline 67F/393P/8S)
pytest --reuse-db --no-migrations -q

# 3. New invariant gates
pytest tests/invariants -q            # atomic rollback, void net-zero, F5 tie-out, schema conformance
pytest tests/security -q              # RLS TransactionTestCase, token lifecycle, settings gates

# 4. Packaging
pip install -e ".[dev]"               # succeeds (NEW-1)

# 5. Lint (guardrails not weakened)
ruff check apps common config tests
```

Claims will be labelled **Verified** (executed) / **Reasoned** / **Assumed** in the final report.

---

## 4. Deferred Debt Register (explicit, not silent)

| Audit IDs | Item | Why deferred | Entry point when picked up |
|---|---|---|---|
| H-02 | Base-currency reporting, retained earnings, BS assertion, real trial balance report | Requires reporting-spec design (period close semantics) | `apps/reporting/views.py` rewrite |
| H-03 | Widen 80 `NUMERIC(10,4)` columns to `NUMERIC(19,4)` | Schema-wide versioned patch + full model alignment + reseed; high blast radius for one sprint | `database_schema.sql` §3-§9 + all money models |
| H-04 | Rate history resolution by document date | Needs line-level snapshot semantics decision | `tax_code_service.get_tax_code_by_code()` ordering + `add_line` |
| H-08 | Wire `send-invoicenow` to `TransmissionService` | Needs adapter contract decision + live AP config | `document_service.send_invoicenow()` |
| H-09 | Tax-invoice fields + PDF `document_number` | PDF template + approval flow touchpoints | `invoice_pdf.html`, `approve_document()` |
| H-10 | Schematron fail-closed validation | Requires schema path strategy + lxml isoschematron wiring | `xml_validation_service.py` |
| H-11 | Fiscal close controls | Needs closing-entry design (ties into H-02) | `core/views/fiscal.py` |
| H-12 | (absorbed into Task 5 — allow-list done; serializer per-box typing deferred) | — | `apps/gst/serializers.py` |
| H-13 | Reproducible container build | Infrastructure work | `apps/backend/Dockerfile` |
| M-02/M-03 | Ledger REVOKE/trigger, audit RLS + hash chain | DB privilege redesign | `database_schema.sql` §12/§15 |
| M-04..M-16 | Sequence-in-transaction, discounts, statement reconciliation, FX, dead code, SSRF, etc. | Feature-level work, each needs its own TDD slice | per audit §5 |
| L-01..L-10, I-01..I-08 | Hygiene, CI, dependency audits | Batch after correctness | per audit §6-7 |
| test_api_endpoints.py (26 fails) | Fixture isolation (auth_client + RLS) | Pre-existing documented issue; needs fixture architecture pass | `tests/test_api_endpoints.py` |
| gst payment tracking | `pay_return` intentionally raises until schema extension | Schema-first rule | new §5b tables when scheduled |

---

## 5. Commit Plan (conventional commits, single branch `main`)

1. `fix(api): re-raise unexpected exceptions so ATOMIC_REQUESTS rolls back (C-04)`
2. `fix(invoicing): restore GL reversal on void; persist void_reason; fix enum (C-02)`
3. `fix(middleware): set RLS/audit session vars inside request transaction (C-03)`
4. `fix(journal): correct FK lookups in trial balance and account balance (H-01)`
5. `fix(gst): rebuild F5 pipeline on real schema with IRAS box convention (C-01, H-14)`
6. `test(invariants): add schema-model conformance gate (M-01/I-01)`
7. `fix(security): refresh rotation + blacklist, SECRET_KEY gate, ratelimit default (H-05/6/7)`
8. `build(pyproject): fix editable install; declare requests (NEW-1/2)`
9. `test(auth): align integration tests with served contract (NEW-3)`
10. `docs: align documentation with remediated codebase; add remediation report`
11. `docs(skill): add ledgersg_SKILL.md distilled from remediation`
