# LedgerSG — Project Architecture Document (PAD)

> **Single Source of Truth for Developers and Coding Agents**
> **Version**: 3.4.0
> **Last Updated**: 2026-11-21
> **P7 note**: API truth & permission hardening — status-transition authorization, routed fiscal endpoints, fail-closed payments, real error messages, working void/send actions; see `docs/REMEDIATION_2026-11-22_P7_REPORT.md`.
> **P5 note**: truth restoration sprint — real InvoiceNow transmission wiring, `amount_paid`/void-reversal accounting integrity, fail-closed control accounts, real dashboard alerts + cache invalidation, repo hygiene; test metrics below reflect the P5 verified counts.
> **Status**: Production Ready ✅
> **Security Score**: 100% (SEC-001/002/003 Remediated)
> **Compliance**: IRAS 2026 (GST F5, InvoiceNow, BCRS)

---

## 📋 Table of Contents

1. [Executive Summary](#executive-summary)
2. [Architectural Principles](#architectural-principles)
3. [System Architecture](#system-architecture)
4. [File Hierarchy & Key Files](#file-hierarchy--key-files)
5. [Frontend Architecture](#frontend-architecture)
6. [Backend Architecture](#backend-architecture)
7. [Database Architecture](#database-architecture)
8. [Security Architecture](#security-architecture)
9. [Developer Handbook](#developer-handbook)
10. [Troubleshooting](#troubleshooting)

---

## Executive Summary

**LedgerSG** is a production-grade, double-entry accounting platform purpose-built for Singapore SMBs. It eliminates the complexity of IRAS compliance through a "SQL-First" design philosophy and a distinctive "Illuminated Carbon" neo-brutalist UI.

### Key Metrics
| Metric | Value | Details |
|--------|-------|---------|
| **Test Coverage** | **1,043 Tests Passing** | 624 Backend + 398 Frontend unit + 21 e2e (9 always + 12 backend-gated) |
| **API Surface** | **95 Endpoints** | RESTful, JSON-API compliant |
| **Security** | **100% Score** | CSP, Rate Limiting, RLS, 4-Layer Auth |
| **Database** | **7 Schemas** | 30 Tables, Row-Level Security Enforced |
| **Performance** | **<100ms** | P95 Response Time (Redis Caching Active) |

### Test Breakdown
| Suite | Tests | Pass Rate | Framework | Status |
|-------|-------|-----------|-----------|--------|
| **Frontend Unit** | 398 | 100% | Vitest + RTL | ✅ Passing |
| **Backend (pytest)** | 624 passed / 5 skipped | 100% of run | pytest | ✅ Passing |
| **E2E (Playwright)** | 21 (9 always + 12 backend-gated) | 100% | Playwright | ✅ Passing |
| **Total Passing** | **1,043** | — | Mixed | ✅ Verified |

---

## Architectural Principles

These mandates are non-negotiable. They define the "Soul" of the system.

### 1. SQL-First & Unmanaged Models
*   **The Rule**: The `database_schema.sql` file is the **absolute source of truth**.
*   **The Mechanism**: All Django models are `managed = False`.
*   **The Prohibition**: NEVER run `makemigrations`. Schema changes are manual SQL patches.
*   **Why?**: Ensures strict data integrity, optimal indexing, and prevents ORM-induced performance degradation.

### 2. Service Layer Supremacy
*   **The Rule**: Views are thin controllers; Logic lives in `services/`.
*   **The Pattern**: 
    *   **View**: Deserializes input -> Calls Service -> Serializes output.
    *   **Service**: Validates business rules -> Executes DB atomic transaction -> Returns Domain Object.
*   **Why?**: Decouples business logic from the HTTP transport layer, enabling easy testing and CLI usage.

### 3. Financial Precision
*   **The Rule**: `NUMERIC(19,4)` for everything (schema v1.1.0 — widened from the original 10,4 so ≥ S$1M amounts, above the GST registration threshold, cannot overflow).
*   **The Prohibition**: **NO FLOATS.** All Python math must use `common.decimal_utils.money()`.
*   **Why?**: Floating point errors are unacceptable in accounting.

### 4. Defense-in-Depth Security
* **The Rule**: Security at every layer.
* **Layers**:
1. **Frontend**: AuthProvider Redirects.
2. **Network**: CSP Headers & Rate Limiting.
3. **Application**: JWT Validation.
4. **Database**: Row-Level Security (RLS) policies.

### 5. Zero JWT Exposure
* **The Rule**: Browser JavaScript must NEVER have access to JWT tokens.
* **Implementation** (P4-verified):
  * Access token held in **api-client module memory only** — never localStorage/sessionStorage — and attached as `Authorization: Bearer <token>`
  * Refresh token set by the backend as an **HttpOnly cookie** (`Path=/api/v1/auth/`, SameSite=Lax, Secure=!DEBUG) — login/register set it, refresh rotates it (with blacklist), logout/change-password expire it
  * A non-secret, JS-readable `session_hint` marker cookie gates client refresh attempts; the refresh token itself is never touched by JavaScript
* **Why?**: Prevents XSS attacks from stealing authentication tokens.

### 6. Multi-Tenancy via RLS
* **The Rule**: Every request must set PostgreSQL session variables.
* **Implementation**: `TenantContextMiddleware` executes:
```sql
SET LOCAL app.current_org_id = '<org_uuid>';
SET LOCAL app.current_user_id = '<user_uuid>';
```
* **Why?**: All queries automatically filtered to current organisation, preventing cross-tenant data access.

### 7. TDD Culture
* **The Rule**: All new features follow RED → GREEN → REFACTOR.
* **Process**:
1. **RED**: Write failing test first
2. **GREEN**: Implement minimal code to pass test
3. **REFACTOR**: Optimize code while keeping tests green
* **Why?**: Ensures comprehensive test coverage, prevents regressions, and documents expected behavior.

---

## System Architecture

```mermaid
flowchart TB
    subgraph Client ["Client Layer (Next.js 16)"]
        UI[React 19 UI]
        Zustand[Zustand Store]
        Query[TanStack Query]
        NextServer[Next.js Server Components]
    end

    subgraph Security ["Security Perimeter"]
        CSP[CSP Headers]
        RL[Rate Limiting]
        WAF[WAF / Proxy]
    end

    subgraph Backend ["Backend Layer (Django 6)"]
        DRF[DRF Views]
        Auth[JWT Auth]
        Service[Service Layer]
        Celery[Celery Workers]
    end

    subgraph Data ["Data Layer (PostgreSQL 16)"]
        Schemas[(7 Domain Schemas)]
        RLS[Row-Level Security]
        Redis[Redis Cache]
    end

    UI -->|Interactivity| Zustand
    UI -->|Data Fetch| Query
    Query -->|API Calls| NextServer
    NextServer -->|HTTPS + JWT| WAF
    WAF --> RL
    RL --> DRF
    DRF -->|Auth| Auth
    DRF -->|Logic| Service
    Service -->|Async| Celery
    Service -->|SQL| Schemas
    Schemas -->|Enforce| RLS
    Service -->|Cache| Redis
    Celery -->|Write| Schemas

    style Client fill:#1a1a1a,stroke:#00E585,stroke-width:2px,color:#fff
    style Backend fill:#1a1a1a,stroke:#3b82f6,stroke-width:2px,color:#fff
    style Data fill:#1a1a1a,stroke:#f59e0b,stroke-width:2px,color:#fff
```

---

## File Hierarchy & Key Files

```text
/home/project/Ledger-SG/
├── apps/
│   ├── backend/                  # Django 6.0.2 Project
│   │   ├── apps/                 # Domain Modules
│   │   │   ├── banking/          # Bank Accounts, Payments, Recon
│   │   │   ├── coa/              # Chart of Accounts
│   │   │   ├── core/             # Org, User, Auth, RLS Middleware
│   │   │   ├── gst/              # Tax Codes, F5 Returns
│   │   │   ├── invoicing/        # Invoices, Credit Notes
│   │   │   ├── journal/          # General Ledger (Double Entry)
│   │   │   ├── peppol/           # InvoiceNow Integration
│   │   │   └── reporting/        # Dashboard & Financial Reports
│   │   ├── common/               # Shared Utilities (Money, Base Models)
│   │   │   ├── middleware/       # CRITICAL: tenant_context.py
│   │   │   └── decimal_utils.py  # CRITICAL: money() function
│   │   ├── config/               # Settings (Base, Dev, Prod)
│   │   ├── database_schema.sql   # ★ SOURCE OF TRUTH ★
│   │   └── manage.py
│   └── web/                      # Next.js 16.1.6 Project
│       ├── src/
│       │   ├── app/              # App Router (Pages & Layouts)
│       │   ├── components/       # Shadcn/Radix UI Components
│       │   ├── hooks/            # Custom React Hooks
│ │ ├── lib/ # Utilities
│ │ │ ├── api-client.ts # Typed API Client (client-side)
│ │ │ ├── gst-engine.ts # GST calculation engine
│ │ │ ├── utils.ts # Utility functions
│ │ │ └── server/ # Server-side utilities
│ │ │ └── api-client.ts # Server-side API Client (zero JWT exposure)
│ │ ├── providers/ # Context Providers (Auth, Theme)
│       │   └── shared/           # Zod Schemas & Types
│       ├── public/
│       ├── next.config.ts
│       └── middleware.ts         # CSP & Security Headers
├── docker/                       # Container Configuration
├── docs/                         # Documentation
├── ACCOMPLISHMENTS.md            # Progress Tracker
├── AGENT_BRIEF.md                # Developer Guidelines
└── GEMINI.md                     # AI Persona & Mandates
```

---

## Frontend Architecture

**Stack**: Next.js 16.1.6 (App Router), React 19, Tailwind 4, Shadcn/Radix UI.

### Authentication Flow
1.  **Initial Load**: `AuthProvider` calls `/api/v1/auth/me/`.
    *   Success: Sets `user` and `organisations` context.
    *   Failure (401): Redirects to `/login`.
2.  **Protected Routes**: `DashboardLayout` checks `isAuthenticated`.
    *   False: Returns `null` (prevents flash) and redirects.
3.  **API Requests**: `api-client.ts` handles JWT.
    *   Attaches `Authorization: Bearer <token>` (module memory).
    *   On 401 **with session evidence** (in-memory token or the `session_hint` marker cookie): attempts silent refresh through the HttpOnly refresh cookie (`/api/v1/auth/refresh/` via `credentials: "include"`) and retries the original request — this is what makes sessions survive full page reloads (P4/E-1).
    *   On an anonymous 401 (no evidence — e.g. bad login credentials): propagates the error to the caller untouched.
    *   On Refresh Fail: Logs out and redirects.

### Data Fetching Strategy
*   **Server Components**: Fetch initial data.
*   **Client Components**: Use **TanStack Query v5** for dynamic data and mutations.
    *   **Pattern**: `useQuery({ queryKey: ['entity', orgId], queryFn: ... })`.
    *   **Mutations**: Use `isPending` (not `isLoading`) for loading state.

### Page Data Truth (P6/C-5 — all pages render real backend data)
Every dashboard page is wired to the real API — mock fixtures are deleted:
*   **Invoices list** (P5): `useInvoices` → `{results, count}` list contract.
*   **Invoice detail** (P6): `useInvoice` → detail serializer incl. `amount_paid`/`amount_due` (F-11); approve/void/send mutations; `await params` in the page component (route params are a Promise in this Next.js version).
*   **General ledger** (P6): `useLedger` → the flat line-level `journal-entries/ledger/` endpoint (one row per journal line; the aggregated entries list cannot drive a line-level table).
*   **Settings** (P6): `useOrganisation` → org detail + allowlisted PATCH updates + GST register/deregister (the GST endpoints seed the GST control accounts).
*   **Invoice actions** (P7): the detail page exposes Approve / Void (REQUIRED-reason dialog) / Send email / Send via InvoiceNow (with live status badge) / PDF download / Print; error toasts surface the backend's real messages (`{error:{message}}` envelope parsed by the api-client).

---

## Backend Architecture

**Stack**: Django 6.0.2, DRF 3.16, Celery 5.6, Redis 6.4.

### Middleware Chain (Request Lifecycle)
The order is critical for security and RLS.

1.  `SecurityMiddleware`: Basic security headers.
2.  `CSPMiddleware`: Enforces Content Security Policy (SEC-003).
3.  `SessionMiddleware` / `CommonMiddleware`: Standard Django.
4.  `CorsMiddleware`: Handles Cross-Origin requests.
5.  `AuthenticationMiddleware`: DRF JWT Auth (Sets `request.user`).
    *   *Note*: `CORSJWTAuthentication` skips auth for `OPTIONS` requests.
6.  **`TenantContextMiddleware` (CRITICAL)**:
    *   Extracts `org_id` from URL.
    *   Verifies `UserOrganisation` membership.
    *   **Opens the request transaction itself** (C-03 remediation, 2026-11-21): `SET LOCAL` is transaction-scoped and Django's `make_view_atomic` opens the view transaction strictly INSIDE the view, so the middleware wraps `get_response()` in `transaction.atomic()` after setting:
        ```python
        with transaction.atomic():
            with connection.cursor() as cursor:
                cursor.execute("SET LOCAL app.current_org_id = %s", [str(org_id)])
                cursor.execute("SET LOCAL app.current_user_id = %s", [str(user_id)])
            response = self.get_response(request)  # same transaction
        ```
    *   Sets `''` (empty string) for unauthenticated requests (fail-closed) in the same transactional pattern.
    *   `AuditContextMiddleware` follows the same pattern for `app.client_ip/user_agent/request_path`.

### Service Layer Pattern
**Location**: `apps/<module>/services.py`

```python
# Example: Creating an Invoice
class InvoiceService:
    @staticmethod
    def create_invoice(org_id: UUID, data: dict) -> InvoiceDocument:
        # 1. Validation & Data Prep (Use money()!)
        total_excl = money(data['total_excl'])
        
        with transaction.atomic():
            # 2. DB Operation
            invoice = InvoiceDocument.objects.create(...)
            
            # 3. Cross-Domain Logic (Journal Posting)
            JournalService.post_invoice(org_id, invoice)
            
        return invoice
```

---

## Database Architecture

**Engine**: PostgreSQL 16+.

### Schemas
| Schema | Purpose | Key Tables | Table Count |
|--------|---------|------------|-------------|
| `core` | Multi-tenancy, users, roles | `organisation`, `app_user`, `user_organisation`, `fiscal_year`, `fiscal_period`, `document_sequence`, `currency`, `exchange_rate`, `organisation_setting`, `role` | 10 |
| `coa` | Chart of Accounts | `account`, `account_type`, `account_sub_type` | 3 |
| `gst` | GST compliance, tax codes, F5 returns | `tax_code`, `gst_return`, `threshold_snapshot`, `peppol_transmission_log`, `contact` | 5 |
| `journal` | General Ledger (immutable) | `entry`, `line` | 2 |
| `invoicing` | Sales/purchases, contacts | `document`, `document_line`, `document_attachment` | 3 |
| `banking` | Cash management | `bank_account`, `payment`, `payment_allocation`, `bank_transaction` | 4 |
| `audit` | Immutable audit trail | `event_log`, `org_event_log` (view) | 2 |
| **Total** | | | **30 tables** |

### RLS Policies
Every table (30 total) has RLS enabled. Policies look like this:

```sql
CREATE POLICY tenant_isolation ON invoicing.document
    USING (org_id = core.current_org_id());
```

### GST F5 Box Model (IRAS convention — matches `gst.return` CHECK constraints)

| Box | Meaning | Source |
|-----|---------|--------|
| 1 | Standard-rated supplies (net) | `tax_code.f5_supply_box = 1` on sales lines |
| 2 | Zero-rated supplies | `f5_supply_box = 2` |
| 3 | Exempt supplies | `f5_supply_box = 3` |
| 4 | Total supplies = 1+2+3 | derived (`chk_box4_total`) |
| 5 | Total taxable purchases | `f5_purchase_box = 5` on purchase lines |
| 6 | Output tax due | `f5_tax_box = 6` |
| 7 | Input tax claimed | `f5_tax_box = 7` AND `is_claimable` |
| 8 | Net GST = 6 − 7 | derived (`chk_box8_net`) |
| 13 | Total revenue | = Box 4 |
| 14 | Reverse charge supplies | `is_reverse_charge` |

---

## Security Architecture

*   **100% Security Score** achieved via:
    *   **SEC-001**: Full validation of Banking endpoints.
    *   **SEC-002**: `django-ratelimit` on all Auth endpoints (Login: 10/min).
    *   **SEC-003**: Strict CSP (`default-src 'none'`, `script-src 'self'`).
*   **CORS**: Custom `CORSJWTAuthentication` allows unauthenticated Preflight (`OPTIONS`) but strictly enforces JWT for all others.

---

## Developer Handbook

### 1. Environment Setup

**Backend**:
```bash
cd apps/backend
python -m venv venv
source venv/bin/activate
pip install -e ".[dev]"
# Initialize DB (Manual!)
export PGPASSWORD=ledgersg_secret_to_change
dropdb -h localhost -U ledgersg ledgersg_dev || true
createdb -h localhost -U ledgersg ledgersg_dev
psql -h localhost -U ledgersg -d ledgersg_dev -f database_schema.sql
python manage.py runserver
```

**Frontend**:
```bash
cd apps/web
npm install
npm run dev
```

### 2. Testing (The "Meticulous" Way)
Backend tests **MUST** use the following command to avoid migration errors:

```bash
# Initialize Test DB first!
dropdb -h localhost -U ledgersg test_ledgersg_dev
createdb -h localhost -U ledgersg test_ledgersg_dev
psql -h localhost -U ledgersg -d test_ledgersg_dev -f database_schema.sql

# Run Tests
pytest --reuse-db --no-migrations

# Expected Output:
# ============================= 624 passed, 0 failed, 5 skipped =============================
# (P1 fixed the 26 documented fixture failures; the suite has been fully green since)
```

**Frontend Tests**: `npm test` (Vitest).

```bash
# Run frontend tests
cd apps/web
npm test

# Expected Output:
# Test Files: 37 passed (37)
# Tests: 398 passed (398)
# Duration: ~60s
```

---

## Performance Metrics

### Cache Performance (Redis)
| Metric | Value | Notes |
|--------|-------|-------|
| Cache Hit Rate | 95%+ | Dashboard metrics cached 5 min |
| Avg Response Time | <50ms | Cached endpoints |
| P95 Response Time | <100ms | All endpoints |

### Database Performance
| Metric | Value | Notes |
|--------|-------|-------|
| Avg Query Time | <20ms | Optimized indexes |
| Connection Pool | 20 connections | pgBouncer in production |
| RLS Overhead | <5ms | Session variable setting |

### API Response Times
| Endpoint Type | Avg Time | P95 Time |
|---------------|----------|----------|
| Auth endpoints | 50ms | 100ms |
| List endpoints | 80ms | 150ms |
| Detail endpoints | 30ms | 60ms |
| Mutation endpoints | 100ms | 200ms |

---

## Troubleshooting

### "Relation does not exist" in Tests
* **Cause**: You didn't initialize the test database with SQL. `pytest-django` cannot create tables for `managed=False` models.
* **Fix**: Run the `psql ... -f database_schema.sql` command against `test_ledgersg_dev`.

### "UUID object has no attribute 'replace'" (500 Error)
* **Cause**: Django URL dispatcher already converted the ID to a UUID object.
* **Fix**: Remove `UUID(org_id)` from your view. Use `org_id` directly.

### Dashboard Stuck on "Loading..."
* **Cause**: CORS Preflight failure.
* **Fix**: Ensure `CORSJWTAuthentication` is in `DEFAULT_AUTHENTICATION_CLASSES` and `CorsMiddleware` is before `CommonMiddleware`.

### "Permission Denied" (403) despite valid token
* **Cause**: The RLS context isn't set.
* **Fix**: Ensure `TenantContextMiddleware` is active and the user has an accepted `UserOrganisation` record.

### "pytest_plugins in non-root conftest" (Collection Error)
* **Cause**: `pytest_plugins` defined in non-top-level conftest file.
* **Fix**: Remove `pytest_plugins` from `apps/peppol/tests/conftest.py`. Use pytest's automatic conftest inheritance instead.

---

**End of Document**
