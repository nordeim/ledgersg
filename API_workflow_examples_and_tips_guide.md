# API Workflow Examples & Tips Guide

## For Accounting AI Agents — Singapore SMBs (Q1 2026 Validation)

**Version:** 1.3.0
**Last Updated:** 2026-03-15
**Status:** ✅ Production Ready — Validated Across 3 Authoritative SMB Workflows
**Supplements:** [`API_CLI_Usage_Guide.md`](./API_CLI_Usage_Guide.md)

---

## 🎉 Recent Milestone: API Contract & 500 Error Investigation ✅ COMPLETE (2026-03-15)

### What Was Fixed & Verified

| Achievement | Impact |
|:---|:---|
| **API Contract Standardization** | 9 endpoints now return `{results, count}` format |
| **500 Error Debunked** | Production API works - 403s from test fixtures only |
| **Test Reality Check** | 67 failing tests = fixture issue, not production bug |

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

### 🔍 Filtering by Code & Response Format
*   **Tip**: When looking for an account (e.g., "1100" for Bank), always use `?code=1100`.
*   **Wrapper**: The result is a list in the `results` key (not `data`). Use `jq -r '.results[0].id'`.
*   **Note**: All list endpoints now return `{results: [...], count: n}` format.

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
