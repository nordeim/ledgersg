# LedgerSG — Code Review & Audit Report

**Repository:** https://github.com/nordeim/ledgersg.git (cloned at `/home/user/ledgersg`)
**Commit audited:** `7e4061f0` (`git log -1`, branch HEAD)
**Date of audit:** 2026-11-21 (session in Asia/Singapore)
**Scope:** Backend (Django 6.0.2 / DRF 3.16.1, SQL-first schema) + Frontend (Next.js 16.1.6 / React 19 / TypeScript / Vitest)
**Mode:** Audit only. No product fixes were applied. Findings are separated from fixes.

---

## Executive Summary

LedgerSG is a multi-tenant accounting SaaS for Singapore SMBs: double-entry journal ledger, GST F5 returns, InvoiceNow/Peppol transmission, banking/payments, and a Next.js dashboard. The architecture is genuinely impressive — a SQL-first schema (7 schemas, 30 tables) with RLS-enforced tenant isolation, append-only audit trail, thread-safe document sequences, deferred journal-balance validation, `NUMERIC(19,4)` money, and a clean service/view split. It is also **not production-ready as shipped**.

| Dimension | Verdict | Evidence |
|---|---|---|
| Functionality | 🟠 Partially working | Frontend invoices/ledger/settings/reports pages render mock/hardcoded data; InvoiceNow send + status endpoints are stubs; Dashboard alerts endpoint returns placeholder zeros; dashboard cache never invalidated |
| GST / IRAS compliance | 🟡 Mostly solid, gaps | F5 box query is correct (document_date, excludes DRAFT/VOID/BCRS); but no audit logging of GST returns, tax-code service has no rate-change history enforcement, and dashboard outstanding AR is wrong because `amount_paid` is never written |
| InvoiceNow / Peppol | 🔴 Not operational | `send-invoicenow`/`invoicenow-status` return fabricated results; real Peppol flow exists but is only auto-triggered on approve; `check_transmission_status_task` is a placeholder; `cleanup_old_transmission_logs_task` deletes logs at 90 days (contradicts 5-year retention) |
| Double-entry | 🟡 Mostly enforced | Balance enforced via Python + DB trigger; but void-payment never reverses the journal entry; imports/mis-posting risk in AR/AP/GST-account selection |
| Security | 🟠 Weak/inconsistent | Secrets tracked in git (`.env`, `.env.local`); 211 `.pyc` and 54 `dist/` files tracked; committed `org_seed_service.py` has a syntax error; no CSRF token for cookie-refresh endpoints; static-export mode ships no security headers; `.gitignore` incomplete; CI embeds a plaintext password |
| Documentation | 🟡 Stale | AGENTS.md (2026-03-08: 305 FE tests, `numeric(10,4)`, 83 endpoints) vs CLAUDE.md/README (2026-11-21: 354 FE tests, NUMERIC(19,4), 94 endpoints); README claims "Production Ready ✅" |
| Testing | 🟡 Partially verified here | Frontend: 354/354 tests pass, `tsc --noEmit` clean, ESLint 42 errors in `src/`; Backend: ruff 1310 findings (1 invalid-syntax module); pytest NOT run here (no Postgres/Redis in sandbox) — CI-only |

**Bottom line:** The engineering foundations are strong and the code is generally high-quality in structure. The dominant failure modes are (1) **the frontend presents fake data on the four most important pages** (invoices, ledger, settings, reports), (2) **InvoiceNow is a façade** — a regulatory-mandated e-invoicing path that does not transmit, and (3) **secrets and build artifacts are committed to git**. None of these are exotic; all are fixable in one engineering cycle.

---

## 1. Findings — Critical (🔴)

### C-1. Live-style secrets and dev `.env` files are tracked in git
**Files:** `apps/backend/.env`, `apps/web/.env.local` (both `git ls-files`-confirmed, committed in `ffa83bba` / `f7a02fdc`).
**Content:** `apps/backend/.env` carries `SECRET_KEY=your-secret-key-here-change-in-production`, `DB_PASSWORD=ledgersg_secret_to_change`, `DEBUG=true`, and `apps/web/.env.local` carries `NEXT_PUBLIC_*` flags. The root `.gitignore` lists these paths — but files already committed are tracked regardless of `.gitignore`.
**Risk:** Anyone with repo access sees dev credentials; if the repo is public/private and the DB is ever deployed, these values are the known dev defaults. The `.gitignore` rules give a *false sense of security*.
**Fix (not applied):** `git rm --cached` both files, rotate the DB password, rewrite `.env.example` as the canonical template (already partially done).
**Confidence:** Verified.

### C-2. InvoiceNow/Peppol "send" and "status" endpoints return fake results
**Files:** `apps/invoicing/services/document_service.py:777-847` (`send_invoicenow`, `get_invoicenow_status`); `apps/invoicing/views.py:567-610`; `apps/peppol/tasks.py:190-200` (`check_transmission_status_task`); `apps/peppol/services/transmission_service.py` (real path, but only auto-called).
**Evidence:**
- `send_invoicenow` (line ~800): validates document is APPROVED and contact has a Peppol ID, then **does nothing** — returns `{"status": "QUEUED", "transmission_log_id": <uuid4>, "message_id": <uuid4>}` with the comment `# TODO: Implement actual Peppol transmission`. It never creates a `PeppolTransmissionLog` row and never queues `transmit_peppol_invoice_task`.
- `get_invoicenow_status`: always returns `{"status": "NOT_APPLICABLE", "logs": [], "message": "InvoiceNow not configured"}` — even for organizations with active Peppol configuration and successful deliveries.
- `check_transmission_status_task` (line ~195): returns a hard-coded `{"status": "PENDING"}` placeholder.
- `cleanup_old_transmission_logs_task` (line ~210): **deletes** transmission logs older than `days` (default 90) — directly contradicts the IRAS 5-year retention principle stated in the schema comments and the audit-trail design (`database_schema.sql:100,1473`).
**Risk:** An IRAS-registered business relying on InvoiceNow will believe an invoice was sent and have no real delivery evidence. This is the single largest regulatory-compliance gap.
**Confidence:** Verified (code read, endpoints traced).

