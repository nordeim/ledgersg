"""
Organisation model for LedgerSG.

Represents a tenant (company/business entity).
Maps to core.organisation table.
"""

from django.db import models

from common.models import BaseModel


class Organisation(BaseModel):
    """
    Organisation (tenant) model.
    
    Maps to core.organisation table.
    Each organisation has its own Chart of Accounts, invoices, etc.
    """
    
    # Basic info
    name = models.CharField(
        max_length=255,
        db_column="name",
    )
    legal_name = models.CharField(
        max_length=255,
        blank=True,
        db_column="legal_name",
    )
    
    # Singapore-specific identifiers
    uen = models.CharField(
        max_length=20,
        blank=True,
        db_column="uen",
        verbose_name="UEN (Unique Entity Number)",
    )
    # SQL CHECK constraint values
    ENTITY_TYPES = [
        ("SOLE_PROPRIETORSHIP", "Sole Proprietorship"),
        ("PARTNERSHIP", "Partnership"),
        ("PRIVATE_LIMITED", "Private Limited Company"),
        ("LIMITED_LIABILITY_PARTNERSHIP", "Limited Liability Partnership"),
        ("PUBLIC_LIMITED", "Public Limited Company"),
        ("NON_PROFIT", "Non-Profit Organisation"),
        ("OTHER", "Other"),
    ]
    entity_type = models.CharField(
        max_length=50,
        default="PRIVATE_LIMITED",
        db_column="entity_type",
        choices=ENTITY_TYPES,
    )
    
    # GST registration
    gst_registered = models.BooleanField(
        default=False,
        db_column="gst_registered",
    )
    gst_reg_number = models.CharField(
        max_length=50,
        blank=True,
        db_column="gst_reg_number",
    )
    gst_reg_date = models.DateField(
        null=True,
        blank=True,
        db_column="gst_reg_date",
    )
    # CRITICAL FIX: Match SQL CHECK constraint values (both cases accepted)
    GST_SCHEMES = [
        ("STANDARD", "Standard GST"),
        ("standard", "Standard GST (legacy)"),
        ("CASH", "Cash Accounting"),
        ("cash", "Cash Accounting (legacy)"),
        ("MARGIN", "Margin Scheme"),
        ("margin", "Margin Scheme (legacy)"),
    ]
    gst_scheme = models.CharField(
        max_length=30,
        default="STANDARD",
        db_column="gst_scheme",
        choices=GST_SCHEMES,
    )
    # CRITICAL FIX: Match SQL CHECK constraint values (both cases accepted)
    GST_FILING_FREQUENCIES = [
        ("MONTHLY", "Monthly"),
        ("monthly", "Monthly (legacy)"),
        ("QUARTERLY", "Quarterly"),
        ("quarterly", "Quarterly (legacy)"),
        ("SEMI_ANNUAL", "Semi-Annual"),
        ("semi_annual", "Semi-Annual (legacy)"),
    ]
    gst_filing_frequency = models.CharField(
        max_length=15,
        default="QUARTERLY",
        db_column="gst_filing_frequency",
        choices=GST_FILING_FREQUENCIES,
    )
    
    # InvoiceNow / Peppol
    peppol_participant_id = models.CharField(
        max_length=64,
        blank=True,
        db_column="peppol_participant_id",
    )
    peppol_scheme_id = models.CharField(
        max_length=10,
        default="0195",
        blank=True,
        db_column="peppol_scheme_id",
    )
    invoicenow_enabled = models.BooleanField(
        default=False,
        db_column="invoicenow_enabled",
    )
    invoicenow_ap_id = models.CharField(
        max_length=100,
        blank=True,
        db_column="invoicenow_ap_id",
    )
    
    # Fiscal settings
    fy_start_month = models.SmallIntegerField(
        default=1,
        db_column="fy_start_month",
        help_text="Month when fiscal year starts (1-12)",
    )
    base_currency = models.CharField(
        max_length=3,
        default="SGD",
        db_column="base_currency",
    )
    timezone = models.CharField(
        max_length=50,
        default="Asia/Singapore",
        db_column="timezone",
    )
    date_format = models.CharField(
        max_length=20,
        default="DD/MM/YYYY",
        db_column="date_format",
    )
    
    # Address
    address_line_1 = models.CharField(
        max_length=255,
        blank=True,
        db_column="address_line_1",
    )
    address_line_2 = models.CharField(
        max_length=255,
        blank=True,
        db_column="address_line_2",
    )
    city = models.CharField(
        max_length=100,
        blank=True,
        db_column="city",
    )
    state = models.CharField(
        max_length=100,
        blank=True,
        db_column="state",
    )
    postal_code = models.CharField(
        max_length=20,
        blank=True,
        db_column="postal_code",
    )
    country = models.CharField(
        max_length=2,
        default="SG",
        db_column="country",
    )
    
    # Contact
    phone = models.CharField(
        max_length=30,
        blank=True,
        db_column="phone",
    )
    email = models.EmailField(
        blank=True,
        db_column="email",
    )
    contact_email = models.EmailField(
        blank=True,
        db_column="contact_email",
    )
    contact_phone = models.CharField(
        max_length=50,
        blank=True,
        db_column="contact_phone",
    )
    website = models.CharField(
        max_length=255,
        blank=True,
        db_column="website",
    )
    logo_url = models.CharField(
        max_length=500,
        blank=True,
        db_column="logo_url",
    )
    
    # Status
    is_active = models.BooleanField(
        default=True,
        db_column="is_active",
    )
    
    # Soft delete
    deleted_at = models.DateTimeField(
        null=True,
        blank=True,
        db_column="deleted_at",
    )
    # CRITICAL FIX: Changed from UUIDField to ForeignKey
    deleted_by = models.ForeignKey(
        "AppUser",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        db_column="deleted_by",
        related_name="deleted_organisations",
    )
    
    class Meta:
        managed = False
        db_table = 'core"."organisation'
        verbose_name = "organisation"
        verbose_name_plural = "organisations"
    
    def __str__(self) -> str:
        return self.name
    
    @property
    def is_gst_registered(self) -> bool:
        """Check if org is GST registered with valid registration."""
        return self.gst_registered and bool(self.gst_reg_number)
    
    @property
    def current_fiscal_year(self):
        """Get the current open fiscal year."""
        from .fiscal_year import FiscalYear
        return FiscalYear.objects.filter(
            org=self,
            is_closed=False,
        ).order_by("start_date").first()
    
    @property
    def gst_filing_periods_per_year(self) -> int:
        """Return number of GST filing periods per year."""
        mapping = {
            "MONTHLY": 12,
            "monthly": 12,
            "QUARTERLY": 4,
            "quarterly": 4,
            "SEMI_ANNUAL": 2,
            "semi_annual": 2,
        }
        return mapping.get(self.gst_filing_frequency, 4)
