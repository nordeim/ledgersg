# LedgerSG — Remediation Report (P8 Sprint: Reporting Truth & Quote Lifecycle)

**Date:** 2026-11-22 (session 16)
**Base commit:** `251b3577` (main)
**Plan:** `docs/REMEDIATION_PLAN_2026-11-22_P8.md`
**Source audit:** post-P7 audit re-verified in source with line numbers before planning
(three deep review passes — a P7-diff regression audit, a reports/quotes backend
surface mapping, a deferred-register validation — plus the repo-skill scanners per
`skills/skills-catalog.md`); every Critical/High finding re-confirmed against the
working tree before execution.
**Method:** TDD (RED → GREEN → full gate). Every production-code fix has a
regression test that failed for the documented reason before the fix and passes
after: **23 new backend tests + 20 new vitest tests + 2 new e2e specs, all RED
first.**

---

## 1. Verification Ledger (executed evidence)

Environment: rootless PostgreSQL 17 on :5432 (schema v1.1.0), Redis 8 on :6379,
Python 3.12 venv, Node with `@playwright/test` 1.58.2 + chromium 1208, Django dev
server (development settings) on :8000 + Next dev on :3000 during the live phase.
Operational incident (recovered, zero work lost): one test invocation without
`--reuse-db` triggered pytest-django's `create_test_db` against the DB named in
`.env` — the dev database was dropped and recreated empty; the schema was reloaded
from `database_schema.sql` (32 tables, 47 NUMERIC(19,4) columns verified) and the
full suite re-run green before any commit. Lesson registered: the local `.env`
points `DB_NAME` at the working database, so a non-`--reuse-db` invocation is
destructive — the documented invocation is the contract.

| # | Check | Command | Result |
|---|---|---|---|
| 1 | Baseline (pre-remediation, session start) | `pytest --reuse-db --no-migrations -q` | **624 passed, 0 failed, 5 skipped** at base `251b3577` — the documented P7 state reproduced exactly before any change |
| 2 | Baseline (frontend) | `npm test` / `npm run typecheck` / `npm run test:e2e` | 398/398, 0 errors, 9 passed + 12 gated skips — documented state reproduced |
| 3 | RED captures (all tasks) | per-task RED runs in the session log | GST permissions 2 (member could register/deregister — live), query-params 10 (500s / AssertionError), void contract 6 (OVERDUE void impossible, draft contradiction, allocation guard absent, filler reason, PAID guidance), send cc/bcc 2 + contract 1, blob envelope 1, financial reports 4 (stub TB, no tie-out, totals-only, 500 on garbage dates — KeyErrors + 500s), custom-account FK 3, aged endpoint 5 (404s), quotes 3 (link not persisted, QUO- prefix, filter key), quote PDF 2, fiscal close 2 (flag flips with open periods, dead route 200) — all failed for the documented reasons pre-fix |
| 4 | Full backend suite (post-remediation) | `pytest --reuse-db --no-migrations -q` | **0 failed, 647 passed, 5 skipped** (624 + 23 new − 22 deleted with the retired core-dashboard duplicate tests) |
| 5 | Invariant / security gates | `pytest tests/invariants -q` / `pytest tests/security -q` | **27 passed** / **53 passed, 3 skipped** (unchanged — no posture regressions) |
| 6 | Ruff (touched backend files) | before/after per file set | parity on every touched legacy file; all new files clean (two I001/E501 fixed on sight) |
| 7 | Frontend unit suite | `npm test` | **418 passed (418)** — 398 + 5 reports-hooks + 5 reports-page + 4 quotes-page + 1 payload-type + 1 org-propagation + 2 blob-errors + 1 send-payload |
| 8 | Frontend typecheck | `npm run typecheck` | **0 errors** |
| 9 | Frontend eslint (touched files) | `npx eslint <touched files>` | new files 0E/0W; parity on the one pre-existing auth-provider warning (untouched effect) |
| 10 | e2e (default, backend-less) | `npm run test:e2e` | **9 passed + 14 gated skips with reasons** (12 previous + the new reports + quotes specs) |
| 11 | e2e (full, live backend + Redis + bootstrapped dev DB) | `E2E_API_URL=… npm run test:e2e:full` | **23/23 passed** — first run 22/23: the reports spec used `isVisible()` (which does not wait) for the row/empty race; fixed with `expect.poll` and re-run green |
| 12 | Live API smoke (dev DB) | bootstrap: register/login → org → account 4100 (exact-code) → SR (effective_on) → contact → 3 invoices → **approve one (journal entry for the statements)** → **quote QT-00001** | DRAFT documents + 1 APPROVED + 1 quote; the P8 additions exercised the approve path and the QT- numbering live |
| 13 | Authorization spot checks | new integration tests | GST register/deregister without `can_manage_org` → **403** (was 200 — the P7 regression closed); aged/financial reports without `can_view_reports` → 403 |
| 14 | Contract spot checks | new integration tests | OVERDUE→VOID 200 + reversal (was a guaranteed 400 on every endpoint); PAID→VOID 400 with credit-note guidance; allocations-present → 400; quote convert → `related_document_id == invoice.id` (was never persisted); new quote numbered `QT-`; `?type=SALES_QUOTE` filters; garbage report dates → 400; `?limit=-1` → 400; year close with open periods → 400 naming them |
| 15 | Report truth spot checks | new tests + screenshots | TB returns rows/totals/balanced; BS ties out with retained earnings (79 == 0 + 79 on the fixture); custom REVENUE account visible in the P&L end-to-end; aged buckets sum to the dashboard's outstanding semantics on the same fixture |
| 16 | UI truth spot checks | e2e + vitest + VLM-verified screenshots | Reports tabs render real statements (rows or explicit empty states, zero dead Generate buttons); quotes list/new/detail live with the Convert action; the detail page shows QUOTATION framing with Quote #/Valid Until and gates the invoice-only surfaces |
| 17 | Screenshots | `docs/screenshots/41..46_*_session16.png` | 6 unique PNGs (md5-distinct, 42–72KB, 1440×900) — reports trial balance (**VLM-verified: real rows, Balanced badge, debits 2,616.00 == credits 2,616.00**), P&L, balance sheet, aged AR/AP, quotes list, quote detail (**VLM-verified: QUOTATION heading, Convert/Void/Send/PDF/Print, 4,000 + 360 GST = 4,360 matching the list total**) — captured through the real UI login path |
| 18 | Docs truth sweep | greps across README/PAD/CLAUDE/AGENTS/ledgersg_SKILL/DEPLOYMENT | counts match the executed evidence (1,088 = 647 + 418 + 23); DEPLOYMENT.md verified + P8 spot checks in the §11 checklist; lessons 26–30 appended to the skill; P8 patterns in AGENTS.md |
| 19 | `.env.example` verification | per-var cross-check | backend template covers every `config()` read (both comm flags were false positives — CORS is read via a multiline config call); web unchanged (NEXT_OUTPUT_MODE documented as reserved); P8 adds no env vars (all behavior is code + Django settings) |