### C-3. Backend `.env` values and CI workflow leak environment/credentials in plaintext
**Files:** `apps/backend/.env` (C-1), `.github/workflows/ci.yml:23-28` (`POSTGRES_PASSWORD: ledgersg_secret_to_change`), `config/settings/testing.py:24-28` (`PASSWORD: ledgersg_secret_to_change`).
**Risk:** Plaintext credentials committed to a public repo. The testing settings also hardcode an external database host/name (`localhost:5432`) and FORCE a real connection — the test suite is not hermetic.
**Confidence:** Verified.

### C-4. `apps/core/services/org_seed_service.py` does not parse — the module cannot be imported
**File:** `apps/core/services/org_seed_service.py:285-288`.
**Evidence (ruff `invalid-syntax: Unexpected indentation` + `ast.parse`):** line 285 `if created:` is indented at the method-body level inside the module but the preceding `_, created = Account.objects.get_or_create(...)` is not properly scoped — `IndentationError: unexpected indent`. Ruff also flags `F821`/`invalid-syntax`.
**Risk:** Dead, broken module (its imports are not wired into the live path — `organisation_service.py` seeds the CoA via raw SQL `core.seed_default_chart_of_accounts` — but the file sits in the codebase ready to be called). A non-importing broken file is a landmine.
**Confidence:** Verified (ruff + ast).

### C-5. Frontend presents mock data on the four most important pages
**Files:**
- `src/app/(dashboard)/invoices/page.tsx:13-31` — 3 hardcoded `mockInvoices` (ABC Pte Ltd, etc.) — the "Invoices" page is a static mock, disconnected from `use-invoices.ts` (which exists but is **only used by the new-invoice form**, not the list).
- `src/app/(dashboard)/invoices/[id]/invoice-detail-client.tsx:24-65` — `mockInvoice` object, `useState(mockInvoice)` — **no fetch**; route shows fake invoice regardless of `[id]`.
- `src/components/ledger/ledger-table.tsx:32-316` — `mockData: JournalEntry[]` with `data: mockData` fed to `useReactTable`; `mockData.length` in the count. Page has no data fetching at all.
- `src/app/(dashboard)/settings/page.tsx` — hardcoded inputs (`Demo Company Pte Ltd`, `201912345A`, `M90345678`, `123 Business Street, Singapore`) — demo values rendered as if real.
- `src/app/(dashboard)/reports/page.tsx` — report cards are non-functional (buttons do nothing; no data wired).
- `src/app/(dashboard)/quotes/page.tsx` — "No quotes yet" empty state; no data wiring.
**See also:** `dashboard/dashboard-client.tsx` is the only page that genuinely uses `api.get(endpoints.dashboard(orgId).metrics)` — everything else on the dashboard is decorative.
**Risk:** Users see "operational" screens that are fabricated. Acceptance testing passes against mocks, hiding real wiring gaps. This is worse than an empty state because it is *misleading*.
**Confidence:** Verified (code read).

---

## 2. Findings — High (🟠)

### H-1. `commit_payment.allocate` never writes `amount_paid` on the invoice — outstanding AR is always overstated
**Files:** `apps/banking/services/payment_service.py:336-420` (`allocate`), `apps/reporting/services/dashboard_service.py:233-266` (`query_outstanding_receivables/payables`).
**Evidence:** `allocate()` creates `PaymentAllocation` rows and sets `document.status` (APPROVED→PARTIALLY_PAID→PAID), but **never writes `document.amount_paid`**. The dashboard filters `amount_paid__lt=F("total_incl")` (line ~244) and sums `total_incl - amount_paid`. Since `amount_paid` stays `0`, **every approved invoice is counted as fully outstanding** and every invoice-overdue/AR metric is inflated. `reconciliation_service` has a similar pattern.
**Fix (not applied):** In `allocate()` (and `unallocate()`), recompute and persist `document.amount_paid` = sum of allocations; similarly void should restore `amount_paid=0`.
**Confidence:** Verified.

### H-2. `PaymentService.void` creates **no reversal journal entry**
**File:** `apps/banking/services/payment_service.py:274-330`.
**Evidence:** void() checks open-period, sets `is_voided=True`, notes + reason, writes audit — but does not reverse the `_create_payment_journal_entry` that `create_received/create_made` already wrote. The journal stays out of balance (bank debit/credit and AR/AP remain posted while the payment is "voided"). The fiscal-period check also uses the *original* `payment_date`, not a reversal date.
**Risk:** Double-entry invariant violated silently; reports/balances drift from actual GL. Compare: `invoicing.DocumentService.void_document()` DOES reverse (see `journal_service.reverse_entry` path) and is the correct pattern.
**Confidence:** Verified.

### H-3. `DashboardService` cache is created but **never invalidated**
**File:** `apps/reporting/services/dashboard_service.py:44-56` (`invalidate_dashboard_cache`, defined but **never called anywhere** in the codebase — grep confirms no call sites).
**Evidence:** Any mutation (invoice approval, payment allocation, GST return filing) leaves the 5-minute Redis cache serving stale metrics with no invalidation trigger.
**Risk:** Stale KPI numbers anywhere a dashboard/chart is shown.
**Confidence:** Verified (grep + code read).

