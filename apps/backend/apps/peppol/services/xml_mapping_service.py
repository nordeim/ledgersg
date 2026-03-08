"""
XML Mapping Service for InvoiceNow/Peppol integration.

Maps LedgerSG InvoiceDocument to UBL 2.1 PINT-SG data structure.
"""

from typing import Dict, Any, Optional
from decimal import Decimal
from datetime import date


class XMLMappingService:
    """
    Maps InvoiceDocument to UBL 2.1 PINT-SG data structure.

    This service converts LedgerSG invoice data to a dictionary structure
    that can be used to generate UBL 2.1 XML for Peppol transmission.
    """

    # Singapore tax code to UBL tax category mapping
    # Based on PINT-SG specification
    TAX_CATEGORY_MAP = {
        "SR": "S",  # Standard-rated (9%)
        "ZR": "Z",  # Zero-rated (0%)
        "ES": "E",  # Exempt
        "OS": "O",  # Out-of-scope
        "TX": "S",  # Taxable purchase (maps to Standard)
        "BL": "K",  # Blocked input tax
        "RS": "K",  # Reverse charge (maps to Blocked)
    }

    @staticmethod
    def map_invoice_to_ubl(invoice) -> Dict[str, Any]:
        """
        Convert InvoiceDocument to UBL 2.1 data structure.

        Args:
            invoice: InvoiceDocument instance

        Returns:
            Dictionary containing UBL 2.1 mapped data

        Raises:
            ValueError: If required Peppol fields are missing
        """
        from apps.core.models import Organisation, Contact, TaxCode

        # Get related objects
        org = invoice.org
        contact = invoice.contact

        # Validate mandatory fields
        XMLMappingService._validate_peppol_requirements(invoice, org, contact)

        # Map to UBL structure
        return {
            # Document Header
            "ubl_version": "2.1",
            "customization_id": "urn:peppol:pint:billing-1@sg-1",
            "profile_id": "urn:peppol:pint:billing-1@sg-1",
            "document_id": invoice.document_number,
            "issue_date": invoice.issue_date.isoformat() if invoice.issue_date else None,
            "due_date": invoice.due_date.isoformat() if invoice.due_date else None,
            "document_type": "CREDIT_NOTE"
            if invoice.document_type == "SALES_CREDIT_NOTE"
            else "INVOICE",
            # Currency
            "currency": invoice.currency or "SGD",
            "tax_currency": "SGD",
            # Supplier (AccountingSupplierParty)
            "supplier": XMLMappingService._map_supplier(org),
            # Customer (AccountingCustomerParty)
            "customer": XMLMappingService._map_customer(contact),
            # Payment Terms
            "payment_terms": XMLMappingService._map_payment_terms(invoice),
            # Tax Totals
            "tax_totals": XMLMappingService._calculate_tax_totals(invoice),
            # Monetary Totals
            "monetary_totals": {
                "line_extension_amount": str(invoice.total_excl or 0),
                "tax_exclusive_amount": str(invoice.total_excl or 0),
                "tax_inclusive_amount": str(invoice.total_incl or 0),
                "payable_amount": str((invoice.total_incl or 0) - (invoice.amount_paid or 0)),
                "prepaid_amount": str(invoice.amount_paid or 0),
            },
            # Invoice Lines
            "lines": [XMLMappingService._map_line(line) for line in invoice.lines.all()],
        }

    @staticmethod
    def _validate_peppol_requirements(invoice, org, contact) -> None:
        """
        Validate mandatory fields for Peppol compliance.

        Args:
            invoice: InvoiceDocument instance
            org: Organisation instance
            contact: Contact instance

        Raises:
            ValueError: If required fields are missing
        """
        errors = []

        # Supplier UEN is required
        if not org.uen:
            errors.append("Supplier UEN is required for Peppol transmission")

        # GST registration number if GST-registered
        if org.gst_registered and not org.gst_reg_number:
            errors.append("GST registration number required for GST-registered supplier")

        # Document number is required
        if not invoice.document_number:
            errors.append("Document number is required")

        # Issue date is required
        if not invoice.issue_date:
            errors.append("Issue date is required")

        if errors:
            raise ValueError("; ".join(errors))

    @staticmethod
    def _map_supplier(org) -> Dict[str, Any]:
        """
        Map Organisation to supplier party structure.

        Args:
            org: Organisation instance

        Returns:
            Supplier dictionary for UBL
        """
        return {
            "name": org.legal_name or org.name,
            "uen": org.uen,
            "gst_registration": org.gst_reg_number if org.gst_registered else None,
            "address": {
                "street": org.address_line_1 or "",
                "street2": org.address_line_2 or "",
                "city": org.city or "Singapore",
                "postal_code": org.postal_code or "",
                "country": org.country or "SG",
            },
            "peppol_id": org.peppol_participant_id or f"0195:{org.uen}" if org.uen else None,
        }

    @staticmethod
    def _map_customer(contact) -> Dict[str, Any]:
        """
        Map Contact to customer party structure.

        Args:
            contact: Contact instance

        Returns:
            Customer dictionary for UBL
        """
        return {
            "name": contact.legal_name or contact.name,
            "uen": contact.uen,
            "gst_registration": contact.gst_reg_number if contact.is_gst_registered else None,
            "address": {
                "street": contact.address_line_1 or "",
                "street2": contact.address_line_2 or "",
                "city": contact.city or "Singapore",
                "postal_code": contact.postal_code or "",
                "country": contact.country or "SG",
            },
            "peppol_id": contact.peppol_id,
        }

    @staticmethod
    def _map_payment_terms(invoice) -> Dict[str, Any]:
        """
        Map invoice payment terms.

        Args:
            invoice: InvoiceDocument instance

        Returns:
            Payment terms dictionary
        """
        return {
            "payment_due_date": invoice.due_date.isoformat() if invoice.due_date else None,
            "payment_means": "BANK_TRANSFER",  # Default, can be customized
        }

    @staticmethod
    def _calculate_tax_totals(invoice) -> Dict[str, Any]:
        """
        Calculate tax totals grouped by tax rate.

        Args:
            invoice: InvoiceDocument instance

        Returns:
            Tax totals dictionary with categories
        """
        # Group by tax code
        tax_by_code = {}

        for line in invoice.lines.all():
            # Skip BCRS deposit lines
            if line.is_bcrs_deposit:
                continue

            tax_code = line.tax_code
            code_str = tax_code.code if tax_code else "OS"
            rate = float(tax_code.rate) if tax_code else 0.0

            if code_str not in tax_by_code:
                tax_by_code[code_str] = {
                    "code": code_str,
                    "rate": rate,
                    "taxable_amount": Decimal("0"),
                    "tax_amount": Decimal("0"),
                    "category": XMLMappingService._get_tax_category(tax_code),
                }

            tax_by_code[code_str]["taxable_amount"] += line.line_amount or 0
            tax_by_code[code_str]["tax_amount"] += line.gst_amount or 0

        # Build tax categories list
        tax_categories = [
            {
                "code": data["code"],
                "rate": data["rate"],
                "taxable_amount": str(data["taxable_amount"]),
                "tax_amount": str(data["tax_amount"]),
                "category": data["category"],
            }
            for data in tax_by_code.values()
        ]

        return {
            "tax_categories": tax_categories,
            "total_tax_amount": str(invoice.gst_total or 0),
        }

    @staticmethod
    def _map_line(line) -> Dict[str, Any]:
        """
        Map invoice line to UBL format.

        Args:
            line: InvoiceLine instance

        Returns:
            Line dictionary for UBL
        """
        tax_code = line.tax_code

        return {
            "line_id": str(line.line_number),
            "description": line.description or "",
            "quantity": str(line.quantity or 1),
            "unit_code": "EA",  # Default to Each
            "unit_price": str(line.unit_price or 0),
            "line_extension_amount": str(line.line_amount or 0),
            "tax_amount": str(line.gst_amount or 0),
            "tax_rate": str(line.tax_rate or 0),
            "tax_category": XMLMappingService._get_tax_category(tax_code),
            "is_bcrs_deposit": line.is_bcrs_deposit,
        }

    @staticmethod
    def _get_tax_category(tax_code) -> str:
        """
        Map Singapore tax code to UBL tax category.

        Args:
            tax_code: TaxCode instance or None

        Returns:
            UBL tax category code (S, Z, E, O, K)
        """
        if not tax_code:
            return "O"  # Out of scope

        return XMLMappingService.TAX_CATEGORY_MAP.get(tax_code.code, "O")