Confidence labels: all rows **Verified** (executed in this environment). One
transient environment incident (the dev-DB drop, row context above) was fully
recovered before any commit; no work was lost.

---

## 2. What Was Fixed

### GST registration is manager-gated again (G-1 — the P7 regression)
The P7/F-10 `get_permissions()` refactor (gate PATCH, keep GET readable) was
applied to `GSTRegistrationView` — a view with no PATCH whose mutations are
POST/DELETE. Class-level `CanManageOrg` was removed, so any member could
register/deregister the org for GST. Restored class-level; the dead PATCH branch
deleted; tests cover member-403 / manager-200 on both verbs.

### The void contract is one contract (G-3, G-5, G-8)
`STATUS_TRANSITIONS` advertised DRAFT/PAID/OVERDUE→VOID while `void_document`
accepted only APPROVED/SENT/PARTIALLY_PAID — an OVERDUE invoice could be voided
through NO endpoint, and DRAFT/PAID users saw a Void button that always 400'd.
The accepted set now equals the advertised one (DRAFT is journal-safe: the
fiscal-period check applies only when an entry exists to reverse); PAID is
refused with credit-note guidance and dropped from the advertised map; a new
allocation guard refuses any void while `PaymentAllocation` rows exist (no more
orphaned allocations); the generic `/status/` endpoint requires a non-empty
reason exactly like the dedicated `/void/`. The frontend gates the Void button
on the accepted statuses and InvoiceNow on `status === "APPROVED"` (the backend
contract); the dialog copy describes the real semantics.

### Query-param hardening completed (G-2, G-9)
The P7/F-11 sweep missed siblings in the same functions: banking
`contact_id`/`bank_account_id` raw UUID casts and `LedgerView` raw dates (500s),
`parse_int_param` without bounds (`?limit=-1` → Django AssertionError 500), and
the financial-report dates (garbage → Django filter 500). All are 400s naming
the param now; the duplicate `ValidationError` import collapsed.

### Send-email delivers what it advertises (G-6); PDF errors surface (G-7)
`send_invoice_email_task` carries cc/bcc into `EmailMultiAlternatives` (both
were validated since P7/F-6 and silently dropped); the phantom `message` field
is removed from the serializer and the frontend payload (the notes travel in the
PDF — a field that promises behavior must deliver or disappear). `api.blob()`
resolves errors through the same shared `resolveErrorMessage()` as the JSON
path; `useInvoicePDF` gained `onError` → toast (a failed download was a silent
no-op).