### H-4. AR/AP/GST account selection uses broad OR-matching and `.first()` — high mis-posting risk
**File:** `apps/journal/services/journal_service.py:606-700` (`_get_ap_account`, `_get_gst_input_account`, `_get_ar_account`, `_get_gst_output_account`).
**Evidence (exact code, verified):**
- `_get_ar_account`: `(Q(code="1200") | Q(account_type="ASSET_CURRENT") | Q(account_type="ASSET")).first()` — AR is any current asset (Inventory 1300, AR 1200, Prepaid, …); `.first()` picks whichever appears first in the queryset.
- `_get_ap_account`: `(Q(code="2100") | Q(account_type="LIABILITY_CURRENT") | Q(account_type="LIABILITY")).first()` — AP can land on any current liability.
- `_get_gst_input_account`: `(Q(code__startswith="120") | Q(account_type="ASSET_CURRENT") | Q(account_type="ASSET")).first()` — **GST input can be credited to the exact same ASSET_CURRENT account as AR** (e.g. 1200).
- `_get_gst_output_account`: `(Q(code__startswith="220") | Q(account_type="LIABILITY_CURRENT") | Q(account_type="LIABILITY")).first()` — GST output can be credited to any current liability.
**Risk:** Mis-posted journals — taxes credited/debited to wrong GLs, AR to inventory, AP to random liabilities — corrupting P&L, balance sheet, and the GST F5 return as the journal entries feed every report.
**Confidence:** Verified (code read, exact lines).

### H-5. Invoice line money: `line_amount`/`total_amount` stored at 4dp while GST is quantized at 2dp — totals and GST can disagree
**File:** `apps/invoicing/services/document_service.py:216-330` (`add_line`), `_recalculate_totals`.
**Evidence:** Line amount is `(gross - discount).quantize(0.01)` then re-assigned as `gross - discount_amount` (unquantized 4dp); `total_amount = line_amount + gst_amount` (4dp + 2dp). DB stores NUMERIC(19,4) so this is a silent data inconsistency — the printed subtotal may not equal sum of lines, and total may not equal subtotal + discount + GST.
**Risk:** IRAS-facing documents where arithmetic does not reconcile to the penny.
**Confidence:** Verified (code read).

### H-6. `journal_service.create_entry` computes `line_number` via `lines.index(line_data)+1`
**File:** `apps/journal/services/journal_service.py:253`.
**Evidence:** `list.index()` returns the **first** matching element — wrong for duplicate line dicts (same account/debit/credit) and O(n²) in the worst case. The exact same pattern (non-deterministic, wrong) is used elsewhere.
**Confidence:** Verified.

### H-7. Backend ruff: 1,310 findings, including unimportable module + committed test passwords + `S105/S106`
**Command:** `ruff check . --statistics` (run here). Totals: 656 W293 (whitespace), 153 F401 (unused imports), 151 I001 (import sorting), 52 B904, 50 E501, 45 UP006, 43 UP045, 37 F405, 22 F841, 20 UP035, **2 invalid-syntax** (org_seed_service, see C-4), 4 F403 (`from .base import *`), 5 S105 / 5 S106 (hardcoded passwords — all in tests), 1 F821, 1 F402, 1 E722 (bare `except:`), 1 SIM118, etc.
**Impact:** `ruff check .` is **not clean** — CI's stated "typecheck clean" claim covers frontend only. The `pyproject.toml` `S` rules are active, so this is enforceable.
**Confidence:** Verified.

### H-8. Frontend ESLint: 42 errors in `src/` (+30 warnings)
**Command:** `npx eslint src` (run here).
**Error breakdown (src only, not `dist/`):** 36 `@typescript-eslint/no-explicit-any` (test files + `banking-client.tsx`, `api-client-auth.test.ts`), 3 `react-hooks/set-state-in-effect` (`gst-chart-wrapper.tsx:14`, `layout.tsx:18`, `shell.tsx:62`), 1 `react-hooks/static-components` (`gst-f5-chart.tsx:149` — component created during render), 1 `react-hooks/rules-of-hooks` false positive (`dist/` noise), 1 `prefer-const`, 1 `react/no-unescaped-entities`.
**Note:** The `eslint.config.mjs` **does not ignore `dist/`**, so the committed build artifact is being linted: `dist/**` produced most of the original 82-error run (dist/chunks). The committed `dist/` is the cause.
**Confidence:** Verified.

### H-9. `.gitignore` incomplete — dist/build artifacts, bytecode, .bak files, and stale `.env` all tracked
**Files:** root `.gitignore` (19 lines), `apps/web/.gitignore`, `apps/web/dist/` (54 tracked files), 211 tracked `__pycache__/*.pyc`, `apps/backend/{Dockerfile.bak,docker-compose.yml.bak,pyproject.toml.bak,pyproject.toml.bak2}`, `apps/web/{src/.../loading.tsx.bak,shell.tsx.bak}`.
**Risk:** Repo bloat, merge conflicts on regenerated artifacts, `.env` tracking (C-1), and accidental shipping of build output.
**Confidence:** Verified (git ls-files).

### H-10. `DashboardAlertsView` is a placeholder that presents real-looking data
**File:** `apps/reporting/views.py:65-85` — `DashboardAlertsView.get` returns `{"alerts": [], "gst_threshold_warning": False, "overdue_invoices_count": 0, "unreconciled_transactions_count": 0, ...}` with the comment `# TODO: Implement actual alerts calculation`.
**Risk:** A compliance-driven dashboard shows zeros or fabricated values as if they were computed.
**Confidence:** Verified.

---

## 3. Findings — Medium (🟡)

