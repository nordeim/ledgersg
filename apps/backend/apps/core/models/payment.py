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
        max_digits=12, decimal_places=6, default=1.000000,
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
