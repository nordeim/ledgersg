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
