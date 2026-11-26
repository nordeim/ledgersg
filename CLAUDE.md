# LedgerSG — Comprehensive Developer Briefing

> **Single Source of Truth** for coding agents and human developers
> **Version**: 2.18.0
> **Last Updated**: 2026-11-26
> **Status**: P15 Remediated 🟢 (P14 completed + the tree repaired after the corrupted 2bcb43f0 commit; the runtime-role gate live: the full onboarding path as ledgersg_app, 13/13 smoke steps; schema v1.2.0 §17 RLS complete; zero known dependency advisories) — all gates green (backend 750P/0F/5S, frontend vitest 530/530, typecheck 0 errors, e2e 40 specs / 11+29skip default, the live suite 40P/0F/0S; eslint 45→9 with the 36 any-casts cleared and the register truthful). Mobile-nav truth: the navigation verified working live at 375/800/1280 with rule-by-rule cascade traces (the `display:flex` reading is correct flex-item blockification, NOT a Tailwind v4 bug — the v4 setup is clean, no legacy config); the open menu now behaves as a modal overlay (Escape closes, body scroll locks, focus moves in on open and returns to the trigger on close, Tab cycles within — the P12/A-1 floor with 7 vitest + 3 gated e2e); `data-scroll-behavior=smooth` on <html> kills the Next.js 16 route-transition warning; the API_CLI guide re-verified live (see `docs/REMEDIATION_2026-11-23_P12_REPORT.md`, plus the P0–P11 reports)

---

## 📋 Table of Contents

