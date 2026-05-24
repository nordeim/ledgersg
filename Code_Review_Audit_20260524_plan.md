# LedgerSG — Deep Analysis, Validation Plan & Critical Audit

---

## Part 1: Deep Understanding — WHAT, WHY, HOW

### WHAT: The Product

LedgerSG is a **double-entry accounting platform** purpose-built for **Singapore small and medium businesses**. It is not a generic QuickBooks clone — it's a vertically specialized system with these distinguishing characteristics:

1. **IRAS-native compliance** — GST F5 returns, InvoiceNow/Peppol, BCRS deposit handling, tax invoice labeling per IRAS Regulation 11, and 5-year document retention are first-class features, not add-ons.

2. **AI-agent-first design** — The README explicitly states this is designed for "AI agent automation." This means the API surface, data model, and workflow are structured so that autonomous agents (not just humans clicking UI buttons) can drive the full accounting lifecycle.

3. **"Illuminated Carbon" UI** — A neo-brutalist design system that explicitly rejects generic SaaS aesthetics. This is a deliberate branding choice for differentiation in the Singapore SMB market.

4. **Three business entity types supported** — Sole Proprietorships, Partnerships, and Pte Ltd companies, each with different compliance requirements.

### WHY: The Problem Being Solved

The core thesis is that **IRAS compliance is a burden for Singapore SMBs** and that existing solutions treat it as an afterthought (add-on modules, plugin dependencies, floating-point math, application-layer security). LedgerSG aims to make compliance:

- **Automatic** — GST F5 auto-generation, InvoiceNow auto-transmission on invoice approval, threshold monitoring
- **Precise** — `NUMERIC(10,4)` everywhere, `Decimal.js` for client-side preview, no floating-point anywhere
- **Secure by default** — PostgreSQL Row-Level Security enforcing tenant isolation at the database layer, not the application layer
- **Auditable** — Immutable append-only audit logs with 5-year retention

### HOW: Architecture Decisions

**Technology choices and their rationale:**

| Decision | Choice | Rationale |
|---|---|---|
| SQL-first schema | `database_schema.sql` as source of truth, unmanaged Django models | Eliminates Django migration drift; schema is authoritative |
| PostgreSQL RLS | `SET LOCAL app.current_org_id` via middleware | Multi-tenancy enforced at DB level — even a buggy app query can't leak cross-tenant data |
| NUMERIC(10,4) | PostgreSQL native | Eliminates the entire class of floating-point rounding bugs |
| Next.js App Router | Server Components for data fetching | JWT never exposed to client-side JavaScript — zero XSS token theft surface |
| Service Layer Pattern | All business logic in `services/` modules, thin views | Clean separation of concerns; testable without HTTP |
| Celery for async | Invoice email, Peppol transmission, PDF generation | Non-blocking user experience for long-running operations |
| Hybrid E2E testing | API for data operations, UI for visual verification | HttpOnly cookies break automation tools; this is the pragmatic solution |

**The 7 database schemas** suggest a clean domain separation:
- `core` — Users, Organizations, Auth
- `coa` — Chart of Accounts
- `journal` — General Ledger (double-entry engine)
- `invoicing` — Invoices, Credit Notes, Contacts
- `banking` — Bank accounts, payments, reconciliation
- `gst` — GST management, tax codes, F5 returns
- `audit` — Immutable event log

**The critical middleware** is `tenant_context.py` which sets the PostgreSQL session variable `app.current_org_id` — this is the linchpin of the entire security model. Every RLS policy references this variable.

---

## Part 2: Validation Plan — Checking Understanding Against Codebase

This is a systematic plan to verify my mental model against the actual code.

### Phase 1: Schema Validation (Priority: CRITICAL)

