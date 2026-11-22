# LedgerSG — Remediation Plan (P8 Sprint: Reporting Truth & Quote Lifecycle — Real Reports Page, Quote Create/Convert, P7-Regression Closure)

- **Date:** 2026-11-22
- **Branch:** `main` only (per repo convention)
- **Inputs:** post-P7 audit of the `251b3577` state. Findings gathered with the repo skills per
  `skills/skills-catalog.md` (`code-review-and-audit` standard mode via `audit_runner.py`,
  `code-quality-standards`, `diagnosing-bugs`, `e2e-testing-lessons`, `writing-plans`) plus three
  deep review passes (P7-diff regression audit, reports/quotes backend surface mapping,
  deferred-register validation). Every Critical/High finding below was re-verified against the
  working tree with line numbers by the lead before this plan was written. Scanner "criticals"
  outside `apps/` fall in the documented false-positive classes (`skills/` tree, test fixtures,
  docstrings, `Bearer ${token}` string building, hardcoded schema-name DDL) — same classes as
  P5 §0/P6 §0/P7 §0.
- **Method:** TDD (RED → GREEN → full gate), lint parity on touched files, conventional
  commits, `skills/` excluded from all checks/tests/compilation.
- **Baselines reproduced before any change (this session, exact):** backend **624 passed /
  0 failed / 5 skipped**, vitest **398/398**, typecheck **0 errors**, e2e default
  **9 passed + 12 gated skips** — the documented P7 state.

---

## 0. Audit Summary (the register this plan is built on)

P7 closed the API-truth gaps. The post-P7 audit has two halves: **(a) regressions and
loose ends the P7 sprint itself introduced or left**, and **(b) the registered P8
headline** — the reports/quotes pages are still static shells while real backend
capability exists (trial balance, P&L/BS, full GST F5 suite, quote create/convert).

