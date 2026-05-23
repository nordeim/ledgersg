### 1. Deep Understanding: WHAT, WHY, and HOW

#### **WHAT: The Product Identity**
**LedgerSG** is an enterprise-grade, double-entry accounting platform purpose-built for Singapore Small and Medium Businesses (SMBs). Unlike traditional software designed for human clicks, LedgerSG is engineered for the **AI-first era**, prioritizing API automation and agent interoperability. It features a distinctive **"Illuminated Carbon"** neo-brutalist user interface and provides native, out-of-the-box compliance for **IRAS 2026** regulations (GST F5, InvoiceNow/Peppol, and BCRS).

#### **WHY: The Core Mission**
The platform exists to transform IRAS compliance from a manual regulatory burden into a seamless, automated experience. By enforcing strict data integrity and precision at the database level, it eliminates the "generic SaaS" feel of competitors, offering an authoritative yet approachable financial tool that guarantees audit-ready accuracy for Sole Proprietorships, Partnerships, and Pte Ltd companies.

#### **HOW: The Architectural Pillars**
*   **SQL-First & Unmanaged Models:** The `database_schema.sql` file is the absolute source of truth. Django models use `managed = False`, and `makemigrations` is strictly prohibited to prevent ORM-induced schema drift.
*   **Service Layer Supremacy:** Business logic is isolated in `services/` modules. Views act as thin controllers, delegating all operations to services that manage atomic transactions.
*   **RLS-Enforced Multi-Tenancy:** Data isolation is enforced at the PostgreSQL level using Row-Level Security (RLS). The `TenantContextMiddleware` sets session variables (`app.current_org_id`) for every request, ensuring the database denies access to unauthorized tenants.
*   **Financial Precision:** All monetary values use `NUMERIC(10,4)` in PostgreSQL and Python's `Decimal` via the `money()` utility. **Floating-point arithmetic is strictly prohibited.**
*   **Zero JWT Exposure:** To prevent XSS, JWT tokens are never exposed to the browser's JavaScript memory. Refresh tokens are stored in **HttpOnly** cookies, and access tokens are handled exclusively by Next.js Server Components.
*   **Hybrid E2E Testing:** Due to HttpOnly cookies breaking browser automation (Playwright), the project uses a hybrid approach: API for data setup/verification and UI for visual validation.

---

### 2. Validation Plan: Aligning Documentation with Codebase

To verify that the codebase strictly adheres to the architectural mandates documented in `CLAUDE.md` and `Project_Architecture_Document.md`, I will execute the following validation steps:

1.  **Schema & ORM Alignment:**
    *   **Action:** Inspect `apps/backend/database_schema.sql` and compare it against Django models in `apps/backend/apps/*/models/`.
    *   **Check:** Verify that every model has `managed = False` in its `Meta` class. Run a dry-run of `python manage.py makemigrations` to confirm zero pending migrations (proving the SQL-first discipline).
2.  **Service Layer Purity Check:**
    *   **Action:** Review key views (e.g., `banking/views.py`, `invoicing/views.py`).
    *   **Check:** Ensure views contain no business logic (no direct DB writes or complex calculations) and strictly delegate to their corresponding `services.py` files.
3.  **RLS & Middleware Verification:**
    *   **Action:** Analyze `apps/backend/common/middleware/tenant_context.py`.
    *   **Check:** Confirm it executes `SET LOCAL app.current_org_id` via raw SQL cursor execution before any view logic runs. Cross-reference with `database_schema.sql` to ensure RLS policies (`CREATE POLICY`) exist on all tenant-scoped tables.
4.  **Financial Precision Sweep:**
    *   **Action:** Perform a regex search across the Python backend for `float()` usage or `FloatField` definitions.
    *   **Check:** Ensure all monetary operations utilize `common.decimal_utils.money()` and that database columns for amounts are strictly `NUMERIC(10,4)`.
5.  **Security Posture Validation:**
    *   **Action:** Inspect Next.js Server Components and `middleware.ts`.
    *   **Check:** Verify that JWT tokens are never serialized into the client-side HTML/JSON payload. Confirm that `CORSJWTAuthentication` correctly handles `OPTIONS` preflight requests without exposing auth logic.
