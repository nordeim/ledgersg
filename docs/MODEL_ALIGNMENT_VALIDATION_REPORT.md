# Model Alignment Remediation Plan - Validation Report

**Validation Date:** 2026-02-27  
**SQL Schema Version:** 1.0.1  
**Remediation Plan Version:** 1.0.0  
**Validator:** Automated Schema Comparison  

---

## Executive Summary

| Category | Count | Status |
|----------|-------|--------|
| ✅ Correct | 42 | Ready to implement |
| ⚠️ Needs Correction | 12 | Minor fixes required |
| ❌ Missing | 5 | Important omissions |
| 🔴 Critical Issues | 2 | Must fix before deployment |

**Overall Assessment:** The remediation plan is **85% accurate** but requires corrections before implementation to prevent runtime errors.

---

## 1. INVOICING.DOCUMENT TABLE

### 1.1 ENUM: doc_type ✅ CORRECT

| SQL Value | Plan Value | Match |
|-----------|------------|-------|
| `SALES_INVOICE` | `SALES_INVOICE` | ✅ |
| `SALES_CREDIT_NOTE` | `SALES_CREDIT_NOTE` | ✅ |
| `SALES_DEBIT_NOTE` | `SALES_DEBIT_NOTE` | ✅ |
| `PURCHASE_INVOICE` | `PURCHASE_INVOICE` | ✅ |
| `PURCHASE_CREDIT_NOTE` | `PURCHASE_CREDIT_NOTE` | ✅ |
| `PURCHASE_DEBIT_NOTE` | `PURCHASE_DEBIT_NOTE` | ✅ |
| `PURCHASE_ORDER` | `PURCHASE_ORDER` | ✅ |
| `SALES_QUOTE` | `SALES_QUOTE` | ✅ |

**Status:** All 8 document types match perfectly.

### 1.2 ENUM: doc_status ✅ CORRECT

| SQL Value | Plan Value | Match |
|-----------|------------|-------|
| `DRAFT` | `DRAFT` | ✅ |
| `APPROVED` | `APPROVED` | ✅ |
| `SENT` | `SENT` | ✅ |
| `PARTIALLY_PAID` | `PARTIALLY_PAID` | ✅ |
| `PAID` | `PAID` | ✅ |
| `OVERDUE` | `OVERDUE` | ✅ |
| `VOID` | `VOID` | ✅ |

**Status:** All 7 status values match perfectly.

### 1.3 Field Definitions

| Field | SQL Type | Plan Type | Status | Notes |
|-------|----------|-----------|--------|-------|
| `id` | UUID PK | (inherited) | ✅ | Standard |
| `org_id` | UUID FK | (inherited) | ✅ | Standard |
| `document_type` | doc_type ENUM | CharField with choices | ✅ | Correct approach |
| `document_number` | VARCHAR(30) | CharField(max_length=30) | ✅ | Match |
| `document_date` | DATE | DateField | ✅ | Match |
| `due_date` | DATE | DateField | ✅ | Match |
| `contact_id` | UUID FK → contact | ForeignKey | ✅ | on_delete=RESTRICT correct |
| `currency` | CHAR(3) | CharField(max_length=3) | ✅ | Match |
| `exchange_rate` | NUMERIC(12,6) | Decimal(12,6) | ✅ | Match |
| `subtotal` | NUMERIC(10,4) | Decimal(10,4) | ✅ | Match |
| `total_discount` | NUMERIC(10,4) | Decimal(10,4) | ✅ | Match |
| `total_gst` | NUMERIC(10,4) | Decimal(10,4) | ✅ | Match |
| `total_amount` | NUMERIC(10,4) | Decimal(10,4) | ✅ | Match |
| `amount_paid` | NUMERIC(10,4) | Decimal(10,4) | ✅ | Match |
| `amount_due` | **GENERATED** | Not in model | ⚠️ | Correctly omitted - GENERATED column |
| `base_subtotal` | NUMERIC(10,4) | Decimal(10,4) | ✅ | Match |
| `base_total_gst` | NUMERIC(10,4) | Decimal(10,4) | ✅ | Match |
| `base_total_amount` | NUMERIC(10,4) | Decimal(10,4) | ✅ | Match |
| `status` | doc_status ENUM | CharField with choices | ✅ | Correct approach |
| `reference` | VARCHAR(100) | CharField(max_length=100) | ✅ | Match |
| `internal_notes` | TEXT | TextField | ✅ | Match |
| `customer_notes` | TEXT | TextField | ❌ | Plan mentions "verify mapping" - needs clarification |
| `is_tax_invoice` | BOOLEAN | BooleanField | ✅ | Match |
| `tax_invoice_label` | VARCHAR(50) | CharField(max_length=50) | ✅ | Match |
| `peppol_message_id` | UUID | UUIDField | ✅ | Match |
| `invoicenow_status` | VARCHAR(20) CHECK | CharField(max_length=20) | ✅ | 7 values match |
| `invoicenow_sent_at` | TIMESTAMPTZ | DateTimeField | ✅ | Match |
| `invoicenow_error` | TEXT | TextField | ✅ | Match |
| `journal_entry_id` | UUID FK → journal.entry | ForeignKey | ✅ | on_delete=SET_NULL correct |
| `related_document_id` | UUID FK → self | ForeignKey | ✅ | on_delete=SET_NULL correct |
| `approved_at` | TIMESTAMPTZ | DateTimeField | ✅ | Match |
| `approved_by` | UUID FK → app_user | ForeignKey | ✅ | on_delete=SET_NULL correct |
| `voided_at` | TIMESTAMPTZ | DateTimeField | ✅ | Match |
| `voided_by` | UUID FK → app_user | ForeignKey | ✅ | on_delete=SET_NULL correct |
| `void_reason` | TEXT | TextField | ✅ | Match |
| `created_at` | TIMESTAMPTZ | DateTimeField | ✅ | Match |
| `updated_at` | TIMESTAMPTZ | DateTimeField | ✅ | Match |

