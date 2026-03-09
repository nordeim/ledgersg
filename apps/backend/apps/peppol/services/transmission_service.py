"""
Transmission Service for InvoiceNow/Peppol integration.

Orchestrates the complete transmission workflow:
1. Retrieve invoice and organization settings
2. Generate UBL 2.1 XML from invoice
3. Validate XML against PINT-SG rules
4. Send to Access Point provider
5. Update transmission log
6. Handle retries and errors
"""

from typing import Optional, Dict, Any
from datetime import datetime
from uuid import UUID

from apps.peppol.services.ap_adapter_base import APAdapterBase, TransmissionResult
from apps.peppol.services.xml_mapping_service import XMLMappingService
from apps.peppol.services.xml_generator_service import XMLGeneratorService
from apps.peppol.services.xml_validation_service import XMLValidationService
from apps.peppol.services.ap_storecove_adapter import StorecoveAdapter
from apps.peppol.models import PeppolTransmissionLog, OrganisationPeppolSettings


class TransmissionService:
    """
    Service for orchestrating Peppol invoice transmission.

    Coordinates the complete workflow from invoice retrieval
    through XML generation, validation, and transmission to AP.

    Usage:
        service = TransmissionService()

        # Transmit an invoice
        log = service.transmit_invoice(invoice_id, org_id)

        # Retry a failed transmission
        log = service.retry_transmission(transmission_log_id)

        # Queue for async processing
        task_id = service.queue_for_transmission(invoice_id, org_id)
    """

    def __init__(self):
        """Initialize transmission service with XML services."""
        self.mapping_service: XMLMappingService = XMLMappingService()
        self.generator_service: XMLGeneratorService = XMLGeneratorService()
        self.validation_service: XMLValidationService = XMLValidationService()

    def transmit_invoice(self, invoice_id: str, org_id: str) -> PeppolTransmissionLog:
        """
        Transmit an invoice via Peppol.

        Main method for synchronously transmitting an invoice.
        This method blocks until transmission completes or fails.

        Workflow:
        1. Retrieve invoice and organization
        2. Check Peppol configuration
        3. Create transmission log entry
        4. Generate UBL 2.1 XML
        5. Validate XML
        6. Send to AP
        7. Update log with result

        Args:
            invoice_id: UUID of the invoice to transmit
            org_id: UUID of the organization

        Returns:
            PeppolTransmissionLog: The updated transmission log entry

        Raises:
            ValueError: If organization not configured for Peppol
            ValueError: If invoice not found
        """
        from apps.core.models import InvoiceDocument, Organisation

        # Get invoice and organization
        try:
            invoice = InvoiceDocument.objects.get(id=invoice_id)
        except InvoiceDocument.DoesNotExist:
            raise ValueError(f"Invoice {invoice_id} not found")

        try:
            org = Organisation.objects.get(id=org_id)
        except Organisation.DoesNotExist:
            raise ValueError(f"Organization {org_id} not found")

        # Check Peppol configuration
        settings = OrganisationPeppolSettings.objects.filter(org_id=org_id).first()

        if not settings or not settings.is_configured:
            raise ValueError(
                f"Organization {org_id} is not configured for Peppol transmission. "
                "Please configure access point settings first."
            )

        # Create transmission log
        log = PeppolTransmissionLog.objects.create(
            org_id=org_id,
            document_id=invoice_id,
            status="TRANSMITTING",
            access_point_provider=settings.access_point_provider,
            attempt_number=1,
        )

        try:
            # Execute transmission
            result = self._execute_transmission(
                invoice=invoice, org=org, log=log, settings=settings
            )

            # Update log with result
            self._update_log_with_result(log, result)

            return log

        except Exception as e:
            # Handle unexpected errors
            log.status = "FAILED"
            log.error_code = "INTERNAL_ERROR"
            log.error_message = str(e)
            log.response_at = datetime.now()
            log.save()
            raise

    def _execute_transmission(
        self, invoice, org, log: PeppolTransmissionLog, settings: OrganisationPeppolSettings
    ) -> TransmissionResult:
        """
        Execute the transmission workflow.

        Private method that handles the actual transmission steps:
        - XML generation
        - Validation
        - AP transmission

        Args:
            invoice: InvoiceDocument instance
            org: Organisation instance
            log: PeppolTransmissionLog instance
            settings: OrganisationPeppolSettings instance

        Returns:
            TransmissionResult from AP adapter
        """
        # Step 1: Map invoice to UBL structure
        ubl_data = self.mapping_service.map_invoice_to_ubl(invoice)

        # Step 2: Generate XML
        if invoice.document_type == "SALES_CREDIT_NOTE":
            xml_payload = self.generator_service.generate_credit_note_xml(ubl_data)
        else:
            xml_payload = self.generator_service.generate_invoice_xml(ubl_data)

        # Calculate hash for audit
        xml_hash = self.generator_service.calculate_xml_hash(xml_payload)
        log.xml_payload_hash = xml_hash
        log.save()

        # Step 3: Validate XML
        validation_result = self.validation_service.validate_invoice_xml(xml_payload)

        if not validation_result.get("is_valid", False):
            errors = validation_result.get("errors", ["Unknown validation error"])
            return TransmissionResult.failure(
                error_code="VALIDATION_ERROR",
                error_message="; ".join(errors),
                status=self._get_status_for_error("VALIDATION_ERROR"),
            )

        # Step 4: Get AP adapter
        adapter = self.get_adapter_for_org(org.id, settings)

        # Step 5: Get recipient Peppol ID
        recipient_peppol_id = self._get_recipient_peppol_id(invoice)
        if not recipient_peppol_id:
            return TransmissionResult.failure(
                error_code="MISSING_PEPPOL_ID",
                error_message="Recipient does not have a Peppol ID configured",
                status=self._get_status_for_error("MISSING_PEPPOL_ID"),
            )

        # Step 6: Send to AP
        result = adapter.send_invoice(xml_payload, recipient_peppol_id)

        return result

    def _update_log_with_result(
        self, log: PeppolTransmissionLog, result: TransmissionResult
    ) -> None:
        """
        Update transmission log with transmission result.

        Args:
            log: PeppolTransmissionLog to update
            result: TransmissionResult from AP adapter
        """
        if result.success:
            log.status = "DELIVERED"
            log.peppol_message_id = result.message_id
            log.response_code = "201"
        else:
            log.status = result.status.value
            log.error_code = result.error_code
            log.error_message = result.error_message
            log.response_code = self._get_http_code_for_error(result.error_code)

        log.response_at = datetime.now()
        log.save()

    def get_adapter_for_org(
        self, org_id: str, settings: Optional[OrganisationPeppolSettings] = None
    ) -> APAdapterBase:
        """
        Get appropriate AP adapter for organization.

        Currently supports Storecove. Future adapters can be added here.

        Args:
            org_id: Organization UUID
            settings: Optional pre-fetched settings

        Returns:
            APAdapterBase instance

        Raises:
            ValueError: If no supported AP provider configured
        """
        if settings is None:
            settings = OrganisationPeppolSettings.objects.filter(org_id=org_id).first()

            if not settings:
                raise ValueError(f"Peppol settings not found for organization {org_id}")

        provider = settings.access_point_provider.lower()

        if provider == "storecove":
            return StorecoveAdapter(
                api_key=settings.access_point_api_key,
                client_id=settings.access_point_client_id,
                base_url=settings.access_point_api_url,
            )
        else:
            raise ValueError(
                f"Unsupported AP provider: {settings.access_point_provider}. "
                "Supported providers: Storecove"
            )

    def retry_transmission(self, transmission_log_id: str) -> PeppolTransmissionLog:
        """
        Retry a failed transmission.

        Increments attempt counter and re-transmits the invoice.

        Args:
            transmission_log_id: UUID of the transmission log entry

        Returns:
            PeppolTransmissionLog: Updated transmission log entry

        Raises:
            ValueError: If transmission log not found
            ValueError: If max retries exceeded
        """
        from apps.core.models import InvoiceDocument, Organisation

        # Get existing log
        try:
            log = PeppolTransmissionLog.objects.get(id=transmission_log_id)
        except PeppolTransmissionLog.DoesNotExist:
            raise ValueError(f"Transmission log {transmission_log_id} not found")

        # Check if retryable
        if log.status not in ["FAILED", "REJECTED"]:
            raise ValueError(
                f"Cannot retry transmission with status {log.status}. "
                "Only FAILED or REJECTED transmissions can be retried."
            )

        # Get settings
        settings = OrganisationPeppolSettings.objects.filter(org_id=log.org_id).first()

        if not settings:
            raise ValueError(f"Peppol settings not found for organization {log.org_id}")

        # Check max retries
        if log.attempt_number >= settings.transmission_retry_attempts:
            raise ValueError(
                f"Maximum retry attempts ({settings.transmission_retry_attempts}) exceeded"
            )

        # Get invoice
        try:
            invoice = InvoiceDocument.objects.get(id=log.document_id)
        except InvoiceDocument.DoesNotExist:
            raise ValueError(f"Invoice {log.document_id} not found")

        try:
            org = Organisation.objects.get(id=log.org_id)
        except Organisation.DoesNotExist:
            raise ValueError(f"Organization {log.org_id} not found")

        # Increment attempt counter
        log.attempt_number += 1
        log.status = "TRANSMITTING"
        log.error_code = ""
        log.error_message = ""
        log.save()

        # Re-execute transmission
        try:
            result = self._execute_transmission(invoice, org, log, settings)
            self._update_log_with_result(log, result)
            return log
        except Exception as e:
            log.status = "FAILED"
            log.error_code = "INTERNAL_ERROR"
            log.error_message = str(e)
            log.response_at = datetime.now()
            log.save()
            raise

    def _get_recipient_peppol_id(self, invoice) -> Optional[str]:
        """
        Get recipient Peppol ID from invoice contact.

        Args:
            invoice: InvoiceDocument instance

        Returns:
            Peppol participant ID or None if not configured
        """
        if invoice.contact and invoice.contact.peppol_id:
            return invoice.contact.peppol_id
        return None

    def _get_status_for_error(self, error_code: str) -> Any:
        """
        Map error code to transmission status.

        Args:
            error_code: Error code from transmission

        Returns:
            TransmissionStatus: Status enum value
        """
        from apps.peppol.services.ap_adapter_base import TransmissionStatus

        retryable_errors = ["TIMEOUT", "NETWORK_ERROR", "RATE_LIMITED"]

        if error_code in retryable_errors:
            return TransmissionStatus.FAILED
        else:
            return TransmissionStatus.REJECTED

    def _get_http_code_for_error(self, error_code: Optional[str]) -> str:
        """
        Map error code to HTTP status code.

        Args:
            error_code: Error code from transmission

        Returns:
            HTTP status code as string
        """
        code_map = {
            "AUTH_ERROR": "401",
            "VALIDATION_ERROR": "400",
            "PEPPOL_VALIDATION_ERROR": "422",
            "RATE_LIMITED": "429",
            "TIMEOUT": "504",
            "NETWORK_ERROR": "503",
            "INTERNAL_ERROR": "500",
            "MISSING_PEPPOL_ID": "400",
        }
        return code_map.get(error_code, "500")

    # Methods for testing - allow injection of mock services
    def _get_mapping_service(self) -> XMLMappingService:
        """Get XML mapping service (allows mocking in tests)."""
        return self.mapping_service

    def _get_generator_service(self) -> XMLGeneratorService:
        """Get XML generator service (allows mocking in tests)."""
        return self.generator_service

    def _get_validation_service(self) -> XMLValidationService:
        """Get XML validation service (allows mocking in tests)."""
        return self.validation_service
