# LedgerSG — Comprehensive Code Review & Audit Report

**Repository:** `https://github.com/nordeim/ledgersg`
**Commit audited:** `82ecd620` ("rootless postgresql db setup"), HEAD of `main` as cloned
**Audit date:** 2026-11-21
**Auditor mode:** Mode C (Audit / Review) — *findings only, no source modifications made to the repository*
**Skill pipeline:** `code-review-and-audit` (deep profile) orchestrating `code-review-checklist`, `code-quality-standards` (Six-Axis), `vulnerability-scanner` (OWASP 2025), `verification-and-review-protocol` (Iron Law / confidence signalling), plus the finance-domain skills `statement-auditor` (F5 tie-out discipline) and `gl-reconciler` (GL ↔ subledger reconciliation discipline) adapted to a GST/GL context.

---

## 0. Executive Summary

LedgerSG is a Django 6 + Next.js 16 double-entry accounting platform aimed at Singapore SMBs with IRAS GST obligations. The repository shows genuine engineering ambition: a 3,202-line PostgreSQL schema with RLS policies, Decimal-safe money helpers, a service-layer architecture, 467 collected backend tests, and extensive design documentation.

**However, the code as committed does not currently produce correct books or a fileable GST F5.** The failures are not stylistic. Four defects independently break the platform's core promise:

| # | What is broken | Consequence |
|---|---|---|
| **C-01** | The GST F5 pipeline is non-functional end-to-end (queries tables that do not exist; writes to model attributes that do not exist; serializers raise on first access) | No GST return can be generated, viewed, filed, or amended. A GST-registered tenant has **no compliant filing path**. |
| **C-02** | Voiding an invoice or payment does not reverse the general ledger (the effective method is a duplicated `pass` placeholder) | Books remain permanently wrong after any void; assets/liabilities drift from reality with no error surfaced. |
| **C-03** | The RLS tenant context (`SET LOCAL`) is executed outside the request transaction and is therefore discarded before any view runs | Database-level tenant isolation is ineffective in production; the same mechanism leaves the audit trail with no actor identity. |
| **C-04** | `wrap_response` converts every unhandled exception into a 500 *inside* `ATOMIC_REQUESTS`, so partial writes commit | Multi-step financial operations that fail halfway leave committed partial state — silent corruption rather than rollback. |

Net effect: **the platform is not release-ready for production bookkeeping or IRAS filing.** The remediations documented in the repo (`AUTHENTICATION_REMEDIATION_COMPLETE.md`, `InvoiceNow_Phase3-4_Completion_Summary.md`, `CORS_FIX_IMPLEMENTATION_COMPLETE.md`, "100% Security Score") do not correspond to the state of the code in this commit; several are contradicted by verifiable evidence in the tables below.

### Findings by severity

| Severity | Count | Release gate |
|---|---|---|
| 🔴 Critical | 4 | Blocks release. Fix before anything else. |
| 🟠 High | 14 | Must fix before any production pilot with real tenant data. |
| 🟡 Medium | 16 | Fix within the sprint; several become High once multi-currency or multi-tenant usage begins. |
| 🟢 Low | 10 | Schedule; hygiene and consistency. |
| ⚪ Info | 8 | Backlog / architectural guidance. |

### Scorecard (Six-Axis, 0–5)

| Axis | Score | Basis |
|---|---|---|
| Correctness | **1.5** / 5 | Broken GST returns, no-op reversals, crashing trial balance, currency-mixed statements |
| Security | **2.0** / 5 | RLS ineffective, rate limiting off by default, token lifecycle unenforced, but no injection or hardcoded production secrets found |
| Architecture | **3.0** / 5 | Clean service/view separation and SQL-first schema, undermined by duplicated services, dead modules and model/schema drift |
| Performance | **3.0** / 5 | Reasonable indexing and caching; N+1 loops in trial balance and reconciliation suggestions |
| Testing | **1.5** / 5 | 467 tests collected, but the highest-risk controls are skipped, and tests are masked by test-harness transactions |
| Regulatory fit | **1.5** / 5 | F5 unproducible, tax invoices never labelled, PINT-SG validation fails open, audit actor not recorded |

**Bottom line — Reasoned (high confidence):** treat this as a **pre-alpha accounting engine with a partially working UI shell**, not a "production-grade, enterprise-grade" platform as the docs assert.

---

## 1. Scope, Method & Verification Ledger

### 1.1 Review surface

| Area | Files | Lines (approx.) |
|---|---|---|
| Backend Python (`apps/backend`) | 187 `.py` (excl. `__pycache__`) | 32,588 |
| Database schema | `database_schema.sql` | 3,202 |
| Frontend TypeScript/React (`apps/web/src`) | 108 files (104 `.ts`/`.tsx`) | 11,018 TS/TSX |
| Test suites (backend) | 42 `test_*.py` files (41 test modules + 1 runner script) | 467 tests collected |
| Markdown docs in repo (excluding `skills/`) | 277 `.md` | — |

Review dimensions covered (per `code-review-and-audit` Phase 3 + Six-Axis): correctness, security (OWASP A01–A10), data integrity, error handling, performance, testing, maintainability, consistency, dependency health, and — added for this domain — **regulatory compliance** (IRAS GST F5, IRAS Regulation 11 tax invoices, InvoiceNow/PINT-SG, record retention/audit trail, PDPA-adjacent data handling).

### 1.2 What was actually executed (evidence, not assertion)

| # | Check | Command / method | Result |
|---|---|---|---|
| 1 | Django system check | `DJANGO_SETTINGS_MODULE=config.settings.testing python manage.py check` | **PASSED**, 1 warning (`django_ratelimit.W001`: RedisCache not officially supported) |
| 2 | Backend test collection | `python -m pytest --collect-only -q` | 467 collected, **1 collection error** (`tests/test_db_conn.py` imports `psycopg`) |
| 3 | Non-DB test subset | `pytest common/tests/test_decimal_utils.py apps/peppol/tests/test_xml_* apps/peppol/tests/test_ap_adapter_base.py` | **42 passed, 18 errors** — all 18 errors were `psycopg2.OperationalError: connection refused` (no PostgreSQL in this sandbox), i.e. infrastructure, not source defects |
| 4 | Field-lookup resolution | Custom harness (`audit_work/harness.py`) building the querysets the services build | **Verified**: `FieldError: Cannot resolve keyword 'journal_entry'` |
| 5 | GST model/attribute contract | Same harness, `GSTReturn._meta.get_fields()` vs attributes used by service + serializers | **Verified**: 12 attributes used by code do not exist on the model |
| 6 | Live method resolution | `inspect.getsource(DocumentService._reverse_journal_entry)` | **Verified**: definition count = 2; effective body is `pass` (placeholder) |
| 7 | DRF serializer contract | Instantiate list/detail GST serializers and read `.data` | **Verified**: `ImproperlyConfigured: Field name 'label' is not valid for model 'GSTReturn'` |
| 8 | Framework transaction semantics | Inspect installed Django 6.0 `django/core/handlers/base.py` (`_middleware_chain`, `make_view_atomic`) | **Verified**: middleware wraps `_get_response`; `transaction.atomic` is applied *inside* it → middleware-level `SET LOCAL` sits outside the request transaction |
| 9 | Skill scanner (Phase 3) | `python skills/code-review-and-audit/scripts/checklist_runner.py apps/backend` | 29 findings: 18 "critical" **all triaged as false positives** (test fixtures `testpassword123`, docstring "JWT Bearer token required"), 5 CAPS-comment false positives, 1 genuine `no_gitignore` signal |
| 10 | Secret sweep | Regex sweep for `SECRET_KEY|PASSWORD|API_KEY|TOKEN =` across `.py/.ts/.sh/.yml` | 1 committed JWT in `start_apps.sh:224` (expired 2026-03-08); committed `.env` with placeholder credentials |
| 11 | Dependency inventory | `pyproject.toml`, `apps/web/package.json`, `package-lock.json` presence | Pinned Python deps; **unpinned** installs in `Dockerfile` (see H-13) |
| 12 | Schema/model/table conformance | Cross-reading `database_schema.sql` §3–§14 against `apps/core/models/*` and raw SQL in services | Multiple mismatches (C-01, M-01, M-04) |

**Not verifiable in this environment (explicitly flagged):** end-to-end runtime behaviour against a live PostgreSQL instance (RLS policy enforcement, constraint behaviour, `numeric field overflow`), browser/E2E/Playwright runs, Lighthouse/Core Web Vitals, and `npm audit` / `pip-audit` CVE results (no network-fetched advisories). Claims that depend on these are labelled **Reasoned** or **Assumed**, never **Verified**.

### 1.3 Confidence vocabulary used below

- **Verified** — executed or read the exact artefact and observed the stated result.
- **Reasoned** — logical inference from code/documentation, not executed.
- **Assumed** — depends on a stated assumption (e.g. production configuration).
- **Unverifiable** — needs an environment this sandbox does not provide.

---

## 2. Architecture As Built (and where it diverges from the design docs)

```
Next.js 16 (App Router, React 19) ──fetch──► Django 6 / DRF
     │  access token in module memory            │  JWT (HS256, SECRET_KEY)
     │  "refresh via HttpOnly cookie" ✗          │  TenantContextMiddleware  ← C-03
     ▼                                           ▼
 apps/web/src/lib/api-client.ts          ┌───────────────────────────────┐
                                         │ apps/*/views.py  (thin)       │
                                         │   @wrap_response  ← C-04      │
                                         │ apps/*/services/*.py (logic)  │
                                         └──────────────┬────────────────┘
                                                        ▼
                                   PostgreSQL 16: 7 schemas, 19 RLS-policied
                                   tables, NUMERIC(10,4), append-only audit
```

Three structural observations drive many findings:

1. **The model layer is a hand-maintained mirror of a hand-written schema** (`managed = False`, `db_table = 'invoicing"."document'`). Nothing enforces conformance — no `makemigrations`, no CI introspection check, no schema-tests. Drift is therefore silent and has already happened (C-01, M-01).
2. **Two parallel implementations exist for several domains** (dashboard, Peppol transmission, invoice reversal). Where they diverge, the one wired to the API is frequently the weaker one (C-02, H-08, M-06).
3. **The documentation asserts completion that the code does not deliver.** Examples verified in this audit:

| Document claim | Code reality | Evidence |
|---|---|---|
| "InvoiceNow Phase 3-4 complete" | `DocumentService.send_invoicenow()` returns fabricated `QUEUED` + random UUIDs with a `# TODO` | `document_service.py:752-772` |
| "Void creates reversal journal entries" | effective `_reverse_journal_entry` body is `pass` | `document_service.py:809-821` (second definition) |
| "Server-side RLS sets `app.current_org_id`" | `SET LOCAL` outside request transaction | `tenant_context.py:118-121` + Django `base.py:193` |
| "SEC-002 rate limiting implemented" | `RATELIMIT_ENABLE` defaults to `False`, not overridden in `production.py` | `settings/base.py:271` |
| "GST F5 with all 15 boxes" | F5 generation queries non-existent tables and writes non-existent attributes | `calculation_service.py:225-245`, `return_service.py:196-205` |
| Test file asserts void reversal | `pytest.skip("Service layer not implemented yet")` | `tests/integration/test_invoice_operations.py:99-100` |

---

## 3. 🔴 Critical Findings

### C-01 — The GST F5 return pipeline is non-functional end-to-end

**Severity:** Critical · **Category:** Correctness / Regulatory compliance · **Confidence:** Verified (queryset + serializer execution), Reasoned (SQL failure mode)

**Locations**