1. [Executive Summary](#-executive-summary)
2. [Project Architecture](#-project-architecture)
3. [Backend Deep Dive](#-backend-deep-dive)
4. [Frontend Deep Dive](#-frontend-deep-dive)
5. [Database Architecture](#-database-architecture)
6. [IRAS Compliance & GST](#-iras-compliance--gst)
7. [Security Architecture](#-security-architecture)
8. [Testing Strategy](#-testing-strategy)
9. [Development Guidelines](#-development-guidelines)
10. [Troubleshooting](#-troubleshooting)

---

## 🎯 Executive Summary

**LedgerSG** is a production-grade, double-entry accounting platform purpose-built for Singapore SMBs. It transforms IRAS compliance from a burden into a seamless, automated experience while delivering a distinctive "Illuminated Carbon" neo-brutalist user interface.

### Current Status

| Component | Version | Status | Key Metrics |
|-----------|---------|--------|-------------|
| **Frontend** | v0.3.3 | ✅ Ready | 16 pages, 532 unit + 40 e2e tests (11 always + 29 backend-gated; the live suite 40P/0F), typecheck clean, axe-clean login flow, cross-reload session persistence, real invoices list/detail + ledger + settings pages, working void dialog + real error messages + PDF/InvoiceNow actions, real reports + quotes pages, organisation creation + full payment workflow + truthful dashboard (P5–P9), registration + contacts + the contact-picker invoice form + the GST F5 lifecycle + bank edit/deactivate + fiscal open + change password + InvoiceNow settings (P10), the truthful edit-dialog prefill + F5 box labels + dashboard GST/chart/prefix truth + permission-gated row actions + dev-only CSP unsafe (P11) |
| **Backend** | v0.6.2 | ✅ Suite Fully Green | 90+ endpoints, **834 tests passing, 0 failed** (5 skipped, documented), HttpOnly refresh-cookie auth, real InvoiceNow + accounting truth (credit notes post reversed entries and net in F5 — P11/C-1), per-status transition permissions + active custom exception handler, real financial reports + aged AR/AP + quote lifecycle + the P9 banking/onboarding contracts (P5–P9), GST F5 review/amend + fiscal-period open + UEN 400s + the 429 rate-limit contract (P10), production settings that boot (builtin cache + LOG_DIR) + typed org-settings PATCH + UUID routing 404s + audit-trail context (P11); the exception-handler rollback + IRAS 2dp GST quantum + typed ImmutabilityError + InvoiceNow 404s + reversal atomicity + timezone-aware dates + copy-on-write settings (P13) |
| **Database** | v1.2.0 | ✅ Complete | 7 schemas + token blacklist, RLS complete on every tenant table (§17, incl. the append-only audit log), 30 domain tables, NUMERIC(19,4) money |
| **Accounting** | v1.0.0 | ✅ Verified | 3/3 Workflows (void reversal restored 2026-11-21) |
| **Security** | v1.3.0 | ✅ P0 Hardened + P4 Cookie Auth + P7 API gates | Token rotation+blacklist, SECRET_KEY gate, ratelimit default-on (settings-driven login knobs), HttpOnly refresh cookie + `session_hint` evidence gate, per-status document permissions, manager-gated settings PATCHes |
| **API Contracts** | v1.2.0 | ✅ Standardized | {results, count} lists; auth contract aligned to tests 2026-11-21; error envelope {error:{code,message,details}} active in DRF (P7/F-19) |

### Latest Milestone: P15 Sprint — Tree Repair, P14 Completion & the Runtime-Role Gate ✅ — 2026-11-26 (session 30)

| Fix | Impact |
|-----|--------|
| **Tree repair** | The interrupted session-29 committed its P14 work to wrong paths (the Payment model destroyed by a serializer overwrite — the backend could not boot); every stranded fix relocated to its canonical home, all P14 RED tests green |
| **C-2 + H-3** | FILED/AMENDED F5 returns are immutable (409, not even `force=true`); the GST period lock refuses back-posted approvals/journals/voids inside filed periods |
| **H-1..H-5** | Allocation cap (no negative amount_due), instalment statuses complete, linked+cap-checked credit notes (IRAS credit-note rule), the GST-registration guard |
| **H-6 + M-6a** | Schema v1.2.0 §17: RLS on all six remaining tenant tables (organisation, user_organisation, role, peppol_settings, tax_code, event_log — append-only); `audit.log_change` pins search_path |
| **C-1 + H-7** | Org creation sets the RLS context before seeding; the whole onboarding path verified LIVE as the non-superuser `ledgersg_app` (13/13 smoke steps; cross-org reads blocked; no-context reads fail closed) |
| **H-8 + H-9** | Django 6.0.10 / DRF 3.18.3 / lxml 6.1.3 / WeasyPrint 70 / Next 16.4.6 / zod 4.6.7 (zero known advisories, both production sets); the Docker path generates a strong per-boot key; service.py gates its key like production |
| **M-1/M-4/M-5/M-10/X-1/H-04b/H-05b** | Honest ACRA/IRAS validators (both M-form lengths; UEN-form GST numbers accepted); the line-item schema (400s); Viewer read-only; tax-code dedupe; XXE-hardened parser; NRIC PayNow masking + masked-echo rejection; F5 override evidence trail |
| **F-A + F-B** | The e2e bootstrap self-creates the F5 return; linked-CN + cap-headroom + real-UEN e2e contracts; single-flight token refresh (the rotation race killed sessions mid-suite) |

### Previous Milestone: P11 Sprint — Accounting Truth & Config Honesty ✅ — 2026-11-23 (session 23)

| Fix | Impact |
|-----|--------|
| **C-1** | Credit notes post REVERSED GL entries (previously invoice-direction — AR debited instead of credited) and NET in the F5 computation; quotes no longer count as supplies (H-3) |
| **C-2** | Production settings boot: the builtin Redis cache replaces the never-installed `django_redis`; `LOG_DIR` is an env knob; `DEBUG=true, DEBUG_TOOLBAR=false` no longer crashes dev (one gate — H-5) |
| **H-1 + M-3/M-4** | The contacts edit dialog prefills from the DETAIL endpoint — uen/peppol_id/address/gst_reg_number arrive with their stored values and a save persists them (previously an unconditional save ERASED them with a success toast); the search debounces |
| **H-2/H-4 + M-1/M-7/M-11/L-2** | The F5 boxes panel reads the real box keys (every box previously rendered "—"), the deadlines envelope and REVIEWED filter are truthful, the dashboard GST payable equals the F5 net GST (was hardcoded 0), the revenue chart takes raw values (was NaN on "SGD x.xx"), single currency prefixes |
| **M-2/M-5/M-6** | Bank-account PATCH without id → 404; the org-settings PATCH is typed (choice fields, clean 400s on garbage); garbage path UUIDs 404 at the routing layer (uuid converters) |
| **M-8** | The audit trigger reads the middleware's request context (ip/user-agent/path were NULL on every row); LOGIN/LOGOUT emission (in the CHECK vocabulary, never emitted) |
| **M-9..M-16 + H-6/H-7 + L-batch** | CI runs coverage + dead steps removed; devDependencies split; `.gitignore` covers `uv.lock`; the Docker path boots (pinned installs, gunicorn CMD, compose credentials, no at-boot migrate); CSP unsafe-* dev-only; root debris removed; `timezone.localdate()`; ledger reversals visible; UEN TOCTOU hardening; permission-gated row actions |

### Previous Milestone: P9 Sprint — Onboarding & Banking Truth ✅ — 2026-11-22 (session 18)

| Fix | Impact |
|-----|--------|
| **O-1** | Organisation creation ships at the route the dashboard's dead-end CTA targeted — a self-serve user could previously not use the product at all (registration creates no org; the CTA 404'd) |
| **B-1/B-2** | Statement import sends real multipart (`JSON.stringify(FormData)` sent `"{}"` — the import could never succeed); reconciliation match suggestions render (envelope + field mapping — the form always said "No matching payments found") |
| **B-3/B-3b** | Payment forms pick real contacts (the Customer field was a raw UUID text input) and settle invoices through inline allocations; the invoice detail's Record Payment deep-links into Banking prefilled |
| **B-4..B-6** | The bank-account dialog ships (the Add buttons were dead); payment Void + transaction Unreconcile give the P5/P6 correction engine its first UI |
| **C-1/C-2** | The quote-conversion envelope is pinned and read (the flat read routed to `/invoices/undefined` on every conversion); the invoices list shows invoices (quotes/bills no longer render as invoices) |
| **C-4** | Seeded accounts are filterable: the seed backfills `account_type` (the invoice form's dropdown was empty on fresh orgs) and the bank accounts are reachable via `is_bank` |
| **D-1..D-4** | The aged report honours its as-at date; the dashboard's invented GST boxes/trends are removed; the dead CTAs route to /reports |
| **C-3/B-7/S-1..S-4** | InvoiceNow transmits invoices only (an APPROVED quote could be delivered as a UBL Invoice — type gate + permission parity); tolerance/date NameError-500s are 400s; transport faults keep sessions; XSD fails closed; the stale root requirements.txt retired |

### Previous Milestone: P5 Sprint — Truth Restoration (Repo Hygiene, Real InvoiceNow, Accounting Integrity & Real Dashboard Data) ✅ — 2026-11-21 (session 11)

Built on the independent audit (`docs/ledgersg-audit-report.md`; every Critical/High re-verified in source):

| Fix | Impact |
|-----|--------|
| **C-1/C-3/H-9** | `.env`/`.env.local`/`.pyc`/`dist/`/`.bak` untracked (the P4 `git add -A` had re-committed the env files); CI DB password generated per run; `testing.py` reads `DB_*` from env |
| **C-2 + seam bug** | `send_invoicenow` creates a real transmission log + queues the task; `invoicenow-status` reports real rows; **the task passed a LOG id to `transmit_invoice(invoice_id)` — auto-transmit could never succeed**; cleanup never deletes DELIVERED/REJECTED (IRAS 5-year retention) |
| **H-1** | `allocate()` persists `document.amount_paid` — outstanding AR/AP and `amount_due` were permanently overstated (amount_paid never left 0) |
| **H-2** | payment `void()` posts a reversing journal entry (create_reversal, open-period date fallback) and releases allocations with document status restoration |
| **H-4** | control-account resolution is exact and fail-closed: AR 1200 / AP 2100 / GST input 1600 / GST output 2600 (the old `.first()` broad-match posted output tax to 2200 Accrued Expenses) |
| **H-5/H-6** | `add_line` stores the 2dp GST base as line_amount and a 2dp total; `create_entry` enumerates lines (duplicate dicts crashed the unique constraint) |
| **H-3/H-10** | dashboard cache invalidated by mutations (approve/void, payments, GST filing); alerts view computes real overdue/unreconciled/unpaid counts |
| **M-5/M-6/M-7** | GST registration seeds the control accounts (dead guard fixed); `update_organisation` allow-listed; dead sequence code removed |
| **C-5 (part 1)** | invoices list page renders real `useInvoices` data with truthful states; hook retyped to the real backend row shape |

### Previous Milestone: P4 Sprint — Cross-Reload Session Persistence & Suite Depth ✅ — 2026-11-21 (session 9)

Sessions now survive page reloads/new tabs/browser restarts, and the auth client can no longer be tricked into pointless refreshes:

| Fix | Impact |
|-----|--------|
| **E-1 backend** | `login/register` set the refresh token as an **HttpOnly cookie** (`Path=/api/v1/auth/`, SameSite=Lax, Secure=!DEBUG, 7d), `refresh` accepts body **or** cookie (rotation+blacklist identical, response re-sets the rotated cookie), `logout` blacklists whichever credential is present and expires the cookie, `change-password` expires it too (revoke-all); body flow unchanged for API clients (8 contract tests → 14 with the hint suite) |
| **E-1 frontend** | `fetchWithAuth` refreshes on a **cold 401** (no in-memory access token) and retries — the `&& accessToken` guard that dropped every reload is gone; the login body tokens stay unchanged |
| **E-1 refinement** | Evidence-gated refresh: a non-secret, JS-readable `session_hint` cookie (set alongside the refresh cookie; expired on logout/password-change/failed cookie-refresh) gates the client's refresh attempt — anonymous 401s (bad credentials) propagate to the caller instead of flooding the refresh rate limit and swallowing the login form's error behind a hard redirect (root-caused from the e2e run; 3 vitest + 6 pytest regression tests) |
| **E-5** | Session-persistence e2e spec: reload survival, post-reload client navigation, logout-kills-session (16 e2e total: 9 always + 7 gated); logout affordance added to the shell footer |
| **Rates** | Login limits became settings knobs (`LOGIN_RATELIMIT_IP/USER`; production defaults unchanged 10/min + 30/min; development 60/min for the e2e budget) via `config/ratelimits.py` dotted-path callables |
| **E-2/E-3/E-4** | Docs truth pass (README/PAD/CLAUDE/AGENTS/ledgersg_SKILL), root `.env.example` index, DEPLOYMENT.md cookie-flow + reload-persistence checklist |

### Previous Milestone: P3 Sprint — Monetary Capacity, Truthful Invoice Form & Suite Depth ✅ — 2026-11-21 (session 7)

Money now fits the business model (S$1M GST threshold), the New Invoice form actually creates documents, and both frontend suites gained real depth:

| Fix | Impact |
|-----|--------|
| **C-1/H-03** | All 47 monetary columns widened `NUMERIC(10,4)` → `NUMERIC(19,4)` (schema v1.1.0): the old width capped every value at S$999,999.9999 — **below the GST registration threshold** — so F5 Box 13 and ≥ S$1M lines/journal amounts overflowed (verified live). §16 ships the idempotent in-place migration (incl. the `amount_due` generated-column drop→widen→re-add sequence); the conformance gate now asserts numeric precision; `add_line` applies `discount_pct` server-side |
| **D-1** | New Invoice form submit was a TODO stub (`console.log` + mock UUID) with `useCreateInvoice` dead code — now wired: per-line posting-account select, pure contact+document payload adapter, error banner, server-authoritative recalculation |
| **D-2** | `useInvoicePDF` read the token from `localStorage` (zero-JWT-exposure violation AND `Bearer null` → 401 on every download) — now `api.blob()` shares the single fetch+refresh auth path |
| **D-3** | Tax-code dropdown + preview use the server rows in force on the document's date (`?effective_on=` wiring); backdated documents preview at the right rate; invalid server rates fail closed to 0, never 9% |
| **D-4/D-5** | Backend `.env.example` complete (15/15 settings-read vars incl. `ALLOWED_HOSTS`); e2e suite 6 → 13 tests (auth + invoice-form specs, `E2E_API_URL`-gated, `npm run test:e2e:full`); +25 vitest tests; fresh-host `docs/DEPLOYMENT.md` |

### Previous Milestone: P1 Sprint — Green Suite & Contract Truth ✅ — 2026-11-21 (session 3)

The 26 documented `test_api_endpoints.py` fixture failures were fixed and the suite went fully green (499P/0F/5S); the fixture pass unmasked and fixed three real endpoint bugs:

| Fix | Impact |
|-----|--------|
| **A-1** | Org fixture sets `UserOrganisation.accepted_at` — the tenant middleware requires accepted memberships (25 of the 26 failures were this one omission) |
| **A-2** | `DocumentSummaryView`: real `DOCUMENT_TYPES` vocabulary, enum-correct outstanding set (`PARTIALLY_PAID`, not `PAID_PARTIAL`), `total_incl` (not phantom `total`), Decimal-safe empty sums; same enum sweep in `deactivate_contact` |
| **A-3** | CoA trial balance aggregates `journal.line` — the schema has no `coa.account_balance` view |
| **A-4** | `ValidStatusTransitionsView` accepts the `org_id` kwarg its route passes |
| **A-6** | `pyproject.toml` declares `django-celery-beat==2.9.0` + `django-ratelimit` — clean-venv install + `manage.py check` now works end-to-end |
| **A-7/8/9** | `.env.example` for both apps; `.env` files gitignored + untracked; schema header v1.0.2 |

### Latest Milestone: P0 Remediation Sprint ✅ — 2026-11-21

All four Critical findings from the independent code audit were fixed test-first:

| Fix | Impact |
|-----|--------|
| **C-04** | `wrap_response` re-raises; journal posting inside the approve atomic block — no more partial commits |
| **C-02** | Void creates a real reversal entry; `void_reason` persisted; `PARTIALLY_PAID` voidable |
| **C-03** | RLS `SET LOCAL` executes inside a request-spanning transaction — tenant isolation actually applies under autocommit |
| **C-01/H-14** | GST F5 rebuilt on `invoicing.document*` with IRAS box convention; state machine `DRAFT→COMPUTED→REVIEWED→FILED→AMENDED` persists |
| **H-01** | Trial balance / account balance endpoints work (FK + `is_posted` fixes) |
| **H-05** | Refresh-token rotation + blacklist (schema §15b); logout and password-change revoke |
| **H-06/H-07** | Production SECRET_KEY gate; rate limiting default-on |
| **M-01** | Schema–model conformance gate in CI (`tests/invariants/test_schema_conformance.py`) — caught and fixed drifted `ExchangeRate`/`OrganisationSetting` models |

**Deferred:** H-02/H-03/H-04/H-08/H-10/H-11/H-13, M-02…M-16, L-*, I-* — full register in `docs/REMEDIATION_PLAN_2026-11-21.md` §4.

### Latest Milestone: API Contract Standardization & 500 Error Investigation ✅ COMPLETE (2026-03-15; superseded in part by the 2026-11-21 audit)
**Date**: 2026-03-15
**Status**: API contracts standardized, "500 error" myth debunked.

| Achievement | Impact |
|-----|--------|
| **API Contract Fix** | 9 endpoints standardized to {results, count} format |
| **8 Contract Tests** | New TDD test suite validates API contracts |
| **500 Error Investigation** | Debunked myth - no actual 500 errors exist |
| **Root Cause Found** | Test fixture issues cause 403s, not production bugs |

**Key Finding**: The "500 errors in journal/invoice endpoints" mentioned in documentation do NOT exist. What exists are:
- **403 Forbidden** errors caused by pytest fixture isolation issues  
- The production API works correctly (verified with direct testing)
- Tests using `auth_client` + `test_organisation` separately can fail due to RLS

**Critical Finding**: HttpOnly cookies break automation tool session persistence. **Solution**: Hybrid approach (API for auth/data, UI for verification only).

### Previous Milestone: SMB Workflow Hardening ✅ COMPLETE
**Date**: 2026-03-10
**Status**: 100% Double-Entry Accuracy Verified across Lakshmi's Kitchen (12mo) and ABC Trading.

| Fix / Alignment | Impact |
|-----|--------|
| **Ghost Column Fix** | Removed invalid timestamp/audit fields from Peppol models to match SQL exactly. |
| **Journal Filter Fix** | Eliminated incorrect `is_voided` reference in `JournalService` posting loop. |
| **Accounting Engine** | Ledger now reflects all transactions (Invoices → Approval → Payment). |
| **Reporting Accuracy**| Real-time SQL aggregations for P&L/BS verified with 100% precision. |
| **Test Results** | **789 unit tests** + **3 authoritative workflows** passing. |

---

## 🧪 Testing Strategy

### E2E Workflow Validation (Recommended Approach)

**Session persistence note (P4/E-1 + P13 correction)**: real-browser
automation (Playwright, full browser contexts) DOES carry the HttpOnly
refresh cookie across navigations and reloads — the green session-persistence
e2e specs prove it. The hybrid API approach below remains the right tool
for cookie-less CLI drivers (curl, agent-browser's request mode) and for
efficient bulk data setup.

**Hybrid Approach (cookie-less CLI drivers):**
```
┌─────────────────────────────────────────────────────────────┐
│  AUTHENTICATION (API)                                       │
│  • POST /api/v1/auth/login/                                 │
│  • Store access_token in memory                              │
│  • Skip HttpOnly cookie dependency                          │
└─────────────────────────────────────────────────────────────┘
                              │
              ┌───────────────┴───────────────┐
              ▼                               ▼
┌─────────────────────────┐         ┌─────────────────────────┐
│  DATA CREATION (API)    │         │  UI VERIFICATION        │
│  • Journal entries      │         │  • Dashboard views      │
│  • Contacts             │         │  • Screenshots          │
│  • Invoices             │         │  • Visual assertions    │
│  • Payments             │         │                         │
└─────────────────────────┘         └─────────────────────────┘
```

**Why cookie-less drivers need the hybrid approach:**
- Access token stored in JavaScript memory (not accessible to CLI drivers)
- Refresh token in HttpOnly cookie (not attachable by curl-style clients)
- Result: those drivers must re-login via the API and carry the bearer token

**Standardized Validation Workflow:**
1. **API Login**: Get tokens via `POST /api/v1/auth/login/`
2. **API Data Creation**: Create all test data via authenticated API calls
3. **UI Verification**: Use Playwright for screenshots and visual checks only
4. **API Cleanup**: Delete test data via API

**Tools by Use Case:**
- **Quick checks**: agent-browser (single page only)
- **Full E2E**: the Playwright live suite (`npm run test:e2e:full`)
- **Visual regression**: Playwright with hybrid approach
- **CI/CD**: Hybrid approach with headless Playwright

---

## 🎓 Lessons Learned (2026-03-14 Update)

### E2E Testing Lessons

1. **Session Persistence is Hard**: HttpOnly cookies designed for security break automation. JWT access tokens in JavaScript memory are ephemeral. **Solution**: API-first authentication, UI only for verification.

2. **API Contracts Must Be Explicit**: Frontend expected `{results, count}`, backend returned `[]`. This broke entire Banking module. **Solution**: Schema validation, integration tests, shared contracts.

3. **Hybrid Testing is Powerful**: API for data, UI for verification. Best of both worlds. More reliable than pure UI, more visual than pure API.

4. **Tool Selection Matters**: 
   - agent-browser: Quick manual checks only
   - Playwright: Full automation with hybrid approach
   - Pure UI: Fragile, avoid for complex workflows

5. **Documentation ≠ Reality**: Test counts differed from README. Schema counts differed from PAD. Always validate against actual code.

### Previous Lessons (2026-03-10)

1. **Model Inheritance Hygiene**: Inheritance in Django is a "greedy" operation. In a SQL-First project, inheriting from `TenantModel` blindly will inject `created_at` and `updated_at` fields into your SQL queries. If the DB schema doesn't have them, the request will fail with a `ProgrammingError`.
2. **Side-Effect Determinism**: Approval is the explicit gateway to the General Ledger. This ensures that financial integrity is maintained even if operational data (DRAFT invoices) is noisy.
3. **Conflict Resilience**: Recent fixes to align `JournalService` and `Peppol` models with the SQL schema reinforce the stability of previous Meridian (Workflow 3) remediations. No regressions or conflicts were introduced.
