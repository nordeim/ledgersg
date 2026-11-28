"""
Invoicing serializers for LedgerSG.

Serializers for Contact and InvoiceDocument models.
"""

from decimal import Decimal

from rest_framework import serializers

from apps.core.models import Contact, InvoiceDocument, InvoiceLine


class ContactListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for contact list views."""

    class Meta:
        model = Contact
        fields = [
            "id", "name", "contact_type", "is_customer", "is_supplier",
            "email", "phone", "is_active", "city", "country",
            # P11/H-1: the edit dialog prefills from the list row — without
            # uen/peppol_id here those fields always prefilled blank and an
            # unconditional save erased the stored values. The row badges
            # also claim them.
            "uen", "peppol_id",
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
    # P11/M-4: the edit dialog renders an editable "GST Registration No"
    # field — without this declaration DRF silently dropped it and the
    # save reported success while nothing persisted.
    gst_reg_number = serializers.CharField(
        max_length=20, required=False, allow_blank=True
    )


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
    """Serializer for creating a new invoice line.

    P14/M-4: bounded quantities/prices (the pre-P14 schema accepted
    negative unit_prices and 10^15 magnitudes that crashed deeper in the
    stack); discount_pct is bounded to [0, 100]. Shared by the line-add
    endpoint AND the document-create `lines` schema."""

    account_id = serializers.UUIDField()
    description = serializers.CharField(max_length=500)
    quantity = serializers.DecimalField(
        max_digits=19,
        decimal_places=4,
        default=Decimal("1.0000"),
        min_value=Decimal("0.0001"),
        max_value=Decimal("1000000"),
    )
    unit_price = serializers.DecimalField(
        max_digits=19,
        decimal_places=4,
        min_value=Decimal("0"),
        max_value=Decimal("9999999999999"),
    )
    tax_code_id = serializers.UUIDField()
    is_bcrs_deposit = serializers.BooleanField(default=False)
    discount_pct = serializers.DecimalField(
        max_digits=5,
        decimal_places=2,
        min_value=Decimal("0"),
        max_value=Decimal("100"),
        required=False,
        default=Decimal("0"),
    )

    # P16/BE-M3: NUMERIC(19,4) holds at most 15 integer digits — the
    # individual bounds above permit a 19-integer-digit PRODUCT that
    # overflows the column at INSERT (unhandled DataError 500).
    _MAX_LINE_TOTAL = Decimal("99999999999999.9999")

    def validate(self, data):
        quantity = data.get("quantity", Decimal("1"))
        unit_price = data.get("unit_price", Decimal("0"))
        if quantity * unit_price > self._MAX_LINE_TOTAL:
            raise serializers.ValidationError(
                {
                    "quantity": (
                        f"Line total (quantity x unit_price = {quantity * unit_price}) "
                        "exceeds the maximum representable amount "
                        f"({self._MAX_LINE_TOTAL})."
                    )
                }
            )
        return data


class InvoiceDocumentListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for document list views."""

    contact_name = serializers.CharField(source="contact.name", read_only=True)
    status_display = serializers.SerializerMethodField()
    # P9/B-3b: the outstanding balance — the payment forms' allocation
    # section (and any list UI) needs what is left to settle per row.
    amount_due = serializers.SerializerMethodField()

    class Meta:
        model = InvoiceDocument
        fields = [
            "id", "document_type", "document_number",
            "contact_id", "contact_name",
            "issue_date", "due_date", "status", "status_display",
            "total_incl", "currency",
            "amount_paid", "amount_due",
            # P9/C-6: the quotes list's CONVERTED badge gates on the link
            # (an approved-but-unconverted quote is APPROVED, not CONVERTED).
            "related_document_id",
        ]

    def get_amount_due(self, obj: InvoiceDocument) -> str:
        """Outstanding balance — mirrors the detail serializer and the
        DB generated column invoicing.document.amount_due."""
        return str(obj.total_incl - obj.amount_paid)

    def get_status_display(self, obj: InvoiceDocument) -> str:
        return obj.get_status_display()


