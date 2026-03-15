# LedgerSG — Global Context & Single Source of Truth (SSOT)

> **Version**: 3.1.0  
> **Last Updated**: 2026-03-10  
> **Status**: Production Ready ✅ (Comprehensive E2E Workflow Validation Complete)  
> **Security Score**: 100% (SEC-001/002/003 Remediated)  
> **Total Tests**: 789 Unit Tests + 3 Authoritative E2E Workflows (100% Pass)

---

## 🎯 Executive Summary
**LedgerSG** is a production-grade, double-entry accounting platform purpose-built for Singapore SMBs. It transforms IRAS 2026 compliance (GST F5, InvoiceNow, BCRS) into a seamless experience with a distinctive "Illuminated Carbon" neo-brutalist UI.

---

## 📊 Verified Metrics & Status
| Component | Status | Version | Key Metrics |
| :--- | :--- | :--- | :--- |
| **Accounting Engine** | ✅ Verified | v1.0.0 | **3/3 E2E Workflows Passing**, Real-time Reports |
| **Frontend** | ✅ Production | v0.1.2 | 12 Pages, 321 Tests, WCAG AAA |
| **Backend** | ✅ Production | v0.3.3 | 84 API Endpoints, 468 Tests |
| **Database** | ✅ Complete | v1.0.3 | 7 Schemas, 29 Tables, RLS Enforced |
| **Banking UI** | ✅ Complete | v1.3.0 | 3 Tabs, 73 TDD Tests, Reconciliation Live |
| **InvoiceNow** | ✅ Complete | v1.0.0 | Phases 1-4, PINT-SG Compliant, 122+ Tests |
| **Security** | ✅ 100% Score | v1.0.0 | CSP (SEC-003), Ratelimit (SEC-002), CORS Fix |

---

## 🧪 Authoritative E2E Workflows (The Validation Gold Standard)
The system is verified against three distinct real-world scenarios. **AI Agents MUST use these as reference templates.**

### 1. Lakshmi's Kitchen (Workflow 1)
- **Profile**: Private Limited, Non-GST Registered.
- **Complexity**: **12-Month Financial Year**.
- **Scope**: Capital injection, Asset purchase, Operational revenue, Salaries, Bank Reconciliation.
- **Result**: Verified 100% accuracy in multi-director equity and P&L aggregation.

### 2. ABC Trading (Workflow 2)
- **Profile**: Sole Proprietorship, Non-GST.
- **Complexity**: 1-Month Smoke Test.
- **Scope**: Core Sales → Approval → Payment → Report cycle.
- **Result**: Verified rapid "Quick Start" deployment integrity.

### 3. Meridian Consulting (Workflow 3)
- **Profile**: Private Limited, Non-GST.
- **Complexity**: Q1 2026 Operational Cycle.
- **Scope**: Full remediation baseline for Journal Posting and Reporting.
- **Result**: Successfully triggered the transition from stubbed logic to a live engine.

---

## 🏗 Architectural Mandates (Core Rules)
1. **SQL-First Design**: `database_schema.sql` is the absolute source of truth. Models are `managed = False`. **NEVER** run `makemigrations`.
2. **Service Layer Supremacy**: Views are thin controllers; **ALL** business logic resides in `apps/backend/apps/*/services/`.
3. **RLS Context**: Every request sets PostgreSQL session variables (`app.current_org_id`) via `TenantContextMiddleware`.
4. **Financial Precision**: `NUMERIC(10,4)` for all currency. **NO FLOATS.** Use `common.decimal_utils.money()`.
5. **Approval Trigger**: `/approve/` is the **MANDATORY** gateway for General Ledger posting. Payments link to documents but only Approval creates Revenue/AR entries.

---

## 🔒 Security & Authentication
**Defense-in-Depth Hierarchy**:
- **Layer 1 (Client)**: `AuthProvider` redirects unauthenticated users to `/login`.
- **Layer 2 (Client)**: `DashboardLayout` guard prevents flash of protected content.
- **Layer 3 (Server)**: `CORSJWTAuthentication` validates JWT and handles preflight `OPTIONS` (401 bypass for preflight).
- **Layer 4 (Database)**: Row-Level Security (RLS) restricts data access to authorized `org_id`.

---

## 🚀 Latest Remediation: SMB Workflow Hardening (2026-03-10)
- ✅ **Automatic Ledger Posting**: Implemented live posting for Invoices and Payments (replacing previous stubs).
- ✅ **Ghost Column Removal**: Fixed `ProgrammingError` by removing non-existent timestamp fields from Peppol models.
- ✅ **Journal Filter Fix**: Removed invalid `is_voided` reference in `JournalService` posting loop.
- ✅ **CSV Normalization**: Implemented case-insensitive header mapping for bank statement imports.
- ✅ **Serialization**: Enhanced `DecimalSafeJSONEncoder` to support native `UUID` and `datetime` objects.

---

## 💡 Troubleshooting & Knowledge Base
- **Zero Profit in Reports**: Ensure invoices are in `APPROVED` status. Drafts do not post to GL.
- **Ghost Column Errors**: Check model inheritance. Avoid `TenantModel` for tables lacking `created_at`/`updated_at` in SQL.
- **UUID Errors**: Django URL converters already return UUID objects. **Do not** double-convert.
- **Response Wrapper**: List endpoints wrap results in `{ "data": [...] }`. Always use `jq '.data'`.

---
**Summary**: LedgerSG is a hardened, production-ready platform with 789 verified tests and 3 E2E workflows. It strictly adheres to SQL-First, Service-Layer, and RLS mandates.
