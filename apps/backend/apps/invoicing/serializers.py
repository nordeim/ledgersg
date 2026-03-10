"""
Invoicing serializers for LedgerSG.

Serializers for Contact and InvoiceDocument models.
"""

from rest_framework import serializers
from decimal import Decimal

from apps.core.models import Contact, InvoiceDocument, InvoiceLine


class ContactListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for contact list views."""
    
    class Meta:
        model = Contact
        fields = [
            "id", "name", "contact_type", "is_customer", "is_supplier",
            "email", "phone", "is_active", "city", "country"
        ]
        read_only_fields = ["id"]


class ContactDetailSerializer(serializers.ModelSerializer):
    """Detailed serializer for contact views."""
    
    class Meta:
        model = Contact
        fields = [
            "id", "name", "contact_type", "company_name", "legal_name", "uen",
            "gst_reg_number", "is_gst_registered", "tax_code_default",
            "is_customer", "is_supplier", "is_active",
            "email", "phone", "fax", "website",
            "address_line_1", "address_line_2", "city", "state_province",
            "postal_code", "country", "default_currency", "payment_terms_days",
            "credit_limit", "receivable_account_id", "payable_account_id",
            "peppol_id", "peppol_scheme_id", "notes",
            "created_at", "updated_at"
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class ContactCreateSerializer(serializers.Serializer):
    """Serializer for creating a new contact."""
    
    name = serializers.CharField(max_length=255)
    company_name = serializers.CharField(max_length=255, required=False, allow_blank=True)
    email = serializers.EmailField(required=False, allow_blank=True)
    phone = serializers.CharField(max_length=50, required=False, allow_blank=True)
    address_line_1 = serializers.CharField(max_length=255, required=False, allow_blank=True)
    address_line_2 = serializers.CharField(max_length=255, required=False, allow_blank=True)
    city = serializers.CharField(max_length=100, required=False, allow_blank=True)
    postal_code = serializers.CharField(max_length=20, required=False, allow_blank=True)
    country = serializers.CharField(max_length=2, default="SG")
    uen = serializers.CharField(max_length=20, required=False, allow_blank=True)
    peppol_id = serializers.CharField(max_length=50, required=False, allow_blank=True)
    is_customer = serializers.BooleanField(default=True)
    is_supplier = serializers.BooleanField(default=False)
    payment_terms_days = serializers.IntegerField(default=30)


class ContactUpdateSerializer(serializers.Serializer):
    """Serializer for updating a contact."""
    
    name = serializers.CharField(max_length=255, required=False)
    company_name = serializers.CharField(max_length=255, required=False, allow_blank=True)
    email = serializers.EmailField(required=False, allow_blank=True)
    phone = serializers.CharField(max_length=50, required=False, allow_blank=True)
    address_line_1 = serializers.CharField(max_length=255, required=False, allow_blank=True)
    address_line_2 = serializers.CharField(max_length=255, required=False, allow_blank=True)
    city = serializers.CharField(max_length=100, required=False, allow_blank=True)
    postal_code = serializers.CharField(max_length=20, required=False, allow_blank=True)
    country = serializers.CharField(max_length=2, required=False)
    uen = serializers.CharField(max_length=20, required=False, allow_blank=True)
    peppol_id = serializers.CharField(max_length=50, required=False, allow_blank=True)
    is_customer = serializers.BooleanField(required=False)
    is_supplier = serializers.BooleanField(required=False)
    is_active = serializers.BooleanField(required=False)
    payment_terms_days = serializers.IntegerField(required=False)


class InvoiceLineSerializer(serializers.ModelSerializer):
    """Serializer for invoice line items."""
    
    account_code = serializers.CharField(source="account.code", read_only=True)
    account_name = serializers.CharField(source="account.name", read_only=True)
    tax_code_code = serializers.CharField(source="tax_code.code", read_only=True)
    
    class Meta:
        model = InvoiceLine
        fields = [
            "id", "line_number", "description", "account_id", "account_code",
            "account_name", "quantity", "unit_price", "discount_pct",
            "discount_amount", "line_amount", "tax_code_id", "tax_code_code",
            "tax_rate", "gst_amount", "total_amount", "is_bcrs_deposit"
        ]
        read_only_fields = ["id", "line_amount", "gst_amount", "total_amount"]


class InvoiceLineCreateSerializer(serializers.Serializer):
    """Serializer for creating a new invoice line."""
    
    account_id = serializers.UUIDField()
    description = serializers.CharField(max_length=500)
    quantity = serializers.DecimalField(max_digits=10, decimal_places=4, default=Decimal("1.0000"))
    unit_price = serializers.DecimalField(max_digits=10, decimal_places=4)
    tax_code_id = serializers.UUIDField()
    is_bcrs_deposit = serializers.BooleanField(default=False)


class InvoiceDocumentListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for document list views."""
    
    contact_name = serializers.CharField(source="contact.name", read_only=True)
    status_display = serializers.SerializerMethodField()
    
    class Meta:
        model = InvoiceDocument
        fields = [
            "id", "document_type", "document_number",
            "contact_id", "contact_name",
            "issue_date", "due_date", "status", "status_display",
            "total_incl", "currency"
        ]
    
    def get_status_display(self, obj: InvoiceDocument) -> str:
        return obj.get_status_display()


