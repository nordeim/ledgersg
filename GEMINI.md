# LedgerSG — Global Context & Project Status

> **Single Source of Truth for Gemini CLI & Developers**  
> **Version**: 2.2.0  
> **Last Updated**: 2026-03-08  
> **Status**: Production Ready ✅  
> **Security Score**: 100% (SEC-001, SEC-002, SEC-003 remediated)  
> **Testing**: 651 Tests (305 Frontend + 346 Backend) — 100% Pass Rate

---

## 🎯 Project Mission
**LedgerSG** is a high-integrity, double-entry accounting platform for Singapore SMBs, purpose-built for **IRAS 2026 compliance** (GST F5, InvoiceNow, BCRS). It features a distinctive "Illuminated Carbon" neo-brutalist UI.

---

## 💻 Tech Stack & Architecture

### **Frontend (Next.js 16.1.6 + React 19)**
- **Architecture**: App Router, Server Components for data fetching (zero JWT exposure to JS).
- **UI/UX**: Tailwind CSS 4.0 + Shadcn/Radix UI.
- **State**: Zustand (UI) + TanStack Query v5 (Server State).
- **Security**: CSP Middleware with dynamic nonces, `strict-dynamic`, and Layer 2 auth guards.

### **Backend (Django 6.0.2 + DRF 3.16.1)**
- **Architecture**: Service Layer Pattern (logic in `services/`, thin views).
- **Database**: PostgreSQL 16+ with 7 domain schemas (`core`, `coa`, `gst`, `journal`, `invoicing`, `banking`, `audit`).
- **Isolation**: Row-Level Security (RLS) via `app.current_org_id` session variable.
- **Financials**: `NUMERIC(10,4)` precision. Floats are prohibited. Use `common.decimal_utils.money()`.

---

## 🏗 Architectural Mandates (Core Rules)

1.  **SQL-First Design**: `database_schema.sql` is the source of truth. Models are `managed = False`. NEVER use `makemigrations`.
2.  **Service Layer**: All business logic MUST reside in `apps/backend/apps/*/services/`.
3.  **RLS Context**: Every request sets the PG session variable via `TenantContextMiddleware`.
4.  **Security Hierarchy**:
    - **Layer 1**: AuthProvider (Client-side redirect).
    - **Layer 2**: DashboardLayout (Route guard).
    - **Layer 3**: Backend (CORSJWTAuthentication + RLS).
5.  **TDD Workflow**: RED → GREEN → REFACTOR. Backend requires manual DB initialization:
    `dropdb test_ledgersg_dev && createdb test_ledgersg_dev && psql -d test_ledgersg_dev -f database_schema.sql`

---

## 📊 Current Status & Metrics

| Component | Status | Version | Metrics |
| :--- | :--- | :--- | :--- |
| **Frontend** | ✅ Production | v0.1.0 | 12 Pages, 305 Passed Tests, WCAG AAA |
| **Backend** | ✅ Production | v1.0.0 | 96+ Endpoints, 346 Passed Tests |
| **Banking UI** | ✅ Complete | v1.3.0 | 3 Tabs (Accounts, Payments, Transactions), 73 Tests |
| **Dashboard** | ✅ Complete | v1.1.0 | Real data, Redis caching (5m TTL), 36 Tests |
| **Security** | ✅ 100% Score | v1.0.0 | Ratelimit (SEC-002), CSP (SEC-003), RLS Fixes |

---

## 🛠 Milestone Implementation Registry

### **Phase A: Journal & SQL Alignment** ✅
- Synchronized Service Layer field names (`narration`, `source_type`) with PostgreSQL schema.
- Fixed `JournalEntry`/`JournalLine` models to correctly map to unmanaged tables.

### **Phase B: Dynamic Organization Context** ✅
- Eliminated `DEFAULT_ORG_ID`. Organization selection is now dynamic via JWT claims.
- Implemented `POST /api/v1/auth/set-default-org/` and Org Selector UI in sidebar.

### **Phase 5.5: Banking & Reconciliation** ✅
- Full CRUD for Bank Accounts with Singapore PayNow badges.
- Reconciliation workflow: Match suggestions, CSV import, and real-time balance tracking.

### **CORS & Auth Flow Remediation** ✅
- **CORS Fix**: Created `CORSJWTAuthentication` to handle unauthenticated OPTIONS preflight.
- **Auth Flow**: Implemented 3-layer defense-in-depth to prevent unauthenticated access.
- **RLS Fix**: Fixed middleware to set RLS context to `''` for unauthenticated requests (PostgreSQL compliance).
- **UUID Fix**: Removed redundant `UUID()` re-conversions in views (Django URL converters handle this).

---

## 📁 Critical Files & Commands

- **DB Schema**: `database_schema.sql`
- **Auth Client**: `apps/web/src/lib/api-client.ts`
- **RLS Middleware**: `apps/backend/common/middleware/tenant_context.py`
- **Auth Logic**: `apps/backend/apps/core/authentication.py`

**Testing Commands:**
- **Backend**: `pytest --reuse-db --no-migrations` (Requires manual DB init first).
- **Frontend**: `npm test` (Vitest).

---

## 💡 Troubleshooting Reference

- **UUID Error**: `AttributeError: 'UUID' object has no attribute 'replace'`. Fix: Remove `UUID(org_id)` in view; it's already a UUID.
- **CORS 401**: OPTIONS request fails. Fix: Use `CORSJWTAuthentication` (returns `None` for OPTIONS).
- **RLS 403**: User exists but has no access. Fix: Check `UserOrganisation.accepted_at` is not NULL.
- **DB Sync**: `relation "X" does not exist`. Fix: Models out of sync with `database_schema.sql`.

---

## 🚀 Strategic Roadmap (Next Steps)

1.  **SEC-004**: Expand frontend test coverage for complex hooks and forms.
2.  **SEC-005**: Implement PII encryption at rest (pgcrypto) for GST/UEN/Bank Account numbers.
3.  **Peppol XML**: Finalize InvoiceNow (PINT-SG) transmission logic.
4.  **CI/CD**: Automate the manual test database initialization in GitHub Actions.

---
**Summary**: LedgerSG is a production-grade platform with 651 verified tests and 100% security score. It strictly follows a SQL-First, Service-Layer architecture with RLS-enforced multi-tenancy.
