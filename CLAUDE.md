# LedgerSG — Comprehensive Developer Briefing

> **Single Source of Truth** for coding agents and human developers
> **Version**: 2.3.0
> **Last Updated**: 2026-03-10
> **Status**: Production Ready ✅ (Complete SMB Workflow Validation: Lakshmi, ABC, Meridian)

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
| **Frontend** | v0.1.2 | ✅ Production Ready | 12 pages, **321 tests**, WCAG AAA |
| **Backend** | v0.3.3 | ✅ Production Ready | **84 API endpoints**, **468 tests** |
| **Database** | v1.0.3 | ✅ Complete | 7 schemas, RLS enforced, **29 tables** |
| **Accounting** | v1.0.0 | ✅ Verified | **3/3 Workflows Passing** (Full FY & Smoke Tests) |
| **Security** | v1.0.0 | ✅ **100% Score** | Rate limiting, CSP, CORS Fix Complete |
| **InvoiceNow** | v1.0.0 | ✅ **Phases 1-4 Complete** | 122+ TDD tests, PINT-SG compliant XML |
| **Overall** | — | ✅ **Platform Ready** | **789 tests**, 3 E2E Workflows verified |

### Latest Milestone: E2E Testing Initiative Complete ✅ COMPLETE
**Date**: 2026-03-14
**Status**: 15-phase comprehensive E2E test suite completed using Hybrid API + UI approach.

| Achievement | Impact |
|-----|--------|
| **15-Phase E2E Suite** | Complete "Lakshmi's Kitchen" workflow from login through financial reporting |
| **API Contract Fix** | Fixed critical mismatch in 9 list views (Banking, Invoicing, GST, COA, Journal) |
| **25+ Screenshots** | Full visual documentation of test execution |
| **Experience Report** | 898-line comprehensive guide with lessons learned & best practices |
| **Test Automation** | `e2e_test_phases_7_15_simplified.py` for reproducible testing |
| **Tool Analysis** | Complete agent-browser vs Playwright comparison with recommendations |

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
