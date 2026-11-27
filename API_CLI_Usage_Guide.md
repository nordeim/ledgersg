# LedgerSG API CLI Usage Guide

> **Direct Backend API Interaction via Command Line**
> **For AI Agents and Advanced Users**
> **Version**: 3.2.1 (the P23 addendum + the P21 list-envelope unification + the P19 addendum + the P20 route errata)
> **Last Updated**: 2026-11-27 (P23 — no API-surface change: the sprint is presentation/test-tier (the mobile-nav drawer transition truth + the vitest advisory closure); every documented contract carries forward unchanged from P21 — the list-envelope unification: every list endpoint returns `{results, count}` incl. `/auth/organisations/` which was a bare array; the InvoiceNow evidence stamp; the on-commit cache invalidation; the ValidateBalance typed-400 body contract; carried forward: the P20 route errata + the P17 400 contracts)
> **Status**: Production Ready ✅ (SEC-001/002/003, E2E Testing Complete, API Contracts Fixed)

---

## 2026-11-23 Live Re-Verification (P12)

Every documented contract below was re-exercised against the running stack
(post-P11 remediation) before this update:

| Contract | Result |
|:---|:---|
| `POST /api/v1/auth/login/` → `{tokens: {access, refresh}}` | ✅ Verified (live curl) |
| All 9 documented list endpoints → `{results, count}` envelope | ✅ Verified — 9/9 return HTTP 200 with the paginated object (banking×3, contacts, documents, tax-codes, returns, accounts, journal entries) |
| Journal mount: `/journal/entries/` 404 vs `/journal-entries/entries/` 200 | ✅ Verified (both directions) |
| `POST /documents/{id}/approve/` → posts the GL journal | ✅ Verified (P11 live gate); **credit notes post REVERSED entries** — AR credit, revenue/GST debit (P11/C-1 fix) |
| F5 computation | ✅ Net of credit notes, posted-types only (P11/H-3) — quotes no longer pollute Box 1 |
| Dashboard metrics | ✅ `GET /api/v1/{orgId}/reports/dashboard/metrics/` (the H-4 surface; `gst_payable` non-zero on real data) |
| Org context for CLI flows | ✅ `GET /api/v1/auth/organisations/` returns the membership list — take `results[i].org.id`; **P21/BE-M6**: this route now speaks the unified `{results, count}` envelope (it was the one bare array) |

### Historical Test Metrics (post-P11/P12 — superseded by post-P16 below)

| Suite | Count | Status |
|:---|:---|:---|
| Backend Tests | 750 passed, 5 skipped, 0 failed (755 collected) | ✅ 100% of registered |
| Frontend vitest | 530 passed (518 P12 + 12 P13) | ✅ |
| Frontend e2e | 11 always-green + 29 backend-gated; 40/40 live under `test:e2e:full` | ✅ |

### 2026-11-24 P13 verification addendum

The P13 backend sprint changed no documented request/response contract;
the behavioral deltas verified live this session:

| Contract | P13 delta |
|:---|:---|
| `POST /gst/calculate/` (and every line-GST path) | Sub-cent bases now round to IRAS 2 decimal places: `100.05 × 0.09 → gst_amount "9.00"` (was the 3-dp `"9.005"`) — verified live via curl |
| `POST /documents/{id}/send-invoicenow/` + `GET /documents/{id}/invoicenow-status/` | A missing document now returns the typed `404 {"error":{"code":"not_found"}}` envelope (was a raw 500) |
| Any unhandled server error | Still the `500 {"error":{"code":"internal_error"}}` envelope, but the request transaction now ROLLS BACK (no partial writes) |
| Health endpoints | The 503 body carries a generic message (no raw DB error strings) |

### 2026-11-26 P14/P15 verification addendum

The P14/P15 sprints changed several request/response contracts (all
exercised live against the running stack this session):

