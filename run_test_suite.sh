#!/bin/bash
# run_test_suite.sh - Automated execution of Singapore SMB workflow test suite

set -e

# Initialize Database for a clean run
echo "🧹 Initializing database..."
pkill -f manage.py || true
sleep 2
export PGPASSWORD=ledgersg_secret_to_change
dropdb -h localhost -U ledgersg ledgersg_dev --force 2>/dev/null || true
createdb -h localhost -U ledgersg ledgersg_dev
psql -h localhost -U ledgersg -d ledgersg_dev -f apps/backend/database_schema.sql > /dev/null
echo "✅ Database ready"

# Restart server
echo "🚀 Starting backend server..."
cd apps/backend
source /opt/venv/bin/activate
nohup python manage.py runserver 0.0.0.0:8000 > /tmp/backend_test_suite.log 2>&1 &
for i in {1..20}; do 
  if curl -s http://localhost:8000/api/v1/health/ > /dev/null; then 
    echo "✅ Server ready"; break; 
  fi; 
  sleep 1; 
done
cd ../..

API_BASE="http://localhost:8000/api/v1"
TEST_USER_EMAIL="test@meridian.sg"
TEST_USER_PASS="SecurePass123!"

echo "🚀 Starting LedgerSG Comprehensive Test Suite"
echo "=============================================="

# 1. Registration
echo -n "1. Registering user... "
REGISTER_RESPONSE=$(curl -s -X POST "$API_BASE/auth/register/" \
  -H "Content-Type: application/json" \
  -d "{
    \"email\": \"$TEST_USER_EMAIL\",
    \"password\": \"$TEST_USER_PASS\",
    \"full_name\": \"Test Accountant\"
  }")

if echo $REGISTER_RESPONSE | grep -q "id"; then
  echo "✅ Success"
elif echo $REGISTER_RESPONSE | grep -q "Email already registered"; then
  echo "✅ Already registered"
else
  echo "❌ Failed"
  echo $REGISTER_RESPONSE | jq '.'
  exit 1
fi

# 2. Login
echo -n "2. Logging in... "
LOGIN_RESPONSE=$(curl -s -X POST "$API_BASE/auth/login/" \
  -H "Content-Type: application/json" \
  -d "{
    \"email\": \"$TEST_USER_EMAIL\",
    \"password\": \"$TEST_USER_PASS\"
  }")

if echo $LOGIN_RESPONSE | grep -q "access"; then
  echo "✅ Success"
  ACCESS_TOKEN=$(echo $LOGIN_RESPONSE | jq -r '.tokens.access')
  REFRESH_TOKEN=$(echo $LOGIN_RESPONSE | jq -r '.tokens.refresh')
else
  echo "❌ Failed"
  echo $LOGIN_RESPONSE | jq '.'
  exit 1
fi