| ID | Severity | Location | Finding (Verified) |
|---|---|---|---|
| G-1 | **Critical** (permission loosening, P7-introduced) | `apps/core/views/organisations.py:161-172` | The P7/F-10 `get_permissions()` refactor was applied to `GSTRegistrationView` — but this view has NO PATCH; its mutating verbs are POST (register for GST) and DELETE (deregister). Class-level `CanManageOrg` was removed, so **any org member can register/deregister the organisation for GST** post-P7 (verified: `git diff` shows the permission line removal in commit `ae543ec0`). The PATCH branch is dead code. |
| G-2 | **High** (F-11 incomplete in edited functions) | `apps/banking/views.py:211-212,462`; `apps/journal/views.py:374-377`; `common/query_params.py:34-40` | P7 converted the date params in these exact functions but left siblings raw: `contact_id=UUID(contact_id)` / `bank_account_id=UUID(bank_account_id)` (garbage → 500), `LedgerView` `date_from/date_to` still passed raw into filters (garbage → 500), and `parse_int_param` has no `min_value` (`?limit=-1` → Django "Negative indexing" AssertionError → 500; `?days=-5` flows through). |
| G-3 | **High** (state-machine contradiction) | `document_service.py:41-49,682` vs `views.py:303-313`; `invoice-detail-client.tsx:204,535` | `STATUS_TRANSITIONS` (served to clients by `ValidStatusTransitionsView`) advertises `DRAFT→VOID`, `PAID→VOID`, `OVERDUE→VOID`, but P7 routed the generic endpoint's VOID into `void_document`, which accepts only `APPROVED/SENT/PARTIALLY_PAID` → **an OVERDUE invoice can be voided through NO endpoint** (the dedicated `/void/` calls the same service), and DRAFT/PAID users see the Void button and get a guaranteed 400. Also: voiding a PARTIALLY_PAID document orphans its `PaymentAllocation` rows (nothing releases them), while the dialog copy claims "releases any payment allocations". |
| G-5 | Medium (contract inconsistency) | `invoicing/views.py:310` vs `:527-529` | The dedicated `/void/` requires a non-empty reason; the generic status endpoint silently defaults `"Voided via status transition"` — same operation, two contracts. |
| G-6 | Medium (advertised-but-dropped fields) | `invoicing/serializers.py:244-253` vs `document_service.py:792`, `tasks.py` | The new `InvoiceSendSerializer` validates `cc`/`bcc`/`message`, but `send_email` only forwards `to` — the Celery task never sees them. The frontend actively sends `message: invoice.notes` (`invoice-detail-client.tsx:222`) — silently discarded. |
| G-7 | Medium (silent failure) | `api-client.ts:271-277`; `use-invoices.ts` (useInvoicePDF) | `api.blob()` still reads only top-level `message`/`detail` — a backend envelope error (e.g. 404) surfaces as generic "Download failed: Not Found"; `useInvoicePDF` (wired in P7) has no `onError` → the user clicks PDF and nothing happens. |
| G-8 | Medium (untruthful gating) | `invoice-detail-client.tsx:201` | `canSendInvoiceNow = !isDraft && !isVoid` but the backend requires exactly `status == "APPROVED"` (`document_service.py:833`) — SENT/PARTIALLY_PAID/PAID/OVERDUE users get a guaranteed 400. |
| R-1 | **High** (500s on bad params) | `reporting/views.py:119-121` | `start_date/end_date/as_at_date` are raw strings into ORM filters — garbage raises Django's `ValidationError` at SQL-compile → generic 500 (the exact class P7/F-11 eliminated elsewhere; the fix pattern `parse_date_param` already exists). |
| R-2 | **High** (stub shipped as feature) | `reporting/views.py:130-132` | `report_type=trial_balance` returns `{"data": {}}` — a dead branch; a real trial balance exists in `JournalService.get_trial_balance` (date-based) and the coa service (fiscal-year-based). |
| R-3 | **High** (report doesn't balance) | `reporting/views.py:171-206` | Balance-sheet equity totals only explicit equity accounts — current-period earnings (revenue/expense balances) are never folded in, so `assets ≠ liabilities + equity` whenever P&L activity exists. Totals-only output (no per-account lines) besides. |
| R-4 | **High** (data invisibility) | `coa/services.py:237-247` vs `reporting/views.py:145-192` | Custom accounts created through the API set the `account_type` varchar but NOT the `account_type_ref` FK — and P&L/BS filter on `account_type_ref__code`. **An org's own revenue account (created via the UI) is invisible to its P&L/BS** (verified in dev DB: 102 seeded FK-typed vs 1 API-created varchar-only account). `ACCOUNT_TYPE_GROUPS[...].category` already maps groups → the coarse FK codes. |
| R-5 | **High** (missing capability the UI advertises) | `reports/page.tsx:48-50` vs backend (zero matches) | The reports page shows an "Aged Receivables" card, but NO aged endpoint exists anywhere (no buckets, no per-contact rows). Payables symmetric. The data (due_date, amount_paid, total_incl, contact) is all on `invoicing.document`. |
| R-7 | **High** (the P8 headline) | `reports/page.tsx` (82 lines), `api-client.ts:284-380` | The reports page is a static card grid with dead Generate buttons; the api-client has NO methods for `/reports/financial/`, `/accounts/trial-balance/`, or any `/gst/returns/*` endpoint. The full GST F5 suite exists (list/detail/generate/file/amend/pay — verified) with zero frontend. |
| R-8 | Medium (dead hooks) | `use-dashboard.ts:47-100` | `useGSTF5Compute` calls `/gst/f5-compute/` and `useRecentActivity` calls `/audit-log/` — **neither route exists** (404); both are unimported. |
| Q-1 | **High** (silent data loss) | `document_service.py:488` | `convert_quote_to_invoice` sets `quote.converted_to_id = invoice.id` — **no such field** (the model has `related_document_id`, verified in model + SQL). The quote→invoice link is never persisted (transient attribute, discarded by `save()`). |
| Q-2 | **High** (silent filter bug) | `use-invoices.ts:115` vs `invoicing/views.py:153` | `useInvoices` sends `document_type=…` but the backend reads `type` — any quotes page reusing the hook would list EVERY document. |
| Q-3 | Medium (prefix mismatch) | `document_service.py:29-37` vs `core.document_sequence` | Python hardcodes `SALES_QUOTE→QUO` and `PURCHASE_INVOICE→PINV`; the seeded sequences say `QT-` and `BILL-` (verified in dev DB). Quotes get `QUO-00001` while the DB config promises `QT-`. |
| Q-4 | **High** (the P8 co-headline) | `quotes/page.tsx` (56 lines) | Quotes page is a static shell (dead "New Quote" buttons). Backend supports quote create (documents endpoint, `SALES_QUOTE` in the create ChoiceField), list (`?type=SALES_QUOTE`), convert (`/quotes/convert/`), PDF, email — all verified. No quote detail page; the invoice detail client has one credit-note label branch only. |
| Q-4b | Medium (wrong document output) | `document_service.py:718-742` | `generate_pdf` renders `invoice_pdf.html` ("TAX INVOICE") for ALL document types — a quote emailed/printed as a TAX INVOICE is materially wrong. |
| S-1 | Medium (self-admitted gap) | `core/views/fiscal.py:59-98` | Year close flips the flag with only `year.is_closed` checked; its own docstring says "Requires all periods to be closed first (validation TBD)". Closing a year with open periods silently locks accounting history. |
| S-2 | Medium (settings round-trip) | `settings-client.tsx:39-42`; `auth-provider.tsx:75-107` | Unsaved org edits are wiped whenever `updated_at` changes (GST register/deregister included — not just saves); after a rename PATCH the sidebar keeps the old org name until F5 (provider useState unreachable from react-query invalidation). |
| S-3 | Medium (dead duplicate surface) | `core/views/dashboard.py` + `core/services/dashboard_service.py` + route + 2 test files | The core dashboard is dead (frontend + e2e only hit `/reports/dashboard/…`; zero importers outside its own route/tests — verified). Deleting it closes the registered duplication debt. |
| G-9 | Low | `banking/views.py:34-35` | P7 left a duplicate import (`ValidationError` imported twice under two names). |

De-escalated (recorded, no action): **DRAFT→SENT "bypass"** — by design: the transition map
explicitly allows DRAFT→SENT (quotes REQUIRE it as their `next_status`), no journal entry
exists at SENT by design, and approval (which posts the JE) is its own gated step; **GST
review route absence** — `FILEABLE_STATUSES` includes `DRAFT/COMPUTED` (verified), so the
F5 lifecycle is not blocked (register the route as polish); **scanner criticals** —
documented FP classes (verified: docstring examples, `Bearer ${token}` building, test
fixtures, dev fallbacks).

---

## 1. Task 1 (G-1): GST registration — manager gate restored on the real verbs

`GSTRegistrationView` has no PATCH and no GET: restore class-level
`permission_classes = [IsAuthenticated, IsOrgMember, CanManageOrg]` and delete the dead
`get_permissions()` override. RED (`tests/integration/` or the organisation API tests):
a member whose role lacks `can_manage_org` POSTs the GST registration → **403** (currently
200); the owner/manager → 201 + org serialized with `gst_registered=True`; DELETE → 403 for
the member.

## 2. Task 2 (G-2): query-param hardening completed

- `banking/views.py` PaymentListView + BankTransactionListView: `contact_id` /
  `bank_account_id` via `parse_uuid_param` (400 with the param name on garbage).
- `journal/views.py` LedgerView: `date_from`/`date_to` via `parse_date_param`.
- `common/query_params.py`: `parse_int_param(value, param, *, min_value=None)` — used with
  `min_value=1` for the coa search `limit` and `min_value=0` for the gst `days` probe.
RED: each site with garbage → 400 naming the param (currently 500); `?limit=-1` → 400
(currently a Django AssertionError 500); valid params unchanged.

## 3. Task 3 (G-3 + G-5 + G-8): the void contract, aligned end to end

Backend (`document_service.py` + `views.py`):
- `void_document` accepts **DRAFT, SENT, APPROVED, OVERDUE, PARTIALLY_PAID** (DRAFT is
  journal-safe: `void_document_entry` already returns `None` when no JE exists — verified).
  **PAID is refused** (the accounting-correct remedy for a paid invoice is a credit note,
  not a void) and `STATUS_TRANSITIONS["PAID"]` drops its `VOID` target so the advertised
  map matches the enforced one.
- New allocation guard inside `void_document`: if `PaymentAllocation` rows exist for the
  document → 400 "Unallocate payments before voiding" (no more orphaned allocations; the
  copy becomes truthful by making the operation refuse instead of lie).
- The generic status endpoint requires a non-empty `reason` for VOID (same contract as the
  dedicated `/void/`; the silent filler default is gone).
Frontend (`invoice-detail-client.tsx`):
- The Void button renders only for the accepted status set (DRAFT/SENT/APPROVED/OVERDUE/
  PARTIALLY_PAID); dialog copy corrected to the real semantics ("posts a reversing journal
  entry; payments must be unallocated first; cannot be undone").
- `canSendInvoiceNow` → `invoice.status === "APPROVED"` only.
RED: per-status backend transitions (OVERDUE→VOID succeeds — currently 400; PAID→VOID 400
with the credit-note message; DRAFT→VOID leaves no orphan rows; allocations-present → 400;
generic endpoint empty reason → 400); vitest for the button gating + InvoiceNow gating.

## 4. Task 4 (G-6): send-email delivers what the contract advertises

`send_invoice_email_task` gains `cc`/`bcc` params (passed to `EmailMultiAlternatives`);
`send_email` forwards them. The `message` field is REMOVED from `InvoiceSendSerializer`
and from the frontend payload (the notes are already in the PDF — the field promised
behavior that never existed; the serializer stops advertising it rather than growing a
half-feature). RED: task receives cc/bcc (mocked `.delay` asserts the kwargs); posting
`message` → ignored no-op (no longer a validated advertised field); vitest asserts the
page payload has no `message` key.

## 5. Task 5 (G-7 + G-9): PDF download errors surface

`api.blob()` parses the error envelope via the same extraction order as `handleResponse`
(shared helper); `useInvoicePDF` gains `onError` → toast with the parsed message. The
duplicate `ValidationError` import in `banking/views.py` is collapsed. RED vitest: blob
rejects with the envelope message ("Not found." from `{error:{message}}`, not "Download
failed: Not Found"); the hook surfaces a toast on failure.

## 6. Task 6 (R-1 + R-2 + R-3): financial reports are real

`FinancialReportView`:
- All three date params via `parse_date_param` (400 on garbage — the P7/F-11 pattern).
- `report_type=trial_balance` delegates to `JournalService.get_trial_balance(org,
  date_to=as_at)` and returns it in the financial envelope (`{report_type, as_at_date,
  currency, data: {lines, totals, balanced}}`) — the stub `{}` is gone.
- Balance sheet folds **retained earnings** (all-time revenue − expense balances up to
  `as_at`) into the equity section and reports `balanced` (assets == liabilities + equity
  incl. retained) — the statement ties out.
- P&L and BS gain **per-account lines** (code, name, amount) grouped by section, ordered
  by code, plus the existing totals.
RED: garbage dates → 400; TB returns the journal rows; a fixture with P&L activity
balances (assets − liabilities − equity − retained == 0); P&L exposes per-account lines
with correct amounts.

## 7. Task 7 (R-4): custom accounts join the reports

`AccountService.create_account` resolves `ACCOUNT_TYPE_GROUPS[account_type]["category"]`
→ the `AccountType` FK (REVENUE→REVENUE, REVENUE_OTHER→OTHER_INCOME, COS→COGS,
ASSET_*→ASSET, LIABILITY_*→LIABILITY, EQUITY→EQUITY, EXPENSE_*→EXPENSE/OTHER_EXPENSE;
TAX has no coarse FK → stays NULL, documented) and sets `account_type_ref`. RED: create a
REVENUE account via the API → `account_type_ref__code == "REVENUE"`; a journal line on it
appears in the P&L (currently invisible). Seeded/system accounts unchanged.

## 8. Task 8 (R-5): aged receivables & payables endpoint

New `GET /api/v1/{org}/reports/aged/?type=receivables|payables&as_at=YYYY-MM-DD`
(`CanViewReports`; dates via `parse_date_param`), mirroring the dashboard service's
document-type/status semantics (receivables: SALES_INVOICE + SALES_DEBIT_NOTE; payables:
PURCHASE_INVOICE + PURCHASE_DEBIT_NOTE; statuses APPROVED/PARTIALLY_PAID/OVERDUE as the
dashboard queries define; outstanding = total_incl − amount_paid > 0). One grouped query:
per-contact rows `{contact_id, contact_name, document_count, outstanding_total, current,
  d1_30, d31_60, d61_90, d90_plus}` bucketed by days past due at `as_at`, plus section
totals; `{type, as_at, results, totals}` envelope. Debit/credit-note netting is a
registered refinement (invoice-based aged views are the SMB standard). RED: fixtures with
documents in every bucket + a paid-off document (excluded) + cross-contact grouping.

## 9. Task 9 (R-7 + R-8): the reports page is real

- api-client: `reports.financial(params)`, `reports.aged(type, asAt)`, `gst.returns.list`,
  `gst.returns.detail`, `gst.returns.create`, `gst.returns.generate`, `gst.returns.file`.
- Hooks: `useFinancialReport(type, params)` (query), `useAgedReport(type, asAt)`,
  `useGSTReturns(year)`, `useGSTReturn(id)` + `useGenerateGSTReturn` /
  `useFileGSTReturn` / `useCreateGSTReturnPeriods` mutations with cache invalidation.
- `reports/page.tsx` rebuilt: report cards → real interactive statements rendered from
  the hooks — Trial Balance (as-at input + table + totals/balanced badge), P&L (date
  range + statement), Balance Sheet (as-at + statement with retained earnings + balanced
  badge), GST F5 (returns list with status badges, create-periods action, generate
  (confirm), file (confirm + reference input), detail with 15 boxes), Aged AR/AP
  (as-at + bucket tables), General Ledger (link to `/ledger`). Empty/loading/error
  states truthful; 403 (no `can_view_reports`) renders a permission state, never fake
  data. Zero-activity states say so.
- Delete the dead hooks `useGSTF5Compute` + `useRecentActivity` (404 endpoints).
RED vitest: each report renders from mocked data; the 403 state; GST actions call the
client methods; no imports of the deleted hooks remain. Gated e2e: open reports, generate
a TB, see the truthful result (rows or an explicit zero-state).

## 10. Task 10 (Q-1 + Q-3 + Q-2): quotes backend truth

- `convert_quote_to_invoice` persists the link: `quote.related_document = invoice` (the
  real field) — and the invoice's `reference` already carries the quote number.
- `DOCUMENT_TYPES` prefixes aligned to the seeded `core.document_sequence`: SALES_QUOTE
  `QUO`→`QT`, PURCHASE_INVOICE `PINV`→`BILL` (numbers already issued keep their stored
  value; only future formatting changes — no migration).
- `useInvoices` sends `type` (the param the backend reads) — the `document_type` filter
  key is fixed on the frontend, and a backend alias is NOT added (one contract, no
  dual keys).
RED: convert → quote.related_document_id == invoice.id (currently NULL); next quote
number starts `QT-`; `?type=SALES_QUOTE` lists quotes only (frontend hook test asserts
the param name).

## 11. Task 11 (Q-4b): quotation PDF template

`generate_pdf` branches on `document_type == "SALES_QUOTE"` → `invoicing/quote_pdf.html`
(title "QUOTATION", quote number/date/validity framing, same line table + totals, no
tax-invoice labelling). RED: quote PDF bytes differ from invoice PDF; template renders
the quote number (WeasyPrint render test beside the existing PDF tests).

## 12. Task 12 (Q-4): quotes pages are real

- `quotes/page.tsx`: list via `useInvoices(orgId, {type: "SALES_QUOTE"})` (the Task-10
  fix), table with number/contact/issue/due/total/status, Convert action on DRAFT/SENT
  rows, New Quote link.
- `quotes/new/page.tsx`: reuses the invoice form client with `document_type:
  "SALES_QUOTE"` + quote labels (heading, submit) — same POST documents endpoint.
- `quotes/[id]/page.tsx`: reuses the invoice detail client with a type-aware gating
  layer — for quotes: hide payment state + InvoiceNow + approve; show Send email,
  PDF (quote template), Convert-to-invoice (DRAFT/SENT), Void (Task-3 set).
- api-client `quotes.convert` + `useConvertQuote` mutation (invalidates quotes list +
  detail, navigates to the new invoice on success).
RED vitest: list renders quotes (and only quotes); New Quote posts `document_type:
  SALES_QUOTE`; Convert calls the client and invalidates; detail gating hides
  invoice-only actions for a quote. Gated e2e: create quote → convert → lands on the
  invoice with the reference link.

## 13. Task 13 (S-1 + S-3): fiscal close precondition + dead dashboard retired

- `FiscalYearCloseView`: 400 listing open period names when
  `year.periods.filter(is_open=True).exists()`; docstring updated (no more "TBD").
- Delete `core/views/dashboard.py`, `core/services/dashboard_service.py`, the
  `dashboard/` route in `core/urls/__init__.py`, and the two core dashboard test files
  (zero-importer verified; the live reporting service + its tests are untouched).
RED: close with an open period → 400 naming it; close after closing periods → 200; the
dashboard route 404s post-deletion (URL test sweep).

## 14. Task 14 (S-2): settings round-trip integrity

- `settings-client.tsx`: the edit overlay resets only in
  `updateOrganisation.onSuccess` (not on `updated_at` changes) — GST register/deregister
  no longer wipes in-flight org edits.
- `auth-provider.tsx` exposes `refreshOrganisations()` (re-fetches `auth.me`-equivalent
  org list, updates the in-memory state); `useUpdateOrganisation.onSuccess` calls it —
  the sidebar org name updates without a reload.
RED vitest: edits survive a background refetch with changed `updated_at`; rename →
provider state updated (mocked).

## 15. Task 15: docs truth pass, `.env.example`, screenshots, session log, report, worklog

- README / PAD / `ledgersg_SKILL.md` / AGENTS.md / CLAUDE.md: P8 milestone, new counts,
  lessons 26+ (wrong-view permission refactor; advertised-map vs enforced-map drift;
  serializer fields are promises; prefix config has two sources of truth).
- `docs/DEPLOYMENT.md`: verify every command against the P8 tree; add the reports/quotes
  pages to the smoke checklist; counts refreshed.
- `.env.example` re-verified var-by-var (no new env vars expected — all P8 behavior is
  Django settings and code; evidence recorded).
- Screenshots `docs/screenshots/41..46_*_session16.png` (continuing numbering): reports
  trial balance, reports P&L/BS, reports GST F5, quotes list, new quote form, quote
  detail (convert visible) — real UI login path, content-based waits.
- `docs/REMEDIATION_2026-11-22_P8_REPORT.md`, `docs/session_17.md` (session-16 log per
  the naming convention), `worklog.md` entry.

---

## 16. Verification Gate (definition of done for the sprint)

| # | Gate | Expected |
|---|---|---|
| 1 | `pytest --reuse-db --no-migrations -q` | all green (624 baseline + new, 0 failed) |
| 2 | `npm run typecheck` / `npm run lint` (touched) / `npm test` | clean / parity / all green |
| 3 | `npm run test:e2e` (no backend) | green, new specs gated with reasons |
| 4 | `npm run test:e2e:full` (live backend + Redis + bootstrapped dev DB) | all green incl. reports + quotes specs |
| 5 | Permission spot checks | GST register/deregister without `can_manage_org` → 403; aged/financial reports without `can_view_reports` → 403 |
| 6 | Contract spot checks | OVERDUE→VOID 200 + reversal; PAID→VOID 400 (credit-note message); allocations-present → 400; quote convert persists `related_document_id`; `?type=SALES_QUOTE` lists quotes only; garbage report dates → 400; `?limit=-1` → 400 |
| 7 | Report truth spot checks | TB returns rows/totals/balanced; BS ties out with retained earnings; custom REVENUE account visible in P&L; aged buckets sum to the dashboard's outstanding totals on the same fixture |
| 8 | Screenshots | ≥ 6 new non-empty unique PNGs (content-verified) |
| 9 | Docs sweep | no stale claims; DEPLOYMENT.md verified; `.env.example` matches the code |
| 10 | `git status` clean; commit set matches §17 | all on `main` |

## 17. Commit Plan (conventional commits, single branch `main`)

1. `fix(core): GST registration write actions manager-gated again (P8/G-1)`
2. `fix(api): query-param hardening completed — banking UUID filters, ledger dates, int bounds (P8/G-2)`
3. `fix(invoicing,web): void contract aligned across the state machine; InvoiceNow gate truthful (P8/G-3, G-5, G-8)`
4. `fix(invoicing): send-email delivers cc/bcc; message field dropped from the contract (P8/G-6)`
5. `fix(web,api): PDF download errors surface the backend envelope (P8/G-7)`
6. `fix(reporting): financial reports truthful — validated dates, real trial balance, balancing balance sheet, per-account lines (P8/R-1, R-2, R-3)`
7. `fix(coa): custom accounts carry their account_type reference (P8/R-4)`
8. `feat(reporting): aged receivables and payables endpoint (P8/R-5)`
9. `feat(web): real reports page — statements, GST F5 lifecycle, aged AR/AP (P8/R-7, R-8)`
10. `fix(invoicing): quote conversion persists the link; prefixes match seeded sequences; type filter fixed (P8/Q-1, Q-2, Q-3)`
11. `fix(invoicing): quotation PDF template (P8/Q-4b)`
12. `feat(web): real quotes pages — list, create, convert, detail (P8/Q-4)`
13. `fix(core): fiscal-year close requires closed periods; dead core dashboard retired (P8/S-1, S-3)`
14. `fix(web): settings round-trip — edits survive refetch, org name propagates (P8/S-2)`
15. `docs: P8 truth pass — README/PAD/CLAUDE/AGENTS/ledgersg_SKILL + DEPLOYMENT verification + .env.example`
16. `docs(worklog): session 16 worklog, session log, P8 report + screenshots`

(Adjacent tasks may fold where they share a RED→GREEN cycle; push incrementally after
each task — the workspace-reset safeguard.)

## 18. Deferred Debt Register (explicit, not silently dropped)

Carried forward from P7 §18 unchanged: H-02 base-currency reporting (reports remain
SGD-labelled); M-1 audit-event coverage beyond banking; M-10 CSRF hardening; M-11
static-export security headers/CSP; M-14 Storecove authenticate semantics; H-07 backend
ruff debt (touched files stay clean); frontend eslint debt (parity); F5 GST return
rate-basis; A-10 stale root `requirements.txt`; GST payment tracking (`pay_return` UI);
invoice-form existing-contact picker; Reg-11 tax-invoice labelling/Schematron;
`status_history` synthesis from timestamps; ledger pagination (L — revisit with real data
volume); invoice edit flow (needs `update_line`); checkSession transport-vs-401; B6
list-envelope standardization (the reports page documents the convention it uses);
account_type seed-column population; dashboard service duplication — CLOSED by Task 13.

New this sprint (registered, not dropped):
- **GST review transition route** (`review_return` has no HTTP endpoint; filing works
  from COMPUTED so the flow is not blocked — polish).
- **Aged AR/AP credit/debit-note netting** — invoice-based buckets ship first; netting
  credit notes against specific invoices needs an allocation model decision.
- **Quote lifecycle vocabulary** (ACCEPTED/REJECTED/EXPIRED + expiry date) — needs a DB
  enum change; P8 ships the DRAFT→SENT→APPROVED(converted) semantics the map already
  defines.
- **Trial-balance zero-activity accounts + fiscal-year mode** — the financial TB returns
  activity rows (journal-service semantics); the coa variant keeps fiscal-year filtering.
- **Reports export** (PDF/CSV download of statements) — the page renders; export is a
  follow-up.

## 19. Open decisions resolved by this plan

- **G-3 void semantics:** accept DRAFT/SENT/APPROVED/OVERDUE/PARTIALLY_PAID (draft-void
  is journal-safe — verified `void_document_entry` returns `None` without a JE); refuse
  PAID (credit note is the accounting-correct remedy; the advertised map is corrected to
  match); refuse any void while allocations exist (fail-closed beats orphaned rows).
- **G-6 message field:** removed, not wired — a field that promises behavior must either
  deliver or disappear; the invoice notes already travel in the PDF.
- **R-2 TB source:** the financial endpoint delegates to the journal service (date-based,
  pairs with the as-at semantics of P&L/BS, one response family for the reports page).
- **R-5 aged scope:** invoice+debit-note based per the dashboard's own semantics; credit
  netting registered; lean single endpoint with `?type=`.
- **Q-3 prefixes:** Python aligns to the seeded DB config (the schema file is the source
  of truth); already-issued numbers are stored and unaffected.
- **Q-2 filter key:** frontend fixed to `type` (the backend contract); no dual-key alias.
- **S-3 deletion:** the core dashboard is removed truthfully (dead duplicate) rather than
  left as a second implementation to maintain.
- **Test configs:** the existing `vitest.config.ts`/`playwright.config.ts` already match
  every new file location (`src/**/__tests__/`, `e2e/` with `E2E_API_URL` gating);
  configs are audited and unchanged unless a new file requires otherwise (evidence in
  the report).