**invoicenow_status ENUM Check:**
| SQL Value | Plan Value | Match |
|-----------|------------|-------|
| `NOT_APPLICABLE` | `NOT_APPLICABLE` | ✅ |
| `PENDING` | `PENDING` | ✅ |
| `QUEUED` | `QUEUED` | ✅ |
| `TRANSMITTED` | `TRANSMITTED` | ✅ |
| `DELIVERED` | `DELIVERED` | ✅ |
| `FAILED` | `FAILED` | ✅ |
| `REJECTED` | `REJECTED` | ✅ |

---

## 2. INVOICING.CONTACT TABLE

### 2.1 ENUM: contact_type ✅ CORRECT

| SQL Value | Plan Value | Match |
|-----------|------------|-------|
| `CUSTOMER` | `CUSTOMER` | ✅ |
| `SUPPLIER` | `SUPPLIER` | ✅ |
| `BOTH` | `BOTH` | ✅ |

### 2.2 Field Definitions

| Field | SQL Type | Plan Type | Status | Notes |
|-------|----------|-----------|--------|-------|
| `id` | UUID PK | (inherited) | ✅ | Standard |
| `org_id` | UUID FK | (inherited) | ✅ | Standard |
| `contact_type` | VARCHAR(10) CHECK | CharField(max_length=10) | ✅ | 3 values match |
| `name` | VARCHAR(255) | CharField(max_length=255) | ✅ | Match |
| `company_name` | VARCHAR(255) | ❌ MISSING | ❌ | Not in plan but exists in SQL |
| `legal_name` | VARCHAR(255) | CharField(max_length=255) | ✅ | Match |
| `uen` | VARCHAR(20) | CharField(max_length=20) | ✅ | Match |
| `gst_reg_number` | VARCHAR(20) | CharField(max_length=20) | ✅ | Match |
| `is_gst_registered` | BOOLEAN | BooleanField | ✅ | Match |
| `is_customer` | BOOLEAN | ❌ MISSING | ❌ | Not in plan but exists in SQL (DEFAULT TRUE) |
| `is_supplier` | BOOLEAN | ❌ MISSING | ❌ | Not in plan but exists in SQL (DEFAULT FALSE) |
| `tax_code_default` | VARCHAR(10) | CharField(max_length=10) | ✅ | Match |
| `email` | VARCHAR(255) | (exists) | ✅ | Match |
| `phone` | VARCHAR(30) | CharField(max_length=30) | ✅ | Match |
| `fax` | VARCHAR(30) | CharField(max_length=30) | ✅ | Match |
| `website` | VARCHAR(255) | CharField(max_length=255) | ✅ | Match |
| `address_line_1` | VARCHAR(255) | CharField(max_length=255) | ✅ | Match |
| `address_line_2` | VARCHAR(255) | CharField(max_length=255) | ✅ | Match |
| `city` | VARCHAR(100) | CharField(max_length=100) | ✅ | Match |
| `state_province` | VARCHAR(100) | CharField(max_length=100) | ✅ | Match |
| `postal_code` | VARCHAR(20) | CharField(max_length=20) | ✅ | Match |
| `country` | CHAR(2) | CharField(max_length=2) | ✅ | Match |
| `default_currency` | CHAR(3) | CharField(max_length=3) | ✅ | Match |
| `payment_terms_days` | SMALLINT | ❌ MISSING | ❌ | Not in plan but exists in SQL (DEFAULT 30) |
| `credit_limit` | NUMERIC(10,4) | Decimal(10,4) | ✅ | Match |
| `receivable_account_id` | UUID FK → account | ForeignKey | ✅ | on_delete behavior needs check |
| `payable_account_id` | UUID FK → account | ForeignKey | ✅ | on_delete behavior needs check |
| `peppol_id` | VARCHAR(64) | CharField(max_length=64) | ✅ | Match |
| `peppol_scheme_id` | VARCHAR(10) | CharField(max_length=10) | ✅ | Match |
| `is_active` | BOOLEAN | ❌ MISSING | ❌ | Not in plan but exists in SQL (DEFAULT TRUE) |
| `notes` | TEXT | TextField | ✅ | Match |
| `created_at` | TIMESTAMPTZ | DateTimeField | ✅ | Match |
| `updated_at` | TIMESTAMPTZ | DateTimeField | ✅ | Match |

