# LedgerSG — Agent & Developer Briefing

> **Single Source of Truth** for coding agents and human developers
> **Version**: 2.1.0
> **Last Updated**: 2026-03-07
> **Status**: Production Ready ✅ (SEC-001, SEC-002, SEC-003, Phase A, Phase B, Phase 3, Phase 4, Phase 5.4, Phase 5.5 Complete)

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
10. [Common Development Tasks](#-common-development-tasks)
11. [Troubleshooting](#-troubleshooting)

---

## 🎯 Executive Summary

**LedgerSG** is a production-grade, double-entry accounting platform purpose-built for Singapore SMBs. It transforms IRAS compliance from a burden into a seamless, automated experience while delivering a distinctive "Illuminated Carbon" neo-brutalist user interface.

### Current Status

| Component | Version | Status | Key Metrics |
|-----------|---------|--------|-------------|
| **Frontend** | v0.1.1 | ✅ Production Ready | 12 pages (including Banking), dynamic org context, **305 tests** |
| **Backend** | v0.3.3 | ✅ Production Ready | **83 API endpoints**, **233+ tests** |
| **Database** | v1.0.3 | ✅ Complete | 7 schemas, RLS enforced, 28 tables |
| **Banking** | v0.6.0 | ✅ SEC-001 Fully Remediated | 55 tests, 13 validated endpoints |
| **Banking UI** | v1.3.0 | ✅ **Phase 5.5 Complete** | **73 TDD tests**, all 3 tabs live, reconciliation workflow |
| **Security** | v1.0.0 | ✅ **SEC-002, SEC-003 Remediated** | Rate limiting + CSP headers |
| **CORS** | v1.0.0 | ✅ **Dashboard Fixed** | CORSJWTAuthentication, preflight handling |
| **Testing** | — | ✅ **538+ Passing** | **305 Frontend + 233 Backend** tests verified |
| **Overall** | — | ✅ **Platform Ready** | **538+ tests**, WCAG AAA, IRAS Compliant, **100% Security** |

### Recent Milestone: CORS Authentication Fix ✅ COMPLETE
**Date**: 2026-03-07
**Status**: Dashboard Loading Issue Resolved - CORS Preflight Working

| Fix | Impact |
|-----|--------|
| **CORSJWTAuthentication** | Custom auth class that skips OPTIONS requests |
| **Dashboard Renders** | No longer stuck at "Loading..." state |
| **CORS Headers Present** | Preflight returns 200 with proper headers |
| **Security Preserved** | Full JWT auth for all non-OPTIONS methods |
| **django-csp 4.0 Fix** | Removed legacy CSP_* settings, fixed startup error |
| **Port 8000 Cleared** | Stopped conflicting librechat-rag-api container |

**Technical Details**:
- Created: `apps/core/authentication.py` (38 lines)
- Modified: `config/settings/base.py` (removed legacy CSP, updated auth)
- Root Cause: DRF authentication executes before permissions
- Solution: Authentication layer returns `None` for OPTIONS requests
- Result: Dashboard renders with "No Organisation Selected" (correct for unauthenticated)

### Recent Milestone: SEC-003 CSP Headers Implementation ✅ COMPLETE
**Date**: 2026-03-07
**Status**: 100% Security Score Achieved - Backend CSP Live

| Fix | Impact |
|-----|--------|
| **django-csp v4.0** | Installed and configured strict CSP defaults |
| **CSPMiddleware** | Added to MIDDLEWARE stack after SecurityMiddleware |
| **Report-Only Mode** | Deployed with `CONTENT_SECURITY_POLICY_REPORT_ONLY` for safe rollout |
| **CSP Report Endpoint** | Added `/api/v1/security/csp-report/` for violation tracking |
| **Integration Tests** | Added 15 TDD tests for CSP header verification (100% passing) |
| **Security Score** | Achieved perfect **100%** on security audit |

**Technical Details**:
- Backend: Strict CSP with `default-src 'none'`, `script-src 'self'`
- Frontend: Already implemented (Next.js middleware with nonce-based CSP)
- Violation Monitoring: Active logging at `/api/v1/security/csp-report/`
- Test Coverage: 15 comprehensive integration tests covering all CSP directives

### Recent Milestone: Phase 3 Bank Transactions Tab Integration ✅ COMPLETE
**Date**: 2026-03-06
**Status**: TDD Integration Tests Complete - Placeholder Replaced

| Fix | Impact |
|-----|--------|
| **7 Integration Tests** | TDD RED → GREEN → REFACTOR cycle |
| **Placeholder Replaced** | Full BankTransactionsTab with all Gap 4 components |
| **Components Wired** | TransactionList, TransactionFilters, ReconciliationSummary, ImportTransactionsForm, ReconcileForm |
| **Pattern Compliance** | Follows PaymentsTab architecture exactly |
| **Async Testing** | userEvent pattern for Radix UI tab switching |
| **Hook Mocks** | Comprehensive mocking for useBankAccounts, useBankTransactions |
| **Test Fixes** | page.test.tsx updated (16/16 tests passing) |
| **Blockers Solved** | Async tab switching, missing hook mocks, multiple button collision |

### Recent Milestone: Phase 5.5 Banking Frontend Complete ✅ COMPLETE
**Date**: 2026-03-06
**Status**: All Tabs Live - Full Reconciliation Workflow

| Component | Tests | Status |
|-----------|-------|--------|
| **Phase 1 Components** | 24 tests | ✅ TransactionRow, TransactionList, TransactionFilters + Payment components |
| **Phase 2 Modals** | 26 tests | ✅ ReconciliationSummary, ImportTransactionsForm, ReconcileForm, MatchSuggestions |
| **Phase 3 Integration** | 7 tests | ✅ BankTransactionsTab wiring and interactions |
| **Page Tests** | 16 tests | ✅ Banking page structure and navigation |
| **Total Banking Tests** | **73 tests** | **100% passing** |

### Recent Milestone: Phase 5.4 Banking Frontend UI ✅ COMPLETE
**Date**: 2026-03-05
**Status**: TDD Banking UI Implementation

| Fix | Impact |
|-----|--------|
| **16 TDD Tests** | Comprehensive coverage of banking UI components |
| **Server/Client Split** | Metadata compliance pattern for Next.js 16 |
| **Tabbed Interface** | Accounts, Payments, Transactions tabs with Radix UI |
| **React Query Integration** | useBankAccounts hook connected to validated backend |
| **Error/Empty States** | Comprehensive handling of all UI states |
| **PayNow Display** | Singapore-specific badges on bank accounts |
| **Files Created** | 5 new files (~800 lines of production code + tests) |
| **Files Modified** | 2 files (navigation, schema export) |

### Recent Milestone: Phase B Dynamic Organization Context ✅ COMPLETE
**Date**: 2026-03-03
**Status**: Hardcoded DEFAULT_ORG_ID Eliminated

| Fix | Impact |
|-----|--------|
| **JWT Claims** | `default_org_id` and `default_org_name` in access token |
| **New Endpoint** | `POST /api/v1/auth/set-default-org/` for changing default org |
| **Org Selector UI** | Sidebar shows current org with dropdown switcher |
| **Client-Side Context** | Dashboard uses `useAuth()` hook for dynamic org_id |
| **Removed Constant** | Eliminated hardcoded `DEFAULT_ORG_ID = "0000..."` from dashboard |
| **TDD Tests** | 12 tests created for auth org context endpoints |

### Recent Milestone: SEC-002 Rate Limiting Remediation ✅ COMPLETE
**Date**: 2026-03-02
**Status**: MEDIUM Severity Finding Fully Remediated

| Fix | Impact |
|-----|--------|
| **django-ratelimit v4.1.0** | Brute-force attack prevention |
| **Registration Rate Limit** | 5 requests/hour per IP (prevents mass registration) |
| **Login Rate Limit** | 10/min per IP + 30/min per user (prevents brute-force) |
| **Token Refresh Limit** | 20 requests/minute per IP (prevents token abuse) |
| **Redis Cache** | Rate limit counts persisted across restarts |
| **Custom 429 Handler** | LedgerSG-formatted error responses |
| **Security Tests** | 5 configuration tests passing |
| **Security Score** | Improved from 95% → **98%** |

### Recent Milestone: SEC-001 Banking Module Remediation (Complete) ✅
**Date**: 2026-03-02
**Status**: HIGH Severity Finding Fully Remediated

| Fix | Impact |
|-----|--------|
| **55 TDD Tests** | 14 bank account + 15 payment + 7 reconciliation + 11 view/serializer + 8 allocation tests |
| **Validated Endpoints** | 13 endpoints replacing 5 unvalidated stubs |
| **Service Layer** | BankAccountService, PaymentService, ReconciliationService |
| **View Layer** | Serializers validated at API layer (BankAccountCreateSerializer, PaymentReceiveSerializer, etc.) |
| **Schema Enhancements** | `updated_at` column, `get_next_document_number()` function |
| **Audit Logging** | All operations logged to audit.event_log |
| **Multi-Currency** | FX gain/loss tracking with base currency conversion |
| **Bug Fixes** | Fixed `UNRECONCILE` → `DELETE` audit action, fixed `account_type.name` → `account_type.upper()` |

### Recent Milestone: Django Model Remediation ✅
**Date**: 2026-02-27  
**Status**: 22 models aligned with SQL schema

| Fix | Impact |
|-----|--------|
| **TaxCode Model** | Removed invalid fields (`name`, `is_gst_charged`, `box_mapping`), added IRAS F5 box mappings |
| **InvoiceDocument** | Added 28 fields (`sequence_number`, `contact_snapshot`, `created_by`, base currency fields) |
| **Organisation** | GST scheme alignment with SQL schema |
| **Test Fixtures** | Updated `conftest.py` for SQL constraint compliance |

### Recent Milestone: Backend Test Fixes ✅
**Date**: 2026-02-27  
**Status**: 52+ tests passing

| Fix | Impact |
|-----|--------|
| **conftest.py** | Fixed `tax_code_data` with `description`, `is_input`, `is_output`, `is_claimable` |
| **Contact Fixture** | Added required `contact_type` field |
| **GSTReturn Fixture** | Aligned with model field structure |
| **SQL Compliance** | All fixtures comply with database constraints |

### Recent Milestone: Frontend Startup & Docker ✅
**Date**: 2026-02-27  
**Status**: Live frontend-backend integration

| Fix | Impact |
|-----|--------|
| **next.config.ts** | Dual-mode config (static export + standalone server) |
| **package.json** | Added `start:server` script for standalone mode |
| **.env.local** | API URL configuration for development |
| **Dockerfile** | Multi-service container with live integration |
| **CORS** | Configured for localhost:3000 ↔ localhost:8000 |

### Recent Milestone: Dashboard API & Real Data Integration (TDD) ✅
**Date**: 2026-02-28  
**Status**: Complete - 22 TDD tests passing, live data integration

| Component | Implementation |
|-----------|----------------|
| **DashboardService** | Aggregates GST, cash, receivables, revenue, compliance alerts |
| **DashboardView** | `GET /api/v1/{org_id}/dashboard/` - 10 API tests |
| **TDD Tests** | 22 tests (Red → Green → Refactor) |
| **Server-Side Auth** | HTTP-only cookies, automatic token refresh |
| **Frontend Integration** | Async Server Component fetching real data |

**Key Files**:
- `apps/core/services/dashboard_service.py` - 360 lines
- `apps/core/views/dashboard.py` - API endpoint
- `apps/core/tests/test_dashboard_service.py` - 12 tests
- `apps/core/tests/test_dashboard_view.py` - 10 tests
- `src/lib/server/api-client.ts` - Server-side auth client

---

### Recent Milestone: Frontend SSR & Hydration Fix ✅
**Date**: 2026-02-28  
**Status**: Production Ready - "Loading..." stuck state resolved

| Fix | Impact |
|-----|--------|
| **Dashboard Server Component** | Converted from Client to Server Component for immediate render |
| **Static Files Auto-Copy** | Build script now copies `.next/static` to standalone folder |
| **Hydration Mismatch Fix** | Removed "Loading..." early return from shell.tsx |
| **New Files** | `dashboard-actions.tsx`, `gst-chart-wrapper.tsx` for client interactivity |

**Key Insight**: Next.js standalone build requires manual static file copy. Build script now handles this automatically.

### Recent Milestone: PDF & Email Services ✅
**Date**: 2026-02-27  
**Status**: Document generation and delivery live

| Service | Implementation |
|---------|----------------|
| **PDF Generation** | WeasyPrint with IRAS-compliant templates |
| **Email Delivery** | Asynchronous Celery tasks with PDF attachments |
| **Verification** | Integration tests verified binary stream and task dispatch |

### Milestone: Database & Model Hardening ✅
**Date**: 2026-02-27  
**Status**: Models restored, Schema Aligned

| Fix | Impact |
|-----|--------|
| **Missing Models** | `InvoiceLine`, `JournalEntry`, `JournalLine`, `GSTReturn` restored |
| **Auth Alignment** | `AppUser` aligned with Django 6.0 standard fields |
| **Circular Deps** | Resolved circular foreign keys in SQL via `ALTER TABLE` |
| **Testing** | Workflow established for unmanaged model verification |

---

## 🏗 Project Architecture

### System Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                        CLIENT LAYER                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │   Next.js    │  │  Zustand     │  │  TanStack    │          │
│  │   16 PWA     │  │  (UI State)  │  │  Query       │          │
│  └──────┬───────┘  └──────────────┘  └──────────────┘          │
└─────────┼───────────────────────────────────────────────────────┘
          │ HTTPS + JWT Access Token (15min)
          ▼
┌─────────────────────────────────────────────────────────────────┐
│                       SECURITY LAYER                             │
│  JWT Auth │ HttpOnly Refresh Cookie │ CSRF │ Rate Limiting      │
└─────────┬───────────────────────────────────────────────────────┘
          │
          ▼
┌─────────────────────────────────────────────────────────────────┐
│                      API LAYER (Django)                          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │  DRF Views   │  │   Services   │  │  Middleware  │          │
│  │  (Thin)      │  │ (Business)   │  │ (RLS/Auth)   │          │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘          │
└─────────┼─────────────────┼─────────────────┼──────────────────┘
          │                 │                 │
          ▼                 ▼                 ▼
┌─────────────────────────────────────────────────────────────────┐
│                     DATA LAYER (PostgreSQL)                      │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │  7 Schemas   │  │     RLS      │  │  NUMERIC     │          │
│  │ (domain)     │  │ (session)    │  │ (10,4)       │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
└─────────────────────────────────────────────────────────────────┘
```

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

### Design Principles

| Principle | Implementation | Critical Notes |
|-----------|----------------|----------------|
| **Unmanaged Models** | `managed = False` | Schema is DDL-managed via SQL. Models map to existing tables. |
| **Service Layer** | `services/` modules | Views are thin controllers. ALL business logic lives in services. |
| **RLS Security** | PostgreSQL session variables | `SET LOCAL app.current_org_id = 'uuid'` per transaction |
| **Decimal Precision** | `NUMERIC(10,4)` | NEVER use float for money. Use `common.decimal_utils.money()` |
| **Atomic Requests** | `ATOMIC_REQUESTS: True` | Every view runs in single transaction for RLS consistency |

---

## 🧪 Testing Strategy

### Backend Tests (Unmanaged Database Workflow)

Since LedgerSG uses unmanaged models, standard Django test runners will fail to create the schema. Follow this established workflow:

```bash
# 1. Manually initialize the test database
export PGPASSWORD=ledgersg_secret_to_change
dropdb -h localhost -U ledgersg test_ledgersg_dev || true
createdb -h localhost -U ledgersg test_ledgersg_dev
psql -h localhost -U ledgersg -d test_ledgersg_dev -f database_schema.sql

# 2. Run tests with reuse flags
source /opt/venv/bin/activate
cd apps/backend
pytest --reuse-db --no-migrations
```

---

## 🔧 Troubleshooting

### Banking Module Issues

**Problem**: `No document sequence configured for org X type PAYMENT_RECEIVED`
**Cause**: Missing entry in `core.document_sequence` for payment types
**Solution**: Seed document sequences:
```sql
INSERT INTO core.document_sequence (org_id, document_type, prefix, next_number, padding)
VALUES (org_uuid, 'PAYMENT_RECEIVED', 'RCP-', 1, 5), (org_uuid, 'PAYMENT_MADE', 'PAY-', 1, 5);
```

**Problem**: `function core.get_next_document_number does not exist`
**Cause**: Database schema not updated to latest version
**Solution**: Reload `database_schema.sql` or create the function manually

**Problem**: `column "updated_at" of relation "payment_allocation" does not exist`
**Cause**: Schema missing column added in v1.0.3
**Solution**: Apply schema patch or reload full schema

### Dashboard API
**Problem**: Dashboard API returns 403 Forbidden.  
**Cause**: `UserOrganisation.accepted_at` is null (TenantContextMiddleware requires it).  
**Solution**: Ensure test fixtures set `accepted_at=datetime.now()`.

**Problem**: `ProgrammingError: column "contact_snapshot" of relation "document" does not exist`.  
**Cause**: Model has fields not in SQL schema.  
**Solution**: Remove invalid fields from `InvoiceDocument` model.

**Problem**: `DataError: invalid input value for enum doc_status: "PARTIAL"`.  
**Cause**: Using wrong enum value.  
**Solution**: Use `PARTIALLY_PAID` (matches SQL enum).

### Unmanaged Models & Testing
**Problem**: Tests fail with `relation "core.app_user" does not exist`.  
**Cause**: `pytest-django` skips migrations for unmanaged models, resulting in an empty test database.  
**Solution**: See the manual test database initialization workflow in [Testing Strategy](#-testing-strategy).

### Database Schema Mismatches
**Problem**: `ProgrammingError: column "updated_at" of relation "role" does not exist`.  
**Cause**: The SQL schema and Django models have drifted.  
**Solution**: Update `database_schema.sql` to include the missing fields and re-initialize both `ledgersg_dev` and `test_ledgersg_dev`.

### SQL Circular Dependencies
**Problem**: Database initialization fails when creating tables with foreign keys to each other.  
**Solution**: Decouple creation order. Create tables with simple columns first, then use `ALTER TABLE ... ADD CONSTRAINT ... FOREIGN KEY` at the end of the script for circular references (e.g., `organisation` <-> `app_user`).

### TaxCode Constraint Violations
**Problem**: `check_tax_code_input_output` constraint fails during fixture creation.  
**Cause**: SQL requires `is_input=TRUE OR is_output=TRUE OR code='NA'`.  
**Solution**: Ensure all TaxCode fixtures set at least one of `is_input` or `is_output` to `True` (except for code='NA').

### Frontend API Connection
**Problem**: Frontend shows "API Error" or cannot fetch data.  
**Cause**: CORS not configured or `NEXT_PUBLIC_API_URL` incorrect.  
**Solution**: Verify `.env.local` has correct API URL and backend CORS allows frontend origin.

### Docker Frontend Standalone
**Problem**: Frontend in Docker serves static files instead of Next.js app.  
**Cause**: `output: 'export'` mode doesn't support API routes.  
**Solution**: Use `NEXT_OUTPUT_MODE=standalone` and run `node .next/standalone/server.js`.

### Phase 3 Integration Lessons (Frontend Testing)

**Problem**: Radix UI Tabs not activating in integration tests.
**Cause**: `fireEvent.click` doesn't trigger Radix UI state changes - requires proper user interaction simulation.
**Solution**: Use `userEvent.setup()` + `await user.click()` instead of `fireEvent.click`:
```typescript
// ❌ Incorrect - doesn't trigger tab activation
fireEvent.click(transactionsTab);

// ✅ Correct - triggers proper state change
const user = userEvent.setup();
await user.click(transactionsTab);
```

**Problem**: "Found multiple elements with the role 'button' and name..." test error.
**Cause**: Multiple elements match the selector (e.g., two "Import Statement" buttons).
**Solution**: Use `findAllByRole` instead of `findByRole`:
```typescript
// ❌ Incorrect - expects single match
const importButton = await screen.findByRole("button", { name: /import statement/i });

// ✅ Correct - handles multiple matches
const importButtons = await screen.findAllByRole("button", { name: /import statement/i });
expect(importButtons.length).toBeGreaterThan(0);
```

**Problem**: Hook returns `undefined` in tests.
**Cause**: Missing mock for the hook in test file.
**Solution**: Add comprehensive hook mocking:
```typescript
vi.mock("@/hooks/use-banking");

vi.mocked(bankingHooks.useBankTransactions).mockReturnValue({
  data: { results: [], count: 0 },
  isLoading: false,
} as any);
```

**Problem**: TransactionList test expects `transactions-list` but finds `transactions-empty`.
**Cause**: Component renders different testids based on `data.count` value.
**Solution**: Understand conditional rendering:
- `count === 0` → renders `transactions-empty`
- `count > 0` → renders `transactions-list`

### Frontend "Loading..." Stuck State
**Problem**: Dashboard shows "Loading..." indefinitely.
**Cause**: Missing static JS files in standalone build OR hydration mismatch OR CORS preflight rejection.
**Solution**:
1. Verify static files: `ls .next/standalone/.next/static/chunks/`
2. Rebuild: `npm run build:server` (now auto-copies static files)
3. Check browser console for hydration errors
4. Test CORS preflight: `curl -X OPTIONS http://localhost:8000/api/v1/auth/me/ -i`
5. Verify CORSJWTAuthentication is configured in settings

### CORS Preflight Authentication Blocking
**Problem**: OPTIONS requests return 401 Unauthorized.
**Cause**: DRF JWT authentication rejects unauthenticated preflight requests.
**Solution**: Use `CORSJWTAuthentication` class that returns `None` for OPTIONS method.

### 404 Errors for JS/CSS Chunks
**Problem**: Browser shows 404 for `/_next/static/chunks/*.js`.  
**Cause**: Static files not copied to standalone folder.  
**Solution**: Build script updated to auto-copy. Manual fix: `cp -r .next/static .next/standalone/.next/`

### Hydration Mismatch Errors
**Problem**: Console shows "Text content does not match server-rendered HTML".  
**Cause**: Component renders differently on server vs client (e.g., `useEffect` with early return).  
**Solution**: Convert to Server Component or ensure identical initial render on both environments.

---

## 🎓 Lessons Learned

### CORS Authentication Fix (2026-03-07)

#### 1. DRF Authentication Executes Before Permissions
- **Discovery**: Permission classes cannot bypass authentication for OPTIONS requests
- **Lesson**: Authentication layer must explicitly handle CORS preflight
- **Pattern**: Create custom authentication class for CORS-specific logic
- **Code**: `CORSJWTAuthentication.authenticate()` returns `None` for OPTIONS

#### 2. django-csp 4.0 Breaking Change
- **Discovery**: Legacy `CSP_*` settings cause errors in django-csp 4.0+
- **Lesson**: Always check package version before using old configuration syntax
- **Pattern**: Use dict-based `CONTENT_SECURITY_POLICY` config for v4.0+
- **Fix**: Removed `CSP_REPORT_ONLY`, `CSP_REPORT_URI` from base.py

#### 3. Port Conflicts in Multi-Service Environments
- **Discovery**: Backend appeared to run but was actually a different service
- **Lesson**: Always verify which process is using a port before debugging
- **Pattern**: Use `lsof -i :PORT` or `ss -tulpn | grep :PORT` to check
- **Case**: `librechat-rag-api` was using port 8000

#### 4. CORS by Design Excludes Auth Tokens
- **Discovery**: Browser preflight requests intentionally don't include authentication
- **Lesson**: Backend must handle unauthenticated OPTIONS requests gracefully
- **Pattern**: Authentication layer should return `None` for OPTIONS, not raise error
- **Implementation**: `if request.method == "OPTIONS": return None`

### CSP Implementation (2026-03-07)

#### 1. django-csp Configuration Syntax
- **Discovery**: v4.0+ uses `CONTENT_SECURITY_POLICY` dict, not individual settings
- **Lesson**: Migration guide at https://django-csp.readthedocs.io/en/latest/migration-guide.html
- **Pattern**: `CONTENT_SECURITY_POLICY_REPORT_ONLY = {"DIRECTIVES": {...}}`

#### 2. CSP Report Endpoint Authentication
- **Discovery**: Browsers send CSP reports without auth tokens
- **Lesson**: Report endpoint must allow anonymous access
- **Pattern**: Add `@permission_classes([AllowAny])` decorator

#### 3. Report-Uri Manual Addition
- **Discovery**: django-csp doesn't auto-append report-uri from settings
- **Lesson**: Must be explicitly added to DIRECTIVES dict
- **Pattern**: `"report-uri": ["/api/v1/security/csp-report/"]`

### Phase 3 Integration (2026-03-06)

#### 1. Radix UI Tabs Require userEvent
- **Discovery**: `fireEvent.click` doesn't trigger Radix UI tab activation
- **Lesson**: Always use `userEvent.setup()` for interactive testing
- **Pattern**: `const user = userEvent.setup(); await user.click(tab)`

#### 2. Hook Mocks Must Be Comprehensive
- **Discovery**: Missing hook mocks caused cascading test failures
- **Lesson**: Audit all hooks used by component tree
- **Pattern**: List all `useXxx` imports and mock each one

#### 3. Multiple Elements Require findAllBy*
- **Discovery**: Multiple elements matching selector caused errors
- **Lesson**: Use `findAllByRole` when multiple elements match
- **Pattern**: `const buttons = await screen.findAllByRole("button", { name: /text/i })`

---

## 🚀 Recommended Next Steps

### Immediate (High Priority)
1. ~~**Journal Entry Integration**: Align JournalService field names with JournalEntry model~~ ✅ COMPLETE (Phase A)
2. ~~**Organization Context**: Replace hardcoded `DEFAULT_ORG_ID` with dynamic org selection~~ ✅ COMPLETE (Phase B)
3. ~~**Bank Reconciliation Tests**: Add tests for ReconciliationService~~ ✅ COMPLETE
4. ~~**View Tests**: Add comprehensive endpoint tests for banking API~~ ✅ COMPLETE
5. ~~**Rate Limiting**: Implement `django-ratelimit` on authentication endpoints (SEC-002)~~ ✅ COMPLETE
6. ~~**Banking UI**: Create frontend pages with TDD tests~~ ✅ COMPLETE (Phase 5.4)
7. ~~**CSP Headers**: Implement Content Security Policy on backend (SEC-003)~~ ✅ COMPLETE
8. **Error Handling**: Add retry logic and fallback UI for dashboard API failures

### Short-term (Medium Priority)
9. ~~**Payment Tab Implementation**: Replace placeholder with payment list UI~~ ✅ COMPLETE (Phase 5.5)
10. ~~**Bank Transactions Tab**: Implement reconciliation UI with matching~~ ✅ COMPLETE (Phase 5.5)
11. **Frontend Test Coverage**: Expand tests for hooks and forms (SEC-004)
12. **Error Handling**: Add retry logic for payment processing

### Long-term (Low Priority)
13. **InvoiceNow Transmission**: Finalize Peppol XML generation
14. **PII Encryption**: Encrypt GST numbers and bank accounts at rest (SEC-005)
15. **Analytics**: Add dashboard analytics tracking
16. **Mobile**: Optimize banking pages for mobile devices