# 3. Create Organisation (Scenario A: Non-GST)
echo -n "3. Creating Non-GST Organisation... "
ORG_RESPONSE=$(curl -s -X POST "$API_BASE/organisations/" \
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

if echo $ORG_RESPONSE | grep -q "id"; then
  echo "✅ Success"
  ORG_ID=$(echo $ORG_RESPONSE | jq -r '.id')
else
  echo "❌ Failed"
  echo $ORG_RESPONSE | jq '.'
  exit 1
fi

# 4. Chart of Accounts Verification
echo "4. Verifying Chart of Accounts... "
# Wait for seeding
sleep 2

get_account_id() {
  local CODE=$1
  local URL="$API_BASE/$ORG_ID/accounts/?code=$CODE"
  local RESP=$(curl -s -X GET "$URL" -H "Authorization: Bearer $ACCESS_TOKEN")
  # echo "Debug: CODE=$CODE URL=$URL RESP=$RESP" >&2
  echo "$RESP" | jq -r '.data[0].id'
}

BANK_ACCOUNT_ID=$(get_account_id "1100")
CAPITAL_ACCOUNT_ID=$(get_account_id "3000")
REVENUE_ACCOUNT_ID=$(get_account_id "4000")
RENT_ACCOUNT_ID=$(get_account_id "6100")
EQUIPMENT_ACCOUNT_ID=$(get_account_id "1510")
UTILITIES_ACCOUNT_ID=$(get_account_id "6110")
SUPPLIES_ACCOUNT_ID=$(get_account_id "6200")

echo "   Bank (1100): $BANK_ACCOUNT_ID"
echo "   Capital (3000): $CAPITAL_ACCOUNT_ID"
echo "   Revenue (4000): $REVENUE_ACCOUNT_ID"

if [ "$BANK_ACCOUNT_ID" == "null" ] || [ "$CAPITAL_ACCOUNT_ID" == "null" ]; then
  echo "❌ CoA verification failed"
  exit 1
else
  echo "✅ CoA verified"
fi

# 5. Get Tax Code (OS)
echo -n "5. Fetching OS Tax Code... "
URL="$API_BASE/$ORG_ID/gst/tax-codes/?code=OS"
RESP=$(curl -s -X GET "$URL" -H "Authorization: Bearer $ACCESS_TOKEN")
OS_TAX_CODE_ID=$(echo "$RESP" | jq -r '.data | .[] | select(.org_id != null) | .id')
if [ -z "$OS_TAX_CODE_ID" ]; then
  OS_TAX_CODE_ID=$(echo "$RESP" | jq -r '.data[0].id')
fi

if [ "$OS_TAX_CODE_ID" == "null" ] || [ -z "$OS_TAX_CODE_ID" ]; then
  echo "❌ OS Tax Code not found"
  exit 1
else
  echo "✅ Success ($OS_TAX_CODE_ID)"
fi

# 6. Create Bank Account
echo -n "6. Creating Bank Account... "
BANK_ACC_RESPONSE=$(curl -s -X POST "$API_BASE/$ORG_ID/banking/bank-accounts/" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d "{
    \"account_name\": \"DBS Business Account\",
    \"bank_name\": \"DBS Bank Ltd\",
    \"account_number\": \"123-456789-001\",
    \"bank_code\": \"7171\",
    \"currency\": \"SGD\",
    \"gl_account\": \"$BANK_ACCOUNT_ID\",
    \"paynow_type\": \"UEN\",
    \"paynow_id\": \"202501234A\",
    \"is_default\": true,
    \"opening_balance\": \"0.0000\",
    \"opening_balance_date\": \"2026-01-01\"
  }")

if echo $BANK_ACC_RESPONSE | grep -q "id"; then
  echo "✅ Success"
  BANK_ACCOUNT_UUID=$(echo $BANK_ACC_RESPONSE | jq -r '.id')
else
  echo "❌ Failed"
  echo $BANK_ACC_RESPONSE | jq '.'
  exit 1
fi

# 7. Opening Balance Journal Entry
echo -n "7. Posting Opening Balance JE... "
JE_RESPONSE=$(curl -s -X POST "$API_BASE/$ORG_ID/journal-entries/entries/" \
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

if echo $JE_RESPONSE | grep -q "id"; then
  echo "✅ Success"
else
  echo "❌ Failed"
  echo $JE_RESPONSE | jq '.'
  exit 1
fi

# 8. Create Contacts
echo -n "8. Creating Contacts... "
CUSTOMER_RESPONSE=$(curl -s -X POST "$API_BASE/$ORG_ID/invoicing/contacts/" \
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
# echo "Debug: CUSTOMER_RESPONSE=$CUSTOMER_RESPONSE" >&2
CUSTOMER_ID=$(echo $CUSTOMER_RESPONSE | jq -r '.id')

SUPPLIER_RESPONSE=$(curl -s -X POST "$API_BASE/$ORG_ID/invoicing/contacts/" \
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
# echo "Debug: SUPPLIER_RESPONSE=$SUPPLIER_RESPONSE" >&2
SUPPLIER_ID=$(echo $SUPPLIER_RESPONSE | jq -r '.id')

if [ "$CUSTOMER_ID" == "null" ] || [ "$SUPPLIER_ID" == "null" ] || [ -z "$CUSTOMER_ID" ] || [ -z "$SUPPLIER_ID" ]; then
  echo "❌ Contact creation failed"
  echo "CUSTOMER_RESPONSE: $CUSTOMER_RESPONSE"
  echo "SUPPLIER_RESPONSE: $SUPPLIER_RESPONSE"
  exit 1
fi
echo "✅ Success (Customer: $CUSTOMER_ID, Supplier: $SUPPLIER_ID)"

# 9. Invoices & Payments Workflow
echo "9. Executing Transaction Workflow... "

# Helper for Invoice & Payment
process_sale() {
  local DATE=$1
  local AMOUNT=$2
  local REF=$3
  
  echo -n "   - Processing Sale ($DATE, $AMOUNT)... "
  
  # Create Invoice
  INV_RESP=$(curl -s -X POST "$API_BASE/$ORG_ID/invoicing/documents/" \
    -H "Authorization: Bearer $ACCESS_TOKEN" \
    -H "Content-Type: application/json" \
    -d "{
      \"document_type\": \"SALES_INVOICE\",
      \"contact_id\": \"$CUSTOMER_ID\",
      \"issue_date\": \"$DATE\",
      \"due_date\": \"$DATE\",
      \"currency\": \"SGD\",
      \"reference\": \"$REF\",
      \"lines\": [{
        \"description\": \"Consulting services\",
        \"account_id\": \"$REVENUE_ACCOUNT_ID\",
        \"quantity\": 1,
        \"unit_price\": \"$AMOUNT\",
        \"tax_code_id\": \"$OS_TAX_CODE_ID\"
      }]
    }")
  INV_ID=$(echo $INV_RESP | jq -r '.id')
  
  if [ "$INV_ID" == "null" ]; then echo "❌ Invoice failed: $INV_RESP"; exit 1; fi

  # Approve
  curl -s -X POST "$API_BASE/$ORG_ID/invoicing/documents/$INV_ID/approve/" -H "Authorization: Bearer $ACCESS_TOKEN" > /dev/null
  
  # Receive Payment
  PAY_RESP=$(curl -s -X POST "$API_BASE/$ORG_ID/banking/payments/receive/" \
    -H "Authorization: Bearer $ACCESS_TOKEN" \
    -H "Content-Type: application/json" \
    -d "{
      \"contact_id\": \"$CUSTOMER_ID\",
      \"bank_account_id\": \"$BANK_ACCOUNT_UUID\",
      \"payment_date\": \"$DATE\",
      \"amount\": \"$AMOUNT\",
      \"payment_method\": \"BANK_TRANSFER\",
      \"currency\": \"SGD\"
    }")
  PAY_ID=$(echo $PAY_RESP | jq -r '.id')
  
  if [ "$PAY_ID" == "null" ]; then echo "❌ Payment failed: $PAY_RESP"; exit 1; fi

  # Allocate
  curl -s -X POST "$API_BASE/$ORG_ID/banking/payments/$PAY_ID/allocate/" \
    -H "Authorization: Bearer $ACCESS_TOKEN" \
    -H "Content-Type: application/json" \
    -d "{
      \"allocations\": [{ \"document_id\": \"$INV_ID\", \"allocated_amount\": \"$AMOUNT\" }]
    }" > /dev/null
    
  echo "✅ Done"
}

process_purchase() {
  local DATE=$1
  local AMOUNT=$2
  local REF=$3
  local ACCOUNT=$4
  
  echo -n "   - Processing Purchase ($DATE, $AMOUNT)... "
  
  # Create Invoice
  INV_RESP=$(curl -s -X POST "$API_BASE/$ORG_ID/invoicing/documents/" \
    -H "Authorization: Bearer $ACCESS_TOKEN" \
    -H "Content-Type: application/json" \
    -d "{
      \"document_type\": \"PURCHASE_INVOICE\",
      \"contact_id\": \"$SUPPLIER_ID\",
      \"issue_date\": \"$DATE\",
      \"due_date\": \"$DATE\",
      \"currency\": \"SGD\",
      \"reference\": \"$REF\",
      \"lines\": [{
        \"description\": \"Expense\",
        \"account_id\": \"$ACCOUNT\",
        \"quantity\": 1,
        \"unit_price\": \"$AMOUNT\",
        \"tax_code_id\": \"$OS_TAX_CODE_ID\"
      }]
    }")
  INV_ID=$(echo $INV_RESP | jq -r '.id')
  
  if [ "$INV_ID" == "null" ]; then echo "❌ Purchase failed: $INV_RESP"; exit 1; fi

  # Approve
  curl -s -X POST "$API_BASE/$ORG_ID/invoicing/documents/$INV_ID/approve/" -H "Authorization: Bearer $ACCESS_TOKEN" > /dev/null
  
  # Make Payment
  PAY_RESP=$(curl -s -X POST "$API_BASE/$ORG_ID/banking/payments/make/" \
    -H "Authorization: Bearer $ACCESS_TOKEN" \
    -H "Content-Type: application/json" \
    -d "{
      \"contact_id\": \"$SUPPLIER_ID\",
      \"bank_account_id\": \"$BANK_ACCOUNT_UUID\",
      \"payment_date\": \"$DATE\",
      \"amount\": \"$AMOUNT\",
      \"payment_method\": \"BANK_TRANSFER\",
      \"currency\": \"SGD\"
    }")
  PAY_ID=$(echo $PAY_RESP | jq -r '.id')
  
  if [ "$PAY_ID" == "null" ]; then echo "❌ Payment failed: $PAY_RESP"; exit 1; fi

  # Allocate
  curl -s -X POST "$API_BASE/$ORG_ID/banking/payments/$PAY_ID/allocate/" \
    -H "Authorization: Bearer $ACCESS_TOKEN" \
    -H "Content-Type: application/json" \
    -d "{
      \"allocations\": [{ \"document_id\": \"$INV_ID\", \"allocated_amount\": \"$AMOUNT\" }]
    }" > /dev/null
    
  echo "✅ Done"
}

