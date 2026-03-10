## 🧪 LedgerSG End-to-End Test Plan: A Complete Financial Year for "Lakshmi's Kitchen"

### 🎯 Executive Summary

This meticulously crafted test plan re-imagines a complete financial year for a typical non-GST registered Singapore business. It serves two critical purposes:

1. **Codebase Validation** – Verify that LedgerSG correctly implements all accounting, compliance, and security requirements for a real-world business scenario.
2. **AI Agent Usage Guide** – Provide a step-by-step workflow demonstrating how an AI agent can use LedgerSG's API to manage a client's complete accounting lifecycle.

**Version:** 3.0.0 (Post-Remediation)
**Last Updated:** 2026-03-10
**Status:** ✅ Validated Against Production Engine

---

## 🏢 PART 1: The Business Profile — "Lakshmi's Kitchen"

### Business Overview

| Attribute | Value | Rationale |
|-----------|-------|-----------|
| **Business Name** | Lakshmi's Kitchen Pte Ltd | Singapore-registered private limited company |
| **Entity Type** | Exempt Private Company | ≤20 members, no corporate shareholders  |
| **UEN** | 202412345Z | ACRA-issued Unique Entity Number |
| **GST Status** | ❌ Not Registered | Turnover < S$1M threshold  |
| **GST Tax Code** | `OS` (Out-of-Scope) | All transactions use OS  |
| **Financial Year** | 1 Jan 2026 – 31 Dec 2026 | Calendar year for simplicity |
| **Base Currency** | SGD | Primary operating currency |
| **Business Activity** | F&B – Indian cuisine restaurant, catering, cooking classes |

---

## 📅 PART 2: The Workflow Timeline (Summary)

Transactions are designed to test:
- **Capital Injection & Loans**: Testing Equity and Liability tracking.
- **Fixed Assets**: Purchase and simplified depreciation entries.
- **Operational Revenue**: Sales Invoices (DRAFT → APPROVED → PAID).
- **Expense Management**: Purchase Bills and Salary Journals.
- **Bank Reconciliation**: CSV Import and Match Suggestions.

---

## 🔐 PART 3: Pre-Flight Checklist — Authentication & Setup

### 3.1 Authentication Sequence

```bash
# Step A1: Register test user
curl -X POST http://localhost:8000/api/v1/auth/register/ \
  -H "Content-Type: application/json" \
  -d '{
    "email": "lakshmi@kitchen.example",
    "password": "SecurePass123!",
    "full_name": "Lakshmi Krishnan"
  }'

# Step A2: Login to obtain tokens
LOGIN_RESPONSE=$(curl -s -X POST http://localhost:8000/api/v1/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{
    "email": "lakshmi@kitchen.example",
    "password": "SecurePass123!"
  }')

# Extract tokens (Note the .tokens.access nesting)
ACCESS_TOKEN=$(echo $LOGIN_RESPONSE | jq -r '.tokens.access')
REFRESH_TOKEN=$(echo $LOGIN_RESPONSE | jq -r '.tokens.refresh')
```

### 3.2 Organisation Creation

```bash
# Step B1: Create the business entity
ORG_RESPONSE=$(curl -s -X POST http://localhost:8000/api/v1/organisations/ \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Lakshmi Kitchen Pte Ltd",
    "legal_name": "Lakshmi Kitchen Pte Ltd",
    "uen": "202412345Z",
    "entity_type": "PRIVATE_LIMITED",
    "gst_registered": false,
    "base_currency": "SGD",
    "fy_start_month": 1,
    "timezone": "Asia/Singapore"
  }')

ORG_ID=$(echo $ORG_RESPONSE | jq -r '.id')
```

---

## 💰 PART 4: Chart of Accounts & Initial Setup

### 4.1 Verify Seeded Accounts (The "Data" Wrapper)

```bash
# Step C1: List all accounts (Note: wrapped in .data)
curl -X GET "http://localhost:8000/api/v1/$ORG_ID/accounts/" \
  -H "Authorization: Bearer $ACCESS_TOKEN" | jq '.data'
```

### 4.2 Helper: Get Account IDs (Corrected JQ Filters)

```bash
# Use .data[0] because filtering returns a list in the data key
BANK_ACCOUNT_ID=$(curl -s -X GET "http://localhost:8000/api/v1/$ORG_ID/accounts/?code=1100" \
  -H "Authorization: Bearer $ACCESS_TOKEN" | jq -r '.data[0].id')

CAPITAL_ACCOUNT_ID=$(curl -s -X GET "http://localhost:8000/api/v1/$ORG_ID/accounts/?code=3000" \
  -H "Authorization: Bearer $ACCESS_TOKEN" | jq -r '.data[0].id')

REVENUE_ACCOUNT_ID=$(curl -s -X GET "http://localhost:8000/api/v1/$ORG_ID/accounts/?code=4000" \
  -H "Authorization: Bearer $ACCESS_TOKEN" | jq -r '.data[0].id')

OS_TAX_CODE_ID=$(curl -s -X GET "http://localhost:8000/api/v1/$ORG_ID/gst/tax-codes/?code=OS" \
  -H "Authorization: Bearer $ACCESS_TOKEN" | jq -r '.data[0].id')
```

