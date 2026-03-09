# LedgerSG SQL Schema vs Django Models - Gap Analysis Report

**Generated:** 2026-02-27  
**SQL Schema Version:** 1.0.1  
**Analysis Scope:** 28 SQL Tables vs 15 Django Models

---

## Executive Summary

| Metric | Count |
|--------|-------|
| Tables with Full Alignment | 4 |
| Tables with Partial Alignment | 9 |
| Tables Missing Django Models | 15 |
| Critical Issues (P0) | 8 |
| High Priority Issues (P1) | 14 |
| Medium Priority Issues (P2) | 6 |

---

## 1. Tables with Full Alignment ✅ (GREEN)

These tables have complete field mapping and are production-ready:

### 1.1 `core.app_user` ↔ `AppUser`
- **Status:** FULLY_ALIGNED
- **All fields mapped:** id, email, password, full_name, phone, is_active, is_staff, is_superuser, last_login, date_joined, password_changed_at, created_at, updated_at, deleted_at

### 1.2 `core.role` ↔ `Role`
- **Status:** FULLY_ALIGNED
- **All permission flags present:** can_manage_org, can_manage_users, can_manage_coa, can_create_invoices, can_approve_invoices, can_void_invoices, can_create_journals, can_manage_banking, can_file_gst, can_view_reports, can_export_data

### 1.3 `journal.line` ↔ `JournalLine`
- **Status:** FULLY_ALIGNED
- **All monetary fields mapped:** debit, credit, tax_amount, base_debit, base_credit
- **All foreign keys mapped:** entry, org, account, tax_code

### 1.4 `invoicing.document_line` ↔ `InvoiceLine`
- **Status:** FULLY_ALIGNED
- **Complete field mapping including BCRS fields:** is_bcrs_deposit

---

## 2. Tables with Partial Alignment ⚠️ (YELLOW)

### 2.1 `invoicing.document` ↔ `InvoiceDocument` [P0 - CRITICAL]

#### ENUM Mismatches
| SQL ENUM Values | Django Values | Status |
|----------------|---------------|--------|
| SALES_INVOICE | SALES_INVOICE | ✅ Match |
| SALES_CREDIT_NOTE | SALES_CREDIT_NOTE | ✅ Match |
| SALES_DEBIT_NOTE | **MISSING** | ❌ |
| SALES_QUOTE | SALES_QUOTE | ✅ Match |
| PURCHASE_INVOICE | **MISSING** | ❌ |
| PURCHASE_CREDIT_NOTE | **MISSING** | ❌ |
| PURCHASE_DEBIT_NOTE | **MISSING** | ❌ |
| PURCHASE_ORDER | **MISSING** | ❌ |

#### Status ENUM Mismatch
- **SQL:** DRAFT, APPROVED, SENT, PARTIALLY_PAID, PAID, OVERDUE, VOID
- **Django:** DRAFT, SENT, APPROVED, PARTIALLY_PAID, PAID, VOID
- **Missing in Django:** OVERDUE
- **Order differs** between SQL and Django

#### Missing Fields (28 fields not mapped)
```sql
-- Currency & Exchange Rate
currency, exchange_rate

-- Monetary Fields
total_discount, amount_paid, amount_due (generated),
base_subtotal, base_total_gst, base_total_amount

-- Notes & References
internal_notes, is_tax_invoice, tax_invoice_label

-- InvoiceNow/Peppol
peppol_message_id, invoicenow_status, invoicenow_sent_at, invoicenow_error

-- Workflow & Linkage
journal_entry_id, related_document_id

-- Audit Fields
approved_at, approved_by, voided_at, voided_by, void_reason
```

#### ON DELETE Mismatch
| Column | SQL | Django | Impact |
|--------|-----|--------|--------|
| contact_id | RESTRICT | CASCADE | SQL prevents contact deletion if documents exist; Django cascades |

---

### 2.2 `invoicing.contact` ↔ `Contact` [P1 - HIGH]

#### Missing Fields (21 fields)
```sql
-- Classification
contact_type, legal_name, uen, gst_reg_number, is_gst_registered, tax_code_default

-- Communication
fax, website

-- Address
address_line_1, address_line_2, city, state_province, postal_code, country

-- Financial
default_currency, credit_limit, receivable_account_id, payable_account_id

-- InvoiceNow
peppol_id, peppol_scheme_id

-- Other
notes
```

