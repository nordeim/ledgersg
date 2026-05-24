I could not complete a local `git clone` here because the container cannot resolve `github.com`, so I inspected the repository directly on GitHub and read the requested docs from the source.

**What LedgerSG is**
LedgerSG is documented as a production-grade, double-entry accounting platform for Singapore SMBs, focused on IRAS 2026 compliance and workflows such as GST F5, InvoiceNow/Peppol, BCRS handling, bank reconciliation, audit trails, and multi-tenant isolation. The README, PAD, CLAUDE, and GEMINI all describe the same core mission: reduce compliance burden while keeping the accounting engine authoritative and auditable. ([GitHub][1])

**Why it is built this way**
The design goal is not just “an accounting app,” but a compliance-first operating system for Singapore SMBs and accountants. The docs consistently frame the product as automating regulatory work, preserving ledger integrity, and making the UI authoritative but not generic, with the “Illuminated Carbon” design language called out repeatedly. ([GitHub][1])

**How the system is supposed to work**
The architecture is explicitly SQL-first: `apps/backend/database_schema.sql` is the source of truth, Django models are unmanaged (`managed = False`), and schema changes are manual SQL patches rather than migrations. The backend follows a service-layer pattern with thin views, `transaction.atomic()` for writes, PostgreSQL 16+ with RLS via session variables, Celery + Redis for async work, and WeasyPrint for document generation. The frontend uses Next.js App Router, React 19, Tailwind 4, Shadcn/Radix UI, Zustand for UI state, and TanStack Query for server state. ([GitHub][2])

**Security and auth model**
The docs describe a defense-in-depth auth setup: client-side session checks, JWT bearer access tokens, HttpOnly refresh cookies, CORS-aware authentication for preflight requests, rate limiting on auth endpoints, and a strict CSP. They also emphasize avoiding JWT exposure to client-side JavaScript and keeping sensitive fetches inside server components where possible. ([GitHub][3])

**Testing and validation philosophy**
Testing is supposed to be TDD-heavy, with backend tests requiring a manual database bootstrap from `database_schema.sql` before pytest can run cleanly. The docs also call out a hybrid E2E approach: use API calls for auth/data setup, then use UI automation only for visual verification, because HttpOnly-cookie persistence breaks pure browser automation. ([GitHub][4])

**The biggest thing I noticed before even touching code**
The docs are not perfectly synchronized. README says backend v0.3.3 with 87 endpoints and 459 collected tests; AGENTS says 83 endpoints and 233+ tests; GEMINI says backend v0.3.4 with 94 URL patterns and 459 collected tests; PAD says 706 tests passing and 94 endpoints. That drift does not prove a code problem, but it is a real audit signal because stale metrics and endpoint counts can hide regressions or confuse implementation decisions. ([GitHub][1])

**Validation plan against the codebase**
First I would verify the repository structure matches the architecture claims: `apps/backend` and `apps/web`, plus the expected domain modules, config, services, and tests. Then I would check the database contract end-to-end: confirm the SQL schema really is the authority, models are unmanaged, and no hidden migrations or model/table drift exist. After that I would validate the auth flow, RLS/session-variable wiring, org-scoped URL patterns, list endpoint response shapes, and the journal/invoicing paths that the API guide specifically calls out. Finally, I would compare the frontend’s server/client split, test coverage, and build modes against the documented behavior. ([GitHub][5])

**Critical code review and audit plan**
I would audit in this order: schema-model alignment and ghost-column risk; org isolation and RLS bypass risk; auth/session handling and token leakage risk; API contract consistency for paginated list endpoints; frontend hydration/state boundaries; and test reliability, especially the known hybrid E2E limitations. The API guide already flags one concrete contract issue that was fixed: list endpoints now return `{results, count}`, and the journal entries route is `/api/v1/{orgId}/journal-entries/entries/`, not `/journal/entries/`. That makes endpoint-contract validation a high-priority audit target rather than a theoretical one. ([GitHub][6])