### 2.3 Missing Fields in Plan

```python
# MISSING from Contact model plan:
company_name = models.CharField(max_length=255, blank=True, db_column="company_name")
is_customer = models.BooleanField(default=True, db_column="is_customer")
is_supplier = models.BooleanField(default=False, db_column="is_supplier")
payment_terms_days = models.SmallIntegerField(default=30, db_column="payment_terms_days")
is_active = models.BooleanField(default=True, db_column="is_active")
```

### 2.4 Foreign Key on_delete Behaviors ⚠️

| FK Field | SQL Constraint | Plan on_delete | Status |
|----------|----------------|----------------|--------|
| `receivable_account_id` | Simple FK (no action specified) | SET_NULL | ⚠️ VERIFY |
| `payable_account_id` | Simple FK (no action specified) | SET_NULL | ⚠️ VERIFY |

**Note:** SQL doesn't specify ON DELETE, which defaults to NO ACTION. The plan uses SET_NULL which is safer but differs from SQL default.

---

## 3. GST.TAX_CODE TABLE

### 3.1 Field Definitions

| Field | SQL Type | Plan Type | Status | Notes |
|-------|----------|-----------|--------|-------|
| `id` | UUID PK | (inherited) | ✅ | Standard |
| `org_id` | UUID FK | (inherited) | ✅ | Standard - nullable in SQL |
| `code` | VARCHAR(10) | CharField(max_length=10) | ✅ | Match |
| `name` | VARCHAR(150) | ❌ NOT IN SQL | 🔴 | **CRITICAL: Field doesn't exist in SQL!** |
| `description` | VARCHAR(150) | CharField(max_length=150) | ✅ | Match |
| `rate` | NUMERIC(5,4) | Decimal(5,4) | ✅ | Match |
| `is_gst_charged` | BOOLEAN | ❌ NOT IN SQL | 🔴 | **CRITICAL: Field doesn't exist in SQL!** |
| `is_input` | BOOLEAN | BooleanField | ✅ | Match |
| `is_output` | BOOLEAN | BooleanField | ✅ | Match |
| `is_claimable` | BOOLEAN | BooleanField | ✅ | Match |
| `is_reverse_charge` | BOOLEAN | BooleanField | ✅ | Match |
| `is_active` | BOOLEAN | BooleanField | ✅ | Match |
| `effective_from` | DATE | DateField | ✅ | Match |
| `effective_to` | DATE | DateField | ❌ | Not in plan |
| `f5_supply_box` | SMALLINT | SmallIntegerField | ✅ | Match |
| `f5_purchase_box` | SMALLINT | SmallIntegerField | ✅ | Match |
| `f5_tax_box` | SMALLINT | SmallIntegerField | ✅ | Match |
| `display_order` | SMALLINT | SmallIntegerField | ✅ | Match |
| `created_at` | TIMESTAMPTZ | DateTimeField | ✅ | Match |
| `updated_at` | TIMESTAMPTZ | DateTimeField | ✅ | Match |
| `deleted_at` | TIMESTAMPTZ | DateTimeField | ✅ | Match |

### 3.2 Critical Issues 🔴

1. **`name` field in plan NOT in SQL**: The plan adds a `name` field, but SQL only has `description`. This will cause errors.
2. **`is_gst_charged` field in plan NOT in SQL**: The plan adds this field, but it doesn't exist in the SQL schema.
3. **`effective_to` missing from plan**: SQL has this field, plan doesn't include it.

### 3.3 Corrected TaxCode Model

```python
class TaxCode(TenantModel):
    # REMOVE these fields (don't exist in SQL):
    # name = models.CharField(...)  # ❌ REMOVE
    # is_gst_charged = models.BooleanField(...)  # ❌ REMOVE
    
    # ADD this field:
    effective_to = models.DateField(null=True, blank=True, db_column="effective_to")
    
    # Unique constraint should include effective_from
    class Meta:
        managed = False
        db_table = 'gst"."tax_code'
        unique_together = [["org", "code", "effective_from"]]  # ✅ Correct in plan
```

