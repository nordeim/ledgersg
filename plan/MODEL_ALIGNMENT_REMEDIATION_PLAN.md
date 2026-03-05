# LedgerSG Model Alignment Remediation Plan

**Version:** 1.0.0  
**Date:** 2026-02-27  
**Status:** READY FOR VALIDATION  
**Estimated Effort:** 3-4 days  

---

## Executive Summary

This remediation plan addresses the alignment gaps between `database_schema.sql` (v1.0.1) and the Django backend models. The current alignment is at **54%**, with critical ENUM mismatches that will cause runtime errors.

### Current State
- **SQL Tables:** 28
- **Django Models:** 15
- **Fully Aligned:** 4 tables (14%)
- **Partially Aligned:** 9 tables (32%)
- **Missing Models:** 15 tables (54%)

### Target State
- **100% ENUM alignment** - prevent CHECK constraint violations
- **100% Critical field alignment** - enable core functionality
- **Create missing banking models** - enable payment processing
- **Create document sequence model** - enable auto-numbering

---

## Phase Breakdown

### Phase 1: P0 Critical Fixes (Day 1) - ESTIMATED 4 HOURS

**Goal:** Fix issues that will cause immediate runtime errors

#### 1.1 Fix InvoiceDocument ENUMs
**File:** `apps/backend/apps/core/models/invoice_document.py`

**Changes:**
```python
# BEFORE (INCORRECT)
DOCUMENT_TYPES = [
    ("SALES_INVOICE", "Invoice"),
    ("SALES_QUOTE", "Quote"),
    ("SALES_CREDIT_NOTE", "Credit Note"),
]

STATUS_CHOICES = [
    ("DRAFT", "Draft"),
    ("SENT", "Sent"),
    ("APPROVED", "Approved"),
    ("PARTIALLY_PAID", "Partially Paid"),
    ("PAID", "Paid"),
    ("VOID", "Void"),
]

# AFTER (CORRECT - matches SQL)
DOCUMENT_TYPES = [
    ("SALES_INVOICE", "Sales Invoice"),
    ("SALES_CREDIT_NOTE", "Sales Credit Note"),
    ("SALES_DEBIT_NOTE", "Sales Debit Note"),
    ("SALES_QUOTE", "Sales Quote"),
    ("PURCHASE_INVOICE", "Purchase Invoice"),
    ("PURCHASE_CREDIT_NOTE", "Purchase Credit Note"),
    ("PURCHASE_DEBIT_NOTE", "Purchase Debit Note"),
    ("PURCHASE_ORDER", "Purchase Order"),
]

STATUS_CHOICES = [
    ("DRAFT", "Draft"),
    ("APPROVED", "Approved"),  # Note: SQL order has APPROVED before SENT
    ("SENT", "Sent"),
    ("PARTIALLY_PAID", "Partially Paid"),
    ("PAID", "Paid"),
    ("OVERDUE", "Overdue"),  # ADD THIS - missing in Django
    ("VOID", "Void"),
]
```

#### 1.2 Fix Organisation gst_scheme Choices
**File:** `apps/backend/apps/core/models/organisation.py`

**Changes:**
```python
# BEFORE (INCORRECT - will cause CHECK constraint violations)
gst_scheme = models.CharField(
    max_length=50,
    default="STANDARD",
    db_column="gst_scheme",
    choices=[
        ("STANDARD", "Standard GST"),
        ("CASH_ACCOUNTING", "Cash Accounting"),  # WRONG
        ("SECOND_HAND", "Second-Hand Goods"),    # WRONG
        ("TOURIST_REFUND", "Tourist Refund"),    # EXTRA
    ],
)

# AFTER (CORRECT - matches SQL CHECK constraint)
gst_scheme = models.CharField(
    max_length=30,
    default="STANDARD",
    db_column="gst_scheme",
    choices=[
        ("STANDARD", "Standard GST"),
        ("STANDARD", "Standard GST (legacy)"),  # Both cases accepted by SQL
        ("CASH", "Cash Accounting"),
        ("CASH", "Cash Accounting (legacy)"),
        ("MARGIN", "Margin Scheme"),
        ("MARGIN", "Margin Scheme (legacy)"),
    ],
)
```

