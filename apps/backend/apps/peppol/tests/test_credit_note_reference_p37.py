"""
P37/BE-P37-H1: the credit-note original-invoice reference truth.

The DB layer REQUIRES related_document_id for every credit note
(P14/H-4 — the docstring quotes the IRAS rule "A credit note must show
the number and date of the original tax invoice"); the IRAS e-Tax Guide
on the GST InvoiceNow requirement §11.6 says the business "should
indicate the number and date of the original invoice… when submitting
credit note data to IRAS"; the Peppol PINT credit-note syntax carries
it as cac:BillingReference/cac:InvoiceDocumentReference (cbc:ID 1..1,
cbc:IssueDate 0..1 — the IBG-03 group). But NEITHER presentation layer
emitted it: the mapper built no reference field, the generator emitted
no BillingReference, and the PDF showed no reference block.

RED on the base tree for exactly the right reasons: the .sch carries no
reference rule (a reference-less credit note validates clean), the
mapper emits no billing_reference, the generator emits no
cac:BillingReference, and the PDF renders the raw enum heading with no
original-invoice reference.
"""

import datetime
import uuid
from decimal import Decimal

from lxml import etree

SCHEMATRON_PATH = (
    "/home/z/my-project/ledgersg/apps/backend/apps/peppol/schemas/"
    "PINT-UBL-validation.sch"
)
NS_CN = "urn:oasis:names:specification:ubl:schema:xsd:CreditNote-2"
NS_INVOICE = "urn:oasis:names:specification:ubl:schema:xsd:Invoice-2"
NS_CBC = "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
NS_CAC = "urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2"
NS = {"cn": NS_CN, "ubl": NS_INVOICE, "cbc": NS_CBC, "cac": NS_CAC}


def _mapped_data(doc_type: str = "CREDIT_NOTE", currency: str = "SGD") -> dict:
    """A minimal honest mapped payload (the generator's own contract)."""
    return {
        "ubl_version": "2.1",
        "customization_id": "urn:peppol:pint:billing-1@sg-1",
        "profile_id": "urn:peppol:pint:billing-1@sg-1",
        "document_id": "CN-P37-001",
        "issue_date": "2026-11-28",
        "due_date": "2026-12-28",
        "document_type": doc_type,
        "currency": currency,
        "tax_currency": currency,
        "supplier": {"name": "P37 Supplier Pte Ltd", "uen": "202312345A",
                     "address": {"country": "SG"}},
        "customer": {"name": "P37 Customer Corp", "uen": "202398765B",
                     "address": {"country": "SG"}},
        "payment_terms": {"payment_due_date": "2026-12-28"},
        "tax_totals": {
            "tax_categories": [
                {"category": "S", "rate": 0.09,
                 "taxable_amount": "1000.00", "tax_amount": "90.00"}
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
                "quantity": "10",
                "unit_code": "EA",
                "line_extension_amount": "1000.00",
                "description": "P37 reference service",
                "unit_price": "100.00",
            }
        ],
    }


def _generate_credit_note_xml(mapped: dict) -> str:
    from apps.peppol.services.xml_generator_service import XMLGeneratorService

    return XMLGeneratorService().generate_credit_note_xml(mapped)


def _validate_credit_note(xml_string: str) -> dict:
    from apps.peppol.services.xml_validation_service import XMLValidationService

    return XMLValidationService().validate_credit_note_xml(xml_string)


def _validate_invoice(xml_string: str) -> dict:
    from apps.peppol.services.xml_validation_service import XMLValidationService

    return XMLValidationService().validate_invoice_xml(xml_string)


def _rule_ids(errors: list) -> set:
    ids = set()
    for error in errors:
        message = error.get("message", "") if isinstance(error, dict) else str(error)
        for part in message.split():
            if part.startswith("BR-"):
                ids.add(part.rstrip(":"))
    return ids


