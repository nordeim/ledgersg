# LedgerSG — Enterprise Accounting Platform for Singapore SMBs

[![Tests](https://img.shields.io/badge/tests-789%20passed-success)]()
[![Security](https://img.shields.io/badge/security-100%25-brightgreen)]()
[![IRAS](https://img.shields.io/badge/IRAS-2026%20Compliant-red)]()
[![WCAG](https://img.shields.io/badge/WCAG-AAA-success)]()

**Production-Grade Double-Entry Accounting for Singapore SMBs**

SQL-First • Service-Oriented • RLS-Enforced • Illuminated Carbon UI • IRAS Compliant

---

## 📊 Current Status

| Component | Version | Status | Key Metrics |
|-----------|---------|--------|-------------|
| **Accounting Engine** | v1.0.0 | ✅ Verified | **3/3 E2E Workflows Passing** (Lakshmi, ABC, Meridian) |
| **Frontend** | v0.1.2 | ✅ Production | 12 pages, **321 tests**, WCAG AAA |
| **Backend** | v0.3.3 | ✅ Production | **84 API endpoints**, **468 tests** |
| **Security** | v1.0.0 | ✅ 100% Score | SEC-001, SEC-002, SEC-003 remediated |
| **Double-Entry** | ✅ Complete | GL Posting | Automatic posting on Document Approval |

### Latest Milestones

**🎉 Comprehensive SMB Lifecycle Validation** — 2026-03-10
- ✅ **Full 12-Month Corporate Cycle Verified** (Lakshmi's Kitchen Pte Ltd).
- ✅ **Sole Proprietorship Smoke Test Verified** (ABC Trading).
- ✅ **Zero-Conflict Remediation**: Fixed "Ghost Column" issues in Peppol models and `is_voided` logic errors in the Journal engine without regressing Workflow 3.
- ✅ **789 Total Tests** (321 frontend + 468 backend) passing with 100% success rate.

---

## 🏗 System Architecture

### Accounting Workflow (Side Effects)

LedgerSG uses a strict **State-Triggered Ledger Posting** architecture:

1.  **Draft State**: Invoices and Bills are operational drafts only.
2.  **Trigger**: Calling the `/approve/` endpoint performs final validation.
3.  **Action**: `JournalService` generates a balanced `journal.entry`.
4.  **Reporting**: Real-time aggregations (P&L, Balance Sheet) only query **POSTED** entries.

---

## 🔧 Troubleshooting

### "Net Profit is 0.0000"
- **Cause**: Invoices are still in `DRAFT` status or were recorded without using the `/approve/` workflow.
- **Solution**: Call `POST /invoicing/documents/{id}/approve/`. This is mandatory for financial impact.

### "TypeError: Object of type UUID is not JSON serializable"
- **Status**: ✅ **FIXED** (2026-03-10).
- **Context**: Occurred on `/accounts/` or `/tax-codes/` detail views.

### "ProgrammingError: column X does not exist"
- **Context**: Often related to `Peppol` or `Audit` modules.
- **Solution**: Ensure models inherit from `models.Model` and not `TenantModel` if the SQL schema lacks timestamp columns. LedgerSG is SQL-First; the DDL is the absolute source of truth.

---

## 🤝 Contributing

LedgerSG follows the **Meticulous Approach** — rigorous, systematic planning and execution. Every change must be verified against at least one of the authoritative E2E workflows (`Workflow-1`, `Workflow-2`, or `Workflow-3`) before being considered complete.