#### 1.3 Fix InvoiceDocument contact FK
**File:** `apps/backend/apps/core/models/invoice_document.py`

**Changes:**
```python
# BEFORE
contact = models.ForeignKey(
    "Contact", on_delete=models.CASCADE,  # WRONG
    db_column="contact_id"
)

# AFTER
contact = models.ForeignKey(
    "Contact", on_delete=models.RESTRICT,  # CORRECT - matches SQL
    db_column="contact_id"
)
```

#### 1.4 Add Missing InvoiceDocument Fields
**Add 28 missing fields to InvoiceDocument model:**

```python
# Currency & Exchange
class InvoiceDocument(TenantModel, SequenceModel):
    # ... existing fields ...
    
    # Currency & Exchange Rate (missing)
    currency = models.CharField(max_length=3, default="SGD", db_column="currency")
    exchange_rate = models.DecimalField(
        max_digits=12, decimal_places=6, default=1.0,
        db_column="exchange_rate"
    )
    
    # Monetary Fields (missing)
    total_discount = models.DecimalField(
        max_digits=10, decimal_places=4, default=0,
        db_column="total_discount"
    )
    amount_paid = models.DecimalField(
        max_digits=10, decimal_places=4, default=0,
        db_column="amount_paid"
    )
    # Note: amount_due is GENERATED in SQL, not stored
    
    # Base Currency Equivalents (missing)
    base_subtotal = models.DecimalField(
        max_digits=10, decimal_places=4, default=0,
        db_column="base_subtotal"
    )
    base_total_gst = models.DecimalField(
        max_digits=10, decimal_places=4, default=0,
        db_column="base_total_gst"
    )
    base_total_amount = models.DecimalField(
        max_digits=10, decimal_places=4, default=0,
        db_column="base_total_amount"
    )
    
    # Notes & References (missing)
    internal_notes = models.TextField(blank=True, db_column="internal_notes")
    # customer_notes exists as 'notes' - verify mapping
    is_tax_invoice = models.BooleanField(default=False, db_column="is_tax_invoice")
    tax_invoice_label = models.CharField(
        max_length=50, blank=True, db_column="tax_invoice_label"
    )
    
    # InvoiceNow / Peppol (missing)
    peppol_message_id = models.UUIDField(null=True, blank=True, db_column="peppol_message_id")
    invoicenow_status = models.CharField(
        max_length=20, default="NOT_APPLICABLE",
        db_column="invoicenow_status",
        choices=[
            ("NOT_APPLICABLE", "Not Applicable"),
            ("PENDING", "Pending"),
            ("QUEUED", "Queued"),
            ("TRANSMITTED", "Transmitted"),
            ("DELIVERED", "Delivered"),
            ("FAILED", "Failed"),
            ("REJECTED", "Rejected"),
        ]
    )
    invoicenow_sent_at = models.DateTimeField(null=True, blank=True, db_column="invoicenow_sent_at")
    invoicenow_error = models.TextField(blank=True, db_column="invoicenow_error")
    
    # Workflow & Linkage (missing)
    journal_entry = models.ForeignKey(
        "JournalEntry", null=True, blank=True,
        on_delete=models.SET_NULL, db_column="journal_entry_id"
    )
    related_document = models.ForeignKey(
        "self", null=True, blank=True,
        on_delete=models.SET_NULL, db_column="related_document_id",
        related_name="related_documents"
    )
    
    # Audit Fields (missing)
    approved_at = models.DateTimeField(null=True, blank=True, db_column="approved_at")
    approved_by = models.ForeignKey(
        "AppUser", null=True, blank=True,
        on_delete=models.SET_NULL, db_column="approved_by",
        related_name="approved_documents"
    )
    voided_at = models.DateTimeField(null=True, blank=True, db_column="voided_at")
    voided_by = models.ForeignKey(
        "AppUser", null=True, blank=True,
        on_delete=models.SET_NULL, db_column="voided_by",
        related_name="voided_documents"
    )
    void_reason = models.TextField(blank=True, db_column="void_reason")
```

---

### Phase 2: P1 High Priority - Create Banking Models (Day 2) - ESTIMATED 6 HOURS

**Goal:** Create missing banking models for payment processing