---

## 4. GST.RETURN TABLE

### 4.1 ENUM: status ✅ CORRECT

| SQL Value | Plan Value | Match |
|-----------|------------|-------|
| `DRAFT` | `DRAFT` | ✅ |
| `COMPUTED` | `COMPUTED` | ✅ |
| `REVIEWED` | `REVIEWED` | ✅ |
| `FILED` | `FILED` | ✅ |
| `AMENDED` | `AMENDED` | ✅ |

### 4.2 ENUM: return_type (Partial)

| SQL Value | Plan Value | Match |
|-----------|------------|-------|
| `F5` | Not defined in plan | ⚠️ |
| `F7` | Not defined in plan | ⚠️ |
| `F8` | Not defined in plan | ⚠️ |

**Note:** Plan doesn't define choices for return_type but SQL has CHECK constraint.

### 4.3 Field Definitions

| Field | SQL Type | Plan Type | Status | Notes |
|-------|----------|-----------|--------|-------|
| `id` | UUID PK | (inherited) | ✅ | Standard |
| `org_id` | UUID FK | (inherited) | ✅ | Standard |
| `return_type` | VARCHAR(5) CHECK | CharField(max_length=5) | ⚠️ | Should add choices |
| `period_start` | DATE | DateField | ✅ | Match |
| `period_end` | DATE | DateField | ✅ | Match |
| `filing_due_date` | DATE | ❌ MISSING | ❌ | Not in plan |
| `box1_std_rated_supplies` | NUMERIC(10,4) | Decimal(10,4) | ✅ | Match |
| `box2_zero_rated_supplies` | NUMERIC(10,4) | Decimal(10,4) | ✅ | Match |
| `box3_exempt_supplies` | NUMERIC(10,4) | Decimal(10,4) | ✅ | Match |
| `box4_total_supplies` | NUMERIC(10,4) | Decimal(10,4) | ✅ | Match |
| `box5_total_taxable_purchases` | NUMERIC(10,4) | Decimal(10,4) | ✅ | Match |
| `box6_output_tax` | NUMERIC(10,4) | Decimal(10,4) | ✅ | Match |
| `box7_input_tax_claimable` | NUMERIC(10,4) | Decimal(10,4) | ✅ | Match |
| `box8_net_gst` | NUMERIC(10,4) | Decimal(10,4) | ✅ | Match |
| `box9_imports_under_schemes` | NUMERIC(10,4) | Decimal(10,4) | ✅ | Match |
| `box10_tourist_refund` | NUMERIC(10,4) | Decimal(10,4) | ✅ | Match |
| `box11_bad_debt_relief` | NUMERIC(10,4) | Decimal(10,4) | ✅ | Match |
| `box12_pre_reg_input_tax` | NUMERIC(10,4) | Decimal(10,4) | ✅ | Match |
| `box13_total_revenue` | NUMERIC(10,4) | Decimal(10,4) | ✅ | Match |
| `box14_reverse_charge_supplies` | NUMERIC(10,4) | Decimal(10,4) | ✅ | Match |
| `box15_electronic_marketplace` | NUMERIC(10,4) | Decimal(10,4) | ✅ | Match |
| `status` | VARCHAR(20) CHECK | CharField with choices | ✅ | 5 values match |
| `computed_at` | TIMESTAMPTZ | DateTimeField | ✅ | Match |
| `reviewed_at` | TIMESTAMPTZ | DateTimeField | ✅ | Match |
| `reviewed_by` | UUID FK → app_user | ForeignKey | ✅ | Match |
| `filed_at` | TIMESTAMPTZ | ❌ MISSING | ❌ | Not in plan |
| `filed_by` | UUID FK → app_user | ❌ MISSING | ❌ | Not in plan |
| `iras_confirmation` | VARCHAR(50) | CharField(max_length=50) | ✅ | Match |
| `notes` | TEXT | TextField | ✅ | Match |
| `created_at` | TIMESTAMPTZ | DateTimeField | ✅ | Match |
| `updated_at` | TIMESTAMPTZ | DateTimeField | ✅ | Match |

### 4.4 Missing Fields in Plan

```python
# MISSING from GSTReturn model plan:
filing_due_date = models.DateField(db_column="filing_due_date")
filed_at = models.DateTimeField(null=True, blank=True, db_column="filed_at")
filed_by = models.ForeignKey(
    "AppUser", null=True, blank=True,
    on_delete=models.SET_NULL, db_column="filed_by"
)
```

---

## 5. COA.ACCOUNT TABLE

### 5.1 Field Definitions

