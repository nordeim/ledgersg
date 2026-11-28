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

from lxml import etree, isoschematron

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
    SCHEMATRON_SCHEMA_PATH = "apps/peppol/schemas/PINT-UBL-validation.sch"

    def __init__(self):
        """Initialize with schema loading."""
        self._invoice_schema = None
        self._credit_note_schema = None
        self._schematron_schema = None
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

        # Load the Schematron business-rule schema (P35/BE-P35-H1(b))
        try:
            sch_doc = etree.parse(
                self.SCHEMATRON_SCHEMA_PATH, self._hardened_parser()
            )
            self._schematron_schema = isoschematron.Schematron(
                sch_doc, store_report=True
            )
        except Exception:
            # Load failure -> the fail-closed posture in
            # _validate_schematron reports it, never silence (the P9/S-3
            # contract mirrored one layer up).
            self._schematron_schema = None

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

        # P35/BE-P35-H1(b): the business-rule layer — the cross-element
        # truths the XSD cannot express (the amount-currencyID consistency
        # sweep, the currency-code shape, the presence floors).
        result["schematron_errors"] = self._validate_schematron(xml_doc)

        # Set is_valid based on BOTH error lists: a document that passes
        # the XSD but fails a business rule is NOT valid — the transmission
        # must not send it.
        result["is_valid"] = (
            len(result["schema_errors"]) == 0
            and len(result["schematron_errors"]) == 0
        )

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

        # P35/BE-P35-H1(b): the business-rule layer on the credit-note path
        # too — the same Schematron rules cover both roots.
        result["schematron_errors"] = self._validate_schematron(xml_doc)

        result["is_valid"] = (
            len(result["schema_errors"]) == 0
            and len(result["schematron_errors"]) == 0
        )

        return result

    def _validate_schematron(self, xml_doc: etree.Element) -> List[Dict[str, Any]]:
        """
        Validate the PINT-SG business rules (P35/BE-P35-H1).

        The layer ABOVE the XSD: the cross-element truths a structural
        schema cannot express — every amount's currencyID must equal the
        document's DocumentCurrencyCode (the P33 truth), the currency
        code's shape, the presence floors. Pre-P35 this method was a
        never-called placeholder returning [] and the .sch artefact was
        unparseable (wrong namespace + an unsupported xslt2 binding).

        Args:
            xml_doc: Parsed XML document

        Returns:
            List of Schematron error dictionaries (message + location)
        """
        if self._schematron_schema is None:
            # The P9/S-3 posture mirrored one layer up: a .sch that failed
            # to load must never validate silently — refuse to pass the
            # document, exactly as a failed XSD load does.
            return [
                {
                    "message": (
                        "Schematron schema could not be loaded — business-rule "
                        "validation unavailable; refusing to pass the document."
                    ),
                    "location": "/",
                }
            ]

        errors: list[dict[str, Any]] = []
        try:
            is_valid = self._schematron_schema.validate(xml_doc)
            if not is_valid:
                svrl_ns = "http://purl.oclc.org/dsdl/svrl"
                report = self._schematron_schema.validation_report
                for failed_assert in report.iter(f"{{{svrl_ns}}}failed-assert"):
                    message = "".join(failed_assert.itertext()).strip()
                    errors.append(
                        {
                            "message": message,
                            "location": failed_assert.get("location") or "/",
                        }
                    )
        except Exception as e:
            errors.append(
                {
                    "message": f"Schematron validation error: {e}",
                    "location": "/",
                }
            )

        return errors
