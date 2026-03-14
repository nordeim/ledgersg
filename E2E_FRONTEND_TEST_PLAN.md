# 🧪 Frontend-Backend Integration Test Execution Plan

**Date**: 2026-03-12  
**Test Suite**: Test_suite_Singapore_SMB_workflow-1.md  
**Tool**: agent-browser  
**Approach**: Meticulous UI-based E2E Testing

---

## 🎯 Executive Summary

This plan uses the `agent-browser` CLI tool to test the complete frontend-backend integration for LedgerSG by simulating real user interactions through the web UI. We will execute the Lakshmi's Kitchen workflow entirely through the browser interface.

---

## 📋 Test Objectives

1. **Validate Frontend Rendering** — Ensure Next.js pages render correctly
2. **Test Authentication Flow** — Register, login, session management
3. **Verify Organisation Creation** — Business entity setup through UI
4. **Test Chart of Accounts** — Account seeding and retrieval
5. **Validate Journal Entries** — Opening balance creation
6. **Test Invoice Workflow** — Create → Approve → Payment cycle
7. **Verify Bank Reconciliation** — Transaction import and matching
8. **Validate Financial Reports** — P&L generation and display

---

## 🔧 Prerequisites

### 1. Backend Server
```bash
# Ensure backend is running
cd /home/project/Ledger-SG/apps/backend
source /opt/venv/bin/activate
python manage.py runserver 0.0.0.0:8000
```

### 2. Frontend Server
```bash
# Ensure frontend is running
cd /home/project/Ledger-SG/apps/web
npm run dev
```

### 3. Verify Services
```bash
# Check backend health
curl http://localhost:8000/api/v1/health/

# Check frontend
curl http://localhost:3000
```

---

## 📊 Phase 1: Browser Initialization & Health Check

### Step 1.1: Open LedgerSG Frontend
```bash
agent-browser open http://localhost:3000
```

### Step 1.2: Take Initial Snapshot
```bash
agent-browser snapshot -i
```

**Expected Output**:
- Login page or landing page
- Interactive elements visible
- No JavaScript errors

### Step 1.3: Screenshot for Baseline
```bash
agent-browser screenshot --annotate /tmp/lakshmi/01-landing.png
```

---

## 📊 Phase 2: User Registration Flow

### Step 2.1: Navigate to Register Page
```bash
# If on landing page, click "Register" link
agent-browser find text "Register" click
# Or navigate directly
agent-browser open http://localhost:3000/register
```

### Step 2.2: Fill Registration Form
```bash
# Get snapshot to find form fields
agent-browser snapshot -i

# Fill email field
agent-browser find label "Email" fill "lakshmi@kitchen.example"

# Fill password field
agent-browser find label "Password" fill "SecurePass123!"

# Fill confirm password (if present)
agent-browser find label "Confirm Password" fill "SecurePass123!"

# Fill full name
agent-browser find label "Full Name" fill "Lakshmi Krishnan"
```

### Step 2.3: Submit Registration
```bash
# Click register button
agent-browser find role button click --name "Register"

# Wait for redirect or success message
agent-browser wait --text "success\|Welcome\|Dashboard" --timeout 10000
```

### Step 2.4: Screenshot Registration Result
```bash
agent-browser screenshot --annotate /tmp/lakshmi/02-registration.png
```

---

## 📊 Phase 3: Login Flow

### Step 3.1: Navigate to Login
```bash
agent-browser open http://localhost:3000/login
```

### Step 3.2: Fill Login Form
```bash
agent-browser snapshot -i

agent-browser find label "Email" fill "lakshmi@kitchen.example"
agent-browser find label "Password" fill "SecurePass123!"
```

### Step 3.3: Submit Login
```bash
agent-browser find role button click --name "Login"

# Wait for dashboard
agent-browser wait --url "**/dashboard" --timeout 15000
```

### Step 3.4: Verify Dashboard Load
```bash
agent-browser snapshot -i
agent-browser screenshot --annotate /tmp/lakshmi/03-dashboard.png
```

**Expected Output**:
- Dashboard page visible
- No "Loading..." stuck state
- Organisation selector visible

---

## 📊 Phase 4: Organisation Creation

### Step 4.1: Navigate to Organisation Settings
```bash
# If no org exists, may auto-redirect to org creation
agent-browser snapshot -i

# If on dashboard without org, look for "Create Organisation"
agent-browser find text "Create Organisation" click
```

