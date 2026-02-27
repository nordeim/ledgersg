"""
TaxCode model for LedgerSG.

Maps to gst.tax_code table.
"""

from django.db import models
from decimal import Decimal
from common.models import TenantModel


class TaxCode(TenantModel):
    """Tax code model for GST calculation."""
    
    code = models.CharField(max_length=10, db_column="code")
    # SQL schema has both 'name' and 'description' fields
    name = models.CharField(max_length=150, blank=True, db_column="name")
    description = models.CharField(max_length=150, blank=True, db_column="description")
    rate = models.DecimalField(
        max_digits=5, decimal_places=4,
        null=True, blank=True,
        db_column="rate"
    )
    # SQL schema includes is_gst_charged
    is_gst_charged = models.BooleanField(default=True, db_column="is_gst_charged")
    is_input = models.BooleanField(default=False, db_column="is_input")
    is_output = models.BooleanField(default=False, db_column="is_output")
    is_claimable = models.BooleanField(default=True, db_column="is_claimable")
    is_reverse_charge = models.BooleanField(default=False, db_column="is_reverse_charge")
    # F5 box mappings
    f5_supply_box = models.SmallIntegerField(null=True, blank=True, db_column="f5_supply_box")
    f5_purchase_box = models.SmallIntegerField(null=True, blank=True, db_column="f5_purchase_box")
    f5_tax_box = models.SmallIntegerField(null=True, blank=True, db_column="f5_tax_box")
    display_order = models.SmallIntegerField(default=0, db_column="display_order")
    is_active = models.BooleanField(default=True, db_column="is_active")
    effective_from = models.DateField(null=True, db_column="effective_from")
    effective_to = models.DateField(null=True, blank=True, db_column="effective_to")
    deleted_at = models.DateTimeField(null=True, blank=True, db_column="deleted_at")
    
    class Meta:
        managed = False
        db_table = 'gst"."tax_code'
        # Include effective_from in unique constraint to allow rate history
        unique_together = [["org", "code", "effective_from"]]
