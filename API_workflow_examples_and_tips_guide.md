# API Workflow Examples & Tips Guide

## For Accounting AI Agents — Singapore SMBs (Q1 2026 Validation)

**Version:** 1.2.0
**Last Updated:** 2026-03-10
**Status:** ✅ Production Ready — Validated Across 3 Authoritative SMB Workflows
**Supplements:** [`API_CLI_Usage_Guide.md`](./API_CLI_Usage_Guide.md)

---

## 🎉 Recent Milestone: Full Workflow Verification ✅ COMPLETE (2026-03-10)

### What Was Fixed & Hardened (Workflow 1 & 2)

| Achievement | Impact |
|:---|:---|
| **SQL-First Enforcement** | Removed "Ghost Columns" from models that didn't exist in SQL (e.g., `OrganisationPeppolSettings`). |
| **Journal Logic Fix** | Fixed `is_voided` filter error in the ledger posting loop. |
| **Corporate Lifecycle** | Verified multi-director equity injection and 12-month P&L aggregation. |
| **Sole Prop Smoke Test** | Verified core Sales → Approval → Payment cycle for micro-entities. |

---

## 🛠 Troubleshooting & Pitfalls (Workflow Insights)

### 👻 The "Ghost Column" Error
*   **Symptom**: `ProgrammingError: column ... created_at does not exist`.
*   **Cause**: You are calling an endpoint whose model inherits from `TenantModel` or `BaseModel`, but the SQL table in `database_schema.sql` doesn't have those columns.
*   **Fix**: Update the Django model to inherit from `models.Model` and match the DDL exactly.

### 🚫 The "Zero Profit" Illusion
*   **Symptom**: You've recorded payments, but the P&L shows zero net profit.
*   **Cause**: You skipped the `/approve/` step for the invoice.
*   **Rule**: In LedgerSG, **Approval is the Trigger**. Payments link to documents, but they do not create Revenue entries. Only Invoice Approval posts to the Revenue/AR accounts.

### 🔍 Filtering by Code
*   **Tip**: When looking for an account (e.g., "1100" for Bank), always use `?code=1100`.
*   **Wrapper**: The result is a list in the `data` key. Use `jq -r '.data[0].id'`.

---

## 📋 Standard Workflow Template (Bug-Free)

For a successful accounting automation, follow this sequence exactly:

1.  **Register & Login** (Tokens are in `.tokens.access`).
2.  **Create Organisation** (Set `gst_registered` correctly).
3.  **Fetch Bank Account ID** (Use `GET /accounts/?code=1100`).
4.  **Create Bank Account** (Field name is `gl_account`, NOT `gl_account_id`).
5.  **Create Contact** (Check constraints are auto-handled by `ContactService`).
6.  **Create Invoice** (Defaults to `DRAFT`).
7.  **Approve Invoice** (MANDATORY: `POST /approve/`).
8.  **Record Payment** (Triggers Bank/AR journal entry).
9.  **Generate Report** (Queries POSTED entries only).

---

**END OF UPDATED GUIDE**