### Step 4.2: Fill Organisation Form
```bash
agent-browser snapshot -i

# Fill organisation name
agent-browser find label "Organisation Name" fill "Lakshmi Kitchen Pte Ltd"

# Fill legal name
agent-browser find label "Legal Name" fill "Lakshmi Kitchen Pte Ltd"

# Fill UEN
agent-browser find label "UEN" fill "202412345Z"

# Select entity type
agent-browser find role combobox select "PRIVATE_LIMITED"

# Set GST status (Not Registered)
agent-browser find label "GST Registered" uncheck

# Set base currency
agent-browser find label "Base Currency" select "SGD"

# Set financial year start
agent-browser find label "FY Start Month" select "January"
```

### Step 4.3: Submit Organisation
```bash
agent-browser find role button click --name "Create Organisation"

agent-browser wait --text "success\|Organisation created" --timeout 10000
```

### Step 4.4: Verify Organisation Creation
```bash
agent-browser snapshot -i
agent-browser screenshot --annotate /tmp/lakshmi/04-organisation.png
```

---

## 📊 Phase 5: Chart of Accounts Verification

### Step 5.1: Navigate to Chart of Accounts
```bash
agent-browser open http://localhost:3000/settings/coa

agent-browser wait --load networkidle
```

### Step 5.2: Verify Seeded Accounts
```bash
agent-browser snapshot -i
agent-browser screenshot --annotate /tmp/lakshmi/05-coa.png
```

**Expected Accounts**:
- 1100 — Bank (Asset)
- 3000 — Capital (Equity)
- 4000 — Revenue (Income)
- OS — Out-of-Scope Tax Code

### Step 5.3: Search for Specific Account
```bash
# Search for Bank account
agent-browser find role searchbox fill "1100"
agent-browser press Enter

agent-browser wait 2000
agent-browser snapshot -i
```

---

## 📊 Phase 6: Bank Account Setup

### Step 6.1: Navigate to Banking
```bash
agent-browser open http://localhost:3000/banking

agent-browser wait --load networkidle
```

### Step 6.2: Create Bank Account
```bash
agent-browser snapshot -i

# Click "Add Bank Account" or similar
agent-browser find role button click --name "Add Bank Account"

agent-browser snapshot -i

# Fill bank account form
agent-browser find label "Account Name" fill "DBS Business Account"
agent-browser find label "Account Number" fill "1234567890"
agent-browser find label "Bank Name" fill "DBS Bank"
agent-browser find label "Currency" select "SGD"

# Select GL Account (Bank - 1100)
agent-browser find label "GL Account" select "1100 - Bank"

agent-browser find role button click --name "Create"
```

### Step 6.3: Verify Bank Account Created
```bash
agent-browser wait --text "DBS Business Account" --timeout 5000
agent-browser snapshot -i
agent-browser screenshot --annotate /tmp/lakshmi/06-bank-account.png
```

---

## 📊 Phase 7: Opening Balance Journal Entry

### Step 7.1: Navigate to Journal Entries
```bash
agent-browser open http://localhost:3000/ledger

agent-browser wait --load networkidle
```

### Step 7.2: Create Journal Entry
```bash
agent-browser snapshot -i

# Click "New Journal Entry"
agent-browser find role button click --name "New Journal Entry"

agent-browser snapshot -i

# Set entry date
agent-browser find label "Entry Date" fill "2026-01-01"

# Set narration
agent-browser find label "Narration" fill "Opening capital contribution"

# Add first line (Debit)
agent-browser find role button click --name "Add Line"

agent-browser find label "Account" select "1100 - Bank"
agent-browser find label "Debit" fill "150000.0000"
agent-browser find label "Credit" fill "0.0000"

# Add second line (Credit)
agent-browser find role button click --name "Add Line"

agent-browser find label "Account" select "3000 - Capital"
agent-browser find label "Debit" fill "0.0000"
agent-browser find label "Credit" fill "150000.0000"

# Save entry
agent-browser find role button click --name "Save"
```

### Step 7.3: Verify Journal Entry Created
```bash
agent-browser wait --text "150000" --timeout 5000
agent-browser snapshot -i
agent-browser screenshot --annotate /tmp/lakshmi/07-journal-entry.png
```

---

## 📊 Phase 8: Customer Contact Creation

### Step 8.1: Navigate to Contacts
```bash
agent-browser open http://localhost:3000/invoices/contacts

agent-browser wait --load networkidle
```

