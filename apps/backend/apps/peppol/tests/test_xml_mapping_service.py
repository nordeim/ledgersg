"""
TDD Tests for Phase 2 Task 2.2: XML Mapping Service
Tests mapping InvoiceDocument to UBL 2.1 data structure.
"""

import pytest
from decimal import Decimal
from datetime import date, timedelta
from uuid import uuid4


@pytest.mark.django_db
class TestXMLMappingService:
    """Test XML mapping from InvoiceDocument to UBL 2.1."""

    def test_service_can_be_imported(self):
        """Test that XMLMappingService can be imported."""
        from apps.peppol.services.xml_mapping_service import XMLMappingService

        assert XMLMappingService is not None

    def test_service_has_map_invoice_method(self):
        """Test that service has map_invoice_to_ubl method."""
        from apps.peppol.services.xml_mapping_service import XMLMappingService

        assert hasattr(XMLMappingService, "map_invoice_to_ubl")
        assert callable(getattr(XMLMappingService, "map_invoice_to_ubl"))

    def test_service_has_tax_category_mapping(self):
        """Test that service has tax category mapping."""
        from apps.peppol.services.xml_mapping_service import XMLMappingService

        assert hasattr(XMLMappingService, "TAX_CATEGORY_MAP")
        assert "SR" in XMLMappingService.TAX_CATEGORY_MAP
        assert XMLMappingService.TAX_CATEGORY_MAP["SR"] == "S"

    def test_service_has_validation_method(self):
        """Test that service has _validate_peppol_requirements method."""
        from apps.peppol.services.xml_mapping_service import XMLMappingService

        assert hasattr(XMLMappingService, "_validate_peppol_requirements")

    def test_service_has_address_mapping_method(self):
        """Test that service has address mapping methods."""
        from apps.peppol.services.xml_mapping_service import XMLMappingService

        assert hasattr(XMLMappingService, "_map_supplier")
        assert hasattr(XMLMappingService, "_map_customer")