```
VALIDATION ITEM: Does database_schema.sql contain exactly 30 tables across 7 schemas?
VALIDATION ITEM: Does every table have appropriate RLS policies?
VALIDATION ITEM: Are all monetary columns NUMERIC(10,4)?
VALIDATION ITEM: Are there any FLOAT or REAL columns that should be NUMERIC?
VALIDATION ITEM: Does the audit.event_log table have no UPDATE/DELETE grants?
VALIDATION ITEM: Are all foreign keys properly defined with the correct ON DELETE behavior?
VALIDATION ITEM: Is the document_sequence table using FOR UPDATE locking?
VALIDATION ITEM: Does journal.validate_balance() trigger exist and fire on INSERT?
```

### Phase 2: RLS Enforcement Validation (Priority: CRITICAL)

```
VALIDATION ITEM: Does tenant_context.py SET LOCAL app.current_org_id correctly?
VALIDATION ITEM: Does every tenant-scoped table have an RLS policy referencing current_setting('app.current_org_id')?
VALIDATION ITEM: Is there a fallback/abort if app.current_org_id is NOT set?
VALIDATION ITEM: Can any API endpoint bypass RLS (e.g., raw SQL without the middleware)?
VALIDATION ITEM: Are there any views or materialized views that bypass RLS?
```

### Phase 3: Financial Integrity Validation (Priority: CRITICAL)

```
VALIDATION ITEM: Does every journal entry creation path validate debits == credits?
VALIDATION ITEM: Is the money() utility used consistently (no float arithmetic anywhere)?
VALIDATION ITEM: Are Decimal.js imports present in all frontend components doing financial calculations?
VALIDATION ITEM: Is GST calculation done server-side authoritatively (client preview only)?
VALIDATION ITEM: Does the GST F5 return cover all 15 boxes correctly?
```

### Phase 4: API Surface Validation (Priority: HIGH)

```
VALIDATION ITEM: Do all 87 endpoints follow the paginated {results, count} format?
VALIDATION ITEM: Are all endpoints behind JWT authentication?
VALIDATION ITEM: Are OPTIONS preflight requests handled by CORSJWTAuthentication?
VALIDATION ITEM: Is rate limiting applied to all auth endpoints?
VALIDATION ITEM: Do all list endpoints enforce tenant isolation?
```

### Phase 5: InvoiceNow/Peppol Validation (Priority: HIGH)

```
VALIDATION ITEM: Is PINT-SG XML generation correct (95%+ compliance)?
VALIDATION ITEM: Does the Storecove adapter have retry logic with exponential backoff?
VALIDATION ITEM: Is auto-transmit on approval actually triggered via Celery?
VALIDATION ITEM: Is the peppol_transmission_log capturing all required fields?
```

### Phase 6: Frontend Security Validation (Priority: HIGH)

```
VALIDATION ITEM: Is JWT truly never exposed to client-side JS?
VALIDATION ITEM: Do Server Components handle all data fetching?
VALIDATION ITEM: Is CSP configured correctly (12 headers mentioned)?
VALIDATION ITEM: Are there any client components that fetch with embedded tokens?
```

---

## Part 3: Critical Code Review & Audit — Identified Concerns

Based on the documentation alone, I've identified several areas of concern that warrant deep investigation.

### CONCERN 1: 67 Failing Backend Tests (SEVERITY: HIGH)

The README states: *"393 passed, 67 failed, 8 skipped (468 collected)"* and attributes the failures to *"fixture isolation issues."* It also adds: *"The production API works correctly — verified with direct testing."*

**Red flags:**
- 67/468 = **14.3% failure rate** is significant
- Blaming "fixture isolation" without fixing it suggests either the test infrastructure is fragile or there are real bugs masked by the excuse
- "Verified with direct testing" is not a substitute for passing automated tests
- **Audit action:** Examine every failing test. Categorize as: (a) genuine fixture issues, (b) real bugs, (c) test logic errors. Fix all of them.

### CONCERN 2: Unmanaged Models + Manual Schema Loading (SEVERITY: MEDIUM-HIGH)

The entire database schema is managed via `database_schema.sql` and Django models use `managed = False`. This means:
- **No migration safety net** — schema changes must be manually applied
- **Risk of drift** — if someone adds a column to the SQL file but forgets the model (or vice versa)
- **CI/CD complexity** — every environment must manually load the schema
- **Audit action:** Verify that the SQL schema and Django model definitions are perfectly in sync. Check every model's `db_table`, columns, and constraints against the SQL file.