| # | File:line | Defect |
|---|---|---|
| a | `apps/gst/services/calculation_service.py:225-245` | F5 aggregation queries `invoicing.invoice` and `invoicing.invoice_line` — **these tables do not exist**; the schema defines `invoicing.document` / `invoicing.document_line` |
| b | `apps/gst/services/calculation_service.py:237` | Filters `i.status IN ('APPROVED','SENT','PAID_PARTIAL','PAID')` — the `invoicing.doc_status` enum value is `PARTIALLY_PAID`, and `i.status` would be the enum type, so this raises `invalid input value for enum` even if the table existed |
| c | `apps/gst/services/calculation_service.py:186-215` | Box numbering contradicts the database schema and IRAS: service assigns `box5 = output tax`, `box6 = taxable purchases`; IRAS/schema are `Box 5 = total value of taxable purchases`, `Box 6 = output tax due`, `Box 7 = input tax claimed`, `Box 8 = Box 6 − Box 7` |
| d | `apps/gst/services/return_service.py:196-205` | Writes `gst_return.box5_output_tax`, `box6_taxable_purchases`, `box7_input_tax` — **none of these attributes exist on the model** (the model has `box5_total_taxable_purchases`, `box6_output_tax`, `box7_input_tax_claimable`). Assignment succeeds as a plain Python attribute and is silently discarded by `save()` |
| e | `apps/gst/services/return_service.py:152-154` | `GSTReturn.objects.create(due_date=…, filing_frequency=…, label=…)` — model has `filing_due_date` and none of the other two → `TypeError` on the first call to `create_return_periods()` |
| f | `apps/gst/serializers.py:169-172, 195-200` | `GSTReturnListSerializer` / `GSTReturnDetailSerializer` declare `label`, `due_date`, `filing_frequency`, `amendment_reason` — non-existent model fields. Reading `.data` raises `ImproperlyConfigured` → **HTTP 500 for `GET /gst/returns/`** |
| g | `apps/gst/services/return_service.py:282, 320` | Sets status `AMENDING` / `PAID`; DB CHECK allows only `DRAFT, COMPUTED, REVIEWED, FILED, AMENDED` → `IntegrityError` on amend/pay |

**Evidence (executed)**

```
$ python audit_work/harness.py
### GSTReturn attributes used by GSTReturnService
{'missing_from_model': ['box5_output_tax', 'box6_taxable_purchases', 'box7_input_tax',
 'label', 'due_date', 'filing_frequency', 'filing_reference', 'payment_amount',
 'payment_reference', 'paid_at', 'amendment_reason', 'box15_indicator'],
 'real_box_columns': ['box1_std_rated_supplies', ..., 'box5_total_taxable_purchases',
 'box6_output_tax', 'box7_input_tax_claimable', 'box8_net_gst', ...]}

### GST return serializers
{'GSTReturnListSerializer': "ImproperlyConfigured: Field name `label` is not valid
  for model `GSTReturn` in `apps.gst.serializers.GSTReturnListSerializer`."}
```

**Impact.** A GST-registered Singapore business using LedgerSG cannot produce a F5 for its accounting period. Worse than a crash is the *silent* variant: `generate_f5()` returns HTTP 200 and a serialized object whose Boxes 5–8 are zero, because the writes went to phantom attributes. A tenant could plausibly read "net GST: 0.00" as a valid result and under-declare/over-claim tax. Under IRAS rules, an incorrect return remains the taxpayer's liability regardless of software defects, and the platform's own DB constraint (`chk_box8_net`) is satisfied by the zeros, so nothing flags the inconsistency.

**Remediation**

1. Rewrite `get_f5_box_amounts()` against `invoicing.document` / `invoicing.document_line`, splitting sales vs purchases on `document_type` (a single query cannot serve both sides of the F5 — output-tax lines and input-tax lines are different boxes).
2. Adopt **one** box-numbering convention matching IRAS/schema across service, serializer, model and PDF; delete the alternative convention.
3. Replace attribute-name string writes with explicit field assignment (`gst_return.box6_output_tax = …`), and add a unit test asserting `GSTReturn.objects.get(...).box6_output_tax == expected` after `generate_f5()` — the current tests never read the persisted value.
4. Align `GSTReturnService` with the model: use `filing_due_date`, drop `label`/`filing_frequency` (or add the columns via a versioned schema change), and constrain `status` transitions to the DB CHECK set.
5. Add a **tie-out test** (the `statement-auditor`/`nav-tieout` discipline): for a fixed fixture of invoices, assert `Box 6 − Box 7 == Box 8`, `Box 4 == Box 1+2+3`, and that Box 6 equals the GL output-tax account balance for the period.

---

### C-02 — Voiding an invoice or payment does not reverse the general ledger

**Severity:** Critical · **Category:** Data integrity · **Confidence:** Verified

**Locations**

- `apps/invoicing/services/document_service.py:520-531` — first `_reverse_journal_entry`: calls `JournalService.void_document_entry()` **twice** (would double-reverse).
- `apps/invoicing/services/document_service.py:809-821` — a **second** `_reverse_journal_entry` defined later in the same class, body `pass  # TODO: Implement in Journal module`. Python keeps the **last** definition, so the double-call version is dead and the no-op is live.
- `apps/invoicing/services/document_service.py:641-647` — `void_document()` sets `status = "VOID"` and calls the no-op reversal. It **never sets `document.void_reason = reason`**, although the parameter is accepted and the DB CHECK `chk_void_reason` requires it (`database_schema.sql:1075-1078`).
- `apps/invoicing/services/document_service.py:618` — void rejects/permits on `["APPROVED","SENT","PAID_PARTIAL"]`; the enum value is `PARTIALLY_PAID`, so a partially-paid invoice can never be voided.
- `apps/banking/services/payment_service.py:307-355` — `PaymentService.void()` sets `is_voided = True` and writes an audit row but creates no reversing journal entry, leaving the bank/cash and AR/AP postings in place.

**Evidence (executed)**

```
### DocumentService._reverse_journal_entry (effective)
placeholder/no-op
### DocumentService._reverse_journal_entry definition count
2
```

**Impact.** After voiding an approved invoice, the GL still carries the receivable and the revenue; only the document flips to `VOID`. Trial balance, P&L, GST output tax and AR ageing all remain overstated indefinitely, and no error is raised — the operation reports success. For a voided payment the cash account and AR/AP remain misstated. This breaks the fundamental accounting invariant that a void is a reversing entry, and it defeats the schema's stated design ("Corrections only via reversal entries"). Because the DOC_STATUS change also violates `chk_void_reason`, the call most likely raises `IntegrityError` on the *document* update and 500s — meaning voids may either fail loudly (best case) or, if the constraint is absent in a drifted database, succeed silently with a wrong ledger.

**Remediation**

1. Delete the duplicate placeholder method; keep exactly one implementation that calls `JournalService.void_document_entry()` once.
2. Persist `void_reason` in `void_document()` and constrain voidable statuses from the enum source of truth (`InvoiceDocument.STATUS_CHOICES`), not a hardcoded list.
3. Apply the same reversal treatment to `PaymentService.void()` (reverse `_create_payment_journal_entry`).
4. Un-skip and implement `tests/integration/test_invoice_operations.py::test_void_creates_reversal_entries` — it currently `pytest.skip`s the exact control that is broken.
5. Add a property test: post → void → assert net effect on every affected account is zero.

---

### C-03 — Tenant isolation context (`SET LOCAL`) is discarded before every view runs

**Severity:** Critical · **Category:** Security / multi-tenant isolation · **Confidence:** Verified (Django source in the pinned version), Reasoned (PostgreSQL semantics)

**Locations**

- `common/middleware/tenant_context.py:118-121` — `SET LOCAL app.current_org_id = %s` and `SET LOCAL app.current_user_id = %s` executed inside `TenantContextMiddleware.__call__`.
- `common/middleware/audit_context.py:35-39` — same pattern for `app.client_ip`, `app.user_agent`, `app.request_path`.
- `database_schema.sql:2385-2411` — policies are `FORCE ROW LEVEL SECURITY` with `USING (org_id = core.current_org_id())`, and `core.current_org_id()` is defined as `NULLIF(current_setting('app.current_org_id', true), '')::UUID`.

**Evidence (verified against installed Django 6.0)**

```
django/core/handlers/base.py:103   self._middleware_chain = handler      # middlewares wrap _get_response
django/core/handlers/base.py:193   wrapped_callback = self.make_view_atomic(callback)   # atomic begins INSIDE the view
django/core/handlers/base.py:346   def make_view_atomic(self, view): ... transaction.atomic(using=alias)(view)
```

`SET LOCAL` is transaction-scoped; with `ATOMIC_REQUESTS: True` the request transaction opens strictly *inside* the view call, after middleware code has run. In autocommit the middleware's `SET LOCAL` is its own statement-scoped transaction and is gone by the time any query executes.

**Why it has not been noticed:** `tests/middleware/test_rls_context.py:85-101` asserts `current_setting('app.current_org_id')` equals the org *after* the middleware returns. Under `pytest.mark.django_db`, pytest-django wraps the whole test in a transaction, so the `SET LOCAL` survives to the assertion. **The test environment manufactures the very transaction the production path lacks** — the test passes precisely because production differs.

**Impact.** Two mutually exclusive outcomes, both unacceptable:
- **Deny-all:** `org_id = NULL` is never true ⇒ every tenant table returns zero rows and every INSERT violates the `WITH CHECK` policy ⇒ total application outage (consistent with the repeated "dashboard shows no data" incident reports in this repo).
- **Leak:** if the application role bypasses RLS (owner without `FORCE`, or a future migration/`GRANT` change), queries run unscoped ⇒ cross-tenant exposure of invoices, ledgers, and GST data (PDPA-relevant personal data breach).

Either way, `audit.event_log.user_id` resolves to NULL for every request-triggered audit row (`database_schema.sql:2233-2270` triggers read `app.current_user_id`), so the "5-year IRAS retention, actor-attributed audit trail" claim is unmet.

**Remediation**

1. Set the session variables inside the transaction boundary: use `connection.cursor()` within `transaction.atomic()` opened by the view, or better, a DRF `BaseAuthentication`/view mixin using `SET LOCAL` after the transaction opens; a clean pattern is a decorator applied to the view function itself so it executes inside `make_view_atomic`'s atomic block.
2. Do not rely on `ATOMIC_REQUESTS` coupling: assert the invariant at runtime (`SELECT current_setting('app.current_org_id', true)` at first query) and fail closed with a 500 + alert if unset.
3. Set `app.current_user_id`, `app.client_ip`, `app.user_agent` in the same transaction.
4. Add a **negative** isolation test that runs with `TransactionTestCase` (no wrapping transaction, mirrors autocommit) and proves a raw `SELECT * FROM invoicing.document` under org A does not return org B rows.
5. Stop trusting `X-Forwarded-For` blindly (`audit_context.py:55-60`) — pin a trusted proxy count or header source, otherwise audit IPs are attacker-controlled.

---

### C-04 — `wrap_response` swallows exceptions inside `ATOMIC_REQUESTS`, committing partial financial state

**Severity:** Critical · **Category:** Data integrity / error handling · **Confidence:** Verified (control flow), Reasoned (Django atomic semantics)

**Location:** `common/views.py:36-88` — the decorator catches `Exception`, logs it, and **returns a 500 `Response`**. Because `DATABASES["default"]["ATOMIC_REQUESTS"] = True` (`settings/base.py:126`), the transaction is owned by Django's view wrapper, which sees a normal return value, not an exception, and therefore **commits**.

**Compounding instance:** `apps/invoicing/services/document_service.py:544-587` — `approve_document()` performs the status transition inside `with transaction.atomic():` and then posts the journal entry **after** that block exits (line 585). If posting fails (missing GL account, closed period, unbalanced lines), the invoice is already `APPROVED` with no journal entry.

**Impact.** Any multi-step financial operation that raises mid-way leaves committed partial state: an approved invoice with no GL postings, a payment with allocations but no journal, a Peppol transmission log without a document update. The client sees "internal error", the operator sees a 500 in logs, and the database silently keeps the half-write. Reconciliation of such states is manual and, given C-02, has no reversal tooling.