### Financial reports are real (R-1, R-2, R-3, R-4)
- `report_type=trial_balance` delegates to `JournalService.get_trial_balance`
  (as-at bounded): lines + totals + balanced flag — the `{data:{}}` stub is gone.
- The balance sheet folds **retained earnings** (all-time revenue − expense to
  as_at) and reports `balanced` — the stub-era statement never tied out once P&L
  activity existed.
- P&L and BS expose per-account lines (code/name/amount per section, ordered).
- All three date params validate via `parse_date_param` (400 on garbage).
- The route is single-prefixed `/reports/financial/` (the historical
  `reports/reports/financial/` double prefix was un-guessable; no consumer
  existed).
- `create_account` links the coarse `account_type_ref` FK via the new
  `GROUP_TO_COARSE_TYPE` map (the groups' `category` is too coarse: COS's
  category is EXPENSE) — an org's own revenue account created through the API
  was invisible to its statements while seeded accounts showed up fine. TAX has
  no coarse counterpart (documented).

### Aged receivables & payables (R-5)
New `GET /reports/aged/?type=receivables|payables&as_at=` (`CanViewReports`):
per-contact rows with current/1-30/31-60/61-90/90+ buckets + section totals,
document-type/status semantics mirroring the dashboard's outstanding queries so
the surfaces reconcile. Credit-note netting is registered debt.

### The reports page is real (R-7, R-8)
The static Generate-button shell is replaced by a tabbed client wired to the
real endpoints — Trial Balance (rows + balanced badge), P&L (per-account lines +
net profit), Balance Sheet (sections + retained earnings + tie-out badge), GST
F5 (returns list, status badges, Compute/File actions), Aged AR/AP (bucket
tables) — with date controls and truthful loading/error/empty/403-permission
states. api-client gains the `reports` group + the gst returns family;
`use-reports.ts` ships seven hooks with toast + cache invalidation. The two
dormant hooks pointing at endpoints that never existed (`useGSTF5Compute` →
`/gst/f5-compute/`, `useRecentActivity` → `/audit-log/`) are deleted.

### Quotes are real (Q-1, Q-2, Q-3, Q-4, Q-4b)
- `convert_quote_to_invoice` persists `quote.related_document = invoice` (the
  old `converted_to_id` assignment set a transient attribute `save()` silently
  discarded — the link never reached the DB).
- `DOCUMENT_TYPES` prefixes align to the seeded `core.document_sequence`
  (SALES_QUOTE QT, PURCHASE_INVOICE BILL; issued numbers unaffected).
- `useInvoices` sends `type` — the param the backend reads (the old
  `document_type` key was silently ignored, so a quotes page would have listed
  every document).
- The quotes pages ship: list (Convert on DRAFT/SENT, truthful CONVERTED badge),
  new (the shared invoice form with `document_type: SALES_QUOTE`),
  detail (the shared client in quote mode — QUOTATION framing, payment/approval/
  InvoiceNow gated, Convert action), and `useConvertQuote` (invalidations +
  navigation to the created invoice).
- `generate_pdf` renders `quote_pdf.html` for SALES_QUOTE (QUOTATION framing,
  no TAX INVOICE labelling on quotes); invoices unchanged.

### Fiscal close + dead surface + settings round-trip (S-1, S-3, S-2)
- `FiscalYearCloseView` enforces the precondition its docstring carried as
  "TBD": all periods closed first, the 400 naming the open periods.
- The core dashboard duplicate is deleted (view, service, route, 2 test files) —
  the frontend and e2e only ever call `/reports/dashboard/*`; the registered
  M-15 duplication debt closes with zero remaining importers.
- The settings edit overlay resets only on the user's own save (GST
  register/deregister no longer wipes in-flight edits); `AuthProvider` exposes
  `refreshOrganisations()` and the update hook calls it — the sidebar org name
  updates after a rename without a reload.

## 3. Deferred Debt Register (explicit — nothing silently dropped)

Carried forward from P7 §18: H-02 base-currency reporting (reports remain
SGD-labelled); M-1 audit-event coverage beyond banking; M-10 CSRF hardening;
M-11 static-export security headers/CSP; M-14 Storecove authenticate semantics;
H-07 backend ruff debt (touched files stay clean); frontend eslint debt
(parity); F5 GST return rate-basis; A-10 stale root `requirements.txt`; GST
payment tracking (`pay_return` UI); invoice-form existing-contact picker;
Reg-11 tax-invoice labelling/Schematron; `status_history` synthesis;
ledger pagination (L — revisit with real data volume); invoice edit flow (needs
`update_line`); checkSession transport-vs-401; B6 list-envelope standardization;
account_type seed-column population.

New this sprint (registered, not dropped):
- **InvoiceNow backend quote gate** — `send_invoicenow` checks APPROVED but not
  document_type; the frontend gates quotes out (Peppol transmission is
  invoice-only); the backend type gate is polish.
