# API Workflow Examples & Tips Guide

## For Accounting AI Agents — Non-GST Registered Singapore SMBs

**Version:** 1.0.0
**Last Updated:** 2026-03-08
**Status:** ✅ Production Ready — Validated Against Codebase — RLS Fixed
**Supplements:** [`API_CLI_Usage_Guide.md`](./API_CLI_Usage_Guide.md)

---

## 🎉 Recent Milestone: RLS & View Layer Fixes ✅ COMPLETE (2026-03-08)

### What Was Fixed

| Fix | Status | Impact |
|-----|--------|--------|
| **SQL NULL Syntax** | ✅ Fixed | `SET LOCAL app.current_org_id = ''` (PostgreSQL requires strings, not NULL) |
| **Test Assertions** | ✅ Fixed | Changed `response.data` → `json.loads(response.content)` (3 locations) |
| **Org Membership Fixtures** | ✅ Fixed | Added Organisation, Role, UserOrganisation test fixtures |
| **UUID Double Conversion** | ✅ Fixed | Removed 20+ redundant `UUID(org_id)` calls in banking, gst, journal views |
| **Error Logging** | ✅ Enhanced | Added proper exception logging to `wrap_response` decorator |
| **Test Results** | ✅ **6/6 Passing** | 100% success rate on RLS + endpoint tests |

### Root Cause: UUID Double Conversion

**Problem:** Django's `<uuid:org_id>` path converter automatically converts URL parameters to UUID objects, but views were trying to convert them again with `UUID(org_id)`.

**Error Message:**
```
'UUID' object has no attribute 'replace'
```

**Solution:** Removed all redundant `UUID(org_id)` calls:
- `apps/banking/views.py`: Multiple occurrences
- `apps/gst/views.py`: 13 occurrences
- `apps/journal/views.py`: 7 occurrences

### Lessons Learned

1. **Django URL Path Converters**: `<uuid:org_id>` automatically converts to UUID — no need for `UUID()` wrapper
2. **PostgreSQL SET LOCAL**: Requires string values, not SQL NULL keyword
3. **JsonResponse**: Has `.content` (bytes), not `.data` attribute
4. **TDD Methodology**: RED → GREEN → REFACTOR cycle successfully identified all root causes

### Files Modified

| File | Change |
|------|--------|
| `common/middleware/tenant_context.py` | Fixed SQL NULL syntax |
| `common/views.py` | Enhanced error logging |
| `tests/middleware/test_rls_context.py` | Complete rewrite with fixtures |
| `apps/banking/views.py` | Removed UUID() calls |
| `apps/gst/views.py` | Removed UUID() calls (13) |
| `apps/journal/views.py` | Removed UUID() calls (7) |

### Documentation Created

- `TDD_RLS_FIXES_SUBPLAN.md` — Comprehensive TDD plan for RLS fixes
- `TDD_VIEW_LAYER_FIXES_SUBPLAN.md` — TDD plan for view layer UUID fixes
- `TDD_IMPLEMENTATION_REPORT.md` — Implementation details
- `RLS_FIX_VALIDATION_REPORT.md` — Validation evidence

---

## 📋 Table of Contents