class TestSchematronReferencePattern:
    """BR-SG-07: every CreditNote carries the original-invoice reference."""

    def test_sch_declares_the_reference_pattern(self):
        """The artefact carries the PINT-SG-REFERENCE pattern with the
        BR-SG-07 rule ID (RED on the base tree: neither exists)."""
        parser = etree.XMLParser(resolve_entities=False, no_network=True)
        root = etree.parse(SCHEMATRON_PATH, parser).getroot()
        xml = etree.tostring(root, encoding="unicode")
        assert "PINT-SG-REFERENCE" in xml
        assert "BR-SG-07" in xml

    def test_referenceless_credit_note_fails_with_br_sg_07(self):
        """A credit note with NO BillingReference fails validation with
        BR-SG-07 named (RED on the base tree: it passes clean — the gap
        the live probe reproduced on the real demo credit note)."""
        result = _validate_credit_note(_generate_credit_note_xml(_mapped_data()))
        assert result["is_valid"] is False
        assert "BR-SG-07" in _rule_ids(result["schematron_errors"])

    def test_credit_note_with_reference_passes(self):
        """The honest shape — the reference carried — validates clean."""
        mapped = _mapped_data()
        mapped["billing_reference"] = {"id": "INV-ORIG-001",
                                       "issue_date": "2026-11-01"}
        result = _validate_credit_note(_generate_credit_note_xml(mapped))
        assert result["schema_errors"] == []
        assert result["schematron_errors"] == []
        assert result["is_valid"] is True

    def test_invoice_without_reference_still_passes(self):
        """BR-SG-07 is CreditNote-scoped: an Invoice root never carries
        BillingReference and must keep validating clean."""
        mapped = _mapped_data(doc_type="INVOICE")
        mapped["document_id"] = "INV-P37-001"
        result = _validate_invoice(
            __import__("apps.peppol.services.xml_generator_service",
                       fromlist=["XMLGeneratorService"])
            .XMLGeneratorService().generate_invoice_xml(mapped)
        )
        assert result["is_valid"] is True


class TestGeneratorEmission:
    """The generator emits cac:BillingReference in the UBL position."""

    def test_generated_credit_note_carries_billing_reference(self):
        """cac:BillingReference/cac:InvoiceDocumentReference/cbc:ID ==
        the original invoice number (RED on the base tree: the element
        is absent — the mapper key did not exist and the generator
        emitted nothing)."""
        mapped = _mapped_data()
        mapped["billing_reference"] = {"id": "INV-ORIG-001",
                                       "issue_date": "2026-11-01"}
        root = etree.fromstring(_generate_credit_note_xml(mapped).encode("utf-8"))
        ref_id = root.find("cac:BillingReference/cac:InvoiceDocumentReference/cbc:ID", NS)
        assert ref_id is not None, "the BillingReference must be emitted"
        assert ref_id.text == "INV-ORIG-001"

    def test_billing_reference_issue_date_emitted(self):
        """cbc:IssueDate carries the original invoice's issue date (the
        IRAS 'number AND date' requirement — both halves)."""
        mapped = _mapped_data()
        mapped["billing_reference"] = {"id": "INV-ORIG-001",
                                       "issue_date": "2026-11-01"}
        root = etree.fromstring(_generate_credit_note_xml(mapped).encode("utf-8"))
        ref_date = root.find(
            "cac:BillingReference/cac:InvoiceDocumentReference/cbc:IssueDate", NS
        )
        assert ref_date is not None
        assert ref_date.text == "2026-11-01"

    def test_billing_reference_precedes_the_supplier_party(self):
        """The UBL 2.1 element order: BillingReference sits before
        AccountingSupplierParty (after the cbc header block)."""
        mapped = _mapped_data()
        mapped["billing_reference"] = {"id": "INV-ORIG-001",
                                       "issue_date": "2026-11-01"}
        root = etree.fromstring(_generate_credit_note_xml(mapped).encode("utf-8"))
        children = list(root)
        tags = [etree.QName(c).localname for c in children]
        assert "BillingReference" in tags
        assert tags.index("BillingReference") < tags.index("AccountingSupplierParty")

    def test_referenceless_mapped_data_emits_nothing(self):
        """The guarded emission: no billing_reference key, no element
        (byte-stability for hand-built payloads without a reference)."""
        root = etree.fromstring(_generate_credit_note_xml(_mapped_data()).encode("utf-8"))
        assert root.find("cac:BillingReference", NS) is None


