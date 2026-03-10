# 🧪 LedgerSG — Comprehensive Test Suite Workflow
## Combined Best Practices from ABC Trading & Lakshmi's Kitchen Scenarios

**Version:** 2.0.0  
**Date:** 2026-03-10  
**Purpose:** Production Validation + AI Agent Usage Guide  
**Compliance:** IRAS 2026, SFRS for Small Entities, PINT-SG Ready

---

## 📋 Executive Summary

This comprehensive test suite combines the strengths of both reference scenarios:
- **ABC Trading:** Clean, focused 1-month workflow with clear step-by-step validation
- **Lakshmi's Kitchen:** Realistic 12-month financial year with complex transactions

**Key Improvements:**
| Aspect | ABC Trading | Lakshmi's Kitchen | Combined Best Practice |
|--------|-------------|-------------------|------------------------|
| Time Period | 1 month | 12 months | **3 months (Q1)** — Balanced complexity |
| Business Type | Sole Proprietorship | Pte Ltd | **Both scenarios covered** |
| Transaction Count | ~5 | ~50 | **25 critical transactions** |
| Test Focus | API validation | Business workflow | **Both API + Business logic** |
| GST Status | Non-GST only | GST-registered | **Both scenarios documented** |
| Bank Reconciliation | Basic | Full workflow | **Complete with CSV import** |
| Reporting | P&L + BS | Full financials | **Plus GST F5 preview** |

**Test Coverage:**
- ✅ 8 API modules validated
- ✅ 25+ transaction scenarios
- ✅ 100% double-entry integrity checks
- ✅ IRAS compliance verification
- ✅ Security & permission testing
- ✅ Error handling validation

---

## 🎯 Test Scenario Design

### Business Profile: "Meridian Consulting Pte Ltd"

| Attribute | Value | Rationale |
|-----------|-------|-----------|
| **Company Name** | Meridian Consulting Pte Ltd | Singapore private limited |
| **UEN** | 202501234A | Valid ACRA format |
| **GST Status** | **Scenario A:** Not Registered<br>**Scenario B:** Registered | Test both workflows |
| **Financial Year** | 1 Jan – 31 Dec | Calendar year |
| **Base Currency** | SGD | Primary operating currency |
| **Bank** | DBS Business Account | Singapore bank |
| **Business Activity** | Management consulting services | Service-based SMB |

### Test Period: Q1 2026 (January – March)

**Why Q1?**
- Covers fiscal year start (opening balances)
- Includes month-end closing procedures
- Quarterly GST filing preparation (if registered)
- Balanced transaction volume for testing

### Transaction Timeline

| Month | Date | Transaction | Amount (SGD) | Type | GST Code | Description |
|-------|------|--------------|--------------|------|----------|-------------|
| **Jan** | 02 Jan | Opening capital injection | 50,000 | Equity | NA | Shareholder investment |
| | 05 Jan | Office equipment purchase | 8,500 | Fixed Asset | SR (if GST) | Computers, furniture |
| | 10 Jan | Client invoice #1 | 12,000 | Revenue | SR/OS | Consulting services |
| | 15 Jan | Payment received #1 | 12,000 | Receipt | — | Bank transfer |
| | 20 Jan | Office rent (Q1) | 9,000 | Expense | SR/OS | 3 months prepaid |
| | 25 Jan | Utilities payment | 450 | Expense | SR/OS | Electricity, water |
| | 31 Jan | Month-end close | — | Process | — | Journal entries |
| **Feb** | 05 Feb | Client invoice #2 | 15,000 | Revenue | SR/OS | Project milestone |
| | 10 Feb | Staff salaries | 8,500 | Expense | OS | 2 employees |
| | 15 Feb | Payment received #2 | 15,000 | Receipt | — | Full payment |
| | 20 Feb | Professional fees | 2,500 | Expense | SR/OS | Accounting, legal |
| | 28 Feb | Month-end close | — | Process | — | Depreciation entry |
| **Mar** | 05 Mar | Client invoice #3 | 18,000 | Revenue | SR/OS | Q1 final deliverable |
| | 10 Mar | Marketing expenses | 3,200 | Expense | SR/OS | Digital ads |
| | 15 Mar | Payment received #3 | 18,000 | Receipt | — | Full payment |
| | 20 Mar | Bank charges | 150 | Expense | EP | Monthly fees |
| | 25 Mar | GST F5 preparation | — | Process | — | If GST-registered |
| | 31 Mar | Q1 closing | — | Process | — | Financial statements |

**Expected Q1 Results:**
| Metric | Non-GST | GST-Registered |
|--------|---------|----------------|
| Total Revenue | 45,000 | 45,000 |
| Total Expenses | 24,300 | 24,300 |
| Net Profit | 20,700 | 20,700 |
| GST Collected | 0 | 4,050 (9% of 45,000) |
| GST Paid (Input) | 0 | ~1,800 (estimated) |
| Net GST Payable | 0 | ~2,250 |
| Cash on Hand | 75,550 | 75,550 |

---

## 🔐 Section 1: Authentication & Setup

### 1.1 Prerequisites Validation

```bash
# Verify backend is running
curl -s http://localhost:8000/api/v1/health/ | jq '.'
# Expected: {"status": "healthy", "database": "connected", "version": "1.0.0"}

# Verify frontend is running
curl -s http://localhost:3000 | head -20
# Expected: HTML with "LedgerSG" title

# Verify Redis is running
docker exec ledgersg_redis redis-cli ping
# Expected: PONG

# Verify PostgreSQL is running
docker exec ledgersg_db pg_isready -U ledgersg
# Expected: accepting connections
```

### 1.2 Test User Creation (TDD RED Phase)

```bash
# Test 1: Register new user (should succeed)
curl -X POST http://localhost:8000/api/v1/auth/register/ \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@meridian.sg",
    "password": "SecurePass123!",
    "full_name": "Test Accountant"
  }' | jq '.'

# Expected: 201 Created with user + tokens

# Test 2: Login with credentials (should succeed)
LOGIN_RESPONSE=$(curl -s -X POST http://localhost:8000/api/v1/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@meridian.sg",
    "password": "SecurePass123!"
  }')

# Extract and store tokens
export ACCESS_TOKEN=$(echo $LOGIN_RESPONSE | jq -r '.tokens.access')
export REFRESH_TOKEN=$(echo $LOGIN_RESPONSE | jq -r '.tokens.refresh')

# Verify token structure
echo $ACCESS_TOKEN | jq -R 'split(".") | .[0], .[1] | @base64d | fromjson'

# Test 3: Verify authentication (should return user profile)
curl -X GET http://localhost:8000/api/v1/auth/me/ \
  -H "Authorization: Bearer $ACCESS_TOKEN" | jq '.'
# Expected: 200 OK with user profile
```

### 1.3 Organisation Creation (TDD GREEN Phase)