The practical outcome is a review lens that is very clear: this project lives or dies on SQL-first consistency, strict tenancy boundaries, and API/UI contract discipline. Those are the three areas I would treat as non-negotiable checkpoints before trusting any feature change.

[1]: https://github.com/nordeim/ledgersg/blob/main/README.md "ledgersg/README.md at main · nordeim/ledgersg · GitHub"
[2]: https://github.com/nordeim/ledgersg/blob/main/GEMINI.md "ledgersg/GEMINI.md at main · nordeim/ledgersg · GitHub"
[3]: https://github.com/nordeim/ledgersg/blob/main/Project_Architecture_Document.md "ledgersg/Project_Architecture_Document.md at main · nordeim/ledgersg · GitHub"
[4]: https://github.com/nordeim/ledgersg/blob/main/AGENTS.md "ledgersg/AGENTS.md at main · nordeim/ledgersg · GitHub"
[5]: https://github.com/nordeim/ledgersg/tree/main/apps "ledgersg/apps at main · nordeim/ledgersg · GitHub"
[6]: https://github.com/nordeim/ledgersg/blob/main/API_CLI_Usage_Guide.md "ledgersg/API_CLI_Usage_Guide.md at main · nordeim/ledgersg · GitHub"

---

Excellent — I now have the actual repository and have begun executing the plan against the real codebase.

### Initial Execution Status

I successfully unpacked and inspected the repository.

**Repository shape (validated against docs):**

* `apps/backend` → Django backend present
* `apps/web` → Next.js frontend present
* `database_schema.sql` → exists in backend as documented
* Documentation corpus present and extensive
* Test infrastructure present
* Docker/containerization present
* Large remediation/audit history exists in `/docs` and `/plan`

**Early quantitative signals**

* ~208 Python files
* ~108 TypeScript/TSX files
* Significant architectural surface area (this is not a small codebase)

**Requested core docs validated**
I confirmed and began reviewing:

* `CLAUDE.md`
* `AGENTS.md`
* `README.md`
* `GEMINI.md`
* `Project_Architecture_Document.md`
* `API_CLI_Usage_Guide.md`

### Early Observations (Evidence-Based)

The repository is substantially more mature than the public-facing docs initially suggested.

I immediately noticed:

1. **Documentation synchronization appears significantly improved**
   Earlier GitHub inspection suggested drift. The attached codebase versions are much more aligned:

   * `CLAUDE.md v2.4.0`
   * `GEMINI.md v3.3.0 (Synchronized)`
   * PAD updated March 2026
   * README indicates **714 passing tests**

2. **Heavy remediation history**
   The repo contains many postmortem/remediation artifacts:

   * auth remediation
   * CORS remediation
   * API contract fixes
   * backend remediation reports
   * validation reports
   * security audit docs

   This is important because it suggests:

   * many historical problems may already be fixed,
   * but also indicates areas that deserve extra scrutiny for regressions.

3. **Potential audit smell: documentation density**
   There is a very large amount of operational documentation and historical reports. That is good for traceability, but can hide:

   * stale assumptions,
   * duplicated truth sources,
   * “documentation says fixed, implementation diverged later” problems.

### Execution Plan (Now Moving Into Code Validation)

I am proceeding in this order:

#### Phase 1 — Deep Architecture Assimilation

Cross-extract architecture claims from:

* CLAUDE
* GEMINI
* PAD
* API guide

Then convert them into **verifiable invariants**.

Examples:

**Database invariant**

> `database_schema.sql` must be authoritative
> → verify unmanaged Django models and drift risk.

**Security invariant**

> org isolation via RLS/session context
> → verify middleware/service propagation.

**Architecture invariant**

> thin views + service layer
> → verify controllers are not leaking business logic.

**Frontend invariant**

> server/client boundaries intentionally designed
> → verify Next.js implementation.

---

