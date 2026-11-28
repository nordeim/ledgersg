"""
P35/BE-P35-H1: the Schematron business-rule truth — the wiring + the rules.

Pre-P35 (all reproduced on the base tree via live probes):
(a) PINT-UBL-validation.sch declared the WRONG XML namespace
    (http://purl.oclc.org/dml/schematron — a typo of the ISO Schematron
    namespace http://purl.oclc.org/dsdl/schematron) AND an unsupported
    queryBinding="xslt2" (lxml ships only the XSLT 1.0 skeleton; an
    XSLT 2.0 binding needs Saxon). The artefact has never been loadable
    by ANY ISO-Schematron implementation: lxml raises
    SchematronParseError on construction.
(b) _validate_schematron is a placeholder returning [] that NEITHER
    validate method ever calls — schematron_errors in every result is
    the constant []. A USD document with ONE amount's currencyID
    tampered to SGD (internally inconsistent UBL, exactly the P33
    hazard class) passes validation clean: the XSD cannot express
    cross-element truths, and the business-rule layer that should is
    dead code.
(c) The one test on the axis was vacuous: `assert hasattr(...) or True`.

Why the suite never saw it: the vacuous test plus the never-called
placeholder — the same stacked-blind-spot class the P34 lesson names,
one layer higher.
"""

import lxml.etree as etree
import pytest
from lxml import isoschematron

pytestmark = pytest.mark.django_db

NS_CBC = "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
NS_CAC = "urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2"
NS_INVOICE = "urn:oasis:names:specification:ubl:schema:xsd:Invoice-2"
NS_CREDIT_NOTE = "urn:oasis:names:specification:ubl:schema:xsd:CreditNote-2"

SCHEMATRON_PATH = "apps/peppol/schemas/PINT-UBL-validation.sch"


def _usd_invoice_mapped_data() -> dict:
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
                "line_extension_amount": "1000.00",
                "unit_price": "100.00",
            }
        ],
    }


def _usd_credit_note_mapped_data() -> dict:
    """The credit-note analog of the invoice payload."""
    data = _usd_invoice_mapped_data()
    data["document_id"] = "CN-USD-001"
    data["document_type"] = "CREDIT_NOTE"
    return data


def _rule_ids(errors: list) -> set:
    """Extract the BR-SG rule IDs carried in the schematron error messages."""
    ids = set()
    for error in errors:
        message = error.get("message", "") if isinstance(error, dict) else str(error)
        for part in message.split():
            if part.startswith("BR-SG-"):
                ids.add(part.rstrip(":"))
    return ids


class TestSchematronArtefactLoads:
    """The .sch must be a real, loadable ISO Schematron schema (H1-a)."""

    def test_pint_sch_loads_as_iso_schematron(self):
        parser = etree.XMLParser(
            resolve_entities=False, no_network=True, load_dtd=False, huge_tree=False
        )
        sch_doc = etree.parse(SCHEMATRON_PATH, parser)
        # RED on the base tree: SchematronParseError (the dml-namespace artefact)
        sct = isoschematron.Schematron(sch_doc, store_report=True)
        assert sct is not None

    def test_pint_sch_declares_the_iso_namespace_and_xslt_binding(self):
        """The artefact's own contract: the dsdl namespace + the xslt binding."""
        parser = etree.XMLParser(resolve_entities=False, no_network=True)
        root = etree.parse(SCHEMATRON_PATH, parser).getroot()
        assert root.tag == "{http://purl.oclc.org/dsdl/schematron}schema"
        assert root.get("queryBinding") == "xslt"