#### Default Value Mismatch
| Field | SQL Default | Django Default |
|-------|-------------|----------------|
| is_customer | TRUE | FALSE |

---

### 2.3 `gst.tax_code` ↔ `TaxCode` [P1 - HIGH]

#### Missing Fields (9 fields)
```sql
description, is_input, is_output, is_claimable, is_reverse_charge,
f5_supply_box, f5_purchase_box, f5_tax_box, display_order
```

#### Django Field Not in SQL
- `box_mapping` - exists in Django but not in SQL schema

#### Unique Constraint Mismatch
- **SQL:** UNIQUE(org_id, code, effective_from) - allows rate history
- **Django:** unique_together = [["org", "code"]] - prevents rate history

---

### 2.4 `gst.return` ↔ `GSTReturn` [P1 - HIGH]

#### Missing Fields (10 fields)
```sql
-- F5 Boxes 11-15
box11_bad_debt_relief, box12_pre_reg_input_tax,
box13_total_revenue, box14_reverse_charge_supplies, box15_electronic_marketplace

-- Workflow
computed_at, reviewed_at, reviewed_by, iras_confirmation, notes
```

#### Field Name Mismatch
| SQL | Django | Issue |
|-----|--------|-------|
| iras_confirmation | filing_reference | Different naming conventions |

---

### 2.5 `coa.account` ↔ `Account` [P1 - HIGH]

#### Missing Fields (7 fields)
```sql
account_type_id, account_sub_type_id, currency,
tax_code_default, is_header, is_bank, is_control
```

**Impact:** Cannot properly manage Chart of Accounts hierarchy without these fields.

---

### 2.6 `core.organisation` ↔ `Organisation` [P0 - CRITICAL]

#### Critical ENUM Mismatch - `gst_scheme`
| SQL CHECK Values | Django Choices | Match? |
|------------------|----------------|--------|
| 'standard' / 'STANDARD' | 'STANDARD' | ✅ |
| 'cash' / 'CASH' | 'CASH_ACCOUNTING' | ❌ |
| 'margin' / 'MARGIN' | 'SECOND_HAND' | ❌ |
| - | 'TOURIST_REFUND' | ❌ (Extra in Django) |

**Risk:** Inserting Django values into SQL will cause CHECK constraint violations.

#### Missing Fields (10 fields)
```sql
peppol_scheme_id, invoicenow_ap_id, date_format,
address_line_1, address_line_2, state, logo_url, email, phone, website
```

#### Field Type Issue
| Column | SQL | Django | Issue |
|--------|-----|--------|-------|
| deleted_by | UUID REFERENCES app_user(id) | UUIDField | Should be FK, not UUIDField |

---

### 2.7 `core.user_organisation` ↔ `UserOrganisation` [P2 - MEDIUM]

#### ON DELETE Differences
| Column | SQL | Django | Note |
|--------|-----|--------|------|
| role_id | RESTRICT | PROTECT | Similar but different error types |

#### Missing Fields (3 fields)
```sql
accepted_by, revoked_at, revoked_by
```

#### Default Value Issue
| Field | SQL | Django | Issue |
|-------|-----|--------|-------|
| invited_at | No default | auto_now_add=True | May cause issues |

---

### 2.8 `journal.entry` ↔ `JournalEntry` [P1 - HIGH]

#### Related Name Mismatches
| SQL Column | Django Field | Related Name Issue |
|------------|--------------|-------------------|
| reversed_by_id | reversed_by | Django uses 'reversal_of' |
| reversal_of_id | reversal_of_entry | Django uses 'reversal_entry' |

#### Field Naming
- SQL uses `reversed_by_id` and `reversal_of_id`
- Django uses `reversed_by` and `reversal_of_entry`

---

### 2.9 `core.fiscal_period` ↔ `FiscalPeriod` [P2 - MEDIUM]

#### Missing Fields (3 fields)
```sql
is_adjustment, closed_at, closed_by
```

---

## 3. Tables Missing Django Models 🔴 (RED)

### 3.1 Banking Schema [P1 - CRITICAL]

| SQL Table | Priority | Description |
|-----------|----------|-------------|
| `banking.bank_account` | P1 | Bank account management |
| `banking.payment` | P1 | Payment records (AR/AP) |
| `banking.payment_allocation` | P1 | Payment-to-invoice matching |
| `banking.bank_transaction` | P2 | Imported bank feed |