1. [Introduction](#introduction)
2. [Quick Start (5-Minute Setup)](#quick-start-5-minute-setup)
3. [Scenario: ABC Trading](#scenario-abc-trading)
4. [Step-by-Step Workflow](#step-by-step-workflow)
   - Step 1: Authentication & Token Management
   - Step 2: Organisation Setup
   - Step 3: Chart of Accounts & Bank Account
   - Step 4: Contact Management
   - Step 5: Opening Balances (Journal Entry)
   - Step 6: Daily Transactions (Invoices & Payments)
   - Step 7: Bank Reconciliation
   - Step 8: Financial Reports & PDF Generation
5. [Helper Functions](#helper-functions)
6. [CORS & Backend Tips](#cors--backend-tips)
7. [IRAS Compliance Checklist](#iras-compliance-checklist)
8. [Troubleshooting](#troubleshooting)
9. [Appendix](#appendix)

---

## 🎯 Introduction

### Purpose

This guide provides a **practical, step-by-step workflow** for using LedgerSG's API to manage the accounts of a small Singapore business that is **NOT GST-registered**. It is designed for accounting AI agents who need to:

- Upload accounting data to PostgreSQL via the API
- Generate P&L and Balance Sheet reports
- Export IRAS-required outputs as PDFs
- Navigate CORS and backend authentication requirements

**Without needing to study the actual codebase.**

### When to Use This Guide

| Use This Guide | Use API_CLI_Usage_Guide.md |
|----------------|---------------------------|
| ✅ First-time setup for non-GST business | ✅ Complete endpoint reference |
| ✅ Typical monthly accounting workflow | ✅ All 87+ endpoints documented |
| ✅ Quick-start with working examples | ✅ Advanced features (GST, Peppol) |
| ✅ AI agent onboarding | ✅ Deep technical specifications |

### Prerequisites

```bash
# Required tools
curl          # For API examples
jq            # For JSON parsing
python3       # For PDF generation scripts
playwright    # For browser automation (optional)

# Environment variables
export API_BASE="http://localhost:8000/api/v1"
export EMAIL="accountant@abctrading.com"
export PASSWORD="secure_password_here"
```

**Setup:**
```bash
# Create a .env file
cat > .env << 'EOF'
API_BASE=http://localhost:8000/api/v1
EMAIL=accountant@abctrading.com
PASSWORD=your_secure_password
EOF

# Source it
source .env
```

---

## 🚀 Quick Start (5-Minute Setup)

### Step 0: Verify Backend is Running

```bash
# Health check
curl -s http://localhost:8000/api/v1/health/ | jq '.'

# Expected response:
{
  "status": "healthy",
  "database": "connected",
  "version": "1.0.0"
}
```

### Step 1: Login and Store Tokens

```bash
#!/bin/bash
# login.sh

LOGIN_RESPONSE=$(curl -s -X POST "${API_BASE}/auth/login/" \
  -H "Content-Type: application/json" \
  -d "{\"email\": \"${EMAIL}\", \"password\": \"${PASSWORD}\"}")

# Extract and store tokens
export ACCESS_TOKEN=$(echo $LOGIN_RESPONSE | jq -r '.tokens.access')
export REFRESH_TOKEN=$(echo $LOGIN_RESPONSE | jq -r '.tokens.refresh')

echo "✅ Logged in successfully"
echo "Access token expires: $(echo $LOGIN_RESPONSE | jq -r '.tokens.access_expires')"
```

### Step 2: Get or Create Organisation

```bash
#!/bin/bash
# get_org.sh

# List existing organisations
ORGS=$(curl -s -X GET "${API_BASE}/organisations/" \
  -H "Authorization: Bearer ${ACCESS_TOKEN}")

ORG_COUNT=$(echo $ORGS | jq '.count')

if [ "$ORG_COUNT" -eq 0 ]; then
  echo "📝 No organisation found. Creating one..."

  ORG_RESPONSE=$(curl -s -X POST "${API_BASE}/organisations/" \
    -H "Authorization: Bearer ${ACCESS_TOKEN}" \
    -H "Content-Type: application/json" \
    -d '{
      "name": "ABC Trading",
      "legal_name": "ABC Trading",
      "entity_type": "SOLE_PROPRIETORSHIP",
      "uen": "T26SS0001A",
      "gst_registered": false,
      "base_currency": "SGD",
      "fy_start_month": 1,
      "timezone": "Asia/Singapore"
    }')

  export ORG_ID=$(echo $ORG_RESPONSE | jq -r '.id')
  echo "✅ Organisation created: $ORG_ID"
else
  export ORG_ID=$(echo $ORGS | jq -r '.data[0].id')
  echo "✅ Using existing organisation: $ORG_ID"
fi

# Save for later use
echo "export ORG_ID=\"$ORG_ID\"" >> .env.local
```

---

## 🏢 Scenario: ABC Trading

### Business Profile

| Attribute | Value |
|-----------|-------|
| **Business Type** | Sole Proprietorship |
| **GST Status** | ❌ Not Registered (Turnover < S$1M) |
| **Base Currency** | SGD |
| **Bank Account** | DBS Business Account |
| **Financial Year** | Calendar Year (Jan-Dec) |
| **Tax Codes** | `OS` (Out-of-Scope) for all transactions |

### January 2026 Transactions

| Date | Transaction | Amount | Type |
|------|-------------|--------|------|
| 1 Jan | Owner capital injection | S$10,000 | Opening Balance |
| 15 Jan | Sales to customer | S$3,000 | Sales Invoice |
| 20 Jan | Office rent payment | S$1,500 | Purchase Invoice |
| 25 Jan | Office supplies | S$200 | Purchase Invoice |
| 31 Jan | Bank reconciliation | — | Reconciliation |

### Expected Outputs

- ✅ Profit & Loss Statement (January 2026)
- ✅ Balance Sheet (as at 31 Jan 2026)
- ✅ PDF reports for IRAS record-keeping (5-year retention)

### Key Chart of Accounts

| Code | Name | Type |
|------|------|------|
| 1100 | Bank Account | Asset |
| 3000 | Owner's Capital | Equity |
| 4000 | Sales Revenue | Revenue |
| 6100 | Rent Expense | Expense |
| 6200 | Office Supplies | Expense |

---

## 🚦 Step-by-Step Workflow

---

### Step 1: Authentication & Token Management

#### 1.1 Login

```bash
#!/bin/bash
# step1_login.sh

LOGIN_RESPONSE=$(curl -s -X POST "${API_BASE}/auth/login/" \
  -H "Content-Type: application/json" \
  -d "{
    \"email\": \"${EMAIL}\",
    \"password\": \"${PASSWORD}\"
  }")

# Validate response
if echo $LOGIN_RESPONSE | jq -e '.tokens.access' > /dev/null; then
  export ACCESS_TOKEN=$(echo $LOGIN_RESPONSE | jq -r '.tokens.access')
  export REFRESH_TOKEN=$(echo $LOGIN_RESPONSE | jq -r '.tokens.refresh')
  echo "✅ Login successful"
else
  echo "❌ Login failed: $(echo $LOGIN_RESPONSE | jq -r '.error.message')"
  exit 1
fi
```

#### 1.2 Token Refresh (Before 15-Minute Expiry)

```bash
#!/bin/bash
# refresh_token.sh

REFRESH_RESPONSE=$(curl -s -X POST "${API_BASE}/auth/refresh/" \
  -H "Content-Type: application/json" \
  -d "{\"refresh\": \"${REFRESH_TOKEN}\"}")

if echo $REFRESH_RESPONSE | jq -e '.tokens.access' > /dev/null; then
  export ACCESS_TOKEN=$(echo $REFRESH_RESPONSE | jq -r '.tokens.access')
  export REFRESH_TOKEN=$(echo $REFRESH_RESPONSE | jq -r '.tokens.refresh')
  echo "✅ Token refreshed"
else
  echo "❌ Refresh failed. Re-login required."
  exit 1
fi
```

#### 1.3 Playwright Example (Browser Automation)

```typescript
// playwright-auth.ts
import { chromium, Browser, Page } from 'playwright';

export async function authenticateAndStoreTokens() {
  const browser: Browser = await chromium.launch({ headless: true });
  const page: Page = await browser.newPage();

  // Navigate to login
  await page.goto('http://localhost:3000/login');

  // Fill credentials
  await page.fill('input[name="email"]', 'accountant@abctrading.com');
  await page.fill('input[name="password"]', 'secure_password_here');

  // Submit and wait for redirect
  await page.click('button[type="submit"]');
  await page.waitForURL('**/dashboard');

  // Extract tokens from cookies (refresh token is HttpOnly)
  const cookies = await page.context().cookies();
  const refreshToken = cookies.find(c => c.name === 'refresh_token');

  console.log('✅ Authentication complete');
  console.log('Refresh token:', refreshToken?.value);

  await browser.close();
  return { refreshToken };
}

// Usage
// const tokens = await authenticateAndStoreTokens();
```

> **⚠️ Critical Tip:** Access tokens expire in **15 minutes**. Always implement refresh logic before token expiry. Store refresh tokens securely (environment variables, never in code).

---

### Step 2: Organisation Setup

#### 2.1 Create Organisation

```bash
#!/bin/bash
# step2_create_org.sh

ORG_RESPONSE=$(curl -s -X POST "${API_BASE}/organisations/" \
  -H "Authorization: Bearer ${ACCESS_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "ABC Trading",
    "legal_name": "ABC Trading",
    "entity_type": "SOLE_PROPRIETORSHIP",
    "uen": "T26SS0001A",
    "gst_registered": false,
    "base_currency": "SGD",
    "fy_start_month": 1,
    "timezone": "Asia/Singapore",
    "address_line_1": "123 Orchard Road",
    "city": "Singapore",
    "postal_code": "238858",
    "country": "SG",
    "email": "contact@abctrading.com",
    "phone": "+65 6123 4567"
  }')

# Validate and extract org_id
if echo $ORG_RESPONSE | jq -e '.id' > /dev/null; then
  export ORG_ID=$(echo $ORG_RESPONSE | jq -r '.id')
  echo "✅ Organisation created: $ORG_ID"
  echo "export ORG_ID=\"$ORG_ID\"" >> .env.local
else
  echo "❌ Organisation creation failed"
  echo $ORG_RESPONSE | jq '.'
  exit 1
fi
```

#### 2.2 Verify Organisation Settings

```bash
#!/bin/bash
# verify_org.sh

ORG_DETAILS=$(curl -s -X GET "${API_BASE}/${ORG_ID}/" \
  -H "Authorization: Bearer ${ACCESS_TOKEN}")

echo $ORG_DETAILS | jq '{
  name: .name,
  gst_registered: .gst_registered,
  base_currency: .base_currency,
  fy_start_month: .fy_start_month
}'

# Verify GST is FALSE for non-GST business
GST_STATUS=$(echo $ORG_DETAILS | jq -r '.gst_registered')
if [ "$GST_STATUS" = "false" ]; then
  echo "✅ GST status confirmed: NOT registered"
else
  echo "⚠️ WARNING: Organisation is GST registered!"
fi
```

---

### Step 3: Chart of Accounts & Bank Account

#### 3.1 List Seeded Accounts

> **Note:** LedgerSG automatically seeds a standard Chart of Accounts when an organisation is created.

```bash
#!/bin/bash
# step3_list_accounts.sh

ACCOUNTS=$(curl -s -X GET "${API_BASE}/${ORG_ID}/accounts/" \
  -H "Authorization: Bearer ${ACCESS_TOKEN}")

# Display key accounts for non-GST business
echo $ACCOUNTS | jq '[.[] | select(
  .code == "1100" or
  .code == "3000" or
  .code == "4000" or
  .code == "6100" or
  .code == "6200"
) | {code, name, id, account_type_id}]'
```

#### 3.2 Helper: Get Account UUID by Code

```bash
#!/bin/bash
# get_account_id.sh

get_account_id() {
  local CODE=$1
  curl -s -X GET "${API_BASE}/${ORG_ID}/accounts/?code=${CODE}" \
    -H "Authorization: Bearer ${ACCESS_TOKEN}" | jq -r '.[0].id'
}

# Usage examples:
BANK_ACCOUNT_ID=$(get_account_id "1100")
CAPITAL_ACCOUNT_ID=$(get_account_id "3000")
SALES_ACCOUNT_ID=$(get_account_id "4000")
RENT_ACCOUNT_ID=$(get_account_id "6100")
SUPPLIES_ACCOUNT_ID=$(get_account_id "6200")

echo "Bank Account UUID: $BANK_ACCOUNT_ID"
echo "Capital Account UUID: $CAPITAL_ACCOUNT_ID"
echo "Sales Account UUID: $SALES_ACCOUNT_ID"
```

#### 3.3 Create Bank Account

> **⚠️ Critical:** Bank account must be created before recording payments or reconciliation.

```bash
#!/bin/bash
# step3_create_bank_account.sh

# First get the GL account UUID for bank (code 1100)
GL_ACCOUNT_ID=$(curl -s -X GET "${API_BASE}/${ORG_ID}/accounts/?code=1100" \
  -H "Authorization: Bearer ${ACCESS_TOKEN}" | jq -r '.[0].id')

BANK_RESPONSE=$(curl -s -X POST "${API_BASE}/${ORG_ID}/banking/bank-accounts/" \
  -H "Authorization: Bearer ${ACCESS_TOKEN}" \
  -H "Content-Type: application/json" \
  -d "{
    \"account_name\": \"DBS Business Account\",
    \"bank_name\": \"DBS Bank Ltd\",
    \"account_number\": \"123-456789-001\",
    \"bank_code\": \"7171\",
    \"currency\": \"SGD\",
    \"gl_account_id\": \"${GL_ACCOUNT_ID}\",
    \"is_active\": true,
    \"opening_balance\": \"0.0000\",
    \"paynow_type\": \"UEN\",
    \"paynow_id\": \"T26SS0001A\"
  }")

if echo $BANK_RESPONSE | jq -e '.id' > /dev/null; then
  export BANK_ACCOUNT_ID=$(echo $BANK_RESPONSE | jq -r '.id')
  echo "✅ Bank account created: $BANK_ACCOUNT_ID"
  echo "export BANK_ACCOUNT_ID=\"$BANK_ACCOUNT_ID\"" >> .env.local
else
  echo "❌ Bank account creation failed"
  echo $BANK_RESPONSE | jq '.'
  exit 1
fi
```

#### 3.4 Helper: Get Tax Code UUID

> **⚠️ Critical for Non-GST:** Use `OS` (Out-of-Scope) tax code for all transactions.

```bash
#!/bin/bash
# get_tax_code_id.sh

get_tax_code_id() {
  local CODE=$1
  curl -s -X GET "${API_BASE}/${ORG_ID}/gst/tax-codes/?code=${CODE}" \
    -H "Authorization: Bearer ${ACCESS_TOKEN}" | jq -r '.[0].id'
}

# For non-GST business, use OS (Out-of-Scope)
export OS_TAX_CODE_ID=$(get_tax_code_id "OS")
export NA_TAX_CODE_ID=$(get_tax_code_id "NA")

echo "OS Tax Code UUID: $OS_TAX_CODE_ID"
echo "NA Tax Code UUID: $NA_TAX_CODE_ID"
```

---

### Step 4: Contact Management

#### 4.1 Create Customer Contact

```bash
#!/bin/bash
# step4_create_customer.sh

CUSTOMER_RESPONSE=$(curl -s -X POST "${API_BASE}/${ORG_ID}/invoicing/contacts/" \
  -H "Authorization: Bearer ${ACCESS_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Cash Customer",
    "contact_type": "CUSTOMER",
    "is_customer": true,
    "is_supplier": false,
    "email": "customer@example.com",
    "phone": "+65 9123 4567",
    "country": "SG",
    "payment_terms_days": 0
  }')

if echo $CUSTOMER_RESPONSE | jq -e '.id' > /dev/null; then
  export CUSTOMER_ID=$(echo $CUSTOMER_RESPONSE | jq -r '.id')
  echo "✅ Customer created: $CUSTOMER_ID"
else
  echo "❌ Customer creation failed"
  exit 1
fi
```

#### 4.2 Create Supplier Contact

```bash
#!/bin/bash
# step4_create_supplier.sh

SUPPLIER_RESPONSE=$(curl -s -X POST "${API_BASE}/${ORG_ID}/invoicing/contacts/" \
  -H "Authorization: Bearer ${ACCESS_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Office Landlord Pte Ltd",
    "contact_type": "SUPPLIER",
    "is_customer": false,
    "is_supplier": true,
    "email": "billing@landlord.com.sg",
    "phone": "+65 6234 5678",
    "country": "SG",
    "payment_terms_days": 30
  }')

if echo $SUPPLIER_RESPONSE | jq -e '.id' > /dev/null; then
  export SUPPLIER_ID=$(echo $SUPPLIER_RESPONSE | jq -r '.id')
  echo "✅ Supplier created: $SUPPLIER_ID"
else
  echo "❌ Supplier creation failed"
  exit 1
fi
```

#### 4.3 List Contacts

```bash
#!/bin/bash
# list_contacts.sh

CONTACTS=$(curl -s -X GET "${API_BASE}/${ORG_ID}/invoicing/contacts/" \
  -H "Authorization: Bearer ${ACCESS_TOKEN}")

echo $CONTACTS | jq '.results[] | {id, name, contact_type, email}'
```

---

### Step 5: Opening Balances (Journal Entry)

#### 5.1 Create Opening Balance Journal Entry

> **⚠️ Critical:** Journal entries require **UUIDs** for `account_id`, NOT code strings.

> **Note:** `fiscal_period_id` is optional — the system auto-detects based on `entry_date`.

```bash
#!/bin/bash
# step5_opening_balance.sh

# Get account UUIDs
BANK_ACCOUNT_ID=$(curl -s -X GET "${API_BASE}/${ORG_ID}/accounts/?code=1100" \
  -H "Authorization: Bearer ${ACCESS_TOKEN}" | jq -r '.[0].id')

CAPITAL_ACCOUNT_ID=$(curl -s -X GET "${API_BASE}/${ORG_ID}/accounts/?code=3000" \
  -H "Authorization: Bearer ${ACCESS_TOKEN}" | jq -r '.[0].id')

# Create journal entry (no tax_code_id needed for journal lines)
JE_RESPONSE=$(curl -s -X POST "${API_BASE}/${ORG_ID}/journal-entries/entries/" \
  -H "Authorization: Bearer ${ACCESS_TOKEN}" \
  -H "Content-Type: application/json" \
  -d "{
    \"entry_date\": \"2026-01-01\",
    \"narration\": \"Opening capital contribution by owner\",
    \"source_type\": \"OPENING_BALANCE\",
    \"lines\": [
      {
        \"account_id\": \"${BANK_ACCOUNT_ID}\",
        \"debit\": \"10000.0000\",
        \"credit\": \"0.0000\",
        \"description\": \"Bank account opening balance\"
      },
      {
        \"account_id\": \"${CAPITAL_ACCOUNT_ID}\",
        \"debit\": \"0.0000\",
        \"credit\": \"10000.0000\",
        \"description\": \"Owner capital contribution\"
      }
    ]
  }")

if echo $JE_RESPONSE | jq -e '.id' > /dev/null; then
  echo "✅ Opening balance journal entry created"
  echo $JE_RESPONSE | jq '{id, entry_number, entry_date, narration}'
else
  echo "❌ Journal entry creation failed"
  echo $JE_RESPONSE | jq '.'
  exit 1
fi
```

> **💡 Tip:** All monetary amounts must be **strings with 4 decimal places** (e.g., `"10000.0000"` not `10000`).

> **💡 Tip:** Journal lines do NOT require `tax_code_id` — this field is only for invoice lines.

---

### Step 6: Daily Transactions (Invoices & Payments)

#### 6.1 Create Sales Invoice (15 Jan)

```bash
#!/bin/bash
# step6_create_sales_invoice.sh

# Get required UUIDs
CUSTOMER_ID=$(curl -s -X GET "${API_BASE}/${ORG_ID}/invoicing/contacts/?name=Cash%20Customer" \
  -H "Authorization: Bearer ${ACCESS_TOKEN}" | jq -r '.results[0].id')

SALES_ACCOUNT_ID=$(curl -s -X GET "${API_BASE}/${ORG_ID}/accounts/?code=4000" \
  -H "Authorization: Bearer ${ACCESS_TOKEN}" | jq -r '.[0].id')

OS_TAX_CODE_ID=$(curl -s -X GET "${API_BASE}/${ORG_ID}/gst/tax-codes/?code=OS" \
  -H "Authorization: Bearer ${ACCESS_TOKEN}" | jq -r '.[0].id')

# Create sales invoice
INVOICE_RESPONSE=$(curl -s -X POST "${API_BASE}/${ORG_ID}/invoicing/documents/" \
  -H "Authorization: Bearer ${ACCESS_TOKEN}" \
  -H "Content-Type: application/json" \
  -d "{
    \"contact_id\": \"${CUSTOMER_ID}\",
    \"document_type\": \"SALES_INVOICE\",
    \"issue_date\": \"2026-01-15\",
    \"due_date\": \"2026-01-15\",
    \"currency\": \"SGD\",
    \"reference\": \"Sale-001\",
    \"notes\": \"Handmade crafts sale\",
    \"lines\": [
      {
        \"description\": \"Handmade crafts sale\",
        \"quantity\": 1,
        \"unit_price\": \"3000.0000\",
        \"tax_code_id\": \"${OS_TAX_CODE_ID}\",
        \"account_id\": \"${SALES_ACCOUNT_ID}\"
      }
    ]
  }")

if echo $INVOICE_RESPONSE | jq -e '.id' > /dev/null; then
  export INVOICE_ID=$(echo $INVOICE_RESPONSE | jq -r '.id')
  export INVOICE_NUMBER=$(echo $INVOICE_RESPONSE | jq -r '.document_number')
  echo "✅ Sales invoice created: $INVOICE_NUMBER"

  # Approve invoice (posts to ledger)
  APPROVE_RESPONSE=$(curl -s -X POST "${API_BASE}/${ORG_ID}/invoicing/documents/${INVOICE_ID}/approve/" \
    -H "Authorization: Bearer ${ACCESS_TOKEN}")

  echo "✅ Invoice approved and posted to ledger"
else
  echo "❌ Invoice creation failed"
  echo $INVOICE_RESPONSE | jq '.'
  exit 1
fi
```

#### 6.2 Record Payment Received from Customer

> **⚠️ Critical:** Payment must be recorded separately, then allocated to invoice.

```bash
#!/bin/bash
# step6_record_payment_received.sh

# Get required UUIDs
CUSTOMER_ID=$(curl -s -X GET "${API_BASE}/${ORG_ID}/invoicing/contacts/?name=Cash%20Customer" \
  -H "Authorization: Bearer ${ACCESS_TOKEN}" | jq -r '.results[0].id')

BANK_ACCOUNT_ID=$(curl -s -X GET "${API_BASE}/${ORG_ID}/banking/bank-accounts/" \
  -H "Authorization: Bearer ${ACCESS_TOKEN}" | jq -r '.[0].id')

# Record payment received
PAYMENT_RESPONSE=$(curl -s -X POST "${API_BASE}/${ORG_ID}/banking/payments/receive/" \
  -H "Authorization: Bearer ${ACCESS_TOKEN}" \
  -H "Content-Type: application/json" \
  -d "{
    \"contact_id\": \"${CUSTOMER_ID}\",
    \"bank_account_id\": \"${BANK_ACCOUNT_ID}\",
    \"payment_date\": \"2026-01-15\",
    \"amount\": \"3000.0000\",
    \"payment_method\": \"BANK_TRANSFER\",
    \"payment_reference\": \"INV-${INVOICE_NUMBER}\",
    \"currency\": \"SGD\"
  }")

if echo $PAYMENT_RESPONSE | jq -e '.id' > /dev/null; then
  export PAYMENT_ID=$(echo $PAYMENT_RESPONSE | jq -r '.id')
  export PAYMENT_NUMBER=$(echo $PAYMENT_RESPONSE | jq -r '.payment_number')
  echo "✅ Payment received: $PAYMENT_NUMBER"
else
  echo "❌ Payment recording failed"
  exit 1
fi
```

#### 6.3 Allocate Payment to Invoice

```bash
#!/bin/bash
# step6_allocate_payment.sh

ALLOCATION_RESPONSE=$(curl -s -X POST "${API_BASE}/${ORG_ID}/banking/payments/${PAYMENT_ID}/allocate/" \
  -H "Authorization: Bearer ${ACCESS_TOKEN}" \
  -H "Content-Type: application/json" \
  -d "{
    \"allocations\": [
      {
        \"document_id\": \"${INVOICE_ID}\",
        \"amount\": \"3000.0000\"
      }
    ]
  }")

if echo $ALLOCATION_RESPONSE | jq -e '.id' > /dev/null; then
  echo "✅ Payment allocated to invoice $INVOICE_NUMBER"
else
  echo "❌ Payment allocation failed"
  exit 1
fi
```

#### 6.4 Create Purchase Invoice for Rent (20 Jan)

```bash
#!/bin/bash
# step6_create_purchase_invoice.sh

SUPPLIER_ID=$(curl -s -X GET "${API_BASE}/${ORG_ID}/invoicing/contacts/?name=Office%20Landlord" \
  -H "Authorization: Bearer ${ACCESS_TOKEN}" | jq -r '.results[0].id')

RENT_ACCOUNT_ID=$(curl -s -X GET "${API_BASE}/${ORG_ID}/accounts/?code=6100" \
  -H "Authorization: Bearer ${ACCESS_TOKEN}" | jq -r '.[0].id')

OS_TAX_CODE_ID=$(curl -s -X GET "${API_BASE}/${ORG_ID}/gst/tax-codes/?code=OS" \
  -H "Authorization: Bearer ${ACCESS_TOKEN}" | jq -r '.[0].id')

PURCHASE_RESPONSE=$(curl -s -X POST "${API_BASE}/${ORG_ID}/invoicing/documents/" \
  -H "Authorization: Bearer ${ACCESS_TOKEN}" \
  -H "Content-Type: application/json" \
  -d "{
    \"contact_id\": \"${SUPPLIER_ID}\",
    \"document_type\": \"PURCHASE_INVOICE\",
    \"issue_date\": \"2026-01-20\",
    \"due_date\": \"2026-02-20\",
    \"currency\": \"SGD\",
    \"reference\": \"RENT-JAN-2026\",
    \"lines\": [
      {
        \"description\": \"Office rent for January 2026\",
        \"quantity\": 1,
        \"unit_price\": \"1500.0000\",
        \"tax_code_id\": \"${OS_TAX_CODE_ID}\",
        \"account_id\": \"${RENT_ACCOUNT_ID}\"
      }
    ]
  }")

if echo $PURCHASE_RESPONSE | jq -e '.id' > /dev/null; then
  export PURCHASE_INVOICE_ID=$(echo $PURCHASE_RESPONSE | jq -r '.id')
  echo "✅ Purchase invoice created: $(echo $PURCHASE_RESPONSE | jq -r '.document_number')"

  # Approve purchase invoice
  curl -s -X POST "${API_BASE}/${ORG_ID}/invoicing/documents/${PURCHASE_INVOICE_ID}/approve/" \
    -H "Authorization: Bearer ${ACCESS_TOKEN}" > /dev/null

  echo "✅ Purchase invoice approved"
else
  echo "❌ Purchase invoice creation failed"
  exit 1
fi
```

#### 6.5 Record Payment Made to Supplier

```bash
#!/bin/bash
# step6_record_payment_made.sh

SUPPLIER_ID=$(curl -s -X GET "${API_BASE}/${ORG_ID}/invoicing/contacts/?name=Office%20Landlord" \
  -H "Authorization: Bearer ${ACCESS_TOKEN}" | jq -r '.results[0].id')

BANK_ACCOUNT_ID=$(curl -s -X GET "${API_BASE}/${ORG_ID}/banking/bank-accounts/" \
  -H "Authorization: Bearer ${ACCESS_TOKEN}" | jq -r '.[0].id')

PAYMENT_MADE_RESPONSE=$(curl -s -X POST "${API_BASE}/${ORG_ID}/banking/payments/make/" \
  -H "Authorization: Bearer ${ACCESS_TOKEN}" \
  -H "Content-Type: application/json" \
  -d "{
    \"contact_id\": \"${SUPPLIER_ID}\",
    \"bank_account_id\": \"${BANK_ACCOUNT_ID}\",
    \"payment_date\": \"2026-01-20\",
    \"amount\": \"1500.0000\",
    \"payment_method\": \"BANK_TRANSFER\",
    \"payment_reference\": \"RENT-JAN-2026\",
    \"currency\": \"SGD\"
  }")

if echo $PAYMENT_MADE_RESPONSE | jq -e '.id' > /dev/null; then
  export PAYMENT_MADE_ID=$(echo $PAYMENT_MADE_RESPONSE | jq -r '.id')
  echo "✅ Payment made: $(echo $PAYMENT_MADE_RESPONSE | jq -r '.payment_number')"

  # Allocate payment to purchase invoice
  curl -s -X POST "${API_BASE}/${ORG_ID}/banking/payments/${PAYMENT_MADE_ID}/allocate/" \
    -H "Authorization: Bearer ${ACCESS_TOKEN}" \
    -H "Content-Type: application/json" \
    -d "{
      \"allocations\": [
        {
          \"document_id\": \"${PURCHASE_INVOICE_ID}\",
          \"amount\": \"1500.0000\"
        }
      ]
    }" > /dev/null

  echo "✅ Payment allocated to purchase invoice"
else
  echo "❌ Payment recording failed"
  exit 1
fi
```

#### 6.6 Record Office Supplies Expense (25 Jan)

```bash
#!/bin/bash
# step6_office_supplies.sh

SUPPLIER_ID=$(curl -s -X GET "${API_BASE}/${ORG_ID}/invoicing/contacts/?name=Office%20Landlord" \
  -H "Authorization: Bearer ${ACCESS_TOKEN}" | jq -r '.results[0].id')

SUPPLIES_ACCOUNT_ID=$(curl -s -X GET "${API_BASE}/${ORG_ID}/accounts/?code=6200" \
  -H "Authorization: Bearer ${ACCESS_TOKEN}" | jq -r '.[0].id')

OS_TAX_CODE_ID=$(curl -s -X GET "${API_BASE}/${ORG_ID}/gst/tax-codes/?code=OS" \
  -H "Authorization: Bearer ${ACCESS_TOKEN}" | jq -r '.[0].id')

# Create purchase invoice for supplies
SUPPLIES_RESPONSE=$(curl -s -X POST "${API_BASE}/${ORG_ID}/invoicing/documents/" \
  -H "Authorization: Bearer ${ACCESS_TOKEN}" \
  -H "Content-Type: application/json" \
  -d "{
    \"contact_id\": \"${SUPPLIER_ID}\",
    \"document_type\": \"PURCHASE_INVOICE\",
    \"issue_date\": \"2026-01-25\",
    \"due_date\": \"2026-01-25\",
    \"currency\": \"SGD\",
    \"reference\": \"SUP-001\",
    \"lines\": [
      {
        \"description\": \"Office supplies and stationery\",
        \"quantity\": 1,
        \"unit_price\": \"200.0000\",
        \"tax_code_id\": \"${OS_TAX_CODE_ID}\",
        \"account_id\": \"${SUPPLIES_ACCOUNT_ID}\"
      }
    ]
  }")

if echo $SUPPLIES_RESPONSE | jq -e '.id' > /dev/null; then
  export SUPPLIES_INVOICE_ID=$(echo $SUPPLIES_RESPONSE | jq -r '.id')
  
  # Approve and pay immediately
  curl -s -X POST "${API_BASE}/${ORG_ID}/invoicing/documents/${SUPPLIES_INVOICE_ID}/approve/" \
    -H "Authorization: Bearer ${ACCESS_TOKEN}" > /dev/null
  
  # Record payment
  PAYMENT_RESPONSE=$(curl -s -X POST "${API_BASE}/${ORG_ID}/banking/payments/make/" \
    -H "Authorization: Bearer ${ACCESS_TOKEN}" \
    -H "Content-Type: application/json" \
    -d "{
      \"contact_id\": \"${SUPPLIER_ID}\",
      \"bank_account_id\": \"${BANK_ACCOUNT_ID}\",
      \"payment_date\": \"2026-01-25\",
      \"amount\": \"200.0000\",
      \"payment_method\": \"BANK_TRANSFER\",
      \"payment_reference\": \"SUP-001\",
      \"currency\": \"SGD\"
    }")
  
  PAYMENT_SUPPLIES_ID=$(echo $PAYMENT_RESPONSE | jq -r '.id')
  
  # Allocate
  curl -s -X POST "${API_BASE}/${ORG_ID}/banking/payments/${PAYMENT_SUPPLIES_ID}/allocate/" \
    -H "Authorization: Bearer ${ACCESS_TOKEN}" \
    -H "Content-Type: application/json" \
    -d "{
      \"allocations\": [{ \"document_id\": \"${SUPPLIES_INVOICE_ID}\", \"amount\": \"200.0000\" }]
    }" > /dev/null
  
  echo "✅ Office supplies recorded and paid"
fi
```

---

### Step 7: Bank Reconciliation

#### 7.1 Import Bank Statement (CSV)

```bash
#!/bin/bash
# step7_import_bank_statement.sh

# Create sample CSV file
cat > /tmp/bank_statement_jan.csv << 'EOF'
Date,Description,Amount,Reference
2026-01-01,Opening Balance,10000.00,OB
2026-01-15,Customer Payment,3000.00,INV-00001
2026-01-20,Rent Payment,-1500.00,RENT-JAN
2026-01-25,Office Supplies,-200.00,SUP-001
EOF

BANK_ACCOUNT_ID=$(curl -s -X GET "${API_BASE}/${ORG_ID}/banking/bank-accounts/" \
  -H "Authorization: Bearer ${ACCESS_TOKEN}" | jq -r '.[0].id')

IMPORT_RESPONSE=$(curl -s -X POST "${API_BASE}/${ORG_ID}/banking/bank-transactions/import/" \
  -H "Authorization: Bearer ${ACCESS_TOKEN}" \
  -F "file=@/tmp/bank_statement_jan.csv" \
  -F "bank_account_id=${BANK_ACCOUNT_ID}")

if echo $IMPORT_RESPONSE | jq -e '.imported_count' > /dev/null; then
  IMPORTED=$(echo $IMPORT_RESPONSE | jq -r '.imported_count')
  DUPLICATES=$(echo $IMPORT_RESPONSE | jq -r '.duplicate_count')
  echo "✅ Bank statement imported: $IMPORTED transactions ($DUPLICATES duplicates)"
else
  echo "❌ Bank import failed"
  echo $IMPORT_RESPONSE | jq '.'
  exit 1
fi
```

#### 7.2 List Unreconciled Transactions

```bash
#!/bin/bash
# step7_list_unreconciled.sh

BANK_ACCOUNT_ID=$(curl -s -X GET "${API_BASE}/${ORG_ID}/banking/bank-accounts/" \
  -H "Authorization: Bearer ${ACCESS_TOKEN}" | jq -r '.[0].id')

TRANSACTIONS=$(curl -s -X GET "${API_BASE}/${ORG_ID}/banking/bank-transactions/?bank_account_id=${BANK_ACCOUNT_ID}&is_reconciled=false" \
  -H "Authorization: Bearer ${ACCESS_TOKEN}")

echo $TRANSACTIONS | jq '.results[] | {
  id,
  date: .transaction_date,
  description,
  amount,
  is_reconciled
}'
```

#### 7.3 Reconcile Transaction

```bash
#!/bin/bash
# step7_reconcile_transaction.sh

# Get first unreconciled transaction
TRANSACTION_ID=$(curl -s -X GET "${API_BASE}/${ORG_ID}/banking/bank-transactions/?is_reconciled=false" \
  -H "Authorization: Bearer ${ACCESS_TOKEN}" | jq -r '.results[0].id')

# Get matching payment ID
PAYMENT_ID=$(curl -s -X GET "${API_BASE}/${ORG_ID}/banking/payments/" \
  -H "Authorization: Bearer ${ACCESS_TOKEN}" | jq -r '.results[0].id')

RECONCILE_RESPONSE=$(curl -s -X POST "${API_BASE}/${ORG_ID}/banking/bank-transactions/${TRANSACTION_ID}/reconcile/" \
  -H "Authorization: Bearer ${ACCESS_TOKEN}" \
  -H "Content-Type: application/json" \
  -d "{\"payment_id\": \"${PAYMENT_ID}\"}")

if echo $RECONCILE_RESPONSE | jq -e '.id' > /dev/null; then
  echo "✅ Transaction reconciled"
else
  echo "❌ Reconciliation failed"
  exit 1
fi
```

---

### Step 8: Financial Reports & PDF Generation

#### 8.1 Generate Profit & Loss Statement

> **⚠️ Note:** Query parameters for financial reports need verification. Test endpoint before using exact parameter names.

```bash
#!/bin/bash
# step8_generate_profit_loss.sh

P_L_RESPONSE=$(curl -s -X GET "${API_BASE}/${ORG_ID}/reports/reports/financial/" \
  -H "Authorization: Bearer ${ACCESS_TOKEN}" \
  -G \
  --data-urlencode "report_type=profit_loss" \
  --data-urlencode "start_date=2026-01-01" \
  --data-urlencode "end_date=2026-01-31")

if echo $P_L_RESPONSE | jq -e '.data' > /dev/null; then
  echo "✅ Profit & Loss generated"
  echo $P_L_RESPONSE | jq '.data'
  
  # Save to file for PDF generation
  echo $P_L_RESPONSE | jq '.data' > /tmp/profit_loss.json
else
  echo "❌ P&L generation failed"
  echo $P_L_RESPONSE | jq '.'
  exit 1
fi
```

#### 8.2 Generate Balance Sheet

```bash
#!/bin/bash
# step8_generate_balance_sheet.sh

B_S_RESPONSE=$(curl -s -X GET "${API_BASE}/${ORG_ID}/reports/reports/financial/" \
  -H "Authorization: Bearer ${ACCESS_TOKEN}" \
  -G \
  --data-urlencode "report_type=balance_sheet" \
  --data-urlencode "as_at_date=2026-01-31")

if echo $B_S_RESPONSE | jq -e '.data' > /dev/null; then
  echo "✅ Balance Sheet generated"
  echo $B_S_RESPONSE | jq '.data'
  
  # Save to file for PDF generation
  echo $B_S_RESPONSE | jq '.data' > /tmp/balance_sheet.json
else
  echo "❌ Balance Sheet generation failed"
  exit 1
fi
```

#### 8.3 Generate Invoice PDF

```bash
#!/bin/bash
# step8_generate_invoice_pdf.sh

# Get the invoice ID from earlier step
if [ -z "$INVOICE_ID" ]; then
  INVOICE_ID=$(curl -s -X GET "${API_BASE}/${ORG_ID}/invoicing/documents/?document_type=SALES_INVOICE" \
    -H "Authorization: Bearer ${ACCESS_TOKEN}" | jq -r '.results[0].id')
fi

# Download PDF
curl -s -X GET "${API_BASE}/${ORG_ID}/invoicing/documents/${INVOICE_ID}/pdf/" \
  -H "Authorization: Bearer ${ACCESS_TOKEN}" \
  -o /tmp/invoice_${INVOICE_NUMBER}.pdf

if [ -f /tmp/invoice_${INVOICE_NUMBER}.pdf ]; then
  echo "✅ Invoice PDF saved: /tmp/invoice_${INVOICE_NUMBER}.pdf"
  ls -lh /tmp/invoice_${INVOICE_NUMBER}.pdf
else
  echo "❌ PDF generation failed"
  exit 1
fi
```

#### 8.4 Python Script: Convert Report JSON to PDF

```python
#!/usr/bin/env python3
# generate_report_pdf.py
"""
Convert LedgerSG financial report JSON to PDF.
Requires: pip install reportlab
"""

import json
import sys
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.platypus import Table, TableStyle

def create_financial_report_pdf(data, filename="financial_report.pdf", report_type="Profit & Loss"):
    c = canvas.Canvas(filename, pagesize=A4)
    width, height = A4
    margin = 0.75 * inch
    y = height - margin
    
    # Title
    c.setFont("Helvetica-Bold", 18)
    c.drawString(margin, y, f"{report_type} Statement")
    y -= 25
    
    # Company info
    c.setFont("Helvetica", 12)
    c.drawString(margin, y, "ABC Trading")
    y -= 18
    c.drawString(margin, y, f"Period: {data.get('period_start', 'N/A')} to {data.get('period_end', 'N/A')}")
    y -= 18
    c.drawString(margin, y, f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    y -= 30
    
    # Table data
    table_data = [["Account", "Amount (SGD)"]]
    total = 0
    
    for line in data.get("line_items", []):
        account_name = line.get("account_name", "Unknown")
        amount = float(line.get("amount", 0))
        table_data.append([account_name, f"{amount:,.2f}"])
        total += amount
    
    # Add total row
    table_data.append(["", ""])  # Spacer
    table_data.append(["NET PROFIT / (LOSS)", f"{total:,.2f}"])
    
    # Create table
    table = Table(table_data, colWidths=[4*inch, 2*inch])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'RIGHT'),
        ('ALIGN', (0, 0), (0, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, -1), (-1, -1), colors.lightgrey),
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('ROWBACKGROUNDS', (0, 1), (-1, -2), [colors.white, colors.lightgrey]),
    ]))
    
    # Draw table
    table.wrapOn(c, width, height)
    table.drawOn(c, margin, y - 200)
    
    # Footer
    y = margin
    c.setFont("Helvetica-Oblique", 8)
    c.drawString(margin, y, "This report is generated for IRAS record-keeping purposes.")
    c.drawString(margin, y - 12, "Retain for minimum 5 years per IRAS requirements.")
    
    c.save()
    print(f"✅ PDF saved: {filename}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: generate_report_pdf.py <report.json> [output.pdf]")
        sys.exit(1)
    
    with open(sys.argv[1], 'r') as f:
        data = json.load(f)
    
    output = sys.argv[2] if len(sys.argv) > 2 else "financial_report.pdf"
    report_type = "Profit & Loss" if "profit_loss" in sys.argv[1] else "Balance Sheet"
    
    create_financial_report_pdf(data, output, report_type)
```

**Usage:**
```bash
# Install dependencies
pip install reportlab

# Generate P&L PDF
python3 generate_report_pdf.py /tmp/profit_loss.json /tmp/profit_loss.pdf

# Generate Balance Sheet PDF
python3 generate_report_pdf.py /tmp/balance_sheet.json /tmp/balance_sheet.pdf
```

---

## 🛠 Helper Functions

### Complete Workflow Script

```bash
#!/bin/bash
# complete_workflow.sh
# Complete accounting workflow for non-GST Singapore SMB

set -e

# Configuration
export API_BASE="http://localhost:8000/api/v1"
export EMAIL="accountant@abctrading.com"
export PASSWORD="secure_password_here"

echo "🚀 Starting LedgerSG Accounting Workflow"
echo "========================================"

# Step 1: Login
echo ""
echo "📝 Step 1: Authentication"
source ./step1_login.sh

# Step 2: Get/Create Organisation
echo ""
echo "🏢 Step 2: Organisation Setup"
source ./step2_create_org.sh

# Step 3: Get Account IDs
echo ""
echo "📊 Step 3: Chart of Accounts"
source ./step3_list_accounts.sh

# Get account UUIDs
BANK_ACCOUNT_ID=$(curl -s -X GET "${API_BASE}/${ORG_ID}/accounts/?code=1100" \
  -H "Authorization: Bearer ${ACCESS_TOKEN}" | jq -r '.[0].id')
CAPITAL_ACCOUNT_ID=$(curl -s -X GET "${API_BASE}/${ORG_ID}/accounts/?code=3000" \
  -H "Authorization: Bearer ${ACCESS_TOKEN}" | jq -r '.[0].id')
SALES_ACCOUNT_ID=$(curl -s -X GET "${API_BASE}/${ORG_ID}/accounts/?code=4000" \
  -H "Authorization: Bearer ${ACCESS_TOKEN}" | jq -r '.[0].id')
RENT_ACCOUNT_ID=$(curl -s -X GET "${API_BASE}/${ORG_ID}/accounts/?code=6100" \
  -H "Authorization: Bearer ${ACCESS_TOKEN}" | jq -r '.[0].id')
OS_TAX_CODE_ID=$(curl -s -X GET "${API_BASE}/${ORG_ID}/gst/tax-codes/?code=OS" \
  -H "Authorization: Bearer ${ACCESS_TOKEN}" | jq -r '.[0].id')
NA_TAX_CODE_ID=$(curl -s -X GET "${API_BASE}/${ORG_ID}/gst/tax-codes/?code=NA" \
  -H "Authorization: Bearer ${ACCESS_TOKEN}" | jq -r '.[0].id')

echo "✅ Account UUIDs retrieved"

# Step 4: Create Contacts
echo ""
echo "👥 Step 4: Contact Management"
source ./step4_create_customer.sh
source ./step4_create_supplier.sh

# Step 5: Opening Balance
echo ""
echo "💰 Step 5: Opening Balances"
source ./step5_opening_balance.sh

# Step 6: Daily Transactions
echo ""
echo "📝 Step 6: Daily Transactions"
source ./step6_create_sales_invoice.sh
source ./step6_record_payment_received.sh
source ./step6_allocate_payment.sh
source ./step6_create_purchase_invoice.sh
source ./step6_record_payment_made.sh
source ./step6_office_supplies.sh

# Step 7: Bank Reconciliation
echo ""
echo "🏦 Step 7: Bank Reconciliation"
source ./step7_import_bank_statement.sh
source ./step7_list_unreconciled.sh

# Step 8: Reports
echo ""
echo "📈 Step 8: Financial Reports"
source ./step8_generate_profit_loss.sh
source ./step8_generate_balance_sheet.sh
source ./step8_generate_invoice_pdf.sh

echo ""
echo "========================================"
echo "✅ Workflow Complete!"
echo "========================================"
echo ""
echo "Generated Files:"
ls -lh /tmp/*.pdf /tmp/*.json 2>/dev/null || echo "No files generated"
echo ""
echo "Next Steps:"
echo "  1. Review PDF reports in /tmp/"
echo "  2. Archive reports for IRAS compliance (5 years)"
echo "  3. Run monthly for ongoing accounting"
```

### UUID Lookup Helper

```bash
#!/bin/bash
# helpers.sh - Reusable helper functions

# Get account UUID by code
get_account_id() {
  local CODE=$1
  curl -s -X GET "${API_BASE}/${ORG_ID}/accounts/?code=${CODE}" \
    -H "Authorization: Bearer ${ACCESS_TOKEN}" | jq -r '.[0].id'
}

# Get tax code UUID by code
get_tax_code_id() {
  local CODE=$1
  curl -s -X GET "${API_BASE}/${ORG_ID}/gst/tax-codes/?code=${CODE}" \
    -H "Authorization: Bearer ${ACCESS_TOKEN}" | jq -r '.[0].id'
}

# Get contact UUID by name
get_contact_id() {
  local NAME=$1
  curl -s -X GET "${API_BASE}/${ORG_ID}/invoicing/contacts/?name=${NAME}" \
    -H "Authorization: Bearer ${ACCESS_TOKEN}" | jq -r '.results[0].id'
}

# Get bank account UUID
get_bank_account_id() {
  curl -s -X GET "${API_BASE}/${ORG_ID}/banking/bank-accounts/" \
    -H "Authorization: Bearer ${ACCESS_TOKEN}" | jq -r '.[0].id'
}

# Format amount with 4 decimal places
format_amount() {
  printf "%.4f" $1
}

# Check if token is expired (within 2 minutes of expiry)
is_token_expiring() {
  local EXPIRY=$(curl -s -X POST "${API_BASE}/auth/me/" \
    -H "Authorization: Bearer ${ACCESS_TOKEN}" | jq -r '.tokens.access_expires')
  local EXPIRY_EPOCH=$(date -d "$EXPIRY" +%s 2>/dev/null || date -j -f "%Y-%m-%dT%H:%M:%S" "$EXPIRY" +%s 2>/dev/null)
  local NOW_EPOCH=$(date +%s)
  local DIFF=$((EXPIRY_EPOCH - NOW_EPOCH))
  
  if [ $DIFF -lt 120 ]; then
    return 0  # Token expiring soon
  else
    return 1  # Token still valid
  fi
}

# Refresh token if expiring
refresh_if_needed() {
  if is_token_expiring; then
    echo "⚠️  Token expiring soon, refreshing..."
    source ./refresh_token.sh
  fi
}
```

---

## 🔐 CORS & Backend Tips

### CORS Configuration

| Scenario | Solution |
|----------|----------|
| **Server-side scripts (curl, Python)** | ✅ CORS not applicable |
| **Browser-based scripts (Playwright)** | ✅ CORS headers handled automatically |
| **Custom frontend origin** | Update `CORS_ALLOWED_ORIGINS` in backend settings |
| **OPTIONS preflight returns 401** | Backend `CORSJWTAuthentication` handles this automatically |

### Backend Configuration Check

```bash
# Verify CORS is configured
curl -X OPTIONS http://localhost:8000/api/v1/auth/me/ -i | grep -i "access-control"

# Expected headers:
# Access-Control-Allow-Origin: http://localhost:3000
# Access-Control-Allow-Methods: GET, POST, PATCH, DELETE, OPTIONS
# Access-Control-Allow-Headers: authorization, content-type
```

### Token Management Best Practices

```bash
#!/bin/bash
# token_manager.sh

# Store tokens securely (never in code)
export ACCESS_TOKEN_FILE="/tmp/ledgersg_access_token"
export REFRESH_TOKEN_FILE="/tmp/ledgersg_refresh_token"

# Save tokens
save_tokens() {
  echo "$ACCESS_TOKEN" > "$ACCESS_TOKEN_FILE"
  echo "$REFRESH_TOKEN" > "$REFRESH_TOKEN_FILE"
  chmod 600 "$ACCESS_TOKEN_FILE" "$REFRESH_TOKEN_FILE"
}

# Load tokens
load_tokens() {
  if [ -f "$ACCESS_TOKEN_FILE" ] && [ -f "$REFRESH_TOKEN_FILE" ]; then
    export ACCESS_TOKEN=$(cat "$ACCESS_TOKEN_FILE")
    export REFRESH_TOKEN=$(cat "$REFRESH_TOKEN_FILE")
    return 0
  else
    return 1
  fi
}

# Check token validity
check_token() {
  curl -s -X GET "${API_BASE}/auth/me/" \
    -H "Authorization: Bearer ${ACCESS_TOKEN}" | jq -e '.id' > /dev/null
  return $?
}

# Auto-refresh workflow
ensure_authenticated() {
  if load_tokens && check_token; then
    echo "✅ Valid session found"
    return 0
  else
    echo "📝 No valid session, logging in..."
    source ./step1_login.sh
    save_tokens
    return 0
  fi
}
```

### Rate Limiting

| Endpoint | Rate Limit | Key |
|----------|------------|-----|
| `/auth/login/` | 10/min | IP + User |
| `/auth/refresh/` | 20/min | IP |
| `/auth/register/` | 5/hour | IP |
| Authenticated endpoints | 100/min | User |

**Handle 429 Responses:**
```bash
#!/bin/bash
# handle_rate_limit.sh

API_RESPONSE=$(curl -s -w "\n%{http_code}" -X GET "${API_BASE}/${ORG_ID}/accounts/" \
  -H "Authorization: Bearer ${ACCESS_TOKEN}")

HTTP_CODE=$(echo "$API_RESPONSE" | tail -n1)
BODY=$(echo "$API_RESPONSE" | head -n-1)

if [ "$HTTP_CODE" = "429" ]; then
  RETRY_AFTER=$(echo "$BODY" | jq -r '.error.details.retry_after // 60')
  echo "⚠️  Rate limited. Waiting ${RETRY_AFTER} seconds..."
  sleep $RETRY_AFTER
  
  # Retry with exponential backoff
  retry_count=0
  max_retries=3
  while [ $retry_count -lt $max_retries ]; do
    sleep $((2 ** retry_count))
    API_RESPONSE=$(curl -s -w "\n%{http_code}" -X GET "${API_BASE}/${ORG_ID}/accounts/" \
      -H "Authorization: Bearer ${ACCESS_TOKEN}")
    HTTP_CODE=$(echo "$API_RESPONSE" | tail -n1)
    
    if [ "$HTTP_CODE" != "429" ]; then
      break
    fi
    
    retry_count=$((retry_count + 1))
  done
fi
```

---

## 📋 IRAS Compliance Checklist

### For Non-GST Registered Businesses

#### Record Keeping Requirements

| Requirement | LedgerSG Feature | Status |
|-------------|------------------|--------|
| ✅ 5-year retention | Immutable audit log + PDF export | Implemented |
| ✅ Source documents | Invoices with document numbers | Step 6 |
| ✅ Accurate P&L | Financial reports | Step 8 |
| ✅ Accurate Balance Sheet | Financial reports | Step 8 |
| ✅ Bank reconciliation | Reconciliation workflow | Step 7 |
| ✅ GST registration tracking | Organisation `gst_registered` field | Step 2 |

#### Tax Filing Requirements

**Annual Income Tax Return (Form C-S or C):**
- Based on financial statements (P&L + Balance Sheet)
- Generated in Step 8 of this workflow
- Export as PDF for submission

**Key Deadlines:**
- **Financial Year End:** 31 December (for calendar year businesses)
- **Filing Deadline:** 30 November (for previous year ended 31 December)
- **Estimated Chargeable Income (ECI):** 3 months after FY end

#### Tax Codes for Non-GST Business

| Code | Name | When to Use |
|------|------|-------------|
| **OS** | Out-of-Scope | ✅ ALL transactions for non-GST business |
| **NA** | Not Applicable | Alternative for internal entries |
| ⚠️ **SR** | Standard Rated | ❌ Do NOT use (GST only) |
| ⚠️ **ZR** | Zero Rated | ❌ Do NOT use (GST only) |
| ⚠️ **ES** | Exempt | ❌ Do NOT use (GST only) |

#### Invoice Requirements (Non-GST)

✅ **Required:**
- Document number (auto-generated)
- Issue date
- Description of goods/services
- Amount (no GST shown)

❌ **Not Required:**
- GST registration number
- GST amount breakdown
- "Tax Invoice" labeling

---

## 🛠 Troubleshooting

### Common Errors

#### 401 Unauthorized

**Symptoms:**
```json
{
  "error": {
    "code": "UNAUTHORIZED",
    "message": "Invalid or expired token"
  }
}
```

**Solutions:**
```bash
# 1. Check token is set
echo $ACCESS_TOKEN

# 2. Refresh token
source ./refresh_token.sh

# 3. Re-login if refresh fails
source ./step1_login.sh
```

#### 403 Forbidden

**Symptoms:**
```json
{
  "error": {
    "code": "FORBIDDEN",
    "message": "You do not have permission"
  }
}
```

**Causes:**
- User not member of organisation
- Missing required permissions
- UserOrganisation.accepted_at not set

**Solutions:**
```bash
# Check user organisations
curl -X GET "${API_BASE}/auth/organisations/" \
  -H "Authorization: Bearer ${ACCESS_TOKEN}"

# Accept organisation invitation if pending
```

#### 400 Bad Request — Unbalanced Journal Entry

**Symptoms:**
```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Debits (10000.0000) must equal credits (0.0000)"
  }
}
```

**Fix:** Ensure every debit has a matching credit
```bash
# Wrong:
{ "lines": [{ "debit": "10000.0000", "credit": "0.0000" }] }

# Right:
{
  "lines": [
    { "debit": "10000.0000", "credit": "0.0000" },
    { "debit": "0.0000", "credit": "10000.0000" }
  ]
}
```

#### 400 Bad Request — Invalid UUID Format

**Symptoms:**
```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "account_id must be a valid UUID"
  }
}
```

**Cause:** Using account code instead of UUID

**Fix:** Use helper function to get UUID
```bash
# Wrong:
"account_id": "1100"  # ❌ Code string

# Right:
"account_id": "550e8400-e29b-41d4-a716-446655440000"  # ✅ UUID

# Use helper:
ACCOUNT_ID=$(get_account_id "1100")
```

#### 429 Too Many Requests

**Symptoms:** Rate limiting response

**Fix:** Implement backoff
```bash
sleep 60  # Wait for rate limit reset
# Or use retry logic from helpers.sh
```

### Decimal Precision Errors

**Symptoms:**
```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "debit must have 4 decimal places"
  }
}
```

**Fix:** Always use strings with 4 decimals
```bash
# Wrong:
{ "debit": 10000 }           # ❌ Integer
{ "debit": 10000.00 }        # ❌ Only 2 decimals

# Right:
{ "debit": "10000.0000" }     # ✅ 4 decimals as string

# Use helper:
format_amount 10000 # Returns "10000.0000"
```

#### 500 Internal Server Error — UUID Double Conversion

**Symptoms:**
```json
{
  "error": {
    "code": "internal_error",
    "message": "'UUID' object has no attribute 'replace'"
  }
}
```

**Root Cause:** Django's `<uuid:org_id>` path converter automatically converts URL parameters to UUID objects, but the backend code was trying to convert them again with `UUID(org_id)`.

**When This Happens:**
- Accessing banking endpoints (`/api/v1/{org_id}/banking/bank-accounts/`)
- Accessing GST endpoints (`/api/v1/{org_id}/gst/tax-codes/`)
- Accessing journal endpoints (`/api/v1/{org_id}/journal-entries/entries/`)

**Solution:** This has been fixed in the backend. If you encounter this error:
1. Ensure backend is updated to latest version
2. Check that views don't have redundant `UUID(org_id)` calls
3. Restart backend server after code changes

**Status:** ✅ Fixed as of 2026-03-08

### CORS Errors

**Symptoms:** Browser console shows CORS errors

**Backend Fix:**
```python
# In settings/base.py
CORS_ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "https://your-frontend-domain.com",
]
```

**Frontend Fix:**
```typescript
// Ensure credentials are included
fetch(url, {
  credentials: 'include',
  headers: {
    'Authorization': `Bearer ${token}`
  }
});
```

### Invoice Not Posted to Ledger

**Symptoms:** Journal entries not created after invoice

**Fix:** Must approve invoice
```bash
# Invoice created as DRAFT
curl -X POST .../documents/  # Creates DRAFT

# Must approve to post
# ✅ Required:
curl -X POST .../documents/{id}/approve/

# ❌ Without approval:
# Journal entries NOT created
```

### Payment Not Allocated

**Symptoms:** Invoice still shows as unpaid

**Fix:** Must allocate payment to invoice
```bash
# Step 1: Record payment
curl -X POST .../payments/receive/

# Step 2: Allocate to invoice ✅ REQUIRED
curl -X POST .../payments/{id}/allocate/ \
  -d '{"allocations": [{"document_id": "...", "amount": "..."}]}'
```

---

## 📚 Appendix

### A. Complete API Endpoint Reference

**Authentication (Non-org scoped):**
```
POST /api/v1/auth/login/
POST /api/v1/auth/logout/
POST /api/v1/auth/refresh/
GET  /api/v1/auth/me/
POST /api/v1/auth/change-password/
GET  /api/v1/auth/organisations/
POST /api/v1/auth/set-default-org/
```

**Organisation Management:**
```
GET  /api/v1/organisations/
POST /api/v1/organisations/
GET  /api/v1/{org_id}/
PATCH /api/v1/{org_id}/
GET  /api/v1/{org_id}/summary/
GET  /api/v1/{org_id}/settings/
GET  /api/v1/{org_id}/fiscal-years/
GET  /api/v1/{org_id}/fiscal-periods/
```

**Chart of Accounts:**
```
GET  /api/v1/{org_id}/accounts/
POST /api/v1/{org_id}/accounts/
GET  /api/v1/{org_id}/accounts/?code={code}
GET  /api/v1/{org_id}/accounts/{account_id}/
GET  /api/v1/{org_id}/accounts/types/
GET  /api/v1/{org_id}/accounts/trial-balance/
```

**Journal Entries:**
```
GET  /api/v1/{org_id}/journal-entries/entries/
POST /api/v1/{org_id}/journal-entries/entries/
GET  /api/v1/{org_id}/journal-entries/entries/{entry_id}/
POST /api/v1/{org_id}/journal-entries/entries/{entry_id}/reverse/
GET  /api/v1/{org_id}/journal-entries/trial-balance/
```

**Banking:**
```
GET  /api/v1/{org_id}/banking/bank-accounts/
POST /api/v1/{org_id}/banking/bank-accounts/
GET  /api/v1/{org_id}/banking/bank-accounts/{account_id}/

GET  /api/v1/{org_id}/banking/payments/
POST /api/v1/{org_id}/banking/payments/receive/
POST /api/v1/{org_id}/banking/payments/make/
GET  /api/v1/{org_id}/banking/payments/{payment_id}/
POST /api/v1/{org_id}/banking/payments/{payment_id}/allocate/

GET  /api/v1/{org_id}/banking/bank-transactions/
POST /api/v1/{org_id}/banking/bank-transactions/import/
POST /api/v1/{org_id}/banking/bank-transactions/{id}/reconcile/
```

**Invoicing:**
```
GET  /api/v1/{org_id}/invoicing/contacts/
POST /api/v1/{org_id}/invoicing/contacts/
GET  /api/v1/{org_id}/invoicing/contacts/{contact_id}/

GET  /api/v1/{org_id}/invoicing/documents/
POST /api/v1/{org_id}/invoicing/documents/
GET  /api/v1/{org_id}/invoicing/documents/{document_id}/
POST /api/v1/{org_id}/invoicing/documents/{document_id}/approve/
POST /api/v1/{org_id}/invoicing/documents/{document_id}/void/
GET  /api/v1/{org_id}/invoicing/documents/{document_id}/pdf/
```

**Reports:**
```
GET /api/v1/{org_id}/reports/dashboard/metrics/
GET /api/v1/{org_id}/reports/reports/financial/
```

### B. Environment Variable Template

```bash
# .env file template
cat > .env << 'EOF'
# API Configuration
API_BASE=http://localhost:8000/api/v1

# User Credentials
EMAIL=accountant@abctrading.com
PASSWORD=your_secure_password_here

# Tokens (set by scripts)
# ACCESS_TOKEN=eyJhbGciOiJIUzI1NiIs...
# REFRESH_TOKEN=eyJhbGciOiJIUzI1NiIs...
# ORG_ID=550e8400-e29b-41d4-a716-446655440000
# BANK_ACCOUNT_ID=...
EOF
```

### C. Testing Checklist

**Before Production Use:**

- [ ] Login works and returns tokens
- [ ] Organisation created with `gst_registered: false`
- [ ] Bank account linked to CoA account 1100
- [ ] Contact creation works
- [ ] Journal entry creates with balanced debits/credits
- [ ] Sales invoice creates and approves
- [ ] Payment records and allocates
- [ ] Bank statement imports
- [ ] Reconciliation works
- [ ] Reports generate
- [ ] PDFs download
- [ ] Token refresh works
- [ ] Rate limiting handled

### D. Singapore Business Types

| Entity Type | GST Threshold | LedgerSG entity_type |
|-------------|---------------|---------------------|
| Sole Proprietorship | S$1M | `SOLE_PROPRIETORSHIP` |
| Partnership | S$1M | `PARTNERSHIP` |
| Private Limited (Pte Ltd) | S$1M | `PRIVATE_LIMITED` |
| Limited Liability Partnership | S$1M | `LLP` |

**Registration:** All business types must register with ACRA before IRAS tax filing.

### E. Common Account Codes

| Code | Name | Type | Typical Use |
|------|------|------|-------------|
| 1100 | Bank Account | Asset | DBS, OCBC, etc. |
| 1200 | Accounts Receivable | Asset | Customer invoices |
| 1500 | Equipment | Asset | Fixed assets |
| 2000 | Accounts Payable | Liability | Supplier invoices |
| 2100 | Loans Payable | Liability | Bank loans |
| 3000 | Owner's Capital | Equity | Initial investment |
| 3100 | Retained Earnings | Equity | Cumulative profit |
| 4000 | Sales Revenue | Revenue | Product sales |
| 4100 | Service Revenue | Revenue | Service income |
| 5000 | Cost of Goods Sold | Expense | Direct costs |
| 6100 | Rent Expense | Expense | Office rent |
| 6200 | Office Supplies | Expense | Stationery |
| 6300 | Utilities | Expense | Electricity, water |
| 6400 | Salaries | Expense | Staff wages |

---

## 📝 Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2026-03-08 | Initial release — Non-GST Singapore SMB workflow |

---

## 📞 Support

**Documentation:**
- [API_CLI_Usage_Guide.md](./API_CLI_Usage_Guide.md) — Complete endpoint reference
- [README.md](./README.md) — Project overview
- [AGENTS.md](./AGENTS.md) — Architecture and development guide

**Troubleshooting:**
1. Check backend is running: `curl http://localhost:8000/api/v1/health/`
2. Verify tokens: `curl -H "Authorization: Bearer $ACCESS_TOKEN" ...`
3. Review error messages in responses
4. Check [Troubleshooting](#troubleshooting) section

---

**END OF GUIDE**

*This guide was generated and validated against LedgerSG codebase v0.3.3*
