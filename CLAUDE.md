# LedgerSG — Comprehensive Developer Briefing

> **Single Source of Truth** for coding agents and human developers
> **Version**: 1.8.0
> **Last Updated**: 2026-03-03
> **Status**: Production Ready ✅ (SEC-001, SEC-002, Phase B, Phase 3 Complete)

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
10. [API Reference](#-api-reference)
11. [Common Development Tasks](#-common-development-tasks)
12. [Troubleshooting](#-troubleshooting)

---

## 🎯 Executive Summary

**LedgerSG** is a production-grade, double-entry accounting platform purpose-built for Singapore SMBs. It transforms IRAS compliance from a burden into a seamless, automated experience while delivering a distinctive "Illuminated Carbon" neo-brutalist user interface.

### Current Status

| Component | Version | Status | Key Metrics |
|-----------|---------|--------|-------------|
| **Frontend** | v0.1.1 | ✅ Production Ready | 11 pages, dynamic org context, 5 test files |
| **Backend** | v0.3.3 | ✅ Production Ready | **81 API endpoints**, 14 test files |
| **Database** | v1.0.3 | ✅ Complete | 7 schemas, RLS enforced, 28 tables |
| **Dashboard** | v1.0.0 | ✅ Production Ready | **21 TDD tests**, 100% coverage, real data |
| **Banking** | v0.6.0 | ✅ SEC-001 Fully Remediated | 55 tests (services + views), 13 validated endpoints |
| **Security** | v1.0.0 | ✅ SEC-002 Remediated | Rate limiting on auth endpoints |
| **Integration** | v1.1.0 | ✅ **Complete** | All endpoint paths aligned, Dashboard real data |
| **Testing** | — | ✅ **108+ Passing** | 87 backend + 21 TDD dashboard tests |
| **Overall** | — | ✅ **Platform Ready** | **108+ tests**, WCAG AAA, IRAS Compliant, 98% Security |

---

## 🔧 Backend Deep Dive

### Technology Stack

| Layer | Technology | Version | Purpose |
|-------|------------|---------|---------|
| Framework | Django | 6.0.2 | Web framework |
| API | Django REST Framework | 3.16.1 | REST endpoints |
| Auth | djangorestframework-simplejwt | Latest | JWT authentication |
| Database | PostgreSQL | 16+ | Primary data store |
| Task Queue | Celery + Redis | 5.4+ / 7+ | Async processing |
| Testing | pytest-django | Latest | Unit/integration tests |

### Backend Metrics

| Metric | Value | Notes |
|--------|-------|-------|
| API Endpoints | **81** | 100% Path Alignment (verified against all URL configs) |
| Service Files | 14 | Core business logic (core: 3, banking: 3, invoicing: 2, gst: 3, journal: 2, reporting: 1) |
| Models | **25** | Aligned with SQL schema (all apps/core/models/) |
| Test Files | 14 | 87 test functions (integration + security) + 21 TDD dashboard tests |
| Lines of Code | **~15,500+** | Logic & Templates |

### Directory Structure

```
apps/backend/
├── apps/
│   ├── core/          # Restored: AppUser, Role, JournalEntry, InvoiceLine, GSTReturn, etc.
│   ├── coa/           # Chart of Accounts
│   ├── gst/           # GST Module
│   ├── invoicing/     # Invoicing (PDF & Email Logic)
│   ├── journal/       # Journal Entry
│   ├── banking/       # Banking
│   └── reporting/     # Dashboard & Reports (NEW: DashboardService)
├── common/            # BaseModel, TenantModel, decimal_utils
├── config/            # settings/base.py, celery.py
└── tests/             # integration/, security/
```

---

## 🗄 Database Architecture

### PostgreSQL Configuration

| Setting | Value | Purpose |
|---------|-------|---------|
| **Schemas** | 7 (core, coa, gst, journal, invoicing, banking, audit) | Domain separation |
| **Money Precision** | `NUMERIC(10,4)` | 4 decimal places for all amounts |
| **RLS** | Session variable `app.current_org_id` | Multi-tenant isolation |
| **Integrity** | Circular Deps Resolved | ALTER TABLE FK strategy |

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
10. [API Reference](#-api-reference)
11. [Common Development Tasks](#-common-development-tasks)
12. [Troubleshooting](#-troubleshooting)

---

## 🎯 Executive Summary

**LedgerSG** is a production-grade, double-entry accounting platform purpose-built for Singapore SMBs. It transforms IRAS compliance from a burden into a seamless, automated experience while delivering a distinctive "Illuminated Carbon" neo-brutalist user interface.

### Current Status

| Component | Version | Status | Key Metrics |
|-----------|---------|--------|-------------|
| **Frontend** | v0.1.1 | ✅ Production Ready | 11 pages, dynamic org context, 5 test files |
| **Backend** | v0.3.3 | ✅ Production Ready | **81 API endpoints** (+5 Phase 1), 13 test files |
| **Database** | v1.0.3 | ✅ Complete | 7 schemas, RLS enforced, 28 tables |
| **Banking** | v0.6.0 | ✅ SEC-001 Fully Remediated | 55 tests (services + views), 13 validated endpoints |
| **Security** | v1.0.0 | ✅ SEC-002 Remediated | Rate limiting on auth endpoints |
| **Integration** | v1.0.0 | ✅ **Fixed** | Critical endpoint path mismatches resolved |
| **Testing** | — | ✅ 87+ Passing | 82 backend + 5 frontend tests (functions) |
| **Overall** | — | ✅ **Platform Ready** | **87+ tests**, WCAG AAA, IRAS Compliant, 98% Security |

---

## 🔧 Backend Deep Dive

### Technology Stack

| Layer | Technology | Version | Purpose |
|-------|------------|---------|---------|
| Framework | Django | 6.0.2 | Web framework |
| API | Django REST Framework | 3.16.1 | REST endpoints |
| Auth | djangorestframework-simplejwt | Latest | JWT authentication |
| Database | PostgreSQL | 16+ | Primary data store |
| Task Queue | Celery + Redis | 5.4+ / 7+ | Async processing |
| Testing | pytest-django | Latest | Unit/integration tests |

### Backend Metrics

| Metric | Value | Notes |
|--------|-------|-------|
| API Endpoints | **76** | 100% Path Alignment (verified against all URL configs) |
| Service Files | 13 | Core business logic (core: 3, banking: 3, invoicing: 2, gst: 3, journal: 2) |
| Models | **25** | Aligned with SQL schema (all apps/core/models/) |
| Test Files | 13 | 82 test functions (integration + security) |
| Lines of Code | **~14,000+** | Logic & Templates |

### Directory Structure

```
apps/backend/
├── apps/
│   ├── core/              # Restored: AppUser, Role, JournalEntry, InvoiceLine, GSTReturn, etc.
│   ├── coa/               # Chart of Accounts
│   ├── gst/               # GST Module
│   ├── invoicing/         # Invoicing (PDF & Email Logic)
│   ├── journal/           # Journal Entry
│   ├── banking/           # Banking
│   └── reporting/         # Dashboard & Reports
├── common/                # BaseModel, TenantModel, decimal_utils
├── config/                # settings/base.py, celery.py
└── tests/                 # integration/, security/
```

---

## 🗄 Database Architecture

### PostgreSQL Configuration

| Setting | Value | Purpose |
|---------|-------|---------|
| **Schemas** | 7 (core, coa, gst, journal, invoicing, banking, audit) | Domain separation |
| **Money Precision** | `NUMERIC(10,4)` | 4 decimal places for all amounts |
| **RLS** | Session variable `app.current_org_id` | Multi-tenant isolation |
| **Integrity** | Circular Deps Resolved | ALTER TABLE FK strategy |

---

## 🧪 Testing Strategy

### Test-Driven Development (TDD)

LedgerSG follows TDD for critical business logic:

```bash
# 1. Write tests first (Red phase)
# tests/test_dashboard_service.py - define expected behavior

# 2. Run tests - they should fail
pytest apps/core/tests/test_dashboard_service.py -v

# 3. Implement code to pass tests (Green phase)
# apps/core/services/dashboard_service.py

# 4. Refactor while keeping tests passing
# Clean code, optimize, document

# 5. All 22 dashboard tests now pass
pytest apps/core/tests/test_dashboard_service.py apps/core/tests/test_dashboard_view.py -v
```

### Backend Tests (Unmanaged Database Workflow)

**MANDATORY Workflow:**
```bash
# 1. Manually initialize the test database
export PGPASSWORD=ledgersg_secret_to_change
dropdb -h localhost -U ledgersg test_ledgersg_dev
createdb -h localhost -U ledgersg test_ledgersg_dev
psql -h localhost -U ledgersg -d test_ledgersg_dev -f database_schema.sql

# 2. Run tests with reuse flags
source /opt/venv/bin/activate
cd apps/backend
pytest --reuse-db --no-migrations
```

---

## 🔧 Troubleshooting

### Dashboard API Issues
- **403 Forbidden on /dashboard/**: Check `UserOrganisation.accepted_at` is set (middleware requires it)
- **500 Internal Server Error**: Check `InvoiceDocument` model matches SQL schema (no extra fields)
- **Enum Value Errors**: Ensure status values match SQL enum exactly (`PARTIALLY_PAID` not `PARTIAL`)
- **Mock Data Still Showing**: DashboardPage must be async Server Component calling `fetchDashboardData()`

### Database Issues
- **relation "core.app_user" does not exist**: The test database is empty. Load `database_schema.sql` manually.
- **TypeError: X() got unexpected keyword arguments**: Model and Schema out of sync. LedgerSG is **SQL-First**; update models to match DB columns.
- **circular dependency on DB init**: FKs must be added via `ALTER TABLE` at the end of the script.
- **TaxCode constraint violation**: SQL requires `is_input=TRUE OR is_output=TRUE OR code='NA'`. Ensure fixtures set at least one direction flag.

### Import Errors
- **ImportError: cannot import name 'X' from 'apps.core.models'**: Check `apps/core/models/__init__.py`. New models must be explicitly exported.

### Frontend Issues
- **API connection failed**: Ensure `NEXT_PUBLIC_API_URL` is set in `.env.local` and CORS is configured on backend.
- **npm run start serves static only**: Use `npm run start:server` for API integration (standalone mode).
- **"Loading..." stuck on dashboard**: Static files not copied or hydration mismatch. Rebuild with `npm run build:server`.
- **404 errors for JS chunks**: Static files missing from standalone. Build script auto-copies now.
- **Hydration mismatch errors**: Component renders differently on server vs client. Convert to Server Component.

### Docker Issues
- **Frontend can't reach backend**: Verify `NEXT_PUBLIC_API_URL` points to correct backend host (use `http://localhost:8000` for local Docker).
- **Port conflicts**: Ensure ports 3000, 8000, 5432, 6379 are available before running container.

---

## 🚀 Recent Milestones

### Phase B: Dynamic Organization Context ✅ COMPLETE (2026-03-03)
- **Hardcoded Org Removed**: Eliminated `DEFAULT_ORG_ID` constant from dashboard
- **JWT Claims Added**: `default_org_id` and `default_org_name` embedded in access token
- **New Endpoint**: `POST /api/v1/auth/set-default-org/` for changing user's default org
- **Org Selector UI**: Sidebar shows current org with dropdown to switch
- **Client-Side Context**: Dashboard uses `useAuth()` hook for dynamic org resolution
- **TDD Tests**: 12 tests created for auth org context endpoints
- **Files Modified**: 
  - `apps/core/services/auth_service.py` — JWT token generation
  - `apps/core/views/auth.py` — New `set_default_org_view`
  - `apps/web/src/providers/auth-provider.tsx` — Fixed org endpoint handling
  - `apps/web/src/app/(dashboard)/dashboard/dashboard-client.tsx` — New client component
  - `apps/web/src/components/layout/shell.tsx` — Org selector UI

### SEC-002 Rate Limiting Remediation (2026-03-02) ✅ COMPLETE
- **django-ratelimit v4.1.0**: Installed and configured
- **Rate Limits**: Registration (5/hr IP), Login (10/min IP + 30/min user), Refresh (20/min IP)
- **Redis Cache**: Rate limit counts persisted in Redis
- **Custom 429 Handler**: LedgerSG-formatted error responses with Retry-After headers
- **Security Tests**: 5 configuration tests passing
- **Security Score**: Improved from 95% to 98%

### SEC-001 Banking Module Remediation (2026-03-02) ✅ COMPLETE
- **Test-Driven Development**: 55 tests written (14 bank account + 15 payment + 7 reconciliation + 11 view/serializer + 8 allocation)
- **All Stubs Replaced**: 13 validated API endpoints
- **Service Layer**: BankAccountService, PaymentService, ReconciliationService
- **View Layer**: Serializers validated at API layer (BankAccountCreateSerializer, PaymentReceiveSerializer, etc.)
- **Database Enhancements**: `updated_at` column, `get_next_document_number()` function
- **Multi-Currency**: FX gain/loss tracking with base currency conversion
- **Audit Logging**: All operations logged to audit.event_log
- **Bug Fixes**: Fixed `UNRECONCILE` → `DELETE` audit action, fixed `account_type.name` → `account_type.upper()`

### Dashboard API & Real Data Integration (TDD) (2026-02-28) ✅
- **Test-Driven Development**: 22 tests written first, then implemented (Red → Green)
- **DashboardService**: Aggregates GST, cash, receivables, revenue, compliance alerts
- **DashboardView API**: `GET /api/v1/{org_id}/dashboard/` - 10 API tests passing
- **Server-Side Auth**: HTTP-only cookies, automatic token refresh
- **Real Data**: Dashboard now fetches live data instead of static mocks

### Frontend SSR & Hydration Fix (2026-02-28) ✅
- **"Loading..." Stuck State Fixed**: Dashboard now renders immediately with full content.
- **Server Component Conversion**: Dashboard converted from Client to Server Component.
- **Static Files Auto-Copy**: Build script now copies `.next/static` to standalone folder automatically.
- **Hydration Mismatch Resolution**: Fixed shell.tsx and ClientOnly components.
- **New Components**: `dashboard-actions.tsx`, `gst-chart-wrapper.tsx` for client interactivity.

### Django Model Remediation (2026-02-27) ✅
- **22 Models Aligned**: Complete audit and alignment with SQL schema v1.0.2.
- **TaxCode Fixed**: Removed invalid fields (`name`, `is_gst_charged`, `box_mapping`), added IRAS F5 box mappings (`f5_supply_box`, `f5_purchase_box`, `f5_tax_box`).
- **InvoiceDocument Enhanced**: Added 28 new fields including `sequence_number`, `contact_snapshot`, `created_by`, base currency fields.
- **Organisation Updated**: GST scheme alignment, removed non-existent `gst_scheme` from SQL.

### Backend Test Infrastructure (2026-02-27) ✅
- **52 Tests Passing**: Fixed `conftest.py` fixtures for SQL constraint compliance.
- **TaxCode Fixtures**: Updated to use `description`, `is_input`, `is_output`, `is_claimable` fields.
- **Contact Fixtures**: Added required `contact_type` field.
- **GSTReturn Fixtures**: Aligned with model field structure.

### Frontend Startup & Docker (2026-02-27) ✅
- **Dual-Mode Config**: `next.config.ts` supports both static export and standalone server.
- **API Integration**: Frontend connects to backend at `http://localhost:8000` with CORS configured.
- **Docker Live**: Multi-service container with PostgreSQL, Redis, Django, Next.js.
- **Standalone Mode**: Frontend runs via `node .next/standalone/server.js` for API access.

### PDF & Email Services (2026-02-27) ✅
- **PDF Generation**: Live via WeasyPrint with IRAS-compliant templates.
- **Email Delivery**: Asynchronous Celery tasks with PDF attachments.
- **API Alignment**: `InvoicePDFView` returns `FileResponse` binary.

### Database & Model Hardening (2026-02-27) ✅
- **Restored Models**: `InvoiceLine`, `JournalEntry`, `JournalLine`, `GSTReturn`.
- **Django 6.0 Alignment**: `AppUser` hardened with `password`, `is_staff`, `is_superuser`.
- **Schema Patches**: 20+ columns added to align SQL with Python models.
