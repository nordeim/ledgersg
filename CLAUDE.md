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

### Latest Milestone: SMB Workflow Hardening ✅ COMPLETE
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

### E2E Workflow Validation (Workflow Template)

Standardized validation workflow for any new SMB scenario:
1. **Reset Database**: `dropdb` → `createdb` → `psql -f database_schema.sql`.
2. **Registration**: `POST /api/v1/auth/register/`.
3. **Organisation**: `POST /api/v1/organisations/` (Note: `gst_registered: false` for smoke tests).
4. **Approval**: `POST /invoicing/documents/{id}/approve/` (MANDATORY for ledger posting).
5. **Reconciliation**: CSV import with normalized headers.

---

## 🎓 Lessons Learned (2026-03-10 Update)

1.  **Model Inheritance Hygiene**: Inheritance in Django is a "greedy" operation. In a SQL-First project, inheriting from `TenantModel` blindly will inject `created_at` and `updated_at` fields into your SQL queries. If the DB schema doesn't have them, the request will fail with a `ProgrammingError`.
2.  **Side-Effect Determinism**: Approval is the explicit gateway to the General Ledger. This ensures that financial integrity is maintained even if operational data (DRAFT invoices) is noisy.
3.  **Conflict Resilience**: Recent fixes to align `JournalService` and `Peppol` models with the SQL schema reinforce the stability of previous Meridian (Workflow 3) remediations. No regressions or conflicts were introduced.
