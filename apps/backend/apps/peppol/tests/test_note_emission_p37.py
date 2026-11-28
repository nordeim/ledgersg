"""
P37/BE-P37-L1: the cbc:Note emission gap (the BR-111-GST-SG reason note).

The Peppol PINT-SG rule BR-111-GST-SG (warning class) expects a credit
note carrying a taxable GST category to have an invoice note giving the
reason for credit. The repo's mapper dropped the document's `notes`
field entirely and the generator emitted no cbc:Note on either path
(the PDF already rendered document.notes when present — the XML surface
was the gap).

RED on the base tree for exactly the right reasons: the mapper carries
no `note` key and the generated XML carries no cbc:Note element on
either document path.
"""

from decimal import Decimal

from lxml import etree

NS_INVOICE = "urn:oasis:names:specification:ubl:schema:xsd:Invoice-2"
NS_CN = "urn:oasis:names:specification:ubl:schema:xsd:CreditNote-2"
NS_CBC = "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
NS = {"ubl": NS_INVOICE, "cn": NS_CN, "cbc": NS_CBC}

NOTE_TEXT = "Reason for credit: 2 units damaged in transit (50% credit)"


def _mapped_data(doc_type: str = "INVOICE") -> dict:
    """A minimal honest mapped payload (the generator's own contract).

    P37: a CREDIT_NOTE payload carries the original-invoice reference
    (the honest mapper shape — BR-SG-07 pins its presence).
    """
    data = {
        "ubl_version": "2.1",
        "customization_id": "urn:peppol:pint:billing-1@sg-1",
        "profile_id": "urn:peppol:pint:billing-1@sg-1",
        "document_id": "DOC-P37-N01",
        "issue_date": "2026-11-28",
        "due_date": "2026-12-28",
        "document_type": doc_type,
        "currency": "SGD",
        "tax_currency": "SGD",
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
                "description": "P37 note service",
                "unit_price": "100.00",
            }
        ],
    }
    if doc_type == "CREDIT_NOTE":
        data["billing_reference"] = {"id": "INV-P37-N01",
                                     "issue_date": "2026-11-01"}
    return data


def _generate(doc_type: str, mapped: dict) -> str:
    from apps.peppol.services.xml_generator_service import XMLGeneratorService

    service = XMLGeneratorService()
    if doc_type == "CREDIT_NOTE":
        return service.generate_credit_note_xml(mapped)
    return service.generate_invoice_xml(mapped)


def _validate(doc_type: str, xml_string: str) -> dict:
    from apps.peppol.services.xml_validation_service import XMLValidationService

    service = XMLValidationService()
    if doc_type == "CREDIT_NOTE":
        return service.validate_credit_note_xml(xml_string)
    return service.validate_invoice_xml(xml_string)


class TestNoteEmission:
    """cbc:Note carries the document's notes on both paths."""

    def test_mapper_carries_the_note(self):
        """The mapper threads invoice.notes into the payload's note key
        (RED on the base tree: the key does not exist)."""
        import datetime

        from apps.peppol.services.xml_mapping_service import XMLMappingService

        class _Addr:
            def __init__(self, **kw):
                self.__dict__.update(kw)

        class _Contact:
            name = "Note Customer Corp"
            legal_name = "Note Customer Corp Pte Ltd"
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
            name = "Note Supplier Pte Ltd"
            legal_name = "Note Supplier Pte Ltd"
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
                          "note service", _TaxCode(), "0.09")
                ]

        class _Invoice:
            document_number = "INV-P37-N01"
            document_type = "SALES_INVOICE"
            issue_date = datetime.date(2026, 11, 28)
            due_date = datetime.date(2026, 12, 28)
            currency = "SGD"
            total_excl = Decimal("1000.00")
            total_incl = Decimal("1090.00")
            gst_total = Decimal("90.00")
            amount_paid = Decimal("0.00")
            notes = NOTE_TEXT
            org = _Org()
            contact = _Contact()
            lines = _Lines()
            related_document_id = None
            related_document = None

        mapped = XMLMappingService.map_invoice_to_ubl(_Invoice())
        assert mapped.get("note") == NOTE_TEXT

    def test_invoice_path_emits_the_note(self):
        """The generated invoice XML carries cbc:Note with the exact
        text (RED on the base tree: the element is absent)."""
        mapped = _mapped_data("INVOICE")
        mapped["note"] = NOTE_TEXT
        root = etree.fromstring(_generate("INVOICE", mapped).encode("utf-8"))
        note = root.find("cbc:Note", NS)
        assert note is not None, "cbc:Note must be emitted when notes is set"
        assert note.text == NOTE_TEXT

    def test_credit_note_path_emits_the_note(self):
        """The same on the credit-note path (the BR-111-GST-SG surface)."""
        mapped = _mapped_data("CREDIT_NOTE")
        mapped["note"] = NOTE_TEXT
        root = etree.fromstring(_generate("CREDIT_NOTE", mapped).encode("utf-8"))
        note = root.find("cbc:Note", NS)
        assert note is not None, "cbc:Note must be emitted when notes is set"
        assert note.text == NOTE_TEXT

    def test_no_note_when_notes_empty(self):
        """The guarded omission: no note key, no element — every
        notes-empty document keeps its exact bytes (the demo substrate
        documents carry notes='')."""
        mapped = _mapped_data("CREDIT_NOTE")
        assert "note" not in mapped
        root = etree.fromstring(_generate("CREDIT_NOTE", mapped).encode("utf-8"))
        assert root.find("cbc:Note", NS) is None

    def test_validation_accepts_the_note_on_both_roots(self):
        """The full validation path stays green with the Note element
        present (the XSD declarations)."""
        for doc_type in ("INVOICE", "CREDIT_NOTE"):
            mapped = _mapped_data(doc_type)
            mapped["note"] = NOTE_TEXT
            result = _validate(doc_type, _generate(doc_type, mapped))
            assert result["schema_errors"] == [], (
                f"{doc_type}: {result['schema_errors']}"
            )
            assert result["is_valid"] is True, (
                f"{doc_type}: {result['schematron_errors']}"
            )

    def test_note_text_round_trips_exactly(self):
        """Special characters survive the emission verbatim (no escaping
        artefacts, no truncation)."""
        tricky = "Return & refund — 2 items <damaged> 50%"
        mapped = _mapped_data("CREDIT_NOTE")
        mapped["note"] = tricky
        root = etree.fromstring(_generate("CREDIT_NOTE", mapped).encode("utf-8"))
        note = root.find("cbc:Note", NS)
        assert note is not None
        assert note.text == tricky
