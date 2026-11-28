"""
P35/BE-P35-H2: the transmission failure-path truth — the error-join crash.

Pre-P35 (reproduced on the base tree via a live probe):
_execute_transmission reads `schema_errors or schematron_errors or errors`
and does `"; ".join(errors)` — but the REAL validator returns a list of
DICTS ({"message": ..., "line": ..., "column": ...}); joining a list of
dicts raises `TypeError: sequence item 0: expected str instance, dict
found`. The TypeError is swallowed by transmit_invoice's outer `except
Exception`, so a schema-invalid document is recorded as INTERNAL_ERROR
carrying a Python TypeError string instead of VALIDATION_ERROR carrying
the real schema messages. An operator debugging a rejected document sees
the framework's crash, not the document's defect.

Why the suite never saw it: the transmission tests mock the validation
service with STRING lists ("errors": ["Invalid tax category"]) and never
exercise _execute_transmission with a failing REAL-shape result — the
test_transmit_invoice_validation_fails body calls the MOCK directly and
asserts the mock's own return, a test of the mock rather than the
service (the same mocked-seam blind-spot class the P34 lesson names).
"""

from unittest.mock import Mock

import pytest

pytestmark = pytest.mark.django_db


def _schema_invalid_mapped_data() -> dict:
    """A mapped payload whose generated XML fails the XSD: no cbc:ID
    (document_id=None makes _add_element skip the element entirely)."""
    return {
        "ubl_version": "2.1",
        "customization_id": "urn:peppol:pint:billing-1@sg-1",
        "profile_id": "urn:peppol:pint:billing-1@sg-1",
        "document_id": None,  # -> no cbc:ID -> the XSD rejects the document
        "issue_date": "2026-11-28",
        "due_date": "2026-12-28",
        "document_type": "INVOICE",
        "currency": "SGD",
        "tax_currency": "SGD",
        "supplier": {"name": "S", "uen": "202312345A"},
        "customer": {"name": "C"},
        "payment_terms": {},
        "tax_totals": {"tax_categories": [], "total_tax_amount": "0.00"},
        "monetary_totals": {
            "line_extension_amount": "10.00",
            "tax_exclusive_amount": "10.00",
            "tax_inclusive_amount": "10.00",
            "payable_amount": "10.00",
        },
        "lines": [
            {
                "line_id": "1",
                "quantity": "1",
                "unit_code": "EA",
                "line_extension_amount": "10.00",
                "unit_price": "10.00",
            }
        ],
    }


class TestTransmissionFailurePath:
    """The REAL failure path: generation + validation real, only the mapper
    mocked (the input source), and the failure surfaced truthfully."""

    def _service_with_invalid_payload(self):
        from apps.peppol.services.transmission_service import TransmissionService

        service = TransmissionService()
        # Mock ONLY the input source — the generator and the VALIDATION
        # service stay real (the seam under test).
        service.mapping_service = Mock()
        service.mapping_service.map_invoice_to_ubl.return_value = (
            _schema_invalid_mapped_data()
        )
        return service

    def test_schema_invalid_document_gets_validation_error_not_a_crash(self):
        service = self._service_with_invalid_payload()

        invoice = Mock()
        invoice.document_type = "SALES_INVOICE"
        org = Mock()
        log = Mock()
        settings = Mock()

        # RED on the base tree: this raises TypeError
        # ("sequence item 0: expected str instance, dict found") from the
        # "; ".join(dict-list) on the real validator's error shape.
        result = service._execute_transmission(
            invoice=invoice, org=org, log=log, settings=settings
        )

        assert result.success is False
        assert result.error_code == "VALIDATION_ERROR"
        # The message carries the REAL schema error text, not a TypeError
        assert "TypeError" not in result.error_message
        assert "ID" in result.error_message  # the missing-element diagnosis

    def test_valid_document_still_validates_clean(self):
        """The control: a schema-valid payload passes the same seam."""
        from apps.peppol.services.ap_adapter_base import TransmissionResult
        from apps.peppol.services.transmission_service import TransmissionService

        service = TransmissionService()
        service.mapping_service = Mock()
        payload = _schema_invalid_mapped_data()
        payload["document_id"] = "INV-VALID-001"  # restore the ID
        service.mapping_service.map_invoice_to_ubl.return_value = payload
        # The adapter is past the seam under test — mock it so the control
        # observes the VALIDATION gate passing, not the AP configuration.
        mock_adapter = Mock()
        mock_adapter.send_invoice.return_value = TransmissionResult.success(
            message_id="msg-1", raw_response={"status": "delivered"}
        )
        service.get_adapter_for_org = Mock(return_value=mock_adapter)

        invoice = Mock()
        invoice.document_type = "SALES_INVOICE"
        org = Mock()
        org.id = "00000000-0000-0000-0000-000000000000"
        log = Mock()
        settings = Mock()

        result = service._execute_transmission(
            invoice=invoice, org=org, log=log, settings=settings
        )
        # The validation gate passed — the run reaches the AP adapter
        assert result.success is True


class TestErrorMessageFormatter:
    """The shape-tolerant formatter at the join seam."""

    def test_dicts_yield_their_message_values(self):
        from apps.peppol.services.transmission_service import (
            _format_validation_error_messages,
        )

        errors = [
            {"message": "missing ID", "line": 3, "column": 0},
            {"message": "unexpected Bogus", "line": 6, "column": 0},
        ]
        assert (
            _format_validation_error_messages(errors) == "missing ID; unexpected Bogus"
        )

    def test_strings_pass_through(self):
        from apps.peppol.services.transmission_service import (
            _format_validation_error_messages,
        )

        # The legacy mock shape (a list of strings) stays joinable
        assert (
            _format_validation_error_messages(["Invalid tax category"])
            == "Invalid tax category"
        )

    def test_mixed_shapes_tolerated(self):
        from apps.peppol.services.transmission_service import (
            _format_validation_error_messages,
        )

        mixed = [{"message": "dict message"}, "plain string"]
        assert (
            _format_validation_error_messages(mixed)
            == "dict message; plain string"
        )

    def test_empty_list_returns_empty_string(self):
        from apps.peppol.services.transmission_service import (
            _format_validation_error_messages,
        )

        assert _format_validation_error_messages([]) == ""
