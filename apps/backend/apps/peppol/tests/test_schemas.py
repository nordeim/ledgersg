"""
TDD Tests for Phase 2 Task 2.1: XML Schemas
Tests that UBL 2.1 and PINT-SG schemas are downloaded and accessible.
"""

import pytest
import os
from pathlib import Path


# Get the project root directory (Ledger-SG)
# Path: apps/backend/apps/peppol/tests/ -> 6 levels up to Ledger-SG
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent.parent.parent
SCHEMAS_DIR = PROJECT_ROOT / "apps" / "backend" / "apps" / "peppol" / "schemas"


class TestSchemas:
    """Test XML schema files are downloaded and accessible."""

    def test_schemas_directory_exists(self):
        """Test that peppol/schemas directory was created."""
        assert SCHEMAS_DIR.exists(), f"Schemas directory not found: {SCHEMAS_DIR}"
        assert SCHEMAS_DIR.is_dir(), f"Path is not a directory: {SCHEMAS_DIR}"

    def test_ubl_invoice_xsd_exists(self):
        """Test that UBL Invoice XSD schema was downloaded."""
        invoice_xsd = SCHEMAS_DIR / "ubl-Invoice.xsd"
        assert invoice_xsd.exists(), "UBL Invoice XSD schema not found"
        assert invoice_xsd.stat().st_size > 0, "UBL Invoice XSD is empty"

    def test_ubl_creditnote_xsd_exists(self):
        """Test that UBL CreditNote XSD schema was downloaded."""
        creditnote_xsd = SCHEMAS_DIR / "ubl-CreditNote.xsd"
        assert creditnote_xsd.exists(), "UBL CreditNote XSD schema not found"
        assert creditnote_xsd.stat().st_size > 0, "UBL CreditNote XSD is empty"

    def test_pint_schematron_exists(self):
        """Test that PINT-SG Schematron validation rules were downloaded."""
        schematron = SCHEMAS_DIR / "PINT-UBL-validation.sch"
        assert schematron.exists(), "PINT-SG Schematron rules not found"
        assert schematron.stat().st_size > 0, "PINT-SG Schematron is empty"

    def test_ubl_invoice_xsd_is_valid_xml(self):
        """Test that UBL Invoice XSD is valid XML."""
        pytest.importorskip("lxml")
        from lxml import etree

        invoice_xsd = SCHEMAS_DIR / "ubl-Invoice.xsd"
        if not invoice_xsd.exists():
            pytest.skip("UBL Invoice XSD not downloaded yet")

        try:
            etree.parse(str(invoice_xsd))
        except etree.XMLSyntaxError as e:
            pytest.fail(f"UBL Invoice XSD is not valid XML: {e}")

    def test_ubl_creditnote_xsd_is_valid_xml(self):
        """Test that UBL CreditNote XSD is valid XML."""
        pytest.importorskip("lxml")
        from lxml import etree

        creditnote_xsd = SCHEMAS_DIR / "ubl-CreditNote.xsd"
        if not creditnote_xsd.exists():
            pytest.skip("UBL CreditNote XSD not downloaded yet")

        try:
            etree.parse(str(creditnote_xsd))
        except etree.XMLSyntaxError as e:
            pytest.fail(f"UBL CreditNote XSD is not valid XML: {e}")
