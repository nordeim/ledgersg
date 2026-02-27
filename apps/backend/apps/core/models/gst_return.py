"""
GSTReturn model for LedgerSG.

Maps to gst.return table.
"""

from django.db import models
from common.models import TenantModel


class GSTReturn(TenantModel):
    """GST Return (F5/F7/F8) model for IRAS filing."""
    
    RETURN_TYPES = [
        ("F5", "GST F5 (Standard)"),
        ("F7", "GST F7 (Correction)"),
        ("F8", "GST F8 (Final)"),
    ]
    
    STATUS_CHOICES = [
        ("DRAFT", "Draft"),
        ("COMPUTED", "Computed"),
        ("REVIEWED", "Reviewed"),
        ("FILED", "Filed"),
        ("AMENDED", "Amended"),
    ]
    
    return_type = models.CharField(
        max_length=5, choices=RETURN_TYPES, default="F5",
        db_column="return_type"
    )
    period_start = models.DateField(db_column="period_start")
    period_end = models.DateField(db_column="period_end")
    filing_due_date = models.DateField(db_column="filing_due_date")
    
    # F5 Boxes 1-10
    box1_std_rated_supplies = models.DecimalField(
        max_digits=10, decimal_places=4, default=0,
        db_column="box1_std_rated_supplies"
    )
    box2_zero_rated_supplies = models.DecimalField(
        max_digits=10, decimal_places=4, default=0,
        db_column="box2_zero_rated_supplies"
    )
    box3_exempt_supplies = models.DecimalField(
        max_digits=10, decimal_places=4, default=0,
        db_column="box3_exempt_supplies"
    )
    box4_total_supplies = models.DecimalField(
        max_digits=10, decimal_places=4, default=0,
        db_column="box4_total_supplies"
    )
    box5_total_taxable_purchases = models.DecimalField(
        max_digits=10, decimal_places=4, default=0,
        db_column="box5_total_taxable_purchases"
    )
    box6_output_tax = models.DecimalField(
        max_digits=10, decimal_places=4, default=0,
        db_column="box6_output_tax"
    )
    box7_input_tax_claimable = models.DecimalField(
        max_digits=10, decimal_places=4, default=0,
        db_column="box7_input_tax_claimable"
    )
    box8_net_gst = models.DecimalField(
        max_digits=10, decimal_places=4, default=0,
        db_column="box8_net_gst"
    )
    box9_imports_under_schemes = models.DecimalField(
        max_digits=10, decimal_places=4, default=0,
        db_column="box9_imports_under_schemes"
    )
    box10_tourist_refund = models.DecimalField(
        max_digits=10, decimal_places=4, default=0,
        db_column="box10_tourist_refund"
    )
    
    # F5 Boxes 11-15 (Missing in original)
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
    
    # Status & Workflow
    status = models.CharField(
        max_length=20, default="DRAFT",
        db_column="status",
        choices=STATUS_CHOICES
    )
    computed_at = models.DateTimeField(null=True, blank=True, db_column="computed_at")
    reviewed_at = models.DateTimeField(null=True, blank=True, db_column="reviewed_at")
    reviewed_by = models.ForeignKey(
        "AppUser", null=True, blank=True,
        on_delete=models.SET_NULL, db_column="reviewed_by"
    )
    filed_at = models.DateTimeField(null=True, blank=True, db_column="filed_at")
    filed_by = models.ForeignKey(
        "AppUser", null=True, blank=True,
        on_delete=models.SET_NULL, db_column="filed_by",
        related_name="filed_gst_returns"
    )
    # CRITICAL FIX: SQL has iras_confirmation, not filing_reference
    iras_confirmation = models.CharField(
        max_length=50, blank=True, db_column="iras_confirmation"
    )
    notes = models.TextField(blank=True, db_column="notes")
    
    class Meta:
        managed = False
        db_table = 'gst"."return'
