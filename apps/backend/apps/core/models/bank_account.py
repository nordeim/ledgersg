"""
BankAccount model for LedgerSG.

Maps to banking.bank_account table.
"""

from django.db import models
from common.models import TenantModel


class BankAccount(TenantModel):
    """Bank account model for reconciliation."""
    
    PAYNOW_TYPES = [
        ("UEN", "UEN"),
        ("MOBILE", "Mobile"),
        ("NRIC", "NRIC"),
    ]
    
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
        choices=PAYNOW_TYPES
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