| Contract | P14/P15 delta |
|:---|:---|
| `POST /gst/returns/{id}/?force=true` | A **FILED/AMENDED** return is refused with a typed 409 (the statutory record is immutable — corrections go through `/amend/`); pre-P14 `force=true` silently recomputed it and regressed the status |
| `POST /documents/{id}/approve/`, `void`, `POST /journal-entries/entries/`, payment void | A 409 "GST-locked" refusal when the document/journal date falls inside a period whose F5 return is FILED/AMENDED (the ledger basis of the filed figures cannot change by back-posting) |
| `POST /banking/payments/receive/` | Allocations are capped at the document's outstanding balance (400 with the outstanding figure in the message; was: negative `amount_due`); allocation-eligible statuses are APPROVED, SENT, PARTIALLY_PAID, OVERDUE (instalment cycles now complete) |
| `POST /invoicing/documents/` | `lines` is REQUIRED (min 1) with a real line schema — `account_id` UUID, `quantity` > 0 ≤ 10^6, `unit_price` ≥ 0 < 10^13, `discount_pct` ∈ [0,100]; a missing `lines` key is a 400 (was a KeyError 500). `*_CREDIT_NOTE` documents REQUIRE `related_document_id` (same contact, same direction, cumulative credit ≤ the original total incl. GST — the IRAS credit-note rule) |
| `POST /organisations/` + `POST /api/v1/{org_id}/gst/` (register) | UEN must match an ACRA format (8 digits+letter / 9 digits+letter / T|S+YY+2letters+4digits+letter); GST numbers accept the M-form (M+7 or 8 digits+check letter) **or** a valid UEN (the old `startswith("M")` rejected valid UEN-form numbers and accepted garbage) |
| `POST /gst/returns/{id}/file/` | Box overrides REQUIRE `override_reason` (≥ 10 chars); the reason + computed-vs-filed deltas persist into the return's `notes` |
| `GET /banking/bank-accounts/` | NRIC-type `paynow_id` values are MASKED on read (`S*****67D`); writes reject values containing `*` (PDPA) |
| Viewer-role members | Contact create/patch/delete and document send now 403 (read-only role) |
| `GET /gst/tax-codes/` | Deduped per (code, effective_from, effective_to) — org bands shadow identical system bands; rate history intact |
| Runtime DB role | The full onboarding path (register → org → contact → invoice → approve → payment → F5) runs as the non-superuser `ledgersg_app` role under RLS — verified by `scripts/rls_smoke.py` (13/13 steps; org creation was a 500 pre-P14) |
| Frontend api-client | Concurrent 401s share ONE refresh call (single-flight) — sessions no longer die mid-suite on the rotation race |

**Test metrics (post-P15)**: backend **834 passed / 0 failed / 5
skipped** · frontend vitest **532/532** · e2e 11 always-green + 29
backend-gated, **40/40 live** under `test:e2e:full`.

### 2026-11-26 P16 verification addendum

The P16 sprint (session 32) changed several request/response contracts
(all exercised live against the running stack):

| Contract | P16 delta |
|:---|:---|
| `POST /banking/payments/{id}/allocate/` | The dedicated allocate endpoint now accepts instalments: allocation-eligible statuses are APPROVED, SENT, PARTIALLY_PAID, OVERDUE (the wire serializer still demanded APPROVED-only — the P14 fix had missed it) |
| `POST /banking/payments/receive/` + `/make/` | Payment creation + allocations are ONE transaction — an allocation failure no longer leaves an orphaned payment + journal entry behind a 400 |
| `POST /gst/returns/{id}/file/` (box overrides) | NaN/Infinity values are refused (400) — a non-finite value could previously be FILED into the statutory record |
| `POST /invoicing/documents/` (lines) | The line TOTAL (quantity × unit_price) is bounded to the NUMERIC(19,4) capacity — in-bounds fields whose product overflowed were a 500 |
| `POST /invoicing/documents/{id}/lines/` | `discount_pct` is now forwarded (the same payload previously produced a discounted line via create and an undiscounted line via line-add) |
| `PATCH /gst/tax-codes/{id}/` (system rows) | System (global) tax-code rows are read-only through the API (a typed 400; previously the RLS policy turned the edit into an unhandled 500) |
| `POST /organisations/` (uen) | The UEN/GST number is stored NORMALIZED (trimmed + upper) — a lowercase tail previously dodged the case-sensitive UNIQUE pre-check |
| Bank statement import (`/banking/bank-transactions/import/`) | Non-UTF-8 (latin-1) statements actually import (the fallback previously re-read a consumed stream and silently imported 0 rows) |
| Payment audit trail | The `trg_audit_payment` trigger is the single audit source for payment rows (the manual duplicate writes were removed); ALLOCATE/UNALLOCATE events remain app-level (payment_allocation has no trigger) |
| Status restoration | Releasing the last allocation of an InvoiceNow-transmitted document restores SENT (not a blanket APPROVED); the payment-void reversal date is Asia/Singapore localdate |
| Frontend (login) | The `?redirect=` parameter only honours same-app paths (open-redirect closed) |
| Frontend (org creation) | The new organisation is SELECTED immediately (the stale-closure fix) — no more "No Organisation Selected" dead-end |
| Frontend (UEN) | All three ACRA formats validate (LLP/society T/S-forms included — previously rejected) |

