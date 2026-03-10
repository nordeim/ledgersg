# 🇸🇬 LedgerSG — Complete Accounting Workflow Test Scenario
## Singapore Non-GST Registered SMB Validation & Usage Guide

**Version:** 3.0.0 (Post-Remediation)
**Date:** 2026-03-10  
**Purpose:** Codebase Validation + AI Agent Usage Guide  
**Compliance:** IRAS 2026, SFRS for Small Entities

---

## 📋 Executive Summary

This document provides a **complete, end-to-end accounting workflow** for a typical Singapore non-GST registered small business using LedgerSG. It serves dual purposes:

1. **Validation Test Suite** — Verify all backend API endpoints work correctly
2. **AI Agent Usage Guide** — Step-by-step instructions for accounting automation

**Business Profile:**
| Attribute | Value |
|-----------|-------|
| Company Name | ABC Trading (Sole Proprietorship) |
| UEN | T26SS0001A |
| GST Status | **Not Registered** (Turnover < S$1M) |
| Financial Year | Calendar Year (Jan-Dec) |
| Base Currency | SGD |
| Tax Code | **OS** (Out-of-Scope) for all transactions |
| Bank | DBS Business Account |

---

## 🔐 Section 1: Authentication & Security Setup

### 1.3 User Login

```bash
# POST /api/v1/auth/login/
LOGIN_RESPONSE=$(curl -s -X POST http://localhost:8000/api/v1/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{
    "email": "accountant@abctrading.sg",
    "password": "SecurePass123!"
  }')

# Note: Tokens are nested in the .tokens object
export ACCESS_TOKEN=$(echo $LOGIN_RESPONSE | jq -r '.tokens.access')
export REFRESH_TOKEN=$(echo $LOGIN_RESPONSE | jq -r '.tokens.refresh')
```

---

## 🏢 Section 2: Organisation Setup

### 2.4 Verify Chart of Accounts (The "Data" Wrapper)

```bash
# Get account IDs (Use .data[0].id for list responses)
export BANK_ACCOUNT_ID=$(curl -s "http://localhost:8000/api/v1/$ORG_ID/accounts/?code=1100" \
  -H "Authorization: Bearer $ACCESS_TOKEN" | jq -r '.data[0].id')

export REVENUE_ACCOUNT_ID=$(curl -s "http://localhost:8000/api/v1/$ORG_ID/accounts/?code=4000" \
  -H "Authorization: Bearer $ACCESS_TOKEN" | jq -r '.data[0].id')
```

---

## 🏦 Section 3: Bank Account Setup

### 3.1 Create Bank Account (Field: `gl_account`)

```bash
# POST /api/v1/{orgId}/banking/bank-accounts/
curl -X POST http://localhost:8000/api/v1/$ORG_ID/banking/bank-accounts/ \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "account_name": "DBS Business Account",
    "bank_name": "DBS Bank Ltd",
    "account_number": "123-456789-001",
    "bank_code": "7171",
    "currency": "SGD",
    "gl_account": "'$BANK_ACCOUNT_ID'",
    "paynow_type": "UEN",
    "paynow_id": "T26SS0001A",
    "is_default": true,
    "opening_balance": "0.0000",
    "opening_balance_date": "2026-01-01"
  }'
```

---

## 📄 Section 6: Sales Invoice (Revenue)

### 6.1 Create Sales Invoice (Field: `total_excl`)

```bash
# 1. Create Invoice (DRAFT)
INV_RESP=$(curl -s -X POST http://localhost:8000/api/v1/$ORG_ID/invoicing/documents/ \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "document_type": "SALES_INVOICE",
    "contact_id": "'$CUSTOMER_ID'",
    "issue_date": "2026-01-15",
    "due_date": "2026-01-15",
    "lines": [
      {
        "description": "Handmade crafts sale",
        "account_id": "'$REVENUE_ACCOUNT_ID'",
        "quantity": 1,
        "unit_price": "3000.0000",
        "tax_code_id": "'$OS_TAX_CODE_ID'"
      }
    ]
  }')
export INVOICE_ID=$(echo $INV_RESP | jq -r '.id')

# 2. Approve (CRITICAL: Triggers ledger posting)
curl -X POST http://localhost:8000/api/v1/$ORG_ID/invoicing/documents/$INVOICE_ID/approve/ \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```

---

## 💵 Section 7: Payment & Allocation

### 7.2 Allocate Payment (Field: `allocated_amount`)

```bash
# POST /api/v1/{orgId}/banking/payments/{id}/allocate/
curl -X POST http://localhost:8000/api/v1/$ORG_ID/banking/payments/$PAYMENT_ID/allocate/ \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "allocations": [
      {
        "document_id": "'$INVOICE_ID'",
        "allocated_amount": "3000.0000"
      }
    ]
  }'
```

---

## 🏦 Section 10: Bank Reconciliation

### 10.1 Import Bank Statement (Header Robustness Verified)

```bash
# Importer handles "Date", "Amount", "Description" variants
curl -X POST http://localhost:8000/api/v1/$ORG_ID/banking/bank-transactions/import/ \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -F "file=@/tmp/bank_statement_jan.csv" \
  -F "bank_account_id=$BANK_ACCOUNT_UUID"
```

---

## 📊 Section 11: Financial Reports

### 11.3 Generate Financial Reports (P&L)

```bash
# Queries the live ledger posting engine
curl -X GET "http://localhost:8000/api/v1/$ORG_ID/reports/reports/financial/?report_type=profit_loss&start_date=2026-01-01&end_date=2026-01-31" \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```

---

## 🔒 Section 14: Security & Compliance

### 14.4 Test Decimal Precision (No Floats)

```bash
# Attempt to use float (100.5) instead of string ("100.5000")
# Expected Response: 400 Bad Request
```

---

## ✅ Section 19: Completion Sign-Off

**Test Status:** ✅ **SUCCESSFULLY VALIDATED** (2026-03-10)

The LedgerSG accounting engine is now fully verified against the single-month ABC Trading workflow. All logic gaps in journal posting and field mismatches have been remediated.