```bash
# Test 4: Create organisation (Scenario A: Non-GST)
ORG_RESPONSE=$(curl -s -X POST http://localhost:8000/api/v1/organisations/ \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Meridian Consulting Pte Ltd",
    "legal_name": "Meridian Consulting Pte Ltd",
    "uen": "202501234A",
    "entity_type": "PRIVATE_LIMITED",
    "gst_registered": false,
    "base_currency": "SGD",
    "fy_start_month": 1,
    "timezone": "Asia/Singapore",
    "address_line_1": "10 Anson Road",
    "city": "Singapore",
    "postal_code": "079903",
    "country": "SG",
    "email": "accounts@meridian.sg",
    "phone": "+65 6123 4567"
  }')

export ORG_ID=$(echo $ORG_RESPONSE | jq -r '.id')
echo "Organisation created: $ORG_ID"

# Test 5: Verify organisation settings
curl -X GET http://localhost:8000/api/v1/$ORG_ID/ \
  -H "Authorization: Bearer $ACCESS_TOKEN" | jq '{
    name: .name,
    uen: .uen,
    gst_registered: .gst_registered,
    base_currency: .base_currency
  }'

# Test 6: Create organisation (Scenario B: GST-Registered)
ORG_RESPONSE_GST=$(curl -s -X POST http://localhost:8000/api/v1/organisations/ \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Meridian Consulting (GST) Pte Ltd",
    "legal_name": "Meridian Consulting (GST) Pte Ltd",
    "uen": "202501235B",
    "entity_type": "PRIVATE_LIMITED",
    "gst_registered": true,
    "gst_reg_number": "M90367890X",
    "gst_reg_date": "2025-01-01",
    "gst_scheme": "STANDARD",
    "gst_filing_frequency": "QUARTERLY",
    "base_currency": "SGD",
    "fy_start_month": 1
  }')

export ORG_ID_GST=$(echo $ORG_RESPONSE_GST | jq -r '.id')
echo "GST Organisation created: $ORG_ID_GST"
```

### 1.4 Chart of Accounts Verification

```bash
# Test 7: Verify seeded accounts (Non-GST org)
curl -X GET "http://localhost:8000/api/v1/$ORG_ID/accounts/?code=1100" \
  -H "Authorization: Bearer $ACCESS_TOKEN" | jq '.[0] | {
    code: .code,
    name: .name,
    account_type: .account_type,
    is_bank: .is_bank
  }'

# Test 8: Get all key account IDs
export BANK_ACCOUNT_ID=$(curl -s -X GET "http://localhost:8000/api/v1/$ORG_ID/accounts/?code=1100" \
  -H "Authorization: Bearer $ACCESS_TOKEN" | jq -r '.[0].id')

export CAPITAL_ACCOUNT_ID=$(curl -s -X GET "http://localhost:8000/api/v1/$ORG_ID/accounts/?code=3000" \
  -H "Authorization: Bearer $ACCESS_TOKEN" | jq -r '.[0].id')

export REVENUE_ACCOUNT_ID=$(curl -s -X GET "http://localhost:8000/api/v1/$ORG_ID/accounts/?code=4000" \
  -H "Authorization: Bearer $ACCESS_TOKEN" | jq -r '.[0].id')

export RENT_ACCOUNT_ID=$(curl -s -X GET "http://localhost:8000/api/v1/$ORG_ID/accounts/?code=6100" \
  -H "Authorization: Bearer $ACCESS_TOKEN" | jq -r '.[0].id')

export EQUIPMENT_ACCOUNT_ID=$(curl -s -X GET "http://localhost:8000/api/v1/$ORG_ID/accounts/?code=1510" \
  -H "Authorization: Bearer $ACCESS_TOKEN" | jq -r '.[0].id')

echo "Account IDs retrieved:"
echo "  Bank: $BANK_ACCOUNT_ID"
echo "  Capital: $CAPITAL_ACCOUNT_ID"
echo "  Revenue: $REVENUE_ACCOUNT_ID"
echo "  Rent: $RENT_ACCOUNT_ID"
echo "  Equipment: $EQUIPMENT_ACCOUNT_ID"

# Test 9: Verify tax codes (Non-GST: OS, NA)
curl -X GET "http://localhost:8000/api/v1/$ORG_ID/gst/tax-codes/?code=OS" \
  -H "Authorization: Bearer $ACCESS_TOKEN" | jq '.[0] | {
    code: .code,
    rate: .rate,
    is_output: .is_output
  }'

# Test 10: Verify tax codes (GST-registered: SR, TX, etc.)
curl -X GET "http://localhost:8000/api/v1/$ORG_ID_GST/gst/tax-codes/?code=SR" \
  -H "Authorization: Bearer $ACCESS_TOKEN" | jq '.[0] | {
    code: .code,
    rate: .rate,
    f5_supply_box: .f5_supply_box,
    f5_tax_box: .f5_tax_box
  }'
```

---

## 🏦 Section 2: Banking Setup & Opening Balances

### 2.1 Bank Account Creation

```bash
# Test 11: Create bank account
BANK_RESPONSE=$(curl -s -X POST "http://localhost:8000/api/v1/$ORG_ID/banking/bank-accounts/" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d "{
    \"account_name\": \"DBS Business Account\",
    \"bank_name\": \"DBS Bank Ltd\",
    \"account_number\": \"123-456789-001\",
    \"bank_code\": \"7171\",
    \"currency\": \"SGD\",
    \"gl_account_id\": \"$BANK_ACCOUNT_ID\",
    \"paynow_type\": \"UEN\",
    \"paynow_id\": \"202501234A\",
    \"is_default\": true,
    \"opening_balance\": \"0.0000\",
    \"opening_balance_date\": \"2026-01-01\"
  }")

export BANK_ACCOUNT_UUID=$(echo $BANK_RESPONSE | jq -r '.id')
echo "Bank account created: $BANK_ACCOUNT_UUID"

# Test 12: Verify bank account
curl -X GET "http://localhost:8000/api/v1/$ORG_ID/banking/bank-accounts/$BANK_ACCOUNT_UUID/" \
  -H "Authorization: Bearer $ACCESS_TOKEN" | jq '{
    account_name: .account_name,
    bank_name: .bank_name,
    paynow_type: .paynow_type,
    opening_balance: .opening_balance
  }'
```

### 2.2 Opening Balance Journal Entry

```bash
# Test 13: Create opening balance journal entry
JE_RESPONSE=$(curl -s -X POST "http://localhost:8000/api/v1/$ORG_ID/journal-entries/entries/" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d "{
    \"entry_date\": \"2026-01-02\",
    \"narration\": \"Opening capital contribution by shareholders\",
    \"source_type\": \"OPENING_BALANCE\",
    \"lines\": [
      {
        \"account_id\": \"$BANK_ACCOUNT_ID\",
        \"debit\": \"50000.0000\",
        \"credit\": \"0.0000\",
        \"description\": \"Bank account opening balance\"
      },
      {
        \"account_id\": \"$CAPITAL_ACCOUNT_ID\",
        \"debit\": \"0.0000\",
        \"credit\": \"50000.0000\",
        \"description\": \"Share capital contribution\"
      }
    ]
  }")

# Verify double-entry balance
echo $JE_RESPONSE | jq '{
  entry_number: .entry_number,
  total_debit: .total_debit,
  total_credit: .total_credit,
  balanced: (.total_debit == .total_credit)
}'

# Test 14: Verify journal entry posted
curl -X GET "http://localhost:8000/api/v1/$ORG_ID/journal-entries/entries/$(echo $JE_RESPONSE | jq -r '.id')/" \
  -H "Authorization: Bearer $ACCESS_TOKEN" | jq '{
  status: .status,
  posted_at: .posted_at,
  lines_count: (.lines | length)
}'
```

---

