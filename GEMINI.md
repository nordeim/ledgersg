# LedgerSG — Global Context & Single Source of Truth (SSOT)

> **Version**: 3.0.0  
> **Last Updated**: 2026-03-10  
> **Status**: Production Ready ✅ (Remediation Phase Complete)  
> **Security Score**: 100% (SEC-001/002/003 Remediated)  
> **Total Tests**: 789 (321 Frontend + 468 Backend) — 100% Pass Rate

---

## 🎯 Executive Summary
**LedgerSG** is a production-grade, double-entry accounting platform purpose-built for Singapore SMBs. It transforms IRAS 2026 compliance (GST F5, InvoiceNow, BCRS) into a seamless experience with a distinctive "Illuminated Carbon" neo-brutalist UI.

---

## 📊 Verified Metrics & Status
| Component | Status | Version | Key Metrics |
| :--- | :--- | :--- | :--- |
| **Frontend** | ✅ Production | v0.1.2 | 12 Pages, 321 Tests, WCAG AAA |
| **Backend** | ✅ Production | v0.3.3 | 84 API Endpoints, 468 Tests |
| **Database** | ✅ Complete | v1.0.3 | 7 Schemas, 29 Tables, RLS Enforced |
| **Banking UI** | ✅ Complete | v1.3.0 | 3 Tabs, 73 TDD Tests, Reconciliation Live |
| **InvoiceNow** | ✅ Complete | v1.0.0 | Phases 1-4, PINT-SG Compliant, 122+ Tests |
| **Security** | ✅ 100% Score | v1.0.0 | CSP (SEC-003), Ratelimit (SEC-002) |

---

## 🏗 Architectural Mandates (Core Rules)
1. **SQL-First Design**: `database_schema.sql` is the absolute source of truth. Models are `managed = False`. **NEVER** run `makemigrations`.
2. **Service Layer Supremacy**: Views are thin controllers; **ALL** business logic resides in `apps/backend/apps/*/services/`.
3. **RLS Context**: Every request sets PostgreSQL session variables (`app.current_org_id`) via `TenantContextMiddleware`.
4. **Financial Precision**: `NUMERIC(10,4)` for all currency. **NO FLOATS.** Use `common.decimal_utils.money()`.
5. **Double-Entry Integrity**: Enforced at database level; debits **must** equal credits.

---

## 🔒 Security & Authentication
**Defense-in-Depth Hierarchy**:
- **Layer 1 (Client)**: `AuthProvider` redirects unauthenticated users to `/login`.
- **Layer 2 (Client)**: `DashboardLayout` guard prevents flash of protected content.
- **Layer 3 (Server)**: `CORSJWTAuthentication` validates JWT and handles preflight `OPTIONS` (401 bypass for preflight).
- **Layer 4 (Database)**: Row-Level Security (RLS) restricts data access to authorized `org_id`.

**Verified Policies**:
- **CSP**: Strict `default-src 'none'`, `script-src 'self'`. Violation tracking at `/api/v1/security/csp-report/`.
- **Rate Limiting**: Auth endpoints (Login: 10/min per IP).

---

## 💻 Technology Stack
- **Frontend**: Next.js 16.1.6 (App Router), React 19.2, Tailwind 4.0, Shadcn/Radix, Zustand, TanStack Query v5.
- **Backend**: Django 6.0.2, DRF 3.16.1, Celery 5.6.2, Redis 6.4.0, WeasyPrint 68.1.
- **Data**: PostgreSQL 16+, 7 Schemas, RLS, 29 Tables.

---

## 🧪 Development Lifecycle & Testing
**TDD Methodology**: RED → GREEN → REFACTOR is mandatory for all business logic.

**Backend Test Workflow**:
Manual database initialization is required before running pytest:
```bash
dropdb test_ledgersg_dev && createdb test_ledgersg_dev && psql -d test_ledgersg_dev -f apps/backend/database_schema.sql
pytest --reuse-db --no-migrations
```

**Frontend Test Workflow**:
```bash
npm test # Vitest + RTL
```

---

## 🚀 Latest Milestone: Frontend-Backend Remediation (2026-03-10)
- ✅ **Auth Refresh Fixed**: Resolved critical token refresh bug (`data.access` vs `data.tokens.access`).
- ✅ **Backward Compatibility**: Supports both nested and flat API response structures.
- ✅ **Tests Added**: +16 TDD tests documenting auth and organisation endpoint behavior.
- ✅ **Technical Debt**: Organisation endpoints documented for future refactor to standard `/org/<id>/` pattern.

---

## 💡 Troubleshooting & Knowledge Base
- **UUID Errors**: Django URL converters already return UUID objects. **Do not** double-convert with `UUID(org_id)`.
- **CORS 401**: OPTIONS preflight failures require checking `CORSJWTAuthentication` in settings.
- **RLS 403**: Check if `UserOrganisation.accepted_at` is set (middleware requirement).
- **TanStack Query v5**: Mutations use `isPending` instead of `isLoading`.

---
**Summary**: LedgerSG is a hardened, production-ready platform with 789 verified tests. It strictly adheres to SQL-First, Service-Layer, and RLS mandates.
