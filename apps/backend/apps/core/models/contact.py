"""
Contact model for LedgerSG.

Maps to invoicing.contact table.
"""

from django.db import models
from common.models import TenantModel


class Contact(TenantModel):
    """Contact model for customers and suppliers."""
    
    # Classification
    CONTACT_TYPES = [
        ("CUSTOMER", "Customer"),
        ("SUPPLIER", "Supplier"),
        ("BOTH", "Both"),
    ]
    contact_type = models.CharField(
        max_length=10, blank=True,
        db_column="contact_type",
        choices=CONTACT_TYPES
    )
    name = models.CharField(max_length=255, db_column="name")
    company_name = models.CharField(
        max_length=255, blank=True,
        db_column="company_name"
    )
    legal_name = models.CharField(max_length=255, blank=True, db_column="legal_name")
    uen = models.CharField(max_length=20, blank=True, db_column="uen")
    gst_reg_number = models.CharField(max_length=20, blank=True, db_column="gst_reg_number")
    is_gst_registered = models.BooleanField(default=False, db_column="is_gst_registered")
    tax_code_default = models.CharField(max_length=10, blank=True, db_column="tax_code_default")
    
    # Flags - CRITICAL FIX: is_customer default should be TRUE (matches SQL)
    is_customer = models.BooleanField(default=True, db_column="is_customer")
    is_supplier = models.BooleanField(default=False, db_column="is_supplier")
    is_active = models.BooleanField(default=True, db_column="is_active")
    
    # Communication
    email = models.EmailField(blank=True, db_column="email")
    phone = models.CharField(max_length=50, blank=True, db_column="phone")
    fax = models.CharField(max_length=30, blank=True, db_column="fax")
    website = models.CharField(max_length=255, blank=True, db_column="website")
    
    # Address
    address_line_1 = models.CharField(max_length=255, blank=True, db_column="address_line_1")
    address_line_2 = models.CharField(max_length=255, blank=True, db_column="address_line_2")
    city = models.CharField(max_length=100, blank=True, db_column="city")
    state_province = models.CharField(max_length=100, blank=True, db_column="state_province")
    postal_code = models.CharField(max_length=20, blank=True, db_column="postal_code")
    country = models.CharField(max_length=2, default="SG", db_column="country")
    
    # Financial
    default_currency = models.CharField(max_length=3, default="SGD", db_column="default_currency")
    payment_terms_days = models.SmallIntegerField(default=30, db_column="payment_terms_days")
    credit_limit = models.DecimalField(
        max_digits=10, decimal_places=4,
        null=True, blank=True,
        db_column="credit_limit"
    )
    receivable_account = models.ForeignKey(
        "Account", null=True, blank=True,
        on_delete=models.SET_NULL,
        db_column="receivable_account_id",
        related_name="contact_receivable"
    )
    payable_account = models.ForeignKey(
        "Account", null=True, blank=True,
        on_delete=models.SET_NULL,
        db_column="payable_account_id",
        related_name="contact_payable"
    )
    
    # InvoiceNow / Peppol
    peppol_id = models.CharField(max_length=64, blank=True, db_column="peppol_id")
    peppol_scheme_id = models.CharField(max_length=10, blank=True, db_column="peppol_scheme_id")
    
    # Other
    notes = models.TextField(blank=True, db_column="notes")
    
    class Meta:
        managed = False
        db_table = 'invoicing"."contact'
