"""
Account model for LedgerSG Chart of Accounts.

Maps to coa.account table.
"""

from django.db import models
from common.models import TenantModel


class Account(TenantModel):
    """Chart of Accounts model."""
    
    code = models.CharField(max_length=10, db_column="code")
    name = models.CharField(max_length=150, db_column="name")
    # SQL has both account_type (varchar) and account_type_id (FK) for flexibility
    account_type = models.CharField(max_length=50, db_column="account_type")
    description = models.TextField(blank=True, db_column="description")
    
    # Foreign Keys to reference tables
    account_type_ref = models.ForeignKey(
        "AccountType", null=True, blank=True,
        on_delete=models.SET_NULL, db_column="account_type_id"
    )
    account_sub_type = models.ForeignKey(
        "AccountSubType", null=True, blank=True,
        on_delete=models.SET_NULL, db_column="account_sub_type_id"
    )
    
    # Self-referential for hierarchy
    parent = models.ForeignKey(
        "self", null=True, blank=True,
        on_delete=models.SET_NULL,
        db_column="parent_id"
    )
    
    # Currency & Tax
    currency = models.CharField(max_length=3, default="SGD", db_column="currency")
    tax_code_default = models.CharField(max_length=10, blank=True, db_column="tax_code_default")
    
    # Flags
    is_system = models.BooleanField(default=False, db_column="is_system")
    is_header = models.BooleanField(default=False, db_column="is_header")
    is_active = models.BooleanField(default=True, db_column="is_active")
    is_bank = models.BooleanField(default=False, db_column="is_bank")
    is_control = models.BooleanField(default=False, db_column="is_control")
    
    # Soft delete
    deleted_at = models.DateTimeField(null=True, blank=True, db_column="deleted_at")
    
    class Meta:
        managed = False
        db_table = 'coa"."account'
        unique_together = [["org", "code"]]
