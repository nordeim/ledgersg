"""
P36/BE-P36-H1: the Peppol arithmetic truth — the BR-CO calculation rules.

Pre-P36: the .sch business-rule layer (P35) checks the currency consistency
and the presence floors, but NO calculation rules — a document whose totals
disagree with its own lines (a tampered TaxInclusiveAmount, a corrupted line
amount) validates clean. The generator computes every total from the DB's
NUMERIC(19,4) Decimals, so the invariants hold by construction in emitted
XML — the missing layer converts construction-truth into checked-truth
(the layer a real Peppol access point adds: the EN 16931 BR-CO rules).

The rounding conversation (registered in the P35 deferred register): XPath
1.0 sum() computes in IEEE doubles while the mapper emits NUMERIC(19,4)
decimal strings. Resolution, prototype-validated against the real generator
output BEFORE this spec: the construction-exact rules compare with the
half-unit-of-the-last-decimal guard (0.00005); BR-CO-17 uses the per-line
rounding bound (the DB rounds GST per line to 2dp — IRAS cent-level — so the
category tax is a sum of per-line roundings, and |tax - taxable*rate/100|
is bounded by 0.005 x line count, never false-rejecting).
"""

import lxml.etree as etree
import pytest

pytestmark = pytest.mark.django_db

NS_CBC = "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
NS_CAC = "urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2"

SCHEMATRON_PATH = "apps/peppol/schemas/PINT-UBL-validation.sch"


