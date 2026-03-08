# LedgerSG — Enterprise Accounting Platform

[![IRAS](https://img.shields.io/badge/IRAS-2026%20Compliant-red)](https://iras.gov.sg)
[![WCAG](https://img.shields.io/badge/WCAG-AAA-success)](https://wcag.com)
[![Security Score](https://img.shields.io/badge/security-100%25-brightgreen)](SECURITY_AUDIT.md)
[![License](https://img.shields.io/badge/license-AGPL--3.0-blue)](LICENSE)
[![Tests](https://img.shields.io/badge/tests-651%20passed-success)](ACCOMPLISHMENTS.md)

> **Production-Grade Double-Entry Accounting for Singapore SMBs**
>
> SQL-First • Service-Oriented • RLS-Enforced • Illuminated Carbon UI

---

## 🎯 Project Overview

**LedgerSG** is a high-integrity accounting platform purpose-built for Singapore SMBs. It transforms IRAS 2026 compliance (GST F5, InvoiceNow, BCRS) into a seamless experience via a distinctive neo-brutalist interface.

### **Current Status (2026-03-08)**
| Component | Status | Version | Metrics |
| :--- | :--- | :--- | :--- |
| **Frontend** | ✅ Production | v0.1.0 | 12 Pages, 305 Passed Tests, WCAG AAA |
| **Backend** | ✅ Production | v1.0.0 | 96+ Endpoints, 346 Passed Tests |
| **Security** | ✅ 100% Score | v1.0.0 | Ratelimit (SEC-002), CSP (SEC-003), RLS Fixes |
| **Overall** | ✅ Platform Ready | — | **651 Tests Verified (100% Pass Rate)** |

---

## 🏗 Architectural Mandates

1.  **SQL-First Design**: `database_schema.sql` is the absolute source of truth. Models are `managed = False`. **NEVER** use `makemigrations`.
2.  **Service Layer Pattern**: All business logic lives in `apps/backend/apps/*/services/`. Views are thin controllers.
3.  **RLS Isolation**: PostgreSQL Row-Level Security enforced via `app.current_org_id` per-request session variables.
4.  **Financial Integrity**: `NUMERIC(10,4)` precision. Floats are prohibited. Use `common.decimal_utils.money()`.

---

## 📚 Project Documentation Registry

| Document | Purpose | Target Audience |
| :--- | :--- | :--- |
| **[PAD.md](Project_Architecture_Document.md)** | **Primary Handbook**: Full architecture, flowcharts, and setup. | New Developers / Agents |
| **[GEMINI.md](GEMINI.md)** | **Source of Truth**: Current status, metrics, and core mandates. | AI Agents / Developers |
| **[API_Usage.md](API_CLI_Usage_Guide.md)** | **API Reference**: 96+ endpoints with curl examples and CLI tips. | AI Agents / DevOps |
| **[AGENT_BRIEF.md](AGENT_BRIEF.md)** | **Engineering Patterns**: TDD workflows and deep-dive logic. | Coding Agents |
| **[UUID_GUIDE.md](UUID_PATTERNS_GUIDE.md)** | **Pitfall Guide**: Correct UUID handling in Django/PostgreSQL. | Developers |
| **[ACCOMPLISHMENTS.md](ACCOMPLISHMENTS.md)** | **Milestone Log**: Detailed record of all remediation phases. | Project Managers |

---

## 🧪 Testing & Development

### **The Manual TDD Workflow**
Standard Django test runners fail on unmanaged models. Follow this strict sequence:

```bash
# 1. Initialize Test DB
dropdb test_ledgersg_dev && createdb test_ledgersg_dev
psql -d test_ledgersg_dev -f database_schema.sql

# 2. Run Backend Tests
pytest --reuse-db --no-migrations

# 3. Run Frontend Tests
npm test
```

---

## ⚠️ Critical Pitfalls & Key Learnings

### **1. The UUID Double-Conversion Trap**
Django URL converters (`<uuid:org_id>`) already provide UUID objects. Wrapping them in `UUID(org_id)` again in views causes an `AttributeError`. **Use variables directly.**

### **2. RLS Middleware Compliance**
PostgreSQL `SET LOCAL` requires string values. Setting `app.current_org_id = NULL` will fail. **Use an empty string `''`** for unauthenticated requests to ensure safe denial.

### **3. Radix UI Interaction Simulation**
Standard `fireEvent.click` often fails to trigger state changes in Radix UI components (Tabs, Selects). **Mandatory**: Use `userEvent.setup()` and `await user.click()`.

### **4. Hydration & Server Components**
Zero JWT exposure is achieved by fetching data in **Server Components**. Avoid moving auth state to Client Components unless strictly necessary for interactivity.

### **5. Decimal vs. JSON**
Standard JSON serializers fail on Decimal types. All API responses must use the `DecimalSafeJSONRenderer` to maintain 4-decimal precision.

---

## 🚀 Strategic Roadmap

- [ ] **SEC-004**: Expand frontend test coverage for complex hooks and forms.
- [ ] **SEC-005**: Implement PII encryption at rest (pgcrypto) for sensitive identifiers.
- [ ] **InvoiceNow**: Finalize PINT-SG XML generation and transmission logic.
- [ ] **CI/CD**: Automate the manual SQL-first testing pipeline in GitHub Actions.

---

<div align="center">

**LedgerSG** — High-Integrity Accounting for Singapore
[Report Issue](https://github.com/ledgersg/ledgersg/issues) · [API Guide](API_CLI_Usage_Guide.md) · [Architecture](Project_Architecture_Document.md)

</div>