**Remediation**

1. Do not catch bare `Exception` in `wrap_response`; let it propagate so the atomic block rolls back. If a friendly message is required, log and re-raise a typed exception handled by `custom_exception_handler`.
2. Explicitly mark safe exceptions as `@transaction.non_atomic_requests` or wrap only the safe read paths.
3. Move `_post_journal_entry()` inside the `atomic()` block in `approve_document()` (and audit every other service for the same post-block-write pattern — `create_received`/`create_made` do it correctly inside a decorator atomic).
4. Add an integration test that forces a failure after the status update and asserts `status == "DRAFT"` afterwards.

---

## 4. 🟠 High Findings

### H-01 — Trial balance and account balance endpoints raise `FieldError` (core reports unavailable)

**Severity:** High · **Category:** Correctness · **Confidence:** Verified (queryset construction executed)

**Location:** `apps/journal/services/journal_service.py:465, 469, 497, 501` — filters use `journal_entry__org_id` and `journal_entry__is_posted`. The FK is `entry` and there is **no `is_posted` field anywhere in the models**.

**Evidence (executed)**

```
FieldError: Cannot resolve keyword 'journal_entry' into field. Choices are: account,
account_id, base_credit, base_debit, created_at, credit, currency, debit, description,
entry, entry_id, exchange_rate, id, line_number, org, org_id, tax_amount, tax_code,
tax_code_id
```

**Impact:** `GET /api/v1/{org}/journal/trial-balance/` (`apps/journal/views.py:191`) and `GET …/journal/accounts/{id}/balance/` (`views.py:227`) return 500 for every request. There is therefore **no working trial balance in the product** (see H-02 for the reporting stub), and `JournalEntrySummaryView` depends on the same helpers.

**Remediation:** use `entry__org_id` / `entry__entry_date`, drop the non-existent `is_posted` predicate (posting is implied by row existence in the immutable-entry design). Add service-level tests that call `get_trial_balance()` directly — the current suite exercises neither method.

---

### H-02 — Financial statements sum transaction currency as if it were SGD; no current-year result; trial balance is an empty stub

**Severity:** High · **Category:** Correctness / Regulatory · **Confidence:** Verified (code), Reasoned (materiality)

**Location:** `apps/reporting/views.py:101-170`

- `_get_profit_loss` and `_get_balance_sheet` aggregate `F("debit") - F("credit")` / `F("credit") - F("debit")` — the **transaction-currency** columns. The schema explicitly provides `base_debit`/`base_credit` "used for all reporting" (`database_schema.sql:875-877`). Any USD/MYR invoice is added directly to SGD totals.
- Equity excludes the current period result: no retained-earnings roll-forward and no `net_profit` component, so **Assets ≠ Liabilities + Equity** for every tenant that has traded in the year. Nothing asserts the balance.
- `report_type == "trial_balance"` returns `{"data": {}}` with HTTP 200 (`views.py:96-98`) — a silent stub for a report the product advertises.

**Impact:** Silent, material misstatement of the balance sheet and P&L for any foreign-currency activity; a balance sheet that cannot balance; and a "trial balance" that returns empty success. For a product whose purpose is producing statutory-quality numbers, this is worse than a crash because it looks like a result.

**Remediation:** switch all reporting aggregates to `base_debit`/`base_credit`; add a `net_profit_for_period` line to equity (or a closing-entry service) and a hard assertion that `assets == liabilities + equity` (raise, do not render, if it fails); implement trial balance on `base_*` with one grouped query, and return `501` rather than `{}` until implemented.

---

### H-03 — `NUMERIC(10,4)` ceilings cap every monetary value at S$999,999.9999

**Severity:** High · **Category:** Data integrity / Scalability · **Confidence:** Reasoned (PostgreSQL numeric semantics — not executed; no DB in sandbox)

**Location:** 80 columns in `database_schema.sql` declared `NUMERIC(10,4)` (e.g. `journal.line.debit` :864, `invoicing.document.total_amount` :1014, `gst.return.box1…box15` :707-731) while the Django models declare `max_digits=19` (`apps/core/models/journal_line.py:33`, `invoice_document.py:69-81`). Money inputs are not range-validated anywhere (`common/decimal_utils.money()` only quantizes).

**Impact:** A single invoice line, payment, journal line or F5 box exceeding **S$999,999.9999** raises `numeric field overflow` at commit. A construction, property or wholesale SMB routinely issues invoices above S$1M, and a quarterly F5 Box 4 (total supplies) above S$1M is a normal outcome for a GST-registered company. The failure surfaces as a 500 at POST time, mid-transaction (and with C-04, possibly after partial commits). The model/DDL divergence (`19` vs `10`) also means DRF happily accepts values the database will reject.

**Remediation:** widen monetary columns to `NUMERIC(19,4)` (or `NUMERIC(20,4)`) in a versioned schema patch and align `max_digits` with the DDL; add a `check_money_range()` validator applied in serializers; add a test inserting `999999.9999 + 0.0001`.

---

### H-04 — GST rate is hardcoded at 9% and rate history is not applied; blocked input tax and reverse charge are not honoured

**Severity:** High · **Category:** Regulatory compliance · **Confidence:** Verified (code), Reasoned (IRAS outcomes)

**Locations**

- `common/decimal_utils.py:288-289` — `GST_RATE = Decimal("0.09")`; `calculate_gst()` and `extract_gst_from_inclusive()` hardcode it.
- `apps/gst/services/calculation_service.py:27` — `DEFAULT_GST_RATE = Decimal("0.09")` applied whenever a caller omits a rate.
- `apps/gst/services/tax_code_service.py:142-152` — `get_tax_code_by_code()` returns `.first()` with **no `effective_from` ordering**, although the schema defines `UNIQUE(org_id, code, effective_from)` and `effective_to` for historical rates (`database_schema.sql:648-652`).
- `apps/gst/services/calculation_service.py:186-215` — F5 aggregation branches on literal code strings (`"SR"`, `"ZR"`, `"ES"`, `"IM"`, `"TX-E33"`) and **ignores** the purpose-built columns `f5_supply_box`, `f5_purchase_box`, `f5_tax_box`, `is_claimable`, `is_reverse_charge`.

**Impact:** Singapore GST was 7% until 2022, 8% in 2023, 9% from 1 Jan 2024. Any back-dated document, credit note against an older period, or amended return is computed at 9% regardless of supply date ⇒ **incorrect output/input tax and an incorrect F5**. Tenants using custom tax codes, blocked input tax (`is_claimable = FALSE`, i.e. IRAS-disallowed claims) or reverse-charge imports will file with input tax they are not entitled to claim — a direct penalty exposure. The schema was correctly designed for all three behaviours; the application layer ignores that design.

**Remediation:** resolve the applicable rate from `(tax_code, document_date)` against `effective_from/effective_to`, snapshot it on the line (already modelled), remove every hardcoded `0.09`, honour `is_claimable` before adding to Box 7, and drive F5 mapping exclusively from `f5_*_box` columns. Add rate-table fixtures for 2022/2023/2024 boundaries.

---

### H-05 — Refresh-token lifecycle is unenforced; logout does not revoke; the frontend's silent refresh cannot work

**Severity:** High · **Category:** Security / Authentication · **Confidence:** Verified

**Locations**

- `apps/core/services/auth_service.py:126-136` — `refresh_access_token()` returns `str(refresh)` — the **same** refresh token, with the original 7-day expiry. `ROTATE_REFRESH_TOKENS = True` / `BLACKLIST_AFTER_ROTATION = True` (`settings/base.py:239-240`) have no effect on this path.
- `settings/base.py` — `rest_framework_simplejwt.token_blacklist` is **not** in `INSTALLED_APPS`, so `token.blacklist()` cannot work; `logout_user()` wraps it in `except Exception: pass` (`auth_service.py:196-204`) — logout silently succeeds while the refresh token stays valid for the full 7 days.
- `apps/web/src/lib/api-client.ts:120-127` — `tryRefreshToken()` POSTs to `/api/v1/auth/refresh/` with **no body and no refresh token**, relying on an HttpOnly cookie the backend never issues (`refresh_view` reads `request.data["refresh"]`, `views.py:106`). Comments in `api-client.ts:5-8` and `apps/web/.env.local:30` assert cookie-based refresh; no cookie code exists anywhere in the backend.

**Impact:** (a) A stolen refresh token is replayable for its whole lifetime with no rotation and no revocation; (b) legitimate users are logged out 15 minutes after sign-in because the silent refresh always 400s; (c) "session expired" redirects mask the defect as normal behaviour. This is simultaneously a security control gap and a functional break of the primary UX path.

**Remediation:** add `token_blacklist` to `INSTALLED_APPS` with its migrations (or implement a signed-cookie refresh properly and drop the JSON refresh token); rotate on refresh and blacklist the predecessor; return the refresh token in an `HttpOnly; Secure; SameSite=Strict` cookie OR send it explicitly from the client — pick one, document it, and test both logout-then-replay and refresh-after-15-min in an E2E test.

---

### H-06 — Production can start with the default insecure `SECRET_KEY`, which is also the JWT signing key

**Severity:** High · **Category:** Security · **Confidence:** Verified (config), Assumed (deployment uses `.env.example` values)

**Location:** `settings/base.py:22` — `SECRET_KEY = config("SECRET_KEY", default="django-insecure-change-in-production")`; `SIMPLE_JWT["SIGNING_KEY"] = SECRET_KEY` (`base.py:236`); `settings/production.py` sets neither and performs no startup assertion. `.env` and `.env.example` both ship `SECRET_KEY=your-secret-key-here-change-in-production`.

**Impact:** With an HS256 JWT signed by a published default key, an attacker can mint a valid access token for any `user_id` — full authentication bypass of every tenant — and forge session/cookie data. Nothing in the deployment path fails closed.

**Remediation:** in `production.py`, `if SECRET_KEY in KNOWN_DEFAULTS or len(SECRET_KEY) < 50: raise ImproperlyConfigured(...)`; rotate to a 64-byte random value from the platform secret store; consider RS256 with a separate signing key so JWT verification does not depend on the cookie secret.

---

### H-07 — Rate limiting is disabled by default in production, contradicting the "SEC-002 complete" claim

**Severity:** High · **Category:** Security · **Confidence:** Verified

**Location:** `settings/base.py:271` — `RATELIMIT_ENABLE = config("RATELIMIT_ENABLE", default=False, cast=bool)`; `production.py` does not set it. Decorators in `apps/core/views/auth.py:24, 53, 55, 95` (`@ratelimit(..., block=True)`) therefore no-op unless the operator remembers the env var. DRF throttling (`anon 20/min`, `user 100/min`) remains, but it is per-IP/per-token and does not bound credential stuffing at the account level.

**Impact:** Login/registration/refresh brute-force protection — the specific control documented as remediated — is off in a default production deployment. Combined with no account lockout or MFA, password spraying is unconstrained.

**Remediation:** default `RATELIMIT_ENABLE = True` in `base.py`, explicitly disable only in `setttings/testing.py`; add per-account lockout with exponential backoff and an audit event on repeated failure; add a test asserting a 429 from the login endpoint in `production` settings.

---

### H-08 — `send-invoicenow` returns fabricated success; the real Peppol service is not wired to the API

**Severity:** High · **Category:** Correctness / Regulatory · **Confidence:** Verified

**Location:** `apps/invoicing/services/document_service.py:737-818` — `send_invoicenow()` returns `{"status": "QUEUED", "message_id": str(uuid4()), …}` with `# TODO: Implement actual Peppol transmission`; `get_invoicenow_status()` returns a fixed `NOT_APPLICABLE` payload. These are the handlers behind `documents/<id>/send-invoicenow/` (`apps/invoicing/urls.py:69-71`, `views.py:575`). A working implementation exists and is **unused by this path**: `apps/peppol/services/transmission_service.py`, `ap_storecove_adapter.py`, `xml_generator_service.py`, `tasks.py`.