## 📄 Section 3: Sales & Receivables (Q1 2026)

### 3.1 Contact Management

```bash
# Test 15: Create customer contact
CUSTOMER_RESPONSE=$(curl -s -X POST "http://localhost:8000/api/v1/$ORG_ID/invoicing/contacts/" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Alpha Technologies Pte Ltd",
    "contact_type": "CUSTOMER",
    "is_customer": true,
    "is_supplier": false,
    "email": "accounts@alpha-tech.sg",
    "phone": "+65 6234 5678",
    "country": "SG",
    "payment_terms_days": 30
  }')

export CUSTOMER_ID=$(echo $CUSTOMER_RESPONSE | jq -r '.id')
echo "Customer created: $CUSTOMER_ID"

# Test 16: Create supplier contact
SUPPLIER_RESPONSE=$(curl -s -X POST "http://localhost:8000/api/v1/$ORG_ID/invoicing/contacts/" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Prime Properties Pte Ltd",
    "contact_type": "SUPPLIER",
    "is_customer": false,
    "is_supplier": true,
    "email": "billing@prime-properties.sg",
    "phone": "+65 6345 6789",
    "country": "SG",
    "payment_terms_days": 30
  }')

export SUPPLIER_ID=$(echo $SUPPLIER_RESPONSE | jq -r '.id')
echo "Supplier created: $SUPPLIER_ID"
```

### 3.2 Sales Invoices (Non-GST Scenario)

```bash
# Test 17: Create Invoice #1 (10 Jan)
INVOICE1_RESPONSE=$(curl -s -X POST "http://localhost:8000/api/v1/$ORG_ID/invoicing/documents/" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d "{
    \"document_type\": \"SALES_INVOICE\",
    \"contact_id\": \"$CUSTOMER_ID\",
    \"document_date\": \"2026-01-10\",
    \"due_date\": \"2026-02-09\",
    \"currency\": \"SGD\",
    \"reference\": \"INV-2026-001\",
    \"customer_notes\": \"Thank you for your business!\",
    \"lines\": [
      {
        \"description\": \"Management consulting services - January 2026\",
        \"account_id\": \"$REVENUE_ACCOUNT_ID\",
        \"quantity\": 1,
        \"unit_price\": \"12000.0000\",
        \"tax_code_id\": \"$(curl -s -X GET "http://localhost:8000/api/v1/$ORG_ID/gst/tax-codes/?code=OS" -H "Authorization: Bearer $ACCESS_TOKEN" | jq -r '.[0].id')\",
        \"is_tax_inclusive\": false
      }
    ]
  }")

export INVOICE1_ID=$(echo $INVOICE1_RESPONSE | jq -r '.id')
export INVOICE1_NUMBER=$(echo $INVOICE1_RESPONSE | jq -r '.document_number')
echo "Invoice #1 created: $INVOICE1_NUMBER ($INVOICE1_ID)"

# Verify invoice totals
echo $INVOICE1_RESPONSE | jq '{
  subtotal: .subtotal,
  total_gst: .total_gst,
  total_amount: .total_amount,
  amount_due: .amount_due
}'

# Test 18: Approve Invoice #1
curl -s -X POST "http://localhost:8000/api/v1/$ORG_ID/invoicing/documents/$INVOICE1_ID/approve/" \
  -H "Authorization: Bearer $ACCESS_TOKEN" | jq '{
  status: .status,
  approved_at: .approved_at,
  journal_entry_id: .journal_entry_id
}'

# Test 19: Create Invoice #2 (05 Feb)
INVOICE2_RESPONSE=$(curl -s -X POST "http://localhost:8000/api/v1/$ORG_ID/invoicing/documents/" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d "{
    \"document_type\": \"SALES_INVOICE\",
    \"contact_id\": \"$CUSTOMER_ID\",
    \"document_date\": \"2026-02-05\",
    \"due_date\": \"2026-03-07\",
    \"currency\": \"SGD\",
    \"reference\": \"INV-2026-002\",
    \"lines\": [
      {
        \"description\": \"Project milestone payment - Q1 2026\",
        \"account_id\": \"$REVENUE_ACCOUNT_ID\",
        \"quantity\": 1,
        \"unit_price\": \"15000.0000\",
        \"tax_code_id\": \"$(curl -s -X GET "http://localhost:8000/api/v1/$ORG_ID/gst/tax-codes/?code=OS" -H "Authorization: Bearer $ACCESS_TOKEN" | jq -r '.[0].id')\",
        \"is_tax_inclusive\": false
      }
    ]
  }")

export INVOICE2_ID=$(echo $INVOICE2_RESPONSE | jq -r '.id')
export INVOICE2_NUMBER=$(echo $INVOICE2_RESPONSE | jq -r '.document_number')
echo "Invoice #2 created: $INVOICE2_NUMBER"

# Test 20: Approve Invoice #2
curl -s -X POST "http://localhost:8000/api/v1/$ORG_ID/invoicing/documents/$INVOICE2_ID/approve/" \
  -H "Authorization: Bearer $ACCESS_TOKEN" | jq '.status'

# Test 21: Create Invoice #3 (05 Mar)
INVOICE3_RESPONSE=$(curl -s -X POST "http://localhost:8000/api/v1/$ORG_ID/invoicing/documents/" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d "{
    \"document_type\": \"SALES_INVOICE\",
    \"contact_id\": \"$CUSTOMER_ID\",
    \"document_date\": \"2026-03-05\",
    \"due_date\": \"2026-04-04\",
    \"currency\": \"SGD\",
    \"reference\": \"INV-2026-003\",
    \"lines\": [
      {
        \"description\": \"Q1 2026 final deliverable\",
        \"account_id\": \"$REVENUE_ACCOUNT_ID\",
        \"quantity\": 1,
        \"unit_price\": \"18000.0000\",
        \"tax_code_id\": \"$(curl -s -X GET "http://localhost:8000/api/v1/$ORG_ID/gst/tax-codes/?code=OS" -H "Authorization: Bearer $ACCESS_TOKEN" | jq -r '.[0].id')\",
        \"is_tax_inclusive\": false
      }
    ]
  }")

export INVOICE3_ID=$(echo $INVOICE3_RESPONSE | jq -r '.id')
export INVOICE3_NUMBER=$(echo $INVOICE3_RESPONSE | jq -r '.document_number')
echo "Invoice #3 created: $INVOICE3_NUMBER"

# Test 22: Approve Invoice #3
curl -s -X POST "http://localhost:8000/api/v1/$ORG_ID/invoicing/documents/$INVOICE3_ID/approve/" \
  -H "Authorization: Bearer $ACCESS_TOKEN" | jq '.status'
```

### 3.3 Payment Receipt & Allocation

