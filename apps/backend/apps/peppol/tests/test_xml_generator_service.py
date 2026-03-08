"""
TDD Tests for Phase 2 Task 2.3: XML Generator Service
Tests generating UBL 2.1 XML from mapped data.
"""

import pytest
from decimal import Decimal
from datetime import date


@pytest.mark.django_db
class TestXMLGeneratorService:
    """Test XML generation from mapped data to UBL 2.1."""

    def test_service_can_be_imported(self):
        """Test that XMLGeneratorService can be imported."""
        from apps.peppol.services.xml_generator_service import XMLGeneratorService

        assert XMLGeneratorService is not None

    def test_service_has_generate_invoice_method(self):
        """Test that service has generate_invoice_xml method."""
        from apps.peppol.services.xml_generator_service import XMLGeneratorService

        assert hasattr(XMLGeneratorService, "generate_invoice_xml")
        assert callable(getattr(XMLGeneratorService, "generate_invoice_xml"))

    def test_service_has_generate_credit_note_method(self):
        """Test that service has generate_credit_note_xml method."""
        from apps.peppol.services.xml_generator_service import XMLGeneratorService

        assert hasattr(XMLGeneratorService, "generate_credit_note_xml")
        assert callable(getattr(XMLGeneratorService, "generate_credit_note_xml"))

    def test_service_has_calculate_hash_method(self):
        """Test that service has calculate_xml_hash method."""
        from apps.peppol.services.xml_generator_service import XMLGeneratorService

        assert hasattr(XMLGeneratorService, "calculate_xml_hash")
        assert callable(getattr(XMLGeneratorService, "calculate_xml_hash"))

    def test_service_has_namespace_constants(self):
        """Test that service defines UBL namespaces."""
        from apps.peppol.services.xml_generator_service import XMLGeneratorService

        assert hasattr(XMLGeneratorService, "NAMESPACE_UBL")
        assert hasattr(XMLGeneratorService, "NAMESPACE_CAC")
        assert hasattr(XMLGeneratorService, "NAMESPACE_CBC")
        assert "ubl" in XMLGeneratorService.NAMESPACE_UBL.lower()

    def test_generate_invoice_xml_structure(self):
        """Test generated XML has correct Invoice structure."""
        from apps.peppol.services.xml_generator_service import XMLGeneratorService

        service = XMLGeneratorService()
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
                "address": {"street": "123 Main St", "city": "Singapore", "country": "SG"},
            },
            "customer": {
                "name": "Test Contact",
                "uen": "202398765B",
                "address": {"street": "456 Oak St", "city": "Singapore", "country": "SG"},
            },
            "payment_terms": {"payment_due_date": "2026-04-09"},
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
                    "description": "Test Item",
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

        xml_string = service.generate_invoice_xml(mapped_data)

        # Verify it's valid XML
        from lxml import etree

        root = etree.fromstring(xml_string.encode("utf-8"))

        # Check root element
        assert root.tag.endswith("Invoice")

    def test_generate_invoice_customization_id(self):
        """Test CustomizationID is PINT-SG."""
        from apps.peppol.services.xml_generator_service import XMLGeneratorService

        service = XMLGeneratorService()
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

        xml_string = service.generate_invoice_xml(mapped_data)

        # Check customization ID
        assert "urn:peppol:pint:billing-1@sg-1" in xml_string

    def test_generate_invoice_has_supplier_party(self):
        """Test supplier party is included."""
        from apps.peppol.services.xml_generator_service import XMLGeneratorService

        service = XMLGeneratorService()
        mapped_data = {
            "ubl_version": "2.1",
            "customization_id": "urn:peppol:pint:billing-1@sg-1",
            "profile_id": "urn:peppol:pint:billing-1@sg-1",
            "document_id": "INV-001",
            "issue_date": "2026-03-09",
            "document_type": "INVOICE",
            "currency": "SGD",
            "tax_currency": "SGD",
            "supplier": {
                "name": "Test Org",
                "uen": "202312345A",
                "address": {"street": "123 Main St", "city": "Singapore", "country": "SG"},
            },
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

        xml_string = service.generate_invoice_xml(mapped_data)

        # Check AccountingSupplierParty
        assert "AccountingSupplierParty" in xml_string

    def test_calculate_xml_hash(self):
        """Test XML hash calculation."""
        from apps.peppol.services.xml_generator_service import XMLGeneratorService

        service = XMLGeneratorService()
        xml_string = '<?xml version="1.0"?><Invoice><ID>TEST</ID></Invoice>'

        hash1 = service.calculate_xml_hash(xml_string)
        hash2 = service.calculate_xml_hash(xml_string)

        # Hash should be 64 characters (SHA-256)
        assert len(hash1) == 64
        # Same XML should produce same hash
        assert hash1 == hash2

    def test_xml_hash_consistency(self):
        """Test hash is consistent for same content."""
        from apps.peppol.services.xml_generator_service import XMLGeneratorService

        service = XMLGeneratorService()

        xml1 = '<?xml version="1.0"?><Invoice><ID>001</ID></Invoice>'
        xml2 = '<?xml version="1.0"?><Invoice><ID>001</ID></Invoice>'

        hash1 = service.calculate_xml_hash(xml1)
        hash2 = service.calculate_xml_hash(xml2)

        assert hash1 == hash2

    def test_calculate_xml_hash_different_content(self):
        """Test different XML produces different hashes."""
        from apps.peppol.services.xml_generator_service import XMLGeneratorService

        service = XMLGeneratorService()

        xml1 = '<?xml version="1.0"?><Invoice><ID>001</ID></Invoice>'
        xml2 = '<?xml version="1.0"?><Invoice><ID>002</ID></Invoice>'

        hash1 = service.calculate_xml_hash(xml1)
        hash2 = service.calculate_xml_hash(xml2)

        assert hash1 != hash2