**Impact:** A user clicks "Send via InvoiceNow", receives a success payload with a message ID, and no invoice is transmitted. Downstream this becomes a commercial dispute ("we never received the invoice") and a GST documentation risk (no valid delivery evidence). The fabricated `message_id` is persisted nowhere, so even the fiction is not auditable.

**Remediation:** route the endpoint through `TransmissionService.transmit_invoice()` (as `approve_document`'s `_queue_peppol_transmission` already does), return the real `PeppolTransmissionLog` id and status, and delete the placeholder methods. Fail with `409` when Peppol is unconfigured rather than synthesising success.

---

### H-09 — IRAS tax-invoice fields are never populated and the PDF renders a blank invoice number

**Severity:** High · **Category:** Regulatory compliance · **Confidence:** Verified

**Locations**

- `apps/core/models/invoice_document.py:110-113` declares `is_tax_invoice` and `tax_invoice_label`; a repository-wide search finds **no assignment** to either field. `grep -rn "is_tax_invoice" --include=*.py` returns only the model declaration.
- `apps/invoicing/templates/invoicing/invoice_pdf.html:24, 96, 100` renders `{{ document.sequence_number }}`; `InvoiceDocument` inherits `TenantModel`, **not** `SequenceModel`, so the attribute does not exist and Django renders an empty string (`sequence_number` lives on `common/models.py:118`, used by other models).
- The same template references `document.bcrs_deposit_total`, which is also not a model attribute → BCRS totals never print.
- `apps/invoicing/tasks.py:32, 38, 53` and `apps/invoicing/views.py:523` use `document.sequence_number` for the email subject and attachment filename ⇒ emails are titled "Invoice  from …" and PDFs download as `.pdf`.

**Impact:** The generated sales document omits its invoice number — a mandatory element of an IRAS tax invoice under Regulation 11 (together with the words "Tax Invoice", GST registration number, and GST amount). GST input-tax claims by the customer can be disallowed for non-compliant tax invoices, which in practice means the customer withholds payment. Additionally the platform cannot demonstrate, per document, whether it was issued as a tax invoice.

**Remediation:** set `is_tax_invoice = org.gst_registered and document_type in {SALES_INVOICE, SALES_DEBIT_NOTE}` and `tax_invoice_label` at approval; replace `sequence_number` with `document_number` everywhere (template, tasks, views); add a compliance test that renders the PDF and asserts the presence of "TAX INVOICE", GST reg no., invoice number, and GST amount for a GST-registered org, and their absence for a non-registered org.

---

### H-10 — Peppol/PINT-SG validation fails open, and the Schematron rules are never executed

**Severity:** High · **Category:** Regulatory compliance · **Confidence:** Verified

**Location:** `apps/peppol/services/xml_validation_service.py:20-51`

- Schema paths are **relative to the process working directory** (`"apps/peppol/schemas/ubl-Invoice.xsd"`) — they resolve only when the process CWD is `apps/backend`; under a different CWD (systemd, Docker `WORKDIR /app`, Celery worker) they fail.
- On failure, `_load_schemas()` does `except Exception: pass`, leaving `self._invoice_schema = None`, and `_validate_xsd()` then returns `[]` — i.e. **"no errors" means "not validated"**.
- `apps/peppol/schemas/PINT-UBL-validation.sch` exists but no code loads or applies it, so Singapore PINT business rules (mandatory fields, code lists, tax category/rate consistency) are unchecked while the class docstring claims the service validates "UBL 2.1 PINT-SG".
- `_parse_xml()` uses `etree.fromstring()` without a hardened parser (`resolve_entities=False`, `no_network=True`, `huge_tree=False`) — XML entity expansion risk if untrusted XML is ever passed in.

**Impact:** Invalid invoices are transmitted to the Peppol Access Point and rejected downstream (or worse, delivered with incorrect tax categories), with the platform reporting them as valid. For InvoiceNow, which IRAS is phasing in as mandatory for GST-registered businesses, this is a compliance-critical control that currently always passes.

**Remediation:** resolve schema paths with `settings.BASE_DIR`/`importlib.resources`; raise `/health`-visible failure at startup if schemas cannot load (never silently degrade); apply the Schematron via `lxml.isoschematron`; configure `etree.XMLParser(resolve_entities=False, no_network=True)`; add a negative test with a deliberately invalid invoice asserting `valid == False`.

---

### H-11 — Fiscal-year close is unauthenticated by role, unvalidated, and posts nothing

**Severity:** High · **Category:** Correctness / Controls · **Confidence:** Verified

**Location:** `apps/core/views/fiscal.py:63-96` — `FiscalYearCloseView`

- `permission_classes = [IsAuthenticated, IsOrgMember]` — **any** member (including a read-only viewer) can close the year. Every other privileged action in the codebase uses `CanManageOrg` / `CanApproveInvoices` etc.
- Its own docstring says "Requires all periods to be closed first (validation TBD)" — no such validation exists, and closed years do not block posting (only `FiscalPeriod.is_open` is checked at `journal_service.py:207-215`).
- No closing journal entries are created: revenue/expense accounts are never zeroed into retained earnings, so the *next* year's P&L and the balance sheet carry the prior year's activity.
- `year.closed_at = datetime.now()` — naive datetime under `USE_TZ = True`.
- Same pattern for `FiscalPeriodCloseView` (`fiscal.py:99+`).

**Impact:** A well-meaning non-finance user can irreversibly close a year, after which statutory reports are structurally wrong (no retained-earnings roll-forward) and the "period locked" control is illusory. Silent, with no undo path.

**Remediation:** require `CanManageOrg`; refuse to close while open periods or unposted entries exist; generate a `YEAR_END` closing entry (P&L → retained earnings) in the same transaction and link it; use `timezone.now()`; expose a two-step confirmation with an audit event.

---

### H-12 — `file_return()` accepts arbitrary field names from the request body (mass assignment)

**Severity:** High · **Category:** Security (A01/A04) · **Confidence:** Verified

**Location:** `apps/gst/services/return_service.py:238-246`

```python
if boxes:
    for box_name, value in boxes.items():
        if hasattr(gst_return, box_name):
            setattr(gst_return, box_name, value)
```

`GSTReturnFileSerializer` accepts `boxes = serializers.DictField(required=False)` — an unvalidated dict (`apps/gst/serializers.py:251`). `hasattr` filters only on *attribute existence*, so keys such as `org`/`org_id`, `id`, `status`, `filed_by`, `return_type`, `period_start` are accepted and assigned. Values are also unvalidated strings that are then written to `NUMERIC(10,4)` columns.

**Impact:** A user with `can_file_gst` can re-point a return to another organisation, rewrite its period, or set `id`; combined with C-04 any subsequent exception still commits. This is a privilege boundary that a role-based attacker can cross without RLS protection (C-03).

**Remediation:** accept an explicit allow-list of the 15 declared box fields with `Decimal` validation (a DRF serializer per box), ignore everything else with a 400 rather than `hasattr`; recompute derived boxes (4 and 8) server-side and reject client-supplied values for them.

---

### H-13 — Container image builds are neither reproducible nor verified (supply chain)

**Severity:** High · **Category:** Security (A03 Software & Data Supply Chain) · **Confidence:** Verified (Dockerfile text), Assumed (used for deployment)

**Location:** `apps/backend/Dockerfile`

- `pip install -U django djangorestframework djangorestframework-simplejwt …` — **unpinned**, contradicting the pinned `pyproject.toml` (`django==6.0.2`, …). Every build resolves "latest", so a major-version change can land without review.
- `wget https://github.com/nordeim/HF-Space/raw/refs/heads/main/bun|uv|uvx` then `chmod a+x` — binaries fetched from a **personal GitHub repository at a moving branch, as root, with no checksum or signature verification**.
- Installs `postgresql`, `redis-server`, `sudo`, `build-essential`, `django-debug-toolbar`, `pytest`, `faker` into the runtime image; `echo "user ALL=(ALL) NOPASSWD: ALL"` grants passwordless root to the app user.
- `CMD` is commented out; the image has no defined entrypoint.

**Impact:** Non-reproducible builds (a financial system must be able to state exactly what it runs), a live supply-chain injection surface (moving-branch binaries), a wide CVE surface from unused system packages, and privilege escalation from any app-level RCE.

**Remediation:** build from `pip install --require-hashes -r requirements.txt` generated from the lock; multi-stage build (build tools and DB servers out of the runtime stage); pin third-party binaries by commit SHA **and** verify SHA-256; drop `sudo` and NOPASSWD; set a non-root `USER` (already present) **without** sudo; define `CMD ["gunicorn", …]`.

---

### H-14 — GST filing/filing-status workflow cannot persist (status vocabulary mismatch) — *see also C-01(g)*

**Severity:** High · **Category:** Correctness · **Confidence:** Verified

**Location:** `apps/gst/services/return_service.py:282` (`status = "AMENDING"`), `:320` (`status = "PAID"`), `:246-256` (`file_return` writes `filing_reference`), `:288-296` (payment fields). Model/schema allow `DRAFT, COMPUTED, REVIEWED, FILED, AMENDED` and provide `iras_confirmation`, not `filing_reference`; there are **no** `paid_at`/`payment_amount`/`payment_reference` columns anywhere in `gst.return`.

**Impact:** Filing a return raises `IntegrityError` (constraint violation) or `AttributeError`, so the workflow `DRAFT → FILED → PAID → AMENDED` cannot be executed or audited. GST payment tracking (`pay_return`) writes to phantom attributes and silently discards the payment record — meaning the platform cannot evidence that GST was paid, which is the first question in any IRAS enquiry.

**Remediation:** either extend the schema (add `filing_reference`, `paid_at`, `payment_amount`, `payment_reference`, `amendment_reason`, and allow the transition set) or reduce the model to the existing columns and implement payment as a `PAYMENT_MADE` journal entry against a GST payable account (the accounting-correct approach). Add a state-machine test over every transition.

---

## 5. 🟡 Medium Findings

### M-01 — Model/schema drift is unguarded and already materialised
**Location:** all `apps/core/models/*.py` (`managed = False`, `db_table = 'invoicing"."document'` at `invoice_document.py:161`, `'journal"."line'`, `'gst"."return'`) · `pyproject.toml` (`MIGRATE = False`) · no CI schema check
**Evidence:** `manage.py check` passes while three separate table/column mismatches exist (C-01a, C-01d, H-01). Table names are produced by embedding quote characters in `db_table`, a fragile hack that depends on the backend's quoting behaviour.
**Impact:** The schema is the source of truth by design, but nothing verifies the mirror. Every drift becomes a runtime `UndefinedColumn`/`FieldError` deep in a financial transaction.
**Remediation:** add a CI test that introspects `information_schema.columns` and asserts every `(db_table, db_column)` declared by each model exists with a compatible type; or generate models from the schema. Replace the quoting hack with a proper `db_table = 'invoicing.document'` + a custom `quote_name`-aware base manager.
**Confidence:** Verified.

### M-02 — "Immutable" journal is not enforced by privileges or triggers
**Location:** `database_schema.sql:3090` (`GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES … TO ledgersg_app`), vs `:2233+` (audit triggers only) and the header claim "Immutable audit log … Double-entry integrity enforced via triggers + constraints"
**Impact:** The application role can `UPDATE`/`DELETE` posted `journal.entry`/`journal.line` rows. The only immutability guarantee is the absence of such code paths — a future `.save()` or `.delete()` (Django `QuerySet.delete()` is easy to reach) silently rewrites history, defeating the audit trail's purpose. The balance trigger validates at commit but does not prevent deletion of a whole entry.
**Remediation:** `REVOKE UPDATE, DELETE ON journal.entry, journal.line FROM ledgersg_app` and add `CREATE TRIGGER … BEFORE UPDATE OR DELETE … RAISE EXCEPTION`; state the reversal-only workflow in a CHECK/trigger so it cannot be bypassed by any role.
**Confidence:** Verified.

### M-03 — Audit trail gaps: not covered by RLS, double-written, not tamper-evident, over-collects
**Location:** `database_schema.sql:2360-2372` (RLS table list omits `audit.event_log`) · app-level duplicates at `payment_service.py:99-112`, `reconciliation_service.py:233-248`, `document_service.py` etc. · triggers `:2233-2270`
**Impact:** (a) `audit.event_log` has `org_id` but no policy — any query path that reaches it is unscoped; (b) every state change is written twice (trigger + service), producing divergent records, and the service rows lack `ip_address`/`user_agent` (which are themselves unreliable — set outside the transaction, see C-03); (c) `old_data`/`new_data` JSONB copies full payloads including customer names/amounts with no retention policy (PDPA data-minimisation); (d) no hash chaining, so a privileged actor can rewrite history undetectably.
**Remediation:** add the table to the RLS loop; choose trigger **or** application writes (not both); record only changed-field diffs; add `prev_hash`/`row_hash` chaining with a periodic anchor; document retention and purge.
**Confidence:** Verified (a,b,c), Reasoned (d).

### M-04 — Document numbers are allocated outside the transaction → gaps and races
**Location:** `apps/invoicing/services/document_service.py:171` (`_get_next_document_number` before `with transaction.atomic()`), `journal_service.py` (`_get_next_entry_number` inside atomic — inconsistent), `core.get_next_document_number()` (`database_schema.sql:1676-1706`, `FOR UPDATE` row lock)
**Impact:** Because the sequence call commits in its own transaction (autocommit) or at latest before the document insert, any later failure consumes a number: invoice numbers are **not** gap-free, contrary to the schema comment "Gap-free sequential number per org". Concurrent creates can also reorder. Auditors treat unexplained gaps in invoice/credit-note sequences as a red flag.
**Remediation:** call the sequence function **inside** the same `transaction.atomic()` as the insert (locks are released at commit, so this is safe and gap-free), and add a test that forces an insert failure and asserts no number is consumed.
**Confidence:** Verified (code order), Reasoned (gap outcome).

### M-05 — Line-level modelling gaps: discounts ignored, tax-inclusive unsupported, rounding policy undefined
**Location:** `document_service.py:255-296` (`add_line`) — `discount_pct`/`discount_amount`/`is_tax_inclusive` exist in the schema (`database_schema.sql:1105-1112`) but are never applied; `_recalculate_totals` (line 488-504) sums `line_amount` only
**Impact:** A line with a discount is posted at gross value; a tax-inclusive price is treated as exclusive (9% overstated), and `document.total_discount` stays 0. GST is computed on a base rounded to 2 dp (`amount`) while `line_amount` is stored unrounded, so `gst_amount` and `line_amount` can disagree with the invoice-level rounding IRAS expects when totals are aggregated.
**Remediation:** implement discount and inclusive-price branches (schema already has the columns and the GST service has `calculate_tax_inclusive_gst`), define and document the rounding policy (per-line vs per-invoice, per IRAS guidance), and add table-driven tests for both.
**Confidence:** Verified.

### M-06 — Duplicated implementations; ~2,000 lines of tests exercise dead code
**Location:** `apps/reporting/services/dashboard_service.py` (462 lines) is referenced **only** by `apps/reporting/tests/test_dashboard_cache.py` (519) and `test_dashboard_service_tdd.py` (1,463); the live path is `apps/core/services/dashboard_service.py` (399) used by `apps/core/views/dashboard.py:13`. Same pattern for Peppol (H-08) and invoice reversal (C-02).
**Impact:** The test suite's reported dashboard coverage measures a module that no user can reach, while the reachable dashboard is materially weaker (M-07). This is how "we have 1,982 lines of dashboard tests" coexists with "the dashboard shows wrong GST".
**Remediation:** delete the dead service and its tests (or point the view at it after fixing M-07); add a CI check for unreferenced modules; require that every service module be reachable from a URL or a task.
**Confidence:** Verified.

### M-07 — Dashboard "GST payable" and "cash position" are invoice-derived approximations
**Location:** `apps/core/services/dashboard_service.py:78-140`
**Evidence:** `# For MVP: Calculate from invoices if GST accounts not available` / `# For MVP: Calculate from invoices as proxy`. The GST query sums `gst_total` for `status__in=['SENT','PARTIALLY_PAID','PAID','OVERDUE']` with **no period filter** and omits `APPROVED`, credit notes and tax-code distinctions; `_get_cash_metrics` derives "cash" from PAID invoices.
**Impact:** A dashboard labelled "GST liability" and "Cash position" shows figures that are neither period-correct nor cash. For a tax-facing KPI this is actively misleading; SMB users make payment decisions from it.
**Remediation:** compute GST liability from the GL (`gst` output/input tax accounts, period-scoped) and cash from `banking.bank_account` balances + unreconciled items; label anything approximate explicitly; remove the "MVP" paths.
**Confidence:** Verified.

### M-08 — Status and type vocabularies diverge across modules
**Location:** `'PAID_PARTIAL'` (`calculation_service.py:237`, `document_service.py:618,621`) vs `'PARTIALLY_PAID'` (schema enum, model choices); `DOCUMENT_TYPES` maps `INVOICE`→`SALES_INVOICE` (`document_service.py:31-41`) while the model uses `SALES_INVOICE`; `ENTRY_TYPE_TO_SOURCE_TYPE` legacy aliases (`journal_service.py:46-56`)
**Impact:** Each divergent literal is a latent `IntegrityError`/`FieldError`. The codebase has already been bitten twice (C-01b, C-02). Legacy alias maps keep two vocabularies alive indefinitely.
**Remediation:** derive status constants from a single module (e.g. `apps/core/constants.py` re-exported from model `TextChoices`), remove the compatibility maps, and add a test that every string literal used in a query appears in the enum.
**Confidence:** Verified.

### M-09 — "Reconciliation" does not reconcile
**Location:** `apps/banking/services/reconciliation_service.py:261-330` (`reconcile`), `:377-424` (`suggest_matches`)
**Evidence:** fixed `tolerance = Decimal("1.00")`; comparison is `abs(txn.amount - payment.amount)` — **sign-agnostic**, so an outflow can be matched to an inflow payment of the same magnitude; no statement end-balance or book-balance comparison exists anywhere; no cleared/`reconciled_balance` concept; `suggest_matches` loads every unreconciled payment for the account with no bound.
**Impact:** The cash control that auditors rely on (bank statement vs cash book, ending balance agrees) is absent. A $1,000 discrepancy is accepted silently. This is the single most important monthly control for an SMB.
**Remediation:** add a statement import with period end balance, compute `book_balance + unreconciled_txns == statement_balance`, enforce sign/direction matching, tolerance from org settings, and cap candidate suggestion queries (filter by date window + amount range).
**Confidence:** Verified.

### M-10 — CSV statement import is unbounded and silently drops duplicates
**Location:** `apps/banking/services/reconciliation_service.py:94-259`
**Evidence:** `csv_file.read().decode("utf-8")` loads the whole upload into memory; no size/row cap; duplicate detection is `(bank_account, transaction_date, amount, description[:500])` and matches are counted as `skipped` **without an error entry**, so two legitimate identical same-day transactions (common for Grab/food receipts) silently disappear from the ledger.
**Impact:** Understated bank activity with no user-visible warning; memory exhaustion on a large upload; and the import's own idempotency depends on a heuristic that produces false positives.
**Remediation:** stream with `io.TextIOWrapper` and enforce a max size; dedupe on a real bank reference (`external_id`) with a documented fallback; report every skipped row with its reason; return the batch for review before commit.
**Confidence:** Verified.

### M-11 — Content-Security-Policy posture is effectively absent in the default build
**Location:** `settings/base.py:344` (`CONTENT_SECURITY_POLICY = None`, report-only only) · `apps/web/next.config.ts:55-70` (headers returned only when `NEXT_OUTPUT_MODE != "export"`; default is `"export"`) · `apps/web/src/middleware.ts:17-22` (`script-src` includes `'unsafe-eval'` **and** `'unsafe-inline'`)
**Impact:** The backend CSP protects API responses (an XSS-irrelevant surface) while the actual browser app ships **no** security headers in its default static-export deployment, and the server-mode policy permits inline/eval — negating most XSS mitigation for a financial UI. The repo's "SEC-003: 100% security score" claim is not supported by this configuration.
**Remediation:** enforce (not report-only) on the app origin; move static-export header delivery to the CDN/proxy config (checked in, versioned); use nonce-based `script-src` with `strict-dynamic` and drop `unsafe-eval` for production builds; add `frame-ancestors`, `object-src 'none'`, `base-uri 'self'` at the edge.
**Confidence:** Verified.

### M-12 — Secret hygiene: `.env` tracked, JWT committed, vendor passwords in schema
**Location:** `apps/backend/.env` and `apps/web/.env.local` are **tracked** while the root `.gitignore` has no `.env` entry; `start_apps.sh:224` embeds a signed access token (expired 2026-03-08 but valid when committed, containing `user_id` and `default_org_id`); `database_schema.sql:3078,3081` create roles with `PASSWORD 'CHANGE_ME_IN_PRODUCTION'`
**Impact:** Current values are placeholders, so no live credential leaked — but the *process* is unsafe: the next developer who fills in a real key commits it, and the presence of a real JWT proves tokens have been pasted into scripts. Nothing prevents pushing production secrets.
**Remediation:** add `.env*` (with `!.env.example`) to `.gitignore`, `git rm --cached` the tracked files, purge history for `start_apps.sh`, add a pre-commit secret scanner (gitleaks/trufflehog) and a CI job; require explicit password provisioning at deploy time instead of a schema default.
**Confidence:** Verified.

### M-13 — FX gain/loss is modelled and documented but never computed
**Location:** `apps/banking/services/payment_service.py:104` (`fx_gain_loss=Decimal("0.0000")` on every payment), `:400-408` (allocation converts at the *payment* rate only), schema `banking.payment.fx_gain_loss` (`database_schema.sql:1327`)
**Impact:** The status docs claim "Multi-currency payment support with FX gain/loss tracking". In practice a USD invoice settled at a different rate produces no FX gain/loss posting, so the P&L omits a real (and auditable) item, and AR/AP clearing does not net to zero.
**Remediation:** on allocation, compare document rate vs settlement rate and post the difference to an FX gain/loss account as part of the payment entry; add period-end revaluation for open foreign balances; test with two rates.
**Confidence:** Verified.

### M-14 — Session/authorisation staleness and details
**Location:** `common/middleware/tenant_context.py:230-260` (membership cached 5 min), `:100-104` (no `is_active` check on token-derived user), `apps/core/services/auth_service.py:112` (naive `datetime.now()`, hardcoded 15-minute expiry), `:92-101` (`default_org_id` claim frozen at login)
**Impact:** A revoked member retains org access for up to 5 minutes (the guard caches `is_member=True`), which is material for a bookkeeper removed for cause. The middleware performs its own JWT decode and DB lookup, sets `request.user`/`request.org_id`, and never checks `is_active` — DRF's authenticator will still reject an inactive user at the view, so this is not currently exploitable, but it establishes a **second, weaker authentication path** that any future view relying on `request.org_id` (or a permission class that omits `IsAuthenticated`) would trust. `access_expires` is a naive timestamp that the client may misread, and the `default_org_id` claim goes stale after `set-default-org` until re-login.
**Remediation:** invalidate the membership cache on membership changes; check `is_active` in `_get_authenticated_user`; read `SIMPLE_JWT["ACCESS_TOKEN_LIFETIME"]` instead of hardcoding and use `timezone.now()`; derive the current org from the request, not the token claim, or refresh the token on switch.
**Confidence:** Verified.

### M-15 — Missing account lifecycle controls
**Location:** `apps/core/views/auth.py` (no password-reset, no email-verification, no MFA endpoints) · `auth_service.change_password()` (`:139-152`) does not invalidate existing JWTs
**Impact:** For a system that files tax returns, absence of MFA (or at least TOTP for `can_file_gst`/`can_approve_invoices` roles), verified email (used for invoice delivery), and self-service reset (forcing weak shared passwords in practice) is a control gap; and changing a password after a suspected compromise leaves the attacker's tokens valid for up to 7 days.
**Remediation:** implement reset (single-use, expiring token) and email verification; add TOTP MFA for privileged roles; on password change, blacklist refresh tokens (requires H-05) and set `CHECK_REVOKE_TOKEN`/`USER_AUTHENTICATION_RULE`.
**Confidence:** Verified (absence), Reasoned (risk).

### M-16 — Peppol credentials at rest and SSRF via configurable Access Point URL
**Location:** `apps/peppol/models.py:179-190` (`access_point_api_key = CharField`, plaintext), `:173` (`access_point_api_url = URLField`, tenant-editable), `apps/peppol/services/ap_storecove_adapter.py:46-60` (sends `Authorization: Bearer <key>` to that URL)
**Impact:** (a) API keys for the certified Access Point are recoverable by anyone with DB read access or a backup; (b) a tenant admin can point `access_point_api_url` at an internal address (e.g. `http://169.254.169.254/`, `http://redis:6379`) and the worker will POST invoice XML plus the bearer key there — server-side request forgery with credential exfiltration to a tenant-chosen host; (c) no idempotency key on submissions, so a retry after timeout can duplicate an invoice on the Peppol network.
**Remediation:** encrypt the key at rest (KMS/`pgcrypto` with a managed key) and never return it; allow-list Access Point hosts (per provider) rather than free-form URLs; block private/link-local ranges at the HTTP client; send an `Idempotency-Key` derived from `xml_payload_hash` (already stored) and suppress duplicates.
**Confidence:** Verified (a,b), Reasoned (c).

---

## 6. 🟢 Low Findings

| ID | Location | Finding | Remediation | Confidence |
|---|---|---|---|---|
| **L-01** | repo root; `apps/web/dist/` (54 files), `GEMINI.bak`, `GEMINI.temp`, `Dockerfile.bak`, `pyproject.toml.bak{,2}`, `shell.tsx.bak`, `Agent-Browser-howto.md` (symlink to `/home/pete/.openclaw/…`) | 277 markdown documents at root, committed build output (`dist/`), `.bak`/`.temp` files, and a symlink pointing at a developer's home directory (broken for everyone else). `.git` is 114 MB. | Move docs into `docs/` (one README + `docs/adr/`), untrack `dist/`, delete `.bak`/`.temp`, replace the symlink with a real file, add `dist/`, `*.bak`, `*.temp` to `.gitignore`. | Verified |
| **L-02** | `pytest.ini` vs `pyproject.toml:105-114` | Two pytest configs; `pytest.ini` wins and pytest prints `WARNING: ignoring pytest config in pyproject.toml`. Marker/`addopts` drift between them is invisible. | Keep one; delete the other. | Verified |
| **L-03** | `tests/test_db_conn.py` | A connectivity scratch script is collected as a test and fails collection (`ModuleNotFoundError: psycopg`) — the only collection error in 467 tests. | Move to `scripts/` or `tests/manual/`, or guard with `pytest.importorskip`. | Verified |
| **L-04** | `apps/peppol/services/xml_validation_service.py:36,44`; `apps/core/services/auth_service.py:203`; `common/middleware/audit_context.py:42-44` | 12 `except …: pass` / silent-failure sites; three of them (or four counting C-03's RLS failure handler) mask security-relevant failures. | Log at `warning` with a stable event name; return a typed failure rather than empty success. | Verified |
| **L-05** | `apps/core/services/auth_service.py:112,132`; `apps/core/views/fiscal.py:85` | `datetime.now()` used under `USE_TZ = True` → naive datetimes, DRF `RuntimeWarning`, and timezone-dependent behaviour. | Use `django.utils.timezone.now()`. | Verified |
| **L-06** | `apps/gst/services/return_service.py:328-374` (`get_f5_json` unused), `common/exceptions.py:164-173` (dead `ValidationError` branch), `common/decimal_utils.py:230-330` (`Money` class unused), `journal_service.py:46-56` (legacy alias map) | Dead code and duplicate money abstractions (`py-moneyed` is a declared but unused dependency). | Delete; one money type only. | Verified |
| **L-07** | `apps/web/src/hooks/use-invoices.ts:298` | Reads `localStorage.getItem("accessToken")` — never written anywhere; produces `Authorization: Bearer null`. | Use the typed `api` client exclusively; ban direct `fetch` in hooks via ESLint rule. | Verified |
| **L-08** | `apps/web/package.json:20-46` | Test tooling (`@playwright/test`, `vitest`, `jsdom`, `@testing-library/*`, `@axe-core/playwright`) and `serve` are in `dependencies`, so they ship in the production install; `serve` (a static dev server) is the documented production host. | Move to `devDependencies`; serve statically from a CDN/reverse proxy. | Verified |
| **L-09** | `apps/web/next.config.ts:24-27` | Default build is a static export into `dist/`, which Next.js documents as incompatible with `headers()` — so the "security headers" block is inert in the default configuration. | Choose one deployment mode; if static, commit the proxy/CDN header config. | Verified |
| **L-10** | `settings/base.py:404-418` | Logging uses `%`-less f-strings and the `ledgersg` logger is pinned at `DEBUG` in base settings (inherited by production). `structlog` is a declared dependency but unused. | Use structured logging with a request/tenant/trace id; `INFO` in production. | Verified |

---

## 7. ⚪ Informational

| ID | Recommendation |
|---|---|
| **I-01** | **Make the schema-model contract executable.** Add a CI job that reflects `information_schema` and asserts every model's table/column/type exists. This single gate would have prevented C-01, H-01, and H-14. |
| **I-02** | **Add an accounting-invariant test suite as a permanent gate** (the `statement-auditor` discipline applied in code): after each workflow — post → settle → void → credit-note — assert (i) every journal entry balances, (ii) Σ debits == Σ credits per period, (iii) Box 6 − Box 7 == Box 8 for the period's F5, (iv) GL GST control accounts tie to the F5 boxes, (v) AR/AP subledger ties to GL control accounts, (vi) Assets == Liabilities + Equity. These are cheap, deterministic, and would have caught five Critical/High findings. |
| **I-03** | **Validate the F5 box model against the current IRAS e-Filing specification before claiming compliance.** The schema models Boxes 10, 11, 12 and 14 as `NUMERIC` amounts, whereas on the current F5 several of these are declaration/indicator fields, and Box 15 has no F5 counterpart. External references confirm Boxes 5–8 semantics used above. Tag the mapping as `verified` only after checking against IRAS's published e-Filing technical spec (Unverified in this environment). |
| **I-04** | **Use an explicit state machine** for `invoicing.document` and `gst.return` (e.g. `django-fsm` or a table-driven transition map) instead of scattered `if status not in [...]` lists (M-08, C-02). |
| **I-05** | **Precision strategy:** consider integer minor units or `NUMERIC(19,4)` plus a currency-aware `Money` (the declared-but-unused `py-moneyed` dependency) so rounding policy is explicit and per-currency (SGD 2 dp, JPY 0 dp). |
| **I-06** | **Frontend framework currency:** Next.js 16 renames `middleware.ts` to `proxy.ts`. `apps/web/src/middleware.ts` should be migrated and the behaviour verified against the 16.1 runtime (Reasoned — verify against the Next 16 docs before acting). |
| **I-07** | **Documentation as a single source of truth:** the 277 root-level markdown files include mutually contradictory status reports. Consolidate to a README + `docs/adr/*` and archive historical remediation reports under `docs/archive/`; delete claims that the code does not support (Section 8). |
| **I-08** | **Dependency health in CI:** add `pip-audit`, `npm audit --omit=dev`, and an SBOM (CycloneDX) to the pipeline; CVE status for the pinned set was **not** verified in this audit (no advisory data available offline). |

---

## 8. Regulatory & Compliance Matrix

Legend: ❌ not met · ⚠️ partially met / unverified · ✅ met (verified in code)

### 8.1 IRAS GST — F5 return and tax invoices

| Requirement | Status | Evidence |
|---|---|---|
| Compute F5 Boxes 1–8 per IRAS definition (Box 5 taxable purchases, Box 6 output tax, Box 7 input tax, Box 8 = 6 − 7) | ❌ | Code uses a contradictory numbering (C-01c) and queries non-existent tables (C-01a) |
| Produce a F5 for a period from posted transactions | ❌ | `generate_f5()` writes to non-existent attributes; API serializers raise (C-01d,f) |
| Persist and evidence filing (reference, date, actor) | ❌ | `filing_reference`/`paid_*` have no columns; status vocabulary rejects `AMENDING`/`PAID` (H-14) |
| Amend a filed return (F7) | ❌ | `amend_return()` violates the DB CHECK (H-14) |
| Apply the GST rate effective on the supply date (7% → 8% → 9%) | ❌ | Hardcoded 9%; `.first()` on a rate-history table (H-04) |
| Exclude blocked input tax (`is_claimable = FALSE`) from Box 7 | ❌ | `is_claimable` never consulted (H-04) |
| Handle reverse-charge imported services (Box 14 / output+input pair) | ❌ | `is_reverse_charge` modelled but unused; no posting path (H-04, C-01c) |
| Compute GST per line and round consistently | ⚠️ | Per-line 2 dp rounding works (`calculate_line_gst` verified: 100.005 × 9% → 9.00); invoice-level rounding policy undocumented, discounts/inclusive pricing not applied (M-05) |
| BCRS deposits excluded from GST and from F5 | ⚠️ | `is_bcrs_deposit` is honoured in `calculate_line_gst` and excluded from the F5 aggregation, but the PDF's BCRS total renders empty (H-09) and BCRS never reaches the GL as a separate line |
| Issue tax invoices stating "Tax Invoice", GST reg no., invoice number, GST amount (Regulation 11) | ❌ | `is_tax_invoice`/`tax_invoice_label` never set; invoice number renders blank in the PDF (H-09) |
| Produce a GST F5/F7-compatible export for IRAS e-Filing | ❌ | No export path exists |
| 5-year record retention with immutable audit trail | ⚠️ | Append-only grants on `audit.event_log` exist and are correct; but actor identity is NULL (C-03), no RLS on the table, no tamper evidence, no retention/purge job (M-03) |

### 8.2 InvoiceNow / Peppol (PINT-SG)

| Requirement | Status | Evidence |
|---|---|---|
| Generate UBL 2.1 Invoice/CreditNote | ✅ | `xml_generator_service.py` produces namespace-correct UBL (tax category map `SR→S`, `ZR→Z`, `ES→E` is EN16931-correct) |
| Validate against UBL XSD | ⚠️ | Implemented but **fails open** and resolves paths relative to CWD (H-10) |
| Validate against PINT-SG Schematron rules | ❌ | `PINT-UBL-validation.sch` present, never loaded (H-10) |
| Transmit and track delivery via a certified Access Point | ⚠️ | Real adapter + retry service exist (`transmission_service.py`, `ap_storecove_adapter.py`) but the API endpoint returns fabricated success (H-08); no idempotency key (M-16c) |
| Persist transmission evidence (message id, payload hash, response) | ⚠️ | `gst.peppol_transmission_log` is well designed; unused by the API path |

### 8.3 Data protection & access control (PDPA-adjacent)

| Requirement | Status | Evidence |
|---|---|---|
| Tenant isolation at the database level | ❌ | RLS policies exist but session context is never active (C-03) |
| Role-based authorisation for privileged actions | ⚠️ | Most endpoints use `Can*` permissions; **fiscal-year/period close** and Peppol settings use only `IsOrgMember` (H-11, M-16) |
| Least-privilege DB role | ❌ | `ledgersg_app` has `UPDATE`/`DELETE` on the immutable ledger (M-02) |
| Secrets not in source control | ⚠️ | No live secrets found; `.env` tracked and a JWT committed (M-12) |
| Data minimisation in logs/audit | ⚠️ | Audit JSONB copies full payloads including customer names (M-03) |
| Breach-relevant controls (MFA, session revocation, lockout) | ❌ | No MFA, logout does not revoke, rate limiting off by default (H-05, H-07, M-15) |
| Cross-border/third-party data flow documented (Access Point, email) | ⚠️ | Access Point integration undocumented from a data-flow perspective; invoices sent to `api.storecove.com` by default (`ap_storecove_adapter.py:45`) |

### 8.4 Financial reporting quality

| Requirement | Status | Evidence |
|---|---|---|
| Double-entry integrity (debits == credits) | ✅ | Service-level check (`journal_service.py:212-215`) plus deferred DB trigger (`database_schema.sql:1719-1770`) |
| Immutable posted entries, corrections by reversal | ❌ | Void reversal is a no-op (C-02); privileges allow UPDATE/DELETE (M-02) |
| Trial balance | ❌ | Endpoint crashes (H-01); reporting returns `{}` (H-02) |
| Balance sheet balances | ❌ | No retained-earnings roll-forward, no assertion, mixed currency (H-02) |
| Period close / year-end close with closing entries | ❌ | Close only flips a boolean, any member may do it (H-11) |
| Audit-grade reconciliation to bank statements | ❌ | No statement balance reconciliation (M-09) |

---

## 9. Claims vs. Reality (documentation integrity)

This is itself a finding: for a compliance-sensitive product, documentation that overstates capability is a safety issue — an operator may rely on a control that does not exist.

| Document | Claim | Verified reality |
|---|---|---|
| `AGENTS.md` / `Current_Project_Status.md` | "production-grade … IRAS 2026 compliance" | F5 pipeline non-functional (C-01), no tax invoices (H-09) |
| `AUTHENTICATION_REMEDIATION_COMPLETE.md` | 3-layer defence-in-depth auth complete | Client-side guards exist; but logout/refresh broken (H-05) and the **server-side RLS layer is ineffective** (C-03) |
| `InvoiceNow_Phase3-4_Completion_Summary.md` | InvoiceNow transmission complete | API endpoint returns fabricated success (H-08); validation fails open (H-10) |
| `CORS_FIX_*` / `BACKEND_REMEDIATION_FINAL_REPORT.md` | "100% security score" | Rate limiting off by default (H-07), CSP report-only/inert (M-11), default SECRET_KEY permitted (H-06) |
| `TEST_SUITE_COMPLETION_REPORT.md` | comprehensive suite | 467 collected but the void-reversal test is skipped (C-02), dashboard tests target dead code (M-06), and the RLS test is masked by the test transaction (C-03) |
| `RLS_FIX_VALIDATION_REPORT.md` | RLS validated | RLS validation test cannot detect the production failure mode (C-03) |
| `schema_model_gap_analysis.json` | gap analysis exists | Gaps documented but unresolved and not gated in CI (M-01) |

---

## 10. Security Review by OWASP 2025 Category

| Category | Verdict | Notes |
|---|---|---|
| **A01 Broken Access Control** | 🔴 Failing | C-03 (RLS ineffective), H-11 (unprivileged fiscal close), H-12 (mass assignment), M-16 (SSRF via AP URL) |
| **A02 Security Misconfiguration** | 🟠 Weak | H-06 (default secret accepted), H-07 (rate limiting off), M-11 (CSP inert), `DEBUG` default False (good) |
| **A03 Supply Chain** | 🟠 Weak | H-13 (unpinned pip + unsigned binaries); Python deps otherwise pinned; CVE status unverified |
| **A04 Cryptographic Failures** | 🟡 Partial | HS256 with shared secret (H-06); Peppol API key plaintext at rest (M-16); passwords use Django's default (PBKDF2/Argon2 available — `argon2-cffi` is a declared dep but `PASSWORD_HASHERS` is not configured to use Argon2) |
| **A05 Injection** | ✅ Strong | No raw-SQL f-strings found (grep clean); all queries parameterised; ORM used throughout; XML parser hardening missing but input is generated internally (H-10) |
| **A06 Insecure Design** | 🔴 Failing | Trusts client-supplied F5 boxes, single-step destructive fiscal close, no statement-balance reconciliation |
| **A07 Authentication Failures** | 🟠 Weak | H-05 (no rotation/revocation), H-07, M-15 (no MFA/reset/verification), no account lockout |
| **A08 Integrity Failures** | 🔴 Failing | C-02 (void without reversal), C-04 (partial commit), M-02 (ledger UPDATE/DELETE permitted) |
| **A09 Logging & Monitoring** | 🟡 Partial | Structured logging dependency unused; audit actor NULL (C-03); no correlation ids; Sentry optional and off by default |
| **A10 Exceptional Conditions** | 🔴 Failing | C-04 (exception swallowed inside atomic), 4 silent fail-open paths (L-04), XML validation fails open (H-10) |

**Positive security observations** (worth preserving): no SQL injection surface, parameterised queries throughout, access tokens kept in memory rather than `localStorage`, CORS explicitly allow-listed in production, `X-Frame-Options: DENY`, `SECURE_CONTENT_TYPE_NOSNIFF`, HSTS/secure-cookie configuration present in `production.py`, password validators at 12 characters with common-password and numeric checks, verbose error suppression at the API boundary, and a genuinely well-designed append-only audit table.

---

## 11. Test & Verification Assessment

**Coverage shape (static analysis):** 467 tests across 42 modules. Distribution is heavily weighted toward services (`test_payment_service.py` 645 lines, `test_dashboard_service_tdd.py` 1,463 lines) with thin coverage of the highest-risk paths.

| Risk area | Test status | Comment |
|---|---|---|
| GST F5 generation | ❌ no test references `GSTReturnService.generate_f5` | The broken control is entirely untested |
| Void reversal | ⚠️ `pytest.skip("Service layer not implemented yet")` | Explicitly skipped (`test_invoice_operations.py:99`) |
| Trial balance / account balance | ❌ none | Both crash (H-01) |
| Multi-tenancy (RLS) | ⚠️ masked | Tests pass because pytest-django wraps each test in a transaction (C-03) |
| Rate limiting | ⚠️ | `tests/security/test_rate_limiting.py` exists, but `RATELIMIT_ENABLE` is False by default, so it is likely asserting the disabled state |
| Peppol XML validation | ⚠️ unit tests exist (pass in isolation) | They exercise the service but cannot catch fail-open, since a `None` schema returns `[]` |
| Decimal safety | ✅ 42 tests pass, meaningful assertions | `common/tests/test_decimal_utils.py` is genuinely good |
| Invoice/Payment/Reconciliation services | ✅ substantial test volume | Behavioural, reasonable quality |

**Structural test problems**
1. **No isolation of the failure modes that matter.** No test asserts *persisted* state after GST generation, no test asserts *account balances after void*, no test asserts *isolation with an unwrapped transaction*.
2. **Test-environment artefacts hide production defects.** `pytest.mark.django_db` transactions make `SET LOCAL` appear to work (C-03); Redis-backed cache/ratelimit in `settings/testing.py` means the cache path is never exercised locally.
3. **Reporting vs production targets differ.** `pytest.ini` overrides `pyproject.toml` config (L-02), the CI workflow runs `--no-migrations --reuse-db` against a manually initialised schema, which is correct for a SQL-first design but means schema drift is only detected if someone runs the schema script.
4. **Coverage of dead code** (M-06) inflates perceived quality.

**Recommended gate (definition of done for the fix programme)**

```bash
# 1. Schema-model conformance (new)
python manage.py shell -c "from tools.schema_conformance import assert_models_match_db; assert_models_match_db()"

# 2. Accounting invariants (new suite)
pytest tests/invariants -q          # balance sheet, F5 tie-out, reversal netting

# 3. Existing suite
pytest -q --no-migrations --reuse-db

# 4. Static gates
ruff check . && ruff format --check . && mypy apps common
npm run lint && npx tsc --noEmit

# 5. Supply chain
pip-audit -r requirements.txt && npm audit --omit=dev
```

---

## 12. Remediation Roadmap

Ordered to restore correctness first (a wrong number is worse than a missing feature), then security, then compliance surface, then hygiene. Effort is indicative for one experienced engineer.

### P0 — Stop the bleeding (before any further feature work; ~2–3 days)

| Order | Finding | Work | Done when |
|---|---|---|---|
| 1 | **C-04** | Remove the catch-all from `wrap_response`; move `_post_journal_entry` inside `approve_document`'s atomic block | A forced mid-operation failure leaves no partial state (regression test) |
| 2 | **C-02** | Delete the duplicate placeholder reversal; persist `void_reason`; align voidable statuses; un-skip and implement the reversal test | Post→void→assert zero net account impact |
| 3 | **C-03** | Move `SET LOCAL` inside the view transaction (or use `SET`+reset per request); add fail-closed assertion; add `TransactionTestCase` isolation test | Raw cross-tenant `SELECT` returns no foreign rows under autocommit |
| 4 | **H-01** | Fix `journal_entry__*` lookups | Trial balance endpoint returns 200 with correct totals |
| 5 | **C-01** | Rewrite F5 aggregation against `invoicing.document*`, one box convention, explicit field writes, fixed serializers | F5 for a fixture period ties to the GL and matches hand-computed IRAS Boxes 1–8 |
| 6 | **H-14** | Reconcile GST return model/columns/status vocabulary | Full `DRAFT→COMPUTED→FILED→PAID→AMENDED` test passes |
| 7 | **M-01 / I-01** | Schema-model conformance test in CI | CI fails on any drift |

### P1 — Compliance and security hardening (~1–2 weeks)

8. **H-04** rate history, `is_claimable`, reverse charge, F5 box columns driving the mapping.
9. **H-09** tax-invoice fields + PDF invoice number + Reg-11 compliance test.
10. **H-10** hardened schema/Schematron validation, absolute paths, fail-closed.
11. **H-08** wire `send-invoicenow` to `TransmissionService`; return real transmission log.
12. **H-05 / M-15** refresh rotation + blacklist + logout revocation + password-change revocation; then reset/verification/MFA.
13. **H-06 / H-07 / M-11 / M-12** secret assertions, rate limiting on by default, enforced CSP, secret scanning in CI.
14. **H-11** fiscal close: permission, validation, closing entries, `timezone.now()`.
15. **H-12** F5 box allow-list serializer.
16. **M-02 / M-03** revoke ledger UPDATE/DELETE, add immutability triggers, RLS on `audit.event_log`, single-writer audit, hash chaining.
17. **H-03** widen money precision (`NUMERIC(19,4)`), add range validation.

### P2 — Correct money, then features (~2–3 weeks)

18. **H-02** base-currency reporting, retained earnings, BS assertion, real trial balance.
19. **M-04** in-transaction sequence allocation (gap-free numbers).
20. **M-05** discounts, tax-inclusive lines, rounding policy.
21. **M-09 / M-10** statement-balance reconciliation, streaming import with per-row reporting.
22. **M-13** FX gain/loss on settlement + period-end revaluation.
23. **M-07** GL-backed dashboard metrics; delete the "MVP" proxies.
24. **M-06 / M-08** delete dead services/tests, unify vocabularies.
25. **M-16** encrypt AP credentials, allow-list AP hosts, idempotency keys.
26. **H-13** reproducible multi-stage container build with hashes and verified binaries.
27. **L-01…L-10, I-01…I-08** hygiene, documentation consolidation, dependency auditing.

### Verification ledger for the fix programme

| Claim after P0 | How it must be proven |
|---|---|
| "Void reverses the ledger" | Test asserts per-account net zero after void; manual check in a seeded DB |
| "RLS isolates tenants" | `TransactionTestCase` + raw SQL cross-tenant query under org A returns 0 rows |
| "F5 is correct" | Fixture-based tie-out: GL GST accounts == Box 6/Box 7; Box 4 == 1+2+3; Box 8 == 6−7 |
| "No partial commits" | Fault-injection test on approve/pay/void paths |
| "Schema and models agree" | CI conformance job green on a freshly initialised database |

---

## Appendix A — Commands & Harnesses Executed

```bash
# Environment (sandbox, no PostgreSQL/Redis available)
python3 --version                                  # 3.13.18
pip install django==6.0.2 djangorestframework==3.16.1 djangorestframework-simplejwt==5.5.1 \
    django-cors-headers==4.9.0 django-filter==25.2 django-csp==4.0 django-celery-beat \
    django-ratelimit whitenoise==6.11.0 celery redis psycopg2-binary pytest-django python-decouple

# 1. Framework-level sanity
cd apps/backend && DJANGO_SETTINGS_MODULE=config.settings.testing python3 manage.py check
#   -> System check identified 1 issue: (django_ratelimit.W001)

# 2. Test collection
python3 -m pytest --collect-only -q
#   -> 467 tests collected, 1 error (tests/test_db_conn.py: ModuleNotFoundError: psycopg)

# 3. Non-DB test subset
python3 -m pytest common/tests/test_decimal_utils.py \
    apps/peppol/tests/test_xml_validation_service.py \
    apps/peppol/tests/test_xml_mapping_service.py \
    apps/peppol/tests/test_ap_adapter_base.py -q
#   -> 42 passed, 18 errors (all psycopg2.OperationalError: connection refused)

# 4. Targeted verification harness (audit_work/harness.py) — results quoted in C-01, C-02, H-01, H-03
python3 /home/user/audit_work/harness.py

# 5. Skill Phase 3 scanner
python3 skills/code-review-and-audit/scripts/checklist_runner.py apps/backend
#   -> 29 findings: 18 'critical' (all triaged false positives: test fixtures/docstrings),
#      5 'Unclear CAPS comment' false positives, 5 informational, 1 no_gitignore

# 6. Framework transaction semantics (evidence for C-03)
sed -n '85,110p;175,200p;340,360p' \
    /usr/local/lib/python3.13/site-packages/django/core/handlers/base.py

# 7. Static sweeps
grep -rn "cursor.execute(f\"|\.raw(f\"" --include=*.py .            # 0 hits (no SQL injection surface)
grep -rn "SECRET_KEY|PASSWORD|API_KEY|TOKEN\s*=\s*['\"]..."        # 1 committed JWT (start_apps.sh:224)
grep -rn "localStorage|document.cookie" apps/web/src               # 1 hit (dead path, L-07)
git ls-files | grep -c "^apps/web/dist/"                          # 54 committed build artefacts
```

**False positives explicitly discarded (per `code-review-and-audit` aggregation rules):** all 18 "Hardcoded credential" hits from the scanner are `test-api-key`, `testpassword123`, `your-api-key` in docstrings or fixtures; "Unclear CAPS comment" hits are `config("REDIS_URL", …)` lines; `X-Frame-Options` present; `DEBUG=False` by default in base and production.

---

## Appendix B — Files Read In Full or Substantively

**Configuration & schema:** `database_schema.sql` (§0–§15 incl. RLS, indexes, grants, functions, triggers), `config/settings/{base,development,production,testing}.py`, `pyproject.toml`, `pytest.ini`, `common/db/backend/base.py`, `common/models.py`, `common/decimal_utils.py`, `common/exceptions.py`, `common/views.py`, `.github/workflows/ci.yml`, `apps/backend/{Dockerfile,docker-compose.yml,.env,.env.example}`, `apps/web/{next.config.ts,package.json,.env.local,src/middleware.ts}`.

**Services:** `apps/gst/services/{calculation_service,return_service,tax_code_service}.py`; `apps/journal/services/journal_service.py`; `apps/invoicing/services/document_service.py`; `apps/banking/services/{payment_service,reconciliation_service,bank_account_service}.py`; `apps/core/services/{auth_service,dashboard_service,org_seed_service}.py`; `apps/reporting/{views,services/dashboard_service}.py`; `apps/peppol/services/{xml_generator_service,xml_mapping_service,xml_validation_service,transmission_service,ap_storecove_adapter}.py`; `apps/peppol/tasks.py`.

**Views/serializers/permissions:** `apps/core/{views/auth.py,views/fiscal.py,views/dashboard.py,permissions.py,authentication.py,serializers/auth.py}`; `apps/gst/{views.py,serializers.py,urls.py}`; `apps/invoicing/{views.py,urls.py}`; `apps/journal/views.py`; `apps/banking/views.py`; `apps/peppol/{views.py,urls.py,models.py}`; `common/middleware/{tenant_context,audit_context}.py`.

**Models:** `apps/core/models/{gst_return,invoice_document,invoice_line,journal_entry,journal_line,organisation}.py`.

**Frontend:** `src/lib/api-client.ts`, `src/providers/auth-provider.tsx`, `src/hooks/use-invoices.ts`, `src/hooks/use-banking.ts`, `(dashboard)/banking/*`, `(dashboard)/dashboard/dashboard-client.tsx`, `src/lib/gst-engine.ts`.

**Tests reviewed for evidence:** `tests/integration/test_invoice_operations.py`, `tests/middleware/test_rls_context.py`, `tests/security/test_rls_isolation.py`, `tests/integration/test_gst_calculation.py`, `apps/reporting/tests/*`, `common/tests/test_decimal_utils.py`.

**Templates:** `apps/invoicing/templates/invoicing/invoice_pdf.html`.

**Skills consulted:** `skills/skills-catalog.md`, `skills/code-review-and-audit/SKILL.md` + `references/{review-modes,severity-matrix}.md` + `scripts/checklist_runner.py`, `skills/code-review-checklist/SKILL.md`, `skills/statement-auditor/skills/audit-xls/SKILL.md`, `skills/gl-reconciler/skills/gl-recon/SKILL.md`, `skills/verification-and-review-protocol`, `skills/code-quality-standards`, `skills/vulnerability-scanner` (referenced via the orchestrator's dependency graph).

---

## Appendix C — How the Skills Were Applied

| Skill | How it shaped this audit |
|---|---|
| `code-review-and-audit` (deep profile) | Provided the pipeline skeleton (Phase 1 static → Phase 2 security → Phase 3 quality → Phase 4 tests → Phase 6 expert review), the severity taxonomy, the finding schema (location/evidence/impact/severity/remediation/confidence) and the aggregation rules used to discard false positives. Its scripts were executed where they existed; where they did not (no `test_runner.py`/`lighthouse_audit.py` available), the native-CLI fallback was used rather than fabricating results. |
| `code-review-checklist` | The 12-category tactical scan (correctness, security, performance, quality, testing, docs, error handling, naming, type safety, React/UI, LLM patterns, anti-patterns) — used as the coverage checklist; findings mapped into Section 3–7. |
| `code-quality-standards` (Six-Axis) | Produced the scorecard in §0 and the maintainability findings (duplication M-06, vocabulary drift M-08, dead code L-06). |
| `vulnerability-scanner` (OWASP 2025) | Section 10 mapping, supply-chain findings (H-13, I-08), secret sweep (M-12), SSRF/mass-assignment analysis (M-16, H-12). |
| `verification-and-review-protocol` (Iron Law) | Every non-trivial claim carries a confidence label (§1.3); "not run in this environment" is stated explicitly for DB, browser, E2E and CVE checks. |
| `statement-auditor` (`audit-xls` / `nav-tieout`) | Reframed for code: treat the F5 as a statement that must tie out to the GL, Box 4 = 1+2+3, Box 8 = 6−7, and refuse to accept "generated successfully" as evidence (C-01, H-02, I-02). |
| `gl-reconciler` (`gl-recon`) | Reframed: GL ↔ subledger/report reconciliation buckets (matched / amount break / GL-only / subledger-only) applied to GL-vs-F5, AR/AP-vs-control-account, and bank-statement-vs-cash-book (M-09 provides no reconciliation at all). |

---

## Appendix D — Not Verified (and what would be needed)

| Item | Why not verified | How to verify |
|---|---|---|
| Runtime RLS behaviour with a live PostgreSQL | No DB in sandbox | Provision PG 16, run `database_schema.sql`, log `current_setting('app.current_org_id', true)` at the first query inside a view under a real WSGI/ASGI server |
| `numeric field overflow` at >999,999.9999 | No DB | `INSERT` a 1,000,000.00 value into `journal.line.debit` |
| Enum violations (`PAID_PARTIAL`, `AMENDING`, `PAID`) | No DB | Execute `void_document`/`amend_return` against the real schema; expect `invalid input value for enum` / CHECK violation |
| End-to-end GST F5 output | No DB, and the API path fails earlier at the serializer | After P0 fixes, run the fixture tie-out suite |
| CVE status of pinned Python/Node dependencies | No advisory data offline | `pip-audit`, `npm audit --omit=dev`, OSV/GitHub Advisory lookup |
| Frontend build, ESLint, tsc, Vitest, Playwright, axe, Lighthouse | `node_modules` absent; no browser | `npm ci && npm run lint && npx tsc --noEmit && npm test && npx playwright test` |
| PEPPOL XSD/Schematron conformance of generated XML | Schemas resolve only from a specific CWD; no reference validator installed | Run `XMLValidationService` from `apps/backend`, then validate against the official PINT-SG release with `lxml.isoschematron` |
| IRAS e-Filing field-level spec for Boxes 9–15 | Requires IRAS technical documentation | Cross-check the box mapping against IRAS's published GST e-Filing spec (I-03) |
| Production deployment topology (whether `settings/production.py` and a proxy that adds headers are actually used) | Not in repo | Inspect deployment manifests/runbooks |

---

## Appendix E — Audit Scope Discipline

Per the `code-review-and-audit` skill and this agent's operating contract:

- **No source file in the repository was modified.** All work was read-only; the harness lives outside the repo at `/home/user/audit_work/harness.py`.
- **Findings are separated from fixes.** The roadmap (§12) is advisory; nothing was refactored.
- **Severity was assigned, not inflated.** Two findings were deliberately *downgraded* during review: the GST rounding behaviour (`100.005 × 9% → 9.00`) is consistent with IRAS's allowance for cent-level rounding and is reported as part of M-05 rather than as a compliance defect; and the middleware's `is_active` bypass was reduced from a security finding to a design weakness because DRF's authenticator still rejects inactive users (M-14).
- **Out-of-scope but noted:** repository hygiene (L-01), the `skills/` subtree itself (third-party skill library — reviewed only for the audit-relevant skills), and the `plan/`, `backup/`, `docs/` documentation sets beyond the claims cross-checked in §9.
- **Clean areas, stated plainly:** no SQL injection surface; no committed live secrets; no `eval`/`exec`; Decimal handling in `common/decimal_utils.py` is correct and well tested; the database schema is thoughtfully designed (RLS scaffolding, deferred balance trigger, rate-history columns, append-only audit table, F5 box columns) — most Critical findings are *the application failing to use the design the schema provides*.

---

*Report generated 2026-11-21 · Mode C (Audit/Review) · 0 repository files modified · Evidence in §1.2 and Appendix A · Confidence labels appear on every non-trivial finding.*
