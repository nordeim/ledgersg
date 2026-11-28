LedgerSG Project Status — Comprehensive Summary
Executive Overview
LedgerSG is a production-grade, double-entry accounting platform purpose-built for Singapore SMBs with IRAS 2026 compliance. The platform has undergone significant development across multiple phases, achieving enterprise-grade security, comprehensive test coverage, and a complete banking UI.
---
Current Status (2026-11-27 — P24 remediated; see the sprint-patterns sections
at the bottom of this file for P0–P24 and the README status table for the
live numbers. The detailed sections between this header and the P0-patterns
appendix are HISTORICAL — written 2026-03-08; treat their counts as
superseded.)

Current truth (all gates executed and green, session 74 / P38):
- Backend: pytest 1146 passed / 0 failed / 5 skipped (1151 collected)
  (+12: the P38 gates — the credit-note InvoiceNow gates + the Celery
  web-process wiring; +20: the P37 gates — the credit-note reference
  truth + the reason note; +25: the P36 gates — 13 Schematron arithmetic
  rules, 12 tax-currency/Percent)
- Backend lint: the closed ruff classes at **0** across the WHOLE tree
  (the P30 production closure + the P31 extension + the P32 set:
  W291/W293 whitespace, I001 import order, F401 unused imports,
  F403/F405 the settings star imports, B904 exception chaining, the
  dead-code/shadow/name/suppress classes — production 277 → 211 → 148,
  tests 379 → 158 → 73 [the honest re-measured baseline; the P31
  report's 157 under-counted by the W605 the P32 sprint closed];
  `make lint-mechanical` + the CI step gate the extended class set
  over production + tests — unchanged by P35/P36: no lint class touched)
- Frontend: vitest 698/698 (85 files, on vitest 4.1.12 — the P23
  advisory closure), coverage green at the RAISED per-glob ratchets
  (the P29 honest-ratchet completion: lib 73/54/78/75, hooks
  55/47/51/55 [the branches floor sat 15 points below the measured
  51.16], app 75/65/73/76, components 83/76/69/84, providers
  63/63/58/62, plus the NEW src/shared tier 73/62/76/73 — the P20
  tier set had missed the shared primitives), tsc --noEmit 0 errors,
  whole-tree eslint **0 errors / 0 warnings**,
  npm audit **0 across dev+prod** (the web tree untouched by P35/P36)
- P34 headline: the credit-note Peppol truth — a TRIPLE defect, all
  reproduced (generate_credit_note_xml emitted header-only UBL while
  the mapper supplies parties/totals/lines for every document type;
  the transmission service validated the CreditNote root against the
  INVOICE XSD, which a CreditNote can never pass — every real
  credit-note transmission was doomed to FAILED; the CreditNote XSD
  carried the Invoice-2 targetNamespace copy-paste artefact) PLUS the
  mid-sprint discovery the TDD RED gate caught: the generated INVOICE
  also failed its own XSD — the single-file XSDs declared the cbc/cac
  children as LOCAL elements in each root's target namespace and never
  declared the amount attributes (currencyID/unitCode/schemeID) at
  all, so the validation layer was DECORATIVE for both paths. Both
  XSDs restructured into the true three-namespace UBL shape (NEW
  ubl-CommonBasicComponents-2.xsd + NEW
  ubl-CommonAggregateComponents-2.xsd + both root XSDs as ref-based
  sequencers); the generated invoice AND credit note now validate
  clean (is_valid=True, 0 errors — verified live on real demo
  documents). Plus the ISO-4217 currency-input truth: the shared
  common/currency.py active-code allowlist on the five input surfaces
  (org create/PATCH base_currency, bank-account create currency,
  payment receive/make currency — a typo like "XYZ"/"SGE" or a
  2-char "US" on the create path is now the typed 400 field
  error; a lower-case "usd" normalizes to "USD")
- P33 headline: the currency-truth closure — the Peppol amount
  currencyID thread (XMLGeneratorService hardcoded currencyID="SGD"
  on all 11 amount elements while the mapper flows the document's own
  currency into DocumentCurrencyCode — a USD/EUR invoice transmitted
  internally inconsistent UBL; the existing tests only ever built SGD
  payloads, the fixture masked the hardcode), the financial-reports
  denomination (the three report views now read org.base_currency,
  not a hardcoded SGD — the invoice PDF already rendered the truthful
  value), and the account-balance currency (the account's own
  currency field, retiring the literal TODO). Byte-identical on the
  SGD substrate; truthful for every other denomination
- P32 headline: the dead-code & shadow-fragility closure + the
  tests-tree residual — the 3 dead service-seam bindings retired
  (void's never-read `reversal`, transition's `old_status`, approve's
  guard-query `fiscal_period`), the F402 `status` shadow renamed in
  DocumentSummaryView, the journal E741/A001 renames, the SIM105 ×10
  suppress conversions, the B017 tightening that exposed a
  vacuously-passing retry test (the blind assert swallowed the
  db-blocker RuntimeError), the S608/E402 documented suppressions;
  the F811 fixture class closed architecturally (payment_fixture →
  tests/integration/conftest.py, the 7 cross-module import blocks
  deleted, a NEW no-import resolution spec pinning the contract);
  production ruff 211 → 148, tests 158 → 73; the extended closed-class
  ratchet (+25 classes) in `make lint-mechanical` + CI
- P30 headline: the ruff mechanical closure — the registered
  928-finding production batch's mechanical classes closed 650 → 0
  (whitespace ×378, import order ×122, unused imports ×121 across 51
  files, the Django split-settings star imports ×29 documented via
  per-file-ignores — the pass-through contract); the register's
  blind-`--fix` trap defused. Plus the fourth-surface walk completion:
  reconcile()/unreconcile() responses now JOIN bank_account instead of
  walking it (the locked fetches chain select_related; byte-identical
  payloads, pinned by query-count gates + the live round-trip); and
  the mechanical-class lint ratchet (`make lint-mechanical` + the CI
  step — a gate nobody runs is a rubber stamp)
- P29 headline: the detail-view N+1 closure — the three detail seams
  (document detail, journal entry detail, payment detail) fetched
  their row with a plain `.objects.get(...)` while the serializers
  walked the related FKs: the invoice/quote detail walked account +
  tax_code on EVERY line (a 5-line invoice paid 14 queries where 3
  would do, across 8 serialising call sites incl. the PDF context),
  the journal entry detail walked account on every line (the
  registered "journal detail N+1"), the payment detail walked
  contact + bank_account. Fixed at the service seam (the same seam
  as the P28 list push-down): the contact rides the document SELECT,
  the lines arrive in ONE joined SELECT carrying account + tax_code,
  the payment joins its related rows — the payloads byte-identical,
  pinned by 3 NEW query-count gates (a detail request issues a
  bounded, line-count-independent set of SELECTs; the RED runs
  proved the per-line walks)
- P28 headline: the SQL-level push-down — the four service-driven
  list surfaces (contacts, documents [invoices AND quotes], payments,
  bank transactions) materialised the ENTIRE filtered set in Python
  on every request (`return list(queryset...)`) and the views
  Python-sliced + `len()`-counted, so every 20-row page of an org
  with N documents fetched all N rows (the P24 envelope paged the
  RESPONSE, not the QUERY). Fixed: the services return lazy
  querysets; the views count via SQL COUNT(*) and page via SQL
  LIMIT/OFFSET — the envelope byte-identical, pinned by 4 new
  query-level gates (a paginated request issues a LIMIT-bounded
  SELECT at the requested page size + a COUNT query; the RED runs
  proved the unbounded fetch)
- P27 headline: the pagination state-machine truth — the P26
  search-debounce effect's MOUNT-run called setOffset(0)
  unconditionally, so a Next click inside the ~600ms window (doubled
  under StrictMode) silently reverted to the cached page 1 (no
  refetch, no feedback — the click lost; the serial full-run e2e lost
  the race deterministically at 42/43 while isolation passed it;
  proven by trace: the click dispatched, the offset=20 request
  answered 200, then the UI back at page 1 with NO third request —
  the cache-served revert signature). Fixed: the page restart fires
  ONLY on a debounced VALUE CHANGE (the last-committed-value ref
  compared inside the timer callback); the org-switch offset reset
  extended to all five P26 surfaces (the P25/FE-L3 render-time
  pattern); the banking filter-change offset reset (the filters-prop
  identity compare + a stable NO_FILTERS default) — all pinned by
  real-hook transport-URL specs. PROVEN: fresh DB → one bootstrap →
  the FIRST e2e:full = 43/43, 0 skipped, deterministic
- P26 headline: the frontend pagination wiring + the Peppol transmission-log contract (see the Previous Milestones in README.md — every remaining list surface server-side paged at size 20; the invoices search migrated server-side; useContacts returns the envelope; the Peppol log joined the ?limit=&offset= contract)
- P25 headline: the fresh-substrate first-run truth + the pagination
  contract hardening — the §9 bootstrap's invoice/credit-note steps had
  been silently broken since P14/M-4 made tax_code_id required (the
  POSTs failed behind `|| true` guards, printing "invoice OK ()" with
  an empty id); a fresh host reproduced the documented 42/42 as
  40P/1F/1S. Fixed: the SR tax code on every substrate line (failures
  LOUD) + the step-4c fodder top-up (≥ 36 ledger lines, ≥ 4 APPROVED
  invoices, idempotent). PROVEN: fresh DB → one bootstrap → the FIRST
  e2e:full = 42/42, 0 skipped. Plus the int8 offset cap (a >2^63−1
  offset was an untyped 500), offset-requires-limit (was silently
  ignored), the WCAG 2.5.3 pagination labels, the beyond-end page
  keeping its controls, the render-time org-switch reset
- P24 headline: the server-side list pagination — the additive
  `?limit=&offset=` contract on the six core list surfaces (the
  general ledger at the SQL level: count() + the queryset slice; the
  entries, documents, contacts, payments and transactions lists at
  the envelope level); with `limit` absent the response stays
  byte-identical {results, count} (every existing consumer keeps
  working); with it the envelope gains next/previous (absolute URLs
  carrying limit+offset+the caller's filters) and count reads as the
  TOTAL matching rows; garbage limit/offset are typed 400s; the
  ordering tiebreakers (contacts name,id; payments/transactions with
  the id final key) close the cross-page skip/dup hazard; the shared
  accessible TablePagination control + the useLedger page identity
  in the queryKey (the cache-paging trap) drive the general-ledger
  UI at page size 20
- P23 headline: the mobile-nav drawer-slide transition truth (the
  one real Tailwind v4 bug the 13 prior functional settlements missed:
  v4 animates translate-x-* through the STANDALONE `translate` CSS
  property and the drawer's transition list omitted it — the 300ms
  slide never interpolated; fixed to
  `transition-[transform,translate,visibility]` and pinned by its own
  compiled-CSS gates) + the vitest critical-advisory closure
  (^4.0.18 → ^4.1.12; both criticals closed, 0 critical remaining,
  the 17 residual findings all dev-tier)
- P21 headline: the list-envelope unification ({results, count} on
  EVERY list surface incl. the former bare-array /auth/organisations/ —
  the prerequisite for pagination; the vacuous RLS isolation assert
  fixed with it), the InvoiceNow invoicenow_sent_at evidence stamp (the
  restore-to-SENT branch was dead code), the on-commit cache truth (the
  dashboard + balance invalidations wait for the commit; void_document
  + manual entries invalidate the dashboard too), the bank-account
  default-flag locks, the ValidateBalance typed-400 body, the banking
  a11y batch (the Reference name, the keyboard-reachable CSV import,
  the loader live regions, the payment-card keyboard contract, the
  reconcile aria-pressed), the timezone-safe date helpers
- E2E: 43 specs (11 always-green + 32 backend-gated); live run 43P/0F/0S
green INCLUDING the fresh-DB first-run proof (re-proven session 50 /
P26: drop + recreate the dev DB → one §9 bootstrap run → the FIRST
test:e2e:full = 43/43, 0 skipped — the new invoices-pagination spec
stocks its own fodder through the public API, the P25 lesson applied
at design time); CI runs the always-green 11
  (P18/CFG-L1)
- Production-CSP smoke (P16/FE-C1): 5/5 — nonce served, hydration
  happened, zero violations (the gate class the dev suite cannot cover)
- Runtime-role smoke: 13/13 steps green as ledgersg_app (C-1/H-7)
- Mobile-nav live probe: 17/17 at 375/800/1280 — the navigation works,
  the functional contract green (the sixteenth settlement, session 45 /
  P24 — the live agent-browser probe this session re-sampled the slide
  mid-flight at translate: -40.963% and read the computed
  transitionProperty "transform, translate, visibility"); the ONE real
  v4-class animation bug (the drawer's transition
  list omitting the standalone `translate` property — the slide never
  interpolated) was found by the P23 compile proof and FIXED with its
  own compiled-CSS gates (the tailwindcss-animate family that silently
  compiled to nothing in v4 was the P18 fix)
- Coverage: green at the ratchet (whole-suite + src/lib + src/hooks
  per-glob floors, the hooks tier added P18/CFG-L2); build:server green;
  schema v1.2.2 (§17 RLS complete + §15c framework tables incl. the
  ENABLE_ADMIN opt-in set)
- npm audit / pip-audit: zero known advisories on the production sets
- P18 headline: the statutory-record locks (generate_f5/review_return
  join file_return under the row lock), the concurrency completion
  (unallocate/unreconcile/convert/credit-cap/add_line + the
  header/archived posting gate), the Celery coverage completion (the
  three remaining Peppol task bodies under the RLS tenant context +
  the on-commit dispatch covered + terminal classification), the email
  status gate, the contrast debt (bg-success/bg-alert/text-muted at AA
  + pairing gates), tw-animate-css, the genuinely-shared uenSchema, the
  nested-Escape fix
- P17 headline: the concurrency guards (double-reversal / double-void /
  double-reconcile refused under row locks), the Celery tenant context
  (on-commit dispatch + worker-side RLS), the 400-contract sweep, the
  admin/STORAGES settings gates, the `--color-success` token, the
  unsaved-changes guard, the org-selector Radix menu contract, the
  shared UEN schema, lint-error zero
---
Major Completed Work
1. Authentication Flow Remediation (Defense-in-Depth) ✅ COMPLETE
Problem: Dashboard showed "No Organisation Selected" instead of redirecting unauthenticated users.
Solution: Implemented three-layer defense-in-depth authentication:
┌─────────────────────────────────────────────────────────────────┐
│ LAYER 1: AuthProvider (Client-Side)                            │
│ - checkSession() on mount                                      │
│ - Calls /api/v1/auth/me/                                        │
│ - 401 → Redirect to /login                                      │
│ - Preserves destination via ?redirect= parameter                │
└─────────────────────────────────────────────────────────────────┘
│ ▼
┌─────────────────────────────────────────────────────────────────┐
│ LAYER 2: DashboardLayout Guard (Client-Side)                   │
│ - Checks isAuthenticated state                                  │
│ - false → Redirect to /login                                    │
│ - false → Return null (prevents flash of protected content)     │
│ - true → Render <Shell>{children}</Shell>                       │
└─────────────────────────────────────────────────────────────────┘
│ ▼
┌─────────────────────────────────────────────────────────────────┐
│ LAYER 3: Backend API (Server-Side)                             │
│ - CORSJWTAuthentication middleware                              │
│ - JWT token validation                                          │
│ - 401 for invalid/missing tokens                                │
│ - TenantContextMiddleware sets RLS session variables            │
└─────────────────────────────────────────────────────────────────┘
Key Fixes:
- Backend response structure: Nested organisation structure, UUID serialization as strings
- Users without organisations: Dashboard shows "No Organisation Selected" with "Create Organisation" button
- 10/10 E2E authentication tests passing
---
2. CORS Authentication Fix ✅ COMPLETE
Problem: Dashboard hung at "Loading..." because CORS preflight requests were rejected with 401.
Root Cause: DRF's JWTAuthentication executes BEFORE permission checks, rejecting OPTIONS requests without auth tokens.
Solution: Created CORSJWTAuthentication class:
class CORSJWTAuthentication(JWTAuthentication):
    def authenticate(self, request: Request):
        if request.method == "OPTIONS":
            return None  # Allow CORS middleware to handle
        return super().authenticate(request)
---
### 3. SEC-003: Content Security Policy Implementation ✅ COMPLETE
**Problem**: Backend had no CSP headers (XSS vulnerability).
**Solution**: Implemented django-csp v4.0 with strict directives:
- `default-src 'none'`
- `script-src 'self'`
- `frame-ancestors 'none'`
- Report-only mode for safe rollout
- CSP violation monitoring at `/api/v1/security/csp-report/`
**Result**: 15 TDD tests passing, **100% Security Score achieved**
---
4. SEC-002: Rate Limiting Remediation ✅ COMPLETE
Implemented django-ratelimit on authentication endpoints:
- Registration: 5/hour
- Login: 10/minute
- Refresh: 20/minute
- Banking: 100/minute
---
5. SEC-001: Banking Module Remediation ✅ COMPLETE
Replaced all stub implementations with validated endpoints (55 TDD tests):
- BankAccountService, PaymentService, ReconciliationService
- 13 validated banking endpoints
- Multi-currency payment support with FX gain/loss tracking
---
6. Banking UI Phase 5.5 ✅ COMPLETE
All three tabs fully implemented with TDD:
- Bank Accounts Tab: Full CRUD, PayNow display, balances
- Payments Tab: PaymentCard, PaymentList, PaymentFilters, ReceivePaymentForm
- Bank Transactions Tab: Full reconciliation workflow with CSV import
73 TDD tests total (Phase 5.4: 16 + Phase 5.5: 50 + Phase 3: 7)
---
7. Dashboard Service Field Remediation ✅ COMPLETE
- 21 TDD tests passing (100% coverage)
- Real data integration: GST liability, revenue MTD/YTD, outstanding amounts, cash position
- Redis caching implemented (5-minute TTL)
---
8. Dynamic Organization Context ✅ COMPLETE
- Removed hardcoded DEFAULT_ORG_ID
- JWT token claims include default_org_id and default_org_name
- New endpoint: POST /api/v1/auth/set-default-org/
- Organization selector UI in sidebar
---
Technical Architecture
Frontend Stack
- Next.js 16.4.6 (App Router) + React 19.2
- Tailwind CSS 4.0 + Shadcn/Radix UI
- Zustand (UI State) + TanStack Query (Server State)
- Hybrid rendering: Server Components for data fetching, Client Components for interactivity
Backend Stack
- Django 6.0.10 + Django REST Framework 3.18.3
- Service Layer Pattern (views are thin controllers)
- Celery 5.4+ with Redis 7+ for async tasks
- WeasyPrint 68.1 for PDF generation
Database Architecture (SQL-First)
- PostgreSQL 16+ with 7 domain schemas
- NUMERIC(19,4) for monetary values, NUMERIC(12,6) for FX rates (NO FLOATS;
  widened from NUMERIC(10,4) in the P3 sprint — see the conformance gate)
- Row-Level Security (RLS) via session variables
- Unmanaged Django models (managed = False)
---
Critical Development Patterns
SQL-First Design
- Schema is the source of truth (database_schema.sql)
- NEVER run python manage.py makemigrations
- Test database must be manually initialized:
export PGPASSWORD=ledgersg_secret_to_change
dropdb -h localhost -U ledgersg test_ledgersg_dev || true
createdb -h localhost -U ledgersg test_ledgersg_dev
psql -h localhost -U ledgersg -d test_ledgersg_dev -f database_schema.sql
pytest --reuse-db --no-migrations
Financial Integrity
- Use common.decimal_utils.money() for all currency operations
- Double-entry enforced at database level
- Posted journal entries are immutable
Testing (TDD Methodology)
- RED → GREEN → REFACTOR cycle
- Backend: pytest with --reuse-db --no-migrations
- Frontend: Vitest + React Testing Library
- Use userEvent.setup() for Radix UI components (NOT fireEvent)
---
Lessons Learned
1. DRF Authentication Order: Authentication executes BEFORE permissions - cannot use permission classes alone for CORS bypass
2. django-csp v4.0 Breaking Change: Uses dict-based CONTENT_SECURITY_POLICY config, not individual CSP_* settings
3. TanStack Query v5: Mutations use isPending instead of isLoading
4. Radix UI Testing: fireEvent.click doesn't trigger state changes - use userEvent
5. UUID Serialization: Backend must convert UUIDs to strings for JSON responses
6. Nested Response Structures: Frontend expects { id, org: {...}, role: {...} } format
---
Security Posture
Domain
Authentication & Session
Authorization & Access Control
Multi-Tenancy & RLS
Input Validation
XSS Prevention (CSP)
SQL Injection Prevention
CSRF Protection
Rate Limiting
---
## Known Issues & Recommendations
### Immediate Priority
- [ ] Add retry logic and fallback UI for dashboard API failures
- [ ] Expand frontend test coverage for hooks and forms (SEC-004)
- [ ] Automate DB initialization in CI/CD
### Short-Term
- [ ] Implement actual Peppol transmission log (currently stub)
- [ ] PII encryption at rest (SEC-005)
- [ ] Mobile optimization for dashboard
### Long-Term
- [ ] InvoiceNow: Finalize Peppol XML transmission
- [ ] Redis caching for dashboard (5-minute TTL)
- [ ] 2FA/MFA support
---
Test Credentials
User Type
With Org
Without Org
---
File Structure
apps/
├── backend/           # Django 6.0.10
│   ├── apps/          # core, coa, gst, journal, invoicing, banking, peppol, reporting
│   ├── common/        # BaseModel, TenantModel, decimal_utils
│   ├── config/        # settings, celery, urls
│   └── tests/         # integration, security, TDD
│
└── web/               # Next.js 16.4.6
    ├── src/
    │   ├── app/       # App Router pages
    │   ├── components/
    │   ├── hooks/
    │   ├── lib/
    │   └── providers/
    └── public/
---
## Next Agent Guidance
1. **Always validate against codebase** before making changes
2. **Follow TDD**: Write failing tests first
3. **Respect SQL-First**: Never use Django migrations
4. **Use Shadcn/Radix**: Don't rebuild UI components
5. **Check AGENTS.md**: Contains detailed troubleshooting and patterns
6. **Run linting**: `npm run lint` and `pytest --reuse-db --no-migrations`
---
Summary: The LedgerSG platform is production-ready with comprehensive test coverage, enterprise-grade security (100% score), and complete banking UI. The authentication system now implements defense-in-depth with three independent layers. All major security findings have been remediated. The codebase follows SQL-first design, service layer patterns, and WCAG AAA accessibility standards.

# LedgerSG Autonomous Agent Briefing Document

**Version:** 1.7.0
**Classification:** CONFIDENTIAL — Internal Development Use
**Date:** 2026-03-08
**Subject:** Comprehensive Project Architecture, Standards, and Operational Directives

**Recent Updates:**
- ✅ **Authentication Remediation Complete**: 5-phase defense-in-depth implementation (10/10 tests passing)
- ✅ **Layer 1**: AuthProvider redirects unauthenticated users to /login
- ✅ **Layer 2**: DashboardLayout guard prevents unauthorized access (no flash)
- ✅ **Layer 3**: Backend JWT validation on all protected endpoints
- ✅ **Backend Response Fix**: Nested organisation structure, UUID serialization
- ✅ **Test Coverage**: E2E authentication tests (login, refresh, security)
- ✅ **Phase 3 Complete**: Bank Transactions Tab Integration (7/7 integration tests passing, 100%)
- ✅ **Placeholder Replaced**: Full BankTransactionsTab implementation with all Gap 4 components
- ✅ **TDD Methodology**: RED → GREEN → REFACTOR cycle for all integration tests
- ✅ **Blockers Solved**: Async tab switching with userEvent, missing hook mocks, multiple button collision
- ✅ **Test Updates**: page.test.tsx fixed with proper useBankTransactions mocks (16/16 tests passing)
- ✅ **Total Frontend Tests**: 305 tests across 22 test files
- ✅ Total API endpoints: 83, Total tests: 548+

---

## 1. Executive Summary

**LedgerSG** is a production-grade, double-entry accounting platform purpose-built for Singapore Small and Medium Businesses (SMBs). Its primary mission is to transform IRAS 2026 compliance from a regulatory burden into a seamless, automated experience. The platform combines enterprise-grade financial integrity with a distinctive "Illuminated Carbon" neo-brutalist user interface.

**Current Status:** ✅ **Production Ready**
- **Frontend:** v0.3.6 (Next.js 16.4.6, 16 pages, 75 test files, **641 tests passing**)
- **Backend:** v0.6.6 (Django 6.0.10, 90+ API endpoints, **969 tests passing, 0 failed**)
- **Database:** v1.2.2 (PostgreSQL 16+, 7 schemas, 29 domain tables + 1 view + §15c framework tables, RLS complete on every tenant table §17)
- **Dashboard:** v1.0.0 (Real Data Integration, 36 TDD tests, 100% coverage)
- **Integration Gaps:** Phase 3 Complete (GAP-3: 20 tests, GAP-4: 13 tests)
- **Banking UI:** Phase 5.5 Complete (73 TDD tests, all tabs live)
- **Security Posture:** P0–P21 remediated; remaining P1/P2 items tracked in the deferred register (see the README Security Posture table)

As an autonomous coding agent, your objective is to maintain this high standard of architectural maturity while executing Pull Requests (PRs). You must operate under the **Meticulous Approach**: Analyze → Plan → Validate → Implement → Verify → Deliver. Surface-level assumptions are prohibited; every change must be grounded in deep technical reasoning.

---

## 2. System Architecture & Technology Stack

The project utilizes a decoupled, service-oriented architecture designed for security, scalability, and regulatory compliance.

### 2.1 Frontend Architecture
- **Framework:** Next.js 16.4.6 (App Router) with React 19.2.
- **Styling:** Tailwind CSS 4.0 + Shadcn/Radix UI primitives.
- **State Management:** Zustand (UI State) + TanStack Query (Server State).
- **Rendering Strategy:** Hybrid. Critical data paths use **Server Components** to ensure zero JWT exposure to client-side JavaScript. Interactive elements (charts, forms) are isolated Client Components.
- **Build Modes:**
  - `standalone`: the ONLY supported mode (`npm run build:server` + `npm start`) — P10/M-12 retired the static export (it cannot support API-driven detail routes).
  - `export`: experiments only; NO build script ships for it.
- **Design Philosophy:** "Illuminated Carbon" Neo-Brutalist. Reject generic templates. Use whitespace as a structural element. Ensure WCAG AAA compliance.

### 2.2 Backend Architecture
- **Framework:** Django 6.0.10 with Django REST Framework (DRF) 3.18.3.
- **Pattern:** **Service Layer Pattern**. Views are thin controllers; ALL business logic resides in `services/` modules.
- **Task Queue:** Celery 5.4+ with Redis 7+ for async tasks (PDF generation, Email delivery).
- **PDF Engine:** WeasyPrint 68.1 for IRAS-compliant document generation.
- **Directory Structure:**
```text
apps/backend/
├── apps/ (core, coa, gst, journal, invoicing, banking, reporting)
├── common/ (BaseModel, TenantModel, decimal_utils)
├── config/ (settings, celery, urls)
└── tests/ (integration, security, TDD)
```

### 2.3 Database Architecture (SQL-First)
- **Engine:** PostgreSQL 16+.
- **Schema:** 7 Domain-Specific Schemas (`core`, `coa`, `gst`, `journal`, `invoicing`, `banking`, `audit`).
- **Precision:** `NUMERIC(19,4)` for monetary values, `NUMERIC(12,6)` for FX rates. **Floats are strictly prohibited.** (Widened from `NUMERIC(10,4)` in the P3 sprint — the old cap could not represent amounts above S$999,999.9999.)
- **Multi-Tenancy:** **Row-Level Security (RLS)** enforced via session variables (`app.current_org_id`).
- **Model Strategy:** **Unmanaged Models** (`managed = False`). The SQL schema (`database_schema.sql`) is the source of truth. Django models map to existing tables; Django migrations are disabled.

---

## 3. Core Development Principles

### 3.1 SQL-First Design
The database schema is the single source of truth. Django models must strictly align with DDL-defined columns.
- **Constraint:** Never run `python manage.py makemigrations`. Schema changes require manual SQL patches followed by model alignment.
- **Testing:** Standard Django test runners fail because they attempt to create tables. You must manually initialize the test database using `database_schema.sql` before running pytest.
- **Alignment:** All 22 Django models are currently aligned with SQL v1.0.2. Any new field requires a SQL patch first.

### 3.2 Security-First Authentication

**Defense-in-Depth Architecture:**

The authentication system implements three independent layers to ensure robust security:

```
┌─────────────────────────────────────────────────────────────────┐
│ LAYER 1: AuthProvider (Client-Side)                            │
│ - checkSession() on mount                                      │
│ - Calls /api/v1/auth/me/                                       │
│ - 401 → Redirect to /login                                     │
│ - Preserves destination via ?redirect= parameter               │
└─────────────────────────────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│ LAYER 2: DashboardLayout Guard (Client-Side)                   │
│ - Checks isAuthenticated state                                 │
│ - false → Redirect to /login                                   │
│ - false → Return null (prevents flash of protected content)    │
│ - true → Render <Shell>{children}</Shell>                      │
└─────────────────────────────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│ LAYER 3: Backend API (Server-Side)                             │
│ - CORSJWTAuthentication middleware                             │
│ - JWT token validation                                         │
│ - 401 for invalid/missing tokens                               │
│ - TenantContextMiddleware sets RLS session variables           │
└─────────────────────────────────────────────────────────────────┘
```

**Key Principles:**
- **JWT Strategy:** 15-minute Access Token + 7-day Refresh Token
- **Storage:** Refresh tokens in **HttpOnly Cookies**. Access tokens in server memory (SSR)
- **Exposure:** **Zero JWT exposure** to browser JavaScript
- **No Flash:** Layer 2 returns `null` if not authenticated, preventing flash of protected content
- **Users Without Organisations:** Dashboard shows "No Organisation Selected" with "Create Organisation" button linking to `/settings/organisations/new`

**Test Coverage:**
- 10/10 E2E authentication tests passing
- Tests cover: redirect flow, login, organisations fetch, users without orgs, token refresh, rate limiting, JWT exposure

**Common Troubleshooting:**
- **403 Forbidden:** Check `UserOrganisation.accepted_at` is set (Middleware requirement)
- **Redirect Loops:** AuthProvider checks current path before redirecting
- **UUID Serialization:** Backend returns UUIDs as strings to avoid JSON serialization errors

### 3.3 Financial Integrity
- **Decimal Precision:** Use `common.decimal_utils.money()` for all currency operations. This utility rejects floats and quantizes to 4 decimal places.
- **Double-Entry:** Enforced via database constraints and `JournalService`. Debits must equal credits.
- **Immutability:** Posted journal entries (`JournalEntry`) are immutable. Corrections require reversing entries, not updates.
- **Audit Trail:** `audit.event_log` table captures immutable before/after values for all critical changes (5-year retention).

### 3.4 Anti-Generic UI Design
- **Library Discipline:** Use Shadcn/Radix primitives. Do not rebuild modals or dropdowns from scratch.
- **Aesthetic:** Reject "safe" defaults (Inter/Roboto). Use bespoke typography and asymmetry where intentional.
- **States:** Handle loading, error, empty, and success states explicitly. Show loading indicators ONLY when no data exists.

---

## 4. Testing Strategy & Quality Assurance

LedgerSG employs Test-Driven Development (TDD) for critical business logic.

### 4.1 Backend Testing Workflow
Standard Django test workflows are incompatible due to unmanaged models.
**Mandatory Workflow:**
1. **Initialize DB:**
```bash
export PGPASSWORD=ledgersg_secret_to_change
dropdb -h localhost -U ledgersg test_ledgersg_dev || true
createdb -h localhost -U ledgersg test_ledgersg_dev
psql -h localhost -U ledgersg -d test_ledgersg_dev -f database_schema.sql
```
2. **Run Tests:**
```bash
source /opt/venv/bin/activate
cd apps/backend
pytest --reuse-db --no-migrations
```
- **Coverage:** 233+ tests passing across 16 test files. Focus on Service Layer logic and API endpoint contracts.
- **Dashboard TDD:** 21 test-driven tests (service + view).
- **Integration Gaps:** 33 new tests (GAP-3: 20 tests, GAP-4: 13 tests), 100% passing.
- **Banking UI:** 73 TDD tests (Phase 5.4: 16 + Phase 5.5: 50 + Phase 3: 7), 100% passing.
- **Fixtures:** Must comply with SQL constraints (e.g., `TaxCode` requires `is_input=TRUE` or `is_output=TRUE`).

### 4.2 Frontend Testing Workflow
- **Runner:** Vitest + React Testing Library.
- **Command:** `npm test` (runs in `apps/web`).
- **Coverage:** 114 tests passing across 5 test files. GST Engine has 100% coverage (critical for IRAS compliance).
- **Test Files:** gst-engine.test.ts, api-client-endpoints.test.ts, button.test.tsx, input.test.tsx, badge.test.tsx
- **E2E:** Playwright used for navigation and accessibility scans.

### 4.3 Quality Assurance Checklist
Before submitting any PR, verify:
- [ ] Solution meets all stated requirements.
- [ ] Code follows language-specific best practices (TypeScript strict mode, Django service layer).
- [ ] Comprehensive testing implemented (TDD for backend logic).
- [ ] Security considerations addressed (RLS, Input Validation, No Floats).
- [ ] Documentation updated (README, CLAUDE.md, AGENT_BRIEF.md).
- [ ] Platform-specific requirements met (Docker, Env vars).
- [ ] Edge cases considered (Empty states, Network failures).
- [ ] Long-term maintenance evaluated.

---

## 5. Security & Compliance Posture

### 5.1 IRAS 2026 Compliance
- **GST:** Standard-rated (9%), Zero-rated, Exempt, and Out-of-Scope codes implemented.
- **F5 Returns:** Auto-generation logic ready (`gst.compute_f5_return`).
- **InvoiceNow:** Peppol transmission architecture ready (XML generation pending final logic).
- **BCRS:** Bank Cash Register System deposits exempted from GST calculations.

### 5.2 Vulnerability Management
Recent Security Audit (2026-03-07) scored **100%**. All critical findings remediated:
- ~~**SEC-001 (HIGH):** Banking module stubs return unvalidated input.~~ ✅ **REMEDIATED** (2026-03-02)
- ~~**SEC-002 (MEDIUM):** No rate limiting on authentication.~~ ✅ **REMEDIATED** (2026-03-02)
- ~~**SEC-003 (MEDIUM):** Content Security Policy (CSP) not configured.~~ ✅ **REMEDIATED** (2026-03-07)
- **SEC-004 (MEDIUM):** Frontend test coverage minimal outside GST engine. **Status:** In Progress (305/305 tests passing)
- **SEC-005 (LOW):** PII encryption at rest not implemented. **Status:** Future Enhancement

### 5.3 Data Protection
- **Passwords:** Django hashing (128 char).
- **PII:** GST numbers and bank accounts currently unencrypted at rest. **Recommendation:** Implement field-level encryption for sensitive PII.
- **SQL Injection:** Protected via parameterized queries and ORM. No string concatenation in SQL.

---

## 6. Operational Guidelines

### 6.1 Environment Configuration
- **Backend:** Requires `.env` with `SECRET_KEY`, `DATABASE_URL`, `REDIS_URL`.
- **Frontend:** Requires `.env.local` with `NEXT_PUBLIC_API_URL=http://localhost:8000` and `NEXT_OUTPUT_MODE=standalone`.
- **Docker:** Multi-service container available (`docker/Dockerfile`). Exposes ports 3000 (FE), 8000 (BE), 5432 (DB), 6379 (Redis).

### 6.2 Common Troubleshooting
- **Dashboard "Loading..." Stuck:** Caused by missing static files in standalone build. **Fix:** Run `npm run build:server` (auto-copies static files).
- **403 Forbidden on API:** Check `UserOrganisation.accepted_at` is set (Middleware requirement).
- **Model Schema Mismatch:** `ProgrammingError: column X does not exist`. **Fix:** Align Django model fields with `database_schema.sql`.
- **Circular Dependencies:** SQL FKs must be added via `ALTER TABLE` at the end of the schema script.
- **URL Registration 404:** Added view to `urls.py` but getting 404. **Fix:** Check `config/urls.py` to see which URL config is actually imported (e.g., `apps/core/urls/__init__.py` vs `apps/core/urls.py`).
- **Radix Tabs Not Activating in Tests:** `fireEvent.click` doesn't trigger state. **Fix:** Use `const user = userEvent.setup(); await user.click(tab)`.
- **"Found Multiple Elements" in Tests:** Multiple elements match selector. **Fix:** Use `findAllByRole()` and check array length.
- **Hook Returns Undefined:** Missing mock in test. **Fix:** Add `vi.mocked(hooks.useXxx).mockReturnValue({...})`.

#### CSP-Specific Troubleshooting (SEC-003)
- **CSP Headers Not Appearing:** Tests failing with no CSP headers in response. **Fix:** Check django-csp version (v4.0+ uses dict-based config). Use `CONTENT_SECURITY_POLICY_REPORT_ONLY = {"DIRECTIVES": {...}}` instead of individual `CSP_*` settings.
- **CSP Report Endpoint Returns 401:** Browser sends CSP reports without auth tokens. **Fix:** Add `@permission_classes([AllowAny])` decorator to the report view.
- **report-uri Missing from CSP Header:** Test expects `report-uri` directive but it's not in header. **Fix:** Explicitly add `"report-uri": ["/api/v1/security/csp-report/"]` to DIRECTIVES dict.
- **django-csp Module Not Found:** `ImportError: No module named 'csp.middleware'`. **Fix:** Add `'csp'` to `INSTALLED_APPS` in `settings/base.py`.
- **CSP Breaks Django Admin:** Admin pages not loading properly with CSP. **Fix:** Use report-only mode first, monitor violations, then consider adding `'unsafe-inline'` to `script-src` if needed for admin-only usage.
- **Tests Passing Locally But Failing in CI:** CSP configuration differences between environments. **Fix:** Ensure `CONTENT_SECURITY_POLICY_REPORT_ONLY` is set in both `base.py` and `testing.py` settings.

#### Backend Test Execution (SQL-First Architecture)

**Issue:** `ProgrammingError: relation "core.app_user" does not exist`

**Cause:** Django models use `managed = False`. Test database must be pre-initialized with SQL schema.

**Solution:**
```bash
# Initialize test database (ONE-TIME setup)
export PGPASSWORD=ledgersg_secret_to_change
dropdb -h localhost -U ledgersg test_ledgersg_dev || true
createdb -h localhost -U ledgersg test_ledgersg_dev
psql -h localhost -U ledgersg -d test_ledgersg_dev -f apps/backend/database_schema.sql

# Run tests (ALWAYS use these flags)
source /opt/venv/bin/activate
pytest --reuse-db --no-migrations

# For specific test files
pytest --reuse-db --no-migrations apps/core/tests/test_csp_headers.py
```

**Why these flags are required:**
- `--reuse-db`: Don't recreate database (use pre-initialized DB with schema already loaded)
- `--no-migrations`: Skip Django migrations (schema already loaded via `database_schema.sql`)

**Alternative:** Use the custom test runner configured in `testing.py`:
```python
TEST_RUNNER = "common.test_runner.SchemaTestRunner"
```

#### Frontend Test Troubleshooting (TanStack Query v5)

**Issue:** Mutation loading state tests failing

**Cause:** TanStack Query v5 renamed `isLoading` to `isPending` for mutations

**Solution:**
```typescript
// Before (v4 or deprecated)
mockUseMutation.mockReturnValue({
  mutateAsync: vi.fn(),
  isLoading: true, // ❌ Wrong for v5 mutations
});

// After (v5)
mockUseMutation.mockReturnValue({
  mutateAsync: vi.fn(),
  isPending: true, // ✅ Correct for v5 mutations
});
```

**Note:** `isLoading` is still used for query hooks, but `isPending` should be used for mutation hooks in TanStack Query v5.

### 6.3 Deployment Modes
- **Development:** `npm run dev` (Frontend) + `python manage.py runserver` (Backend).
- **Production:** `npm run build:server` + `npm run start` (Frontend) + Gunicorn (Backend).
- **Static:** `npm run build` + `npm run serve` (No API integration).

---

## 7. Autonomous Agent Directives

As an autonomous agent working on PRs, you must adhere to the following operational protocols:

### 7.1 Request Analysis & Planning
- **Deep Understanding:** Do not accept surface-level requirements. Identify implicit needs (e.g., if asked to add a field, consider RLS, Audit Log, and Serializer implications).
- **Solution Exploration:** Validate assumptions against the `AGENTS.md` knowledge base. If a pattern contradicts the SQL-First architecture, reject it.
- **Risk Assessment:** Identify impacts on Multi-tenancy (RLS) and Financial Integrity (Decimal Precision).

### 7.2 Implementation Standards
- **Backend:** 
  - Logic goes in `services/`, not views.
  - Use `transaction.atomic()` for write operations.
  - Use `money()` utility for all currency values.
  - Respect `managed = False` on models.
- **Frontend:** 
  - Prefer Server Components for data fetching.
  - Use Shadcn primitives; do not custom-build UI components unless necessary.
  - Ensure WCAG AAA accessibility.
- **Database:** 
  - Never use floats.
  - Always filter by `org_id` or rely on RLS session variables.

### 7.3 Validation & Verification
- **Testing:** Write failing tests first (TDD) for backend logic. Ensure frontend tests pass (`npm test`).
- **Security:** Verify no JWT leakage to client. Check input validation on all endpoints (especially Banking).
- **Documentation:** Update relevant markdown files (`README.md`, `ACCOMPLISHMENTS.md`) with change details.

### 7.4 Communication & Delivery
- **Transparency:** Document trade-offs. If a security compromise is made for speed, flag it explicitly.
- **Handoff:** Provide clear usage instructions and migration steps (SQL patches).
- **Lessons Learned:** Record challenges encountered during implementation for future reference.

#### Frontend Testing Lessons (Phase 3)
- **Radix UI Async Behavior**: `fireEvent.click` doesn't trigger Radix UI state changes. Always use `userEvent.setup()` and `await user.click(tab)` for tab switching.
- **Comprehensive Hook Mocking**: Missing `useBankTransactions` mock caused cascading failures. Audit all hooks used by component tree.
- **Multiple Element Handling**: When multiple buttons have same text (e.g., "Import Statement"), use `findAllByRole` and check array length instead of `findByRole`.
- **Component State Awareness**: TransactionList renders `transactions-empty` when `count=0` and `transactions-list` when `count>0`. Understand conditional renders before writing assertions.

#### CSP Implementation Lessons (SEC-003)
- **django-csp v4.0 Breaking Change**: Configuration changed from individual `CSP_*` settings to dict-based `CONTENT_SECURITY_POLICY`. Always check package version before implementation.
- **Report Endpoint Authentication**: CSP reports are sent by browsers without auth tokens. Use `@permission_classes([AllowAny])` for the report endpoint.
- **Middleware Order Matters**: CSPMiddleware must be placed after SecurityMiddleware but before response-generating middleware.
- **Report-Uri Manual Addition**: django-csp doesn't auto-append report-uri from settings; must be explicitly added to DIRECTIVES dict.
- **Report-Only Mode First**: Always deploy CSP in report-only mode to monitor violations before enforcement.

#### Validation & Test Fix Lessons (2026-03-07)
- **TanStack Query v5 API Change**: Mutations use `isPending` instead of `isLoading`. Check library version before writing test mocks.
- **SQL-First Test Workflow**: Test database must be pre-initialized with schema. Use `--reuse-db --no-migrations` flags.
- **Documentation Audit**: Cross-reference claims against actual codebase quarterly. Journal Service was marked "deferred" but already complete.
- **Button Text Matching**: Use flexible matchers (`findByText`, `getAllByRole`) when button text includes dynamic content (e.g., "Reconciling...").
- **Test Database Initialization**: One-time setup required before running backend tests. Automated via `database_schema.sql` import.

### 7.5 Prohibited Actions
- **NO** Django migrations (`makemigrations`).
- **NO** Float arithmetic for money.
- **NO** Client-side JWT storage (localStorage).
- **NO** Generic Bootstrap-style layouts.
- **NO** Skipping test initialization steps for backend.

---


## 8. Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                         USER REQUEST                             │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  LAYER 1: AuthProvider (Phase 1)                                │
│  - checkSession() on mount                                       │
│  - Calls /api/v1/auth/me/                                        │
│  - 401 → Redirect to /login                                      │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  LAYER 2: DashboardLayout Guard (Phase 3)                       │
│  - Check isAuthenticated                                         │
│  - false → Redirect to /login                                    │
│  - false → Return null (no flash)                                │
│  - true → Render <Shell>{children}</Shell>                       │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  LAYER 3: Backend API (Existing)                                 │
│  - CORSJWTAuthentication                                         │
│  - JWT token validation                                          │
│  - 401 for invalid/missing tokens                                │
└─────────────────────────────────────────────────────────────────┘
```

---

## 9. Future Roadmap & Priorities

### 9.1 Immediate (High Priority)
- ✅ **Banking Module:** Replace stubs in `banking/views.py` with validated logic (SEC-001). **COMPLETE** (2026-03-02)
- ✅ **Organization Context:** Replace hardcoded `DEFAULT_ORG_ID` with dynamic user context. **COMPLETE** (2026-03-03)
- ✅ **Integration Gaps:** Validate GAP-3 (Peppol) and GAP-4 (Org Settings) endpoints. **COMPLETE** (2026-03-04)
- ✅ **Bank Transactions Tab:** Implement full reconciliation UI with TDD. **COMPLETE** (2026-03-06)
- ✅ **Content Security Policy:** Implement CSP headers on backend (SEC-003). **COMPLETE** (2026-03-07)
- **Error Handling:** Add retry logic and fallback UI for dashboard API failures.

### 9.2 Short-Term (Medium Priority)
- ✅ **Rate Limiting:** Implement `django-ratelimit` on auth endpoints (SEC-002). **COMPLETE** (2026-03-02)
- ✅ **CSP Headers:** Configure Content Security Policy (SEC-003). **COMPLETE** (2026-03-07)
- **Frontend Tests:** Expand coverage for hooks and forms (SEC-004).
- **CI/CD:** Automate manual DB initialization workflow in GitHub Actions.
- **Peppol Enhancement:** Implement actual transmission log (currently stub).

### 9.3 Long-Term (Low Priority)
- **InvoiceNow:** Finalize Peppol XML transmission logic.
- **PII Encryption:** Encrypt sensitive data at rest.
- **Mobile Optimization:** Responsive refinements for dashboard.
- **Redis Caching:** Add caching for dashboard data (5-minute TTL).

---

## 10. Conclusion

LedgerSG represents a mature, security-conscious platform balancing regulatory compliance with modern engineering practices. The **SQL-First** design ensures data integrity, while the **Service Layer** ensures maintainability. 

Your role is to protect this integrity. Every line of code you commit must uphold the **Meticulous Approach**. Do not rush. Validate deeply. Ensure that every feature not only works but is secure, compliant, and aesthetically aligned with the "Illuminated Carbon" vision.

---

Added a comprehensive Troubleshooting section to API_CLI_Usage_Guide.md covering:
- UUID Formatting: Django URL converter already provides UUID objects, don't double-convert
- Decimal Precision: Strings with 4 decimals required, helper function included
- CORS Errors: Backend handles OPTIONS without auth via CORSJWTAuthentication
- 403 Forbidden: Check org_id, RLS context, and membership status
- 500 Errors: Exception logging via wrap_response decorator

# Documentation Created ✅
- UUID_PATTERNS_GUIDE.md - Comprehensive guide covering:
  - Django URL converter behavior
  - Common mistakes and fixes
  - Safe conversion patterns
  - Testing and migration checklist
  - Error message explanations
Files Modified
File
tests/integration/test_auth_api.py
apps/coa/views.py
UUID_PATTERNS_GUIDE.md
Key Lessons
1. Django URL converters automatically convert <uuid:org_id> to UUID objects
2. Don't double-convert - calling UUID() on a UUID object fails
3. Query params still need conversion: UUID(request.query_params.get("id"))
4. LSP errors are type checker warnings, not runtime errors
Testing Commands
# Verify RLS tests
pytest tests/middleware/test_rls_context.py -v --reuse-db --no-migrations

## 2026-11-21 P0 Remediation — New Patterns & Lessons

### Transaction-Scoped RLS (C-03 pattern — CRITICAL for any middleware touching session variables)
`SET LOCAL` is transaction-scoped. Under `ATOMIC_REQUESTS`, the request transaction opens
strictly INSIDE the view, after middleware runs. Any middleware that needs session variables
(RLS or audit) must open `transaction.atomic()` itself and call `get_response()` inside it —
Django's `make_view_atomic` then nests as a savepoint. Verified by
`tests/security/test_rls_transaction_isolation.py` (TransactionTestCase = production semantics;
pytest-django's wrapping transactions MASK this failure mode in TestCase tests).

### wrap_response Contract (C-04)
Typed exceptions (ValidationError/ResourceNotFound/DuplicateResource) map to 400/404/409.
UNEXPECTED exceptions must PROPAGATE — converting them to a 500 Response inside
ATOMIC_REQUESTS commits partial multi-step financial state. The rollback is worth more than
a pretty error body.

### Void = Reversal Entry (C-02)
`DocumentService.void_document()` persists `void_reason` (DB CHECK `chk_void_reason`),
uses enum-correct voidable statuses (`PARTIALLY_PAID`, never `PAID_PARTIAL`), and calls the
SINGLE `_reverse_journal_entry` which delegates to `JournalService.void_document_entry()`.
`create_reversal` must set `is_reversed = True` together with `reversed_by` (CHECK
`chk_reversal_consistency`), and the reversal date must fall in an OPEN fiscal period.

### GST F5 Box Convention (C-01 — matches schema CHECKs and IRAS)
Box 1/2/3 = supplies (net), Box 4 = 1+2+3, Box 5 = total taxable purchases,
Box 6 = output tax, Box 7 = input tax claimable (only `is_claimable` codes),
Box 8 = 6 − 7, Box 13 = revenue, Box 14 = reverse charge.
Drive ALL box placement from `gst.tax_code.f5_supply_box/f5_purchase_box/f5_tax_box` —
never from literal tax-code strings. Statuses: DRAFT, COMPUTED, REVIEWED, FILED, AMENDED.

### Schema–Model Conformance Gate (M-01)
`tests/invariants/test_schema_conformance.py` introspects `information_schema.columns` and
fails on any model/table drift. SQL-First means the model is a hand-maintained mirror —
this gate is what catches the next drift before production does. Run it after ANY model edit.

### Document Status/Type Vocabulary (M-08)
`doc_status` enum: DRAFT, APPROVED, SENT, PARTIALLY_PAID, PAID, OVERDUE, VOID.
`doc_type` enum: SALES_INVOICE, SALES_CREDIT_NOTE, …, SALES_QUOTE. Never invent literals
(`PAID_PARTIAL`, `INVOICE`) — they raise `invalid input value for enum` / CHECK violations.

### Test Environment Prerequisites
Redis on :6379 is REQUIRED for the suite (middleware membership cache + audit context use
the configured cache). Without it every org-scoped request test fails with
`tenant_context_error` 500s. PG on :5432 with schema v1.0.2 (includes token_blacklist tables §15b).

### Refresh-Token Lifecycle (H-05)
`refresh_access_token()` rotates and blacklists; `logout_user()` blacklists;
`change_password()` revokes ALL outstanding tokens. The blacklist tables are hand-written DDL
in `database_schema.sql` §15b (SQL-First; the simplejwt app's migrations are never run).

## 2026-11-21 P1 Sprint — New Patterns & Lessons (session 3)

### The Fixture Contract: `accepted_at` is Mandatory (A-1)
`TenantContextMiddleware._verify_org_membership` filters on
`accepted_at__isnull=False` — an org membership without `accepted_at` is treated as a
pending invitation and every org-scoped request 403s. ANY test fixture that creates
`UserOrganisation` must set `accepted_at=timezone.now()`. The root `tests/conftest.py`
fixture does this correctly; `tests/test_api_endpoints.py` had shadowed it with a local
copy that omitted it — 25 of the 26 "documented fixture debt" failures were that single
omission. Prefer consuming the root conftest fixtures over redefining them locally.

### Fixture Debt Masks Real Bugs (A-2/A-3/A-4)
Fixing the fixture gate immediately exposed three production defects that had been
hiding behind the 403s: `DocumentSummaryView` (phantom `DOCUMENT_TYPE_CHOICES`,
invalid `PAID_PARTIAL` enum literal, phantom `total` attribute, int/Decimal `.quantize()`
crash on empty sums), CoA `get_trial_balance` (LEFT JOIN on the non-existent
`coa.account_balance` view), and `ValidStatusTransitionsView` (missing `org_id` kwarg).
Lesson: never let a known-failing test population sit — red suites hide real defects.

### Enum Vocabulary Sweep (M-08 discipline)
`PAID_PARTIAL` (invalid) vs `PARTIALLY_PAID` (valid `doc_status` value) appeared in
THREE places (`invoicing/views.py` twice, `contact_service.py` once). When an invalid
literal is found, sweep the whole app for the same string — the same copy-paste mistake
travels in groups. `entity_type` has its own CHECK vocabulary too
(`PRIVATE_LIMITED`, not `pte_ltd`).

### Packaging Completeness (A-6)
Settings-imported packages MUST be declared in `pyproject.toml` (the canonical
manifest): `django_celery_beat` and `django_ratelimit` were imported by INSTALLED_APPS
but undeclared, so the documented `pip install -e ".[dev]"` + `manage.py check` path
failed in a clean venv. Note: `django-celery-beat` 2.8.1 pins Django<6 (downgrades the
venv); 2.9.0 supports Django 6. The root `requirements.txt` is a stale second manifest
(pyproject is canonical — do not add dependencies there).

### Trial Balance Aggregation Pattern (A-3)
There is no `coa.account_balance` view in the schema. Any balance aggregation must
go to `journal.line` joined to `journal.entry` (see `AccountService.get_account_balance`
and the rewritten `get_trial_balance`). The optional `fiscal_year_id` filter maps to
`journal.entry.fiscal_year_id`.

### Env File Hygiene (A-7/A-8)
`.env` and `.env.local` are gitignored; `.env.example` files (backend + web) are the
canonical dev templates and must list every variable the code actually reads. When
adding a `config(...)` call to settings, update `apps/backend/.env.example` in the
same commit.

## 2026-11-21 P2 Sprint — New Patterns & Lessons (session 5)

### Rate Resolution Must Be Date-Aware (H-04/B-3)
`gst.tax_code` stores rate HISTORY as sibling rows (`effective_from`/`effective_to`;
SR: 0.07 → 2022-12-31, 0.08 → 2023, 0.09 → 2024-01-01). Any lookup by code MUST
resolve the row in force on a date: `TaxCodeService.get_tax_code_by_code(org_id,
code, as_of=None)` (org-scoped rows shadow system rows, latest `effective_from`
wins, NULL `effective_to` = open-ended). An unordered `.first()` silently returns
the 2007 row (7%) — verified live before the fix. `add_line` fails closed with a
`ValidationError` when the passed tax code is not effective on
`document.issue_date` (the model field behind the `document_date` column).
F5 returns still resolve at computation date — the period-cut semantics decision
is registered debt (ties into H-02).

### Fail Closed on Compliance Calculations (B-3)
The GST calculate endpoint used to fall back to `Decimal("0.09")` when a code was
unknown — a wrong-rate answer on a compliance endpoint. Unknown or not-in-force
codes now raise `ResourceNotFound` → 404. Rule: on money/tax paths, an explicit
error beats a plausible default. The endpoint accepts `tax_code` (canonical) +
`document_date`; the legacy `tax_code_id` field always held a CODE (never a UUID)
and is kept as a deprecated string alias.

### Phantom-Kwarg View Bugs (B-7)
`TaxCodeListCreateView.post` passed `box_mapping=...` into
`TaxCode.objects.create` — a field that exists on neither the serializer nor the
model — so EVERY custom tax-code create 500'd with `TypeError`. The path was
triple-broken (the calculate view's code branch also crashed on `UUID(org_id)`
re-wrapping and an `UnboundLocalError` on `Decimal`). Lesson: endpoints whose
only tests exercise the "other" branch (rate, not code) rot invisibly — the
tax-code branch had zero coverage while the suite was green. When adding a
serializer field, check the view actually forwards model fields (f5_* now persist).

### Playwright: Green by Default (B-1)
Never declare browser projects the environment does not have — `npm run
test:e2e` failed on 24/30 tests with `Executable doesn't exist` before any
assertion ran. Config now runs chromium only by default; the full 5-project
matrix opts in via `PLAYWRIGHT_PROJECTS=all` (needs `npx playwright install`).
Mobile viewport coverage stays via `setViewportSize` in the responsive tests.
Reporters: `list` + `html` with `open: "never"`.

### Axe Scans Must Wait for Auth Redirects (B-2)
`/` → `/dashboard` → auth guard → `/login` is a redirect CHAIN; scanning right
after `page.goto("/")` can capture the guard's null shell (no landmarks) and
flake. The a11y test now awaits `expect(page).toHaveURL(/\/login/)` before
`.analyze()`. Login page semantics: `<main>` landmark, exactly one `<h1>` (the
brand — `CardTitle` renders `<h3>`, use an explicit h1), and
`text-text-secondary` (#A0A0A0, 7.2:1) instead of `text-text-muted` (#666666,
3.3:1) for small text on carbon backgrounds.

### Runtime-Green Is Not Type-Green (B-5)
Vitest injects `describe`/`beforeEach` at runtime, so 321 passing tests coexisted
with 25 `tsc` errors (jest-style `jest.Mock` typings, un-imported `beforeEach`,
fixture objects missing required schema fields). `npm run typecheck` is now a
first-class gate and `test:all` chains vitest → tsc → playwright. Fixture typing:
use the schema's input-side type (`z.input`, e.g. `BankAccountInputParams`) when
testing zod defaults; construct full payloads when calling mutations typed with
`z.infer` output types.

## 2026-11-21 P3 Sprint — New Patterns & Lessons (session 7)

### Capacity Ceilings Are Schema-Level Contracts (C-1/H-03)
NUMERIC(10,4) capped every monetary value at S$999,999.9999 — below the S$1M
GST registration threshold, the product's own target market could not file an
F5 return. Lesson: for a financial schema, the INTEGER DIGITS of the money
type are a business-model decision, not a formatting detail. The conformance
gate now asserts DecimalField max_digits/decimal_places against
information_schema numeric_precision/numeric_scale — it caught the
pre-existing JournalLine.exchange_rate over-declaration (model said 19,6;
column is 12,6) on its first run. Schema is truth: align the model DOWN, and
never trust a model that over-declares.

### Generated Columns Block Their Inputs' Migration (§16)
`ALTER TABLE invoicing.document ALTER COLUMN total_amount TYPE …` fails with
`cannot alter type of a column used by a generated column` because amount_due
is GENERATED ALWAYS AS (total_amount - amount_paid) STORED. The migration
sequence is drop generated → alter inputs → re-add generated with the identical
expression — verified inside a transaction and rolled back BEFORE writing the
migration. Ship the in-place block with an idempotent guard (count remaining
10,4 columns; skip when zero) so re-runs are no-ops.

### Dead Hooks Signal Unfinished Wiring (D-1)
`useCreateInvoice` was fully implemented and 100% dead — zero importers — while
the form's onSubmit was a console.log stub. When a hook exists with no caller,
grep for its intended caller before writing a new one; the "TODO: Milestone 4"
comment in the form was the only pointer. The fix pattern: a PURE payload
adapter (`lib/invoice-submit.ts`, unit-testable without React) that maps form
state to the backend contract and drops computed preview fields (the server
recalculates authoritatively; the local invoice_number is display-only —
document_sequence owns numbering).

### One Auth Path for Everything (D-2)
The PDF hook built its own fetch with `localStorage.getItem("accessToken")` —
a second token reader that violated the zero-JWT-exposure mandate and was
broken anyway (the token lives in the api-client's module memory; storage was
never written → `Bearer null`). Refactor: extract fetchWithAuth (fetch +
401-refresh-retry) and build BOTH the JSON helpers and api.blob() on it. Any
new transport that needs auth goes through the client, never around it.

### Backend-Dependent E2E: Gate, Don't Break (D-5)
The default `npm run test:e2e` must stay green on a fresh clone with no
backend — specs that need one read E2E_API_URL and `test.skip(!apiUrl, reason)`
(philosophy inherited from PLAYWRIGHT_PROJECTS=all). `npm run test:e2e:full`
sets it. Sessions are memory-only (backend returns tokens in the body, sets no
cookie), so authed specs must walk the REAL user path with client-side
navigations only: UI login → dashboard → sidebar Link → page — a page.goto
after login drops the session. Native form validation is real in headless
chromium: an 8-char minLength silently blocks a short-password submit (no
event fires, no error shows) — check input constraints before debugging
"nothing happens". And the login rate limit (10/min per IP) accumulates across
dev iterations: flush the Redis cache when a full e2e run fails only on login.

### Radix Selects in jsdom Need Pointer-Capture Mocks
`target.hasPointerCapture is not a function` aborts Select option rendering
mid-interaction and masks real assertions. The setup now polyfills
hasPointerCapture/setPointerCapture/releasePointerCapture/scrollIntoView on
Element.prototype. Clicking options still races jsdom pointer-events — drive
selection via keyboard (`{ArrowDown}{Enter}`) in component tests, and prefer
`findAllByText` (Radix renders the selected label in the trigger AND the list).

## 2026-11-21 P4 Sprint — New Patterns & Lessons (session 9)

### The Three-Link Defect Chain (E-1)
"Sessions don't survive reloads" was three independent, mutually-compensating
defects: (1) the backend returned the token pair in the body and set NO
cookie — while the api-client header comment claimed "HttpOnly cookie" had
existed all along; (2) the frontend discarded the refresh token (login stored
access only); (3) `fetchWithAuth` gated the refresh on `&& accessToken`, so
even with a cookie backend the cold-reload retry could never fire. Lesson: a
comment describing nonexistent behavior is a defect detector — audit every
comment claim against the code it describes; and when a symptom spans
layers, hunt ALL links before fixing one (fixing link 3 alone would have
changed nothing). Acceptance test: a full `page.reload()` that stays on
`/dashboard` — not a passing unit test, the real browser event
(`e2e/session.spec.ts`).

### Evidence-Gated Refresh (E-1 refinement)
Refreshing on EVERY 401 — the "obvious" first fix — turned an anonymous
failure (bad login credentials) into a pointless refresh POST: it flooded
the refresh endpoint's rate limit (20/min per IP, structurally exceeded by
the e2e suite) AND the refresh-failure path (`window.location.href =
"/login"`) swallowed the login form's own error behind a hard redirect. The
e2e run caught what the unit tests blessed. Correct design: attempt the
refresh ONLY with evidence a session exists — an in-memory access token OR
the backend's non-secret, JS-readable `session_hint` marker cookie
(deliberately NOT HttpOnly, path=/; the HttpOnly refresh token stays
invisible to JavaScript). Dead evidence must be expired server-side (failed
cookie-refresh, logout, password change) or the browser keeps retrying a
dead session on every boot. Lesson: an auth client's 401 handler is a
state machine, not a reflex — write the anonymous-state test before the
expiry test.

### Settings-Driven Rate Knobs (rates)
django-ratelimit resolves `rate="module.callable"` dotted paths lazily per
request — decorator literals are NOT the only option. Production defaults
moved to `LOGIN_RATELIMIT_IP/USER` (identical 10/min + 30/min); only the
development settings raise the IP budget (60/min) because `test:e2e:full`
legitimately issues ~11 logins per run. The guardrail was never weakened —
only the local budget moved. Lesson: when a test suite structurally exceeds
a rate limit, make the limit a settings knob and document WHY the dev
value differs; never silence or disable the guard.

### Long-Lived Dev Servers in a Reaped Sandbox
The sandbox reaper kills detached background servers BETWEEN tool
invocations (silently — logs end mid-request with no traceback). Symptom:
a server that answered a health probe inside one command is gone by the
next. Countermeasure: run the whole e2e/screenshot session inside ONE
invocation — start backend + wait for readiness, let playwright's
`webServer` own the frontend, run, tear down in a trap. Also beware the
stale-survivor inverse: a `--noreload` dev server from a previous session
can still hold the port and serve OLD code (cookies missing, features
absent) — check `ss -ltnp` for the PID's start time and restart on
config/code drift before debugging the app.

### jsdom Cookie State Leaks Between Tests
`document.cookie` persists across tests within a vitest file — a hint
cookie set for one test silently flips the evidence gate for later
anonymous-state tests. Set the marker inside the test (or its beforeEach)
and CLEAR it in an afterEach with an expired-dated deletion — same hygiene
as token state, one tier lower in the stack.

## Session 11 Lessons (2026-11-21 — P5 Truth Restoration)

### Untracked Is Not Safe: git add -A Re-Tracks Ignored Files
The P1 sprint `git rm --cached`'d the env files; the P4 sprint's
`git add -A` re-committed them because a MODIFIED file that is already
tracked gets staged regardless of .gitignore (ignore rules only apply to
untracked files). The audit caught it. Countermeasures: (a) after any
`git add -A`, run `git ls-files | rg '\.env|\.pyc|dist/|\.bak'` as a gate;
(b) `git stash` + `stash pop` silently UNSTAGES staged deletions of
still-on-disk files (pop without --index restores everything to the
worktree) — re-stage and re-verify before committing; (c) commit
mechanical untracks in the SAME command block that stages them.

### ID-Type Seam Bugs Hide Between Layers
`transmit_peppol_invoice_task(log_id, org_id)` called
`transmit_invoice(invoice_id, ...)` — both UUIDs, both strings, no type
error, no test: the auto-transmit path could NEVER succeed and left the
pre-created log PENDING forever. When two layers exchange opaque ids,
each side must name its parameters for the ROW it means
(`transmission_log_id` vs `invoice_id`) and the seam method should
re-fetch the row it owns. Unit tests that mock the service and assert
`assert_called_once_with(log_id, org_id)` merely encode the bug — test
the SEAM's observable effect (the log row's final status), not the mock's
call shape.