### Step 8.2: Create Customer
```bash
agent-browser snapshot -i

agent-browser find role button click --name "Add Contact"

agent-browser snapshot -i

# Fill contact details
agent-browser find label "Name" fill "Corporate Catering Pte Ltd"
agent-browser find label "Email" fill "orders@catering.example"
agent-browser find label "Phone" fill "+65 9123 4567"

# Set as customer
agent-browser find label "Is Customer" check

agent-browser find role button click --name "Save"
```

### Step 8.3: Verify Contact Created
```bash
agent-browser wait --text "Corporate Catering" --timeout 5000
agent-browser snapshot -i
agent-browser screenshot --annotate /tmp/lakshmi/08-contact.png
```

---

## 📊 Phase 9: Sales Invoice Creation

### Step 9.1: Navigate to Invoices
```bash
agent-browser open http://localhost:3000/invoices

agent-browser wait --load networkidle
```

### Step 9.2: Create Invoice
```bash
agent-browser snapshot -i

agent-browser find role button click --name "New Invoice"

agent-browser wait --load networkidle
agent-browser snapshot -i

# Select customer
agent-browser find label "Customer" select "Corporate Catering Pte Ltd"

# Set dates
agent-browser find label "Invoice Date" fill "2026-01-31"
agent-browser find label "Due Date" fill "2026-01-31"

# Add line item
agent-browser find role button click --name "Add Line"

agent-browser find label "Description" fill "Dine-in revenue"
agent-browser find label "Account" select "4000 - Revenue"
agent-browser find label "Quantity" fill "1"
agent-browser find label "Unit Price" fill "22450.0000"

# Tax code (OS - Out of Scope)
agent-browser find label "Tax Code" select "OS"

agent-browser find role button click --name "Save Draft"
```

### Step 9.3: Verify Invoice Created (DRAFT)
```bash
agent-browser wait --text "DRAFT" --timeout 5000
agent-browser snapshot -i
agent-browser screenshot --annotate /tmp/lakshmi/09-invoice-draft.png
```

---

## 📊 Phase 10: Invoice Approval (CRITICAL)

### Step 10.1: Approve Invoice
```bash
agent-browser snapshot -i

# Click Approve button
agent-browser find role button click --name "Approve"

# Confirm approval (if dialog appears)
agent-browser wait --text "Approve\|Confirm" --timeout 3000
agent-browser find role button click --name "Confirm"
```

### Step 10.2: Verify Approval
```bash
agent-browser wait --text "APPROVED" --timeout 10000
agent-browser snapshot -i
agent-browser screenshot --annotate /tmp/lakshmi/10-invoice-approved.png
```

**Critical Validation**:
- Status changed from DRAFT to APPROVED
- Journal entries created (check ledger)

---

## 📊 Phase 11: Payment Recording

### Step 11.1: Navigate to Banking Payments
```bash
agent-browser open http://localhost:3000/banking

agent-browser wait --load networkidle
```

### Step 11.2: Record Payment Receipt
```bash
agent-browser snapshot -i

# Click "Receive Payment" tab or button
agent-browser find role tab click --name "Payments"

agent-browser snapshot -i

agent-browser find role button click --name "Receive Payment"

agent-browser snapshot -i

# Fill payment details
agent-browser find label "Customer" select "Corporate Catering Pte Ltd"
agent-browser find label "Bank Account" select "DBS Business Account"
agent-browser find label "Payment Date" fill "2026-01-31"
agent-browser find label "Amount" fill "22450.0000"
agent-browser find label "Payment Method" select "Bank Transfer"

agent-browser find role button click --name "Save"
```

### Step 11.3: Allocate Payment to Invoice
```bash
agent-browser wait --text "22450" --timeout 5000

agent-browser snapshot -i

# Click on payment to allocate
agent-browser find text "22450.0000" click

agent-browser snapshot -i

# Allocate to invoice
agent-browser find role button click --name "Allocate"

agent-browser find label "Invoice" select "INV-0001"
agent-browser find label "Allocated Amount" fill "22450.0000"

agent-browser find role button click --name "Confirm Allocation"
```

### Step 11.4: Verify Payment Allocated
```bash
agent-browser wait --text "Fully Allocated\|22450" --timeout 5000
agent-browser snapshot -i
agent-browser screenshot --annotate /tmp/lakshmi/11-payment.png
```

---

## 📊 Phase 12: Dashboard Verification

### Step 12.1: Navigate to Dashboard
```bash
agent-browser open http://localhost:3000/dashboard

agent-browser wait --load networkidle
```

### Step 12.2: Verify Metrics
```bash
agent-browser snapshot -i
agent-browser screenshot --annotate /tmp/lakshmi/12-dashboard.png
```