- **GST review transition route** (`review_return` has no HTTP endpoint; filing
  works from COMPUTED — polish).
- **Aged AR/AP credit/debit-note netting** — invoice-based buckets ship first;
  netting needs an allocation model decision.
- **Quote lifecycle vocabulary** (ACCEPTED/REJECTED/EXPIRED + expiry date) —
  needs a DB enum change; P8 ships the DRAFT→SENT→APPROVED(converted) semantics
  the map defines.
- **Reports export** (PDF/CSV download of statements) — the page renders;
  export is a follow-up.
- **Trial-balance zero-activity accounts + fiscal-year mode** — the financial
  TB returns activity rows; the coa variant keeps fiscal-year filtering.
- **P&L/BS section labels are code-grouped** — sections expose revenue/expenses
  and assets/liabilities/equity without the sub-grouping
  (`bs_section`/`pl_section`) the account groups define; a richer statement is
  a follow-up.
- **Destructive test invocation hazard** — a non-`--reuse-db` pytest run drops
  the DB named in `.env` (pytest-django `create_test_db`); documented here and
  in the session log; the DEPLOYMENT.md invocation is the contract.

## 4. How to Verify (reproduction commands)

```bash
# Prerequisites: PG on :5432 (schema v1.1.0), Redis on :6379, backend venv +
# web node_modules, playwright chromium installed. ALWAYS --reuse-db
# --no-migrations (a bare run drops the .env DB — see §1 incident note).

cd apps/backend
pytest --reuse-db --no-migrations -q                     # 647 passed, 0 failed, 5 skipped
pytest tests/integration/test_void_contract_p8.py -q     # the G-3 state-machine suite
pytest tests/integration/test_gst_registration_p8.py -q  # the G-1 permission gates

cd ../web
npm run typecheck && npm test                            # 0 errors; 418 passed
npm run test:e2e                                         # 9 passed + 14 gated skips

# Full e2e against a live stack (development settings budget the run):
#   backend: python manage.py runserver 127.0.0.1:8000  (dev DB bootstrapped)
#   web:     npm run dev
E2E_API_URL=http://127.0.0.1:8000 E2E_DEMO_EMAIL=… E2E_DEMO_PASSWORD=… \
  npm run test:e2e:full                                  # 23/23

# Authorization check (the G-1 evidence):
#   a member whose role lacks can_manage_org POSTs {"gst_reg_number": …}
#   to /api/v1/{org}/gst/  → 403 (post-P7-regression: 200)

# Report tie-out check (the R-3 evidence): books with P&L activity must
# satisfy  assets == liabilities + equity + retained_earnings  with
# balanced == true on GET /api/v1/{org}/reports/financial/?report_type=balance_sheet
```

## 5. Commits

Conventional commits on `main`, **pushed incrementally after every task** via
`docs/ssh_git_wrapper_v3.py` (paramiko shim; remote ref verified on every push;
deploy key shredded after the final push):

1. `fix(core,api): GST registration manager-gated again; query-param hardening completed (P8/G-1, G-2)` — includes the financial-route single-prefix fix (R-1) and the financial date validation
2. `fix(invoicing,web): void contract aligned across the state machine (P8/G-3, G-5, G-8)` — carries the validated P8 plan document (first commit of the sprint)
3. `fix(invoicing,web): send-email delivers cc/bcc; PDF download errors surface (P8/G-6, G-7)` — note: the commit-message body lost two backtick-quoted words to shell substitution (`to`, `message`) — cosmetic, subject and evidence intact
4. `fix(reporting,coa): financial reports are real; custom accounts join them (P8/R-2, R-3, R-4)`
5. `feat(reporting): aged receivables and payables endpoint (P8/R-5)`
6. `feat(web): real reports page — statements, GST F5 lifecycle, aged AR/AP (P8/R-7, R-8)`
7. `fix(invoicing,web): quote conversion persists the link; prefixes match seeded sequences; type filter fixed (P8/Q-1, Q-2, Q-3)`
8. `fix(invoicing): quotation PDF template (P8/Q-4b)` + `style(tests): import order in test_quote_pdf_p8` (ruff autofix)
9. `feat(web): real quotes pages — list, create, convert, detail (P8/Q-4)`
10. `fix(core): fiscal-year close requires closed periods; dead core dashboard retired (P8/S-1, S-3)` — net −22 duplicate tests, +4 new
11. `fix(web): settings round-trip — edits survive refetch, org name propagates (P8/S-2)`
12. `docs: P8 truth pass — README/PAD/CLAUDE/AGENTS/ledgersg_SKILL + DEPLOYMENT verification + .env.example`
13. `docs(worklog): session 16 worklog, session log, P8 report + screenshots`