# Execute Timeline
process_purchase "2026-01-05" "8500.0000" "BILL-2026-001" "$EQUIPMENT_ACCOUNT_ID"
process_sale "2026-01-10" "12000.0000" "INV-2026-001"
process_purchase "2026-01-20" "9000.0000" "BILL-2026-002" "$RENT_ACCOUNT_ID"
process_purchase "2026-01-25" "450.0000" "BILL-2026-003" "$UTILITIES_ACCOUNT_ID"
process_sale "2026-02-05" "15000.0000" "INV-2026-002"
process_purchase "2026-02-20" "2500.0000" "BILL-2026-004" "$RENT_ACCOUNT_ID"
process_sale "2026-03-05" "18000.0000" "INV-2026-003"
process_purchase "2026-03-10" "3200.0000" "BILL-2026-005" "$SUPPLIES_ACCOUNT_ID"
process_purchase "2026-03-20" "150.0000" "BANK-FEE-001" "$BANK_ACCOUNT_ID" # Simplified bank charge

# 10. Bank Reconciliation
echo -n "10. Importing Bank Statement... "
cat > /tmp/statement.csv << EOF
Date,Description,Amount,Reference
2026-01-02,Opening Balance,50000.00,OB
2026-01-05,Office Equipment,-8500.00,BILL-2026-001
2026-01-10,Client Payment,12000.00,INV-2026-001
2026-01-15,Client Payment,12000.00,INV-2026-001
2026-01-20,Office Rent,-9000.00,BILL-2026-002
2026-01-25,Utilities,-450.00,BILL-2026-003
2026-02-15,Client Payment,15000.00,INV-2026-002
2026-03-15,Client Payment,18000.00,INV-2026-003
2026-03-20,Bank Charges,-150.00,BANK-FEE-001
EOF

