# LedgerSG — Comprehensive Developer Briefing

> **Single Source of Truth** for coding agents and human developers
> **Version**: 2.6.0
> **Last Updated**: 2026-11-21
> **Status**: P1 Remediated 🟢 — suite fully green (0 failed); all four Critical + the P1 contract/fixture findings fixed (see `docs/REMEDIATION_2026-11-21_REPORT.md` and `docs/REMEDIATION_2026-11-21_P1_REPORT.md`)

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
| **Frontend** | v0.1.2 | ✅ Ready | 12 pages, 321 tests, WCAG AAA |
| **Backend** | v0.3.6 | ✅ Suite Fully Green | 88+ endpoints, **499 tests passing, 0 failed** (5 skipped, documented) |
| **Database** | v1.0.2 | ✅ Complete | 7 schemas + token blacklist, RLS enforced (transaction-scoped), 30 domain tables |
| **Accounting** | v1.0.0 | ✅ Verified | 3/3 Workflows (void reversal restored 2026-11-21) |
| **Security** | v1.1.0 | ✅ P0 Hardened | Token rotation+blacklist, SECRET_KEY gate, ratelimit default-on; P1 open (CSP, MFA, PII) |
| **API Contracts** | v1.1.0 | ✅ Standardized | {results, count} lists; auth contract aligned to tests 2026-11-21 |

### Latest Milestone: P1 Sprint — Green Suite & Contract Truth ✅ — 2026-11-21 (session 3)

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

**⚠️ CRITICAL DISCOVERY**: HttpOnly cookies break browser automation tool session persistence.

**Recommended Hybrid Approach:**
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

**Why Pure UI Automation Fails:**
- Access token stored in JavaScript memory (lost on navigation)
- Refresh token in HttpOnly cookie (not sent by agent-browser/Playwright)
- Result: Redirect to login on every page navigation

**Standardized Validation Workflow:**
1. **API Login**: Get tokens via `POST /api/v1/auth/login/`
2. **API Data Creation**: Create all test data via authenticated API calls
3. **UI Verification**: Use Playwright for screenshots and visual checks only
4. **API Cleanup**: Delete test data via API

**Tools by Use Case:**
- **Quick checks**: agent-browser (single page only)
- **Full E2E**: Hybrid script (`e2e_test_phases_7_15_simplified.py`)
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