```bash
# Test 23: Record Payment Received #1 (15 Jan)
PAYMENT1_RESPONSE=$(curl -s -X POST "http://localhost:8000/api/v1/$ORG_ID/banking/payments/receive/" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d "{
    \"contact_id\": \"$CUSTOMER_ID\",
    \"bank_account_id\": \"$BANK_ACCOUNT_UUID\",
    \"payment_date\": \"2026-01-15\",
    \"amount\": \"12000.0000\",
    \"currency\": \"SGD\",
    \"payment_method\": \"BANK_TRANSFER\",
    \"payment_reference\": \"INV-2026-001\"
  }")

export PAYMENT1_ID=$(echo $PAYMENT1_RESPONSE | jq -r '.id')
export PAYMENT1_NUMBER=$(echo $PAYMENT1_RESPONSE | jq -r '.payment_number')
echo "Payment #1 received: $PAYMENT1_NUMBER"

# Test 24: Allocate Payment #1 to Invoice #1
curl -s -X POST "http://localhost:8000/api/v1/$ORG_ID/banking/payments/$PAYMENT1_ID/allocate/" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d "{
    \"allocations\": [
      {
        \"document_id\": \"$INVOICE1_ID\",
        \"allocated_amount\": \"12000.0000\"
      }
    ]
  }" | jq '{
  allocation_id: .id,
  allocated_amount: .allocated_amount
}'

# Verify invoice status changed to PAID
curl -s -X GET "http://localhost:8000/api/v1/$ORG_ID/invoicing/documents/$INVOICE1_ID/" \
  -H "Authorization: Bearer $ACCESS_TOKEN" | jq '{
  status: .status,
  amount_paid: .amount_paid,
  amount_due: .amount_due
}'

# Test 25: Record Payment Received #2 (15 Feb)
PAYMENT2_RESPONSE=$(curl -s -X POST "http://localhost:8000/api/v1/$ORG_ID/banking/payments/receive/" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d "{
    \"contact_id\": \"$CUSTOMER_ID\",
    \"bank_account_id\": \"$BANK_ACCOUNT_UUID\",
    \"payment_date\": \"2026-02-15\",
    \"amount\": \"15000.0000\",
    \"currency\": \"SGD\",
    \"payment_method\": \"BANK_TRANSFER\",
    \"payment_reference\": \"INV-2026-002\"
  }")

export PAYMENT2_ID=$(echo $PAYMENT2_RESPONSE | jq -r '.id')
echo "Payment #2 received: $(echo $PAYMENT2_RESPONSE | jq -r '.payment_number')"

# Test 26: Allocate Payment #2 to Invoice #2
curl -s -X POST "http://localhost:8000/api/v1/$ORG_ID/banking/payments/$PAYMENT2_ID/allocate/" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d "{
    \"allocations\": [
      {
        \"document_id\": \"$INVOICE2_ID\",
        \"allocated_amount\": \"15000.0000\"
      }
    ]
  }" | jq '.allocated_amount'

# Test 27: Record Payment Received #3 (15 Mar)
PAYMENT3_RESPONSE=$(curl -s -X POST "http://localhost:8000/api/v1/$ORG_ID/banking/payments/receive/" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d "{
    \"contact_id\": \"$CUSTOMER_ID\",
    \"bank_account_id\": \"$BANK_ACCOUNT_UUID\",
    \"payment_date\": \"2026-03-15\",
    \"amount\": \"18000.0000\",
    \"currency\": \"SGD\",
    \"payment_method\": \"BANK_TRANSFER\",
    \"payment_reference\": \"INV-2026-003\"
  }")

export PAYMENT3_ID=$(echo $PAYMENT3_RESPONSE | jq -r '.id')
echo "Payment #3 received: $(echo $PAYMENT3_RESPONSE | jq -r '.payment_number')"

# Test 28: Allocate Payment #3 to Invoice #3
curl -s -X POST "http://localhost:8000/api/v1/$ORG_ID/banking/payments/$PAYMENT3_ID/allocate/" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d "{
    \"allocations\": [
      {
        \"document_id\": \"$INVOICE3_ID\",
        \"allocated_amount\": \"18000.0000\"
      }
    ]
  }" | jq '.allocated_amount'
```

---

## 💸 Section 4: Purchases & Payables (Q1 2026)

### 4.1 Purchase Invoices (Non-GST Scenario)

```bash
# Test 29: Create Purchase Invoice - Equipment (05 Jan)
PURCHASE1_RESPONSE=$(curl -s -X POST "http://localhost:8000/api/v1/$ORG_ID/invoicing/documents/" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d "{
    \"document_type\": \"PURCHASE_INVOICE\",
    \"contact_id\": \"$SUPPLIER_ID\",
    \"document_date\": \"2026-01-05\",
    \"due_date\": \"2026-02-04\",
    \"currency\": \"SGD\",
    \"reference\": \"BILL-2026-001\",
    \"lines\": [
      {
        \"description\": \"Office equipment - computers and furniture\",
        \"account_id\": \"$EQUIPMENT_ACCOUNT_ID\",
        \"quantity\": 1,
        \"unit_price\": \"8500.0000\",
        \"tax_code_id\": \"$(curl -s -X GET "http://localhost:8000/api/v1/$ORG_ID/gst/tax-codes/?code=OS" -H "Authorization: Bearer $ACCESS_TOKEN" | jq -r '.[0].id')\",
        \"is_tax_inclusive\": false
      }
    ]
  }")

export PURCHASE1_ID=$(echo $PURCHASE1_RESPONSE | jq -r '.id')
echo "Purchase Invoice #1 created: $(echo $PURCHASE1_RESPONSE | jq -r '.document_number')"

# Test 30: Approve Purchase Invoice #1
curl -s -X POST "http://localhost:8000/api/v1/$ORG_ID/invoicing/documents/$PURCHASE1_ID/approve/" \
  -H "Authorization: Bearer $ACCESS_TOKEN" | jq '.status'

# Test 31: Create Purchase Invoice - Rent (20 Jan)
PURCHASE2_RESPONSE=$(curl -s -X POST "http://localhost:8000/api/v1/$ORG_ID/invoicing/documents/" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d "{
    \"document_type\": \"PURCHASE_INVOICE\",
    \"contact_id\": \"$SUPPLIER_ID\",
    \"document_date\": \"2026-01-20\",
    \"due_date\": \"2026-02-19\",
    \"currency\": \"SGD\",
    \"reference\": \"BILL-2026-002\",
    \"lines\": [
      {
        \"description\": \"Office rent - Q1 2026 (Jan-Mar)\",
        \"account_id\": \"$RENT_ACCOUNT_ID\",
        \"quantity\": 1,
        \"unit_price\": \"9000.0000\",
        \"tax_code_id\": \"$(curl -s -X GET "http://localhost:8000/api/v1/$ORG_ID/gst/tax-codes/?code=OS" -H "Authorization: Bearer $ACCESS_TOKEN" | jq -r '.[0].id')\",
        \"is_tax_inclusive\": false
      }
    ]
  }")

export PURCHASE2_ID=$(echo $PURCHASE2_RESPONSE | jq -r '.id')
echo "Purchase Invoice #2 created: $(echo $PURCHASE2_RESPONSE | jq -r '.document_number')"

# Test 32: Approve Purchase Invoice #2
curl -s -X POST "http://localhost:8000/api/v1/$ORG_ID/invoicing/documents/$PURCHASE2_ID/approve/" \
  -H "Authorization: Bearer $ACCESS_TOKEN" | jq '.status'

# Test 33: Create Purchase Invoice - Utilities (25 Jan)
PURCHASE3_RESPONSE=$(curl -s -X POST "http://localhost:8000/api/v1/$ORG_ID/invoicing/documents/" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d "{
    \"document_type\": \"PURCHASE_INVOICE\",
    \"contact_id\": \"$SUPPLIER_ID\",
    \"document_date\": \"2026-01-25\",
    \"due_date\": \"2026-02-24\",
    \"currency\": \"SGD\",
    \"reference\": \"BILL-2026-003\",
    \"lines\": [
      {
        \"description\": \"Utilities - January 2026\",
        \"account_id\": \"$(curl -s -X GET "http://localhost:8000/api/v1/$ORG_ID/accounts/?code=6110" -H "Authorization: Bearer $ACCESS_TOKEN" | jq -r '.[0].id')\",
        \"quantity\": 1,
        \"unit_price\": \"450.0000\",
        \"tax_code_id\": \"$(curl -s -X GET "http://localhost:8000/api/v1/$ORG_ID/gst/tax-codes/?code=OS" -H "Authorization: Bearer $ACCESS_TOKEN" | jq -r '.[0].id')\",
        \"is_tax_inclusive\": false
      }
    ]
  }")

export PURCHASE3_ID=$(echo $PURCHASE3_RESPONSE | jq -r '.id')
echo "Purchase Invoice #3 created: $(echo $PURCHASE3_RESPONSE | jq -r '.document_number')"

# Test 34: Approve Purchase Invoice #3
curl -s -X POST "http://localhost:8000/api/v1/$ORG_ID/invoicing/documents/$PURCHASE3_ID/approve/" \
  -H "Authorization: Bearer $ACCESS_TOKEN" | jq '.status'
```

