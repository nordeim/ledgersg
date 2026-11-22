LedgerSG Project Status — Comprehensive Summary
Executive Overview
LedgerSG is a production-grade, double-entry accounting platform purpose-built for Singapore SMBs with IRAS 2026 compliance. The platform has undergone significant development across multiple phases, achieving enterprise-grade security, comprehensive test coverage, and a complete banking UI.
---
Current Status (2026-03-08)
Production Metrics
Component
Frontend
Backend
Database
Dashboard
Banking UI
Security
Testing
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
- Next.js 16.1.6 (App Router) + React 19.2
- Tailwind CSS 4.0 + Shadcn/Radix UI
- Zustand (UI State) + TanStack Query (Server State)
- Hybrid rendering: Server Components for data fetching, Client Components for interactivity
Backend Stack
- Django 6.0.2 + Django REST Framework 3.16.1
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
├── backend/           # Django 6.0.2
│   ├── apps/          # core, coa, gst, journal, invoicing, banking, reporting
│   ├── common/        # BaseModel, TenantModel, decimal_utils
│   ├── config/        # settings, celery, urls
│   └── tests/         # integration, security, TDD
│
└── web/               # Next.js 16.1.6
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
- **Frontend:** v0.1.1 (Next.js 16.1.6, 12 pages, 22 test files, **305 tests passing**)
- **Backend:** v0.3.3 (Django 6.0.2, 83 API endpoints, 16 test files, **233+ tests passing**)
- **Database:** v1.0.3 (PostgreSQL 16+, 7 schemas, 28 tables, RLS enforced)
- **Dashboard:** v1.0.0 (Real Data Integration, 36 TDD tests, 100% coverage)
- **Integration Gaps:** Phase 3 Complete (GAP-3: 20 tests, GAP-4: 13 tests)
- **Banking UI:** Phase 5.5 Complete (73 TDD tests, all tabs live)
- **Security Score:** 98% (Audit Verified, All Issues Remediated)

As an autonomous coding agent, your objective is to maintain this high standard of architectural maturity while executing Pull Requests (PRs). You must operate under the **Meticulous Approach**: Analyze → Plan → Validate → Implement → Verify → Deliver. Surface-level assumptions are prohibited; every change must be grounded in deep technical reasoning.

---

## 2. System Architecture & Technology Stack

The project utilizes a decoupled, service-oriented architecture designed for security, scalability, and regulatory compliance.

### 2.1 Frontend Architecture
- **Framework:** Next.js 16.1.6 (App Router) with React 19.2.
- **Styling:** Tailwind CSS 4.0 + Shadcn/Radix UI primitives.
- **State Management:** Zustand (UI State) + TanStack Query (Server State).
- **Rendering Strategy:** Hybrid. Critical data paths use **Server Components** to ensure zero JWT exposure to client-side JavaScript. Interactive elements (charts, forms) are isolated Client Components.
- **Build Modes:**
  - `standalone`: For production API integration (`npm run build:server`).
  - `export`: For static CDN deployment (`npm run build`).
- **Design Philosophy:** "Illuminated Carbon" Neo-Brutalist. Reject generic templates. Use whitespace as a structural element. Ensure WCAG AAA compliance.

### 2.2 Backend Architecture
- **Framework:** Django 6.0.2 with Django REST Framework (DRF) 3.16.1.
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