6.  **API Contract Verification:**
    *   **Action:** Test the 9 recently standardized list endpoints (e.g., `/banking/bank-accounts/`).
    *   **Check:** Confirm they return the paginated `{results, count}` format instead of raw arrays, validating the fix for the "Banking page broken" bug.

---

### 3. Critical Code Review & Audit Plan

This audit will identify latent bugs, security vulnerabilities, and architectural debt, focusing on the specific "known issues" and "myths" highlighted in the documentation.

#### **Phase 1: Security & Authentication Audit**
*   **RLS Bypass Vectors:** Audit all raw SQL queries (`.raw()`, `.extra()`, `cursor.execute()`) to ensure they do not bypass RLS policies. Verify that the `TenantContextMiddleware` cannot be skipped by malformed headers.
*   **JWT & Session Hardening:** Review the `HttpOnly` cookie configuration. Ensure `Secure` and `SameSite=Strict` flags are set. Verify that the 15-minute access token expiry is strictly enforced on the backend.
*   **CSP & Rate Limiting:** Validate `django-csp` directives to ensure they are restrictive enough to prevent XSS. Check `django-ratelimit` decorators on auth endpoints to ensure they effectively mitigate brute-force attacks.

#### **Phase 2: Database & Performance Audit**
*   **Indexing Strategy:** Analyze `database_schema.sql` for missing B-tree indexes on high-cardinality foreign keys (e.g., `org_id`, `contact_id`, `document_id`). Missing indexes here will cause severe performance degradation as tenant data grows.
*   **N+1 Query Detection:** Review Service layer queries, particularly in list views and reporting aggregations. Ensure `select_related` and `prefetch_related` are used to prevent N+1 query problems.
*   **Transaction Management:** Audit `services.py` for `transaction.atomic()` usage. Ensure no long-running loops or external API calls (e.g., Storecove/Peppol transmission) occur *inside* atomic blocks, which would hold database locks and degrade concurrency.

#### **Phase 3: Financial & Compliance Audit (IRAS)**
*   **GST Calculation Logic:** deeply audit the `gst` module. Verify that Standard-Rated (SR 9%), Zero-Rated (ZR), and Exempt (ES) supplies are categorized correctly. Ensure the rounding logic for the F5 return matches IRAS guidelines (e.g., rounding to the nearest cent vs. truncation).
*   **Audit Trail Immutability:** Verify that the `audit.event_log` table has **NO** `UPDATE` or `DELETE` privileges granted to the application role. This is a critical IRAS requirement for 5-year retention.
*   **Peppol/InvoiceNow XML:** Review the XML generation logic for PINT-SG compliance. Ensure mandatory fields are validated before transmission to prevent rejection by the Access Point.

#### **Phase 4: Code Quality & Architecture Audit**
*   **Ghost Column Residue:** Scan models to ensure none incorrectly inherit from `TenantModel` if the underlying SQL table lacks `created_at`/`updated_at` columns. This was a known cause of `ProgrammingError` in previous iterations.
*   **Type Safety:** Audit TypeScript strictness in `apps/web`. Ensure `any` is eliminated in favor of `unknown` and that Zod validation schemas perfectly mirror the DRF serializers on the backend.
*   **Error Handling:** Check if exceptions in the Service layer are properly caught and returned as standardized API errors (e.g., `{"detail": "..."}`) without leaking stack traces or internal system paths.

#### **Phase 5: Testing & CI/CD Audit**
*   **Fixture Isolation (The "403 Bug"):** Investigate the 67 failing backend tests mentioned in the docs. Audit `conftest.py` to fix RLS context leakage. The issue likely stems from `app.current_org_id` persisting across tests or fixtures not correctly setting the RLS session variable before DB access.
*   **Coverage Gaps:** Identify untested edge cases in complex workflows, such as multi-currency FX gain/loss realization, BCRS deposit handling, and credit note reversals.
*   **E2E Flakiness:** Review the hybrid E2E scripts (`e2e_test_phases_7_15_simplified.py`). Ensure proper data teardown and cleanup routines exist to prevent state pollution between test runs, which is critical for the "Hybrid API + UI" approach.

---