class InvoiceDocumentDetailSerializer(serializers.ModelSerializer):
    """Detailed serializer for document views."""
    
    contact = ContactListSerializer(read_only=True)
    lines = InvoiceLineSerializer(many=True, read_only=True)
    status_history = serializers.SerializerMethodField()
    peppol_status = serializers.CharField(source="invoicenow_status", read_only=True)
    
    class Meta:
        model = InvoiceDocument
        fields = [
            "id", "document_type", "document_number",
            "contact",
            "issue_date", "due_date",
            "reference", "notes",
            "status", "lines",
            "total_excl", "gst_total", "total_incl", "currency",
            "journal_entry_id", "peppol_status",
            "approved_at", "voided_at",
            "status_history",
            "created_at", "updated_at"
        ]
        read_only_fields = [
            "id", "document_number", "total_excl", "gst_total", "total_incl",
            "created_at", "updated_at"
        ]
    
    def get_status_history(self, obj: InvoiceDocument) -> list:
        """Get audit log for status changes."""
        # TODO: Implement once audit module is ready
        return []


class InvoiceDocumentCreateSerializer(serializers.Serializer):
    """Serializer for creating a new document."""
    
    document_type = serializers.ChoiceField(choices=InvoiceDocument.DOCUMENT_TYPES)
    contact_id = serializers.UUIDField()
    issue_date = serializers.DateField()
    due_date = serializers.DateField(required=False, allow_null=True)
    reference = serializers.CharField(max_length=100, required=False, allow_blank=True)
    notes = serializers.CharField(required=False, allow_blank=True)
    lines = serializers.ListField(
        child=serializers.DictField(),
        required=False
    )


class InvoiceDocumentUpdateSerializer(serializers.Serializer):
    """Serializer for updating a document draft."""
    
    due_date = serializers.DateField(required=False)
    reference = serializers.CharField(max_length=100, required=False, allow_blank=True)
    notes = serializers.CharField(required=False, allow_blank=True)


class StatusTransitionSerializer(serializers.Serializer):
    """Serializer for status transition request."""
    
    status = serializers.CharField()
    reason = serializers.CharField(required=False, allow_blank=True)


class QuoteConversionSerializer(serializers.Serializer):
    """Serializer for quote to invoice conversion."""
    
    quote_id = serializers.UUIDField()


class DocumentSummarySerializer(serializers.Serializer):
    """Serializer for document status summary."""
    
    by_status = serializers.DictField(child=serializers.IntegerField())
    by_type = serializers.DictField(child=serializers.IntegerField())
    total_outstanding = serializers.DecimalField(max_digits=15, decimal_places=2)
    overdue_count = serializers.IntegerField()