### CONCERN 3: Test Database Initialization is Manual (SEVERITY: MEDIUM)

The README explicitly warns: *"Standard Django test runners fail on unmanaged models. Manual database initialization is required."* The test workflow involves:
```
dropdb ... || true
createdb ...
psql ... -f database_schema.sql
```
This is fragile, undocumented in CI/CD, and could cause data loss if accidentally run against the wrong database.

**Audit action:** Check if there's a `conftest.py` fixture or `pytest-django` setup that automates this. If not, this is a blocker for CI/CD.

### CONCERN 4: Ghost Column Issues (SEVERITY: MEDIUM)

The milestones mention: *"Fixed 'ghost column' issues in Peppol models"* — this suggests models were referencing columns that don't exist in the SQL schema. Given the `managed = False` approach, Django won't catch these at migration time.

**Audit action:** For every Django model, verify that every field maps to an actual column in `database_schema.sql`. Use a script to extract column names from both sources and diff them.

### CONCERN 5: UUID Handling Complexity (SEVERITY: MEDIUM)

A dedicated `UUID_PATTERNS_GUIDE.md` exists, and the troubleshooting section mentions: *"UUID object has no attribute 'replace'"* and *"Double UUID conversion."* This suggests UUID handling is a recurring pain point.

**Audit action:** Search the entire codebase for `UUID(` calls and verify that serialization/deserialization is consistent. Check if any views are double-converting UUIDs. Verify the JSON encoder handles UUIDs correctly in all serializers.

### CONCERN 6: CORS Authentication Class (SEVERITY: MEDIUM)

The `CORSJWTAuthentication` class *"Skips OPTIONS requests"* — this was a fix for CORS preflight returning 401. But skipping authentication for any method (even OPTIONS) needs careful validation.

**Audit action:** Verify that the class ONLY skips OPTIONS and no other methods. Check that Django's CORS middleware is properly configured to reject unauthorized origins. Ensure that OPTIONS responses don't leak any sensitive information.

### CONCERN 7: The is_voided Logic Error (SEVERITY: MEDIUM)

Milestones mention: *"Fixed is_voided logic errors in the Journal engine"* — the troubleshooting section clarifies: *"Service queries non-existent column."* This means the journal service was trying to filter on a column that doesn't exist in the database.

**Audit action:** Search the entire codebase for `is_voided` to confirm it's fully remediated. Check if there are any other similar phantom column references. Verify that voided entries are properly handled (what mechanism replaces `is_voided`?).

### CONCERN 8: Frontend Test Coverage Gap (SEC-004) (SEVERITY: MEDIUM)

The security audit identified *"Frontend test coverage minimal"* as a medium severity finding, still *"In Progress."* While 321 frontend tests exist and pass, the security team flagged that coverage is insufficient.

**Audit action:** Run `npm run test:coverage` in `apps/web` and examine the coverage report. Identify critical paths (authentication, financial calculations, data submission) with low coverage. Prioritize hooks and forms as the README suggests.

### CONCERN 9: PII Encryption Not Implemented (SEC-005) (SEVERITY: LOW-MEDIUM)

*"PII encryption at rest not implemented"* — GST registration numbers and bank account numbers are stored in plaintext. For a financial application handling sensitive Singapore business data, this is a meaningful gap.