#### 2.1 Create BankAccount Model
**New File:** `apps/backend/apps/core/models/bank_account.py`

```python
"""
BankAccount model for LedgerSG.

Maps to banking.bank_account table.
"""

from django.db import models
from common.models import TenantModel


class BankAccount(TenantModel):
    """Bank account model for reconciliation."""
    
    account_name = models.CharField(max_length=150, db_column="account_name")
    bank_name = models.CharField(max_length=100, db_column="bank_name")
    account_number = models.CharField(max_length=30, db_column="account_number")
    bank_code = models.CharField(max_length=20, blank=True, db_column="bank_code")
    branch_code = models.CharField(max_length=20, blank=True, db_column="branch_code")
    currency = models.CharField(max_length=3, default="SGD", db_column="currency")
    
    # Link to GL Account
    gl_account = models.ForeignKey(
        "Account", on_delete=models.PROTECT,
        db_column="gl_account_id"
    )
    
    # PayNow (Singapore)
    paynow_type = models.CharField(
        max_length=10, blank=True, db_column="paynow_type",
        choices=[
            ("UEN", "UEN"),
            ("MOBILE", "Mobile"),
            ("NRIC", "NRIC"),
        ]
    )
    paynow_id = models.CharField(max_length=20, blank=True, db_column="paynow_id")
    
    # Status
    is_default = models.BooleanField(default=False, db_column="is_default")
    is_active = models.BooleanField(default=True, db_column="is_active")
    opening_balance = models.DecimalField(
        max_digits=10, decimal_places=4, default=0,
        db_column="opening_balance"
    )
    opening_balance_date = models.DateField(null=True, blank=True, db_column="opening_balance_date")
    
    class Meta:
        managed = False
        db_table = 'banking"."bank_account'
        unique_together = [["org", "account_number"]]
```

#### 2.2 Create Payment Model
**New File:** `apps/backend/apps/core/models/payment.py`

```python
"""
Payment model for LedgerSG.

Maps to banking.payment table.
"""

from django.db import models
from common.models import TenantModel


class Payment(TenantModel):
    """Payment record for money received or made."""
    
    PAYMENT_TYPES = [
        ("RECEIVED", "Received"),
        ("MADE", "Made"),
    ]
    
    PAYMENT_METHODS = [
        ("BANK_TRANSFER", "Bank Transfer"),
        ("CHEQUE", "Cheque"),
        ("CASH", "Cash"),
        ("PAYNOW", "PayNow"),
        ("CREDIT_CARD", "Credit Card"),
        ("GIRO", "GIRO"),
        ("OTHER", "Other"),
    ]
    
    payment_type = models.CharField(
        max_length=15, db_column="payment_type",
        choices=PAYMENT_TYPES
    )
    payment_number = models.CharField(max_length=30, db_column="payment_number")
    payment_date = models.DateField(db_column="payment_date")
    
    # Parties
    contact = models.ForeignKey(
        "Contact", on_delete=models.RESTRICT,
        db_column="contact_id"
    )
    bank_account = models.ForeignKey(
        "BankAccount", on_delete=models.RESTRICT,
        db_column="bank_account_id"
    )
    
    # Amount
    currency = models.CharField(max_length=3, default="SGD", db_column="currency")
    exchange_rate = models.DecimalField(
        max_digits=12, decimal_places=6, default=1.0,
        db_column="exchange_rate"
    )
    amount = models.DecimalField(max_digits=10, decimal_places=4, db_column="amount")
    base_amount = models.DecimalField(max_digits=10, decimal_places=4, db_column="base_amount")
    fx_gain_loss = models.DecimalField(
        max_digits=10, decimal_places=4, default=0,
        db_column="fx_gain_loss"
    )
    
    # Payment Method
    payment_method = models.CharField(
        max_length=20, default="BANK_TRANSFER",
        db_column="payment_method", choices=PAYMENT_METHODS
    )
    payment_reference = models.CharField(max_length=100, blank=True, db_column="payment_reference")
    
    # Journal Link
    journal_entry = models.ForeignKey(
        "JournalEntry", null=True, blank=True,
        on_delete=models.SET_NULL, db_column="journal_entry_id"
    )
    
    # Status
    is_reconciled = models.BooleanField(default=False, db_column="is_reconciled")
    is_voided = models.BooleanField(default=False, db_column="is_voided")
    
    notes = models.TextField(blank=True, db_column="notes")
    
    class Meta:
        managed = False
        db_table = 'banking"."payment'
        unique_together = [["org", "payment_type", "payment_number"]]
```

