# LedgerSG API CLI Usage Guide

> **Direct Backend API Interaction via Command Line**
> **For AI Agents and Advanced Users**
> **Version**: 3.7.0 (the P34 credit-note Peppol structure + the ISO-4217 currency-input contract + the P33 currency-truth contract + the P26 transmission-log pagination + the P25 pagination-contract hardening + the P24 pagination contract + the P23 addendum + the P21 list-envelope unification + the P19 addendum + the P20 route errata)
> **Last Updated**: 2026-11-28 (P33 — ONE contract-visible change, byte-identical on the SGD default: three `currency` fields became truthful. (1) The financial reports — `GET /api/v1/{org_id}/reports/financial/?report_type=trial_balance|profit_loss|balance_sheet` — now carry the ORG's `base_currency` instead of a hardcoded `"SGD"` (the ledger they aggregate is denominated in the org's base currency; the invoice PDF already rendered the truthful value). (2) `GET /api/v1/{org_id}/accounts/{account_id}/balance/` now carries the ACCOUNT's own `currency` field instead of a hardcoded `"SGD"` (retiring a literal TODO). (3) The InvoiceNow UBL: every amount element's `currencyID` now carries the document's own currency instead of a hardcoded `"SGD"` (a USD/EUR-denominated document previously transmitted `DocumentCurrencyCode=USD` beside `currencyID="SGD"` amounts — internally inconsistent UBL; `TaxCurrencyCode` stays SGD by design — IRAS GST is accounted in SGD regardless of the document currency). Verified live this session on the SGD demo substrate: the three reports carry `"currency": "SGD"` byte-identical, the account balance carries `"currency": "SGD"`, and a real demo document's generated XML carries only its own currency. Consumers parsing `currency` should treat it as data, never assume SGD. Carried forward: P32 — no API contract changes that sprint (the P32 changes are dead-code/lint-level + test-infrastructure-level: the 3 dead service-seam bindings retired (void's never-read `reversal`, transition's `old_status`, approve's guard-query `fiscal_period` — the side-effect calls stay), the F402 `status` shadow renamed to `status_value` in the document-summary view (a loop-variable rename; the response shape untouched), the journal `credits` → `credit_total` rename (a local rename; the response keys untouched — the trial-balance payload verified live), the SIM105 `contextlib.suppress` conversions + the tests-tree conftest placement — none touch a rendered byte. Verified live this session on the remediated stack: the not-found document detail → the exact documented 404 body `{"error":{"code":"not_found","message":"Document <uuid> not found"}}`, the allocation typed-400s → `{"payment_id":["Payment not found in this organisation."]}` and `{"allocations":["Invalid allocated_amount: garbage"]}` byte-stable, the document-summary endpoint → 200 with the counts envelope (total_count, by_status, by_type, total_outstanding, overdue_count)). Carried forward: P31 — no API contract changes this sprint (the P31 changes are exception-object-level + lint-level: the 66 raise-inside-except sites now chain explicitly (`from exc` / `from None`) — the chaining sets `__cause__`/`__suppress_context__` on the raised exception and NEVER touches the rendered HTTP bodies, verified live this session on the remediated stack: the not-found document detail → the exact documented 404 body `{"error":{"code":"not_found","message":"Document <uuid> not found"}}`, the allocation typed-400s → `{"payment_id":["Payment not found in this organisation."]}` and `{"allocations":["Invalid allocated_amount: garbage"]}` byte-stable; the tests-tree lint closure touched no behaviour). Carried forward: P30 — no API contract changes this sprint (the P30 changes are query-level + lint-level: the reconcile/unreconcile responses now JOIN bank_account instead of walking it (the RESPONSE BYTES pinned byte-identical, verified live this session with a reconcile round-trip on the demo substrate — unreconcile then re-reconcile restored, both payloads carrying bank_account_name), and the ruff mechanical closure touched no behaviour. The bank-transactions list envelope re-verified live: `?limit=2` → count 7 + 2 rows + bank_account_name present). Carried forward: P29 — no API contract changes this sprint (the P29 detail-view N+1 closure is query-level: the three detail seams — document detail, journal entry detail, payment detail — now fetch their related rows in bounded, line-count-independent queries (the contact rides the document SELECT, the lines arrive in ONE joined SELECT carrying account + tax_code, the payment joins its related rows); the RESPONSE BYTES are pinned byte-identical, verified live this session on the remediated stack: the document detail payload (lines with account_code/tax_code_code, the nested contact, the totals), the payment detail payload (contact_name, bank_account_name, the allocations), the contacts envelope `?limit=1` → count 2 total + 1 row + the next URL carrying offset=1). Carried forward: P28 — no API contract changes (the push-down is query-level: the four service-driven lists — contacts, documents, payments, bank transactions — now fetch only the requested page via SQL LIMIT/OFFSET and count via SQL COUNT(*); the RESPONSE BYTES are pinned byte-identical, verified live on the remediated stack: the contacts mid-set page `?limit=1` → count 2 total + 1 row + the next URL carrying offset=1, the beyond-end page → count 2 + 0 rows + previous present, the payments + bank-transactions envelopes `{count, next, previous, results}` with the total counts, the invoices page 2 `?limit=20&offset=20` → count 23 + the last 3 rows + next null, `?offset=` without `?limit=` → the typed 400, `?limit=abc` → the typed 400, the unpaginated path → the byte-identical `{results, count}`). Carried forward: P27 — no API contract changes (frontend state-machine wiring); Carried forward: P26 — the Peppol transmission-log surface joins the pagination contract (limit/offset + the id tiebreaker + the counters in both modes, byte-identical unpaginated) — see the P26 Addendum below; carried forward: P25 — two request-semantics tightenings on the pagination contract: `offset` requires `limit` (the typed 400), the int8 offset cap at 2^63−1 — see the P25 Addendum below; carried forward: the P24 additive `?limit=&offset=` server-side pagination on every core list surface, the P23 presentation/test-tier sprint, the P21 list-envelope unification, the InvoiceNow evidence stamp, the on-commit cache invalidation, the ValidateBalance typed-400 body contract; carried forward: the P20 route errata + the P17 400 contracts)
> **Status**: Production Ready ✅ (SEC-001/002/003, E2E Testing Complete, API Contracts Fixed)

---

## 2026-11-23 Live Re-Verification (P12)

Every documented contract below was re-exercised against the running stack
(post-P11 remediation) before this update:

| Contract | Result |
|:---|:---|
| `POST /api/v1/auth/login/` → `{tokens: {access, refresh}}` | ✅ Verified (live curl) |
| All 9 documented list endpoints → `{results, count}` envelope | ✅ Verified — 9/9 return HTTP 200 with the paginated object (banking×3, contacts, documents, tax-codes, returns, accounts, journal entries); **P24**: the six core list surfaces additionally accept `?limit=&offset=` (the pagination contract — see the P24 Addendum) |
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

## P24 Addendum — the server-side list pagination contract (2026-11-27, session 45)

**The contract change (additive — the default behaviour is unchanged):** every
core list surface now accepts `?limit=N&offset=M` query params. With `limit`
ABSENT, the response stays exactly `{results, count}` as documented in the P21
addendum (every existing recipe below keeps working byte-identically). With
`limit` PRESENT, the envelope gains `next` / `previous` and `count` reads as
the TOTAL matching rows:

```json
{
  "results": [ /* the N rows of this page */ ],
  "count": 1234,           /* the TOTAL matching rows (not the page size) */
  "next": "https://api.example.com/api/v1/{org}/journal-entries/ledger/?limit=50&offset=100",
  "previous": null           /* null on the first page; an absolute URL otherwise */
}
```

The paginated surfaces (the six core lists):

| Route | Notes |
|:---|:---|
| `GET /api/v1/{org_id}/journal-entries/ledger/` | the line-level ledger — paginated at the SQL level (`LIMIT`/`OFFSET` pushed into the query; `count` via `COUNT()`) |
| `GET /api/v1/{org_id}/journal-entries/entries/` | the entries list |
| `GET /api/v1/{org_id}/invoicing/documents/` | invoices / quotes / credit notes |
| `GET /api/v1/{org_id}/invoicing/contacts/` | contacts |
| `GET /api/v1/{org_id}/banking/payments/` | payments |
| `GET /api/v1/{org_id}/banking/bank-transactions/` | imported bank transactions |

**Rules (typed, tested):**

- `limit` must be an integer in **[1, 1000]** — anything else (garbage, 0,
  negative, > 1000) is a **400** error envelope naming the param (the P7/F-11
  convention; a caller's paging bug surfaces rather than silently clamping).
- `offset` must be a non-negative integer — garbage or negative is a 400.
- `next` is present only while `offset + limit < count` (null on the last
  page and beyond); `previous` is present whenever `offset > 0` (clamped to
  offset 0). Both URLs are absolute and **carry the caller's filter params
  unchanged** (paging inside a filtered set does not widen it).
- `offset` beyond the end returns an empty `results` page with the true
  `count` and a valid `previous`.
- The orders are deterministic total orders (the ledger by
  `-entry_date, -entry_number, line_number`; contacts by `name, id`; payments
  by `-payment_date, -created_at, -id`) — page boundaries cannot skip or
  duplicate a tied row.

**CLI recipes:**

```bash
# Page through the general ledger 50 rows at a time
curl -s -H "Authorization: Bearer $TOKEN" \
  "http://127.0.0.1:8000/api/v1/$ORG/journal-entries/ledger/?limit=50&offset=0"
# -> {"results": [...50 rows...], "count": 1234, "next": "...offset=50", "previous": null}

# Follow the envelope's own URL (jq extracts it verbatim)
curl -s -H "Authorization: Bearer $TOKEN" "$(curl -s -H "Authorization: Bearer $TOKEN" \
  "http://127.0.0.1:8000/api/v1/$ORG/journal-entries/ledger/?limit=50&offset=0" \
  | jq -r '.next')"

# The last partial page: 36 rows at limit 20 -> page 2 = rows 21-36, next=null
curl -s -H "Authorization: Bearer $TOKEN" \
  "http://127.0.0.1:8000/api/v1/$ORG/journal-entries/ledger/?limit=20&offset=20"

# Filters survive into next/previous (page inside the filtered set)
curl -s -H "Authorization: Bearer $TOKEN" \
  "http://127.0.0.1:8000/api/v1/$ORG/journal-entries/ledger/?limit=5&date_from=2026-01-01"

# A typed 400 names the param
curl -s -H "Authorization: Bearer $TOKEN" \
  "http://127.0.0.1:8000/api/v1/$ORG/journal-entries/ledger/?limit=0"
# -> 400 {"error": {"code": "validation_error", "message": "Invalid 'limit' — must be between 1 and 1000, got '0'."}}
```

The general-ledger web UI consumes this contract at page size 20 (the shared
TablePagination control). Gate truth at P24 (session 45): backend **995
passed / 0 failed / 5 skipped** (the +26 are the pagination contract gates) ·
frontend **660 vitest + 42 e2e** (42/42 live) · the production dependency set
clean at 0 advisories. See `docs/REMEDIATION_2026-11-27_P24_REPORT.md`.

## P25 Addendum — the pagination-contract hardening (2026-11-28, session 48)

**Two request-semantics tightenings on the P24 pagination contract** (both
typed 400s, both pinned by `tests/integration/test_pagination_p25.py`):

1. **`offset` now REQUIRES `limit`.** A well-formed `offset` without a
   `limit` used to be silently ignored (the response returned the FULL
   unpaginated set with the offset unused) — a caller that dropped `limit`
   mid-paging got no signal. It is now the typed 400 (explicit beats
   silent — the module's own convention; no existing consumer sends the
   shape):

   ```bash
   curl -s -H "Authorization: Bearer $TOKEN" \
     "http://127.0.0.1:8000/api/v1/$ORG/journal-entries/ledger/?offset=50"
   # -> 400 {"error": {"code": "validation_error",
   #         "message": "Invalid 'offset' — 'limit' is required when 'offset' is present ..."}}
   ```

2. **`offset` is capped at the Postgres bigint bound (2^63 − 1).** A
   validly-typed but astronomically large offset used to reach the SQL
   layer and detonate as an untyped **500** on the ledger
   (`DataError: bigint out of range`). It is now the typed 400 on every
   paginated surface; `offset=9223372036854775807` itself remains valid
   (an empty page with a live `previous`):

   ```bash
   curl -s -H "Authorization: Bearer $TOKEN" \
     "http://127.0.0.1:8000/api/v1/$ORG/journal-entries/ledger/?limit=10&offset=99999999999999999999"
   # -> 400 {"error": {"code": "validation_error",
   #         "message": "Invalid 'offset' — must be <= 9223372036854775807, got 99999999999999999999."}}
   ```

Everything else in the P24 addendum above is unchanged (the unpaginated
`{results, count}` default stays byte-identical; `?limit=&offset=` empty
strings behave as absent).

**One documented divergence (not a change):** the account typeahead
`GET /api/v1/{org_id}/coa/accounts/search/?q=…&limit=N` keeps its OWN
legacy `limit` semantics (a result CAP, not a page: default 10, no upper
bound, no offset, no next/previous) — it predates the P24 contract and
serves autocomplete, not paging. Do not follow the P24 recipes there; the
migration to the unified contract is registered for the search-surface
work.

Current gate truth (session 48): backend **1009 passed / 0 failed / 5
skipped** (the +14 are the hardening gates) · frontend **664 vitest + 42
e2e** (42/42 live INCLUDING the fresh-DB first-run proof) · the production
dependency set clean at 0 advisories. See
`docs/REMEDIATION_2026-11-28_P25_REPORT.md`.

## P26 Addendum — the Peppol transmission-log pagination (2026-11-28, session 50)

**The last unbounded backend list joins the P24 pagination contract.**
`GET /api/v1/{org_id}/peppol/transmission-log/` now accepts
`?limit=&offset=` with exactly the P24/P25 semantics (typed 400s on
garbage, the offset-requires-limit rule, the int8 cap), gains the
`-transmitted_at, -id` deterministic order (the tiebreaker — a paginated
boundary can no longer skip or duplicate tied rows), and computes its
three status counters in one query:

```bash
# The paginated mode — next/previous + the TOTAL count + the counters:
curl -s -H "Authorization: Bearer $TOKEN"   "http://127.0.0.1:8000/api/v1/$ORG/peppol/transmission-log/?limit=2"
# -> {"results": [ …2 rows… ], "count": 5,
#     "next": "http://…/transmission-log/?limit=2&offset=2",
#     "previous": null,
#     "pending": 2, "failed": 1, "completed": 2}

# No limit — the envelope stays BYTE-IDENTICAL to the pre-P26 shape:
curl -s -H "Authorization: Bearer $TOKEN"   "http://127.0.0.1:8000/api/v1/$ORG/peppol/transmission-log/"
# -> {"results": [ …all rows… ], "count": N,
#     "pending": P, "failed": F, "completed": C}   # no next/previous keys
```

Notes for CLI consumers: the counters count the FILTERED set when
`?status=` is supplied (the pre-P26 semantics, now pinned by test); the
`?status=` filter survives paging (the `next`/`previous` URLs carry it);
pinned by `tests/integration/test_peppol_pagination_p26.py` (12 gates —
the forced-tie walk, the counters in both modes, the P25 400 rules on
this surface).

**Frontend consumers (no API change, documented for completeness):** the
web app's invoices, contacts, payments, bank-transactions and quotes
pages now page server-side at page size 20 through this contract with
the shared TablePagination control; the invoices list search now goes
server-side through `GET …/invoicing/documents/?type=SALES_INVOICE&search=…`.

Current gate truth (session 50): backend **1021 passed / 0 failed / 5
skipped** (the +12 are the transmission-log gates) · frontend **686
vitest + 43 e2e** (43/43 live INCLUDING the fresh-DB first-run proof —
the new invoices-pagination spec stocks its own fodder) · the production
dependency set clean at 0 advisories. See
`docs/REMEDIATION_2026-11-28_P26_REPORT.md`.

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

## P33 Addendum — the currency-truth contract (2026-11-28, session 64)

**The contract change (byte-identical on the SGD default; truthful for
every other denomination):** three `currency` fields stopped hardcoding
`"SGD"` and now carry what the data says. Consumers that parse these
fields should treat them as data — never assume SGD.

| Surface | Pre-P33 | Post-P33 |
|:---|:---|:---|
| `GET /api/v1/{org_id}/reports/financial/?report_type=trial_balance` | `"currency": "SGD"` (hardcoded) | `"currency": <the org's base_currency>` |
| `GET /api/v1/{org_id}/reports/financial/?report_type=profit_loss` | `"currency": "SGD"` (hardcoded) | `"currency": <the org's base_currency>` |
| `GET /api/v1/{org_id}/reports/financial/?report_type=balance_sheet` | `"currency": "SGD"` (hardcoded) | `"currency": <the org's base_currency>` |
| `GET /api/v1/{org_id}/accounts/{account_id}/balance/` | `"currency": "SGD"` (hardcoded behind a TODO) | `"currency": <the account's own currency field>` |
| The InvoiceNow UBL (`POST /documents/{id}/send-invoicenow/`) | every amount element carried `currencyID="SGD"` (hardcoded) | every amount element's `currencyID` carries the document's currency (`DocumentCurrencyCode` and the amounts now agree) |

Notes for CLI operators:

- `base_currency` is the org's CHAR(3) ledger denomination (default
  `SGD`, settable at org creation and via the typed settings PATCH) —
  the three financial reports aggregate that ledger.
- The account's balance endpoint returns the ACCOUNT's own currency
  (the `coa.account.currency` column, default `SGD`) — for the rare
  mixed-denomination chart this is the honest per-account answer.
- `TaxCurrencyCode` in the Peppol UBL intentionally STAYS `SGD` — IRAS
  GST is accounted in SGD regardless of the document currency (the
  statutory posture, not an oversight).
- On an SGD-default org (the demo substrate) every one of these bytes
  is unchanged — the P33 verification re-ran the live contracts and
  confirmed byte-identity on the SGD paths.

## P34 Addendum — the credit-note Peppol structure + the ISO-4217 currency-input contract (2026-11-28, session 66)

**Two contract-visible changes (byte-identical on the SGD default; no
existing consumer breaks):**

### 1. The credit-note InvoiceNow XML now carries the full PINT-SG structure

`POST /api/v1/{org_id}/documents/{document_id}/send-invoicenow/` on a
`SALES_CREDIT_NOTE` previously transmitted header-only UBL (no parties,
no amounts, no lines) — and the transmission was marked FAILED before
reaching the access point (the CreditNote root was validated against the
Invoice XSD, which it can never pass). Post-P34:

- The credit-note UBL carries the full structure:
  `cac:AccountingSupplierParty`, `cac:AccountingCustomerParty`,
  `cac:PaymentTerms`, `cac:TaxTotal`, `cac:LegalMonetaryTotal` and the
  true UBL 2.1 line — `cac:CreditNoteLine` with `cbc:CreditedQuantity`
  (never `InvoiceLine`/`InvoicedQuantity` inside a credit note).
- Every amount element's `currencyID` carries the document's currency
  (the P33 truth, threaded through the credit-note path too).
- The validator dispatches by document type: a credit note is validated
  against the CreditNote XSD (`ubl-CreditNote.xsd`, target namespace
  `CreditNote-2`), an invoice against the Invoice XSD.
- The generated invoice AND credit note both validate clean against
  their schemas (verified live on real demo documents — pre-P34 the
  validation layer rejected every generated document, both types).

### 2. Currency inputs accept only active ISO-4217 codes (the typed 400)

| Surface | Pre-P34 | Post-P34 |
|:---|:---|:---|
| `POST /api/v1/organisations/` — `base_currency` | any string <= 3 chars (even 2-char "US") | an active ISO-4217 code (3 letters; case-insensitive, normalised to upper case) or the typed 400 field error |
| `PATCH /api/v1/{org_id}/` — `base_currency` | any 3-char string ("XYZ"/"SGE" accepted) | an active ISO-4217 code or the typed 400 field error |
| `POST /api/v1/{org_id}/bank-accounts/` — `currency` | any 3-char string | an active ISO-4217 code or the typed 400 field error |
| `POST /api/v1/{org_id}/payments/receive/` — `currency` | any 3-char string | an active ISO-4217 code or the typed 400 field error |
| `POST /api/v1/{org_id}/payments/make/` — `currency` | any 3-char string | an active ISO-4217 code or the typed 400 field error |

The 400 body is the standard DRF field-error shape:

```json
{"base_currency": ["base_currency must be an active ISO-4217 currency code (e.g. SGD, USD, EUR)."]}
```

Notes for CLI operators:

- A lower-case valid code is ACCEPTED and stored upper-cased
  (`"usd"` -> `"USD"`) — the normalisation is part of the contract.
- The allowlist (`common/currency.py`) covers the ACTIVE ISO-4217
  national currencies; the placeholder codes (`XXX` no-currency, `XTS`
  testing) and the supranational/precious-metal units (`XDR`, `XAU`,
  `XAG`, `XPD`, `XPT`) are deliberately excluded, as are withdrawn
  codes (`HRK`, `ANG`, `ZWL`, `SLL`, `VEF`).
- The bank-account UPDATE path does not accept `currency` (unchanged);
  the document currency is a database default, not an API input
  (unchanged).
- On an SGD-default org every rendered byte is unchanged — the P34
  verification re-ran the live contracts and confirmed byte-identity on
  the SGD paths (the invoice XML, the three reports, the account
  balance).
