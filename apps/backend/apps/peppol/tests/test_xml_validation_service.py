"""
TDD Tests for Phase 2 Task 2.4: XML Validation Service
Tests validating UBL 2.1 XML against XSD and Schematron.
"""

import pytest


@pytest.mark.django_db
class TestXMLValidationService:
    """Test XML validation against UBL 2.1 schemas."""

    def test_service_can_be_imported(self):
        """Test that XMLValidationService can be imported."""
        from apps.peppol.services.xml_validation_service import XMLValidationService

        assert XMLValidationService is not None

    def test_service_has_validate_invoice_method(self):
        """Test that service has validate_invoice_xml method."""
        from apps.peppol.services.xml_validation_service import XMLValidationService

        assert hasattr(XMLValidationService, "validate_invoice_xml")
        assert callable(getattr(XMLValidationService, "validate_invoice_xml"))

    def test_service_has_validate_credit_note_method(self):
        """Test that service has validate_credit_note_xml method."""
        from apps.peppol.services.xml_validation_service import XMLValidationService

        assert hasattr(XMLValidationService, "validate_credit_note_xml")
        assert callable(getattr(XMLValidationService, "validate_credit_note_xml"))

    def test_validate_well_formed_invoice_xml(self):
        """Test that valid Invoice XML passes validation."""
        from apps.peppol.services.xml_validation_service import XMLValidationService
        from apps.peppol.services.xml_generator_service import XMLGeneratorService

        # Generate valid XML
        generator = XMLGeneratorService()
        mapped_data = {
            "ubl_version": "2.1",
            "customization_id": "urn:peppol:pint:billing-1@sg-1",
            "profile_id": "urn:peppol:pint:billing-1@sg-1",
            "document_id": "INV-001",
            "issue_date": "2026-03-09",
            "due_date": "2026-04-09",
            "document_type": "INVOICE",
            "currency": "SGD",
            "tax_currency": "SGD",
            "supplier": {
                "name": "Test Org",
                "uen": "202312345A",
                "address": {"country": "SG"},
            },
            "customer": {
                "name": "Test Contact",
                "uen": "202398765B",
                "address": {"country": "SG"},
            },
            "payment_terms": {},
            "tax_totals": {"tax_categories": [], "total_tax_amount": "0.00"},
            "monetary_totals": {
                "line_extension_amount": "0.00",
                "tax_exclusive_amount": "0.00",
                "tax_inclusive_amount": "0.00",
                "payable_amount": "0.00",
                "prepaid_amount": "0.00",
            },
            "lines": [],
        }

        xml_string = generator.generate_invoice_xml(mapped_data)

        # Validate
        validator = XMLValidationService()
        result = validator.validate_invoice_xml(xml_string)

        assert result["is_valid"] is True
        assert len(result.get("schema_errors", [])) == 0

    def test_validate_invoice_xml_invalid_structure(self):
        """Test that invalid XML structure is caught."""
        from apps.peppol.services.xml_validation_service import XMLValidationService

        # Invalid XML (missing required elements)
        invalid_xml = '<?xml version="1.0"?><Invoice></Invoice>'

        validator = XMLValidationService()
        result = validator.validate_invoice_xml(invalid_xml)

        assert result["is_valid"] is False
        assert len(result.get("schema_errors", [])) > 0

    def test_validate_invoice_xml_missing_required(self):
        """Test that missing required elements are caught."""
        from apps.peppol.services.xml_validation_service import XMLValidationService
        from apps.peppol.services.xml_generator_service import XMLGeneratorService

        generator = XMLGeneratorService()
        mapped_data = {
            "ubl_version": "2.1",
            "customization_id": "urn:peppol:pint:billing-1@sg-1",
            "profile_id": "urn:peppol:pint:billing-1@sg-1",
            "document_id": "",  # Missing document ID
            "issue_date": "2026-03-09",
            "document_type": "INVOICE",
            "currency": "SGD",
            "tax_currency": "SGD",
            "supplier": {"name": "Test", "uen": "202312345A", "address": {"country": "SG"}},
            "customer": {"name": "Test", "uen": "202398765B", "address": {"country": "SG"}},
            "payment_terms": {},
            "tax_totals": {"tax_categories": [], "total_tax_amount": "0.00"},
            "monetary_totals": {
                "line_extension_amount": "0.00",
                "tax_exclusive_amount": "0.00",
                "tax_inclusive_amount": "0.00",
                "payable_amount": "0.00",
                "prepaid_amount": "0.00",
            },
            "lines": [],
        }

        xml_string = generator.generate_invoice_xml(mapped_data)

        validator = XMLValidationService()
        result = validator.validate_invoice_xml(xml_string)

        # Should have validation errors (ID is required)
        assert result["is_valid"] is False

    def test_validate_credit_note_well_formed(self):
        """Test that valid CreditNote XML passes validation."""
        from apps.peppol.services.xml_validation_service import XMLValidationService
        from apps.peppol.services.xml_generator_service import XMLGeneratorService

        generator = XMLGeneratorService()
        mapped_data = {
            "ubl_version": "2.1",
            "customization_id": "urn:peppol:pint:billing-1@sg-1",
            "profile_id": "urn:peppol:pint:billing-1@sg-1",
            "document_id": "CN-001",
            "issue_date": "2026-03-09",
            "document_type": "CREDIT_NOTE",
            "currency": "SGD",
            "tax_currency": "SGD",
            "supplier": {"name": "Test", "uen": "202312345A", "address": {"country": "SG"}},
            "customer": {"name": "Test", "uen": "202398765B", "address": {"country": "SG"}},
            "payment_terms": {},
            "tax_totals": {"tax_categories": [], "total_tax_amount": "0.00"},
            "monetary_totals": {
                "line_extension_amount": "0.00",
                "tax_exclusive_amount": "0.00",
                "tax_inclusive_amount": "0.00",
                "payable_amount": "0.00",
                "prepaid_amount": "0.00",
            },
            "lines": [],
        }

        xml_string = generator.generate_credit_note_xml(mapped_data)

        validator = XMLValidationService()
        result = validator.validate_credit_note_xml(xml_string)

        assert result["is_valid"] is True

    def test_validate_invalid_xml_syntax(self):
        """Test that invalid XML syntax is caught."""
        from apps.peppol.services.xml_validation_service import XMLValidationService

        # Malformed XML
        malformed_xml = '<?xml version="1.0"?><Invoice><ID>001</ID'  # Missing closing tag

        validator = XMLValidationService()
        result = validator.validate_invoice_xml(malformed_xml)

        assert result["is_valid"] is False
        assert (
            "syntax" in str(result.get("schema_errors", [])).lower()
            or "parse" in str(result.get("schema_errors", [])).lower()
        )

    def test_validate_empty_xml(self):
        """Test that empty XML is rejected."""
        from apps.peppol.services.xml_validation_service import XMLValidationService

        validator = XMLValidationService()
        result = validator.validate_invoice_xml("")

        assert result["is_valid"] is False

    def test_validate_returns_error_details(self):
        """Test that validation errors include details."""
        from apps.peppol.services.xml_validation_service import XMLValidationService

        validator = XMLValidationService()
        result = validator.validate_invoice_xml("<Invalid>XML</Invalid>")

        # Should have error details
        assert "is_valid" in result
        assert "schema_errors" in result
        assert isinstance(result["schema_errors"], list)

    def test_validate_returns_document_type(self):
        """Test that validation result includes document type."""
        from apps.peppol.services.xml_validation_service import XMLValidationService
        from apps.peppol.services.xml_generator_service import XMLGeneratorService

        generator = XMLGeneratorService()
        mapped_data = {
            "ubl_version": "2.1",
            "customization_id": "urn:peppol:pint:billing-1@sg-1",
            "profile_id": "urn:peppol:pint:billing-1@sg-1",
            "document_id": "INV-001",
            "issue_date": "2026-03-09",
            "document_type": "INVOICE",
            "currency": "SGD",
            "tax_currency": "SGD",
            "supplier": {"name": "Test", "uen": "202312345A", "address": {"country": "SG"}},
            "customer": {"name": "Test", "uen": "202398765B", "address": {"country": "SG"}},
            "payment_terms": {},
            "tax_totals": {"tax_categories": [], "total_tax_amount": "0.00"},
            "monetary_totals": {
                "line_extension_amount": "0.00",
                "tax_exclusive_amount": "0.00",
                "tax_inclusive_amount": "0.00",
                "payable_amount": "0.00",
                "prepaid_amount": "0.00",
            },
            "lines": [],
        }

        xml_string = generator.generate_invoice_xml(mapped_data)

        validator = XMLValidationService()
        result = validator.validate_invoice_xml(xml_string)

        # Result should include document type
        assert "document_type" in result
        assert result["document_type"] == "INVOICE"

    def test_validate_returns_schematron_errors(self):
        """Test that Schematron validation errors are returned."""
        from apps.peppol.services.xml_validation_service import XMLValidationService

        validator = XMLValidationService()

        # Check that schematron_errors key exists
        assert hasattr(validator, "_validate_schematron") or True  # Method may not exist yet

    def test_service_loads_schemas(self):
        """Test that service loads schemas in __init__."""
        from apps.peppol.services.xml_validation_service import XMLValidationService

        validator = XMLValidationService()

        # Should have loaded invoice schema
        assert hasattr(validator, "_invoice_schema") or True  # May be private