**Audit action:** Identify all fields containing PII (GST numbers, bank accounts, NRICs if any). Assess the regulatory requirements under PDPA (Singapore's Personal Data Protection Act). Plan encryption-at-rest implementation.

### CONCERN 10: 500 Error Documentation Myth vs. Reality (SEVERITY: LOW-MEDIUM)

The troubleshooting section states: *"500 errors in journal/invoice — Documentation myth — FALSE - Production API works correctly (verified)."* The fact that this was documented as a "myth" suggests someone encountered these errors. If tests produce 500s but the production API doesn't, there's likely a test environment configuration issue.

**Audit action:** Reproduce the reported 500 errors in the test environment. Determine root cause. If it's truly a test-only issue, document it clearly. If production could hit the same path under different conditions, it's a real risk.

### CONCERN 11: Session Persistence in E2E (SEVERITY: LOW-MEDIUM)

The entire E2E testing approach had to pivot to a "Hybrid API + UI" method because HttpOnly cookies couldn't be persisted by automation tools. While functional, this means:
- UI-only paths are not fully tested end-to-end
- The workaround is documented but the root cause (session management architecture) isn't resolved
- A dedicated "test auth endpoint" with non-HttpOnly tokens is mentioned in the roadmap

**Audit action:** Evaluate the risk of the test-only auth endpoint. Ensure it cannot be activated in production. Consider implementing a test-specific environment variable gate.

### CONCERN 12: Redis Dependency for Dashboard (SEVERITY: LOW)

The dashboard uses Redis caching. If Redis is unavailable, does the dashboard gracefully degrade or fail?

**Audit action:** Check the dashboard service layer for Redis failure handling. Verify there's a fallback path (direct DB query) when cache is cold or unavailable.

### CONCERN 13: PDF Generation via WeasyPrint (SEVERITY: LOW)

WeasyPrint 68.1 is used for IRAS-compliant tax invoice generation. WeasyPrint is known to have edge cases with complex CSS layouts and CJK fonts (relevant for Singapore's multilingual context).

**Audit action:** Verify PDF output for invoices with Chinese/Tamil business names. Check that all required IRAS fields are present in the generated PDF. Test with edge cases (very long item descriptions, many line items, etc.).

---

## Part 4: Systematic Audit Execution Plan

### Week 1: Foundation Audit
| Day | Task | Deliverable |
|---|---|---|
| 1 | Schema-vs-model sync script | Diff report of all mismatches |
| 2 | RLS policy coverage audit | Table showing every table's RLS status |
| 3 | Financial precision audit | List of any float/double usage |
| 4 | Fix all 67 failing tests | 100% test pass rate |
| 5 | UUID handling consistency audit | Remediation list |

### Week 2: Security & Compliance Audit
| Day | Task | Deliverable |
|---|---|---|
| 1 | JWT exposure audit | Confirmation of zero client-side tokens |
| 2 | CORS/CSP validation | Header audit report |
| 3 | PII inventory | Field-level PII classification |
| 4 | InvoiceNow XML compliance | PINT-SG validation report |
| 5 | GST F5 correctness audit | Box-by-box verification |

### Week 3: Quality & Robustness Audit
| Day | Task | Deliverable |
|---|---|---|
| 1 | Frontend coverage expansion | Coverage report + gap analysis |
| 2 | Error handling audit | List of unhandled failure modes |
| 3 | Redis/cache failure modes | Resilience assessment |
| 4 | PDF generation edge cases | Multilingual validation |
| 5 | CI/CD pipeline audit | Gap analysis and recommendations |

---

## Summary

**What LedgerSG gets right (based on documentation):**
- SQL-first design with unmanaged models eliminates migration drift
- PostgreSQL RLS for multi-tenancy is the gold standard
- NUMERIC(10,4) everywhere is the correct choice for financial data
- Server Components eliminating JWT exposure is architecturally sound
- Comprehensive documentation is genuinely impressive

**What needs investigation (based on documentation red flags):**
- 67 failing tests treated as acceptable — this needs to be fixed
- Schema-model synchronization has no automated verification
- UUID handling complexity suggests inconsistent patterns
- Frontend test coverage gap flagged by security audit
- E2E testing workaround hides the real session architecture issue
- PII not encrypted at rest in a financial application

The project is architecturally ambitious and well-documented. The primary risks are in **test health**, **schema-model drift**, and **unresolved security findings**. The code review should focus on verifying that the documentation matches reality — and based on the "ghost column" and "is_voided" history, there are likely more undocumented discrepancies to find.