class TestMapperTruth:
    """The mapper threads the DB's related_document into the payload."""

    @staticmethod
    def _invoice_mock(document_type="SALES_CREDIT_NOTE",
                      with_reference=True):
        class _Addr:
            def __init__(self, **kw):
                self.__dict__.update(kw)

        class _Contact:
            name = "P37 Customer Corp"
            legal_name = "P37 Customer Corp Pte Ltd"
            uen = "202398765B"
            gst_reg_number = None
            is_gst_registered = False
            address_line_1 = "2 Oak St"
            address_line_2 = None
            city = "Singapore"
            postal_code = "048583"
            country = "SG"
            peppol_id = "0195:1234567890-UEN"

        class _Line:
            def __init__(self, line_number, line_amount, gst_amount,
                         quantity, unit_price, description, tax_code, tax_rate):
                self.line_number = line_number
                self.line_amount = Decimal(line_amount)
                self.gst_amount = Decimal(gst_amount)
                self.quantity = Decimal(quantity)
                self.unit_price = Decimal(unit_price)
                self.description = description
                self.tax_code = tax_code
                self.tax_rate = Decimal(tax_rate)
                self.is_bcrs_deposit = False

        class _TaxCode:
            code = "SR"
            rate = Decimal("0.0900")

        class _Org:
            name = "P37 Supplier Pte Ltd"
            legal_name = "P37 Supplier Pte Ltd"
            uen = "202312345A"
            gst_registered = True
            gst_reg_number = "M90312345A"
            peppol_participant_id = "0195:202312345A-UEN"
            address_line_1 = "1 Main St"
            address_line_2 = None
            city = "Singapore"
            postal_code = "048583"
            country = "SG"
            peppol_id = "0195:202312345A-UEN"

        class _Lines:
            @staticmethod
            def all():
                return [
                    _Line(1, "1000.00", "90.00", "10", "100.00",
                          "P37 service", _TaxCode(), "0.09")
                ]

        class _Original:
            document_number = "INV-ORIG-001"
            issue_date = datetime.date(2026, 11, 1)

        class _Invoice:
            document_number = "CN-P37-001"
            issue_date = datetime.date(2026, 11, 28)
            due_date = datetime.date(2026, 12, 28)
            currency = "SGD"
            total_excl = Decimal("1000.00")
            total_incl = Decimal("1090.00")
            gst_total = Decimal("90.00")
            amount_paid = Decimal("0.00")
            notes = ""
            org = _Org()
            contact = _Contact()
            lines = _Lines()

        # Class bodies cannot read the enclosing function's parameters —
        # the parameterised fields are set on the instance.
        invoice = _Invoice()
        invoice.document_type = document_type
        invoice.related_document_id = (
            uuid.UUID("12345678-1234-5678-1234-567812345678")
            if with_reference else None
        )
        invoice.related_document = _Original() if with_reference else None
        return invoice

    def test_mapper_carries_billing_reference_for_credit_note(self):
        """The mapper emits billing_reference with the original invoice's
        number and issue date (RED on the base tree: the key does not
        exist in the mapped payload)."""
        from apps.peppol.services.xml_mapping_service import XMLMappingService

        mapped = XMLMappingService.map_invoice_to_ubl(
            self._invoice_mock("SALES_CREDIT_NOTE", with_reference=True)
        )
        assert mapped.get("billing_reference") == {
            "id": "INV-ORIG-001",
            "issue_date": "2026-11-01",
        }

    def test_mapper_omits_reference_when_no_related_document(self):
        """An invoice (or a document without the FK) maps without the
        billing_reference key (the guarded omission)."""
        from apps.peppol.services.xml_mapping_service import XMLMappingService

        mapped = XMLMappingService.map_invoice_to_ubl(
            self._invoice_mock("SALES_INVOICE", with_reference=False)
        )
        assert not mapped.get("billing_reference")