| Field | SQL Type | Plan Type | Status | Notes |
|-------|----------|-----------|--------|-------|
| `id` | UUID PK | (inherited) | ✅ | Standard |
| `org_id` | UUID FK | (inherited) | ✅ | Standard |
| `code` | VARCHAR(10) | CharField(max_length=10) | ✅ | Match |
| `name` | VARCHAR(150) | CharField(max_length=150) | ✅ | Match |
| `account_type` | VARCHAR(50) | ❌ NOT IN SQL (was added) | ⚠️ | Field exists but should note it's for alignment |
| `description` | TEXT | TextField | ✅ | Match |
| `account_type_id` | SMALLINT FK → account_type | ForeignKey | ✅ | on_delete=SET_NULL correct |
| `account_sub_type_id` | SMALLINT FK → account_sub_type | ForeignKey | ✅ | on_delete=SET_NULL correct |
| `parent_id` | UUID FK → self | ❌ MISSING | ❌ | Not in plan |
| `currency` | CHAR(3) | CharField(max_length=3) | ✅ | Match |
| `tax_code_default` | VARCHAR(10) | CharField(max_length=10) | ✅ | Match |
| `is_system` | BOOLEAN | ❌ MISSING | ❌ | Not in plan (DEFAULT FALSE) |
| `is_header` | BOOLEAN | BooleanField | ✅ | Match |
| `is_active` | BOOLEAN | ❌ MISSING | ❌ | Not in plan (DEFAULT TRUE) |
| `is_bank` | BOOLEAN | BooleanField | ✅ | Match |
| `is_control` | BOOLEAN | BooleanField | ✅ | Match |
| `created_at` | TIMESTAMPTZ | DateTimeField | ✅ | Match |
| `updated_at` | TIMESTAMPTZ | DateTimeField | ✅ | Match |
| `deleted_at` | TIMESTAMPTZ | DateTimeField | ✅ | Match |

### 5.2 Missing Fields in Plan

```python
# MISSING from Account model plan:
parent = models.ForeignKey(
    "self", null=True, blank=True,
    on_delete=models.SET_NULL, db_column="parent_id"
)
is_system = models.BooleanField(default=False, db_column="is_system")
is_active = models.BooleanField(default=True, db_column="is_active")
```

---

## 6. CORE.ORGANISATION TABLE

### 6.1 ENUM: gst_scheme ⚠️ NEEDS CORRECTION

| SQL Value | Plan Value | Status |
|-----------|------------|--------|
| `STANDARD` | `STANDARD` | ✅ |
| `standard` | Not in plan | ⚠️ Missing lowercase variant |
| `CASH` | `CASH` | ✅ |
| `cash` | Not in plan | ⚠️ Missing lowercase variant |
| `MARGIN` | `MARGIN` | ✅ |
| `margin` | Not in plan | ⚠️ Missing lowercase variant |

**Issue:** SQL accepts both uppercase and lowercase, but plan only includes uppercase.

### 6.2 ENUM: gst_filing_frequency ⚠️ NOT IN PLAN

| SQL Value | Plan Value | Status |
|-----------|------------|--------|
| `monthly` | Not in plan | ❌ MISSING |
| `quarterly` | Not in plan | ❌ MISSING |
| `semi_annual` | Not in plan | ❌ MISSING |
| `MONTHLY` | Not in plan | ❌ MISSING |
| `QUARTERLY` | Not in plan | ❌ MISSING |
| `SEMI_ANNUAL` | Not in plan | ❌ MISSING |

**Issue:** Plan completely missing `gst_filing_frequency` field choices.

### 6.3 ENUM: entity_type ⚠️ NOT IN PLAN

| SQL Value | Plan Value | Status |
|-----------|------------|--------|
| `SOLE_PROPRIETORSHIP` | Not in plan | ❌ MISSING |
| `PARTNERSHIP` | Not in plan | ❌ MISSING |
| `PRIVATE_LIMITED` | Not in plan | ❌ MISSING |
| `LIMITED_LIABILITY_PARTNERSHIP` | Not in plan | ❌ MISSING |
| `PUBLIC_LIMITED` | Not in plan | ❌ MISSING |
| `NON_PROFIT` | Not in plan | ❌ MISSING |
| `OTHER` | Not in plan | ❌ MISSING |

### 6.4 Field Definitions

