"""
P36/BE-P36-H2 + P36/BE-P36-L1: the tax-currency truth + the Percent truth.

Pre-P36: the mapper hardcodes "tax_currency": "SGD" (xml_mapping_service),
so a USD document emits TaxCurrencyCode=SGD beside DocumentCurrencyCode=USD
and currencyID="USD" amounts — internally inconsistent UBL, the exact P33
hazard class that P33 fixed for the amounts but missed for the tax currency
(the P33 USD fixture itself carried "SGD", the default-value-fixture blind
spot). And the generator formats the tax-category Percent through a float:
str(float(0.07) * 100) = "7.000000000000001" — a float artifact in a
financial document's stated tax rate (the 7% rate rows are live in the DB).
"""

import pytest
from lxml import etree

pytestmark = pytest.mark.django_db

NS_CBC = "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
NS_CAC = "urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2"


def _mapped_data(document_type: str = "INVOICE", currency: str = "USD") -> dict:
    """A minimal valid payload (the mapper's own shape) in the given currency."""
    return {
        "ubl_version": "2.1",
        "customization_id": "urn:peppol:pint:billing-1@sg-1",
        "profile_id": "urn:peppol:pint:billing-1@sg-1",
        "document_id": "INV-P36-H2",
        "issue_date": "2026-11-28",
        "due_date": "2026-12-28",
        "document_type": document_type,
        "currency": currency,
        "supplier": {
            "name": "P36 Supplier Pte Ltd",
            "uen": "202312345A",
            "address": {"street": "1 Main St", "city": "Singapore", "country": "SG"},
        },
        "customer": {
            "name": "P36 Customer Corp",
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
                "description": "P36 tax-currency service",
                "quantity": "10",
                "unit_code": "EA",
                "unit_price": "100.00",
                "line_extension_amount": "1000.00",
                "tax_amount": "90.00",
                "tax_rate": "0.09",
                "tax_category": "S",
            }
        ],
    }


class TestTaxCurrencyTruth:
    """The tax currency no longer contradicts the document currency."""

    def test_mapper_carries_the_document_currency(self):
        """RED on the base tree: the mapper hardcodes "SGD"."""
        from apps.peppol.services.xml_mapping_service import XMLMappingService

        mapped = XMLMappingService.map_invoice_to_ubl(_usd_invoice())
        assert mapped["tax_currency"] == "USD", (
            "the tax is computed in the document currency — the mapper must "
            "carry it, never a hardcoded SGD (the P33 hazard class)"
        )

    def test_usd_document_omits_tax_currency_code(self):
        """The element exists to declare a DIFFERENT tax currency; the tax is
        in the document currency, so it must be omitted (the UBL semantic).
        RED on the base tree: TaxCurrencyCode=SGD is emitted on a USD doc."""
        from apps.peppol.services.xml_generator_service import XMLGeneratorService

        xml = XMLGeneratorService().generate_invoice_xml(_mapped_data("INVOICE", "USD"))
        root = etree.fromstring(xml.encode("utf-8"))
        tcc = root.find("cbc:TaxCurrencyCode", {"cbc": NS_CBC})
        assert tcc is None, (
            f"TaxCurrencyCode={tcc.text if tcc is not None else None!r} on a USD "
            "document whose tax is USD-denominated — the element only exists "
            "to declare a DIFFERENT tax currency"
        )

    def test_sgd_document_omits_tax_currency_code(self):
        """The redundancy is retired on the SGD path too (equal → omitted)."""
        from apps.peppol.services.xml_generator_service import XMLGeneratorService

        mapped = _mapped_data("INVOICE", "SGD")
        mapped["tax_currency"] = "SGD"
        xml = XMLGeneratorService().generate_invoice_xml(mapped)
        root = etree.fromstring(xml.encode("utf-8"))
        assert root.find("cbc:TaxCurrencyCode", {"cbc": NS_CBC}) is None

    def test_divergent_tax_currency_is_still_emitted(self):
        """The divergence path stays open: a payload whose tax currency
        genuinely differs emits the element with the differing code."""
        from apps.peppol.services.xml_generator_service import XMLGeneratorService

        mapped = _mapped_data("INVOICE", "USD")
        mapped["tax_currency"] = "MYR"
        xml = XMLGeneratorService().generate_invoice_xml(mapped)
        root = etree.fromstring(xml.encode("utf-8"))
        tcc = root.find("cbc:TaxCurrencyCode", {"cbc": NS_CBC})
        assert tcc is not None and tcc.text == "MYR"

    def test_credit_note_path_omits_tax_currency_code_when_equal(self):
        from apps.peppol.services.xml_generator_service import XMLGeneratorService

        mapped = _mapped_data("CREDIT_NOTE", "SGD")
        mapped["document_id"] = "CN-P36-H2"
        mapped["tax_currency"] = "SGD"
        xml = XMLGeneratorService().generate_credit_note_xml(mapped)
        root = etree.fromstring(xml.encode("utf-8"))
        assert root.find("cbc:TaxCurrencyCode", {"cbc": NS_CBC}) is None


