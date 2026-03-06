# LedgerSG - Global Context & Instructions

This document serves as the **Single Source of Truth** for Gemini CLI to understand the LedgerSG project architecture, development standards, and operational mandates.

## 🎯 Project Overview

**LedgerSG** is a production-grade, double-entry accounting platform purpose-built for Singapore SMBs. It transforms IRAS 2026 compliance into a seamless experience with a distinctive "Illuminated Carbon" neo-brutalist UI.

- **Mission**: Automated IRAS compliance and high-integrity financial management.
- **Architecture**: Decoupled Monorepo (Next.js Frontend + Django Backend).
- **Core Principles**: SQL-First, Service-Oriented, Security-First, WCAG AAA.
- **Current Status**: **Production Ready** (645+ tests, 100% Security Score).

## 💻 Technical Stack

### Backend (Django 6.0.2)
- **Framework**: Django REST Framework (DRF) 3.16.1.
- **Database**: PostgreSQL 16+ (7 schemas: `core`, `coa`, `gst`, `journal`, `invoicing`, `banking`, `audit`).
- **Isolation**: Row-Level Security (RLS) via `app.current_org_id` session variable.
- **Security**: 
  - `django-ratelimit` (4.1.0) for auth endpoints.
  - `django-csp` (4.0) for Content Security Policy.
- **Async**: Celery 5.4+ with Redis 7+.
- **Precision**: `NUMERIC(10,4)` for all money values. **Floats are strictly prohibited.**

### Frontend (Next.js 16.1.6)
- **Framework**: React 19 (App Router).
- **Styling**: Tailwind CSS 4.0 + Shadcn/Radix UI.
- **State**: Zustand (UI) + TanStack Query v5 (Server State).
- **Security**: 
  - Server Components for data fetching (Zero JWT exposure to browser JS).
  - Strict CSP Middleware with dynamic nonces and `strict-dynamic`.
- **Design**: "Illuminated Carbon" Neo-Brutalist (Anti-Generic).

## 🏗 Architectural Mandates

### 1. SQL-First Design (Unmanaged Models)
- The database schema (`database_schema.sql`) is the source of truth.
- Django models use `managed = False`.
- **Prohibited**: `python manage.py makemigrations`. Schema changes require manual SQL patches and model alignment.

### 2. Service Layer Pattern
- **Logic Location**: All business logic MUST reside in `apps/backend/apps/*/services/`.
- **Views**: Should be thin controllers delegating to services.
- **Atomic Requests**: Every request runs in a transaction for RLS consistency.
- **Recent Alignments**: Phase A complete (Journal Service fields aligned with schema).

### 3. Financial Integrity
- Use `common.decimal_utils.money()` for all currency operations.
- Debits must equal credits (enforced via `JournalService` and DB constraints).
- Posted entries are immutable; corrections require reversing entries.

### 4. Security & Multi-Tenancy
- **JWT**: 15m Access / 7d Refresh (stored in HttpOnly Cookies).
- **RLS**: Every query must respect the `org_id` context. `TenantContextMiddleware` sets the PG session variable.
- **Context**: Phase B complete (Dynamic Organisation Context implemented across UI).
- **Defense-in-Depth**: Both Frontend and Backend enforce strict Content Security Policies (SEC-003).

## 🧪 Frontend Development Standards

### 1. Library & API Usage
- **TanStack Query v5**: Use `isPending` for mutations (instead of `isLoading`).
- **Zod**: Use `error.issues` when iterating validation errors.
- **Strict Typing**: Filters that can represent "all" should use `boolean | null` to distinguish from `undefined`.

### 2. Schema Management
- All new data schemas must be created in `src/shared/schemas/` and exported via the barrel file (`index.ts`).
- Schemas should use Zod for runtime validation and TypeScript for static typing.

## 🛠 Core Commands

### Backend
| Task | Command |
|------|---------|
| Initialize DB | `psql -h localhost -U ledgersg -d ledgersg_dev -f database_schema.sql` |
| Start Server | `python manage.py runserver` |
| Run Tests | `pytest --reuse-db --no-migrations` |
| Celery | `celery -A config worker -l info` |

### Frontend
| Task | Command |
|------|---------|
| Dev Mode | `npm run dev` |
| Build (Server) | `npm run build:server` (Standalone mode) |
| Start Prod | `npm run start` |
| Run Tests | `npm test` |
| Type Check | `npx tsc --noEmit` |

## 🧪 Testing Strategy (TDD)

LedgerSG follows a strict **Meticulous Approach**:
1. **Analyze**: Deep requirement mining.
2. **Plan**: Structured roadmap.
3. **Validate**: Confirmation before code.
4. **Implement**: TDD (RED -> GREEN -> REFACTOR).
5. **Verify**: Rigorous QA + edge cases.

**Note**: To run backend tests, you MUST manually initialize the test database:
```bash
dropdb test_ledgersg_dev && createdb test_ledgersg_dev
psql -d test_ledgersg_dev -f database_schema.sql
```

## 📁 Critical Files
- `database_schema.sql`: Authoritative DB structure.
- `apps/backend/config/settings/base.py`: Core system config (Middleware, CSP, DB).
- `apps/web/src/middleware.ts`: Frontend security middleware (CSP, Nonces).
- `apps/web/src/lib/api-client.ts`: Frontend-Backend bridge.
- `apps/web/src/providers/auth-provider.tsx`: Dynamic org context.
- `ACCOMPLISHMENTS.md`: Project status and milestones (Current: 645+ tests).
- `AGENT_BRIEF.md`: Detailed engineering patterns and lessons learned.

## 🎨 Visual Identity
- **Palette**: Dark (Carbon), High-contrast accents (Emerald/Amber).
- **Typography**: Bespoke hierarchy, mono-space for financial data.
- **Philosophy**: Whitespace as structure, no "safe" templates.
