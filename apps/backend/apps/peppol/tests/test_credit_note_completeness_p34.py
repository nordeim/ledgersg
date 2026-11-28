"""
P34/BE-P34-H1: the credit-note Peppol truth — completeness + wiring + XSD.

Pre-P34 (all three reproduced on the base tree via a live probe):
(a) generate_credit_note_xml emitted header-only UBL — the mapper's
    supplier/customer/payment_terms/tax_totals/monetary_totals/lines were
    all DISCARDED, so a transmitted credit note carried no parties, no
    amounts and no lines.
(b) transmission_service._execute_transmission validated the CreditNote
    root against the INVOICE XSD (validate_invoice_xml) — a CreditNote
    document can never pass it ("No matching global declaration available
    for the validation root"), so the SALES_CREDIT_NOTE InvoiceNow path
    was structurally doomed to FAILED before reaching the access point.
(c) ubl-CreditNote.xsd declared targetNamespace="...Invoice-2" (a
    copy-paste artefact of its Invoice sibling) while the generator
    correctly emits the true UBL 2.1 CreditNote-2 namespace — even the
    DEDICATED validate_credit_note_xml rejected every generated document.

Why the suite never saw it: the generator test only asserted the method
EXISTS, the validation test deliberately did not assert is_valid, and the
transmission tests MOCK the validation service — three blind spots
stacked on the one path (the P34 lesson).
"""

import pytest

pytestmark = pytest.mark.django_db

NS_CBC = "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
NS_CAC = "urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2"
NS_CN = "urn:oasis:names:specification:ubl:schema:xsd:CreditNote-2"


def _usd_credit_note_mapped_data() -> dict:
    """A minimal valid credit-note payload denominated in USD (the mapper's own shape)."""
    return {
        "ubl_version": "2.1",
        "customization_id": "urn:peppol:pint:billing-1@sg-1",
        "profile_id": "urn:peppol:pint:billing-1@sg-1",
        "document_id": "CN-USD-001",
        "issue_date": "2026-11-28",
        "due_date": "2026-12-28",
        "document_type": "CREDIT_NOTE",
        "currency": "USD",
        "tax_currency": "SGD",
        "supplier": {
            "name": "USD Supplier Pte Ltd",
            "uen": "202312345A",
            "address": {"street": "1 Main St", "city": "Singapore", "country": "SG"},
        },
        "customer": {
            "name": "USD Customer Corp",
            "uen": "202398765B",
            "address": {"street": "2 Oak St", "city": "Singapore", "country": "SG"},
        },
        "payment_terms": {"payment_due_date": "2026-12-28"},
        "tax_totals": {
            "tax_categories": [
                {
                    "category": "S",
                    "rate": 0.09,
                    "taxable_amount": "1000.00",
                    "tax_amount": "90.00",
                }
            ],
            "total_tax_amount": "90.00",
        },
        "monetary_totals": {
            "line_extension_amount": "1000.00",
            "tax_exclusive_amount": "1000.00",
            "tax_inclusive_amount": "1090.00",
            "payable_amount": "1090.00",
            "prepaid_amount": "0.00",
        },
        "lines": [
            {
                "line_id": "1",
                "description": "USD-denominated service credited",
                "quantity": "10",
                "unit_code": "EA",
                "unit_price": "100.00",
                "line_extension_amount": "1000.00",
            }
        ],
    }


def _generate(data=None):
    from apps.peppol.services.xml_generator_service import XMLGeneratorService

    return XMLGeneratorService().generate_credit_note_xml(
        data or _usd_credit_note_mapped_data()
    )


def _parse(xml_string):
    from lxml import etree

    return etree.fromstring(xml_string.encode("utf-8"))


