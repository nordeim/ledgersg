# LedgerSG — Instructional Context

LedgerSG is an exceptionally well-architected, production-grade double-entry accounting platform purpose-built for Singapore SMBs. It transforms IRAS 2026 compliance into a seamless, automated experience while delivering a distinctive "Illuminated Carbon" neo-brutalist user interface.

## 🎯 Project Overview

- **Mission:** Automate IRAS compliance (GST F5, InvoiceNow, BCRS) with enterprise-grade financial integrity and a bold aesthetic.
- **Frontend:** Next.js 16.1.6 (App Router), React 19.2.3, Tailwind CSS 4.0, Shadcn/Radix UI.
- **Backend:** Django 6.0.2, Django REST Framework 3.16.1, Celery 5.6.2, Redis 6.4.0.
- **Database:** PostgreSQL 16+ with 7 domain-specific schemas and Row-Level Security (RLS).
- **Compliance:** IRAS 2026 Ready (9% GST, F5 returns, Peppol PINT-SG XML, 5-year retention).

## 🏗 Key Architectural Patterns

### 1. SQL-First & Unmanaged Models
The PostgreSQL schema (`database_schema.sql`) is the single source of truth. Django models use `managed = False` and map to existing tables. **Never run `makemigrations`**. Schema changes must be applied via SQL patches followed by model alignment.

### 2. Service Layer Pattern
All business logic resides in `services/` modules (e.g., `DashboardService`, `PaymentService`). Views are "thin" and only handle HTTP/serialization. Write operations should use `transaction.atomic()`.

### 3. Monetary Precision (No Floats)
All currency values use `NUMERIC(10,4)` internal precision.
- **Backend:** Use `common.decimal_utils.money()` which rejects `float` types.
- **Frontend:** Use `decimal.js` for all calculations.

### 4. Zero-Exposure JWT Security
Access tokens are kept in server memory (Server Components) or HttpOnly cookies. Browser JavaScript has **zero access** to JWTs. Next.js Server Components fetch data server-side via `serverFetch` in `lib/server/api-client.ts`.

### 5. Multi-Tenancy via RLS
Row-Level Security is enforced at the database level using session variables (`app.current_org_id`). `TenantContextMiddleware` sets this per-request.

## 🚀 Building and Running

### Backend Setup
1.  **Environment:** `python3 -m venv /opt/venv && source /opt/venv/bin/activate`
2.  **Install:** `pip install -e ".[dev]"`
3.  **Database:** `psql -h localhost -U ledgersg -d ledgersg_dev -f database_schema.sql` (Manual init is mandatory).
4.  **Run:** `python manage.py runserver`
5.  **Service Control:** Use `./backend_api_service.sh` for start/stop/status.

### Frontend Setup
1.  **Install:** `npm install`
2.  **Run Dev:** `npm run dev`
3.  **Run Server:** `npm run build:server && npm run start` (Standalone mode for API integration).

### Testing Strategy
**Standard Django test runners fail on unmanaged models.**
1.  **Init Test DB:**
    ```bash
    dropdb test_ledgersg_dev && createdb test_ledgersg_dev
    psql -d test_ledgersg_dev -f database_schema.sql
    ```
2.  **Run Backend:** `pytest --reuse-db --no-migrations`
3.  **Run Frontend:** `npm test` (Vitest) or `npm run test:e2e` (Playwright).

## 📁 Critical Files & Directories

- `database_schema.sql`: Source of truth for all table definitions.
- `apps/backend/apps/`: Domain modules (core, coa, gst, invoicing, journal, banking).
- `apps/backend/common/decimal_utils.py`: Essential monetary safety utilities.
- `apps/web/src/lib/server/api-client.ts`: Server-side API client with auth logic.
- `Project_Architecture_Document.md`: Comprehensive system reference.
- `ACCOMPLISHMENTS.md`: Recent feature completion log.

## 📐 Development Conventions

- **Elite / Meticulous / Avant-Garde:** Adhere to the "Illuminated Carbon" aesthetic—whitespace as a structural element, distinctive typography, and zero "AI slop" generics.
- **WCAG AAA:** Accessibility is non-negotiable.
- **IRAS 2026:** Every invoice and transaction must comply with Singapore regulatory standards.
- **Meticulous SOP:** ANALYZE → PLAN → VALIDATE → IMPLEMENT → VERIFY → DELIVER.