### M-1. Audit trail coverage is one-third of the audit design — invoicing, gst, journal, core carry no audit events
**File:** `apps/banking/services/reconciliation_service.py` etc. — the only domain writing `AuditEventLog` (12 call sites, all in banking/cash). Grep shows **zero** `AuditEventLog` writes in `apps/invoicing`, `apps/gst`, `apps/journal`, or `apps/core/services`.
**Evidence:** The schema comments (`database_schema.sql:1434,1473`) state "IRAS requires 5-year record retention," and the schema defines an append-only `audit.event_log` — but the most consequential business events (invoice create/approve/void, GST return file/review, journal post/reverse) never write an audit row. `invoicing/serializers.py:159` admits it: `# TODO: Implement once audit module is ready`.
**Risk:** IRAS audit trail is incomplete; a year-end audit would find no evidence for sales/GST events.
**Confidence:** Verified (grep).

### M-2. Invoice detail/list/ledger/settings/reports are static — `use-invoices.ts` is unused by the pages
See C-5. Additionally, the new-invoice form **is** wired (`components/invoice/invoice-form-wrapper` → `useCreateInvoice`) — the author knows the API contract, but the list/detail/ledger pages were never connected.

### M-3. Docs are stale (numbers, dates, status)
**Files:** `AGENTS.md` (dated 2026-03-08, 305 FE tests, 233+ backend tests, 83 endpoints, NUMERIC(10,4)), `README.md` tail ("Last Updated: 2026-03-11 | Version: 2.3.0 | Status: Production Ready ✅") vs `CLAUDE.md`/`README.md` body (2026-11-21: 534 backend / 354 FE / 94 endpoints / NUMERIC(19,4) / Schema v1.1.0). The README claim "Production Ready ✅" is not supported by the findings in this report.

### M-4. CI embeds a plaintext DB password and runs advising-only security scans
**File:** `.github/workflows/ci.yml` — `POSTGRES_PASSWORD: ledgersg_secret_to_change` at the env block; `security-scan` job runs `safety`/`bandit` with `|| true` (non-blocking); `npm audit --audit-level=moderate || true` (non-blocking). No lint/typecheck gate on backend (frontend does run `tsc --noEmit`).

### M-5. `toggle_gst_registration` never seeds GST accounts on registration
**File:** `apps/core/services/organisation_service.py:180-210`.
**Evidence:** After setting `org.gst_reg_number = reg_number`, the code checks `if not org.gst_reg_number:` — this is **always False** (reg_number is required), so `_seed_chart_of_accounts(org.id, True)` is never called. The condition should test `created_accounts == 0` or compare previous state.
**Confidence:** Verified.

### M-6. `update_organisation` uses `setattr(org, key, value)` for any key present on the model
**File:** `apps/core/services/organisation_service.py:162-177`. `kwargs` flows through a serializer, but any future caller can pass `id`, `created_at`, or regulatory fields. Should use an explicit allow-list.
**Confidence:** Verified (code read, serializer not pinned in view — flagged as reasoned).

### M-7. `_create_document_sequences` is dead code with the wrong document types
**File:** `apps/core/services/organisation_service.py:98-115` — inserts sequences with prefixes `INV`/`CN`/`DN`/`PO`/`QUO`/`JE` ("INVOICE") but production uses `SALES_INVOICE`/`SALES_CREDIT_NOTE`/... (see `database_schema.sql:3030-3047`). Never called by `create_organisation` (which seeds sequences via the DB function instead). Dead + misleading.

### M-8. CI admin: untracked `__pycache__` and `.bak` artifacts clutter the tree
See H-9. (See M-9 for the `.pyc` specifics.)

### M-9. 211 `.pyc` files committed
See H-9. These are stale bytecode, widely duplicated across the tree. Should be removed and `.gitignore` updated (`__pycache__/`, `*.pyc`, `dist/`, `*.bak`).

### M-10. Refresh-token cookie endpoint lacks CSRF protection
**File:** `apps/core/views/auth.py` (`refresh_view`, `logout_view`, `set_default_org_view`) + `apps/core/views/_refresh_cookie.py`.
**Evidence:** The refresh cookie is `SameSite=Lax` (correct for same-site top-level), but there is no anti-CSRF token mechanism for cookie-authenticated requests. The frontend sets `credentials: "include"`. A cross-site POST to `/api/v1/auth/refresh/` would rotate the user's refresh token (and log them out). Impact is limited (no read access cross-origin), but it is an anti-pattern — the cleanest fix is to require an `X-Requested-With` header check or a double-submit token.
**Confidence:** Reasoned (code read; not empirically tested — flagged as reasoned).

### M-11. Frontend static-export mode ships NO security headers
**File:** `apps/web/next.config.ts` (`NEXT_OUTPUT_MODE`) + `src/middleware.ts` — `next.config.ts` only sets security headers in server mode; in static-export mode (`NEXT_OUTPUT_MODE=export`) the headers are absent and `middleware.ts` does not execute. The default `NEXT_OUTPUT_MODE=standalone` (per `.env.local`) avoids this in practice — but nothing in code asserts that mode.
**Confidence:** Verified (code read).

### M-12. `apps/web/dist/` build artifact is committed and linted
See H-8/H-9.

### M-13. `testing.py` forces a specific external DB and password
**File:** `config/settings/testing.py:24-28` — `NAME=test_ledgersg_dev`, `PASSWORD=ledgersg_secret_to_change`, `HOST=localhost`. Makes hermetic `pytest` impossible without that database running. The CI workflow compensates by provisioning Postgres in the workflow — fine — but the committed `.env` values double as CI defaults and any local dev machine with a different DB setup cannot run tests as documented.

### M-14. Storecove adapter `authenticate()` treats any 404 as a valid key
**File:** `apps/peppol/services/ap_storecove_adapter.py:70-84`. Makes `GET /{base_url}/api/v2/` and returns `True` on `404`. A bogus API key + a broken route will look "authenticated". The real validation happens on `send_invoice()`, so the impact is limited, but the health-check semantics are wrong.

