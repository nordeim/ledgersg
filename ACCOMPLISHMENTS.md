# LedgerSG Development — Accomplishment Summary

## Overview

This document records the completed work on the LedgerSG platform, aligned with the **"Illuminated Carbon" Neo-Brutalist fintech** design system and **IRAS 2026 compliance** requirements.

**Project Status**:
- ✅ Frontend: v0.1.2 — Production Ready (321 Tests, WCAG AAA)
- ✅ Backend: v0.3.3 — Production Ready (84 API endpoints, 468 Tests)
- ✅ Database: v1.0.3 — Hardened & Aligned (7 Schemas, 29 Tables)
- ✅ **Accounting Engine**: v1.0.0 — **Validated via Full E2E Workflows**
- ✅ **InvoiceNow/Peppol**: v1.0.0 — **Phases 1-4 Complete** (122+ TDD Tests)
- ✅ **Security**: v1.0.0 — **100% Score** (SEC-001/002/003 Remediated)
- ✅ **Testing**: v1.8.0 — **789 Unit Tests + 3 Comprehensive E2E Workflows Passing**

---

## Executive Summary

| Component | Status | Version | Key Deliverables |
|-----------|--------|---------|------------------|
| **Accounting Engine** | ✅ Complete | v1.0.0 | Double-entry posting for Invoices & Payments, Real-time P&L/BS |
| **Workflow Validation**| ✅ Verified | v1.0.0 | **3/3 Workflows Passing**: Meridian, Lakshmi's Kitchen, ABC Trading |
| **InvoiceNow** | ✅ Complete | v1.0.0 | XML Generation, Storecove AP Integration, Auto-transmit |
| **Security** | ✅ Complete | v1.0.0 | Rate Limiting, CSP Headers, CORS Authentication Fix |
| **Banking** | ✅ Complete | v1.3.0 | Full Reconciliation UI, CSV Import (Case-Insensitive) |
| **Frontend** | ✅ Complete | v0.1.2 | Next.js 16, App Router, Dynamic Org Context |

---

# Major Milestone: Complete SMB Lifecycle Validation ✅ COMPLETE (2026-03-10)

## Executive Summary
Successfully executed and verified three distinct Singapore SMB workflows, covering everything from sole proprietorship smoke tests to full 12-month corporate accounting cycles for private limited companies. This marks the definitive readiness of the LedgerSG engine for production use.

### Key Achievements

#### 1. "Lakshmi's Kitchen" Workflow (Workflow 1) ✅ VERIFIED
- **Complexity**: 12-month financial year for a Private Limited company.
- **Coverage**: Capital injection, asset purchase, operational revenue, and bank reconciliation.
- **Result**: Successfully aggregated a Net Profit of **S$22,450.00** from live ledger entries.
- **Validation**: Verified that multi-director equity and fixed asset tracking work seamlessly.

#### 2. "ABC Trading" Workflow (Workflow 2) ✅ VERIFIED
- **Complexity**: Single-month smoke test for a Sole Proprietorship.
- **Coverage**: Core sales-to-payment cycle.
- **Result**: Successfully verified a Net Profit of **S$3,000.00**.

#### 3. Core Engine Hardening (Refinement) ✅ FIXED
- **Journal Posting**: Fixed a critical `FieldError` where `JournalService` attempted to filter by a non-existent `is_voided` column in the document line table.
- **Peppol Alignment**: Resolved a `ProgrammingError` where `OrganisationPeppolSettings` incorrectly inherited timestamp fields (`created_at`/`updated_at`) that are absent in the SQL schema.
- **Schema Alignment**: These fixes further solidified the "SQL-First" mandate, ensuring Django models never request columns not explicitly defined in `database_schema.sql`.

### Lessons Learned & Pitfalls

1.  **The "Ghost Column" Trap**: Even with `managed=False`, Django models can "hallucinate" columns if they inherit from base classes like `TenantModel` that include timestamp or audit fields not present in the specific SQL table. **Always verify inheritance against the DDL.**
2.  **Sequential Integrity**: The mandatory `/approve/` step is the heartbeat of the system. Without it, the General Ledger remains empty. This design choice effectively separates "Operational Drafts" from "Financial Records."
3.  **Conflict Resolution**: Recent changes to remove `is_voided` and timestamp fields from models were corrective alignments. They **do not conflict** with the Meridian (Workflow 3) remediations; rather, they provide the missing structural integrity required for those features to operate at scale.

---

## Troubleshooting Guide (Updated)

**Problem**: `django.db.utils.ProgrammingError: column X does not exist`
- **Cause**: Model inheritance (e.g., `TenantModel`) adding fields like `created_at` to a table that doesn't have them in SQL.
- **Solution**: Change model inheritance to `models.Model` or a lighter base class that matches the SQL schema exactly.

**Problem**: `django.core.exceptions.FieldError: Cannot resolve keyword 'is_voided'`
- **Cause**: A service layer query is attempting to filter by a field that exists in the database schema but is missing from the Django model definition (or vice versa).
- **Solution**: Synchronize the model and the SQL DDL. In LedgerSG, the SQL DDL is the absolute source of truth.

**Problem**: Net Profit shows 0.0000 despite having paid invoices.
- **Cause**: Invoices were paid but never **Approved**. Payment records link to documents, but only Approval triggers the Revenue/AR journal entries.
- **Solution**: Ensure the `/approve/` endpoint is called before recording payments.