#### 2.3 Create PaymentAllocation Model
**New File:** `apps/backend/apps/core/models/payment_allocation.py`

```python
"""
PaymentAllocation model for LedgerSG.

Maps to banking.payment_allocation table.
"""

from django.db import models
from common.models import TenantModel


class PaymentAllocation(TenantModel):
    """Maps payments to invoices (supports partial payments)."""
    
    payment = models.ForeignKey(
        "Payment", on_delete=models.CASCADE,
        db_column="payment_id"
    )
    document = models.ForeignKey(
        "InvoiceDocument", on_delete=models.RESTRICT,
        db_column="document_id"
    )
    allocated_amount = models.DecimalField(
        max_digits=10, decimal_places=4,
        db_column="allocated_amount"
    )
    base_allocated_amount = models.DecimalField(
        max_digits=10, decimal_places=4,
        db_column="base_allocated_amount"
    )
    
    class Meta:
        managed = False
        db_table = 'banking"."payment_allocation'
        unique_together = [["payment", "document"]]
```

#### 2.4 Create DocumentSequence Model
**New File:** `apps/backend/apps/core/models/document_sequence.py`

```python
"""
DocumentSequence model for LedgerSG.

Maps to core.document_sequence table.
"""

from django.db import models
from common.models import TenantModel


class DocumentSequence(TenantModel):
    """Auto-numbering sequence for documents."""
    
    document_type = models.CharField(max_length=30, db_column="document_type")
    prefix = models.CharField(max_length=20, default="", db_column="prefix")
    next_number = models.BigIntegerField(default=1, db_column="next_number")
    padding = models.SmallIntegerField(default=5, db_column="padding")
    fiscal_year_reset = models.BooleanField(default=False, db_column="fiscal_year_reset")
    
    class Meta:
        managed = False
        db_table = 'core"."document_sequence'
        unique_together = [["org", "document_type"]]
```

#### 2.5 Update __init__.py
**File:** `apps/backend/apps/core/models/__init__.py`

Add imports for new models:
```python
from .bank_account import BankAccount
from .payment import Payment
from .payment_allocation import PaymentAllocation
from .document_sequence import DocumentSequence

__all__ = [
    # ... existing exports ...
    "BankAccount",
    "Payment",
    "PaymentAllocation",
    "DocumentSequence",
]
```

---

### Phase 3: P1 High Priority - Add Missing Fields (Day 3) - ESTIMATED 6 HOURS

#### 3.1 Add Missing Contact Fields
**File:** `apps/backend/apps/core/models/contact.py`

```python
class Contact(TenantModel):
    # ... existing fields ...
    
    # Classification (missing)
    contact_type = models.CharField(
        max_length=10, blank=True, db_column="contact_type",
        choices=[
            ("CUSTOMER", "Customer"),
            ("SUPPLIER", "Supplier"),
            ("BOTH", "Both"),
        ]
    )
    legal_name = models.CharField(max_length=255, blank=True, db_column="legal_name")
    uen = models.CharField(max_length=20, blank=True, db_column="uen")
    gst_reg_number = models.CharField(max_length=20, blank=True, db_column="gst_reg_number")
    is_gst_registered = models.BooleanField(default=False, db_column="is_gst_registered")
    tax_code_default = models.CharField(max_length=10, blank=True, db_column="tax_code_default")
    
    # Communication (missing)
    fax = models.CharField(max_length=30, blank=True, db_column="fax")
    website = models.CharField(max_length=255, blank=True, db_column="website")
    
    # Address (missing)
    address_line_1 = models.CharField(max_length=255, blank=True, db_column="address_line_1")
    address_line_2 = models.CharField(max_length=255, blank=True, db_column="address_line_2")
    city = models.CharField(max_length=100, blank=True, db_column="city")
    state_province = models.CharField(max_length=100, blank=True, db_column="state_province")
    postal_code = models.CharField(max_length=20, blank=True, db_column="postal_code")
    country = models.CharField(max_length=2, default="SG", db_column="country")
    
    # Financial (missing)
    default_currency = models.CharField(max_length=3, default="SGD", db_column="default_currency")
    credit_limit = models.DecimalField(
        max_digits=10, decimal_places=4, null=True, blank=True,
        db_column="credit_limit"
    )
    receivable_account = models.ForeignKey(
        "Account", null=True, blank=True,
        on_delete=models.SET_NULL, db_column="receivable_account_id",
        related_name="contact_receivable"
    )
    payable_account = models.ForeignKey(
        "Account", null=True, blank=True,
        on_delete=models.SET_NULL, db_column="payable_account_id",
        related_name="contact_payable"
    )
    
    # InvoiceNow (missing)
    peppol_id = models.CharField(max_length=64, blank=True, db_column="peppol_id")
    peppol_scheme_id = models.CharField(max_length=10, blank=True, db_column="peppol_scheme_id")
    
    # Other (missing)
    notes = models.TextField(blank=True, db_column="notes")
```

