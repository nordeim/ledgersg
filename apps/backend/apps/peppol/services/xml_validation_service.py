"""
XML Validation Service for InvoiceNow/Peppol integration.

Validates UBL 2.1 XML against XSD schemas.

P14/X-1 — hardened parsing: the validation path accepts candidate UBL XML
from the outside world, so EVERY parse (schemas and candidate documents)
uses the shared hardened parser: no entity resolution (XXE), no network
(SSRF), no DTD loading, no huge trees (billion-laughs). lxml does not
expose its parser flags for introspection, so `_HARDENED_PARSER_FLAGS`
is the single source of truth for the policy — the configuration gate
asserts the constant.
"""

from typing import Any, Dict, List  # noqa: UP006 — Dict matches the codebase idiom

from lxml import etree

# P14/X-1: the parser policy (the knobs, asserted by the configuration gate —
# lxml.etree.XMLParser does not expose its construction flags for reading).
_HARDENED_PARSER_FLAGS: Dict[str, Any] = {
    "resolve_entities": False,
    "no_network": True,
    "load_dtd": False,
    "huge_tree": False,
}


class XMLValidationService:
    """
    Validates UBL 2.1 XML against XSD schemas.

    This service provides XML validation using lxml's XMLSchema support.
    Validates both Invoice and CreditNote XML documents.
    """

    # Schema file paths (relative to Django project root)
    INVOICE_SCHEMA_PATH = "apps/peppol/schemas/ubl-Invoice.xsd"
    CREDIT_NOTE_SCHEMA_PATH = "apps/peppol/schemas/ubl-CreditNote.xsd"

    def __init__(self):
        """Initialize with schema loading."""
        self._invoice_schema = None
        self._credit_note_schema = None
        self._load_schemas()

    @staticmethod
    def _hardened_parser() -> etree.XMLParser:
        """The shared hardened parser (P14/X-1) — built from
        `_HARDENED_PARSER_FLAGS`, the single policy constant."""
        return etree.XMLParser(**_HARDENED_PARSER_FLAGS)

    def _load_schemas(self):
        """Load XSD schemas."""
        # Load Invoice schema
        try:
            schema_doc = etree.parse(
                self.INVOICE_SCHEMA_PATH, self._hardened_parser()
            )
            self._invoice_schema = etree.XMLSchema(schema_doc)
        except Exception:
            # Schema loading failed
            pass

        # Load CreditNote schema
        try:
            schema_doc = etree.parse(
                self.CREDIT_NOTE_SCHEMA_PATH, self._hardened_parser()
            )
            self._credit_note_schema = etree.XMLSchema(schema_doc)
        except Exception:
            # Schema loading failed
            pass

    def _parse_xml(self, xml_string: str):
        """
        Parse XML safely.

        Args:
            xml_string: XML content as string

        Returns:
            Tuple of (xml_doc, error) where xml_doc is None on error
        """
        try:
            xml_doc = etree.fromstring(
                xml_string.encode("utf-8"), self._hardened_parser()
            )
            return xml_doc, None
        except etree.XMLSyntaxError as e:
            return None, str(e)
        except Exception as e:
            return None, str(e)

    def _validate_xsd(self, xml_doc: etree.Element, schema) -> List[Dict[str, Any]]:
        """
        Validate XML against XSD schema.

        Args:
            xml_doc: Parsed XML document
            schema: XMLSchema object

        Returns:
            List of error dictionaries
        """
        if schema is None:
            # P9/S-3: fail CLOSED. A schema that failed to load must never
            # validate silently — the pre-P9 branch returned [] (valid),
            # inverting the Peppol path's posture exactly when it mattered.
            return [
                {
                    "path": "/",
                    "message": (
                        "XSD schema could not be loaded — validation "
                        "unavailable; refusing to pass the document."
                    ),
                }
            ]

        errors = []

        try:
            is_valid = schema.validate(xml_doc)
            if not is_valid:
                for error in schema.error_log:
                    errors.append(
                        {
                            "message": error.message,
                            "line": error.line,
                            "column": error.column,
                        }
                    )
        except Exception as e:
            errors.append(
                {
                    "message": str(e),
                    "line": 0,
                    "column": 0,
                }
            )

        return errors

    def _get_document_type(self, xml_doc: etree.Element) -> str:
        """
        Detect document type from XML.

        Args:
            xml_doc: Parsed XML document

        Returns:
            Document type string
        """
        if xml_doc is None:
            return "UNKNOWN"

        tag = xml_doc.tag.lower()
        if "creditnote" in tag:
            return "CREDIT_NOTE"
        elif "invoice" in tag:
            return "INVOICE"
        return "UNKNOWN"

    def validate_invoice_xml(self, xml_string: str) -> Dict[str, Any]:
        """
        Validate Invoice XML.

        Args:
            xml_string: XML content as string

        Returns:
            Validation result dictionary
        """
        result = {
            "is_valid": False,
            "document_type": "INVOICE",
            "schema_errors": [],
            "schematron_errors": [],
        }

        if not xml_string:
            result["schema_errors"].append(
                {
                    "message": "XML string is empty",
                    "line": 0,
                    "column": 0,
                }
            )
            return result

        # Parse XML
        xml_doc, parse_error = self._parse_xml(xml_string)
        if xml_doc is None:
            result["schema_errors"].append(
                {
                    "message": f"XML parsing error: {parse_error}",
                    "line": 0,
                    "column": 0,
                }
            )
            return result

        # Detect document type
        result["document_type"] = self._get_document_type(xml_doc)

        # Validate against XSD
        result["schema_errors"] = self._validate_xsd(xml_doc, self._invoice_schema)

        # Set is_valid based on errors
        result["is_valid"] = len(result["schema_errors"]) == 0

        return result

    def validate_credit_note_xml(self, xml_string: str) -> Dict[str, Any]:
        """
        Validate CreditNote XML.

        Args:
            xml_string: XML content as string

        Returns:
            Validation result dictionary
        """
        result = {
            "is_valid": False,
            "document_type": "CREDIT_NOTE",
            "schema_errors": [],
            "schematron_errors": [],
        }

        if not xml_string:
            result["schema_errors"].append(
                {
                    "message": "XML string is empty",
                    "line": 0,
                    "column": 0,
                }
            )
            return result

        # Parse XML
        xml_doc, parse_error = self._parse_xml(xml_string)
        if xml_doc is None:
            result["schema_errors"].append(
                {
                    "message": f"XML parsing error: {parse_error}",
                    "line": 0,
                    "column": 0,
                }
            )
            return result

        # Detect document type
        result["document_type"] = self._get_document_type(xml_doc)

        # Validate against XSD
        result["schema_errors"] = self._validate_xsd(xml_doc, self._credit_note_schema)

        # Set is_valid based on errors
        result["is_valid"] = len(result["schema_errors"]) == 0

        return result

    def _validate_schematron(self, xml_doc: etree.Element) -> List[Dict[str, Any]]:
        """
        Placeholder for Schematron validation.

        Args:
            xml_doc: Parsed XML document

        Returns:
            List of Schematron errors (empty for now)
        """
        # Schematron validation would require additional setup
        # This is a placeholder for future implementation
        return []
