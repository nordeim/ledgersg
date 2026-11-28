"""
Payment Allocation Serializers for LedgerSG Banking Module.

Validates allocation of payments to invoices/bills.
SEC-001 Remediation: Replaces unvalidated request.data.get() stubs.
"""

from decimal import Decimal

from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from apps.core.models import InvoiceDocument, Payment, PaymentAllocation
from common.decimal_utils import money

# P16/BE-H2: the allocation-eligible status set — ONE wire contract.
# A PARTIALLY_PAID invoice MUST accept its next instalment (the pre-P14
# APPROVED-only check made instalments impossible through the API), and
# SENT/OVERDUE are billed documents awaiting money. DRAFT/VOID are never
# allocatable. Mirrors the service-side guard in payment_service.allocate
# (P14/H-1) and PaymentReceiveSerializer (P14/H-2).
ALLOCATABLE_STATUSES = ("APPROVED", "SENT", "PARTIALLY_PAID", "OVERDUE")


class PaymentAllocationSerializer(serializers.ModelSerializer):
    """Read serializer for PaymentAllocation."""

    document_number = serializers.CharField(source="document.document_number", read_only=True)
    document_total = serializers.DecimalField(
        source="document.total_incl",
        max_digits=19,
        decimal_places=4,
        read_only=True,
    )

    class Meta:
        model = PaymentAllocation
        fields = [
            "id",
            "payment",
            "document",
            "document_number",
            "document_total",
            "allocated_amount",
            "base_allocated_amount",
            "created_at",
        ]
        read_only_fields = ["id", "base_allocated_amount", "created_at"]


class BulkAllocationSerializer(serializers.Serializer):
    """
    Serializer for bulk allocation of a payment to multiple documents.

    Validates:
    - Payment belongs to org and is not voided
    - All documents belong to org and are in ALLOCATABLE_STATUSES
      (P16/BE-H2: the pre-P16 APPROVED-only literal here refused the
      second instalment of a PARTIALLY_PAID invoice on the dedicated
      endpoint while the embedded path accepted it)
    - Total allocations don't exceed payment amount
    - No duplicate document allocations
    """

    payment_id = serializers.UUIDField()
    allocations = serializers.ListField(
        child=serializers.DictField(),
        allow_empty=False,
    )

    def validate_payment_id(self, value):
        org_id = self.context.get("org_id")
        if not org_id:
            raise serializers.ValidationError(_("Organisation context required."))

        try:
            payment = Payment.objects.get(id=value, org_id=org_id)
        except Payment.DoesNotExist:
            raise serializers.ValidationError(_("Payment not found in this organisation."))

        if payment.is_voided:
            raise serializers.ValidationError(_("Cannot allocate a voided payment."))

        return value

    def validate_allocations(self, value):
        if not value:
            raise serializers.ValidationError(_("At least one allocation is required."))

        total = Decimal("0")
        document_ids = set()

        for alloc in value:
            if "document_id" not in alloc:
                raise serializers.ValidationError(_("Each allocation must have a document_id."))
            if "allocated_amount" not in alloc:
                raise serializers.ValidationError(
                    _("Each allocation must have an allocated_amount.")
                )

            try:
                amount = money(alloc["allocated_amount"])
            except (ValueError, TypeError):
                raise serializers.ValidationError(
                    _("Invalid allocated_amount: {}").format(alloc.get("allocated_amount"))
                )

            if amount <= Decimal("0"):
                raise serializers.ValidationError(_("Allocated amount must be positive."))

            doc_id = alloc["document_id"]
            if doc_id in document_ids:
                raise serializers.ValidationError(
                    _("Duplicate document allocation: {}").format(doc_id)
                )
            document_ids.add(doc_id)

            total += amount

        return value

    def validate(self, data):
        org_id = self.context.get("org_id")
        if not org_id:
            raise serializers.ValidationError(_("Organisation context required."))

        payment = Payment.objects.get(id=data["payment_id"], org_id=org_id)

        total_allocated = sum(money(alloc["allocated_amount"]) for alloc in data["allocations"])

        if total_allocated > payment.amount:
            raise serializers.ValidationError(
                _("Total allocations ({}) exceed payment amount ({}).").format(
                    total_allocated, payment.amount
                )
            )

        for alloc in data["allocations"]:
            try:
                document = InvoiceDocument.objects.get(
                    id=alloc["document_id"],
                    org_id=org_id,
                )
            except InvoiceDocument.DoesNotExist:
                raise serializers.ValidationError(
                    _("Document {} not found.").format(alloc["document_id"])
                )

            if document.status not in ALLOCATABLE_STATUSES:
                raise serializers.ValidationError(
                    _(
                        "Document {} must be APPROVED, SENT, PARTIALLY_PAID or "
                        "OVERDUE for allocation."
                    ).format(alloc["document_id"])
                )

            if document.contact_id != payment.contact_id:
                raise serializers.ValidationError(
                    _("Document {} contact does not match payment contact.").format(
                        alloc["document_id"]
                    )
                )

        return data