class TestSchematronWiring:
    """The business-rule layer is wired into both validate methods (H1-b)."""

    def _generate_and_validate_invoice(self, mapped: dict) -> dict:
        from apps.peppol.services.xml_generator_service import XMLGeneratorService
        from apps.peppol.services.xml_validation_service import XMLValidationService

        xml = XMLGeneratorService().generate_invoice_xml(mapped)
        return XMLValidationService().validate_invoice_xml(xml)

    def _generate_and_validate_credit_note(self, mapped: dict) -> dict:
        from apps.peppol.services.xml_generator_service import XMLGeneratorService
        from apps.peppol.services.xml_validation_service import XMLValidationService

        xml = XMLGeneratorService().generate_credit_note_xml(mapped)
        return XMLValidationService().validate_credit_note_xml(xml)

    def test_clean_invoice_passes_the_business_rules(self):
        result = self._generate_and_validate_invoice(_usd_invoice_mapped_data())
        assert result["schema_errors"] == []
        # RED on the base tree: this passes, but the tampered twin below proves
        # the layer is decorative; the assertion that FAILS on base is the twin.
        assert result["schematron_errors"] == []
        assert result["is_valid"] is True

    def test_tampered_currency_id_fails_the_business_rules(self):
        """The flagship cross-element rule: a USD document whose TaxAmount
        claims SGD is internally inconsistent UBL — the P33 hazard class."""
        from apps.peppol.services.xml_generator_service import XMLGeneratorService

        mapped = _usd_invoice_mapped_data()
        xml = XMLGeneratorService().generate_invoice_xml(mapped)
        # Flip ONE amount's currencyID (the first: the TaxTotal TaxAmount)
        assert 'currencyID="USD"' in xml
        tampered = xml.replace('currencyID="USD"', 'currencyID="SGD"', 1)

        from apps.peppol.services.xml_validation_service import XMLValidationService

        result = XMLValidationService().validate_invoice_xml(tampered)
        # RED on the base tree: is_valid is True today — the XSD cannot see it
        assert result["is_valid"] is False
        assert _rule_ids(result["schematron_errors"]) >= {"BR-SG-06"}

    def test_lowercased_document_currency_fails_the_shape_rule(self):
        from apps.peppol.services.xml_generator_service import XMLGeneratorService
        from apps.peppol.services.xml_validation_service import XMLValidationService

        mapped = _usd_invoice_mapped_data()
        xml = XMLGeneratorService().generate_invoice_xml(mapped)
        lowered = xml.replace(
            "<cbc:DocumentCurrencyCode>USD</cbc:DocumentCurrencyCode>",
            "<cbc:DocumentCurrencyCode>usd</cbc:DocumentCurrencyCode>",
        )
        assert lowered != xml, "fixture sanity: the tamper must apply"

        result = XMLValidationService().validate_invoice_xml(lowered)
        assert result["is_valid"] is False
        assert "BR-SG-04" in _rule_ids(result["schematron_errors"])

    def test_missing_id_fails_the_business_floor_too(self):
        from apps.peppol.services.xml_generator_service import XMLGeneratorService
        from apps.peppol.services.xml_validation_service import XMLValidationService

        mapped = _usd_invoice_mapped_data()
        xml = XMLGeneratorService().generate_invoice_xml(mapped)
        no_id = xml.replace("<cbc:ID>INV-USD-001</cbc:ID>", "")

        result = XMLValidationService().validate_invoice_xml(no_id)
        # The XSD rejects it (structure) AND the business floor fires (BR-SG-02)
        assert result["is_valid"] is False
        assert "BR-SG-02" in _rule_ids(result["schematron_errors"])

    def test_clean_credit_note_passes_the_business_rules(self):
        result = self._generate_and_validate_credit_note(_usd_credit_note_mapped_data())
        assert result["schema_errors"] == []
        assert result["schematron_errors"] == []
        assert result["is_valid"] is True

    def test_tampered_credit_note_currency_fails(self):
        from apps.peppol.services.xml_generator_service import XMLGeneratorService
        from apps.peppol.services.xml_validation_service import XMLValidationService

        mapped = _usd_credit_note_mapped_data()
        xml = XMLGeneratorService().generate_credit_note_xml(mapped)
        tampered = xml.replace('currencyID="USD"', 'currencyID="EUR"', 1)
        assert tampered != xml, "fixture sanity"

        result = XMLValidationService().validate_credit_note_xml(tampered)
        assert result["is_valid"] is False
        assert "BR-SG-06" in _rule_ids(result["schematron_errors"])

    def test_schematron_errors_carry_message_and_location(self):
        """The SVRL extraction shape: a dict with a human message + a location."""
        from apps.peppol.services.xml_generator_service import XMLGeneratorService
        from apps.peppol.services.xml_validation_service import XMLValidationService

        mapped = _usd_invoice_mapped_data()
        xml = XMLGeneratorService().generate_invoice_xml(mapped)
        tampered = xml.replace('currencyID="USD"', 'currencyID="SGD"', 1)

        result = XMLValidationService().validate_invoice_xml(tampered)
        errors = result["schematron_errors"]
        assert errors, "the tampered document must produce schematron errors"
        for error in errors:
            assert isinstance(error, dict)
            assert isinstance(error.get("message"), str) and error["message"]
            assert "location" in error

    def test_fail_closed_when_schematron_fails_to_load(self):
        """The P9/S-3 posture mirrored: a .sch that failed to load reports an
        error in schematron_errors — never silence, never a silent pass."""
        from apps.peppol.services.xml_generator_service import XMLGeneratorService
        from apps.peppol.services.xml_validation_service import XMLValidationService

        service = XMLValidationService()
        service._schematron_schema = None  # simulate the load failure

        mapped = _usd_invoice_mapped_data()
        xml = XMLGeneratorService().generate_invoice_xml(mapped)
        result = service.validate_invoice_xml(xml)
        assert result["is_valid"] is False
        assert result["schematron_errors"], "the load failure must be reported"
        messages = " ".join(
            e.get("message", "") if isinstance(e, dict) else str(e)
            for e in result["schematron_errors"]
        )
        assert "Schematron" in messages or "schematron" in messages