**Historical test metrics (post-P16 — superseded by post-P21 below)**: backend **860 passed / 0 failed / 5
skipped** (865 collected; invariants 34, security 76+3 skipped) · frontend
vitest **554/554** (64 files) · e2e 11 always-green + 29 backend-gated,
**40/40 live** under `test:e2e:full` · the production-CSP smoke **5/5** ·
the runtime-role smoke **13/13**.

### Endpoints added to this guide's coverage (P16)

| Endpoint | Contract |
|:---|:---|
| `POST /api/v1/{org_id}/banking/payments/make/` | Pay a supplier (contact + bank account + amount + optional allocations) — the twin of `/receive/` |
| `POST /api/v1/{org_id}/banking/bank-transactions/import/` | Multipart CSV statement import (utf-8 or latin-1); returns `{imported, skipped, errors}` |
| `GET /api/v1/{org_id}/gst/returns/deadlines/` | The filing-deadline envelope (current + upcoming periods) |
| `GET /api/v1/{org_id}/journal-entries/ledger/` | The flat line-level ledger (one row per journal line — the line-level table's source) |

### 2026-11-27 P17 verification addendum

The P17 sprint (session 34) closed the money-mutation concurrency races and
the 400-contract gaps (all pinned by `tests/integration/test_concurrency_
contracts_p17.py` + `tests/integration/test_api_contract_p17.py` +
`tests/integration/test_journal_workflow.py` for the double-reversal):

| Contract | P17 delta |
|:---|:---|
| `POST /journal-entries/entries/{id}/reverse/` | A **second reversal of the same entry is refused (400)** — the row is locked for the whole reversal and re-checked (`select_for_update`); pre-P17 two sequential (or concurrent) reversals posted the swap-side lines twice, misstating every account 2x while the trial balance stayed balanced |
| `POST /banking/payments/{id}/void/` | A **second void is refused (400)** — the payment row is locked and `is_voided` re-checked post-lock (the TOCTOU window is closed); the single void still posts the reversal GL entry |
| `POST /banking/bank-transactions/{id}/reconcile/` | Reconciling the **same payment twice is refused (400)**; the payment and transaction rows are locked for the match. The two routes now use `<uuid:transaction_id>` converters — a malformed id is a **404 at the routing layer** (was a UUID() 500) |
| `POST /gst/returns/{id}/file/` (box overrides) | Box values are **type-checked before parsing** — `null`, objects, and non-numeric strings are a 400 field error (was a TypeError 500); NaN/Infinity stay 400 (P16) |
| `POST /banking/payments/{id}/allocate/` (bulk) | A non-UUID `document_id` ("abc") is a **400 field error** (was an unhandled UUID 500); valid UUIDs unchanged |
| `PATCH /api/v1/{org_id}/` (uen) | The UEN is **normalized (trim + upper) then validated** on update — lowercase/whitespace input is accepted and stored normalized; an invalid ACRA form is a 400; the case-dodge UNIQUE collision (update "abc123d" against existing "ABC123D") is refused. **URL: the org-scoped root** (`PATCH /api/v1/{org_id}/` — `PATCH /api/v1/organisations/{id}/` 404s; `POST /api/v1/organisations/` remains the create route) |
| `PATCH /gst/tax-codes/{id}/` (rate) | The rate is range-checked on update — 9 (a percent) and negative values are 400; `0.09` unchanged |
| `POST /banking/payments/receive/` (exchange_rate) | FX rates round-trip at their wire precision — a 6-dp rate (0.876543) is stored and used exactly (the money() quantize no longer truncates it to 4 dp); monetary amounts stay 4-dp |
| InvoiceNow/PDF/email tasks | Dispatched **on commit** — a rolled-back transaction no longer queues phantom tasks; a real Celery worker runs the task inside the tenant RLS context (`app.current_org_id` SET LOCAL — `common/tenant_context.py`). Eager mode (dev default) is bit-identical |
| `GET /admin/` | **404 under non-DEBUG settings** (the URL is no longer mounted in production/service settings — settings-gate tested) |
| List endpoints (`payments`, `documents`, `transactions`) | `select_related` on the FK joins — the N+1 is gone (query-count gated); response shapes unchanged |

**Historical test metrics (post-P17 — superseded by post-P21 below)**: backend **882 passed / 0 failed / 5
skipped** (887 collected; invariants 34, security 78+3 skipped) · frontend
vitest **582/582** (69 files) · e2e 11 always-green + 29 backend-gated,
**40/40 live** under `test:e2e:full` · the production-CSP smoke **5/5** ·
the runtime-role smoke **13/13** · the mobile-nav probe **17/17**.

### 2026-11-27 P18 verification addendum

The P18 sprint (session 36) closed the statutory-record TOCTOU, the
residual concurrency seams, and the task-contract gaps (all pinned by
`tests/integration/test_concurrency_contracts_p18.py` +
`test_celery_tenant_context_p18.py` + `test_api_contract_p18.py` +
`tests/security/test_schema_gates_p18.py`):

| Contract | P18 delta |
|:---|:---|
| `POST /gst/returns/{id}/?force=true` (recompute) + `POST /gst/returns/{id}/review/` | The return row is **locked for the whole recompute/review** (`select_for_update` inside an atomic block, the `file_return` pattern) — a recompute can no longer interleave with a filing and regress a FILED statutory record to COMPUTED while `filed_at` stays populated. (P20/X-M5 erratum: the P18 addendum originally documented a nonexistent `POST /gst/returns/{id}/generate/` route — the recompute has always been the force-recompute POST the P14 row documents.) |
| `POST /banking/bank-transactions/{id}/unreconcile/` | The transaction→payment lock order matches its siblings — `amount_paid`/status recomputes and the reconcile-flag writes are serialized against `allocate()`/`reconcile()`. (P20/X-M6 erratum: the P18 addendum originally documented a `POST /banking/payments/allocations/{id}/` unallocate route — no such HTTP route exists; `unallocate` is a SERVICE-level operation with no view. The documented contract is unreconcile only.) |
| `POST /invoicing/quotes/convert/` (the quote id in the request body: `{"quote_id": "<uuid>"}`) | The quote row is **locked with a post-lock status re-check** — two concurrent converts no longer create two invoices from one quote. (P20/X-M7 erratum: the P18 addendum originally documented `POST /invoicing/quotes/{id}/convert/` — the route is body-parameterised, no path id.) |
| `POST /invoicing/documents/{id}/lines/` (add_line) | The document row is locked for the line-number read+insert; a residual `uq_docline_doc_lineno` race surfaces as a **typed 400** ("the document changed while the line was being added — reload and retry"), never an IntegrityError 500 |
| Credit notes (`POST /invoicing/documents/` with `related_document_id`) | The ORIGINAL document row is locked for the cumulative-cap check, and the check runs inside the create transaction — racing credit notes can no longer jointly exceed the original total |
| `POST /journal-entries/entries/` (manual entries) | Lines posting to a **header** account or an **archived** (`is_active=false`) account are refused with a typed 400 — the trial balance (which filters active accounts) can no longer diverge from the ledger |
| `GET /banking/bank-transactions/{id}/suggest-matches/` | Malformed transaction ids are a **routing 404** (the `<uuid:transaction_id>` converter — the same contract as reconcile/unreconcile) |
| `POST /invoicing/documents/{id}/send/` (email) | Only **APPROVED (or settled) SALES_INVOICEs** can be emailed — the emailed PDF is a rendered TAX INVOICE (the same gate `send_invoicenow` carries); VOID/DRAFT/quotes are a 400 |
| Peppol task contracts | `retry_failed_transmission_task` / `check_transmission_status_task` take the **org_id argument** (the RLS-scoped log row cannot be read to learn it) and open the RLS tenant context; `cleanup_old_transmission_logs_task` runs per-org (`org_id` argument) or refuses loudly without one; a deleted org/document mid-task is a **terminal** result, not a 3x60s retry cycle |
| `create_return_periods` | The UNIQUE(org, type, period) race is typed — the loser skips cleanly (never an IntegrityError 500) |
| Service seam (`_validated_exchange_rate`) | A garbage rate from a direct (non-DRF) caller is a typed 400, not an InvalidOperation 500 |

**Current test metrics (post-P21)**: backend **969 passed / 0 failed / 5
skipped** (974 collected; invariants 34, security 83+3 skipped) ·
frontend vitest **641/641** (75 files) · e2e 11 always-green + 29
backend-gated, **40/40 live** under `test:e2e:full` · the
production-CSP smoke **5/5** · the runtime-role smoke **13/13** · the
mobile-nav probe **17/17**.

---

## P23 Addendum — no API-surface change; the gates re-verified (2026-11-27, session 44)

**The P23 sprint touched no backend application code and no request/response
contract.** The changes: the frontend drawer's transition token
(`transition-[transform,translate,visibility]` — presentation-only), one
vitest spec + one e2e spec (test-tier), and the vitest devDependency bump
(^4.0.18 → ^4.1.12, tooling-only). Every contract below carries forward
unchanged from P21.

Current gate truth (re-verified on a fresh clone, session 44): backend
**969 passed / 0 failed / 5 skipped** · frontend **642 vitest + 41 e2e**
(41/41 live) · typecheck 0 · eslint 0E/0W · `npm audit` **0 critical** (the
17 residual findings are dev-tier; the production dependency set is clean).
The environment lesson for CLI operators: the `ledgersg_app` role carries
the schema's dev default password `CHANGE_ME_IN_PRODUCTION` — the RLS tests
rely on it (see `docs/REMEDIATION_2026-11-27_P23_REPORT.md`).

## P21 Addendum — the list-envelope unification (2026-11-27, session 42)

**The contract change:** every LIST endpoint now returns
`{results, count}`. Single-report payloads (`/reports/financial/`
trial-balance / profit-loss / balance-sheet, dashboard metrics) keep
their `{data: {...}}` shape — the convention is *lists → results,
reports → data*.

Seven routes changed shape in P21 (all previously `{data, count}` or a
bare array):

| Route | Old shape | New shape |
|:---|:---|:---|
| `GET /api/v1/auth/organisations/` | bare array `[...]` | `{results: [...], count}` |
| `GET /api/v1/organisations/` | `{data, count}` | `{results, count}` |
| `GET /api/v1/{org_id}/fiscal-years/` | `{data, count}` | `{results, count}` |
| `GET /api/v1/{org_id}/journal-entries/trial-balance/` | `{data, count, totals, as_of_date}` | `{results, count, totals, as_of_date}` |
| `GET /api/v1/{org_id}/journal-entries/entries/types/` | `{data, count}` | `{results, count}` |
| `GET /api/v1/{org_id}/gst/tax-codes/iras-info/` | `{data, count}` (results carries the keyed map) | `{results, count}` |
| `POST /api/v1/{org_id}/gst/returns/` (create periods) | `{message, count, data}` | `{message, count, results}` |

CLI recipes that read `.data` or indexed the bare array must read
`.results` (the e2e helpers + the bootstrap script were migrated in the
same commit). Every other list endpoint already spoke `{results, count}`.

**Also in P21** (behaviour, not shape): `invoicenow_sent_at` is now
stamped on a DELIVERED Peppol transmission (the void/unallocate restore
reads it); the dashboard + balance caches invalidate on COMMIT
(`transaction.on_commit`) after voids / manual journal entries /
postings; `POST /journal-entries/entries/validate/` returns a typed 400
envelope (not a 500) on malformed bodies; the bank-account default flag
is row-locked (concurrent `set_default` calls serialize).

---

## 🎉 Recent Milestone: API Contract Standardization & 500 Error Investigation ✅ COMPLETE (2026-03-15)

### Summary

1. **API Contract Standardization**: 9 endpoints now return standardized `{results, count}` format
2. **500 Error Investigation**: Debunked myth - production API works correctly (verified with direct testing)

### Key Knowledge & Fixes (2026-03-15)

| Category | Finding / Issue | Resolution / Knowledge |
|:---|:---|:---|
| **API Contract** | Backend returned arrays `[]`, frontend expected `{results, count}`. | **FIXED**: 9 list views updated to return paginated format. |
| **500 Error Myth** | Documentation claimed "500 errors in journal/invoice" | **DEBUNKED**: Production API works correctly - 403s from test fixtures only |
| **Test Fixture Issue** | 67 tests fail with "User not authorized" | pytest isolation issue, not production bug |
| **Session Persistence** | HttpOnly cookies break automation tools. | **SOLUTION**: Hybrid API + UI approach. |

### Test Metrics (as of 2026-03-15 — superseded by the 2026-11-23 block above)

| Suite | Count | Status |
|:---|:---|:---|
| Backend Tests | 468 collected, 393 passing | ✅ 84% (historical) |
| Frontend Tests | 321 passing | ✅ 100% (historical) |
| API Contract Tests | 8 passing | ✅ 100% |

### Previous Milestone: SMB Workflow Hardening ✅ COMPLETE (2026-03-10)

Successfully completed full E2E validation for **Lakshmi's Kitchen** (12-month Corporate Cycle) and **ABC Trading** (Sole Prop Smoke Test). This involved hardening the `JournalService` posting engine and ensuring models match the `database_schema.sql` exactly.

### Key Knowledge & Fixes (Workflow 1 & 2)

| Category | Finding / Issue | Resolution / Knowledge |
|:---|:---|:---|
| **Ghost Columns** | Model inheritance adding `created_at` to tables without them. | Switched `Peppol` models to inherit from `models.Model` to match SQL exactly. |
| **Logic Filter** | `is_voided` filter in `JournalService` caused 500 errors. | Removed invalid filter; posting engine now handles lines via the document's approved state. |
| **Side Effects** | Payments alone don't show revenue. | **MANDATORY**: You MUST call `/approve/` on an invoice to trigger the Revenue/AR journal entries. |

---

## Troubleshooting (Updated)

### "ProgrammingError: column organisation_peppol_settings.created_at does not exist"
**Status**: ✅ **FIXED** (2026-03-10)
**Cause**: The model was incorrectly inheriting from a base class that adds timestamp fields not present in the SQL schema.
**Solution**: Ensure models match `database_schema.sql` exactly.

### "FieldError: Cannot resolve keyword 'is_voided' into field"
**Status**: ✅ **FIXED** (2026-03-10)
**Cause**: Service layer code was trying to filter by a field that doesn't exist in the database table.
**Solution**: Refined `JournalService` to query lines directly via the parent document.

### API Contract Mismatch: List Endpoints Return Arrays
**Status**: ✅ **FIXED** (2026-03-14)
**Cause**: Backend list views returned `serializer.data` (array), but frontend expected `{results, count}` (paginated object).
**Impact**: Banking page completely broken with `TypeError: Cannot read properties of undefined (reading 'map')`
**Solution**: Updated 9 list views to return paginated format:
- ✅ `BankAccountListView` → `GET /api/v1/{orgId}/banking/bank-accounts/`
- ✅ `PaymentListView` → `GET /api/v1/{orgId}/banking/payments/`
- ✅ `BankTransactionListView` → `GET /api/v1/{orgId}/banking/bank-transactions/`
- ✅ `ContactListView` → `GET /api/v1/{orgId}/invoicing/contacts/`
- ✅ `InvoiceDocumentListView` → `GET /api/v1/{orgId}/invoicing/documents/`
- ✅ `TaxCodeListView` → `GET /api/v1/{orgId}/gst/tax-codes/`
- ✅ `GSTReturnListView` → `GET /api/v1/{orgId}/gst/returns/`
- ✅ `AccountListView` → `GET /api/v1/{orgId}/accounts/`
- ✅ `JournalEntryListView` → `GET /api/v1/{orgId}/journal-entries/entries/`

**Response Format** (all list endpoints now):
```json
{
  "results": [...],
  "count": 42
}
```

### Session Not Persisting in E2E Tests
**Status**: ✅ **RESOLVED FOR PLAYWRIGHT** (2026-11-23)
**Cause**: HttpOnly refresh cookies are invisible to JS-based automation drivers.
**Resolution**: the Playwright e2e suite authenticates through the UI and the
browser context carries the HttpOnly cookie session across reloads and
client-side navigation (P4/E-1 — the `session.spec.ts` specs assert the
reload-persistence contract and run green under `test:e2e:full`). For
pure-CLI drivers without a cookie jar, the hybrid API approach below still
applies:
```bash
# 1. Authenticate via API
curl -X POST http://localhost:8000/api/v1/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.sg", "password": "password"}'
# Returns: {"tokens": {"access": "...", "refresh": "..."}}

# 2. Use access token for all API calls
curl -H "Authorization: Bearer $ACCESS_TOKEN" \
  http://localhost:8000/api/v1/{orgId}/banking/bank-accounts/

# 3. Use UI only for screenshots/visual verification
# (Playwright with hybrid approach)
```

### Journal Entries Endpoint URL
**Status**: ⚠️ **CLARIFIED** (2026-03-14)
**Issue**: `/api/v1/{orgId}/journal/entries/` returns 404
**Actual URL**: `/api/v1/{orgId}/journal-entries/entries/`
**Cause**: Root URL config mounts journal URLs at `journal-entries/` not `journal/`:
```python
# config/urls.py
org_scoped_urlpatterns.append(path("journal-entries/", include("apps.journal.urls")))
```
**Correct CLI**:
```bash
# ❌ Incorrect
curl http://localhost:8000/api/v1/{orgId}/journal/entries/

# ✅ Correct
curl http://localhost:8000/api/v1/{orgId}/journal-entries/entries/
```

---

## CLI Examples

### 1. Approve an Invoice (Mandatory for GL)
```bash
curl -X POST "http://localhost:8000/api/v1/{orgId}/invoicing/documents/{id}/approve/" \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```

**P11/C-1 direction truth**: approving a **credit note** posts the journal
REVERSED — the AR line is a CREDIT (customer receivable shrinks), the revenue
and GST lines are DEBITS. Approving an invoice posts the normal direction.

### 2. Verify Ledger Posting
```bash
# Check if journal entries were created
curl -X GET "http://localhost:8000/api/v1/{orgId}/journal-entries/entries/" \
  -H "Authorization: Bearer $ACCESS_TOKEN" | jq '.results'
```

### 3. Dashboard Metrics (the H-4 surface)
```bash
curl "http://localhost:8000/api/v1/{orgId}/reports/dashboard/metrics/" \
  -H "Authorization: Bearer $ACCESS_TOKEN"
# gst_payable is computed from document lines (non-zero on real data)
```

---

## P19 Addendum (2026-11-27, session 38)

**Route-contract completion (BE-M7):** the five remaining `<str:…>`
path segments are now `<uuid:…>` — `fiscal-years/{year_id}/close/`,
`fiscal-periods/{period_id}/close/` and `/open/`, `accounts/{account_id}/`
and `accounts/{account_id}/balance/`. A malformed UUID on these routes
is a **404 at the routing layer** (identical to every sibling route;
previously an untyped 500).

**The bank-statement import caps (X-M2):** `POST
/api/v1/{orgId}/banking/bank-transactions/import/` (multipart: the CSV
file + `bank_account_id` as form fields — the account is NOT a path
segment; P20/X-M4 erratum: the P19 addendum originally documented a
nonexistent `bank-accounts/{accountId}/import-csv/` route, contradicting
the P16 row above) now refuses with a typed 400 before any row
processing when the upload is over **5 MB** or carries more than
**10,000 rows** ("split the export and import it in parts"). At-limit
files import exactly as before — and since P20 one DB-level poison row
(a NUMERIC(19,4) overflow amount) is a **typed row error in the
`errors[]` array** while the surrounding rows import (never an
abort-everything 500).

**The document-line seam (BE-H1):** `DELETE
/api/v1/{orgId}/invoicing/documents/{documentId}/lines/{lineId}/` is
now lock-protected (and actually functional — pre-P19 the service
filtered by a non-existent field and 500'd on every call). Removal is
refused with a 400-class validation error unless the document is
DRAFT, the same contract as `add_line`.

**The journal tolerance (BE-D1):** the create-serializer balance gate
is now `0.0001` (the service and DB-trigger boundary) — a 0.0002..0.001
imbalance is rejected at the serializer with the same error shape as
the service, and the detail serializer's `totals.balanced` flag uses
the same boundary.

---

**End of Guide**