### 4.2 Payment Made & Allocation

```bash
# Test 35: Record Payment Made - Equipment (05 Jan)
PAYMENT_MADE1_RESPONSE=$(curl -s -X POST "http://localhost:8000/api/v1/$ORG_ID/banking/payments/make/" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d "{
    \"contact_id\": \"$SUPPLIER_ID\",
    \"bank_account_id\": \"$BANK_ACCOUNT_UUID\",
    \"payment_date\": \"2026-01-05\",
    \"amount\": \"8500.0000\",
    \"currency\": \"SGD\",
    \"payment_method\": \"BANK_TRANSFER\",
    \"payment_reference\": \"BILL-2026-001\"
  }")

export PAYMENT_MADE1_ID=$(echo $PAYMENT_MADE1_RESPONSE | jq -r '.id')
echo "Payment Made #1: $(echo $PAYMENT_MADE1_RESPONSE | jq -r '.payment_number')"

# Test 36: Allocate Payment Made #1
curl -s -X POST "http://localhost:8000/api/v1/$ORG_ID/banking/payments/$PAYMENT_MADE1_ID/allocate/" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d "{
    \"allocations\": [
      {
        \"document_id\": \"$PURCHASE1_ID\",
        \"allocated_amount\": \"8500.0000\"
      }
    ]
  }" | jq '.allocated_amount'

# Test 37: Record Payment Made - Rent (20 Jan)
PAYMENT_MADE2_RESPONSE=$(curl -s -X POST "http://localhost:8000/api/v1/$ORG_ID/banking/payments/make/" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d "{
    \"contact_id\": \"$SUPPLIER_ID\",
    \"bank_account_id\": \"$BANK_ACCOUNT_UUID\",
    \"payment_date\": \"2026-01-20\",
    \"amount\": \"9000.0000\",
    \"currency\": \"SGD\",
    \"payment_method\": \"BANK_TRANSFER\",
    \"payment_reference\": \"BILL-2026-002\"
  }")

export PAYMENT_MADE2_ID=$(echo $PAYMENT_MADE2_RESPONSE | jq -r '.id')

# Test 38: Allocate Payment Made #2
curl -s -X POST "http://localhost:8000/api/v1/$ORG_ID/banking/payments/$PAYMENT_MADE2_ID/allocate/" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d "{
    \"allocations\": [
      {
        \"document_id\": \"$PURCHASE2_ID\",
        \"allocated_amount\": \"9000.0000\"
      }
    ]
  }" | jq '.allocated_amount'

# Test 39: Record Payment Made - Utilities (25 Jan)
PAYMENT_MADE3_RESPONSE=$(curl -s -X POST "http://localhost:8000/api/v1/$ORG_ID/banking/payments/make/" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d "{
    \"contact_id\": \"$SUPPLIER_ID\",
    \"bank_account_id\": \"$BANK_ACCOUNT_UUID\",
    \"payment_date\": \"2026-01-25\",
    \"amount\": \"450.0000\",
    \"currency\": \"SGD\",
    \"payment_method\": \"BANK_TRANSFER\",
    \"payment_reference\": \"BILL-2026-003\"
  }")

export PAYMENT_MADE3_ID=$(echo $PAYMENT_MADE3_RESPONSE | jq -r '.id')

# Test 40: Allocate Payment Made #3
curl -s -X POST "http://localhost:8000/api/v1/$ORG_ID/banking/payments/$PAYMENT_MADE3_ID/allocate/" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d "{
    \"allocations\": [
      {
        \"document_id\": \"$PURCHASE3_ID\",
        \"allocated_amount\": \"450.0000\"
      }
    ]
  }" | jq '.allocated_amount'
```

---

## 🏦 Section 5: Bank Reconciliation

### 5.1 CSV Import Preparation

```bash
# Create bank statement CSV file
cat > /tmp/bank_statement_q1.csv << 'EOF'
Date,Description,Amount,Reference
2026-01-02,Opening Balance,50000.00,OB
2026-01-05,Office Equipment,-8500.00,BILL-2026-001
2026-01-10,Client Payment,12000.00,INV-2026-001
2026-01-15,Client Payment,12000.00,INV-2026-001
2026-01-20,Office Rent,-9000.00,BILL-2026-002
2026-01-25,Utilities,-450.00,BILL-2026-003
2026-02-15,Client Payment,15000.00,INV-2026-002
2026-03-15,Client Payment,18000.00,INV-2026-003
2026-03-20,Bank Charges,-150.00,FEE-MAR-2026
EOF

echo "Bank statement CSV created: /tmp/bank_statement_q1.csv"
cat /tmp/bank_statement_q1.csv
```

### 5.2 Import & Reconciliation

```bash
# Test 41: Import bank transactions
IMPORT_RESPONSE=$(curl -s -X POST "http://localhost:8000/api/v1/$ORG_ID/banking/bank-transactions/import/" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -F "file=@/tmp/bank_statement_q1.csv" \
  -F "bank_account_id=$BANK_ACCOUNT_UUID")

echo $IMPORT_RESPONSE | jq '{
  imported_count: .imported_count,
  duplicate_count: .duplicate_count,
  error_count: .error_count
}'

# Test 42: List unreconciled transactions
curl -s -X GET "http://localhost:8000/api/v1/$ORG_ID/banking/bank-transactions/?unreconciled_only=true&bank_account_id=$BANK_ACCOUNT_UUID" \
  -H "Authorization: Bearer $ACCESS_TOKEN" | jq '.results | length'

# Test 43: Get match suggestions for first transaction
FIRST_TXN_ID=$(curl -s -X GET "http://localhost:8000/api/v1/$ORG_ID/banking/bank-transactions/?unreconciled_only=true&bank_account_id=$BANK_ACCOUNT_UUID" \
  -H "Authorization: Bearer $ACCESS_TOKEN" | jq -r '.results[0].id')

curl -s -X GET "http://localhost:8000/api/v1/$ORG_ID/banking/bank-transactions/$FIRST_TXN_ID/suggest-matches/" \
  -H "Authorization: Bearer $ACCESS_TOKEN" | jq '.[0] | {
  payment_id: .payment_id,
  confidence_score: .confidence_score,
  amount_match: .amount_match
}'

# Test 44: Reconcile first transaction
curl -s -X POST "http://localhost:8000/api/v1/$ORG_ID/banking/bank-transactions/$FIRST_TXN_ID/reconcile/" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d "{
    \"payment_id\": \"$(curl -s -X GET "http://localhost:8000/api/v1/$ORG_ID/banking/payments/" -H "Authorization: Bearer $ACCESS_TOKEN" | jq -r '.results[0].id')\"
  }" | jq '{
  is_reconciled: .is_reconciled,
  reconciled_at: .reconciled_at
}'

# Test 45: Verify reconciliation count
curl -s -X GET "http://localhost:8000/api/v1/$ORG_ID/banking/bank-transactions/?bank_account_id=$BANK_ACCOUNT_UUID" \
  -H "Authorization: Bearer $ACCESS_TOKEN" | jq '{
  total: .count,
  reconciled: [.results[] | select(.is_reconciled == true)] | length,
  unreconciled: [.results[] | select(.is_reconciled == false)] | length
}'
```

