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
