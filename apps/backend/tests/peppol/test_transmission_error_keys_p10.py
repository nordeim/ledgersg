"""
P10/M-4: the transmission path reads validation_result["errors"] but the
validator writes schema_errors/schematron_errors — every XSD failure
surfaced as the literal string "Unknown validation error", hiding the
real validation detail (and blunting the P9/S-3 fail-closed message).
"""

from unittest.mock import Mock

from django.test import TestCase


class TestTransmissionErrorKeysP10(TestCase):
    """The failure message must carry the validator's real error keys."""

    def _service_with_failed_validation(self, validation_result: dict):
        from apps.peppol.services.transmission_service import TransmissionService

        service = TransmissionService()
        service.mapping_service = Mock()
        service.mapping_service.map_invoice_to_ubl.return_value = {}
        service.generator_service = Mock()
        service.generator_service.generate_invoice_xml.return_value = "<Invoice/>"
        service.generator_service.calculate_xml_hash.return_value = "hash123"
        service.validation_service = Mock()
        service.validation_service.validate_invoice_xml.return_value = validation_result
        return service

    def test_schema_errors_surface_in_the_failure_message(self):
        """The REAL validator shape: {is_valid, schema_errors, schematron_errors}."""
        service = self._service_with_failed_validation(
            {
                "is_valid": False,
                "schema_errors": ["cvc-enumeration-valid: value 'BAD' is not valid"],
                "schematron_errors": [],
            }
        )

        invoice = Mock()
        invoice.document_type = "SALES_INVOICE"
        org = Mock()
        log = Mock()
        settings = Mock()

        result = service._execute_transmission(invoice, org, log, settings)

        self.assertFalse(result.success)
        self.assertIn(
            "cvc-enumeration-valid", result.error_message,
            "the real XSD detail must reach the operator, not 'Unknown validation error'",
        )
        self.assertNotIn("Unknown validation error", result.error_message)

    def test_schematron_errors_surface_too(self):
        service = self._service_with_failed_validation(
            {
                "is_valid": False,
                "schema_errors": [],
                "schematron_errors": ["BR-CO-10: sum of line net amounts mismatch"],
            }
        )

        invoice = Mock()
        invoice.document_type = "SALES_INVOICE"
        org = Mock()
        log = Mock()
        settings = Mock()

        result = service._execute_transmission(invoice, org, log, settings)

        self.assertFalse(result.success)
        self.assertIn("BR-CO-10", result.error_message)