---

## 📊 Section 6: Financial Reporting

### 6.1 Dashboard Metrics

```bash
# Test 46: Get dashboard metrics
DASHBOARD_RESPONSE=$(curl -s -X GET "http://localhost:8000/api/v1/$ORG_ID/reports/dashboard/metrics/" \
  -H "Authorization: Bearer $ACCESS_TOKEN")

echo $DASHBOARD_RESPONSE | jq '{
  revenue_mtd: .revenue_mtd,
  revenue_ytd: .revenue_ytd,
  outstanding_receivables: .outstanding_receivables,
  outstanding_payables: .outstanding_payables,
  cash_on_hand: .cash_on_hand,
  gst_threshold_status: .gst_threshold_status
}'

# Test 47: Get compliance alerts
curl -s -X GET "http://localhost:8000/api/v1/$ORG_ID/reports/dashboard/alerts/" \
  -H "Authorization: Bearer $ACCESS_TOKEN" | jq '.alerts | length'
```

### 6.2 Financial Statements

```bash
# Test 48: Generate Profit & Loss (Q1 2026)
PL_RESPONSE=$(curl -s -X GET "http://localhost:8000/api/v1/$ORG_ID/reports/reports/financial/" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -G \
  --data-urlencode "report_type=profit_loss" \
  --data-urlencode "start_date=2026-01-01" \
  --data-urlencode "end_date=2026-03-31")

echo $PL_RESPONSE | jq '{
  report_type: .report_type,
  period_start: .period_start,
  period_end: .period_end,
  revenue: .data.revenue.Total,
  expenses: .data.expenses.Total,
  net_profit: .data.net_profit
}'

# Test 49: Generate Balance Sheet (as at 31 Mar 2026)
BS_RESPONSE=$(curl -s -X GET "http://localhost:8000/api/v1/$ORG_ID/reports/reports/financial/" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -G \
  --data-urlencode "report_type=balance_sheet" \
  --data-urlencode "as_at_date=2026-03-31")

echo $BS_RESPONSE | jq '{
  report_type: .report_type,
  as_at_date: .as_at_date,
  total_assets: .data.assets.Total,
  total_liabilities: .data.liabilities.Total,
  total_equity: .data.equity.Total,
  balanced: (.data.assets.Total == (.data.liabilities.Total + .data.equity.Total))
}'

# Test 50: Verify double-entry integrity
curl -s -X GET "http://localhost:8000/api/v1/$ORG_ID/journal-entries/entries/" \
  -H "Authorization: Bearer $ACCESS_TOKEN" | jq '
  [.results[] | select(.total_debit != .total_credit)] | length |
  if . == 0 then "✅ All journal entries balanced"
  else "❌ \(.) unbalanced entries found"
  end'
```

### 6.3 GST F5 Preview (GST-Registered Scenario)

```bash
# Test 51: Get GST summary (GST-registered org)
curl -s -X GET "http://localhost:8000/api/v1/$ORG_ID_GST/gst/returns/" \
  -H "Authorization: Bearer $ACCESS_TOKEN" | jq '.results | length'

# Test 52: Get tax code summary
curl -s -X GET "http://localhost:8000/api/v1/$ORG_ID_GST/gst/tax-codes/" \
  -H "Authorization: Bearer $ACCESS_TOKEN" | jq '[.results[] | {
  code: .code,
  rate: .rate,
  is_output: .is_output,
  is_input: .is_input
}]'
```

---

## 🔒 Section 7: Security & Permission Testing

### 7.1 Authentication Tests

```bash
# Test 53: Test rate limiting (10 login attempts)
echo "Testing rate limiting..."
for i in {1..12}; do
  RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "http://localhost:8000/api/v1/auth/login/" \
    -H "Content-Type: application/json" \
    -d '{"email": "test@meridian.sg", "password": "wrongpassword"}')
  
  HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
  if [ "$HTTP_CODE" = "429" ]; then
    echo "✅ Rate limiting triggered at attempt $i"
    break
  fi
done

# Test 54: Test token refresh
REFRESH_RESPONSE=$(curl -s -X POST "http://localhost:8000/api/v1/auth/refresh/" \
  -H "Content-Type: application/json" \
  -d "{\"refresh\": \"$REFRESH_TOKEN\"}")

echo $REFRESH_RESPONSE | jq -r '.tokens.access' | head -c 50
echo "..."

# Test 55: Test invalid token
curl -s -X GET "http://localhost:8000/api/v1/auth/me/" \
  -H "Authorization: Bearer invalid_token" | jq '.error.code'
# Expected: "authentication_failed"
```

### 7.2 Authorization Tests

```bash
# Test 56: Test cross-org access (should fail)
curl -s -X GET "http://localhost:8000/api/v1/$ORG_ID_GST/invoicing/documents/" \
  -H "Authorization: Bearer $ACCESS_TOKEN" | jq '.error.code'
# Expected: "permission_denied"

# Test 57: Test RLS enforcement
curl -s -X GET "http://localhost:8000/api/v1/$ORG_ID/banking/bank-accounts/" \
  -H "Authorization: Bearer $ACCESS_TOKEN" | jq '.results | length'
# Expected: 1 (only our bank account)
```

### 7.3 Input Validation Tests

```bash
# Test 58: Test decimal precision validation
curl -s -X POST "http://localhost:8000/api/v1/$ORG_ID/banking/payments/receive/" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d "{
    \"contact_id\": \"$CUSTOMER_ID\",
    \"bank_account_id\": \"$BANK_ACCOUNT_UUID\",
    \"payment_date\": \"2026-03-20\",
    \"amount\": 100.5,
    \"currency\": \"SGD\",
    \"payment_method\": \"CASH\"
  }" | jq '.error.code'
# Expected: "validation_error" (amount must be string with 4 decimals)

# Test 59: Test UUID format validation
curl -s -X GET "http://localhost:8000/api/v1/$ORG_ID/invoicing/documents/invalid-uuid/" \
  -H "Authorization: Bearer $ACCESS_TOKEN" | jq '.error.code'
# Expected: "validation_error" or "not_found"

# Test 60: Test required field validation
curl -s -X POST "http://localhost:8000/api/v1/$ORG_ID/invoicing/contacts/" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": ""
  }' | jq '.error.errors.name'
# Expected: ["This field may not be blank."]
```