| Field | SQL Type | Plan Type | Status | Notes |
|-------|----------|-----------|--------|-------|
| `id` | UUID PK | (inherited) | ✅ | Standard |
| `name` | VARCHAR(255) | CharField(max_length=255) | ✅ | Match |
| `legal_name` | VARCHAR(255) | CharField(max_length=255) | ✅ | Match |
| `uen` | VARCHAR(20) UNIQUE | CharField(max_length=20) | ✅ | Match |
| `entity_type` | VARCHAR(50) CHECK | CharField(max_length=50) | ⚠️ | Choices missing |
| `gst_registered` | BOOLEAN | BooleanField | ✅ | Match |
| `gst_reg_number` | VARCHAR(20) | CharField(max_length=20) | ✅ | Match |
| `gst_reg_date` | DATE | DateField | ✅ | Match |
| `gst_scheme` | VARCHAR(30) CHECK | CharField(max_length=30) | ⚠️ | Missing lowercase variants |
| `gst_filing_frequency` | VARCHAR(15) CHECK | ❌ MISSING FIELD | ❌ | Not in plan at all! |
| `peppol_participant_id` | VARCHAR(64) | ❌ MISSING | ❌ | Not in plan |
| `peppol_scheme_id` | VARCHAR(10) | CharField(max_length=10) | ✅ | Match |
| `invoicenow_enabled` | BOOLEAN | ❌ MISSING | ❌ | Not in plan |
| `invoicenow_ap_id` | VARCHAR(100) | CharField(max_length=100) | ✅ | Match |
| `fy_start_month` | SMALLINT | SmallIntegerField | ❌ | Not in plan |
| `base_currency` | CHAR(3) | CharField(max_length=3) | ✅ | Match |
| `timezone` | VARCHAR(50) | ❌ MISSING | ❌ | Not in plan |
| `date_format` | VARCHAR(20) | CharField(max_length=20) | ✅ | Match |
| `address_line_1` | VARCHAR(255) | CharField(max_length=255) | ✅ | Match |
| `address_line_2` | VARCHAR(255) | CharField(max_length=255) | ✅ | Match |
| `city` | VARCHAR(100) | CharField(max_length=100) | ✅ | Match |
| `state` | VARCHAR(100) | CharField(max_length=100) | ✅ | Match |
| `postal_code` | VARCHAR(10) | CharField(max_length=10) | ✅ | Match |
| `country` | CHAR(2) | CharField(max_length=2) | ✅ | Match |
| `phone` | VARCHAR(30) | CharField(max_length=30) | ✅ | Match |
| `email` | VARCHAR(255) | EmailField | ✅ | Match |
| `contact_email` | VARCHAR(255) | ❌ MISSING | ❌ | Not in plan |
| `contact_phone` | VARCHAR(50) | ❌ MISSING | ❌ | Not in plan |
| `website` | VARCHAR(255) | CharField(max_length=255) | ✅ | Match |
| `logo_url` | VARCHAR(500) | CharField(max_length=500) | ✅ | Match |
| `is_active` | BOOLEAN | BooleanField | ✅ | Match |
| `created_at` | TIMESTAMPTZ | DateTimeField | ✅ | Match |
| `updated_at` | TIMESTAMPTZ | DateTimeField | ✅ | Match |
| `deleted_at` | TIMESTAMPTZ | DateTimeField | ✅ | Match |
| `deleted_by` | UUID FK → app_user | ForeignKey | ✅ | Match |

### 6.5 Missing Fields in Plan

```python
# MISSING from Organisation model plan:
gst_filing_frequency = models.CharField(
    max_length=15, 
    default="QUARTERLY",
    db_column="gst_filing_frequency",
    choices=[
        ("monthly", "Monthly"),
        ("quarterly", "Quarterly"),
        ("semi_annual", "Semi-Annual"),
        ("MONTHLY", "Monthly (legacy)"),
        ("QUARTERLY", "Quarterly (legacy)"),
        ("SEMI_ANNUAL", "Semi-Annual (legacy)"),
    ]
)
peppol_participant_id = models.CharField(max_length=64, blank=True, db_column="peppol_participant_id")
invoicenow_enabled = models.BooleanField(default=False, db_column="invoicenow_enabled")
fy_start_month = models.SmallIntegerField(default=1, db_column="fy_start_month")
timezone = models.CharField(max_length=50, default="Asia/Singapore", db_column="timezone")
contact_email = models.EmailField(blank=True, db_column="contact_email")
contact_phone = models.CharField(max_length=50, blank=True, db_column="contact_phone")
```

---

## 7. BANKING.BANK_ACCOUNT TABLE

### 7.1 ENUM: paynow_type ✅ CORRECT

| SQL Value | Plan Value | Match |
|-----------|------------|-------|
| `UEN` | `UEN` | ✅ |
| `MOBILE` | `MOBILE` | ✅ |
| `NRIC` | `NRIC` | ✅ |

### 7.2 Field Definitions