#### 3.2 Add Missing TaxCode Fields
**File:** `apps/backend/apps/core/models/tax_code.py`

```python
class TaxCode(TenantModel):
    # ... existing fields ...
    
    # Remove: box_mapping (doesn't exist in SQL)
    
    # Add missing fields
    description = models.CharField(max_length=150, blank=True, db_column="description")
    is_input = models.BooleanField(default=False, db_column="is_input")
    is_output = models.BooleanField(default=False, db_column="is_output")
    is_claimable = models.BooleanField(default=True, db_column="is_claimable")
    is_reverse_charge = models.BooleanField(default=False, db_column="is_reverse_charge")
    
    # F5 Box Mappings
    f5_supply_box = models.SmallIntegerField(null=True, blank=True, db_column="f5_supply_box")
    f5_purchase_box = models.SmallIntegerField(null=True, blank=True, db_column="f5_purchase_box")
    f5_tax_box = models.SmallIntegerField(null=True, blank=True, db_column="f5_tax_box")
    
    display_order = models.SmallIntegerField(default=0, db_column="display_order")
    deleted_at = models.DateTimeField(null=True, blank=True, db_column="deleted_at")
    
    class Meta:
        managed = False
        db_table = 'gst"."tax_code'
        unique_together = [["org", "code", "effective_from"]]  # Fix: add effective_from
```

#### 3.3 Add Missing GSTReturn Fields
**File:** `apps/backend/apps/core/models/gst_return.py`

```python
class GSTReturn(TenantModel):
    # ... existing fields ...
    
    # Missing F5 Boxes
    box11_bad_debt_relief = models.DecimalField(
        max_digits=10, decimal_places=4, default=0,
        db_column="box11_bad_debt_relief"
    )
    box12_pre_reg_input_tax = models.DecimalField(
        max_digits=10, decimal_places=4, default=0,
        db_column="box12_pre_reg_input_tax"
    )
    box13_total_revenue = models.DecimalField(
        max_digits=10, decimal_places=4, default=0,
        db_column="box13_total_revenue"
    )
    box14_reverse_charge_supplies = models.DecimalField(
        max_digits=10, decimal_places=4, default=0,
        db_column="box14_reverse_charge_supplies"
    )
    box15_electronic_marketplace = models.DecimalField(
        max_digits=10, decimal_places=4, default=0,
        db_column="box15_electronic_marketplace"
    )
    
    # Workflow fields
    computed_at = models.DateTimeField(null=True, blank=True, db_column="computed_at")
    reviewed_at = models.DateTimeField(null=True, blank=True, db_column="reviewed_at")
    reviewed_by = models.ForeignKey(
        "AppUser", null=True, blank=True,
        on_delete=models.SET_NULL, db_column="reviewed_by"
    )
    iras_confirmation = models.CharField(max_length=50, blank=True, db_column="iras_confirmation")
    notes = models.TextField(blank=True, db_column="notes")
    
    # Fix: rename filing_reference to iras_confirmation
    # Remove: filing_reference field
```

#### 3.4 Add Missing Account Fields
**File:** `apps/backend/apps/core/models/account.py`