def _usd_invoice():
    """An InvoiceDocument-shaped object for the MAPPER test (the real model
    fields the mapper reads)."""
    from decimal import Decimal

    class _Addr:
        def __init__(self, **kw):
            self.__dict__.update(kw)

    class _Contact:
        name = "USD Customer Corp"
        legal_name = "USD Customer Corp Pte Ltd"
        uen = "202398765B"
        gst_reg_number = None
        is_gst_registered = False
        address_line_1 = "2 Oak St"
        address_line_2 = None
        city = "Singapore"
        postal_code = "048583"
        country = "US"
        peppol_id = "0195:1234567890-UEN"

    class _Line:
        def __init__(self, line_number, line_amount, gst_amount, quantity,
                     unit_price, description, tax_code, tax_rate):
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
        name = "P36 Supplier Pte Ltd"
        legal_name = "P36 Supplier Pte Ltd"
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
                      "USD service", _TaxCode(), "0.09")
            ]

    class _Invoice:
        document_number = "INV-USD-P36"
        document_type = "INVOICE"
        issue_date = __import__("datetime").date(2026, 11, 28)
        due_date = __import__("datetime").date(2026, 12, 28)
        currency = "USD"
        total_excl = Decimal("1000.00")
        total_incl = Decimal("1090.00")
        gst_total = Decimal("90.00")
        amount_paid = Decimal("0.00")
        org = _Org()
        contact = _Contact()
        lines = _Lines()

    return _Invoice()


class TestPercentTruth:
    """The tax-category Percent is formatted through Decimal, never a float."""

    def _percent_for_rate(self, rate) -> str:
        from apps.peppol.services.xml_generator_service import XMLGeneratorService

        mapped = _mapped_data("INVOICE", "SGD")
        mapped["tax_currency"] = "SGD"
        mapped["tax_totals"]["tax_categories"][0]["rate"] = rate
        xml = XMLGeneratorService().generate_invoice_xml(mapped)
        root = etree.fromstring(xml.encode("utf-8"))
        percent = root.find(
            "cac:TaxTotal/cac:TaxSubtotal/cac:TaxCategory/cbc:Percent",
            {"cac": NS_CAC, "cbc": NS_CBC},
        )
        assert percent is not None, "fixture sanity: the Percent must be emitted"
        return percent.text

    def test_seven_percent_rate_formats_exactly(self):
        """RED on the base tree: str(float(0.07) * 100) emits the float
        artifact "7.000000000000001"."""
        assert self._percent_for_rate(0.07) == "7"

    def test_nine_percent_rate_formats_exactly(self):
        assert self._percent_for_rate(0.09) == "9"

    def test_fractional_rate_formats_exactly(self):
        assert self._percent_for_rate(0.0875) == "8.75"

    def test_zero_rate_formats_exactly(self):
        assert self._percent_for_rate(0.0) == "0"

    def test_decimal_rate_input_formats_exactly(self):
        """The mapper may carry the DB Decimal (scale 4) — the formatter
        must tolerate both shapes and emit the canonical form."""
        from decimal import Decimal

        assert self._percent_for_rate(Decimal("0.0700")) == "7"

    def test_changed_outputs_still_pass_the_full_validation(self):
        """The changed bytes (no TaxCurrencyCode, canonical Percent) must
        stay XSD-valid and business-rule-valid end to end."""
        from apps.peppol.services.xml_generator_service import XMLGeneratorService
        from apps.peppol.services.xml_validation_service import XMLValidationService

        mapped = _mapped_data("INVOICE", "SGD")
        mapped["tax_currency"] = "SGD"
        xml = XMLGeneratorService().generate_invoice_xml(mapped)
        result = XMLValidationService().validate_invoice_xml(xml)
        assert result["schema_errors"] == [], result["schema_errors"]
        assert result["schematron_errors"] == [], result["schematron_errors"]
        assert result["is_valid"] is True