### Compliance Paths Fail Closed — Including GL Resolution
Broad `.first()` over `Q(account_type="ASSET")` posted output tax to
2200 Accrued Expenses and could land AR on a header account. The fix
(exact code → name → sub-type, ValidationError otherwise) follows the
P2 lesson #17 (never guess a rate) generalized to accounts. The test
fixture itself carried the wrong account map (2200 named "GST Output
Tax") — when a domain constant is wrong in code, sweep the FIXTURES too.

### Fixtures Can Mask Generated-Column Semantics
`transmitted_at` is `auto_now_add` — a test that passes an explicit value
on create() gets it silently discarded (the row stamps NOW). Use
`queryset.update()` to bypass auto timestamps when you need historical
times. Same class as the phantom-attribute anti-pattern: what the ORM
accepts and what the DB does are different contracts.

### Cache Invalidation Is Part of the Mutation Contract
A 5-minute dashboard cache with an `invalidate_dashboard_cache` method
that has ZERO production call sites is a stale-data bug dressed as a
feature. Every mutation service that changes dashboard-visible state now
calls the invalidator (local import, exception-guarded so a cache hiccup
can never fail the mutation). When you add a cache, grep for the
invalidation call sites in the same commit.

## 2026-11-22 P7 Sprint — New Patterns & Lessons (session 14)

### The Wrong Settings Key Is a Silent Dead Integration (F-19)
`REST_FRAMEWORK["DEFAULT_EXCEPTION_HANDLER"]` is not a DRF setting — the key is
`EXCEPTION_HANDLER` (not namespaced under DEFAULT_*). The custom exception
handler therefore NEVER ran: every LedgerSGException that wrap_response
re-raises (UnauthorizedOrgAccess, GST calculation, Peppol transmission)
surfaced as an unhandled 500 instead of its mapped status code. The tell: an
in-view permission raise produced 500s while middleware-raised ones produced
403s. Gate integrations by their resolved value, not the settings dict
(`tests/security/test_settings_gates.py::test_custom_exception_handler_is_active`).

### Permission Literals Come From the Gated Vocabulary (F-2)
The status-transition view checked `elif new_status == "VOIDED"` — the enum
value is VOID — so the CanVoidInvoices branch was dead code and ANY org member
could void ANY document through `/status/`, bypassing the guarded `/void/`
endpoint. Fix pattern: `ChoiceField(choices=Model.STATUS_CHOICES)` (wrong
literals become 400s) + a per-target-status permission map + payment-derived
statuses (PAID/PARTIALLY_PAID) refused outright on generic endpoints — the
allocation service owns them.

### Advertised Serializer Fields Must Survive Receipt (F-3)
The org-create serializer declared `address` — the Organisation model has no
such field — so POSTing it (a field the API itself advertised) crashed with a
TypeError 500. The PATCH twin was the P6/F-10 fix; always sweep BOTH paths of
a serializer pair.

### Error Envelopes Are Contracts (F-7)
The api-client read `errorData.message || errorData.detail` — the backend
envelope is `{"error": {"code", "message", "details"}}` and DRF field errors
are `{"field": ["msg"]}`. Neither key existed, so every business-rule failure
surfaced as "Request failed: Bad Request" — which is exactly what hid the
always-broken Void button (F-1: the page sent `reason: ""` and every void
400'd). Parse the real shape and test the parser against both shapes.

### Shadowed URL Modules Keep 404-ing Routes Alive (F-4)
`apps/core/urls.py` (module) is shadowed by `apps/core/urls/` (package) — the
three fiscal routes lived only in the dead module, so the frontend's calls
404'd. The same class bit set-default-org in P2 (NEW-3). When a route 404s,
check WHICH urls file actually resolves before adding routes to the wrong one.

### Dead Hooks: Wire or Delete, Never Leave Both (F-13)
`useInvoicePDF` and `useSendInvoiceNow`/`useInvoiceNowStatus` sat fully
implemented with zero importers beside REAL backends (P3/D-2, P5/C-2) — now
wired as actions on the invoice detail page. The mock-era edit route and the
stale `lib/server/api-client.ts` were deleted truthfully (the edit route would
have created a duplicate contact + invoice if reached by URL). Every sprint:
grep zero-importer hooks and decide wire-vs-delete explicitly.

### Query Params Are Untrusted Input Too (F-11)
Malformed `date_from`/UUID/int query params raised raw ValueError/
InvalidOperation -> 500 at every audited list endpoint, and banking's
tolerance probe silently DEFAULTED garbage via a bare `except:`. Shared
helpers (`common.query_params.parse_*_param`) map them to clean 400s with the
param name in the message.

## 2026-11-22 P8 Sprint — New Patterns & Lessons (session 16)

### Copy a Permission Pattern Only After Listing the View's Verbs (G-1)
The P7/F-10 `get_permissions()` pattern (gate PATCH, keep GET member-
readable) was applied to `GSTRegistrationView` — which has no PATCH: its
mutations are POST/DELETE. Class-level `CanManageOrg` was removed, and any
member could register/deregister the org for GST. Before transplanting a
hardening pattern, enumerate the target view's mutating verbs.

### The Advertised Map and the Enforced Set Must Be One Contract (G-3)
`STATUS_TRANSITIONS` (served to clients) advertised DRAFT/PAID/OVERDUE→VOID
while `void_document` accepted only APPROVED/SENT/PARTIALLY_PAID. An
OVERDUE invoice could be voided through NO endpoint; DRAFT/PAID users saw
a Void button that always 400'd. The accepted set now equals the
advertised one, PAID is refused with credit-note guidance, and payment
allocations must be released before any void (no orphaned allocation rows).

### A Serializer Field Is a Promise (G-6)
`InvoiceSendSerializer` validated `cc`/`bcc`/`message` while the email
task received only `to` — the frontend actively sent `message` and it was
silently dropped. Fields either deliver end-to-end or leave the contract.

### The Schema Seed Is the Source of Truth for Sequences (Q-3)
Python-hardcoded prefixes (QUO, PINV) drifted from the seeded
`core.document_sequence` (QT-, BILL-). Align Python to the schema; issued
numbers are stored values and unaffected.

### Phantom-Field Assignment Fails Silently (Q-1)
`quote.converted_to_id = invoice.id` set a transient attribute that
`save()` discarded — the conversion link never reached the DB. Persist
through the real FK (`related_document`) and regression-test via
`refresh_from_db`.

### Report Aggregates Need Every Account (R-4)
P&L/BS aggregate via `account_type_ref__code`, but `create_account` never
set the FK — an org's own revenue account was invisible to its statements.
New accounts link the coarse FK through `GROUP_TO_COARSE_TYPE` (the
groups' `category` field is too coarse: COS's category is EXPENSE).

## 2026-11-22 P9 Sprint — New Patterns & Lessons (session 18)

### The Wire Contract Lives in Three Places (B-4 follow-up)
The bank-account dialog's unit test passed, the zod schema validated, and
the live POST still 400'd: the payload sent `paynow_type: null` and the
ModelSerializer rejected null while the DB column is nullable (the CHECK
allows NULL or UEN/MOBILE/NRIC — "" violates it). Pin the exact payload
in the unit test AND keep a live e2e that posts it; "null vs omitted vs
empty" is decided by the schema, not by the serializer's default.

### A Structural List Default Can Hide Filtered Rows (C-4 follow-up)
`list_accounts` defaulted to top-level-only (`parent__isnull=True`) even
with an `account_type` query — and the seeded bank accounts are CHILDREN
of the 1000 header, so the dialog's GL picker was empty while every test
passed (fixtures were top-level). When a filter narrows by type or flag,
lift the structural default; test against the SEEDED shape.

### Writer Specs Need Serial Execution (the live gate)
`fullyParallel: true` raced the banking workflow's three chained tests
against each other and against the reader specs on one shared dev DB.
Chains get `test.describe.configure({ mode: "serial" })`; runs that
mutate shared state get `--workers=1`. Overlay dialogs collide with the
page behind them in strict mode — scope locators to the overlay.

### Locator Semantics (the small print)
`get_by_role(name)` matches substrings, but "Add Account" is NOT a
substring of "Add Bank Account" — either-branch locators need a regex
alternation. And the payment sequence emitted `RCP-` where the seed table
suggested `REC-` for PAYMENT_RECEIVED: assert on values read from the
system, never on prefixes assumed from config.

### Orphaned Dev Servers Serve Stale Code (the debugging trap)
Killing the npm wrapper leaves `next-server` holding port 3000; a stale
Django runserver kept serving the pre-fix serializer while the "fix
didn't work" was being debugged. Teardown pkills the process tree, and
the first debugging step for a failed fix is verifying the port serves
the changed code.

### The e2e Phase Is a Finding Source, Not Just a Gate
Three production defects surfaced only in the live runs: the null-PayNow
contract break (mocked tests passed), the deep-link tab default
(PaymentsTab reads params it never sees — the tab never mounted), and the
is_bank children invisibility. Budget for e2e iterations; treat each
failure as a lead-verify-then-fix cycle, not as flake.

## 2026-11-23 P10 Sprint — New Patterns & Lessons (session 20)

### A Mount-Time Session Check Must Know Which Pages Are Public (H-2 follow-up)
The auth-provider's `checkSession` runs on every page, including public
ones — and treated the anonymous 401 an unauthenticated visitor gets from
/auth/me like session expiry: clearAuth + redirect to /login. The
registration form only ever worked by winning that race (the e2e click
landed mid-navigation, "element detached"). Redirect guards need the
public-route exemption list as explicit as the loop guard (/login) already
was.

### A Rate-Limit Block Must Not Masquerade As An Authorization Failure (LG-2)
django-ratelimit's `Ratelimited` is a bare `PermissionDenied` subclass; on
a DRF view it fell through the fallback handler as 403 "You do not have
permission to perform this action." Clients cannot distinguish throttling
from authz — and the frontend api-client treats 403 as an auth failure and
bounces to /login mid-spec. Map it in `custom_exception_handler` to the
documented 429 contract (code, retry_after, Retry-After header). When you
raise a rate budget, remember EVERY knob: the login IP budget was raised in
P4 and the refresh IP budget in P6, but the per-user login budget was
missed and blocked the grown suite's tail.

### Settings Modules Must Copy-On-Write Their Base Structures (LG-4)
`development.py` did `INSTALLED_APPS += [...]` and `MIDDLEWARE.insert(...)` —
in-place mutations of the module-level lists `from .base import *` shares.
Importing development.py into ANY process running other settings (a test
asserting its knobs) injected debug_toolbar into the live app registry
mid-run and crashed middleware loading — a 79-test cascade that looked like
everything and was one file. The file already documented the rule for
REST_FRAMEWORK ("Copy-on-write: never mutate the shared base dict") — the
rule applies to every shared structure.

### Serializer-Guarded Endpoints Need The Guard On Every Path (LG-5)
`core.organisation.uen` is UNIQUE at the DB level, but only the CREATE
serializer validated it — the detail PATCH is a raw request.data allowlist
(no serializer at all) and the settings PATCH passes no instance. A taken
UEN was an IntegrityError 500 on all three paths. When a constraint guard
exists, enumerate every writer path (including raw allowlists) and share
the check (`ensure_uen_available(uen, exclude_org=…)`).

### Verify Raw Bytes Before Declaring Corruption (M-11 correction)
The "corrupted CI trigger" (`branches: ain]`) was a tool-DISPLAY artifact:
the output layer eats the byte sequence `[m` when rendering text. The file
on disk was always intact (`od -c` ground truth at both commits). Before
acting on "corruption" seen through a tool, check the raw bytes; and when a
finding turns out to be an artifact, correct the record explicitly (the
corrective commit) rather than leaving the false history in place.

### e2e Specs Must Not Depend On Fixture Names From Other Eras (LG-6)
The banking statement spec filtered on "Marina" — a P9-era fixture name
that silently depended on the dev-DB bootstrap's customer naming; it broke
the moment P10's bootstrap named a customer differently. Specs against a
persistent dev DB must generate run-unique data (timestamps in
descriptions/references) and assert on values read from the system, and
duplicate-looking headings (a shell breadcrumb h2 next to each page's h1)
belong to ONE heading per page — demote the decorative one to aria-hidden.

## 2026-11-23 P12 Sprint — New Patterns & Lessons (session 25)

### A "Suspicious" Computed Style Gets A Rule Trace Before A Bug Claim
The mobile-nav toggle read `display:flex` while wearing `md:hidden` +
`inline-flex` — looks like a Tailwind v4 cascade defect. The matched-rule
trace (walk `document.styleSheets`, keep rules whose selector the element
matches and that set `display`) showed only `.inline-flex` and the
media-gated `.md\:hidden` — and `display:flex` is the CORRECT CSS
blockification of an inline-level child of a flex container (the header).
Trace the cascade before claiming a framework bug; also verify the setup
class first (this repo: `@import "tailwindcss"` + `@theme`, no legacy
config — the #1 v4 failure mode).

### An Open Mobile Menu Owes The Overlay Contract (A-1)
The §9.4 mandatory set (skills/nextjs16-tailwind4): Escape closes, focus
traps inside, body scroll locks, focus returns to the trigger. The shipped
floor: a document keydown listener mounted while open (Escape + Tab wrap
handling), a `useEffect` on the open flag locking `body.style.overflow`
with cleanup, a prev-state ref returning focus to the toggle, and focus
moved into the sidebar on open. Every behavior shipped with its failing
test first (6 RED → 7 GREEN) plus gated e2e specs — the live re-verification
confirmed all four behaviors in the real browser.

### Lint Parity On Touched Files Silently Drifts The Whole Tree (A-3)
The documented register said "47 no-explicit-any findings"; the truthful
whole-tree state was 79 (36 any + 30 unused-vars + 13 react-hooks-v7
classes). Parity checks on touched files catch NEW debt but hide ACCUMULATED
debt — measure the full count every sprint, clear the mechanical classes
(30 unused imports/vars, a dead `mounted` gate, a `catch (error)` with an
unused binding, an in-render tooltip component definition, a type-only
const object), and re-register the honest remainder (45 post-P12).

### Playwright Accessible-Name Matching Is Substring (A-2 spec lesson)
`getByRole('link', { name: 'Ledger' })` resolved to TWO elements — the
Ledger nav link AND the logo ("L LEDGERSG" contains "LEDGER") — and the
strict-mode violation read exactly like an app bug (click "did nothing").
Scope to the landmark and use `exact: true` when a nav item's name is a
substring of another element's accessible name; the error context yaml
names both matches — read it before diagnosing the app.

## 2026-11-23 P11 Sprint — New Patterns & Lessons (session 23)

### A Document-Type Branch In The Posting Engine Must Be Verified PER TYPE (C-1)
`post_invoice` served SALES_INVOICE and SALES_CREDIT_NOTE identically — a
credit note DEBITED the customer's AR instead of crediting it, and the F5
computation counted quotes as supplies while ignoring credit notes. The
books overstated receivables and GST on every credit note since the posting
engine shipped. TDD direction assertions belong PER document type (every
journal line's debit/credit side), and statutory computation must net the
contra documents. The live gate proved it at the ledger level: invoice
AR-debit 2725.00 vs credit note AR-CREDIT 817.50, F5 Box 1 = 3500.00 with
credit notes netting.

### An Edit Dialog Prefills From The Payload Its Save Writes (H-1 + M-3/M-4)
The contacts dialog prefilled from the LIST row's serializer — uen,
peppol_id, gst_reg_number and address rendered BLANK, and an unconditional
eight-field save erased the stored values with a success toast (Peppol ID
loss breaks InvoiceNow). The dialog now prefills from the DETAIL endpoint
(the payload the PATCH actually accepts), `gst_reg_number` is a DECLARED
serializer field (undeclared fields are silently dropped by DRF — the save
reported success and persisted nothing), and the search debounces. The
regression test round-trips: open → prefill assertions → save → API re-read.

### Panel Keys Must Match The Backend Contract Byte-For-Before (H-2 + M-1)
The F5 boxes panel read idealized `box1` keys while the serializer sends
`box1_std_rated_supplies` — every box rendered "—" because the lookup
matched nothing. Key lists get PASTED from a real API response, never
written from memory, and the live e2e asserts a monetary value renders
(catches the whole class). Same class: the deadlines endpoint's envelope
and the REVIEWED deadline filter — contract tests on BOTH sides of a wire.

### One Knob Per Behavior; Production Imports Only What Production Installs (C-2 + H-5)
Two crashes from the same disease: production's CACHES declared
`django_redis` (a dev extra never in the production dependency set — the
first cache touch crashed the boot) while debug_toolbar had TWO gates
(INSTALLED_APPS keyed on DEBUG_TOOLBAR, urls.py on DEBUG — the unreachable
quadrant DEBUG=true+DEBUG_TOOLBAR=false raised ImportError). Production
settings are now booted by a settings-gate test that imports the module
and round-trips the cache; every behavior has exactly one gate.

### Silence Assertions Scope To The Actor; e2e Fixtures Self-Create (live gate)
The failed-login audit test asserted NO LOGIN rows anywhere — the live
gate's legitimate demo-user logins into the SHARED dev DB broke it (scope
to the test's user, matching the positive test). The register throttle's
hardcoded 5/hour literal 429'd the self-serve e2e spec on the 6th full-suite
re-run — the P4/P6 knob pattern (settings knob + dev budget + posture gate)
applies to EVERY throttle. The banking payment spec consumed its own
fixture (the previous run settled the invoice) — specs that consume their
fixture create their own via idempotent ensure* helpers.

### Compute From The Raw Value, Never The Display String (H-4 + M-7 + L-2)
The dashboard chart fed `parseFloat("SGD 315.00")` → NaN → 0 while the GST
payable card was hardcoded to 0.00 — and six sites rendered "S$ SGD x.xx"
double prefixes. The API ships both the raw value and a `*_display`
string; anything that COMPUTES reads the raw one (the GST payable is
re-sourced from the F5 computation — single statutory truth), and the DOM
renders single-prefix display strings.

## 2026-11-24 P13 Sprint — New Patterns & Lessons (session 27)

### The DRF Exception Handler Is Inside The Transaction (B-1 — the C-04 closure)
`wrap_response`'s careful re-raise was nullified ONE LAYER UP: the custom
DRF exception handler's 500 fallback returned a normal `Response`, DRF's
dispatch accepted it, and Django's ATOMIC_REQUESTS wrapper saw a
"successful" request → partial writes COMMITTED. Fix: `transaction.set_rollback(True)`
before returning the 500 envelope (guarded by `in_atomic_block`). Lesson:
a typed-exception contract must be audited at EVERY layer the exception
can be caught — the handler is the last catch before the transaction
boundary, and it is inside the request transaction.

### Rounding Quantum Bugs Hide Behind Round Fixtures (B-2)
`Decimal(f"0.{('0' * rounding)}1")` built `0.001` for rounding=2 — one
decimal place too fine — yet every existing GST test passed because the
fixtures used round amounts (100.00 × 0.09 = 9.000 at BOTH quanta).
`Decimal(1).scaleb(-rounding)` is the correct unit. Lesson: statutory
rounding gates need SUB-UNIT fixtures (100.05, 100.06) or they verify
nothing; the same applies to tolerance gates (see B-13: the service
tolerance 0.001 vs the DB trigger's 0.0001 — test at the boundary).

### Value-Masked Mutation: Settings Copy-On-Write Gates Must Assert Identity (B-7)
The first B-7 test compared VALUES (base's DB name before/after importing
development) and PASSED — a `.env` file resolved both sides to the same
string, masking the shared-dict mutation. Assert OBJECT IDENTITY
(`dev.DATABASES is not base.DATABASES` and the inner dicts too): value
comparisons can be masked by config resolution; identity cannot.

### Middleware Headers Override next.config Headers (H-1 — the silent CSP defeat)
Next.js applies `next.config.ts headers()` and then the middleware sets
its own on the response — for the same header key, MIDDLEWARE WINS. The
repo shipped two definitions; the looser one (unconditional
`'unsafe-eval' 'unsafe-inline'`, Vercel origins) silently defeated the
P11/M-15 env-aware hardening in production while every unit test passed
(the table was correct — the SERVED header wasn't). Fix: ONE source of
truth (delete the middleware; port its unique headers into
`next.config.ts`); gate the header table with a unit test that stubs
NODE_ENV, and verify the SERVED headers live. Deleting the middleware
also retired the Next 16 middleware→proxy deprecation warning.

### Off-Canvas ≠ Unfocusable (H-2 — the inverse P12 lesson)
P12 hardened the OPEN menu; the audit then found the CLOSED drawer
still keyboard-focusable — `transform` moves an element off-screen but
NOT out of the tab order or the a11y tree (~10 invisible focusables
before the header at 375px; WCAG 2.4.3/2.4.7). Fix:
`invisible md:visible` on the closed state plus
`transition-[transform,visibility]` (visibility is discretely-animatable:
closing stays visible through the slide-out, opening flips visible
immediately). Lesson: test BOTH states of every overlay; and a nice
proof artifact — a role locator CANNOT resolve the hidden link (a11y
tree exclusion), so the e2e spec switched to a CSS locator for the
closed-state assertion.

### Z-Index Stacking Is A Layout Fact jsdom Cannot See (M-1)
The overlay (z-40) painted ABOVE the header (z-30): the X toggle was
blurred and unclickable while the menu was open, and NO unit test could
catch it (jsdom has no layout/hit-testing) — only the overlay's own
onClick-close masked it. Fix: header z-50 (DOM order after the aside
paints it above z-40) + an e2e hit-target assertion
(`document.elementFromPoint` at the toggle's center resolves to the
toggle's button). Lesson: pointer-target bugs need real-browser
elementFromPoint probes; add one for every z-index fix.

### Mutation Retries Are Double-Submission Hazards (M-3)
`mutations: { retry: 1 }` re-fires failed POSTs — including 4xx on
non-idempotent payment endpoints. A network timeout after the server
processed a payment re-sends it. Fix: `retry: 0` for mutations (React
Query's default); idempotency keys belong on the backend if retry-on-
mutation is ever needed.

### Per-Glob Coverage Thresholds Make Tier Claims Enforceable (M-4)
The vitest header claimed "lib/gst-engine.ts: 100%" but nothing enforced
it, and the whole-suite ratchet averaged over 57 excluded files. Vitest 4
glob-keyed thresholds (`"src/lib/**": {…}` at the measured floor) turn
the tier claim into a gate. Lesson: set the glob ratchet at the MEASURED
floor (never aspirational), then bump.

### The Lint Debt Parity Lesson, Applied To A Debt Class (W-3)
P12 measured whole-tree drift (79 vs the documented 47); P13 cleared the
remaining 36 `no-explicit-any` — 35 were copy-paste test-cast debt
fixable with the `as unknown as ReturnType<typeof hook>` pattern already
proven in-file, and exactly ONE was production code needing the real
type. Lesson: classify a debt class before fixing it — most of a debt
class is usually mechanical, and the mechanical fix pattern often already
exists in the same file.

### Environment Lesson: Daemonized Dev Stack Survives Tool-Call Boundaries
The sandbox kills descendant processes at tool-call end, but TRUE daemons
(pg_ctl, redis --daemonize) survive. A ~60-line double-fork daemonizer
(os.fork + setsid + fork + exec with stdio to a log) gives `runserver`
and `next dev` the same survival — the one-call constraint of earlier
sessions no longer forces servers+audit into a single call. Next dev
needs a manual restart for next.config.ts changes (HMR covers source
only).


## 2026-11-26 P15 Sprint — New Patterns & Lessons (session 30)

### A Partially-Committed Sprint Is a Tree-Corruption Vector (R-0)
The interrupted session-29 committed its P14 work to wrong paths: the real
Payment MODEL file was overwritten with the payment SERIALIZER (a circular
import killed `manage.py check`), while the C-1/C-2/H-05b fixes sat
stranded at `apps/backend/` root where no import could reach them. Lesson:
when a session is interrupted mid-commit, the NEXT session must first
verify the tree boots before building anything on it — `manage.py check`
is the cheapest possible corruption probe, and `git show <commit>~1:<path>`
is the ground truth for what a file should contain. Repair = restore the
destroyed file from the parent commit + relocate the stranded fixes (diff
first — port the FIX BLOCKS into the canonical files, do not adopt
wholesale rewrites that diverged from canonical).

### Never-Run RED Suites Carry Their Own Bugs (R-0.7)
The P14 test files had never executed (the backend could not boot). Five
test-side defects surfaced only at first run: a DRF-vs-LedgerSG
ValidationError import mismatch, a fixture that created a duplicate fiscal
year (UNIQUE violation), approve-path tests that skipped the state
machine, posting fixtures without document lines, and a cursor-spy that
reursed when Django used the cursor outside a with-block. Lesson: a RED
suite written blind is a HYPOTHESIS batch — diagnose every failure as
either a genuine implementation gap (write the fix) or a test-side bug
(fix the test), and never treat the batch as uniformly correct.

### RLS Completion Must Account for the Pre-Context Reads (§17c)
Enabling RLS on `core.role` with org-scoped-only SELECT broke EVERY
org-scoped request: the middleware attaches `request.org_role` BEFORE the
org context is set — the role row vanished behind the policy and every
permission gate saw an empty role. Lesson: enumerate every pre-context
read path (login, org-list, the membership+role attach) before choosing
policy predicates; NULL-context SELECT on the membership/role tables is
the documented tradeoff (the app-layer membership checks remain the gate).

### lxml Parser Flags Are Write-Only (X-1)
`etree.XMLParser(resolve_entities=False, ...)` accepts the flags but the
parser object exposes NONE of them for reading — a config gate that
asserts `parser.resolve_entities is False` fails on a missing attribute.
Ship the policy as a module-level constant the parser is built from and
gate THAT (single source of truth).

### The M-Form GST Number Has Two Documented Lengths (M-1)
The OECD TIN guide specifies ASGD = ANNNNNNNC (9 chars — M + 7 digits +
check letter), while real IRAS-issued numbers on company documents are
M + 8 digits + check letter (10 chars, e.g. M90356174N). Accept both
(`^M\d{7,8}[A-Z]$`); inventing a checksum remains the registered P16
decision. Lesson: when authoritative sources disagree on a format's
length, accept the union unless one form is provably dead — a validator
that rejects real numbers is worse than one that accepts both.

### npm audit fix --omit=dev PRunes the Dev Tree (H-8 follow-up)
Running `npm audit fix --omit=dev` removed vitest/playwright from
node_modules (the flag filters what gets INSTALLED, not just what gets
AUDITED). The fix: run the audit fix, then a plain `npm install` to
restore devDependencies — verify with the dev bins before running gates.

### A Dup-Definition Serializer Is the F811 Tell (M-4)
Adding a "new" InvoiceLineCreateSerializer without checking for an
existing one created a silent shadow (the second definition wins — the
P5/A-6 anti-pattern in class form). The lint warning (F811) caught it
before it shipped a behavior change to the line-add endpoint. Lesson:
grep for the class name before defining a serializer; lint parity on
touched files is a functional gate, not a style gate.


## 2026-11-26 P16 Sprint — New Patterns & Lessons (session 32)

### A Static Production CSP Can Kill Hydration Silently (FE-C1 — the Critical)
The production branch shipped `script-src 'self'` while EVERY prerendered
page carried non-nonced inline bootstrap scripts (`<script id="_R_">`, the
`self.__next_f.push(...)` flight payloads) — browsers blocked them and the
shipped production app was inert server HTML. No test could catch it: the
whole suite runs against `next dev` (whose CSP allows unsafe-inline), so
the production CSP branch had ZERO coverage. Lessons: (a) a security
posture that breaks the app in the untested mode needs a smoke test IN
that mode — `scripts/prod-csp-smoke.js` builds standalone, boots it and
asserts nonce + hydration + zero violations; (b) the nonce mechanism
requires DYNAMIC rendering (the root layout opts into force-dynamic — the
per-request cost is a thin shell for a login-gated dashboard); (c) keep
the CSP in ONE place (proxy.ts + lib/csp.ts) — the P13/H-1 override trap
applies to any second source.

### A From-Scratch Middleware List Is a Drift Bomb (BE-H1)
`config/settings/service.py` rebuilt MIDDLEWARE by hand "for performance"
and silently dropped TenantContextMiddleware + AuditContextMiddleware +
CSP + WhiteNoise — the Docker/script API path would have served every
org-scoped request with no org context (403s, RLS NULL) and no audit
attribution. Derive from base (`MIDDLEWARE = list(base.MIDDLEWARE)`) and
gate EVERY HTTP-serving settings module on the four entries (a
parametrised settings-gate test).

### The Fix That Missed Its Wire Twin (BE-H2)
The P14 instalment fix landed in the SERVICE and the embedded-path
serializer, but the dedicated `POST /payments/{id}/allocate/` endpoint's
own serializer kept the stale APPROVED-only literal — the contract tests
called the service directly and never exercised the wire. When fixing a
contract, enumerate every entry point that enforces it (service,
embedded serializer, dedicated serializer, view) — and test through the
wire, not just the service.

### Query-Key Conventions Are Type Systems (FE-H1)
The dashboard page keyed its query `["dashboard", orgId]` while every
mutation invalidated `[orgId, "dashboard"]` — TanStack prefix matching
requires the key to START with the prefix, so all 10 invalidations were
silent no-ops. The correct hook existed the whole time with zero
importers. Lesson: assert the key convention at the consumption site (a
render test that reads the QueryCache), and grep for zero-importer hooks
that already encode the right contract.

### Closures Capture The List They Were Built With (FE-H2)
`useCreateOrganisation.onSuccess` ran `refreshOrganisations()` then
`switchOrg(org.id)` — but the `switchOrg` in the closure held the
PRE-creation organisations list (empty for a fresh registrant), so the
lookup guard silently skipped the selection AND the persist. State
updates do not rebind variables in already-running closures. Lesson:
mutation callbacks that depend on post-mutation state need an API that
takes the id directly (selectOrgById), not one that re-reads state.

### The Frontend Must Not Be Stricter Than The Backend (FE-H3)
The frontend UEN regex accepted only 2 of the 3 ACRA formats while the
backend validator accepted all three — an LLP customer failed invoice
validation for a number the backend itself considers valid. Mirror the
backend's vocabulary in the shared frontend schema, and delete dead
duplicates of validators (a second `isValidUEN` carried the same wrong
regex with zero importers).

### money() Must Reject Non-Finite (BE-M2)
`Decimal("NaN")` parses cleanly and `quantize()` propagates NaN without
raising — a NaN box override could be FILED into the statutory record
through the `{k: Decimal(str(v))}` parse. Every decimal seam needs an
`is_finite()` gate (and the gate belongs in `money()` itself, plus at the
parse sites that bypass it).

### Small Honesty Fixes Ride Together (the L-batch)
The payment-void reversal date is `timezone.localdate()` (UTC dates
diverge 00:00–07:59 SGT); releasing an InvoiceNow-sent document's last
allocation restores SENT (evidence-based, not blanket APPROVED — the
email-only residual is registered); the CSV latin-1 fallback must read
bytes ONCE (a re-read of a consumed stream returns b"" and "successfully"
imports 0 rows); a docstring that overstates wiring (period_lock) is a
defect in the next auditor's model of the system — fix it in the same
commit as the truth.


## 2026-11-27 P21 Sprint — New Patterns & Lessons (session 42)

### The Bare Array Was The Envelope Debt In Miniature
`/auth/organisations/` returned a raw JSON array while every sibling
list spoke `{results, count}` — the frontend org-selector, the e2e
helpers, and the bootstrap script each carried their own dual-shape
fallback. Unifying to `{results, count}` (reports keep `{data: {...}}`:
*lists → results, reports → data*) deleted three fallbacks and made the
pagination prerequisite real. Lesson: an envelope inconsistency
multiplies consumers that must "handle both" — each fallback is a small
lie that survives the unification and then becomes dead code.

### on_commit Is The Only Honest Cache-Invalidation Point
Deleting a cache key INSIDE the open transaction re-seeds the stale
value in the delete→commit window (a concurrent read re-populates from
the still-pre-commit DB; the value then survives to TTL).
`transaction.on_commit` is the correct hook — and it fires immediately
in autocommit contexts, so non-transactional callers keep working. The
pytest probe: `django_capture_on_commit_callbacks(execute=False)` +
assert the spy was NOT called inside the block, then execute the
captured callbacks and assert it fired. (Gotcha the first probe hit:
the `patch` context must WRAP the capture — exiting the with-block
undoes the spy before the callbacks execute.)

### A Dead Evidence Column Is A Dead Branch
`invoicenow_sent_at` existed in the schema and model, was read by the
void/unallocate restore ("SENT" if stamped else "APPROVED") — and was
written by NOTHING. The branch was untestable dead code. Stamping it
on the DELIVERED transmission (one `.update()` with an `isnull=True`
filter — stamp-once, no status write) resurrected the designed behavior
without touching the transition map.

### The Vacuous-Assert Trap, Envelope Edition
`test_rls_isolation.py` read `response.data.get("data", [])` against
the accounts list — which returns `{results}`. The fallback produced
`[]` and the "other org's account is not visible" assertion ALWAYS
passed, even if isolation broke. When an envelope changes, grep the
tests for the OLD key with a default — a `.get(old_key, default)`
assert is a test that verifies nothing.

### Keyboard Reachability: sr-only, Not display:none
The CSV import's `<input type="file" className="hidden">` removed the
input from the tab order AND the a11y tree — the visible label was the
only affordance and it wasn't focusable. `sr-only` keeps the input
focusable + labelled (Enter/Space opens the picker natively) while the
label's click target still works. The e2e masked the bug
(`setInputFiles` bypasses the UI) — a DOM-attribute probe
(className + label association) is the honest unit contract.


## 2026-11-27 P23 Sprint — New Patterns & Lessons (session 44)

### A Functional Contract Can Hide A Dead Animation
Thirteen consecutive mobile-nav settlements asserted the functional
contract (state, visibility, focus, scroll-lock, overlay, Escape) — all
green, and all blind to the drawer's 300ms slide never interpolating:
Tailwind v4 animates `translate-x-*` through the STANDALONE `translate`
CSS property, and the drawer's `transition-[transform,visibility]`
omitted it (the same Trap 5(b) family as the P18 animate-in bug — the
utility compiles, the consumer just never references it). The probe
gap: nobody asserted the property the engine actually animates. Lesson:
an animation contract needs its own gate — pin the compiled
`transition-property` token in a unit test AND the computed
`transitionProperty` in a real browser (the e2e spec), or a future
class edit silently re-drops the property with every suite green. The
compile proof (`npx @tailwindcss/cli`) is the one-command ground truth
for "does this utility compile to what I think it compiles to".

### The dev-tier advisory that IS worth a controlled bump
`npm audit` reported 2 criticals in vitest 4.0.18 — dev-tier, so the
P22B decision was defer-everything. But the fix release (4.1.12) sat
inside the existing caret range (a minor bump), and the full gate
matrix was runnable in-session: probe the bump `--no-save`, run the
whole suite, then commit the pin only if green. That closed both
criticals with re-verified evidence — the distinction that matters is
NOT dev-tier vs production, it's "fix available inside the declared
range + gates runnable" vs "needs major bumps". The remaining 17
findings (typescript-eslint/vite/undici chains) are the second kind —
still deferred, now with the boundary drawn.

### The Role Password Is Test-Visible Environment State
Running `ALTER ROLE ledgersg_app PASSWORD …` for an rls_smoke setup
broke two RLS tests on the next pytest run — the tests hardcode the
schema's documented dev default (`CHANGE_ME_IN_PRODUCTION`) exactly as
the schema comments promise. The failure looked like a code
regression (it appeared right after a code change elsewhere) but was
pure environment state. Lesson: on a red suite, FIRST inventory what
environment state changed since the last green run; role passwords and
other DB-level state are invisible to `git status`. And when a probe
changes role state, restore it before the next gate run.

## 2026-11-27 P24 Sprint — New Patterns & Lessons (session 45)

### The Page Identity Must Live In The queryKey
Adding `offset` to a paginated fetch WITHOUT adding it to the TanStack
queryKey makes every page resolve the FIRST page's cache — the table
silently shows the wrong rows with no error anywhere (the exact
silent-wrong-data class). The behavioral pin: render two different
offsets under one QueryClient and assert BOTH URLs were fetched and the
page-2 data differs from page-1. Query-key conventions are type
systems (the P16/FE-H1 lesson, now with a second concrete instance).

### An Additive Envelope Beats A Flipped Default
Pagination could have shipped as a capped DEFAULT (every list capped at
N rows) — one line per view. It would also have changed the contract
for every existing consumer at once: the e2e specs, the bootstrap
script, rls_smoke, five frontend hooks. The additive shape — `limit`
absent → the response byte-identical `{results, count}`; `limit`
present → `{results, count, next, previous}` with count as the TOTAL —
cost one extra branch per view and broke nothing (the full matrix
re-ran green, zero consumer changes). Flip the default only after
every consumer passes an explicit limit.

### Pagination Requires A Deterministic Total Order
`order_by("name")` (contacts) and `order_by(-payment_date, -created_at)`
(payments) carry no unique final key — Postgres tie order is not stable
across EXECUTIONS, so a page boundary can skip or duplicate a tied row
(two same-name contacts, two same-instant payments). Every paginated
surface needs a total order: the schema's UNIQUE keys already carry
the ledger/entries/documents (`(org_id, entry_number)` + line_number;
`(org_id, document_number)`); the tiebreaker fix appends `id`. The
pin: create two same-name rows, page limit=1 across the set, assert
no skip and no duplicate.

### A Settings String Can Point At A Class Nobody Runs
`config/settings/base.py` declared `DEFAULT_PAGINATION_CLASS:
"common.pagination.StandardPagination"` — a module the repo never had.
It survived every boot because DRF's pagination check short-circuits
on `PAGE_SIZE`... until `PAGE_SIZE: 50` also appeared, making the check
import the class path at every system check. The latent crash surfaced
only when a real `common/pagination.py` landed WITHOUT the class (the
first restart after the edit). Lesson: string-referenced settings are
load-bearing contracts — when you CREATE a module a settings path
points at, grep the settings for its name first, and boot the server
after module surgery, not just the test suite (pytest never ran the
check).

### Restart The --noreload Backends After Backend Code Changes
The dev servers run with `--noreload` (the daemonize pattern) — code
changes do NOT reach them. The live-probe/e2e loop will silently test
yesterday's code (the first pagination e2e run failed against the
old backend that ignored `limit`). After any backend edit: restart
both instances (:8000 + the :8001 RLS one) before a live gate.

## 2026-11-28 P25 Sprint — New Patterns & Lessons (session 48)

### A Spec's Substrate Claim Is A Contract — Pin It In The Bootstrap
The P24 ledger e2e spec documented "the demo substrate posts 36+ journal
lines (the §9 bootstrap)" — but that claim only held on a DB whose
volume had ACCUMULATED across prior sessions' e2e runs; a fresh host
bootstrapped 6 lines and the spec failed (40P/1F/1S vs the documented
42/42). Worse, the bootstrap's own invoice/credit-note steps had been
silently broken since P14/M-4 made `tax_code_id` required — the POSTs
failed behind `|| true` guards and printed "invoice OK ()" with an
empty id, masked for months by the specs being self-sufficient. Lesson:
when a spec depends on substrate volume or shape, the bootstrap is part
of the contract — a `test.skip` that silently passes on a thin
substrate hides the dependency until a volume-hungry spec exposes it.
And a bootstrap step that can fail MUST fail loudly (print the response
body, exit 1) — an idempotency guard that reuses what exists is not
evidence that creation ever worked. The proof belongs in the sprint:
drop the DB, run the bootstrap ONCE, run the suite FIRST-run, count the
skips.

### Parse The Range, Not Just The Type
`parse_int_param` validated that an offset was a well-formed
non-negative integer — but `?offset=99999999999999999999` parses fine
and detonates at the SQL layer (`DataError: bigint out of range` → an
untyped 500 on the ledger, while the Python-sliced envelope views
quietly returned an empty page). A "garbage param" is anything the
STORE cannot round-trip, not just what the parser cannot read: a
bigint-backed param needs the int8 bound at the parse layer. The
`min_value`/`max_value` pair is now symmetric (the upper mirror landed
a sprint after the lower — asymmetries in validation helpers are where
the next 500 lives).

### Silent-Ignore Is A Contract Hole Too
A well-formed `offset` without a `limit` was parsed, then discarded —
every view returned the FULL unpaginated set with the offset unused,
while `?offset=abc` correctly 400'd. The module's own philosophy
("explicit beats silent clamping") was contradicted by its own code
path. When a parameter is meaningless without its pair, say so with
the typed 400 — but verify the blast radius first: grep every consumer
(e2e, bootstrap, smoke scripts, hooks) for the orphan shape before
making it an error, and document the rule in the API guide with a
version bump.

### Test The Observable Transport, Not The Mocked Hook
The org-switch offset-reset test could not be written against a module
mock of `useLedger` — a React render that is DISCARDED still calls the
mock synchronously, so the mock records calls that never commit a
fetch. The honest pin mocks only the api-client TRANSPORT and runs the
real TanStack hook under a real QueryClient: the recorded URLs are
exactly what hit the network. Bonus finding: the "stale fetch" the fix
targeted never actually fired on React 19 + TanStack 5.90 (notifyManager
batching suppresses it — the old useEffect code was accidentally safe).
Empiricism downgraded the finding from "bug" to "hardening" — and the
render-time reset (the React prev-state pattern) makes the guarantee
explicit instead of timing-emergent. Write the real-hook test BEFORE
concluding a timing-interior bug exists.

## 2026-11-28 P30 Sprint — New Patterns & Lessons (session 57)

### A Star Import Can Be A Contract — Suppress With Rationale, Never Convert
The Django split-settings idiom (`from .base import *` in
development/production/testing.py) is a PASS-THROUGH CONTRACT: the star
is the mechanism that flows every base setting — and every FUTURE base
addition — into the derived modules. Ruff's F403/F405 flags it, and the
"clean" fix (explicit imports) would silently DROP future base
additions: the exact drift class this repo registers as a lesson. The
honest fix is `[tool.ruff.lint.per-file-ignores]` with the rationale in
a comment at the config — ONE documented place, not 29 scattered
noqa sites. When a linter flags an idiom, ask what the idiom is FOR
before removing it; the flag describes the mechanism, not the intent.

### The Hidden-Fix Tier Deserves Line-Level Review
Ruff's safe/unsafe fix split earned its keep on the whitespace batch:
378 W291/W293 findings, of which 96 were "hidden" (unsafe) because
they sat INSIDE docstrings — where whitespace is string content, not
code style. The batch applied the safe 282 first, then reviewed the
hidden 96 line-by-line (`git diff` + the docstring-context check)
before the `--unsafe-fixes` apply. Blind-fixing the whole class would
have rewritten string bytes sight-unseen. The rule: `--fix` for the
safe tier, `git diff` review for the hidden tier, and never
`--unsafe-fixes` as a first move on a class you haven't sampled.

### An Edit Tool Can Break A Makefile — Verify Tab-Sensitive Formats Byte-Level
A mid-sprint Makefile edit came back with every recipe tab normalised
to spaces (make: "missing separator") — the edit layer's display
form silently replaced the byte that make's grammar requires. The same
class as the P10 "corrupted YAML" scare: verify surprising failures
byte-level (`cat -A`) BEFORE remediating, and for tab-sensitive formats
(Makefiles, some YAML) apply edits through a scripted write that
asserts the byte survived. Also: a make target name cannot contain a
colon (`lint:mechanical` parses as a target pattern) — hyphenate.

## 2026-11-28 P29 Sprint — New Patterns & Lessons (session 55)

### A Detail Page Costs One Detail Per Line — Audit The Get-Seam, Not Just The Lists
The P28 sprint closed the LIST-surface cost class and the audit
stopped there — the DETAIL surfaces carried the same disease at a
different seam: three `get_*` service methods returned a plain
`.objects.get(...)` while the serializers walked FKs per line (the
invoice detail paid 2 queries per line; a 5-line detail = 14 queries).
The tell: any serializer field with `source="fk.field"` is a walk
UNLESS the queryset that produced the row carried the
select_related/prefetch_related. The sweep is mechanical — grep the
serializers for nested `source=` access, then check the service get
the view called. The fix belongs at the SERVICE seam (uniform, one
test per service, every serialising consumer benefits incl. the PDF
context), never per-view: per-view optimisation is how the drift class
re-enters. And pin it with the query-count gate, not the response —
the bytes are identical at any query count, which is exactly why no
existing test could see the cost.

### The Per-Row Walk Hides Behind A Correct Response — Count Queries By Table Anchor
The detail N+1 was invisible to every contract test because each
per-line walk returns the RIGHT bytes. The pin that bites:
`CaptureQueriesContext` + a table anchor (`coa"."account`), asserting
an upper bound INDEPENDENT of the line count. Two design notes from
the RED runs: (a) with select_related the JOIN puts the anchor table
INSIDE the main query, so "queries touching the anchor" counts 1 both
before (the walk) and after (the join) for FIXED related rows — the
distinguishable assertion for those is that the MAIN query carries
the JOIN (read the SQL, don't just count); (b) for per-LINE walks the
count IS the signal (3 lines → 3 walks on the base code, 1 joined
fetch after). Pick the assertion shape by whether the walk multiplies
per row or is a fixed extra.

### A Tier Set Is A Blind-Spot Generator — Re-Enumerate The Source Tree When Tiering
The P20 sprint added per-glob coverage tiers for lib/hooks/app/
components/providers and MISSED src/shared — the shared
money-formatting primitives sat gated only by the whole-suite floor
for nine sprints. The same sprint pattern repeated at the TIER level:
once a tier set exists, new directories are born outside it silently.
The lesson: whenever a tiered gate ships, enumerate the ACTUAL source
tree against the tier set in the same commit (a two-line `ls src/`
diff), and re-check it whenever a new src/ subtree lands. A tier
nobody adds is a tier nobody gates.

## 2026-11-28 P28 Sprint — New Patterns & Lessons (session 53)

### A Paginated Response Is Not A Paginated Query — Pin The SQL, Not Just The Envelope
The P24 sprint shipped the `?limit=&offset=` envelope and called the
lists paginated — but four of the surfaces fetched the ENTIRE filtered
set into Python and sliced the list in the view (`len()` for the
count). The response was correct at every size; the cost was quadratic
in org size and invisible to every envelope-level test (the bytes are
identical whether you fetch 20 rows or 20,000). The gate that pins it
is `CaptureQueriesContext`: assert the SELECT carries the REQUESTED
`LIMIT n` and that a `COUNT(*)` ran. Correctness tests pin the
contract; query-level tests pin the cost. When a fix's value is
performance, its regression test must read the query log — an
envelope assertion cannot fail on a full-table fetch.

### A Ratchet Nobody Bumps Is A Rubber Stamp
Seven consecutive sprint reports (P21–P27) each recorded "the coverage
floor RAISED to <measured value>" — and the config still held the P20
thresholds. The gate passed every time (it sat 2+ points below the
truth), so nothing forced the discrepancy to surface. The lesson: a
ratchet's value is the WRITE, not the read — the sprint that raises
the measured floor must also raise the configured floor in the same
commit, or the mechanism silently degrades into a pass-through. Audit
the ratchet whenever a report claims a raise: `grep` the config for
the claimed numbers.

### Verify The Dev/Prod Split Before A Dependency Sprint
"17 findings, 7 high" sounds like an incident; the split (`npm audit
--omit=dev` → 0) says none of them can touch production. The dry-run
then showed every fix was an in-range semver bump. Three checks
(dev-only paths, the dry-run diff, the full gate matrix after) turned
a scary audit into a 10-minute mechanical closure with zero risk
transfer. Run all three before any dependency work; never `--force`
when the in-range set already resolves.

## 2026-11-28 P27 Sprint — New Patterns & Lessons (session 52)

### A Page Reset Belongs To The VALUE CHANGE, Never The Timer
The P26 "batch the reset into the debounce tick" lesson was half right:
it fixed the double-fire but put `setOffset(0)` in the timer BODY —
which runs on the effect's MOUNT-run too (search never changed; the
reset fires anyway ~300ms after mount, doubled under React StrictMode).
A user paginating inside that window had the click silently reverted to
the cached page 1 — no refetch, no feedback. The lesson: a state reset
that means "the input VALUE changed" must be gated on the value actually
changing (compare against the last committed value — inside the timer
callback, an event, never during render where the react-hooks/refs rule
forbids ref access). The mount-run of any keyed effect is a render you
did not ask for; anything unconditional in it runs against a user who
has not acted.

### A Race Proven By Trace Is A Bug Even When Isolation Passes
The full-run e2e failed 3× at the same assertion while the isolated
re-run passed — the lazy read is "flaky, retry". The Playwright trace
settled it in minutes: the click WAS dispatched, the page-2 request
fired and answered 200, then the failure snapshot showed the page back
at "Showing 1–20" with NO third network request — the cache-served
revert signature. When a test passes in isolation and fails in the full
run: pull the trace, read the network log, and diff what the UI shows
against what the transport saw. "Flaky" is a hypothesis, not a
diagnosis.

### A Module Mock Cannot Observe A Cache-Served Revert
The P26 page tests mock the list hook — and a mocked hook cannot exhibit
cache behaviour. When the defect IS the cache (a queryKey reverting to
a cached entry), only the REAL hook under a REAL QueryClient shows it,
and only the rendered page-math summary (not URL counting) catches the
revert (no refetch happens — that is the bug). The real-hook
transport-mock pattern (the P25 ledger-org-switch spec) is the right
tool for state-machine contracts; the module-mock pattern remains right
for render-shape contracts. Pick the mock by what the defect touches.

### The Absent-Prop Default Needs A Stable Identity
`filters = {}` in a destructured default creates a FRESH object every
render — harmless until a render-time identity compare keys on it, at
which point it is an infinite re-render loop ("Too many re-renders",
found by the existing suite the moment the reset landed). The fix is a
module-level `NO_FILTERS = {}` constant as the default value. Any
component that compares a prop by identity must give that prop's
absent-case default a stable, shared identity.

## 2026-11-28 P26 Sprint — New Patterns & Lessons (session 50)

### The Page Identity Lives In The QueryKey — Every Paginated Hook, Not Just The Ledger
The P24 cache-paging trap (a page change resolving the previous page
from cache) was fixed on `useLedger` and then NOT carried to the next
surfaces — the invoices/contacts/payments/transactions hooks all gained
page params this sprint, and each one needed the SAME pin: `limit`/
`offset` ride the query string AND the queryKey (two pages = two cache
entries). The trap is per-hook, not per-app: any hook that pages without
the key identity silently serves stale pages the moment a second
consumer pages the same list. The corollary: the pin is a test, not a
comment — the "two renders, two fetches" spec (only the transport
mocked) proves the key identity better than any code review.

### An Offset Reset In Its Own Effect Double-Fires The Query
Resetting the page offset in a `useEffect` keyed on the debounced search
double-counted the hook call: React may render once more before bailing
out of a same-value setState that originates in an effect, and each
render calls the (mocked) hook again — the "one search per burst" test
caught it ('acme' fired twice). The fix batches the reset INTO the state
transition that causes it: the debounce timeout sets both
`setDebouncedSearch(v)` and `setOffset(0)` in one tick (one render), and
the filter buttons reset the offset in their own click handler. A state
reset that accompanies another state change belongs in the same
setState call site, never in a watching effect.

### A Self-Sufficient Spec Beats A Substrate Claim
The P25 lesson (a spec's substrate claim must be pinned in the
bootstrap) has a stronger form: make the spec stock its own
preconditions through the public API. The P26 invoices-pagination spec
counts the org's invoices and creates small DRAFT fodder only while
count ≤ 20 — idempotent across runs, zero journal lines (the F5 boxes
and dashboard stay untouched), and no bootstrap contract to drift. The
fresh-DB proof then verifies the SELF-SUFFICIENCY rather than a
documented dependency. Reserve bootstrap-pinned substrate for shapes
the specs cannot create themselves (posted journal history, fiscal
periods); prefer self-stocking for volume.

### Return The Envelope From List Hooks — Unwrapping Is A Data Lie
`useContacts` returned `response.results` — the count, next and previous
were discarded at the hook boundary, so no consumer could ever render a
truthful total, and pagination was structurally impossible (the page
would have had to re-fetch outside the hook). When a backend contract
carries an envelope, the hook returns the envelope; consumers unwrap at
the point of use (`data?.results ?? []`). The breaking-change cost was
bounded because a consumer sweep preceded the change (exactly two
callers); an un-enumerated hook-shape change is where regressions hide.

### An Implicit __context__ Is Not A Chain — Make The Translation Explicit
B904's 66 sites all "worked" — Python's implicit `__context__` captured
the original exception inside every except block. But implicit context
renders as "During handling of the above exception, another exception
occurred" — the wording of an ACCIDENT, not a translation — and it is
an implementation detail of WHERE the raise sits: any refactor that
moves the raise out of the except block silently drops the chain. The
P31 contract: `from exc` by default (the cause preserved as `__cause__`,
stable across refactors, the constraint name visible in race
translations), `from None` ONLY where the raised message already embeds
the original error's own string (`f"...: {e}"` — the suppressed context
is pure duplication). The response bytes never change — the pinning
lives at the exception object level (`__cause__` isinstance /
`__suppress_context__`), a truth no HTTP-contract test can see.

### A Tests-Tree F401 Sweep Must Check The Import-Is-The-Side-Effect Class
Extending the P30 mechanical closure from production to tests/ was not
a blind re-run: test files import for SIDE EFFECTS more often than
production modules (fixture registration via import, conftest helpers,
settings patching). The P31 review enumerated every one of the 66
tests-tree F401s by name — all models/stdlib/test-helpers, zero
factory-or-registration modules — so the safe `--fix` was justified,
and the full 1034-test suite (not a sample) proved it. The lesson
generalises the P30 __init__.py re-export review: before autofixing
F401 in ANY new tree, classify the imported names by whether the
import itself is the behaviour; when in doubt, the suite is the
arbiter, not the linter.

### An Incomplete Builtin-Shadow Rename Binds To The Builtin — Silently
The P32 A001 rename (`credits` → `credit_total` in journal_service's
trial balance) was applied to the local bindings but one dict VALUE
still read `str(credits)`. No NameError fired — `credits` resolved to
Python's BUILTIN easter-egg object (the `credits()` about-text), whose
str() landed in the API payload and blew the downstream Decimal()
parse with ConversionSyntax. The rename of a builtin-shadowing name
must be COMPLETE (grep every use in the function, not just the
bindings ruff flagged), and the failure mode is a DATA corruption
disguised as a parse error, never a crash at the rename site. The
full suite — not the linter's clean bill — is the arbiter; the three
trial-balance tests caught it within one run.

### A Cross-Module Fixture Import Is A Missing Conftest — Close It Architecturally
The 26 F811s were all one pattern: `payment_fixture` defined in a
sibling test module, imported by 7 files purely so pytest could
resolve it, with every consuming test's PARAMETER then shadowing the
import. The suppression temptation (26 noqas) would have hidden the
real defect — the fixture's availability depended on an implementation
detail of another test file. The conftest placement is pytest's own
resolution model: the fixture moved verbatim to
tests/integration/conftest.py, the 7 import blocks were DELETED (simpler
files), and a NEW spec pins the contract by using the fixture with NO
import — RED on the base tree (fixture not found), GREEN after the
move. When a lint class traces back to a workaround for missing
infrastructure, fix the infrastructure; the findings close as a side
effect.

## 2026-11-28 P33 Sprint — New Patterns & Lessons (session 64)

### A Fixture At The Default Value Masks A Hardcode At The Same Value
The Peppol generator hardcoded `currencyID="SGD"` on all 11 amount
elements while the mapper correctly flowed the document's own currency
into `DocumentCurrencyCode` — and every existing generator test built
its payload with `"currency": "SGD"`. The suite was green, the fixture
was truthful FOR THE DEFAULT, and the defect was invisible: a
USD-denominated invoice would have transmitted UBL whose header said
USD and whose every amount said SGD. The same class as P1/A-2
(fixture debt masks real bugs), sharpened: when a seam has a DEFAULT
value, write at least one spec whose fixture sits at a NON-default
value — the default-valued fixture can never distinguish "the code
reads the value" from "the code hardcodes the default". The P33 specs
pair the non-default probe (USD) with the default-path control (SGD)
so the byte-stability claim is pinned too.

### A Money-Denominated Response Owes Its Currency The Same Truth As Its Amounts
Three surfaces returned real, computed amounts beside a hardcoded
`"currency": "SGD"` (the financial reports ×3, the account balance —
the latter behind a literal TODO). The pattern generalises the P5
dashboard-truth class: any response carrying a monetary amount carries
an IMPLIED denomination, and a hardcoded one is a lie that only
non-default data exposes (a USD-based org's trial balance claimed
SGD). The audit sweep that finds them is mechanical — grep every
`"SGD"`/currency literal outside defaults/validators and ask, per
site, "what does the DATA say?" The Peppol mapper's
`tax_currency: "SGD"` survives that question (IRAS GST is accounted in
SGD regardless of the document currency — the statutory posture);
the amount-level currencyIDs did not.

## 2026-11-28 P34 Sprint — New Patterns & Lessons (session 66)

### Three Stacked Blind Spots On One Path Hide Each Other's Silence
The credit-note Peppol path had THREE tests touching it, and all three
were structurally incapable of seeing the defect: the generator test
only asserted the method EXISTS (`hasattr(XMLGeneratorService,
"generate_credit_note_xml")`), the validation test deliberately did not
assert `is_valid` (its own comment said "validation may have schema
errors but service works"), and the transmission tests MOCKED the
validation service entirely. Individually each looks defensible — an
existence test, a tolerant test, a mocked unit test. Stacked on the one
path they form a complete blind spot: the hollow generator, the wrong
validator wiring and the broken XSD namespace were all invisible. The
lesson: when auditing a path, list EVERY test that touches it and ask
per test "what would this test see if the path were COMPLETELY
broken?" — if the answer is "nothing", the path has no tests, whatever
the count says. The P34 fix strengthens all three layers (the
existence test's file now carries the full-structure + acceptance
gates; the tolerant test now asserts `is_valid=True` with a
lines-carrying fixture; the dispatch is pinned at the seam).

### A Validator The Suite Never Satisfies Is Decorative — Prove It Accepts Its Own Producer
The deeper P34 discovery: the generated INVOICE also failed its own
XSD — the custom single-file schemas declared the cbc/cac children as
LOCAL elements in each root's target namespace (the generator
correctly emits them in the real cbc/cac namespaces) and never
declared the amount attributes at all. No test ever validated the
generator's actual output, so the layer passed CI while rejecting
everything it was supposed to accept — on the real transmission path
every document would have been marked FAILED before reaching the
access point. The lesson generalises the P33 fixture lesson: for every
validator, keep ONE gate that feeds it its own producer's real output
and asserts acceptance (`test_X_validator_accepts_generated_Y`). A
validator only ever seeing hand-built fixtures (or nothing) is a
rubber stamp; the producer-validator round-trip gate is the cheap
permanent proof that the two ends of the seam agree.

### A Validation Stack Is Only As Truthful As Its Topmost WIRED Layer
The P35 finding, one layer above the P34 one: the Schematron
business-rule layer had been decorative end to end — the `.sch`
artefact declared the wrong XML namespace (a `dml` typo of `dsdl`:
unparseable by ANY ISO-Schematron implementation) and an unsupported
`queryBinding="xslt2"` (lxml ships only the XSLT 1.0 skeleton); the
`_validate_schematron` placeholder was never CALLED by either validate
method (`schematron_errors` was a constant `[]` in every result); and
the one test on the axis was `assert hasattr(...) or True` — vacuous
by construction. The suite was green while a USD document carrying
one SGD-claiming amount validated clean: the P34 work made the XSD
layer real, but the layer ABOVE it (the cross-element truths a
structural schema cannot express) was still nothing. The lesson: when
a validation stack has multiple layers (XSD → Schematron → code-list
checks), verify EACH layer's wiring separately — a real bottom layer
plus a decorative top layer still overstates what was checked. The
cheap probe: hand-craft a document that passes the bottom layer but
violates the top layer's strongest rule, and assert the verdict is
False. If it validates clean, the top layer is wired to nothing. The
P35 fix wires the layer (the five-rule deterministic XPath 1.0 set,
the fail-closed load posture, `is_valid` folding both error lists)
and pins exactly that probe (`test_tampered_currency_id_fails_the_business_rules`).

### Join Consumer Shapes, Don't Assume The Mock's Shape At The Seam
The P35 second finding: `_execute_transmission`'s failure message
was built with `"; ".join(errors)` — the transmission TESTS mocked
the validation service with a list of STRINGS, so the join worked in
the suite; the REAL validator returns a list of DICTS, so the join
raised TypeError the first time a real schema-invalid document hit
the path, and the outer `except` rewrote the intended VALIDATION_ERROR
into an INTERNAL_ERROR carrying the Python error string. The defect
class: a seam where the mock's data shape and the real collaborator's
shape diverge — the suite proves the mock's shape joinable, never the
real one. The lesson: at every seam that formats/serialises a
collaborator's return, keep ONE test that runs the REAL collaborator
through the seam (mock the INPUT, not the collaborator, when the
collaborator is the thing under test), and make the formatter
defensive about shape (dicts → their message values, strings pass
through) — the join should never be the thing that crashes.

### Construction-Truth Is Not Checked-Truth: Validate What The Constructor Guarantees
The P36 headline: the generator computes every total from the DB's
NUMERIC(19,4) Decimals (total_excl = Σ line amounts, gst_total = Σ line
GST, total_incl = total_excl + gst_total, payable = total_incl −
amount_paid), so the arithmetic invariants held BY CONSTRUCTION in every
emitted document — and precisely because they always held, no layer
checked them: the XSD checks structure, the P35 rules check currency
consistency, but a document whose TaxInclusiveAmount was tampered +500
(or whose line amounts were corrupted in transit) validated CLEAN. The
defect class: construction-truth masquerading as validation-truth —
"the numbers are right because we compute them right" leaves the
pipeline blind to everything that happens AFTER construction (a bug in
a future refactor, a tampered payload, a corrupted store). The lesson:
for every invariant the constructor guarantees, decide DELIBERATELY
whether the validation layer re-checks it — the re-check is cheap (the
same values, re-derived from the document itself) and it is the layer
a real counterpart (here: a Peppol access point's EN 16931 BR-CO rules)
adds on top. And when the invariant involves ROUNDING (per-line 2dp
GST), the validation rule must use the SOUND bound — the accumulated
per-line rounding slack (0.005 × line count), never a fixed epsilon
(false-rejects legitimate documents) and never naive equality
(false-rejects the constructor's own output). The P36 fix pins exactly
this: the six-rule BR-CO pattern with the per-line rounding-sound bound,
proven by the tampered-total probes failing with the rules named while
ALL 37 real demo documents pass clean.

### The Currency Sweep Is Not Done Until Every Currency-Bearing Element Is Swept
The P36 second finding: the mapper hardcoded "tax_currency": "SGD" —
a USD document emitted TaxCurrencyCode=SGD beside DocumentCurrencyCode=USD
and currencyID="USD" amounts. P33 swept the AMOUNT elements (11 hardcode
sites) and fixed them; the tax-currency element sat one field over,
outside the sweep's named scope, and — the recurring kicker — the P33
USD test fixture ITSELF carried "SGD" (the default-value-fixture blind
spot the P33 docstring names). The lesson: a truth sweep named after a
class of elements (amounts) must enumerate EVERY element in the same
semantic family (any currency-bearing header), not just the class the
original bug report named — the fixture should be built from the
honest mapper output (or its divergence pinned), so the fixture cannot
mask the very class it tests. The cheap probe: for every hardcoded
3-letter currency literal in the transmission path, grep it and ask
"what does this become on a non-SGD document?" — P36 found exactly one
answer that was still "SGD".

### A Data-Layer Guarantee Is Not A Presentation-Layer Truth
The P37 headline: the service layer has refused a credit note without
related_document_id since P14 — the IRAS rule quoted in its own
docstring ("A credit note must show the number and date of the original
tax invoice") — yet the transmitted XML named no invoice (the live
probe on the real demo credit note measured 0 BillingReference elements,
0 occurrences of the original number) and the PDF showed none. The
defect class: a guarantee enforced at the data layer silently masquer-
ading as a guarantee the DOCUMENT carries — the FK exists, the
validation passes, the receiver cannot match the credit note to the
invoice it corrects. The lesson: for every required relationship the
schema/service enforces, walk the FULL presentation path and ask "where
does this surface?" — every emitted artefact (the XML, the PDF, the
API response) either carries it or there is a gap; and the validation
layer can pin it (BR-SG-07 is sound exactly BECAUSE the service layer
enforces the FK — the rule can never false-reject a document this
system creates). The corollary: when a surface renders a document type,
check the TYPE's own labelling (the raw "SALES_CREDIT_NOTE" enum
leaking as the PDF heading was the same bug wearing a costume).

## 2026-11-28 P38 Sprint — New Patterns & Lessons (session 74)

### A Gate Calibrated When A Path Was Broken Must Be Revisited When The Path Is Fixed
The P38 headline: the send-invoicenow type gate (P9/C-3) refused every
non-SALES_INVOICE document — calibrated when "the transmission path maps
anything non-credit-note to UBL Invoice" (its own test docstring), i.e.
when the credit-note pipeline was HOLLOW. P34 then fixed the pipeline
(the type-aware generator + validator dispatch), P35 added the business
rules, P36 the arithmetic, P37 the reference truth — four sprints of
building a first-class credit-note transmission path that NO workflow
entry point could reach: send_invoicenow refused the type (400), the
approval auto-transmit only fired for invoices, and the UI rendered the
"Send via InvoiceNow" button on APPROVED credit notes (a button that
always 400'd — the advertised-workflow hazard). The defect class: a
guard whose rationale was TRUE at birth, silently outliving the
condition that justified it — and the guard never gets re-audited
because the pipeline tests all pass (they test the layers the guard
blocks, never the guard's own reachability). The lesson: every gate
that cites a defect as its rationale ("the mapping layer renders X as
Y") carries an implicit EXPIRY — when the cited defect is fixed, sweep
for the gates it justified. The cheap probe the P38 audit used: for
every workflow-refusal message, paste it into the UI affordance and ask
"does a surface advertise what this gate refuses?" (the answer here was
the credit-note detail page's own button). The corollary: gates that
must NEVER expire (the quote refusal — a quote rendered as a tax
invoice is wrong regardless of pipeline maturity) are the ones whose
rationale names the TYPE's semantics, not the pipeline's current state;
both classes of gate should say which they are.

### The Celery App That Never Loads In The Web Process (And The Tests That Cannot See It)
The P38 second finding, discovered by the sprint's own live contract
re-verification: `config/__init__.py` was empty — nothing in the backend
tree imported `config.celery`, so in every WSGI process the
`@shared_task`s bound to Celery's DEFAULT app (broker amqp://localhost
via kombu's fallback, eager off). The first REAL `queue_task` dispatch
on a Peppol-configured org 500'd with Connection refused — the pyamqp
transport in the traceback naming the wrong broker outright. The
defect class: process-dependent wiring — the worker found the app
through `celery -A config`'s fallback search (`config.celery.app`), the
web process never did, and the test suite could not tell the
difference because every dispatch-shaped test mocks `.delay` (the mock
erases the app) or uses `.apply()` (eager by definition — the app never
consulted). The masking had two layers: the demo org carried no Peppol
settings (every dispatch path returned early), and the eager-mode
contract the docs describe was true only in processes that had loaded
the app. The lesson: a framework whose canonical wiring lives in the
project package's `__init__` (`from .celery import app as celery_app`)
should have a config-level gate asserting THE PACKAGE IMPORT wires the
app (`celery.current_app.main == "<the-app>"` + the broker + the eager
flag) — the assertion costs three lines, needs no broker, and would
have failed on every host since the file was left empty; and when a
dispatch path is first exercised, exercise it LIVE against a
configured org before calling it delivered (the plan's Phase 3 live
contract re-verification is where this one surfaced — exactly what
that step is for).