class TestCreditNoteCompleteness:
    """The generated credit note must carry the full PINT-SG structure."""

    def test_parties_are_present(self):
        root = _parse(_generate())
        ns = {"cac": NS_CAC, "cbc": NS_CBC}

        supplier = root.find("cac:AccountingSupplierParty", ns)
        assert supplier is not None, "AccountingSupplierParty missing — the mapper sends it"
        customer = root.find("cac:AccountingCustomerParty", ns)
        assert customer is not None, "AccountingCustomerParty missing — the mapper sends it"

    def test_tax_total_carries_document_currency(self):
        root = _parse(_generate())
        ns = {"cac": NS_CAC, "cbc": NS_CBC}

        tax_amount = root.find("cac:TaxTotal/cbc:TaxAmount", ns)
        assert tax_amount is not None, "TaxTotal/TaxAmount missing"
        assert tax_amount.get("currencyID") == "USD", (
            f"TaxAmount currencyID={tax_amount.get('currencyID')!r} — "
            "the credit note is USD-denominated"
        )
        taxable = root.find("cac:TaxTotal/cac:TaxSubtotal/cbc:TaxableAmount", ns)
        assert taxable is not None and taxable.get("currencyID") == "USD"

    def test_monetary_totals_carry_document_currency(self):
        root = _parse(_generate())
        ns = {"cac": NS_CAC, "cbc": NS_CBC}

        for tag in ("LineExtensionAmount", "TaxExclusiveAmount",
                    "TaxInclusiveAmount", "PayableAmount"):
            el = root.find(f"cac:LegalMonetaryTotal/cbc:{tag}", ns)
            assert el is not None, f"LegalMonetaryTotal/{tag} missing"
            assert el.get("currencyID") == "USD", (
                f"{tag} currencyID={el.get('currencyID')!r} — the credit note is USD-denominated"
            )

    def test_credit_note_line_shape(self):
        """The line must be the UBL 2.1 CreditNoteLine with CreditedQuantity."""
        root = _parse(_generate())
        ns = {"cac": NS_CAC, "cbc": NS_CBC}

        line = root.find("cac:CreditNoteLine", ns)
        assert line is not None, (
            "cac:CreditNoteLine missing — the true UBL 2.1 credit-note line "
            "(a bare InvoiceLine is not a credit-note line)"
        )
        quantity = line.find("cbc:CreditedQuantity", ns)
        assert quantity is not None, "CreditNoteLine/CreditedQuantity missing"
        assert quantity.get("unitCode") == "EA"
        line_ext = line.find("cbc:LineExtensionAmount", ns)
        assert line_ext is not None and line_ext.get("currencyID") == "USD"
        price = line.find("cac:Price/cbc:PriceAmount", ns)
        assert price is not None and price.get("currencyID") == "USD"

    def test_every_currency_id_claims_the_document_currency(self):
        """The sweep gate: the document carries amounts, and they all claim USD."""
        root = _parse(_generate())

        currency_ids = {el.get("currencyID") for el in root.iter() if el.get("currencyID")}
        assert currency_ids == {"USD"}, (
            f"a USD credit note must carry only USD currencyIDs: {currency_ids}"
        )

    def test_sgd_credit_note_control(self):
        """The SGD default path carries currencyID=SGD everywhere it carries amounts."""
        data = _usd_credit_note_mapped_data()
        data["currency"] = "SGD"
        root = _parse(_generate(data))

        currency_ids = {el.get("currencyID") for el in root.iter() if el.get("currencyID")}
        assert currency_ids == {"SGD"}, (
            f"SGD credit note must carry only SGD currencyIDs: {currency_ids}"
        )


class TestCreditNoteValidationTruth:
    """The dedicated validator must accept what the generator emits."""

    def test_dedicated_validator_accepts_generated_credit_note(self):
        from apps.peppol.services.xml_validation_service import XMLValidationService

        result = XMLValidationService().validate_credit_note_xml(_generate())

        assert result["document_type"] == "CREDIT_NOTE"
        assert result["is_valid"] is True, (
            f"the CreditNote XSD must accept the generator's own output — "
            f"schema_errors: {result['schema_errors']}"
        )

    def test_validator_rejects_invoice_line_inside_credit_note(self):
        """The true-UBL pin: an InvoiceLine inside a CreditNote must NOT validate."""
        from apps.peppol.services.xml_validation_service import XMLValidationService

        wrong_line_xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<CreditNote xmlns="{NS_CN}"
            xmlns:cac="{NS_CAC}"
            xmlns:cbc="{NS_CBC}">
  <cbc:UBLVersionID>2.1</cbc:UBLVersionID>
  <cbc:CustomizationID>urn:peppol:pint:billing-1@sg-1</cbc:CustomizationID>
  <cbc:ProfileID>urn:peppol:pint:billing-1@sg-1</cbc:ProfileID>
  <cbc:ID>CN-WRONG-LINE</cbc:ID>
  <cbc:IssueDate>2026-11-28</cbc:IssueDate>
  <cbc:CreditNoteTypeCode>381</cbc:CreditNoteTypeCode>
  <cbc:DocumentCurrencyCode>SGD</cbc:DocumentCurrencyCode>
  <cac:AccountingSupplierParty><cac:Party><cac:PartyName><cbc:Name>S</cbc:Name></cac:PartyName></cac:Party></cac:AccountingSupplierParty>
  <cac:AccountingCustomerParty><cac:Party><cac:PartyName><cbc:Name>C</cbc:Name></cac:PartyName></cac:Party></cac:AccountingCustomerParty>
  <cac:TaxTotal><cbc:TaxAmount currencyID="SGD">0.00</cbc:TaxAmount></cac:TaxTotal>
  <cac:LegalMonetaryTotal>
    <cbc:LineExtensionAmount currencyID="SGD">0.00</cbc:LineExtensionAmount>
    <cbc:TaxExclusiveAmount currencyID="SGD">0.00</cbc:TaxExclusiveAmount>
    <cbc:TaxInclusiveAmount currencyID="SGD">0.00</cbc:TaxInclusiveAmount>
    <cbc:PayableAmount currencyID="SGD">0.00</cbc:PayableAmount>
  </cac:LegalMonetaryTotal>
  <cac:InvoiceLine>
    <cbc:ID>1</cbc:ID>
    <cbc:LineExtensionAmount currencyID="SGD">0.00</cbc:LineExtensionAmount>
    <cac:Item/>
    <cac:Price><cbc:PriceAmount currencyID="SGD">0.00</cbc:PriceAmount></cac:Price>
  </cac:InvoiceLine>