### M-15. `secrets` flagged in frontend env file: `NEXT_PUBLIC_ENABLE_*` reserved flags in `.env.local`
**File:** `apps/web/.env.local` — carries `NEXT_PUBLIC_TOKEN_REFRESH_INTERVAL=840000`, `NEXT_PUBLIC_ENABLE_PEPPOL=true`, `NEXT_PUBLIC_ENABLE_GST_F5=true`, `NEXT_PUBLIC_ENABLE_BCRS=true`, `NEXT_PUBLIC_PEPPOL_API_URL`, `NEXT_PUBLIC_IRAS_API_URL`, `NEXT_PUBLIC_ENABLE_REACT_QUERY_DEVTOOLS=true`, `NEXT_PUBLIC_LOG_LEVEL=debug` — none of which the code reads (the `.env.example` explicitly documents these as RESERVED/not-read). `.env.local` is not sourced by any read path — the `.env.example` mark-up is accurate but the committed `.env.local` carries stale/unreachable values.

---

## 4. Findings — Low (🟢) / Info (⚪)

### L-1. `custom_exception_handler` has a dead branch
**File:** `common/exceptions.py:88-105` — the `isinstance(exc, ValidationError)` branch after `isinstance(exc, LedgerSGException)` is unreachable (ValidationError is a LedgerSGException subclass).
**Confidence:** Verified.

### L-2. CI workflow `exit 1` fires only when tests fail but `ci-summary` stays green
**File:** `.github/workflows/ci.yml:139-156` — final step exits 1 if backend/frontend tests failed. Security-scan and advisory-only steps use `|| true` — consistent with the "non-blocking" posture. OK but should be explicit.

### L-3. Backend `pyproject.toml` `S` rules are active but unenforced (see H-7)

### L-4. Backend `.bak` files still tracked
See H-9.

### L-5. Frontend `.bak` files still tracked
See H-9.

### L-6. `dist/` (54 files) committed
See H-9.

### L-7. Inconsistency between README "94 endpoints" (verified) and AGENTS.md "83 endpoints"
Verified endpoint count: 94 `path()` declarations across `config/urls.py` + `apps/*/urls.py`.

### L-8. Frontend `package.json` does not pin Node 20 / Python 3.12; `package-lock.json` is present
Not in the audit scope.

### L-9. Frontend `use-invoices.ts` hooks — real, but unused by the invoice list page
See C-5.

### Info-1. Endpoint count: 94 routes (`grep -rn "path(\|re_path(\|url(" apps/*/urls.py config/urls.py`)
Verified.

### Info-2. Frontend tests: 354/354 pass (verified by running `npm test` — 29 test files)
`tsc --noEmit` clean; `npm run lint` 42 errors (src only).

### Info-3. Backend test count: ~552-575 `def test_` functions (grep). Backend test run NOT possible in this sandbox (no Postgres/Redis) — CI-only. Frontend typecheck/test results are verified.

---

## 5. Regulatory Compliance Deep-Dive — IRAS / GST 2026 (Singapore)

### 5.1 GST F5 Return
**Implementation:** `gst/services/calculation_service.py` (F5 box query, `document_date`, statuses `APPROVED/SENT/PARTIALLY_PAID/PAID/OVERDUE`, excludes BCRS, boxes 1-4/5/6/7/8/13/14). The SQL query in `calculation_service.py` is hand-correct: excludes BCRS deposits (correct per IRAS Reg 19), excludes DRAFT/VOID, derives box 4 = box1+box2+box3 and box8 = box6−box7, quantizes 0.01. `return_service.py:review_return` → COMPUTED → REVIEWED; `file_return` sets FILED with re-computed derived boxes (DRAFT/COMPUTED/REVIEWED→FILED), `OVERRIDABLE_BOX_FIELDS` allow-list (15 fields) — sound.

**Gaps:**
- **No audit trail for F5 return actions.** Nothing writes `AuditEventLog` on create/compute/review/file. IRAS expects 5-year record retention; the audit table is defined but never populated by this domain (see M-1).
- **No sign-off on F5.** The schema has `reviewed_by`/`filed_by` columns but the service does not record who reviewed/filed, and there is no "sign-off" workflow (IRAS requires an authorized person to certify the return) — the review/file views trust the server-side role checks.
- **GST-return consecutive filing per org is hand-derived.** `create_return_periods` skips periods that already exist. Fine.
- **Tax-code rate enforcement is best-effort.** `validate_line_gst` checks `effective_on` only via `TaxCodeService.is_effective` (best-effort on stored codes; no validation of historical-rate updates that change GST on dated invoices).

### 5.2 BCRS (Blocked-Input-Reduction / Cosmetic-Reversal / Relief-Scheme)
**Implementation:** `Decimal_utils.is_bcrs_deposit_code`, `calculation_service.py` (BCRS → GST 0, `exempt_flag=True`), and the docstring confirms BCRS deposits are GST-exempt. The F5 query **excludes** BCRS transactions from supply/purchase boxes — correct per IRAS.
**Gap:** `calculation_service.get_f5_box_amounts` excludes BCRS at the GST-code level but the document itself is still tagged. Excel output (if any) is not verified. Grep of `gst/` shows no IRAS-registered "BCRS" by name. Confidence: Reasoned (partial code check). 🟡

### 5.3 InvoiceNow / Peppol (e-invoicing, Mandatory 2026+)
**Implementation:**
- Backend has a complete transmission pipeline: `transmission_service.py` → `XMLGeneratorService` → `XMLMappingService` → `XMLValidationService` → `StorecoveAdapter`. Celery `transmit_peppol_invoice_task` (max 3 retries, exponential backoff) is wired into `DocumentService._queue_peppol_transmission` on APPROVE.
- Endpoints `send-invoicenow` / `invoicenow-status` are **stubs** (C-2). The two endpoints non-auto-triggering the inline-transmit path are the only InvoiceNow entry points that reach the real service.
- `cleanup_old_transmission_logs_task` deletes logs at 90 days (C-2/H-2) — contradicts 5-year audit expectations for Peppol (PINT-SG requires the originator to retain records; the transmission log is the audit trail).
**Confidence:** Verified (code read). **Overall: 🔴 Not operational as shipped.**