```python
class Account(TenantModel):
    # ... existing fields ...
    
    # Remove: account_type CharField (replaced by FK)
    
    # Add missing fields
    account_type_ref = models.ForeignKey(
        "AccountType", null=True, blank=True,
        on_delete=models.SET_NULL, db_column="account_type_id"
    )
    account_sub_type = models.ForeignKey(
        "AccountSubType", null=True, blank=True,
        on_delete=models.SET_NULL, db_column="account_sub_type_id"
    )
    currency = models.CharField(max_length=3, default="SGD", db_column="currency")
    tax_code_default = models.CharField(max_length=10, blank=True, db_column="tax_code_default")
    is_header = models.BooleanField(default=False, db_column="is_header")
    is_bank = models.BooleanField(default=False, db_column="is_bank")
    is_control = models.BooleanField(default=False, db_column="is_control")
    description = models.TextField(blank=True, db_column="description")
    deleted_at = models.DateTimeField(null=True, blank=True, db_column="deleted_at")
```

#### 3.5 Add Missing Organisation Fields
**File:** `apps/backend/apps/core/models/organisation.py`

```python
class Organisation(BaseModel):
    # ... existing fields ...
    
    # InvoiceNow (missing)
    peppol_scheme_id = models.CharField(
        max_length=10, default="0195", blank=True,
        db_column="peppol_scheme_id"
    )
    invoicenow_ap_id = models.CharField(max_length=100, blank=True, db_column="invoicenow_ap_id")
    
    # Other (missing)
    date_format = models.CharField(
        max_length=20, default="DD/MM/YYYY",
        db_column="date_format"
    )
    state = models.CharField(max_length=100, blank=True, db_column="state")
    logo_url = models.CharField(max_length=500, blank=True, db_column="logo_url")
    email = models.EmailField(blank=True, db_column="email")
    phone = models.CharField(max_length=30, blank=True, db_column="phone")
    website = models.CharField(max_length=255, blank=True, db_column="website")
```

---

### Phase 4: P2 Medium Priority - Reference Tables & Audit (Day 4) - ESTIMATED 4 HOURS

#### 4.1 Create AccountType Model
**New File:** `apps/backend/apps/core/models/account_type.py`

```python
"""
AccountType model for LedgerSG.

Maps to coa.account_type table (reference data).
"""

from django.db import models


class AccountType(models.Model):
    """Account type classification."""
    
    id = models.SmallIntegerField(primary_key=True, db_column="id")
    code = models.CharField(max_length=20, unique=True, db_column="code")
    name = models.CharField(max_length=50, db_column="name")
    normal_balance = models.CharField(
        max_length=6, db_column="normal_balance",
        choices=[("DEBIT", "Debit"), ("CREDIT", "Credit")]
    )
    classification = models.CharField(
        max_length=20, db_column="classification",
        choices=[("BALANCE_SHEET", "Balance Sheet"), ("INCOME_STATEMENT", "Income Statement")]
    )
    display_order = models.SmallIntegerField(db_column="display_order")
    is_debit_positive = models.BooleanField(db_column="is_debit_positive")
    
    class Meta:
        managed = False
        db_table = 'coa"."account_type'
```

#### 4.2 Create AccountSubType Model
**New File:** `apps/backend/apps/core/models/account_sub_type.py`

```python
"""
AccountSubType model for LedgerSG.

Maps to coa.account_sub_type table (reference data).
"""

from django.db import models


class AccountSubType(models.Model):
    """Account sub-type classification."""
    
    id = models.SmallIntegerField(primary_key=True, db_column="id")
    account_type = models.ForeignKey(
        "AccountType", on_delete=models.CASCADE,
        db_column="account_type_id"
    )
    code = models.CharField(max_length=30, unique=True, db_column="code")
    name = models.CharField(max_length=80, db_column="name")
    description = models.TextField(blank=True, db_column="description")
    display_order = models.SmallIntegerField(db_column="display_order")
    
    class Meta:
        managed = False
        db_table = 'coa"."account_sub_type'
```

#### 4.3 Create Currency Model
**New File:** `apps/backend/apps/core/models/currency.py`