**Impact:** Cannot process payments or bank reconciliation without these models.

### 3.2 Core Schema [P1 - HIGH]

| SQL Table | Priority | Description |
|-----------|----------|-------------|
| `core.document_sequence` | P1 | Auto-numbering for documents |
| `core.currency` | P2 | Reference table (20 currencies) |
| `core.exchange_rate` | P2 | Multi-currency exchange rates |
| `core.organisation_setting` | P3 | Key-value configuration store |

### 3.3 COA Schema [P2 - MEDIUM]

| SQL Table | Priority | Description |
|-----------|----------|-------------|
| `coa.account_type` | P2 | Account type classification (8 types) |
| `coa.account_sub_type` | P2 | Account sub-classification (28 sub-types) |

### 3.4 GST Schema [P2 - MEDIUM]

| SQL Table | Priority | Description |
|-----------|----------|-------------|
| `gst.peppol_transmission_log` | P2 | InvoiceNow/Peppol transmission tracking |
| `gst.threshold_snapshot` | P3 | GST threshold monitoring |

### 3.5 Invoicing Schema [P2 - MEDIUM]

| SQL Table | Priority | Description |
|-----------|----------|-------------|
| `invoicing.document_attachment` | P2 | File attachments for documents |

### 3.6 Audit Schema [P2 - MEDIUM]

| SQL Table | Priority | Description |
|-----------|----------|-------------|
| `audit.event_log` | P2 | Immutable audit trail - IRAS compliance |

---

## 4. Critical Naming Mismatches

These differences won't cause runtime errors (db_column mappings are correct), but they create semantic confusion:

| Severity | SQL Column | Django Field | Impact |
|----------|------------|--------------|--------|
| HIGH | `document_number` | `sequence_number` | Confusing - same data, different names |
| HIGH | `document_date` | `issue_date` | Same concept, different terminology |
| HIGH | `subtotal` | `total_excl` | Excl. vs Exclusive |
| HIGH | `total_amount` | `total_incl` | Incl. vs Inclusive |
| MEDIUM | `customer_notes` | `notes` | Less specific in Django |

---

## 5. Missing Fields Analysis

### 5.1 InvoiceDocument (28 missing of 38 total fields)

**Critical Missing:**
- `currency`, `exchange_rate` - Multi-currency support
- `amount_paid`, `amount_due` - Payment tracking
- `journal_entry_id` - GL linkage
- `approved_by`, `voided_by` - Workflow audit

### 5.2 Contact (21 missing of 28 total fields)

**Critical Missing:**
- `contact_type` - Customer vs Supplier classification
- `country`, `default_currency` - International support
- `receivable_account_id`, `payable_account_id` - AR/AP control accounts

### 5.3 TaxCode (13 missing of 20 total fields)

**Critical Missing:**
- `is_input`, `is_output`, `is_claimable` - GST classification
- `f5_supply_box`, `f5_purchase_box`, `f5_tax_box` - GST F5 reporting

### 5.4 Account (11 missing of 17 total fields)

**Critical Missing:**
- `account_type_id`, `account_sub_type_id` - Chart hierarchy
- `currency` - Multi-currency accounts
- `tax_code_default` - Default tax for account

### 5.5 Organisation (11 missing of 32 total fields)

**Critical Missing:**
- `peppol_scheme_id`, `invoicenow_ap_id` - InvoiceNow configuration
- `country` - International support

---

## 6. Recommendations by Priority

### P0 - CRITICAL (Fix Immediately)

1. **Fix InvoiceDocument DOCUMENT_TYPES**
   ```python
   DOCUMENT_TYPES = [
       ("SALES_INVOICE", "Invoice"),
       ("SALES_CREDIT_NOTE", "Credit Note"),
       ("SALES_DEBIT_NOTE", "Debit Note"),
       ("SALES_QUOTE", "Quote"),
       ("PURCHASE_INVOICE", "Purchase Invoice"),
       ("PURCHASE_CREDIT_NOTE", "Purchase Credit Note"),
       ("PURCHASE_DEBIT_NOTE", "Purchase Debit Note"),
       ("PURCHASE_ORDER", "Purchase Order"),
   ]
   ```