#### Phase 2 — Architecture ↔ Code Alignment Validation

I will systematically validate:

Backend:

* Django app structure
* models/services/views separation
* auth implementation
* tenancy enforcement
* transaction integrity
* accounting invariants
* Celery async handling

Database:

* schema-model drift
* indexes
* constraints
* FK integrity
* double-entry enforcement

Frontend:

* API integration correctness
* auth handling
* TanStack Query usage
* hydration risks
* state management quality

Tests:

* test realism
* gaps
* false confidence risks
* coverage concentration

---

#### Phase 3 — Critical Code Review & Audit

Then I will identify:

* bugs
* blockers
* hidden failure modes
* architectural drift
* performance risks
* security weaknesses
* maintainability issues
* technical debt hotspots

with **severity ranking and evidence**.

I have started execution and will continue meticulously against the actual implementation rather than relying on documentation claims.

---

I’ve continued the audit against the real codebase and found several high-confidence issues that matter in practice.

The biggest blockers so far are:

1. **Tenant/RLS context is being set in middleware before the request’s atomic transaction is active.**
   `TenantContextMiddleware` calls `SET LOCAL app.current_org_id` / `app.current_user_id`, but Django middleware runs outside the `ATOMIC_REQUESTS` transaction wrapper. That means the RLS session settings may not persist into the actual view transaction, or may fail outright. This directly threatens tenancy isolation.

2. **Auth refresh/logout is contract-broken between frontend and backend.**
   The backend’s `refresh_view` and `logout_view` require `request.data["refresh"]`, but the frontend login flow only stores the access token in memory and never stores or sends the refresh token. The frontend refresh path also posts with no refresh body and assumes an HttpOnly refresh cookie, but the backend never sets one. This makes session renewal and logout unreliable.

3. **Organisation creation has an address field mismatch that can break creation.**
   `OrganisationCreateSerializer` accepts `address`, and `OrganisationListCreateView.post()` forwards `serializer.validated_data` directly into `create_organisation()`. But the `Organisation` model has `address_line_1`, `address_line_2`, `city`, etc., not `address`. That means creating an organisation with an `address` value can raise an unexpected keyword error or otherwise fail.

4. **Several runtime dependencies are missing from `pyproject.toml`.**
   The code imports and configures:

   * `django_ratelimit`
   * `django_celery_beat`
   * `django_redis`
   * `requests`
     None of those are declared in the backend dependencies. That is a real install/runtime risk, not a cosmetic issue.

5. **GST account seeding appears broken on registration.**
   In `toggle_gst_registration()`, the code assigns `org.gst_reg_number = reg_number` and then checks `if not org.gst_reg_number:` before seeding GST accounts. That condition will never be true after assignment, so the intended seeding path will not run.

6. **Organisation creation/update contract is not aligned with the schema.**
   The serializer accepts free-form `entity_type`, while the schema only allows the uppercase enum values like `PRIVATE_LIMITED`. The tests even use `pte_ltd`, which does not match the model/schema values. That is likely to surface as validation or DB-constraint failures.

7. **Some API response shapes still diverge from the standardized contract.**
   For example, `OrganisationListCreateView.get()` returns `{"data": ..., "count": ...}` while the contract standardization tests expect `{"results": ..., "count": ...}`. That is exactly the kind of mismatch that causes frontend and test drift.

I’m continuing through the remaining backend and frontend surfaces with the same pass: auth, tenancy, schema alignment, API contracts, and the most failure-prone service paths.

---

I continued the audit and confirmed several concrete issues in the implementation, not just documentation drift.

The most important findings so far are:

* **Hard blocker:** `apps/core/services/org_seed_service.py` has a Python `IndentationError` around line 285. That file does not compile, so the codebase contains at least one outright syntax-level failure.