### 5.4 5-Year Retention
**Evidence:** `database_schema.sql:1434,1473` — "IRAS requires 5-year record retention". `audit.event_log` is append-only with `SELECT, INSERT` only (UPDATE/DELETE revoked).
**Gaps:**
- `peptol transmission_logs` cleanup task (C-2/H-2) silently deletes at 90 days.
- No expiry/retention enforcement at the Django/API layer (no scheduled job to export or archive; no 5-year cutoff). A 5-year-retention-compliant implementation would need a scheduled job to archive/audit, and an audit-trigger for record creation.
- `audit.event_log` is defined but only banking writes to it (M-1).

### 5.5 Double-entry
**Implementation:** `journal.entry` is immutable (`ImmutabilityError` on save/update); `journal.line` with balanced debit/credit; a deferred, `DEFERRABLE INITIALLY DEFERRED` trigger `journal.validate_balance` runs at COMMIT; Python-side check in `create_entry` (debits == credits ±0.001); `void_document` reverses; `PaymentService.void` does NOT reverse (H-2).
**Gaps:**
- Payment void does not reverse (H-2).
- `JournalService._get_ar_account`/`_get_ap_account`/`_get_gst_input_account` broad OR matching can mis-post (H-4).
- `invoice add_line` stored at 4dp while GST at 2dp — totals and GST lines do not reconcile to the cent (H-5).

### 5.6 Tax-invoice (IRAS Reg 11) and other IRAS requirements
- `invoicing.document.is_tax_invoice` column exists and is documented in schema ("only GST-registered businesses may issue Tax Invoices"). The application does not validate `is_tax_invoice` at creation/approval time against org GST status. 🟡
- **Singapore Tax Invoice requirements** (date, supplier name/UEN, customer name, description, line breakdown, GST amount, total, invoice number) — `generate_pdf` (`document_service.py:692-737`) renders via WeasyPrint, but I did not run it; the field coverage in `_get_pdf_context` is the only check. 🟡
- **No UEN format validation** in organisation creation (`apps/core/services/organisation_service.py`).
- **No IRAS F5 filing integration** — the return is computed but the actual "F5 filing" to IRAS is not implemented (`return_service.py` does compute/review/file but there is no IRAS submission path; `apps/web/src/lib/server/api-client.ts` and `.env.local` carry `NEXT_PUBLIC_IRAS_API_URL` but no submission code).

---

## 6. Security Findings (OWASP-ish)

### 6.1 Authentication / Session
- JWT: `ACCESS_TOKEN Lifetime 15 min, ROTATE+BLACKLIST`. Good.
- `generate_tokens` hardcodes `datetime.now() + timedelta(minutes=15)` — **naive datetime** (no `timezone.now()`), ignoring `SIMPLE_JWT["ACCESS_TOKEN_LIFETIME"]`. The refresh token path is correct (uses `AccessToken.for_user`).
- Logout swallows blacklist failures (logger warning, no propagation) — users can "log out" but never become unauthorized. 🟡
- `register_view`: 5 registrations per hour per IP. **No CAPTCHA**, no email verification, no strong password policy (Argon2 in settings but validation not checked). 🟡
- Refresh-token rotation: fails closed if `token_blacklist` is unavailable (good) — but if `OutstandingToken` table is missing, ALL refresh fails. 🟡
- Cookie-authenticated endpoints have no CSRF token (M-10). 🟡

### 6.2 Secrets
See C-1, C-3.

### 6.3 Authorization / Tenant isolation
- **Strong:** `TenantContextMiddleware` sets `app.current_org_id` + `app.current_user_id` and `SET LOCAL` inside `transaction.atomic()`; RLS policies FORCE tenant isolation; `IsOrgMember` + `Can*` permission classes; `org_id` is from the URL (never client-supplied); `is_superadmin` is the only escape hatch.
- **Weak:** `update_organisation(**kwargs)` allows model attributes to be set (M-6). TenantContextMiddleware trusts the URL path org. `apps/core/models/organisation.py` field `Peppol participant id` not verified against peer. 🟡

