# API Workflow Examples & Tips Guide

## For Accounting AI Agents — Singapore SMBs (Q1 2026 Validation)

**Version:** 1.1.0
**Last Updated:** 2026-03-10
**Status:** ✅ Production Ready — Validated Against SMB Workflow — Ledger Posting Active
**Supplements:** [`API_CLI_Usage_Guide.md`](./API_CLI_Usage_Guide.md)

---

## 🎉 Recent Milestone: SMB Workflow Remediation ✅ COMPLETE (2026-03-10)

### What Was Fixed & Learned

| Achievement | Impact |
|:---|:---|
| **Automatic Ledger Posting** | Approving an invoice or making a payment now correctly creates `journal.entry` and `journal.line` records. |
| **Response Wrapper Consistency** | Verified that all list responses (Accounts, Tax Codes, Contacts) use the `{ "data": [...] }` pattern. |
| **Field Name Alignment** | Fixed mismatches: `is_bank`, `total_excl`, `total_incl`, and `gl_account` (for bank account creation). |
| **UUID Serialization** | Fixed 500 errors when retrieving detail objects containing UUIDs. |
| **CSV Robustness** | Bank import now handles mixed-case headers and various date formats. |

---

## 🚦 Step-by-Step Workflow Refinements

### Step 3: Chart of Accounts & Bank Account

#### 3.1 List Seeded Accounts (The "Data" Wrapper)

> **CRITICAL**: List responses are wrapped in a `data` key.

```bash
# Get Bank Account UUID (Code 1100)
BANK_GL_ID=$(curl -s -X GET "${API_BASE}/${ORG_ID}/accounts/?code=1100" \
  -H "Authorization: Bearer ${ACCESS_TOKEN}" | jq -r '.data[0].id')
```

#### 3.2 Create Bank Account (Field: `gl_account`)

> **⚠️ Note**: Use `gl_account` (not `gl_account_id`) when creating a bank account.

```bash
curl -s -X POST "${API_BASE}/${ORG_ID}/banking/bank-accounts/" \
  -H "Authorization: Bearer ${ACCESS_TOKEN}" \
  -H "Content-Type: application/json" \
  -d "{
    \"account_name\": \"DBS Business Account\",
    \"gl_account\": \"${BANK_GL_ID}\",
    ...
  }"
```

---

### Step 6: Daily Transactions (Side Effects)

#### 6.1 Create & Approve Sales Invoice

> **💡 Knowledge**: Creating an invoice defaults to `DRAFT`. It does NOT affect the ledger.
> You MUST call the `approve` endpoint to post the journal entries.

```bash
# 1. Create Draft
INV_ID=$(curl ... -d '{"document_type": "SALES_INVOICE", ...}' | jq -r '.id')

# 2. Approve (Triggers Ledger Posting)
curl -s -X POST "${API_BASE}/${ORG_ID}/invoicing/documents/${INV_ID}/approve/" \
  -H "Authorization: Bearer ${ACCESS_TOKEN}"
```

#### 6.2 Record & Allocate Payment

> **💡 Knowledge**: Recording a payment (`/receive/` or `/make/`) now also triggers an automatic ledger entry (Debit Bank, Credit AR/AP).

```bash
# 1. Record Payment (Posts to GL)
PAY_ID=$(curl ... -X POST "${API_BASE}/${ORG_ID}/banking/payments/receive/" | jq -r '.id')

# 2. Allocate to Invoice (Updates Document Status to PAID)
curl -s -X POST "${API_BASE}/${ORG_ID}/banking/payments/${PAY_ID}/allocate/" \
  -d "{ \"allocations\": [{ \"document_id\": \"$INV_ID\", \"allocated_amount\": \"3000.0000\" }] }"
```

---

## 🛠 Troubleshooting & Pitfalls

### "My Dashboard / Reports are Empty"
*   **Cause**: You have invoices, but they are all in `DRAFT` status.
*   **Solution**: Approve the invoices. The reporting engine only aggregates `POSTED` journal entries.

### "TypeError: Object of type UUID is not JSON serializable"
*   **Status**: ✅ Fixed in codebase (2026-03-10).
*   **Context**: Occurred on `/accounts/{id}/` or `/tax-codes/{id}/` lookups.

### CSV Header Sensitivity
*   **Tip**: The system now supports "Date", "DATE", or "date". However, for the most reliable results, stick to the expected schema: `transaction_date`, `amount`, `description`.

### contact_type Constraint
*   **Tip**: If you see an IntegrityError on `contact_type`, ensure your `ContactService` is up to date. The service should automatically set `CUSTOMER` or `SUPPLIER` based on your boolean flags.

---

## 📋 Completion Checklist for Agents

- [ ] Use `jq -r '.data[0].id'` for list lookups.
- [ ] Ensure all money strings have 4 decimal places (`"0.0000"`).
- [ ] Always `approve` documents to see financial impact.
- [ ] Use `gl_account` for Bank Account setup.
- [ ] Use `allocated_amount` in payment allocation payloads.

---

**END OF UPDATED GUIDE**