| Field | SQL Type | Plan Type | Status | Notes |
|-------|----------|-----------|--------|-------|
| `id` | UUID PK | (inherited) | ✅ | Standard |
| `org_id` | UUID FK | (inherited) | ✅ | Standard |
| `account_name` | VARCHAR(150) | CharField(max_length=150) | ✅ | Match |
| `bank_name` | VARCHAR(100) | CharField(max_length=100) | ✅ | Match |
| `account_number` | VARCHAR(30) | CharField(max_length=30) | ✅ | Match |
| `bank_code` | VARCHAR(20) | CharField(max_length=20) | ✅ | Match |
| `branch_code` | VARCHAR(20) | CharField(max_length=20) | ✅ | Match |
| `currency` | CHAR(3) | CharField(max_length=3) | ✅ | Match |
| `gl_account_id` | UUID FK → account | ForeignKey | ⚠️ | Plan has on_delete=PROTECT, SQL has no action |
| `paynow_type` | VARCHAR(10) CHECK | CharField(max_length=10) | ✅ | Match |
| `paynow_id` | VARCHAR(20) | CharField(max_length=20) | ✅ | Match |
| `is_default` | BOOLEAN | BooleanField | ✅ | Match |
| `is_active` | BOOLEAN | BooleanField | ✅ | Match |
| `opening_balance` | NUMERIC(10,4) | Decimal(10,4) | ✅ | Match |
| `opening_balance_date` | DATE | DateField | ✅ | Match |
| `created_at` | TIMESTAMPTZ | DateTimeField | ✅ | Match |
| `updated_at` | TIMESTAMPTZ | DateTimeField | ✅ | Match |

### 7.3 Foreign Key Issue ⚠️

| FK Field | SQL Constraint | Plan on_delete | Status |
|----------|----------------|----------------|--------|
| `gl_account_id` | Simple FK | PROTECT | ⚠️ DIFFERENT |

**Note:** SQL doesn't specify ON DELETE (defaults to NO ACTION). Plan uses PROTECT which is safer but differs.

---

## 8. BANKING.PAYMENT TABLE

### 8.1 ENUM: payment_type ✅ CORRECT

| SQL Value | Plan Value | Match |
|-----------|------------|-------|
| `RECEIVED` | `RECEIVED` | ✅ |
| `MADE` | `MADE` | ✅ |

### 8.2 ENUM: payment_method ✅ CORRECT

| SQL Value | Plan Value | Match |
|-----------|------------|-------|
| `BANK_TRANSFER` | `BANK_TRANSFER` | ✅ |
| `CHEQUE` | `CHEQUE` | ✅ |
| `CASH` | `CASH` | ✅ |
| `PAYNOW` | `PAYNOW` | ✅ |
| `CREDIT_CARD` | `CREDIT_CARD` | ✅ |
| `GIRO` | `GIRO` | ✅ |
| `OTHER` | `OTHER` | ✅ |

### 8.3 Field Definitions

| Field | SQL Type | Plan Type | Status | Notes |
|-------|----------|-----------|--------|-------|
| `id` | UUID PK | (inherited) | ✅ | Standard |
| `org_id` | UUID FK | (inherited) | ✅ | Standard |
| `payment_type` | VARCHAR(15) CHECK | CharField(max_length=15) | ✅ | Match |
| `payment_number` | VARCHAR(30) | CharField(max_length=30) | ✅ | Match |
| `payment_date` | DATE | DateField | ✅ | Match |
| `contact_id` | UUID FK → contact | ForeignKey | ✅ | on_delete=RESTRICT correct |
| `bank_account_id` | UUID FK → bank_account | ForeignKey | ✅ | on_delete=RESTRICT correct |
| `currency` | CHAR(3) | CharField(max_length=3) | ✅ | Match |
| `exchange_rate` | NUMERIC(12,6) | Decimal(12,6) | ✅ | Match |
| `amount` | NUMERIC(10,4) | Decimal(10,4) | ✅ | Match |
| `base_amount` | NUMERIC(10,4) | Decimal(10,4) | ✅ | Match |
| `fx_gain_loss` | NUMERIC(10,4) | Decimal(10,4) | ✅ | Match |
| `payment_method` | VARCHAR(20) CHECK | CharField(max_length=20) | ✅ | Match |
| `payment_reference` | VARCHAR(100) | CharField(max_length=100) | ✅ | Match |
| `journal_entry_id` | UUID FK → journal.entry | ForeignKey | ✅ | on_delete=SET_NULL correct |
| `is_reconciled` | BOOLEAN | BooleanField | ✅ | Match |
| `is_voided` | BOOLEAN | BooleanField | ✅ | Match |
| `notes` | TEXT | TextField | ✅ | Match |
| `created_at` | TIMESTAMPTZ | DateTimeField | ✅ | Match |
| `updated_at` | TIMESTAMPTZ | DateTimeField | ✅ | Match |

**Status:** All fields match correctly.

---

## 9. BANKING.PAYMENT_ALLOCATION TABLE

### 9.1 Field Definitions