```python
"""
Currency model for LedgerSG.

Maps to core.currency table (reference data).
"""

from django.db import models


class Currency(models.Model):
    """ISO 4217 currency reference."""
    
    code = models.CharField(max_length=3, primary_key=True, db_column="code")
    name = models.CharField(max_length=100, db_column="name")
    symbol = models.CharField(max_length=5, db_column="symbol")
    decimal_places = models.SmallIntegerField(default=2, db_column="decimal_places")
    is_active = models.BooleanField(default=True, db_column="is_active")
    
    class Meta:
        managed = False
        db_table = 'core"."currency'
```

#### 4.4 Create AuditEventLog Model
**New File:** `apps/backend/apps/core/models/audit_event_log.py`

```python
"""
AuditEventLog model for LedgerSG.

Maps to audit.event_log table.
"""

from django.db import models


class AuditEventLog(models.Model):
    """Immutable audit trail for IRAS compliance."""
    
    id = models.BigAutoField(primary_key=True, db_column="id")
    org = models.ForeignKey(
        "Organisation", on_delete=models.CASCADE,
        db_column="org_id"
    )
    user = models.ForeignKey(
        "AppUser", null=True, blank=True,
        on_delete=models.SET_NULL, db_column="user_id"
    )
    session_id = models.CharField(max_length=64, blank=True, db_column="session_id")
    
    action = models.CharField(max_length=30, db_column="action")
    entity_schema = models.CharField(max_length=30, db_column="entity_schema")
    entity_table = models.CharField(max_length=50, db_column="entity_table")
    entity_id = models.UUIDField(db_column="entity_id")
    
    old_data = models.JSONField(null=True, db_column="old_data")
    new_data = models.JSONField(null=True, db_column="new_data")
    changed_fields = models.JSONField(default=list, db_column="changed_fields")
    
    ip_address = models.GenericIPAddressField(null=True, db_column="ip_address")
    user_agent = models.TextField(blank=True, db_column="user_agent")
    request_path = models.CharField(max_length=500, blank=True, db_column="request_path")
    
    created_at = models.DateTimeField(auto_now_add=True, db_column="created_at")
    
    class Meta:
        managed = False
        db_table = 'audit"."event_log'
```

---

## Validation Checklist

### Pre-Execution Validation
- [ ] Review all SQL table definitions
- [ ] Verify all db_column mappings match SQL
- [ ] Confirm all ENUM values match SQL CHECK constraints
- [ ] Validate Foreign Key on_delete behaviors

### Post-Execution Validation
- [ ] Run `python manage.py check`
- [ ] Test model imports
- [ ] Verify no circular import issues
- [ ] Run pytest to verify no regressions

### Files to be Modified
1. `apps/backend/apps/core/models/invoice_document.py`
2. `apps/backend/apps/core/models/organisation.py`
3. `apps/backend/apps/core/models/contact.py`
4. `apps/backend/apps/core/models/tax_code.py`
5. `apps/backend/apps/core/models/gst_return.py`
6. `apps/backend/apps/core/models/account.py`
7. `apps/backend/apps/core/models/__init__.py`

### Files to be Created
1. `apps/backend/apps/core/models/bank_account.py`
2. `apps/backend/apps/core/models/payment.py`
3. `apps/backend/apps/core/models/payment_allocation.py`
4. `apps/backend/apps/core/models/document_sequence.py`
5. `apps/backend/apps/core/models/account_type.py`
6. `apps/backend/apps/core/models/account_sub_type.py`
7. `apps/backend/apps/core/models/currency.py`
8. `apps/backend/apps/core/models/audit_event_log.py`

---

## Risk Assessment

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| ENUM mismatch causes runtime error | High | Critical | Fix P0 items first |
| Circular import errors | Medium | High | Careful import ordering |
| Missing related_name conflicts | Medium | Medium | Test all relationships |
| Model validation failures | Low | Medium | Run manage.py check |

---

## Success Criteria

1. ✅ All P0 issues resolved
2. ✅ All banking models created
3. ✅ All critical fields added to existing models
4. ✅ No import errors
5. ✅ No CHECK constraint violations on test data
6. ✅ pytest passes (or fails only on unrelated tests)

---

**Plan Status:** READY FOR VALIDATION
