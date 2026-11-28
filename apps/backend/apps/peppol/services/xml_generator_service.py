"""
XML Generator Service for InvoiceNow/Peppol integration.

Generates UBL 2.1 XML from mapped data structure.
"""

import hashlib
from decimal import Decimal
from typing import Any, Dict

from lxml import etree


def _format_percent_text(rate) -> str:
    """Format a tax rate (0-1 scale) as the cbc:Percent canonical form.

    P36/BE-P36-L1: the pre-P36 formatting went through a float —
    str(float(Decimal('0.07')) * 100) emits "7.000000000000001", a float
    artifact in a financial document's stated tax rate. This formatter
    goes through Decimal (tolerating both Decimal inputs from the mapper
    and float inputs from hand-built test payloads) and emits the
    normalized plain-notation form ("9", "7", "8.75", "0") — the 'f'
    format spec avoids normalize's 1E+2 exponent trap on integral values.
    """
    return format((Decimal(str(rate)) * 100).normalize(), "f")


class XMLGeneratorService:
    """
    Generates UBL 2.1 PINT-SG compliant XML from mapped data.

    This service converts the mapped dictionary from XMLMappingService
    into valid UBL 2.1 XML for Peppol transmission.
    """

    # UBL 2.1 namespaces
    NAMESPACE_UBL = "urn:oasis:names:specification:ubl:schema:xsd:Invoice-2"
    NAMESPACE_CAC = "urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2"
    NAMESPACE_CBC = "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"

    # CreditNote namespace
    NAMESPACE_CREDIT_NOTE = "urn:oasis:names:specification:ubl:schema:xsd:CreditNote-2"

    def __init__(self):
        """Initialize the XML generator service."""
        pass

    def generate_invoice_xml(self, mapped_data: Dict[str, Any]) -> str:
        """
        Generate UBL 2.1 Invoice XML from mapped data.

        Args:
            mapped_data: Dictionary from XMLMappingService

        Returns:
            XML string (UTF-8 encoded)
        """
        # Create root Invoice element
        nsmap = {
            None: self.NAMESPACE_UBL,
            "cac": self.NAMESPACE_CAC,
            "cbc": self.NAMESPACE_CBC,
        }

        invoice = etree.Element(f"{{{self.NAMESPACE_UBL}}}Invoice", nsmap=nsmap)

        # Document Header
        self._add_element(invoice, "UBLVersionID", mapped_data.get("ubl_version"))
        self._add_element(invoice, "CustomizationID", mapped_data.get("customization_id"))
        self._add_element(invoice, "ProfileID", mapped_data.get("profile_id"))
        self._add_element(invoice, "ID", mapped_data.get("document_id"))
        self._add_element(invoice, "IssueDate", mapped_data.get("issue_date"))

        if mapped_data.get("due_date"):
            self._add_element(invoice, "DueDate", mapped_data["due_date"])

        # Document type code (380 = Invoice)
        self._add_element(invoice, "InvoiceTypeCode", "380")

        # Currency
        self._add_element(invoice, "DocumentCurrencyCode", mapped_data.get("currency"))
        # P36/BE-P36-H2: TaxCurrencyCode exists to declare a DIFFERENT tax
        # currency; the tax is computed in the document currency, so the
        # element is omitted when equal (the pre-P36 unconditional emission
        # put a redundant SGD declaration on every SGD document and a FALSE
        # one on every non-SGD document).
        tax_currency = mapped_data.get("tax_currency")
        if tax_currency and tax_currency != (mapped_data.get("currency") or "SGD"):
            self._add_element(invoice, "TaxCurrencyCode", tax_currency)

        # P33/BE-P33-H1: every amount element's currencyID carries the
        # DOCUMENT currency — the mapper already sends it (`invoice.currency
        # or "SGD"`); the hardcoded "SGD" produced internally inconsistent
        # UBL on any non-SGD document (DocumentCurrencyCode=USD beside
        # currencyID="SGD" amounts — a Peppol PINT-SG validation hazard).
        # The defensive fallback keeps hand-built payloads honest.
        currency = mapped_data.get("currency") or "SGD"

        # Supplier (AccountingSupplierParty)
        if mapped_data.get("supplier"):
            supplier_party = self._create_supplier_party(mapped_data["supplier"])
            invoice.append(supplier_party)

        # Customer (AccountingCustomerParty)
        if mapped_data.get("customer"):
            customer_party = self._create_customer_party(mapped_data["customer"])
            invoice.append(customer_party)

        # Payment Terms
        if mapped_data.get("payment_terms"):
            payment_terms = self._create_payment_terms(mapped_data["payment_terms"])
            invoice.append(payment_terms)

        # Tax Totals
        if mapped_data.get("tax_totals"):
            tax_total = self._create_tax_total(mapped_data["tax_totals"], currency)
            invoice.append(tax_total)

        # Monetary Totals
        if mapped_data.get("monetary_totals"):
            monetary_total = self._create_monetary_total(mapped_data["monetary_totals"], currency)
            invoice.append(monetary_total)

        # Invoice Lines
        if mapped_data.get("lines"):
            for line_data in mapped_data["lines"]:
                line = self._create_invoice_line(line_data, currency)
                invoice.append(line)

        # Generate XML string
        xml_string = etree.tostring(
            invoice, pretty_print=True, encoding="UTF-8", xml_declaration=True
        )

        return xml_string.decode("utf-8")

    def generate_credit_note_xml(self, mapped_data: Dict[str, Any]) -> str:
        """
        Generate UBL 2.1 CreditNote XML from mapped data.

        P34/BE-P34-H1(a): the full PINT-SG structure — the pre-P34
        generator emitted header-only UBL while the mapper already
        supplies the parties, payment terms, tax totals, monetary totals
        and lines for every document type; a transmitted credit note
        carried no parties, no amounts and no lines.

        Args:
            mapped_data: Dictionary from XMLMappingService

        Returns:
            XML string (UTF-8 encoded)
        """
        # Create root CreditNote element
        nsmap = {
            None: self.NAMESPACE_CREDIT_NOTE,
            "cac": self.NAMESPACE_CAC,
            "cbc": self.NAMESPACE_CBC,
        }

        credit_note = etree.Element(f"{{{self.NAMESPACE_CREDIT_NOTE}}}CreditNote", nsmap=nsmap)

        # Document Header
        self._add_element(credit_note, "UBLVersionID", mapped_data.get("ubl_version"))
        self._add_element(credit_note, "CustomizationID", mapped_data.get("customization_id"))
        self._add_element(credit_note, "ProfileID", mapped_data.get("profile_id"))
        self._add_element(credit_note, "ID", mapped_data.get("document_id"))
        self._add_element(credit_note, "IssueDate", mapped_data.get("issue_date"))
        if mapped_data.get("due_date"):
            self._add_element(credit_note, "DueDate", mapped_data["due_date"])

        # Document type code (381 = Credit Note)
        self._add_element(credit_note, "CreditNoteTypeCode", "381")

        # Currency
        self._add_element(credit_note, "DocumentCurrencyCode", mapped_data.get("currency"))
        # P36/BE-P36-H2: the same guarded emission on the credit-note path.
        tax_currency = mapped_data.get("tax_currency")
        if tax_currency and tax_currency != (mapped_data.get("currency") or "SGD"):
            self._add_element(credit_note, "TaxCurrencyCode", tax_currency)

        # P34 carries the P33 currency truth: every amount element's
        # currencyID carries the DOCUMENT currency, never a hardcoded
        # denomination.
        currency = mapped_data.get("currency") or "SGD"

        # Supplier (AccountingSupplierParty)
        if mapped_data.get("supplier"):
            supplier_party = self._create_supplier_party(mapped_data["supplier"])
            credit_note.append(supplier_party)

        # Customer (AccountingCustomerParty)
        if mapped_data.get("customer"):
            customer_party = self._create_customer_party(mapped_data["customer"])
            credit_note.append(customer_party)

        # Payment Terms
        if mapped_data.get("payment_terms"):
            payment_terms = self._create_payment_terms(mapped_data["payment_terms"])
            credit_note.append(payment_terms)

        # Tax Totals
        if mapped_data.get("tax_totals"):
            tax_total = self._create_tax_total(mapped_data["tax_totals"], currency)
            credit_note.append(tax_total)

        # Monetary Totals
        if mapped_data.get("monetary_totals"):
            monetary_total = self._create_monetary_total(
                mapped_data["monetary_totals"], currency
            )
            credit_note.append(monetary_total)

        # Credit Note Lines — the UBL 2.1 CreditNoteLine (CreditedQuantity),
        # never an InvoiceLine
        if mapped_data.get("lines"):
            for line_data in mapped_data["lines"]:
                line = self._create_credit_note_line(line_data, currency)
                credit_note.append(line)

        # Generate XML string
        xml_string = etree.tostring(
            credit_note, pretty_print=True, encoding="UTF-8", xml_declaration=True
        )

        return xml_string.decode("utf-8")

    def calculate_xml_hash(self, xml_string: str) -> str:
        """
        Calculate SHA-256 hash of XML payload.

        Args:
            xml_string: XML content as string

        Returns:
            64-character hex string (SHA-256)
        """
        return hashlib.sha256(xml_string.encode("utf-8")).hexdigest()

    def _add_element(
        self, parent: etree.Element, tag_name: str, value: Any, namespace: str = "cbc"
    ) -> None:
        """
        Add a namespaced element to XML tree.

        Args:
            parent: Parent element
            tag_name: Tag name (without namespace)
            value: Element value (will be converted to string)
            namespace: Namespace prefix ('cbc', 'cac', or 'ubl')
        """
        if value is None:
            return

        # Get namespace URI
        if namespace == "ubl":
            ns = self.NAMESPACE_UBL
        elif namespace == "cac":
            ns = self.NAMESPACE_CAC
        else:  # cbc
            ns = self.NAMESPACE_CBC

        # Create element with namespace
        element = etree.SubElement(parent, f"{{{ns}}}{tag_name}")
        element.text = str(value)

    def _create_supplier_party(self, supplier_data: Dict[str, Any]) -> etree.Element:
        """
        Create AccountingSupplierParty element.

        Args:
            supplier_data: Supplier dictionary from mapped data

        Returns:
            AccountingSupplierParty element
        """
        # Create AccountingSupplierParty
        party = etree.Element(f"{{{self.NAMESPACE_CAC}}}AccountingSupplierParty")

        # Party element
        party_element = etree.SubElement(party, f"{{{self.NAMESPACE_CAC}}}Party")

        # Party name
        if supplier_data.get("name"):
            party_name = etree.SubElement(party_element, f"{{{self.NAMESPACE_CAC}}}PartyName")
            name = etree.SubElement(party_name, f"{{{self.NAMESPACE_CBC}}}Name")
            name.text = supplier_data["name"]

        # Party legal entity (for UEN)
        if supplier_data.get("uen"):
            legal_entity = etree.SubElement(
                party_element, f"{{{self.NAMESPACE_CAC}}}PartyLegalEntity"
            )

            # Registration name
            reg_name = etree.SubElement(legal_entity, f"{{{self.NAMESPACE_CBC}}}RegistrationName")
            reg_name.text = supplier_data.get("name", "")

            # Company ID (UEN)
            company_id = etree.SubElement(legal_entity, f"{{{self.NAMESPACE_CBC}}}CompanyID")
            company_id.text = supplier_data["uen"]

            # Company ID scheme
            company_id.set("schemeID", "0195")  # Singapore UEN scheme

        # Postal address
        if supplier_data.get("address"):
            address = self._create_address(supplier_data["address"])
            party_element.append(address)

        return party

    def _create_customer_party(self, customer_data: Dict[str, Any]) -> etree.Element:
        """
        Create AccountingCustomerParty element.

        Args:
            customer_data: Customer dictionary from mapped data

        Returns:
            AccountingCustomerParty element
        """
        # Create AccountingCustomerParty
        party = etree.Element(f"{{{self.NAMESPACE_CAC}}}AccountingCustomerParty")

        # Party element
        party_element = etree.SubElement(party, f"{{{self.NAMESPACE_CAC}}}Party")

        # Party name
        if customer_data.get("name"):
            party_name = etree.SubElement(party_element, f"{{{self.NAMESPACE_CAC}}}PartyName")
            name = etree.SubElement(party_name, f"{{{self.NAMESPACE_CBC}}}Name")
            name.text = customer_data["name"]

        # Party legal entity
        if customer_data.get("uen"):
            legal_entity = etree.SubElement(
                party_element, f"{{{self.NAMESPACE_CAC}}}PartyLegalEntity"
            )

            # Registration name
            reg_name = etree.SubElement(legal_entity, f"{{{self.NAMESPACE_CBC}}}RegistrationName")
            reg_name.text = customer_data.get("name", "")

            # Company ID (UEN)
            company_id = etree.SubElement(legal_entity, f"{{{self.NAMESPACE_CBC}}}CompanyID")
            company_id.text = customer_data["uen"]
            company_id.set("schemeID", "0195")

        # Postal address
        if customer_data.get("address"):
            address = self._create_address(customer_data["address"])
            party_element.append(address)

        return party

    def _create_address(self, address_data: Dict[str, str]) -> etree.Element:
        """
        Create PostalAddress element.

        Args:
            address_data: Address dictionary

        Returns:
            PostalAddress element
        """
        address = etree.Element(f"{{{self.NAMESPACE_CAC}}}PostalAddress")

        # Street name
        if address_data.get("street"):
            street = etree.SubElement(address, f"{{{self.NAMESPACE_CBC}}}StreetName")
            street.text = address_data["street"]

        # Additional street name
        if address_data.get("street2"):
            add_street = etree.SubElement(address, f"{{{self.NAMESPACE_CBC}}}AdditionalStreetName")
            add_street.text = address_data["street2"]

        # City
        if address_data.get("city"):
            city = etree.SubElement(address, f"{{{self.NAMESPACE_CBC}}}CityName")
            city.text = address_data["city"]

        # Postal code
        if address_data.get("postal_code"):
            postal = etree.SubElement(address, f"{{{self.NAMESPACE_CBC}}}PostalZone")
            postal.text = address_data["postal_code"]

        # Country
        if address_data.get("country"):
            country = etree.SubElement(address, f"{{{self.NAMESPACE_CAC}}}Country")
            country_code = etree.SubElement(country, f"{{{self.NAMESPACE_CBC}}}IdentificationCode")
            country_code.text = address_data["country"]

        return address

    def _create_payment_terms(self, payment_data: Dict[str, Any]) -> etree.Element:
        """Create PaymentTerms element."""
        terms = etree.Element(f"{{{self.NAMESPACE_CAC}}}PaymentTerms")

        # Payment due date
        if payment_data.get("payment_due_date"):
            due_date = etree.SubElement(terms, f"{{{self.NAMESPACE_CBC}}}PaymentDueDate")
            due_date.text = payment_data["payment_due_date"]

        return terms

    def _create_tax_total(self, tax_data: Dict[str, Any], currency: str) -> etree.Element:
        """
        Create TaxTotal element.

        Args:
            tax_data: Tax totals dictionary
            currency: the document's currency (P33 — every amount's
                currencyID carries it, never a hardcoded denomination)

        Returns:
            TaxTotal element
        """
        tax_total = etree.Element(f"{{{self.NAMESPACE_CAC}}}TaxTotal")

        # Total tax amount
        if tax_data.get("total_tax_amount"):
            tax_amount = etree.SubElement(tax_total, f"{{{self.NAMESPACE_CBC}}}TaxAmount")
            tax_amount.set("currencyID", currency)
            tax_amount.text = tax_data["total_tax_amount"]

        # Tax subtotals for each category
        for category in tax_data.get("tax_categories", []):
            tax_subtotal = etree.SubElement(tax_total, f"{{{self.NAMESPACE_CAC}}}TaxSubtotal")

            # Taxable amount
            taxable = etree.SubElement(tax_subtotal, f"{{{self.NAMESPACE_CBC}}}TaxableAmount")
            taxable.set("currencyID", currency)
            taxable.text = category.get("taxable_amount", "0.00")

            # Tax amount
            amount = etree.SubElement(tax_subtotal, f"{{{self.NAMESPACE_CBC}}}TaxAmount")
            amount.set("currencyID", currency)
            amount.text = category.get("tax_amount", "0.00")

            # Tax category
            tax_category = etree.SubElement(tax_subtotal, f"{{{self.NAMESPACE_CAC}}}TaxCategory")

            # Category ID
            cat_id = etree.SubElement(tax_category, f"{{{self.NAMESPACE_CBC}}}ID")
            cat_id.text = category.get("category", "S")

            # Percent
            if category.get("rate") is not None:
                percent = etree.SubElement(tax_category, f"{{{self.NAMESPACE_CBC}}}Percent")
                percent.text = _format_percent_text(category["rate"])

        return tax_total

    def _create_monetary_total(self, totals_data: Dict[str, str], currency: str) -> etree.Element:
        """
        Create LegalMonetaryTotal element.

        Args:
            totals_data: Monetary totals dictionary
            currency: the document's currency (P33 — every amount's
                currencyID carries it)

        Returns:
            LegalMonetaryTotal element
        """
        monetary_total = etree.Element(f"{{{self.NAMESPACE_CAC}}}LegalMonetaryTotal")

        # Line extension amount
        if totals_data.get("line_extension_amount"):
            line_ext = etree.SubElement(
                monetary_total, f"{{{self.NAMESPACE_CBC}}}LineExtensionAmount"
            )
            line_ext.set("currencyID", currency)
            line_ext.text = totals_data["line_extension_amount"]

        # Tax exclusive amount
        if totals_data.get("tax_exclusive_amount"):
            tax_exc = etree.SubElement(
                monetary_total, f"{{{self.NAMESPACE_CBC}}}TaxExclusiveAmount"
            )
            tax_exc.set("currencyID", currency)
            tax_exc.text = totals_data["tax_exclusive_amount"]

        # Tax inclusive amount
        if totals_data.get("tax_inclusive_amount"):
            tax_inc = etree.SubElement(
                monetary_total, f"{{{self.NAMESPACE_CBC}}}TaxInclusiveAmount"
            )
            tax_inc.set("currencyID", currency)
            tax_inc.text = totals_data["tax_inclusive_amount"]

        # Payable amount
        if totals_data.get("payable_amount"):
            payable = etree.SubElement(monetary_total, f"{{{self.NAMESPACE_CBC}}}PayableAmount")
            payable.set("currencyID", currency)
            payable.text = totals_data["payable_amount"]

        # Prepaid amount
        if totals_data.get("prepaid_amount"):
            prepaid = etree.SubElement(monetary_total, f"{{{self.NAMESPACE_CBC}}}PrepaidAmount")
            prepaid.set("currencyID", currency)
            prepaid.text = totals_data["prepaid_amount"]

        return monetary_total

    def _create_invoice_line(self, line_data: Dict[str, Any], currency: str) -> etree.Element:
        """
        Create InvoiceLine element.

        Args:
            line_data: Line dictionary from mapped data
            currency: the document's currency (P33 — every amount's
                currencyID carries it)

        Returns:
            InvoiceLine element
        """
        line = etree.Element(f"{{{self.NAMESPACE_CAC}}}InvoiceLine")

        # Line ID
        line_id = etree.SubElement(line, f"{{{self.NAMESPACE_CBC}}}ID")
        line_id.text = line_data.get("line_id", "1")

        # Invoiced quantity
        quantity = etree.SubElement(line, f"{{{self.NAMESPACE_CBC}}}InvoicedQuantity")
        quantity.set("unitCode", line_data.get("unit_code", "EA"))
        quantity.text = line_data.get("quantity", "1")

        # Line extension amount
        ext_amount = etree.SubElement(line, f"{{{self.NAMESPACE_CBC}}}LineExtensionAmount")
        ext_amount.set("currencyID", currency)
        ext_amount.text = line_data.get("line_extension_amount", "0.00")

        # Item
        item = etree.SubElement(line, f"{{{self.NAMESPACE_CAC}}}Item")

        # Description
        if line_data.get("description"):
            desc = etree.SubElement(item, f"{{{self.NAMESPACE_CBC}}}Description")
            desc.text = line_data["description"]

        # Price
        price = etree.SubElement(line, f"{{{self.NAMESPACE_CAC}}}Price")
        price_amount = etree.SubElement(price, f"{{{self.NAMESPACE_CBC}}}PriceAmount")
        price_amount.set("currencyID", currency)
        price_amount.text = line_data.get("unit_price", "0.00")

        return line

    def _create_credit_note_line(self, line_data: dict[str, Any], currency: str) -> etree.Element:
        """
        Create CreditNoteLine element (the UBL 2.1 credit-note line).

        P34/BE-P34-H1(a): mirrors _create_invoice_line's shape with the
        credit-note element names — cac:CreditNoteLine carrying
        cbc:CreditedQuantity (never InvoicedQuantity; real Peppol access
        points validate against the OASIS UBL 2.1 CreditNote schema).

        Args:
            line_data: Line dictionary from mapped data
            currency: the document's currency (the P33 truth — every
                amount's currencyID carries it)

        Returns:
            CreditNoteLine element
        """
        line = etree.Element(f"{{{self.NAMESPACE_CAC}}}CreditNoteLine")

        # Line ID
        line_id = etree.SubElement(line, f"{{{self.NAMESPACE_CBC}}}ID")
        line_id.text = line_data.get("line_id", "1")

        # Credited quantity (the credit-note analog of InvoicedQuantity)
        quantity = etree.SubElement(line, f"{{{self.NAMESPACE_CBC}}}CreditedQuantity")
        quantity.set("unitCode", line_data.get("unit_code", "EA"))
        quantity.text = line_data.get("quantity", "1")

        # Line extension amount
        ext_amount = etree.SubElement(line, f"{{{self.NAMESPACE_CBC}}}LineExtensionAmount")
        ext_amount.set("currencyID", currency)
        ext_amount.text = line_data.get("line_extension_amount", "0.00")

        # Item
        item = etree.SubElement(line, f"{{{self.NAMESPACE_CAC}}}Item")

        # Description
        if line_data.get("description"):
            desc = etree.SubElement(item, f"{{{self.NAMESPACE_CBC}}}Description")
            desc.text = line_data["description"]

        # Price
        price = etree.SubElement(line, f"{{{self.NAMESPACE_CAC}}}Price")
        price_amount = etree.SubElement(price, f"{{{self.NAMESPACE_CBC}}}PriceAmount")
        price_amount.set("currencyID", currency)
        price_amount.text = line_data.get("unit_price", "0.00")

        return line