IMPORT_RESP=$(curl -s -X POST "$API_BASE/$ORG_ID/banking/bank-transactions/import/" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -F "file=@/tmp/statement.csv" \
  -F "bank_account_id=$BANK_ACCOUNT_UUID")

if echo $IMPORT_RESP | grep -q "\"imported\":"; then
  echo "✅ Success ($(echo $IMPORT_RESP | jq -r '.imported') transactions)"
else
  echo "❌ Failed"
  echo $IMPORT_RESP | jq '.'
  exit 1
fi

# 11. Reports
echo "11. Generating Reports... "

# Dashboard
echo -n "   - Dashboard Metrics: "
curl -s -X GET "$API_BASE/$ORG_ID/reports/dashboard/metrics/" -H "Authorization: Bearer $ACCESS_TOKEN" | jq -r '"Revenue YTD: " + .revenue_ytd + ", Cash: " + .cash_on_hand'

# P&L
echo -n "   - Profit & Loss: "
PL_RESP=$(curl -s -X GET "$API_BASE/$ORG_ID/reports/reports/financial/?report_type=profit_loss&start_date=2026-01-01&end_date=2026-03-31" -H "Authorization: Bearer $ACCESS_TOKEN")
echo "$PL_RESP" | jq -r '"Net Profit: " + (.data.net_profit|tostring)'

# Balance Sheet
echo -n "   - Balance Sheet: "
BS_RESP=$(curl -s -X GET "$API_BASE/$ORG_ID/reports/reports/financial/?report_type=balance_sheet&as_at_date=2026-03-31" -H "Authorization: Bearer $ACCESS_TOKEN")
echo "$BS_RESP" | jq -r '"Total Assets: " + (.data.assets.Total|tostring)'

echo "=============================================="
echo "✅ Test Suite Execution Complete"