**Expected Metrics**:
- Revenue YTD: S$22,450
- Cash Balance: S$172,450
- Net Profit: S$22,450

---

## 📊 Phase 13: Financial Reports

### Step 13.1: Navigate to Reports
```bash
agent-browser open http://localhost:3000/reports

agent-browser wait --load networkidle
```

### Step 13.2: Generate P&L Report
```bash
agent-browser snapshot -i

agent-browser find role button click --name "Profit & Loss"

# Set date range
agent-browser find label "Start Date" fill "2026-01-01"
agent-browser find label "End Date" fill "2026-01-31"

agent-browser find role button click --name "Generate"
```

### Step 13.3: Verify P&L Report
```bash
agent-browser wait --text "22450" --timeout 10000
agent-browser snapshot -i
agent-browser screenshot --annotate /tmp/lakshmi/13-pnl-report.png
```

**Expected Values**:
- Revenue: S$22,450.00
- Net Profit: S$22,450.00

---

## 📊 Phase 14: Journal Entry Verification

### Step 14.1: Navigate to Journal Entries
```bash
agent-browser open http://localhost:3000/ledger

agent-browser wait --load networkidle
```

### Step 14.2: Verify All Journal Entries
```bash
agent-browser snapshot -i
agent-browser screenshot --annotate /tmp/lakshmi/14-journal-entries.png
```

**Expected Entries**:
1. Opening Balance (Jan 1): Debit Bank 150,000 / Credit Capital 150,000
2. Invoice Approval (Jan 31): Debit AR 22,450 / Credit Revenue 22,450
3. Payment Receipt (Jan 31): Debit Bank 22,450 / Credit AR 22,450

---

## 📊 Phase 15: Cleanup & Summary

### Step 15.1: Generate Test Summary
```bash
agent-browser close
```

### Step 15.2: Create Summary Report
```bash
# Count screenshots
ls -la /tmp/lakshmi/*.png

# Expected: 14+ screenshots
```

---

## ✅ Success Criteria

| Criterion | Expected | Validation |
|-----------|----------|------------|
| **Registration** | User created successfully | Screenshot 02 |
| **Login** | Dashboard loads | Screenshot 03 |
| **Organisation** | Entity created with GST=false | Screenshot 04 |
| **COA** | Accounts seeded | Screenshot 05 |
| **Bank Account** | Account linked to GL | Screenshot 06 |
| **Journal Entry** | Opening balance posted | Screenshot 07 |
| **Contact** | Customer created | Screenshot 08 |
| **Invoice Draft** | Invoice saved | Screenshot 09 |
| **Invoice Approved** | Status changed, journal posted | Screenshot 10 |
| **Payment** | Receipt recorded and allocated | Screenshot 11 |
| **Dashboard** | Metrics reflect transactions | Screenshot 12 |
| **P&L Report** | Revenue matches invoice amount | Screenshot 13 |
| **Journal Entries** | 3 entries visible | Screenshot 14 |

---

## ⚠️ Error Handling

### Common Issues & Solutions

1. **"Loading..." Stuck**
   - Check backend is running
   - Check CORS configuration
   - Wait longer: `agent-browser wait 10000`

2. **Element Not Found**
   - Re-snapshot: `agent-browser snapshot -i`
   - Use ref from fresh snapshot
   - Try alternative selector

3. **Authentication Failure**
   - Check backend logs
   - Verify JWT token handling
   - Try manual login first

4. **Page Not Loading**
   - Verify frontend server: `curl http://localhost:3000`
   - Check console errors: `agent-browser console`
   - Check network: `agent-browser network requests`

---

## 📝 Execution Notes

1. **Screenshot Naming**: Use sequential numbering for easy tracking
2. **Wait Times**: Adjust based on system performance
3. **Alternative Selectors**: Use refs first, fallback to CSS selectors
4. **State Preservation**: Use `--session-name lakshmi` to persist login
5. **Headed Mode**: Add `--headed` flag for debugging

---

## 🎯 Execution Command Sequence

```bash
# Full automated execution (run in sequence)
mkdir -p /tmp/lakshmi

# Phase 1
agent-browser open http://localhost:3000 && \
agent-browser snapshot -i && \
agent-browser screenshot --annotate /tmp/lakshmi/01-landing.png

# Phase 2-15: Execute each phase sequentially
# (Full command sequence in actual execution)
```

---

**Plan Created**: 2026-03-12  
**Estimated Duration**: 45-60 minutes  
**Confidence**: 90%  
**Status**: ✅ **READY FOR EXECUTION**