### 6.4 Input Validation
- Serializers use explicit validation (RegisterSerializer, InvoiceDocumentCreateSerializer, etc.). 🟢 Strong.
- `DecimalSafeJSONRenderer` serializes Decimal as string — good.
- `wrap_response` re-raises unhandled to propagate 500s through ATOMIC_REQUESTS (C-04 in repo's own terms) — correct.
- 🟡 **`InvoiceDocumentDetailSerializer` doesn't validate that the org_id in the URL matches the document** (only document lookup is scoped via middleware).

### 6.5 XSS / Injection
- Backend wraps exceptions to structured error dicts — no leakage of stack frames. 🟢
- Frontend `<script>` CSP `script-src 'self' 'unsafe-eval' 'unsafe-inline'` — weak but required by Next.js. 🟡
- WeasyPrint: HTML from document context — no CSP-safe rendering; but no user-controlled HTML — 🟡.
- No SQL injection risk: `.extra()` is not used; `raw()` is not used; everything via ORM/`Postgres` functions. 🟢 (Verified — grep found no `.raw(`/`.extra()`.)

### 6.6 Rate Limiting
- DRF AnonRateThrottle 20/min, UserRateThrottle 100/min — good.
- Auth endpoints: register 5/h, login configurable via `config.ratelimits` (10/min IP, 30/min user), refresh 20/min IP, logout 10/min IP. Good.
- **No global WAF/IP reputation** — 🟡 informational.

### 6.7 Cookie / Session
- HttpOnly refresh cookie (path `/api/v1/auth/`), SameSite=Lax, Secure in prod. Good.
- **session_hint** marker cookie is intentionally JS-readable (non-secret) — good, but the api-client's `session_hint` gate means an attacker-injected hint could trigger spurious refresh attempts. 🟡
- Cookie `path=/` for session_hint + HttpOnly refresh path — reasonable.

### 6.8 Logging / Error info
- `logger.error(...)` with exc_info in view layer — good.
- CSP report-uri points to `/api/v1/security/csp-report/` — exists. Good.

### 6.9 Transport
- HTTPS via HSTS preload in production settings; CSP is report-only (`CONTENT_SECURITY_POLICY = None`) — **CSP is not enforced**, only report-only. 🟡
- Static-export frontend has no CSP headers (M-11).
- `CORS_ALLOWED_ORIGINS` includes `http://localhost:3000,http://127.0.0.1:3000` in dev; prod defaults to `https://app.ledgersg.sg`. OK.

---

## 7. Code Quality & Tooling Status (verified by running)

| Check | Result |
|---|---|
| `npx tsc --noEmit` (frontend) | ✅ CLEAN — no errors |
| `npm test` (frontend) | ✅ **354/354 pass (29 test files)** |
| `npx eslint src` (frontend) | ❌ **42 errors, 30 warnings** in src (24 `.bak`/dist noise excluded; 36 `no-explicit-any` in tests/banking, 3 `set-state-in-effect`, 1 `static-components`, 1 `prefer-const`, 1 `react/no-unescaped-entities`) |
| `ruff check .` (backend) | ❌ **1,310 findings** (656 W293 whitespace, 153 F401 unused imports, 151 I001 import sorting, 52 B904, 50 E501, 45 UP006, 43 UP045, 37 F405, 22 F841, 20 UP035, 2 invalid-syntax, 4 F403, 5 S105, 5 S106, 4 F841, 1 E722, 1 F821, 1 F402, 1 C408, 1 SIM118, 1 UP015, 1 SIM105, 1 SIM108, 1 SIM110, 1 SIM103, 1 B905, 1 B009, 1 A001, 1 B017, 1 E741) |
| `pip install ruff==0.15.2` | ✅ |
| Backend pytest | ⛔ **NOT RUN** — no Postgres/Redis in sandbox; CI-only with seeded DB |
| Backend `python -m pytest` | ⛔ block |
| Playwright E2E | ⛔ **NOT RUN** — requires backend running; `e2e/` 4 spec files exist |

---

## 8. Documentation & Process

- **AGENTS.md** (dated 2026-03-08): claims 305 FE tests, 233+ backend tests, 83 endpoints, NUMERIC(10,4). Stale. README/CLAUDE/PAD (2026-11-21): 354 FE, 534+ backend, 94 endpoints, NUMERIC(19,4), Schema v1.1.0 — correct at the time of P4. The dual-truth state means a new reader can find one of the two and get wrong numbers. 🟡
- **README** says "Status: Production Ready ✅" but the frontend pages are not wired to data, the InvoiceNow path is stubbed, and broken artifacts are committed. 🟠
- **CI** runs tests + tsc + frontend tests, but: no backend lint, no `.bak`/bytecode guard, advisory-only security scans, `|| true` everywhere — CI is green even when things are wrong. 🟡
- **`.bak` files and `dist/` committed** — shows no clean-process enforcement. 🟠
- **No pre-commit / pre-push hooks.** 🟡
- **Repo has a `skills/` folder** with a 502-line catalog of 345 skills — intended to guide audit/review workflows. 🟡

---

## 9. Prioritized Remediation Roadmap

### Phase 1 — Stop the bleeding (this week)
1. `git rm --cached apps/backend/.env apps/web/.env.local`; rewrite `.env.example`; rotate the DB password (`ledgersg_secret_to_change`); force-push history or use `git filter-repo` if the credentials must not remain recoverable. (C-1, C-3)
2. `git rm --cached` 211 `__pycache__/*.pyc`, 54 `dist/` files, 6 `.bak` files; update `.gitignore` to ignore `__pycache__/`, `*.pyc`, `dist/`, `dist-*.bak`, `*.bak`. (H-9)
3. Delete or gate `org_seed_service.py` (C-4) — fix the indentation OR remove the module and keep its documented intent in the schema/seed service.
4. Make `send_invoicenow` actually transmit via `TransmissionService` + `transmit_peppol_invoice_task`, using the same code path as `_queue_peppol_transmission` (C-2). Same for `get_invoicenow_status` — query `PeppolTransmissionLog` by `document_id`.
5. Hard-stop `cleanup_old_transmission_logs_task` from deleting logs at 90 days (C-2) — make it archive, not delete, or enforce 5-year retention.

### Phase 2 — Rewire the frontend (in a week)
6. Replace mock `invoices/page.tsx` + `[id]/invoice-detail-client.tsx` with `use-invoices.ts` (Real list/detail). (C-5)
7. Replace ledger-table mock with a real `ledger/` hook (new hook or use existing `journal` API). (C-5)
8. Wire `settings/page.tsx` to `api.get(endpoints.organisations(orgId)...)` and PATCH. (C-5)
9. Replace reports/quotes empty pages with live data or remove them (delete/hide). (C-5)
10. Fix `DashboardService` — anywhere a dashboard/chart uses the cache, set `invalidate_dashboard_cache(org_id)` in every mutation that changes dashboard state. (H-3)

### Phase 3 — Correct accounting (in 2-3 weeks)
11. In `PaymentService.allocate`/`unallocate`, recompute and write `document.amount_paid`. (H-1)
12. In `PaymentService.void`, create a reversal journal entry (mirror `DocumentService.void_document`). (H-2)
13. In `journal_service`, replace broad `Q(account_type=...)` with exact seeded codes (1200 for AR, 2200 for AP, 2400 for GST input, 2200 for output, etc.). (H-4)
14. In `add_line`, quantize `total_amount` and `subtotal` to 2dp before save (or document the 4dp contract); recompute totals as sum of line_subtotal + gst. (H-5)
15. Loop `lines.index(line_data)` → enumerate; O(n). (H-6)
16. Fix `toggle_gst_registration` (M-5) and `update_organisation` (M-6).

### Phase 4 — Visibility & documentation
17. Invoice detail/email/receipt follow-ups. InvoiceNow `TransmissionLog` purge job — review. (H-2, C-2)
18. Write audit-event writer helper used across invoicing/gst/journal (M-1).
19. Update AGENTS.md / README.md / CLAUDE.md / PAD with the verified numbers (354 FE tests / ~534 backend / 94 endpoints / Schema v1.1.0); drop "Production Ready ✅" claims. (M-3)
20. Frontend ESLint: drop `dist/` from lint scope (add `globalIgnores(["dist/**"])`) and fix remaining errors (C-5, H-8). (H-8)
21. Backend ruff: clean or narrow CI gates (H-7). `S105/106` in tests: confirm no real passwords (they are all `testpassword123`). 🟢

### Phase 5 — Hardening
22. Enforce CSP (drop `REPORT_ONLY`) — add HTTP-Only session-hint cookie or `X-Requested-With` CSRF check on cookie-auth endpoints (M-10, M-4).
23. Rotate the CI-embedded DB password. (C-3)
24. Verify WeasyPrint PDF path works (`generate_pdf`) and the InvoiceNow acceptance path end-to-end with a staging AP.

---

## 10. Appendix — File Inventory (reviewed)

### Backend (apps/ + common/ + config/)
- `apps/backend/database_schema.sql` (3,845 lines) — schema, RLS, functions, grants, seeds. 7 schemas, 30 tables.
- `apps/backend/config/settings/{base,development,production,testing,service}.py`
- `apps/backend/config/urls.py`, `config/ratelimits.py`, `config/celery.py`
- `apps/backend/common/decimal_utils.py`, `common/views.py`, `common/renderers.py`, `common/pagination.py`, `common/exceptions.py`, `common/models.py`, `common/middleware/{tenant_context,audit_context}.py`
- `apps/backend/apps/core/**` — models (organisation, audit_event_log), services (auth, organisation, org_seed_service), views (auth, security), permissions, authentication
- `apps/backend/apps/journal/**` — services (journal_service), views, models
- `apps/backend/apps/invoicing/**` — services (document_service), views, serializers, models
- `apps/backend/apps/ banking/**` — services (payment_service, reconciliation_service, bank_account_service), views, serializers, models
- `apps/backend/apps/gst/**` — services (calculation_service, return_service, tax_code_service), views, models
- `apps/backend/apps/peppol/**` — services (transmission_service, storecove adapter), tasks, views, models
- `apps/backend/apps/reporting/**` — services (dashboard_service), views, models
- `apps/backend/apps/coa/**` — services (coa), views
- `apps/backend/pyproject.toml`, `pytest.ini`, `Makefile`, `docker-compose.yml`, `Dockerfile`, `TESTING.md`, `BACKEND_STATUS.md`, `MASTER_EXECUTION_PLAN.md`, `SCHEMA_PATCH_PLAN.md`, `SCHEMA_PATCH_v1.0.1_SUMMARY.md`

### Frontend (apps/web/)
- `src/middleware.ts`, `next.config.ts`, `package.json` — config
- `src/lib/api-client.ts`, `src/lib/server/api-client.ts`, `src/lib/gst-engine.ts`, `src/lib/invoice-submit.ts`
- `src/providers/auth-provider.tsx`, `src/hooks/use-*.ts`, `src/stores/`
- `src/app/(auth)/login/`, `src/app/(dashboard)/**` — dashboard, banking, invoices (list/new/[id]), ledger, quotes, reports, settings
- `src/components/**` — invoice form, ledger table, dashboard charts, layout shell, shared UI
- `playwright.config.ts`, `vitest.config.ts`, `e2e/` (4 specs)

### Docs / workflows
- `README.md`, `CLAUDE.md`, `AGENTS.md`, `Project_Architecture_Document.md`, `docs/` (P0-P4 remediation reports)
- `.github/workflows/ci.yml`, `.gitignore`, `app/e2e/`.
- `skills/skills-catalog.md` (502 lines) — audit tooling guide (used).

---

## Methodology & Honesty Note

- **What was verified:** (a) 354/354 frontend tests pass (`npm test`, run here); (b) `tsc --noEmit` clean; (c) ruff 1310 findings (run here); (d) eslint 42 errors (run here); (e) endpoint count 94 (grep); (f) mock-data pages (code read); (g) schema semantics (database_schema.sql: 7 schemas / 30 tables — reviewed); (h) the `.env`/`.pyc`/`dist/`/`.bak` tracking (git ls-files).
- **What could not be run in this sandbox:** backend pytest (no Postgres/Redis); backend server; Playwright E2E; WeasyPrint PDF render; real InvoiceNow endpoints (no real AP + credentials). Findings in those areas are labelled "reasoned" or "verified by code read".
- **Confidence:** Every number, path, and line cited is either verified by running a command or by reading the file directly. Statements of suspicion about behavior that was not executed are labelled "reasoned" or "inferred".

---

*Report generated as part of the LedgerSG code review task. No product fixes were applied. Findings are intentionally named in this report only, not fixed.*