class InvoiceDocumentDetailSerializer(serializers.ModelSerializer):
    """Detailed serializer for document views."""

    contact = ContactListSerializer(read_only=True)
    lines = InvoiceLineSerializer(many=True, read_only=True)
    status_history = serializers.SerializerMethodField()
    peppol_status = serializers.CharField(source="invoicenow_status", read_only=True)
    # P6/F-11: the payment state — the model persists amount_paid (P5/H-1)
    # and the DB exposes amount_due as a generated column
    # (total_amount - amount_paid) that the model does not declare.
    amount_due = serializers.SerializerMethodField()

    class Meta:
        model = InvoiceDocument
        fields = [
            "id", "document_type", "document_number",
            "contact",
            "issue_date", "due_date",
            "reference", "notes",
            "status", "lines",
            "total_excl", "gst_total", "total_incl", "currency",
            "amount_paid", "amount_due",
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
        """Synthesize the status history from the model's timestamps
        (P9/C-5 — the field previously returned [] behind a TODO).

        created_at -> DRAFT, approved_at -> APPROVED, voided_at -> VOID.
        SENT and PAID have no dedicated timestamps (the model stores no
        sent_at/paid_at) — they are absent rather than invented; a full
        event log needs the audit module's coverage decision.
        """
        history = [{"status": "DRAFT", "at": obj.created_at.isoformat()}]
        if obj.approved_at:
            history.append({"status": "APPROVED", "at": obj.approved_at.isoformat()})
        if obj.voided_at:
            history.append({"status": "VOID", "at": obj.voided_at.isoformat()})
        return history

    def get_amount_due(self, obj: InvoiceDocument) -> str:
        """Outstanding balance — mirrors the DB generated column
        invoicing.document.amount_due (total_amount - amount_paid)."""
        return str(obj.total_incl - obj.amount_paid)


class InvoiceDocumentCreateSerializer(serializers.Serializer):
    """Serializer for creating a new document."""

    document_type = serializers.ChoiceField(choices=InvoiceDocument.DOCUMENT_TYPES)
    contact_id = serializers.UUIDField()
    issue_date = serializers.DateField()
    due_date = serializers.DateField(required=False, allow_null=True)
    reference = serializers.CharField(max_length=100, required=False, allow_blank=True)
    notes = serializers.CharField(required=False, allow_blank=True)
    # P14/M-4: REQUIRED with min_length=1 — a document without lines is a
    # data error, not a valid state (the view's data["lines"] KeyError'd
    # to a 500 when the field was optional).
    lines = serializers.ListField(
        child=InvoiceLineCreateSerializer(),
        required=True,
        min_length=1,
    )
    # P14/H-4: the original invoice a credit note corrects — REQUIRED at
    # the service layer for *_CREDIT_NOTE (validated there, where the
    # same-contact + cap rules live; here it is just the typed pass-through).
    related_document_id = serializers.UUIDField(required=False, allow_null=True)


class InvoiceDocumentUpdateSerializer(serializers.Serializer):
    """Serializer for updating a document draft."""

    due_date = serializers.DateField(required=False)
    reference = serializers.CharField(max_length=100, required=False, allow_blank=True)
    notes = serializers.CharField(required=False, allow_blank=True)


class StatusTransitionSerializer(serializers.Serializer):
    """Serializer for status transition request.

    P7/F-2: `status` is a ChoiceField over the real doc_status vocabulary —
    the pre-P7 bare CharField accepted arbitrary strings (and the view's
    permission check compared against the non-existent "VOIDED" literal).
    """

    status = serializers.ChoiceField(choices=InvoiceDocument.STATUS_CHOICES)
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


class RecipientListField(serializers.ListField):
    """Email list that also accepts a single bare string (normalized to a
    one-element list — P7/F-6: the email task requires a list; a string
    crashed it silently)."""

    def to_internal_value(self, data):
        if isinstance(data, str):
            data = [data]
        return super().to_internal_value(data)


class InvoiceSendSerializer(serializers.Serializer):
    """Serializer for the send-invoice-email payload (P7/F-6).

    Recipients are email-validated and NORMALIZED: a single string is
    accepted and becomes a one-element list (the email task requires a
    list — a bare string crashed it silently while the API had already
    returned success).
    """

    to = RecipientListField(
        child=serializers.EmailField(), required=False, allow_empty=True
    )
    cc = RecipientListField(
        child=serializers.EmailField(), required=False, allow_empty=True
    )
    bcc = RecipientListField(
        child=serializers.EmailField(), required=False, allow_empty=True
    )
    # P8/G-6: the `message` field is gone — it was validated but never
    # delivered (the task has no body-message parameter; the document
    # notes already travel in the attached PDF). A field that promises
    # behavior must deliver it or disappear.

    def validate(self, data):
        # `to` may be omitted entirely — the service falls back to the
        # contact's email — but an explicitly EMPTY list must not silently
        # drop every recipient.
        if "to" in data and not data["to"]:
            raise serializers.ValidationError(
                {"to": "Provide at least one recipient, or omit 'to' to use the contact's email."}
            )
        return data
