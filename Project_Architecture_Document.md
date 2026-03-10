# LedgerSG — Project Architecture Document (PAD)

> **Single Source of Truth for Developers and Coding Agents**  
> **Version**: 2.3.0  
> **Last Updated**: 2026-03-10  
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
| **Test Coverage** | **789 Tests** | 321 Frontend + 468 Backend (100% Pass Rate) |
| **API Surface** | **84 Endpoints** | RESTful, JSON-API compliant |
| **Security** | **100% Score** | CSP, Rate Limiting, RLS, 3-Layer Auth |
| **Database** | **7 Schemas** | 29 Tables, Row-Level Security Enforced |
| **Performance** | **<100ms** | P95 Response Time (Redis Caching Active) |

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
*   **The Rule**: `NUMERIC(10,4)` for everything.
*   **The Prohibition**: **NO FLOATS.** All Python math must use `common.decimal_utils.money()`.
*   **Why?**: Floating point errors are unacceptable in accounting.

### 4. Defense-in-Depth Security
*   **The Rule**: Security at every layer.
*   **Layers**:
    1.  **Frontend**: AuthProvider Redirects.
    2.  **Network**: CSP Headers & Rate Limiting.
    3.  **Application**: JWT Validation.
    4.  **Database**: Row-Level Security (RLS) policies.

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
│       │   ├── lib/              # Utilities
│       │   │   └── api-client.ts # Typed API Client
│       │   ├── providers/        # Context Providers (Auth, Theme)
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
    *   Attaches `Authorization: Bearer <token>`.
    *   On 401: Attempts silent refresh via HttpOnly cookie (`/api/v1/auth/refresh/`).
    *   On Refresh Fail: Logs out and redirects.

### Data Fetching Strategy
*   **Server Components**: Fetch initial data.
*   **Client Components**: Use **TanStack Query v5** for dynamic data and mutations.
    *   **Pattern**: `useQuery({ queryKey: ['entity', orgId], queryFn: ... })`.
    *   **Mutations**: Use `isPending` (not `isLoading`) for loading state.

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
    *   **Sets PostgreSQL RLS Variables**:
        ```python
        cursor.execute("SET LOCAL app.current_org_id = %s", [str(org_id)])
        cursor.execute("SET LOCAL app.current_user_id = %s", [str(user_id)])
        ```
    *   Sets `''` (empty string) for unauthenticated requests to ensure safe RLS denial.

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
| Schema | Purpose | Key Tables |
|--------|---------|------------|
| `core` | Multi-tenancy | `organisation`, `app_user`, `user_organisation` |
| `coa` | Accounting | `account`, `account_type` |
| `journal`| General Ledger | `journal_entry`, `journal_line` (Immutable) |
| `invoicing`| Sales/Purchases | `document`, `line_item`, `contact` |
| `banking` | Cash Mgmt | `bank_account`, `payment`, `bank_transaction` |
| `gst` | Compliance | `tax_code`, `gst_return` |
| `audit` | Security | `event_log` (Append-Only) |

### RLS Policies
Every table (29 total) has RLS enabled. Policies look like this:

```sql
CREATE POLICY tenant_isolation ON invoicing.document
    USING (org_id = core.current_org_id());
```

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
```

**Frontend Tests**: `npm test` (Vitest).

---

## Troubleshooting

### "Relation does not exist" in Tests
*   **Cause**: You didn't initialize the test database with SQL. `pytest-django` cannot create tables for `managed=False` models.
*   **Fix**: Run the `psql ... -f database_schema.sql` command against `test_ledgersg_dev`.

### "UUID object has no attribute 'replace'" (500 Error)
*   **Cause**: Django URL dispatcher already converted the ID to a UUID object.
*   **Fix**: Remove `UUID(org_id)` from your view. Use `org_id` directly.

### Dashboard Stuck on "Loading..."
*   **Cause**: CORS Preflight failure.
*   **Fix**: Ensure `CORSJWTAuthentication` is in `DEFAULT_AUTHENTICATION_CLASSES` and `CorsMiddleware` is before `CommonMiddleware`.

### "Permission Denied" (403) despite valid token
*   **Cause**: The RLS context isn't set.
*   **Fix**: Ensure `TenantContextMiddleware` is active and the user has an accepted `UserOrganisation` record.

---

**End of Document**