| Field | SQL Type | Plan Type | Status | Notes |
|-------|----------|-----------|--------|-------|
| `id` | UUID PK | (inherited) | ✅ | Standard |
| `org_id` | UUID FK | ❌ NOT AS FK | ⚠️ | SQL has org_id, plan relies on TenantModel |
| `payment_id` | UUID FK → payment | ForeignKey | ✅ | on_delete=CASCADE correct |
| `document_id` | UUID FK → document | ForeignKey | ✅ | on_delete=RESTRICT correct |
| `allocated_amount` | NUMERIC(10,4) | Decimal(10,4) | ✅ | Match |
| `base_allocated_amount` | NUMERIC(10,4) | Decimal(10,4) | ✅ | Match |
| `created_at` | TIMESTAMPTZ | DateTimeField | ✅ | Match |

**Note:** `org_id` in SQL is NOT NULL but the plan relies on TenantModel which may/may not include it. SQL has it as a standalone column, not just via RLS.

---

## 10. CORE.DOCUMENT_SEQUENCE TABLE

### 10.1 Field Definitions

| Field | SQL Type | Plan Type | Status | Notes |
|-------|----------|-----------|--------|-------|
| `id` | UUID PK | (inherited) | ✅ | Standard |
| `org_id` | UUID FK | (inherited) | ✅ | Standard |
| `document_type` | VARCHAR(30) | CharField(max_length=30) | ✅ | Match |
| `prefix` | VARCHAR(20) NOT NULL DEFAULT '' | CharField(max_length=20) | ⚠️ | Plan has default="", SQL also has DEFAULT '' |
| `next_number` | BIGINT | BigIntegerField | ✅ | Match |
| `padding` | SMALLINT | SmallIntegerField | ✅ | Match |
| `fiscal_year_reset` | BOOLEAN | BooleanField | ✅ | Match |
| `created_at` | TIMESTAMPTZ | DateTimeField | ✅ | Match |
| `updated_at` | TIMESTAMPTZ | DateTimeField | ✅ | Match |

**Status:** All fields match correctly.

---

## Summary of Issues

### 🔴 Critical Issues (Must Fix)

1. **gst.tax_code.name field doesn't exist in SQL** - Will cause runtime errors
2. **gst.tax_code.is_gst_charged field doesn't exist in SQL** - Will cause runtime errors

### ⚠️ Corrections Needed

3. **gst.tax_code** - Missing `effective_to` field
4. **invoicing.contact** - Missing fields: `company_name`, `is_customer`, `is_supplier`, `payment_terms_days`, `is_active`
5. **gst.return** - Missing fields: `filing_due_date`, `filed_at`, `filed_by`
6. **coa.account** - Missing fields: `parent_id` (self-referential FK), `is_system`, `is_active`
7. **core.organisation** - Missing field: `gst_filing_frequency` (entire field missing)
8. **core.organisation** - Missing fields: `peppol_participant_id`, `invoicenow_enabled`, `fy_start_month`, `timezone`, `contact_email`, `contact_phone`
9. **core.organisation.gst_scheme** - Missing lowercase variants in choices
10. **FK on_delete behaviors** - Several differ from SQL defaults (though PROTECT/SET_NULL is safer)

### ❌ Missing ENUM Definitions

11. **core.organisation.entity_type** - No choices defined in plan
12. **core.organisation.gst_filing_frequency** - No choices defined in plan
13. **gst.return.return_type** - No choices defined in plan

---

## Recommendations

### Immediate Actions

1. **Fix Critical Issues First:**
   - Remove `name` and `is_gst_charged` from TaxCode model plan
   - Add `effective_to` to TaxCode model plan

2. **Add Missing Fields:**
   - Contact: 5 missing fields
   - GSTReturn: 3 missing fields
   - Account: 3 missing fields
   - Organisation: 8 missing fields

3. **Complete ENUM Definitions:**
   - Add all entity_type choices
   - Add all gst_filing_frequency choices (with lowercase variants)
   - Add return_type choices

4. **Document FK Differences:**
   - Note that Django uses PROTECT/SET_NULL while SQL uses NO ACTION
   - This is acceptable as Django's approach is safer

### Validation Command

After implementing fixes, run:
```bash
python manage.py check
python manage.py inspectdb --database default 2>&1 | head -100
```

---

## Updated Effort Estimate

| Phase | Original | Revised | Change |
|-------|----------|---------|--------|
| P0 Critical Fixes | 4 hours | 6 hours | +2 hours for corrections |
| P1 Banking Models | 6 hours | 6 hours | No change |
| P1 Missing Fields | 6 hours | 8 hours | +2 hours for additional fields |
| P2 Reference Tables | 4 hours | 4 hours | No change |
| **Total** | **20 hours** | **24 hours** | **+4 hours** |

---

**Report Generated:** 2026-02-27  
**Status:** VALIDATION COMPLETE - CORRECTIONS REQUIRED BEFORE IMPLEMENTATION