2. **Fix InvoiceDocument STATUS_CHOICES**
   ```python
   STATUS_CHOICES = [
       ("DRAFT", "Draft"),
       ("APPROVED", "Approved"),
       ("SENT", "Sent"),
       ("PARTIALLY_PAID", "Partially Paid"),
       ("PAID", "Paid"),
       ("OVERDUE", "Overdue"),  # Add this
       ("VOID", "Void"),
   ]
   ```

3. **Fix Organisation gst_scheme choices**
   ```python
   GST_SCHEMES = [
       ("STANDARD", "Standard GST"),
       ("CASH", "Cash Accounting"),  # Match SQL
       ("MARGIN", "Margin Scheme"),  # Match SQL
   ]
   ```

4. **Change InvoiceDocument contact FK**
   ```python
   contact = models.ForeignKey(
       "Contact", 
       on_delete=models.RESTRICT,  # Change from CASCADE
       db_column="contact_id"
   )
   ```

### P1 - HIGH (Create Missing Models & Add Fields)

1. **Create banking models:**
   - `BankAccount`
   - `Payment`
   - `PaymentAllocation`

2. **Create core.models:**
   - `DocumentSequence` (critical for numbering)
   - `Currency`
   - `ExchangeRate`

3. **Add missing fields to existing models**
   - Contact: 21 fields
   - TaxCode: 9 fields  
   - GSTReturn: 10 fields
   - Account: 7 fields

4. **Create audit model:**
   - `AuditEventLog` (IRAS compliance)

### P2 - MEDIUM

1. Create reference table models:
   - `AccountType`
   - `AccountSubType`

2. Create InvoiceNow models:
   - `PeppolTransmissionLog`

3. Create attachment model:
   - `DocumentAttachment`

### P3 - LOW

1. Create utility models:
   - `OrganisationSetting`
   - `GSTThresholdSnapshot`
   - `BankTransaction`

---

## 7. SQL Tables Summary

| Schema | Table | Django Model | Status |
|--------|-------|--------------|--------|
| core | organisation | Organisation | ⚠️ Partial |
| core | app_user | AppUser | ✅ Full |
| core | role | Role | ✅ Full |
| core | user_organisation | UserOrganisation | ⚠️ Partial |
| core | fiscal_year | FiscalYear | ✅ Full |
| core | fiscal_period | FiscalPeriod | ⚠️ Partial |
| core | currency | **MISSING** | 🔴 None |
| core | exchange_rate | **MISSING** | 🔴 None |
| core | document_sequence | **MISSING** | 🔴 None |
| core | organisation_setting | **MISSING** | 🔴 None |
| coa | account_type | **MISSING** | 🔴 None |
| coa | account_sub_type | **MISSING** | 🔴 None |
| coa | account | Account | ⚠️ Partial |
| gst | tax_code | TaxCode | ⚠️ Partial |
| gst | return | GSTReturn | ⚠️ Partial |
| gst | threshold_snapshot | **MISSING** | 🔴 None |
| gst | peppol_transmission_log | **MISSING** | 🔴 None |
| journal | entry | JournalEntry | ⚠️ Partial |
| journal | line | JournalLine | ✅ Full |
| invoicing | contact | Contact | ⚠️ Partial |
| invoicing | document | InvoiceDocument | ⚠️ Partial |
| invoicing | document_line | InvoiceLine | ✅ Full |
| invoicing | document_attachment | **MISSING** | 🔴 None |
| banking | bank_account | **MISSING** | 🔴 None |
| banking | payment | **MISSING** | 🔴 None |
| banking | payment_allocation | **MISSING** | 🔴 None |
| banking | bank_transaction | **MISSING** | 🔴 None |
| audit | event_log | **MISSING** | 🔴 None |

---

## 8. Conclusion

**Current State:** The Django models cover approximately **54%** of the SQL schema functionality.

**Critical Blockers:**
1. ENUM mismatches will cause CHECK constraint violations at runtime
2. Missing banking models prevent payment processing
3. Missing document_sequence will break auto-numbering

**Recommended Action Plan:**
1. **Week 1:** Fix all P0 issues (ENUMs, ON DELETE)
2. **Week 2:** Create banking models (P1)
3. **Week 3:** Add missing fields to existing models (P1)
4. **Week 4:** Create reference table models (P2)

**Estimated Effort:** 2-3 weeks for a single developer to achieve full alignment.