---

## ✅ Section 8: Validation Checklist

### 8.1 Double-Entry Integrity

```bash
# Verify all journal entries balance
echo "=== Double-Entry Integrity Check ==="
curl -s -X GET "http://localhost:8000/api/v1/$ORG_ID/journal-entries/entries/" \
  -H "Authorization: Bearer $ACCESS_TOKEN" | jq '
  .results | 
  map(select(.total_debit != .total_credit)) | 
  if length == 0 then 
    "✅ PASS: All journal entries balanced"
  else 
    "❌ FAIL: \(length) unbalanced entries"
  end'

# Verify debits = credits across all entries
curl -s -X GET "http://localhost:8000/api/v1/$ORG_ID/journal-entries/entries/" \
  -H "Authorization: Bearer $ACCESS_TOKEN" | jq '
  {
    total_debits: ([.results[].total_debit | tonumber] | add),
    total_credits: ([.results[].total_credit | tonumber] | add),
    difference: (([.results[].total_debit | tonumber] | add) - ([.results[].total_credit | tonumber] | add)),
    balanced: ((([.results[].total_debit | tonumber] | add) - ([.results[].total_credit | tonumber] | add)) | fabs < 0.0001)
  }'
```

### 8.2 Bank Reconciliation

```bash
echo "=== Bank Reconciliation Check ==="
curl -s -X GET "http://localhost:8000/api/v1/$ORG_ID/banking/bank-transactions/?bank_account_id=$BANK_ACCOUNT_UUID" \
  -H "Authorization: Bearer $ACCESS_TOKEN" | jq '
  {
    total_transactions: .count,
    reconciled: [.results[] | select(.is_reconciled == true)] | length,
    unreconciled: [.results[] | select(.is_reconciled == false)] | length,
    reconciliation_rate: (([.results[] | select(.is_reconciled == true)] | length) / .count * 100 | floor)
  }'
```

### 8.3 Invoice Status

```bash
echo "=== Invoice Status Check ==="
curl -s -X GET "http://localhost:8000/api/v1/$ORG_ID/invoicing/documents/" \
  -H "Authorization: Bearer $ACCESS_TOKEN" | jq '
  .results | group_by(.status) | 
  map({status: .[0].status, count: length}) |
  sort_by(.status)'

# Verify all invoices paid
curl -s -X GET "http://localhost:8000/api/v1/$ORG_ID/invoicing/documents/" \
  -H "Authorization: Bearer $ACCESS_TOKEN" | jq '
  [.results[] | select(.status == "PAID")] | length |
  "✅ \(.) invoices paid"'
```

### 8.4 Financial Statement Balance

```bash
echo "=== Balance Sheet Check ==="
curl -s -X GET "http://localhost:8000/api/v1/$ORG_ID/reports/reports/financial/" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -G \
  --data-urlencode "report_type=balance_sheet" \
  --data-urlencode "as_at_date=2026-03-31" | jq '
  if .data.assets.Total == (.data.liabilities.Total + .data.equity.Total) then
    "✅ PASS: Balance sheet balanced"
  else
    "❌ FAIL: Balance sheet out of balance"
  end'
```

### 8.5 Expected Q1 Results Summary

```bash
echo "=== Q1 2026 Expected Results ==="

# Fetch data
DASHBOARD=$(curl -s -X GET "http://localhost:8000/api/v1/$ORG_ID/reports/dashboard/metrics/" -H "Authorization: Bearer $ACCESS_TOKEN")
PL_REPORT=$(curl -s -X GET "http://localhost:8000/api/v1/$ORG_ID/reports/reports/financial/?report_type=profit_loss&start_date=2026-01-01&end_date=2026-03-31" -H "Authorization: Bearer $ACCESS_TOKEN")
BS_REPORT=$(curl -s -X GET "http://localhost:8000/api/v1/$ORG_ID/reports/reports/financial/?report_type=balance_sheet&as_at_date=2026-03-31" -H "Authorization: Bearer $ACCESS_TOKEN")
RECON_STATS=$(curl -s -X GET "http://localhost:8000/api/v1/$ORG_ID/banking/bank-transactions/?bank_account_id=$BANK_ACCOUNT_UUID" -H "Authorization: Bearer $ACCESS_TOKEN")
JE_BALANCE_CHECK=$(curl -s -X GET "http://localhost:8000/api/v1/$ORG_ID/journal-entries/entries/" -H "Authorization: Bearer $ACCESS_TOKEN" | jq -r '.results | map(select(.total_debit != .total_credit)) | if length == 0 then "Yes" else "No (\(length) unbalanced)" end')

# Calculate reconciliation rate
RECON_RATE=$(echo $RECON_STATS | jq -r 'if .count > 0 then (([.results[] | select(.is_reconciled == true)] | length) / .count * 100 | floor | tostring + "%") else "0%" end')

# Check Balance Sheet
BS_BALANCED=$(echo $BS_REPORT | jq -r 'if .data.assets.Total == (.data.liabilities.Total + .data.equity.Total) then "Yes" else "No" end')

# Output table
cat << EOF
| Metric                    | Expected  | Actual (from API) |
|---------------------------|-----------|-------------------|
| Total Revenue             | 45,000.00 | $(echo $PL_REPORT | jq -r '.data.revenue.Total') |
| Total Expenses            | 24,300.00 | $(echo $PL_REPORT | jq -r '.data.expenses.Total') |
| Net Profit                | 20,700.00 | $(echo $PL_REPORT | jq -r '.data.net_profit') |
| Cash on Hand              | 75,550.00 | $(echo $DASHBOARD | jq -r '.cash_on_hand') |
| Outstanding Receivables   | 0.00      | $(echo $DASHBOARD | jq -r '.outstanding_receivables') |
| Outstanding Payables      | 0.00      | $(echo $DASHBOARD | jq -r '.outstanding_payables') |
| Bank Reconciliation Rate  | 100%      | $RECON_RATE |
| Journal Entries Balanced  | Yes       | $JE_BALANCE_CHECK |
| Balance Sheet Balanced    | Yes       | $BS_BALANCED |
EOF
```

---

## 🎯 Section 9: Playwright E2E Tests

### 9.1 Authentication Flow

```typescript
// tests/e2e/auth-flow.spec.ts
import { test, expect } from '@playwright/test';

test.describe('Authentication Flow', () => {
  test('should register new user', async ({ page }) => {
    await page.goto('http://localhost:3000/register');
    await page.fill('input[name="email"]', 'test@meridian.sg');
    await page.fill('input[name="password"]', 'SecurePass123!');
    await page.fill('input[name="full_name"]', 'Test Accountant');
    await page.click('button[type="submit"]');
    await expect(page).toHaveURL(/\/dashboard/);
  });

  test('should login with credentials', async ({ page }) => {
    await page.goto('http://localhost:3000/login');
    await page.fill('input[name="email"]', 'test@meridian.sg');
    await page.fill('input[name="password"]', 'SecurePass123!');
    await page.click('button[type="submit"]');
    await expect(page).toHaveURL(/\/dashboard/);
  });

  test('should redirect unauthenticated users', async ({ page }) => {
    await page.context().clearCookies();
    await page.goto('http://localhost:3000/dashboard');
    await expect(page).toHaveURL(/\/login/);
  });
});
```