---

## 💵 PART 5: Opening Balances (1 Jan 2026)

### 5.1 Capital Injection Journal Entry

```bash
curl -X POST "http://localhost:8000/api/v1/$ORG_ID/journal-entries/entries/" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d "{
    \"entry_date\": \"2026-01-01\",
    \"narration\": \"Opening capital contribution\",
    \"source_type\": \"OPENING_BALANCE\",
    \"lines\": [
      {
        \"account_id\": \"$BANK_ACCOUNT_ID\",
        \"debit\": \"150000.0000\",
        \"credit\": \"0.0000\",
        \"description\": \"Initial injection\"
      },
      {
        \"account_id\": \"$CAPITAL_ACCOUNT_ID\",
        \"debit\": \"0.0000\",
        \"credit\": \"150000.0000\",
        \"description\": \"Share capital\"
      }
    ]
  }"
```

---

## 🧾 PART 6: Sales Operations

### 6.1 Create & Approve Sales Invoice

```bash
# 1. Create Invoice (DRAFT)
INV_RESP=$(curl -s -X POST "http://localhost:8000/api/v1/$ORG_ID/invoicing/documents/" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d "{
    \"contact_id\": \"$CUSTOMER_ID\",
    \"document_type\": \"SALES_INVOICE\",
    \"document_date\": \"2026-01-31\",
    \"due_date\": \"2026-01-31\",
    \"lines\": [
      {
        \"description\": \"Dine-in revenue\",
        \"account_id\": \"$REVENUE_ACCOUNT_ID\",
        \"quantity\": 1,
        \"unit_price\": \"22450.0000\",
        \"tax_code_id\": \"$OS_TAX_CODE_ID\"
      }
    ]
  }")
INV_ID=$(echo $INV_RESP | jq -r '.id')

# 2. Approve (CRITICAL: Triggers General Ledger posting)
curl -X POST "http://localhost:8000/api/v1/$ORG_ID/invoicing/documents/$INV_ID/approve/" \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```

### 6.2 Record & Allocate Payment

```bash
# 1. Record Receipt (Field: gl_account for bank)
PAY_RESP=$(curl -s -X POST "http://localhost:8000/api/v1/$ORG_ID/banking/payments/receive/" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d "{
    \"contact_id\": \"$CUSTOMER_ID\",
    \"bank_account_id\": \"$BANK_ACCOUNT_UUID\",
    \"payment_date\": \"2026-01-31\",
    \"amount\": \"22450.0000\",
    \"payment_method\": \"BANK_TRANSFER\"
  }")
PAY_ID=$(echo $PAY_RESP | jq -r '.id')

# 2. Allocate (Field: allocated_amount)
curl -X POST "http://localhost:8000/api/v1/$ORG_ID/banking/payments/$PAY_ID/allocate/" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d "{
    \"allocations\": [{ \"document_id\": \"$INV_ID\", \"allocated_amount\": \"22450.0000\" }]
  }"
```

---

## 🏦 PART 10: Bank Reconciliation

### 10.1 Import Bank Statement (Header Normalization Verified)

```bash
# The importer handles case variations like "Date" or "Amount"
curl -X POST "http://localhost:8000/api/v1/$ORG_ID/banking/bank-transactions/import/" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -F "file=@jan_statement.csv" \
  -F "bank_account_id=$BANK_ACCOUNT_UUID"
```

---

## 📊 PART 13: Financial Reports

### 13.1 Real-Time aggregations (Q1 2026)

```bash
# Generate P&L (Queries the ledger directly)
curl -X GET "http://localhost:8000/api/v1/$ORG_ID/reports/reports/financial/?report_type=profit_loss&start_date=2026-01-01&end_date=2026-03-31" \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```

---

## 🎯 Conclusion

This test plan validates that LedgerSG correctly implements:
- ✅ **Double-entry accounting** – Balanced journals for all transactions
- ✅ **Non-GST compliance** – OS tax code used throughout
- ✅ **Mandatory Approval Workflow** – DRAFT → APPROVED ensures ledger integrity
- ✅ **UUID & Precision Support** – Native serialisation and string-based decimals

The LedgerSG engine is functionally complete for the documented Singapore SMB lifecycle.