* **Tenant/RLS context is likely set in the wrong place:** `TenantContextMiddleware` executes `SET LOCAL app.current_org_id` / `app.current_user_id` in middleware, but the project relies on `ATOMIC_REQUESTS`. Middleware runs outside the request transaction, so the `SET LOCAL` session state may not survive into the actual view’s DB work. That threatens tenant isolation.

* **Auth/session handling is internally inconsistent:**
  The frontend stores the access token only in memory via `setAccessToken(...)`, but nothing writes it to persistent storage, and the backend does not set the refresh token as an HttpOnly cookie. On a page reload, `checkSession()` calls `/auth/me/` without an auth header, so the session cannot naturally restore. On top of that, `use-invoices.ts` reads `localStorage.getItem("accessToken")`, but nothing in the app writes that key.

* **Auth API contracts are out of sync across code paths:**
  The backend `refresh_view` expects `refresh`, while integration tests send `refresh_token`. The backend `change-password` serializer expects `old_password`, while tests send `current_password`. The login response returns nested `{"tokens": {...}}`, while some tests expect flat `access_token` / `refresh_token` fields. That is a real contract drift problem.

* **Organisation creation/update has a field mismatch:**
  `OrganisationCreateSerializer` accepts `address`, and `OrganisationListCreateView.post()` forwards `serializer.validated_data` directly into `create_organisation()`. The model has `address_line_1`, `address_line_2`, `city`, `postal_code`, etc., but no `address` field. `update_organisation()` also silently ignores unknown keys, so `address` updates will not persist.

* **GST seeding logic is broken:**
  In `toggle_gst_registration()`, `org.gst_reg_number` is assigned and then checked with `if not org.gst_reg_number:` before seeding GST accounts. That condition will never be true after assignment, so the seeding path will not run as intended.

* **API response contract drift exists in collection endpoints:**
  Several views still return `{"data": ..., "count": ...}` instead of the standardized `{"results": ..., "count": ...}` that the contract tests expect. I confirmed this in:

  * `apps/core/views/organisations.py`
  * `apps/gst/views.py` (`TaxCodeIrasInfoView`)
  * `apps/journal/views.py` (`EntryTypesView`)

* **Packaging drift risk:**
  `apps/backend/pyproject.toml` does not list every runtime dependency used by settings/views, though `requirements.txt` does include many of them. That means install behavior may vary depending on whether the project is built from `pyproject.toml` or the requirements file.

I’m now moving through the remaining banking, invoicing, and reporting surfaces using the same lens: compile safety, contract alignment, tenant isolation, and auth/session correctness.

---

I’ve continued the code audit and confirmed more concrete implementation problems.

The strongest findings so far are:

* **Hard compile blocker:** `apps/backend/apps/core/services/org_seed_service.py` has an `IndentationError` around line 285, so the repository contains at least one file that cannot even be imported.

* **Tenant/RLS context is set in the wrong execution phase:** `common.middleware.tenant_context.TenantContextMiddleware` issues `SET LOCAL app.current_org_id` and `SET LOCAL app.current_user_id` from middleware, but the project relies on `ATOMIC_REQUESTS = True`. That means the `SET LOCAL` scope may not align with the actual view transaction, which threatens the RLS isolation model the architecture depends on.

* **Auth refresh is broken end-to-end:**
  Backend `refresh_view` and `logout_view` expect `request.data["refresh"]`, but the browser client’s `tryRefreshToken()` posts to `/auth/refresh/` with no body at all. The frontend also assumes refresh cookies exist, but the backend login flow does not set any cookies. That makes token refresh and logout contract-incompatible.

* **Session persistence is not actually implemented in the browser client:**
  `AuthProvider.login()` stores the access token only in memory via `setAccessToken(...)`. There is no write to `localStorage` or cookies. Yet `useInvoicePDF()` later reads `localStorage.getItem("accessToken")`, which will be `null` unless some other code stores it. On reload, `checkSession()` also has no durable token to restore from.