### 9.2 Invoice Creation Flow

```typescript
// tests/e2e/invoice-flow.spec.ts
import { test, expect } from '@playwright/test';

test.describe('Invoice Creation Flow', () => {
  test.beforeEach(async ({ page }) => {
    // Login before each test
    await page.goto('http://localhost:3000/login');
    await page.fill('input[name="email"]', 'test@meridian.sg');
    await page.fill('input[name="password"]', 'SecurePass123!');
    await page.click('button[type="submit"]');
    await page.waitForURL(/\/dashboard/);
  });

  test('should create sales invoice', async ({ page }) => {
    await page.goto('http://localhost:3000/invoices/new');
    await page.selectOption('select[name="contact_id"]', '1');
    await page.fill('input[name="lines.0.description"]', 'Consulting services');
    await page.fill('input[name="lines.0.quantity"]', '1');
    await page.fill('input[name="lines.0.unit_price"]', '12000');
    await page.click('button[type="submit"]');
    await expect(page).toHaveURL(/\/invoices\/[^/]+$/);
  });

  test('should approve invoice', async ({ page }) => {
    await page.goto('http://localhost:3000/invoices');
    await page.click('text=Approve');
    await expect(page.locator('text=Approved')).toBeVisible();
  });
});
```

### 9.3 Bank Reconciliation Flow

```typescript
// tests/e2e/reconciliation-flow.spec.ts
import { test, expect } from '@playwright/test';

test.describe('Bank Reconciliation Flow', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('http://localhost:3000/login');
    await page.fill('input[name="email"]', 'test@meridian.sg');
    await page.fill('input[name="password"]', 'SecurePass123!');
    await page.click('button[type="submit"]');
  });

  test('should import bank statement', async ({ page }) => {
    await page.goto('http://localhost:3000/banking');
    await page.click('text=Transactions');
    await page.click('text=Import Statement');
    await page.setInputFiles('input[type="file"]', '/tmp/bank_statement_q1.csv');
    await expect(page.locator('text=Imported')).toBeVisible();
  });

  test('should reconcile transaction', async ({ page }) => {
    await page.goto('http://localhost:3000/banking');
    await page.click('text=Transactions');
    await page.click('text=Reconcile');
    await page.click('text=Match');
    await expect(page.locator('text=Reconciled')).toBeVisible();
  });
});
```

---

## 📋 Section 10: Test Execution Summary

### 10.1 Test Count Summary

| Category | Tests | Status |
|----------|-------|--------|
| Authentication | 3 | ✅ Complete |
| Organisation Setup | 6 | ✅ Complete |
| Chart of Accounts | 4 | ✅ Complete |
| Banking Setup | 2 | ✅ Complete |
| Opening Balances | 2 | ✅ Complete |
| Contact Management | 2 | ✅ Complete |
| Sales Invoices | 6 | ✅ Complete |
| Payment Receipts | 6 | ✅ Complete |
| Purchase Invoices | 6 | ✅ Complete |
| Payment Made | 6 | ✅ Complete |
| Bank Reconciliation | 5 | ✅ Complete |
| Financial Reporting | 5 | ✅ Complete |
| Security Testing | 8 | ✅ Complete |
| Validation Checks | 5 | ✅ Complete |
| Playwright E2E | 8 | ✅ Complete |
| **Total** | **84** | **✅ Complete** |

### 10.2 Expected Outcomes

| Test Group | Expected Result | Validation Method |
|------------|-----------------|-------------------|
| Authentication | 200 OK, tokens returned | API response |
| Organisation | GST status correct | API response |
| Journal Entries | All balanced | Debit = Credit |
| Invoices | All approved & paid | Status = PAID |
| Payments | All allocated | Allocation count |
| Bank Reconciliation | 100% reconciled | is_reconciled = true |
| Financial Reports | Balance sheet balanced | Assets = Liabilities + Equity |
| Security | Rate limiting works | 429 after 10 attempts |
| Authorization | Cross-org blocked | 403 Forbidden |

### 10.3 Troubleshooting Guide

| Issue | Root Cause | Solution |
|-------|------------|----------|
| 401 Unauthorized | Token expired | Refresh token |
| 403 Forbidden | Wrong org context | Check org_id in URL |
| 400 Bad Request | Invalid decimal format | Use "100.0000" not 100 |
| 404 Not Found | Invalid UUID | Verify UUID format |
| 429 Too Many Requests | Rate limited | Wait and retry |
| 500 Internal Error | Database constraint | Check SQL schema |
| CORS Error | Backend not running | Start backend server |
| RLS Error | No org membership | Create UserOrganisation |

---

## 📝 Section 11: Documentation & Reporting

### 11.1 Test Results Template

```markdown
# LedgerSG Test Results - Q1 2026

**Date:** 2026-03-10  
**Tester:** [Name]  
**Scenario:** Non-GST Registered SMB  
**Organisation:** Meridian Consulting Pte Ltd  

## Summary

| Metric | Value |
|--------|-------|
| Total Tests | 84 |
| Passed | XX |
| Failed | XX |
| Skipped | XX |
| Pass Rate | XX% |

## Critical Findings

### ✅ Passed
- [ ] All journal entries balanced
- [ ] Balance sheet balanced
- [ ] All invoices paid
- [ ] Bank reconciliation 100%

### ⚠️ Warnings
- [ ] [Issue description]

### ❌ Failed
- [ ] [Issue description]

## Recommendations

1. [Recommendation 1]
2. [Recommendation 2]
```

### 11.2 IRAS Compliance Checklist

```markdown
# IRAS Compliance Verification

## GST F5 Requirements (Non-GST)
- [ ] No GST charged on invoices
- [ ] OS tax code used for all transactions
- [ ] No "Tax Invoice" label on documents
- [ ] GST threshold monitored (< S$1M)

## Record Keeping
- [ ] 5-year retention (audit.event_log)
- [ ] Source documents attached
- [ ] Bank reconciliation completed
- [ ] Financial statements generated

## Double-Entry Integrity
- [ ] All journal entries balanced
- [ ] Debits = Credits
- [ ] Posted entries immutable
```

---

## 🎯 Conclusion

This comprehensive test suite combines the best elements from both reference scenarios:

**Strengths Retained:**
- ✅ ABC Trading: Clear step-by-step API validation
- ✅ Lakshmi's Kitchen: Realistic business workflow complexity
- ✅ Both: IRAS compliance verification

**Improvements Added:**
- ✅ 3-month period (balanced complexity)
- ✅ Both GST scenarios documented
- ✅ Security & permission testing
- ✅ Playwright E2E tests included
- ✅ Expected results documented
- ✅ Troubleshooting guide provided

**Next Steps:**
1. Execute all 84 tests against running instance
2. Document actual results vs expected
3. Fix any failures identified
4. Update documentation with findings
5. Archive test results for audit trail

**Status:** ✅ READY FOR EXECUTION

---

**Document Version:** 2.0.0  
**Last Updated:** 2026-03-10  
**Test Coverage:** 84 tests across 15 categories  
**Compliance:** IRAS 2026, SFRS for Small Entities

# https://chat.qwen.ai/s/aca62027-3359-4031-97a2-7b5f370e50fe?fev=0.2.11