</CreditNote>"""

        result = XMLValidationService().validate_credit_note_xml(wrong_line_xml)

        assert result["is_valid"] is False, (
            "the CreditNote XSD must reject cac:InvoiceLine — the true UBL 2.1 "
            "credit-note line is cac:CreditNoteLine"
        )


class TestInvoiceValidationTruth:
    """The invoice-side pin of the same P34 XSD restructure.

    Discovered mid-sprint (the TDD RED gate caught it): the pre-P34
    Invoice XSD could not validate the generator's own output either —
    the header children were declared as LOCAL elements in the Invoice-2
    namespace while the generator (correctly) emits them in the cbc
    namespace, and the amount attributes (currencyID/unitCode/schemeID)
    were never declared at all. The validation layer was decorative for
    BOTH paths; the transmission service would have marked every
    transmission FAILED before reaching the access point.
    """

    def test_invoice_validator_accepts_generated_invoice(self):
        from apps.peppol.services.xml_generator_service import XMLGeneratorService
        from apps.peppol.services.xml_validation_service import XMLValidationService

        data = _usd_credit_note_mapped_data()
        data["document_id"] = "INV-USD-001"
        data["document_type"] = "INVOICE"
        xml_string = XMLGeneratorService().generate_invoice_xml(data)

        result = XMLValidationService().validate_invoice_xml(xml_string)

        assert result["document_type"] == "INVOICE"
        assert result["is_valid"] is True, (
            f"the Invoice XSD must accept the generator's own output — "
            f"schema_errors: {result['schema_errors']}"
        )


class TestTransmissionValidatorDispatch:
    """The transmission seam must validate by document type (as it already generates)."""

    def _service_with_mocks(self, document_type: str):
        from unittest.mock import Mock

        from apps.peppol.services.ap_adapter_base import TransmissionResult
        from apps.peppol.services.transmission_service import TransmissionService

        service = TransmissionService()
        service.mapping_service = Mock()
        service.mapping_service.map_invoice_to_ubl.return_value = {"currency": "SGD"}

        service.generator_service = Mock()
        service.generator_service.generate_credit_note_xml.return_value = "<CreditNote/>"
        service.generator_service.generate_invoice_xml.return_value = "<Invoice/>"
        service.generator_service.calculate_xml_hash.return_value = "hash"

        service.validation_service = Mock()
        service.validation_service.validate_credit_note_xml.return_value = {
            "is_valid": True, "schema_errors": [],
        }
        service.validation_service.validate_invoice_xml.return_value = {
            "is_valid": True, "schema_errors": [],
        }

        adapter = Mock()
        adapter.send_invoice.return_value = TransmissionResult.success(
            message_id="msg-1", raw_response={"status": "accepted"}
        )
        service.get_adapter_for_org = Mock(return_value=adapter)
        service._get_recipient_peppol_id = Mock(return_value="0195:202312345A")

        invoice = Mock()
        invoice.document_type = document_type
        org = Mock()
        org.id = "00000000-0000-0000-0000-000000000000"
        log = Mock()
        settings = Mock()
        return service, invoice, org, log, settings

    def test_credit_note_transmission_validates_with_credit_note_schema(self):
        service, invoice, org, log, settings = self._service_with_mocks(
            "SALES_CREDIT_NOTE"
        )

        service._execute_transmission(
            invoice=invoice, org=org, log=log, settings=settings
        )

        service.validation_service.validate_credit_note_xml.assert_called_once()
        service.validation_service.validate_invoice_xml.assert_not_called()

    def test_invoice_transmission_still_validates_with_invoice_schema(self):
        """The control: the invoice path keeps its validator."""
        service, invoice, org, log, settings = self._service_with_mocks(
            "SALES_INVOICE"
        )

        service._execute_transmission(
            invoice=invoice, org=org, log=log, settings=settings
        )

        service.validation_service.validate_invoice_xml.assert_called_once()
        service.validation_service.validate_credit_note_xml.assert_not_called()
