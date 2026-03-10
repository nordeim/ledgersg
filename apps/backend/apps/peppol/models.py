"""
Peppol models for InvoiceNow integration.

Maps to gst schema tables for Peppol transmission tracking.
SQL-First Architecture: managed = False
"""

from django.db import models
from common.models import TenantModel


class PeppolTransmissionLog(TenantModel):
    """
    Peppol transmission log entry.

    Immutable log of InvoiceNow/Peppol transmission attempts.
    Each row = one attempt. Enables retry tracking and audit trail.

    Maps to: gst.peppol_transmission_log
    """

    STATUS_CHOICES = [
        ("PENDING", "Pending"),
        ("TRANSMITTING", "Transmitting"),
        ("DELIVERED", "Delivered"),
        ("FAILED", "Failed"),
        ("REJECTED", "Rejected"),
    ]

    # Document reference (foreign key to invoicing.document)
    document_id = models.UUIDField(
        db_column="document_id",
        help_text="Reference to InvoiceDocument",
    )

    # Transmission status
    attempt_number = models.SmallIntegerField(
        db_column="attempt_number",
        default=1,
        help_text="Attempt number for retry tracking",
    )
    status = models.CharField(
        db_column="status",
        max_length=20,
        choices=STATUS_CHOICES,
        default="PENDING",
        help_text="Current transmission status",
    )

    # Peppol identifiers
    peppol_message_id = models.UUIDField(
        db_column="peppol_message_id",
        null=True,
        blank=True,
        help_text="Peppol message ID from AP",
    )
    access_point_id = models.CharField(
        db_column="access_point_id",
        max_length=100,
        blank=True,
        help_text="Access Point identifier",
    )

    # XML payload tracking
    request_hash = models.CharField(
        db_column="request_hash",
        max_length=64,
        blank=True,
        help_text="SHA-256 hash of XML request",
    )
    xml_payload_hash = models.CharField(
        db_column="xml_payload_hash",
        max_length=64,
        blank=True,
        help_text="SHA-256 hash of complete XML payload",
    )

    # Response tracking
    response_code = models.CharField(
        db_column="response_code",
        max_length=20,
        blank=True,
        help_text="HTTP response code from AP",
    )
    error_code = models.CharField(
        db_column="error_code",
        max_length=50,
        blank=True,
        help_text="Error code from AP or validation",
    )
    error_message = models.TextField(
        db_column="error_message",
        blank=True,
        help_text="Detailed error message",
    )

    # Timestamps
    transmitted_at = models.DateTimeField(
        db_column="transmitted_at",
        auto_now_add=True,
        help_text="When transmission was initiated",
    )
    response_at = models.DateTimeField(
        db_column="response_at",
        null=True,
        blank=True,
        help_text="When response received from AP",
    )

    # Access Point
    access_point_provider = models.CharField(
        db_column="access_point_provider",
        max_length=100,
        blank=True,
        help_text="IMDA-accredited AP provider name",
    )

    # Message Level Response (MLR) Tracking
    mlr_status = models.CharField(
        db_column="mlr_status",
        max_length=50,
        blank=True,
        help_text="MLR status from recipient AP",
    )
    mlr_received_at = models.DateTimeField(
        db_column="mlr_received_at",
        null=True,
        blank=True,
        help_text="When MLR received",
    )

    # IRAS 5th Corner Tracking
    iras_submission_id = models.CharField(
        db_column="iras_submission_id",
        max_length=100,
        blank=True,
        help_text="IRAS submission reference ID",
    )

    class Meta:
        managed = False
        db_table = 'gst"."peppol_transmission_log'
        verbose_name = "Peppol Transmission Log"
        verbose_name_plural = "Peppol Transmission Logs"

    def __str__(self) -> str:
        return f"Transmission {self.id} - {self.status}"


class OrganisationPeppolSettings(TenantModel):
    """
    Peppol/InvoiceNow configuration per organisation.

    One-to-one relationship with Organisation.
    Extends Organisation with Peppol-specific configuration.

    Maps to: gst.organisation_peppol_settings
    """

    # Access Point Configuration
    access_point_provider = models.CharField(
        db_column="access_point_provider",
        max_length=100,
        default="",
        help_text="IMDA-accredited AP provider (e.g., Storecove)",
    )
    access_point_api_url = models.URLField(
        db_column="access_point_api_url",
        blank=True,
        null=True,
        help_text="AP provider API endpoint",
    )
    access_point_api_key = models.CharField(
        db_column="access_point_api_key",
        max_length=255,
        blank=True,
        help_text="AP provider API key (encrypted at app level)",
    )
    access_point_client_id = models.CharField(
        db_column="access_point_client_id",
        max_length=100,
        blank=True,
        help_text="AP provider client ID",
    )

    # Transmission Settings
    auto_transmit = models.BooleanField(
        db_column="auto_transmit",
        default=False,
        help_text="Auto-transmit invoices on approval",
    )
    transmission_retry_attempts = models.SmallIntegerField(
        db_column="transmission_retry_attempts",
        default=3,
        help_text="Number of retry attempts on failure",
    )

    # Status
    is_active = models.BooleanField(
        db_column="is_active",
        default=True,
        help_text="Whether Peppol integration is active",
    )
    configured_at = models.DateTimeField(
        db_column="configured_at",
        auto_now_add=True,
        help_text="When settings were configured",
    )
    last_transmission_at = models.DateTimeField(
        db_column="last_transmission_at",
        null=True,
        blank=True,
        help_text="Last successful transmission timestamp",
    )

    class Meta:
        managed = False
        db_table = 'gst"."organisation_peppol_settings'
        verbose_name = "Organisation Peppol Settings"
        verbose_name_plural = "Organisation Peppol Settings"

    def __str__(self) -> str:
        return f"Peppol Settings for Org {self.org_id}"

    @property
    def is_configured(self) -> bool:
        """Check if Peppol is fully configured."""
        return bool(
            self.is_active
            and self.access_point_provider
            and self.access_point_api_url
            and self.access_point_api_key
        )