* **Organisation creation has a field mismatch that can break writes:**
  `OrganisationCreateSerializer` accepts an `address` field, and `OrganisationListCreateView.post()` forwards `serializer.validated_data` directly into `organisation_service.create_organisation(...)`. The `Organisation` model does not have an `address` field; it has `address_line_1`, `address_line_2`, `city`, `postal_code`, and related fields. That can trigger unexpected keyword errors or silently lose data depending on the path.

* **Organisation update drops address changes:**
  `OrganisationDetailView.patch()` allows `"address"` in `allowed_fields`, but `organisation_service.update_organisation()` only applies attributes that actually exist on the model. Since `address` is not a model field, the update never persists.

* **GST seeding logic is inverted:**
  In `toggle_gst_registration()`, the code assigns `org.gst_reg_number = reg_number` and then checks `if not org.gst_reg_number:` before seeding GST accounts. That condition will never be true after assignment, so the intended seed path will not run.

* **API contract drift is still present:**
  Collection endpoints like `OrganisationListCreateView.get()` return `{"data": ..., "count": ...}`, while the contract standardization tests expect `{"results": ..., "count": ...}`. That is a real mismatch between implementation and the project’s own test/contract direction.

* **Authentication contract drift exists inside the codebase itself:**
  The current backend view layer returns nested `{"tokens": {...}}`, while some integration tests still expect flat `access_token` / `refresh_token` fields, and some tests send `refresh_token` or `current_password` while the live serializers/views expect `refresh` and `old_password`. The codebase is not fully aligned on the auth contract yet.

* **Missing runtime dependencies in `pyproject.toml`:**
  The backend settings and code use packages such as `django_ratelimit`, `django_celery_beat`, and `requests`, but those are not declared in `apps/backend/pyproject.toml`. That creates a real install/runtime risk depending on how the project is built.

I’m continuing the audit through the remaining backend modules next, especially banking, invoicing, reporting, and the database/schema layer, to check for similar contract and invariant breaks.

---

I’ve continued the audit against the actual uploaded codebase and found more concrete issues.

The highest-confidence findings so far are:

* `apps/backend/apps/core/services/org_seed_service.py` has a real `IndentationError` in the account seeding loop. That file does not compile.
* The auth contract is still inconsistent end-to-end:

  * backend `login_view` returns `{"user": ..., "tokens": {...}}`
  * backend `refresh_view` expects `refresh`
  * backend `logout_view` also expects `refresh`
  * backend `change_password_view` expects `old_password`
  * backend integration tests still send `refresh_token` and `current_password`
  * frontend login stores only an in-memory access token, while the server-side client expects `access_token` and `refresh_token` cookies that the backend does not set
* `OrganisationCreateSerializer` accepts `address`, but the organisation model uses `address_line_1`, `address_line_2`, `city`, `postal_code`, and related fields. That makes organisation creation/update contract-wrong for address data.
* `OrganisationDetailView.patch()` allows `"address"` in updates, but `organisation_service.update_organisation()` only sets real model attributes, so `address` updates will silently do nothing.
* `toggle_gst_registration()` assigns `gst_reg_number` and then checks `if not org.gst_reg_number:` before seeding GST accounts. That seed path will never run after assignment.
* `_create_document_sequences()` exists in `organisation_service.py` but is never called anywhere, so document numbering sequences are not initialized by organisation creation.
* The project’s own API contract standardization tests expect collection endpoints to return `{"results": ..., "count": ...}`, but some implemented views still return `{"data": ..., "count": ...}`.

I also confirmed a deeper architectural risk that matters for production safety: `TenantContextMiddleware` is doing `SET LOCAL app.current_org_id` / `app.current_user_id`, but it is executed in middleware rather than inside the request transaction boundary the code is relying on. That makes the RLS tenancy model fragile and worth treating as a serious audit item.

I’m now moving through the remaining banking, invoicing, reporting, and frontend integration surfaces with the same approach: compile safety, contract alignment, tenancy isolation, and data integrity.
