"""
P33/BE-P33-H1: the Peppol amount-currency truth.

Pre-P33: XMLMappingService maps the document's own currency
(`invoice.currency or "SGD"`) into DocumentCurrencyCode, but
XMLGeneratorService hardcodes currencyID="SGD" on every amount element
(11 sites) — a USD/EUR-denominated document transmitted through
InvoiceNow produced internally inconsistent UBL
(DocumentCurrencyCode=USD beside currencyID="SGD" amounts). The existing
generator tests only ever built SGD payloads — the fixture masked the
hardcode (the same default-value-fixture blind-spot class as P1/A-2).
"""


import pytest

pytestmark = pytest.mark.django_db


def _usd_mapped_data() -> dict:
    """A minimal valid invoice payload denominated in USD (the mapper's own shape)."""
    return {
        "ubl_version": "2.1",
        "customization_id": "urn:peppol:pint:billing-1@sg-1",
        "profile_id": "urn:peppol:pint:billing-1@sg-1",
        "document_id": "INV-USD-001",
        "issue_date": "2026-11-28",
        "due_date": "2026-12-28",
        "document_type": "INVOICE",
        "currency": "USD",
        "tax_currency": "USD",
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
                "description": "USD-denominated service",
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


class TestPeppolAmountCurrencyTruth:
    """Every amount element's currencyID must match the document currency."""

    def test_document_currency_code_is_usd(self):
        from lxml import etree

        from apps.peppol.services.xml_generator_service import XMLGeneratorService

        xml_string = XMLGeneratorService().generate_invoice_xml(_usd_mapped_data())
        root = etree.fromstring(xml_string.encode("utf-8"))

        ns = {"cbc": "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"}
        code = root.find("cbc:DocumentCurrencyCode", ns)
        assert code is not None and code.text == "USD"

    def test_tax_total_amounts_carry_document_currency(self):
        from lxml import etree

        from apps.peppol.services.xml_generator_service import XMLGeneratorService

        xml_string = XMLGeneratorService().generate_invoice_xml(_usd_mapped_data())
        root = etree.fromstring(xml_string.encode("utf-8"))

        ns = {
            "cbc": "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2",
            "cac": "urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2",
        }
        # TaxTotal/TaxAmount
        tax_amount = root.find(".//cbc:TaxAmount", ns)
        assert tax_amount is not None, "TaxTotal/TaxAmount missing"
        assert tax_amount.get("currencyID") == "USD", (
            f"TaxTotal/TaxAmount currencyID={tax_amount.get('currencyID')!r} — "
            "the document is USD-denominated"
        )
        # TaxSubtotal/TaxableAmount + TaxSubtotal/TaxAmount
        taxable = root.findall(".//cbc:TaxableAmount", ns)
        assert len(taxable) == 1
        assert taxable[0].get("currencyID") == "USD"
        subtotal_amounts = root.findall(".//cac:TaxSubtotal/cbc:TaxAmount", ns)
        assert len(subtotal_amounts) == 1
        assert subtotal_amounts[0].get("currencyID") == "USD"

    def test_monetary_total_amounts_carry_document_currency(self):
        from lxml import etree

        from apps.peppol.services.xml_generator_service import XMLGeneratorService

        xml_string = XMLGeneratorService().generate_invoice_xml(_usd_mapped_data())
        root = etree.fromstring(xml_string.encode("utf-8"))

        ns = {
            "cbc": "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2",
            "cac": "urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2",
        }
        for tag in (
            "LineExtensionAmount",
            "TaxExclusiveAmount",
            "TaxInclusiveAmount",
            "PayableAmount",
            "PrepaidAmount",
        ):
            el = root.find(f"cac:LegalMonetaryTotal/cbc:{tag}", ns)
            assert el is not None, f"LegalMonetaryTotal/{tag} missing"
            assert el.get("currencyID") == "USD", (
                f"{tag} currencyID={el.get('currencyID')!r} — the document is USD-denominated"
            )

    def test_line_amounts_carry_document_currency(self):
        from lxml import etree

        from apps.peppol.services.xml_generator_service import XMLGeneratorService

        xml_string = XMLGeneratorService().generate_invoice_xml(_usd_mapped_data())
        root = etree.fromstring(xml_string.encode("utf-8"))

        ns = {
            "cbc": "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2",
            "cac": "urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2",
        }
        line_ext = root.find(".//cac:InvoiceLine/cbc:LineExtensionAmount", ns)
        assert line_ext is not None, "InvoiceLine/LineExtensionAmount missing"
        assert line_ext.get("currencyID") == "USD"
        price = root.find(".//cac:InvoiceLine/cac:Price/cbc:PriceAmount", ns)
        assert price is not None, "InvoiceLine/Price/PriceAmount missing"
        assert price.get("currencyID") == "USD"

    def test_no_amount_element_claims_sgd_on_a_usd_document(self):
        """The sweep gate: zero currencyID attributes may claim SGD on a USD document."""
        from lxml import etree

        from apps.peppol.services.xml_generator_service import XMLGeneratorService

        xml_string = XMLGeneratorService().generate_invoice_xml(_usd_mapped_data())
        root = etree.fromstring(xml_string.encode("utf-8"))

        offenders = [
            f"{el.getparent().tag.split('}')[-1]}/{el.tag.split('}')[-1]}"
            for el in root.iter()
            if el.get("currencyID") == "SGD"
        ]
        assert offenders == [], (
            f"amount elements still claiming currencyID=SGD on a USD document: {offenders}"
        )

    def test_sgd_document_output_is_unchanged(self):
        """The SGD default path is byte-stable: a SGD payload carries currencyID=SGD everywhere."""
        from lxml import etree

        from apps.peppol.services.xml_generator_service import XMLGeneratorService

        data = _usd_mapped_data()
        data["currency"] = "SGD"
        xml_string = XMLGeneratorService().generate_invoice_xml(data)
        root = etree.fromstring(xml_string.encode("utf-8"))

        currency_ids = {el.get("currencyID") for el in root.iter() if el.get("currencyID")}
        assert currency_ids == {"SGD"}, (
            f"SGD document must carry only SGD currencyIDs: {currency_ids}"
        )