def _sgd_invoice_mapped_data() -> dict:
    """A minimal valid invoice payload denominated in SGD (the mapper's own
    shape), with arithmetic-consistent totals (1000 / 90 / 1090)."""
    return {
        "ubl_version": "2.1",
        "customization_id": "urn:peppol:pint:billing-1@sg-1",
        "profile_id": "urn:peppol:pint:billing-1@sg-1",
        "document_id": "INV-SGD-P36",
        "issue_date": "2026-11-28",
        "due_date": "2026-12-28",
        "document_type": "INVOICE",
        "currency": "SGD",
        "tax_currency": "SGD",
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
                "description": "P36 arithmetic service",
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


def _rule_ids(errors: list) -> set:
    """Extract the BR-CO rule IDs carried in the schematron error messages."""
    ids = set()
    for error in errors:
        message = error.get("message", "") if isinstance(error, dict) else str(error)
        for part in message.split():
            if part.startswith(("BR-CO-", "BR-SG-")):
                ids.add(part.rstrip(":,"))
    return ids


def _generate_invoice_xml(mapped: dict) -> str:
    from apps.peppol.services.xml_generator_service import XMLGeneratorService

    return XMLGeneratorService().generate_invoice_xml(mapped)


def _validate_invoice(xml_string: str) -> dict:
    from apps.peppol.services.xml_validation_service import XMLValidationService

    return XMLValidationService().validate_invoice_xml(xml_string)


def _generate_credit_note_xml(mapped: dict) -> str:
    from apps.peppol.services.xml_generator_service import XMLGeneratorService

    return XMLGeneratorService().generate_credit_note_xml(mapped)


def _validate_credit_note(xml_string: str) -> dict:
    from apps.peppol.services.xml_validation_service import XMLValidationService

    return XMLValidationService().validate_credit_note_xml(xml_string)


class TestArithmeticRulesWired:
    """The six BR-CO calculation rules run on every candidate document."""

    def test_sch_declares_the_arithmetic_pattern(self):
        """The artefact carries the PINT-SG-ARITHMETIC pattern with the
        six rule IDs (RED on the base tree: the pattern does not exist)."""
        parser = etree.XMLParser(resolve_entities=False, no_network=True)
        root = etree.parse(SCHEMATRON_PATH, parser).getroot()
        xml = etree.tostring(root, encoding="unicode")
        assert "PINT-SG-ARITHMETIC" in xml
        for role in ("BR-CO-10", "BR-CO-13", "BR-CO-14", "BR-CO-15", "BR-CO-16", "BR-CO-17"):
            assert role in xml, f"the artefact must carry {role}"

    def test_clean_invoice_passes_the_arithmetic_rules(self):
        result = _validate_invoice(_generate_invoice_xml(_sgd_invoice_mapped_data()))
        assert result["schema_errors"] == []
        assert result["schematron_errors"] == []
        assert result["is_valid"] is True

    def test_clean_credit_note_passes_the_arithmetic_rules(self):
        mapped = _sgd_invoice_mapped_data()
        mapped["document_id"] = "CN-SGD-P36"
        mapped["document_type"] = "CREDIT_NOTE"
        # P37/BE-P37-H1: the honest mapper shape (BR-SG-07 requires the
        # reference on every CreditNote root).
        mapped["billing_reference"] = {"id": "INV-SGD-P36",
                                       "issue_date": "2026-11-01"}
        result = _validate_credit_note(_generate_credit_note_xml(mapped))
        assert result["schema_errors"] == []
        assert result["schematron_errors"] == []
        assert result["is_valid"] is True

    def test_tampered_tax_inclusive_fails_br_co_15(self):
        """The registered gap: a document whose TaxInclusiveAmount was edited
        after generation (or corrupted in transit) must NOT validate clean.
        RED on the base tree: is_valid is True today."""
        xml = _generate_invoice_xml(_sgd_invoice_mapped_data())
        tampered = xml.replace(
            "<cbc:TaxInclusiveAmount currencyID=\"SGD\">1090.00",
            "<cbc:TaxInclusiveAmount currencyID=\"SGD\">1590.00",
        )
        assert tampered != xml, "fixture sanity: the tamper must apply"

        result = _validate_invoice(tampered)
        assert result["is_valid"] is False
        ids = _rule_ids(result["schematron_errors"])
        assert "BR-CO-15" in ids, f"BR-CO-15 must fire, got {ids}"
        assert "BR-CO-16" in ids, "the payable no longer reconciles either"

    def test_tampered_line_amount_fails_br_co_10(self):
        """A corrupted line amount (the sum no longer equals the document
        LineExtensionAmount) must fail with BR-CO-10 named."""
        xml = _generate_invoice_xml(_sgd_invoice_mapped_data())
        tampered = xml.replace(
            "<cbc:LineExtensionAmount currencyID=\"SGD\">1000.00"
            "</cbc:LineExtensionAmount>\n            <cbc:InvoicedQuantity",
            "<cbc:LineExtensionAmount currencyID=\"SGD\">3000.00"
            "</cbc:LineExtensionAmount>\n            <cbc:InvoicedQuantity",
        )
        if tampered == xml:
            # the line-level element (first occurrence) — target it directly
            tampered = xml.replace(
                "<cbc:LineExtensionAmount currencyID=\"SGD\">1000.00",
                "<cbc:LineExtensionAmount currencyID=\"SGD\">3000.00", 1
            )
        assert tampered != xml, "fixture sanity: the tamper must apply"

        result = _validate_invoice(tampered)
        assert result["is_valid"] is False
        assert "BR-CO-10" in _rule_ids(result["schematron_errors"])

    def test_tampered_payable_fails_br_co_16(self):
        xml = _generate_invoice_xml(_sgd_invoice_mapped_data())
        tampered = xml.replace(
            "<cbc:PayableAmount currencyID=\"SGD\">1090.00",
            "<cbc:PayableAmount currencyID=\"SGD\">1080.00",
        )
        assert tampered != xml, "fixture sanity: the tamper must apply"

        result = _validate_invoice(tampered)
        assert result["is_valid"] is False
        assert "BR-CO-16" in _rule_ids(result["schematron_errors"])

    def test_tampered_tax_exclusive_fails_br_co_13(self):
        xml = _generate_invoice_xml(_sgd_invoice_mapped_data())
        tampered = xml.replace(
            "<cbc:TaxExclusiveAmount currencyID=\"SGD\">1000.00",
            "<cbc:TaxExclusiveAmount currencyID=\"SGD\">1100.00",
        )
        assert tampered != xml, "fixture sanity: the tamper must apply"

        result = _validate_invoice(tampered)
        assert result["is_valid"] is False
        ids = _rule_ids(result["schematron_errors"])
        assert "BR-CO-13" in ids
        assert "BR-CO-15" in ids, "the tax-inclusive no longer reconciles either"

    def test_tampered_subtotal_tax_fails_br_co_14_and_17(self):
        xml = _generate_invoice_xml(_sgd_invoice_mapped_data())
        root = etree.fromstring(xml.encode("utf-8"))
        # Target the SUBTOTAL tax (not the document-level TaxTotal amount):
        # tamper it so it no longer matches taxable x rate (BR-CO-17) nor
        # sums to the document total (BR-CO-14).
        subtotal_tax = root.find(
            "cac:TaxTotal/cac:TaxSubtotal/cbc:TaxAmount",
            {"cac": NS_CAC, "cbc": NS_CBC},
        )
        assert subtotal_tax is not None, "fixture sanity: the subtotal must exist"
        subtotal_tax.text = "190.00"

        result = _validate_invoice(etree.tostring(root).decode())
        assert result["is_valid"] is False
        ids = _rule_ids(result["schematron_errors"])
        assert "BR-CO-14" in ids, "the document total no longer equals the subtotals"
        assert "BR-CO-17" in ids, "the subtotal tax no longer matches taxable x rate"


class TestArithmeticRuleEdges:
    """The edge cases the XPath-1.0 formulation must survive."""

    def _synthetic_invoice_xml(
        self, lines: list, totals: dict, tax_total: str
    ) -> str:
        line_xml = "".join(
            f"<cac:InvoiceLine><cbc:ID>{i + 1}</cbc:ID>"
            f"<cbc:LineExtensionAmount currencyID=\"SGD\">{amount}"
            f"</cbc:LineExtensionAmount></cac:InvoiceLine>"
            for i, amount in enumerate(lines)
        )
        return (
            '<Invoice xmlns="urn:oasis:names:specification:ubl:schema:xsd:Invoice-2"'
            ' xmlns:cac="urn:oasis:names:specification:ubl:schema:xsd:'
            'CommonAggregateComponents-2"'
            ' xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:'
            'CommonBasicComponents-2">'
            "<cbc:ID>EDGE-P36</cbc:ID><cbc:IssueDate>2026-11-28</cbc:IssueDate>"
            "<cbc:DocumentCurrencyCode>SGD</cbc:DocumentCurrencyCode>"
            f"{line_xml}"
            "<cac:LegalMonetaryTotal>"
            f"<cbc:LineExtensionAmount currencyID=\"SGD\">{totals['le']}</cbc:LineExtensionAmount>"
            f"<cbc:TaxExclusiveAmount currencyID=\"SGD\">{totals['te']}</cbc:TaxExclusiveAmount>"
            f"<cbc:TaxInclusiveAmount currencyID=\"SGD\">{totals['ti']}</cbc:TaxInclusiveAmount>"
            f"<cbc:PayableAmount currencyID=\"SGD\">{totals['pa']}</cbc:PayableAmount>"
            "</cac:LegalMonetaryTotal>"
            f"{tax_total}"
            "</Invoice>"
        )

    def test_no_tax_total_inconsistent_tax_inclusive_fails(self):
        """TaxInclusive must equal TaxExclusive when the tax total is absent
        (sum() over an empty node-set is 0 — the absent-element NaN trap)."""
        xml = self._synthetic_invoice_xml(
            ["100.00"], {"le": "100.00", "te": "100.00", "ti": "109.00", "pa": "109.00"}, ""
        )
        result = _validate_invoice(xml)
        assert result["is_valid"] is False
        assert "BR-CO-15" in _rule_ids(result["schematron_errors"])

    def test_no_tax_total_consistent_passes(self):
        xml = self._synthetic_invoice_xml(
            ["100.00"], {"le": "100.00", "te": "100.00", "ti": "100.00", "pa": "100.00"}, ""
        )
        result = _validate_invoice(xml)
        assert result["schematron_errors"] == []

    def test_prepaid_reconciles_and_drift_fails(self):
        tax = (
            '<cac:TaxTotal><cbc:TaxAmount currencyID="SGD">9.00</cbc:TaxAmount>'
            '<cac:TaxSubtotal><cbc:TaxableAmount currencyID="SGD">100.00'
            "</cbc:TaxableAmount>"
            '<cbc:TaxAmount currencyID="SGD">9.00</cbc:TaxAmount>'
            "<cac:TaxCategory><cbc:Percent>9.0</cbc:Percent></cac:TaxCategory>"
            "</cac:TaxSubtotal></cac:TaxTotal>"
        )
        consistent = self._synthetic_invoice_xml(
            ["100.00"], {"le": "100.00", "te": "100.00", "ti": "109.00", "pa": "100.00"}, tax
        ).replace(
            "<cbc:PayableAmount currencyID=\"SGD\">100.00",
            "<cbc:PrepaidAmount currencyID=\"SGD\">9.00</cbc:PrepaidAmount>"
            "<cbc:PayableAmount currencyID=\"SGD\">100.00",
        )
        result = _validate_invoice(consistent)
        assert result["schematron_errors"] == [], result["schematron_errors"]

        drifted = consistent.replace(
            "<cbc:PayableAmount currencyID=\"SGD\">100.00</cbc:PayableAmount>",
            "<cbc:PayableAmount currencyID=\"SGD\">99.00</cbc:PayableAmount>",
        )
        result2 = _validate_invoice(drifted)
        assert result2["is_valid"] is False
        assert "BR-CO-16" in _rule_ids(result2["schematron_errors"])

    def test_per_line_rounding_passes_the_sound_bound(self):
        """3 x 5.55 at 9%: the DB rounds GST per line to 2dp, so the category
        tax is 0.50 + 0.50 + 0.50 = 1.50 while 16.65 x 0.09 = 1.4985 — a
        naive equality rule would false-reject this legitimate document."""
        tax = (
            '<cac:TaxTotal><cbc:TaxAmount currencyID="SGD">1.50</cbc:TaxAmount>'
            '<cac:TaxSubtotal><cbc:TaxableAmount currencyID="SGD">16.65'
            "</cbc:TaxableAmount>"
            '<cbc:TaxAmount currencyID="SGD">1.50</cbc:TaxAmount>'
            "<cac:TaxCategory><cbc:Percent>9.0</cbc:Percent></cac:TaxCategory>"
            "</cac:TaxSubtotal></cac:TaxTotal>"
        )
        xml = self._synthetic_invoice_xml(
            ["5.55", "5.55", "5.55"],
            {"le": "16.65", "te": "16.65", "ti": "18.15", "pa": "18.15"},
            tax,
        )
        result = _validate_invoice(xml)
        assert result["schematron_errors"] == [], result["schematron_errors"]

    def test_rounded_tax_drift_beyond_the_bound_fails_br_co_17(self):
        """+0.02 on the rounded tax exceeds the 0.005 x 3 bound — the tamper
        must be caught (the bound is tight enough to catch gross drift)."""
        tax = (
            '<cac:TaxTotal><cbc:TaxAmount currencyID="SGD">1.52</cbc:TaxAmount>'
            '<cac:TaxSubtotal><cbc:TaxableAmount currencyID="SGD">16.65'
            "</cbc:TaxableAmount>"
            '<cbc:TaxAmount currencyID="SGD">1.52</cbc:TaxAmount>'
            "<cac:TaxCategory><cbc:Percent>9.0</cbc:Percent></cac:TaxCategory>"
            "</cac:TaxSubtotal></cac:TaxTotal>"
        )
        xml = self._synthetic_invoice_xml(
            ["5.55", "5.55", "5.55"],
            {"le": "16.65", "te": "16.65", "ti": "18.17", "pa": "18.17"},
            tax,
        )
        result = _validate_invoice(xml)
        assert result["is_valid"] is False
        assert "BR-CO-17" in _rule_ids(result["schematron_errors"])

    def test_float_artifact_percent_still_passes_br_co_17(self):
        """A Percent carrying a float artifact ("7.000000000000001") deviates
        from the true rate by ~1e-15 — the tolerance must absorb it (the
        artifact is a P36/L1 generator fix, not a validation failure)."""
        tax = (
            '<cac:TaxTotal><cbc:TaxAmount currencyID="SGD">7.00</cbc:TaxAmount>'
            '<cac:TaxSubtotal><cbc:TaxableAmount currencyID="SGD">100.00'
            "</cbc:TaxableAmount>"
            '<cbc:TaxAmount currencyID="SGD">7.00</cbc:TaxAmount>'
            "<cac:TaxCategory><cbc:Percent>7.000000000000001</cbc:Percent>"
            "</cac:TaxCategory></cac:TaxSubtotal></cac:TaxTotal>"
        )
        xml = self._synthetic_invoice_xml(
            ["100.00"], {"le": "100.00", "te": "100.00", "ti": "107.00", "pa": "107.00"}, tax
        )
        result = _validate_invoice(xml)
        assert result["schematron_errors"] == [], result["schematron_errors"]
