"""
Payment Service for LedgerSG Banking Module.

Business logic for payment creation, allocation, and voiding.
SEC-001 Remediation: All operations validated and logged.
"""

from uuid import UUID, uuid4
from typing import List, Optional, Dict, Any
from decimal import Decimal
from datetime import date
from django.db import transaction, connection
from django.utils import timezone

from apps.core.models import (
    Payment,
    PaymentAllocation,
    BankAccount,
    Contact,
    InvoiceDocument,
    JournalEntry,
    JournalLine,
    Account,
    AuditEventLog,
    FiscalPeriod,
)
from common.exceptions import ValidationError, ResourceNotFound
from common.decimal_utils import money


def _invalidate_dashboard_cache(org_id) -> None:
    """
    Invalidate the 5-minute dashboard cache after a mutation (P5/H-3).

    The cache existed but nothing ever invalidated it, so every approve /
    payment / filing left the dashboard serving stale KPIs until TTL.
    Local import: reporting must not be a hard dependency of the
    transactional services.
    """
    try:
        from apps.reporting.services.dashboard_service import DashboardService

        DashboardService().invalidate_dashboard_cache(str(org_id))
    except Exception:  # noqa: BLE001 — cache invalidation must never fail a mutation
        import logging

        logging.getLogger(__name__).exception(
            "dashboard cache invalidation failed for org %s", org_id
        )

class PaymentService:
    """Service class for payment operations."""

    @staticmethod
    def _get_next_payment_number(org_id: UUID, payment_type: str) -> str:
        """
        Get next payment number from sequence.

        Args:
            org_id: Organisation UUID
            payment_type: 'RECEIVED' or 'MADE'

        Returns:
            Payment number (e.g., 'RCP-00042' or 'PAY-00042')
        """
        prefix = "RCP" if payment_type == "RECEIVED" else "PAY"

        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT core.get_next_document_number(%s, %s)",
                [str(org_id), f"PAYMENT_{payment_type}"],
            )
            next_num = cursor.fetchone()[0]

        return f"{prefix}-{next_num:05d}"

    @staticmethod
    @transaction.atomic()
    def create_received(
        org_id: UUID,
        data: dict,
        user_id: Optional[UUID] = None,
    ) -> Payment:
        """
        Create a received payment from a customer.

        Args:
            org_id: Organisation UUID
            data: Validated serializer data
            user_id: Creating user ID

        Returns:
            Created Payment instance

        Raises:
            ValidationError: If validation fails
        """
        contact = Contact.objects.get(id=data["contact_id"], org_id=org_id)
        bank_account = BankAccount.objects.get(id=data["bank_account_id"], org_id=org_id)

        amount = money(data["amount"])
        exchange_rate = money(data.get("exchange_rate", Decimal("1.000000")))
        currency = data.get("currency", "SGD")

        base_amount = (amount * exchange_rate).quantize(Decimal("0.0001"))

        payment_number = PaymentService._get_next_payment_number(org_id, "RECEIVED")

        payment = Payment.objects.create(
            org_id=org_id,
            payment_type="RECEIVED",
            payment_number=payment_number,
            payment_date=data["payment_date"],
            contact=contact,
            bank_account=bank_account,
            currency=currency,
            exchange_rate=exchange_rate,
            amount=amount,
            base_amount=base_amount,
            fx_gain_loss=Decimal("0.0000"),
            payment_method=data["payment_method"],
            payment_reference=data.get("payment_reference", ""),
            notes=data.get("notes", ""),
            is_reconciled=False,
            is_voided=False,
        )

        AuditEventLog.objects.create(
            org_id=org_id,
            user_id=user_id,
            action="CREATE",
            entity_schema="banking",
            entity_table="payment",
            entity_id=payment.id,
            new_data={
                "payment_number": payment.payment_number,
                "payment_type": "RECEIVED",
                "amount": str(payment.amount),
                "contact": contact.name,
            },
        )

        # Create journal entry
        journal_entry = PaymentService._create_payment_journal_entry(org_id, payment, user_id)
        payment.journal_entry = journal_entry
        payment.save()

        _invalidate_dashboard_cache(org_id)
        return payment

    @staticmethod
    @transaction.atomic()
    def create_made(
        org_id: UUID,
        data: dict,
        user_id: Optional[UUID] = None,
    ) -> Payment:
        """
        Create a payment made to a supplier.

        Args:
            org_id: Organisation UUID
            data: Validated serializer data
            user_id: Creating user ID

        Returns:
            Created Payment instance
        """
        contact = Contact.objects.get(id=data["contact_id"], org_id=org_id)
        bank_account = BankAccount.objects.get(id=data["bank_account_id"], org_id=org_id)

        amount = money(data["amount"])
        exchange_rate = money(data.get("exchange_rate", Decimal("1.000000")))
        currency = data.get("currency", "SGD")

        base_amount = (amount * exchange_rate).quantize(Decimal("0.0001"))

        payment_number = PaymentService._get_next_payment_number(org_id, "MADE")

        payment = Payment.objects.create(
            org_id=org_id,
            payment_type="MADE",
            payment_number=payment_number,
            payment_date=data["payment_date"],
            contact=contact,
            bank_account=bank_account,
            currency=currency,
            exchange_rate=exchange_rate,
            amount=amount,
            base_amount=base_amount,
            fx_gain_loss=Decimal("0.0000"),
            payment_method=data["payment_method"],
            payment_reference=data.get("payment_reference", ""),
            notes=data.get("notes", ""),
            is_reconciled=False,
            is_voided=False,
        )

        AuditEventLog.objects.create(
            org_id=org_id,
            user_id=user_id,
            action="CREATE",
            entity_schema="banking",
            entity_table="payment",
            entity_id=payment.id,
            new_data={
                "payment_number": payment.payment_number,
                "payment_type": "MADE",
                "amount": str(payment.amount),
                "contact": contact.name,
            },
        )

        # Create journal entry
        journal_entry = PaymentService._create_payment_journal_entry(org_id, payment, user_id)
        payment.journal_entry = journal_entry
        payment.save()

        _invalidate_dashboard_cache(org_id)
        return payment

    @staticmethod
    def list(
        org_id: UUID,
        payment_type: Optional[str] = None,
        contact_id: Optional[UUID] = None,
        bank_account_id: Optional[UUID] = None,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
        is_reconciled: Optional[bool] = None,
        is_voided: Optional[bool] = None,
    ) -> List[Payment]:
        """
        List payments with optional filters.

        Args:
            org_id: Organisation UUID
            payment_type: Filter by type ('RECEIVED' or 'MADE')
            contact_id: Filter by contact
            bank_account_id: Filter by bank account
            date_from: Filter from date
            date_to: Filter to date
            is_reconciled: Filter by reconciliation status
            is_voided: Filter by void status

        Returns:
            List of Payment instances
        """
        queryset = Payment.objects.filter(org_id=org_id)

        if payment_type:
            queryset = queryset.filter(payment_type=payment_type)

        if contact_id:
            queryset = queryset.filter(contact_id=contact_id)

        if bank_account_id:
            queryset = queryset.filter(bank_account_id=bank_account_id)

        if date_from:
            queryset = queryset.filter(payment_date__gte=date_from)

        if date_to:
            queryset = queryset.filter(payment_date__lte=date_to)

        if is_reconciled is not None:
            queryset = queryset.filter(is_reconciled=is_reconciled)

        if is_voided is not None:
            queryset = queryset.filter(is_voided=is_voided)

        return list(queryset.order_by("-payment_date", "-created_at"))

    @staticmethod
    def get(org_id: UUID, payment_id: UUID) -> Payment:
        """
        Get a single payment.

        Args:
            org_id: Organisation UUID
            payment_id: Payment UUID

        Returns:
            Payment instance

        Raises:
            ResourceNotFound: If not found
        """
        try:
            return Payment.objects.get(id=payment_id, org_id=org_id)
        except Payment.DoesNotExist:
            raise ResourceNotFound(f"Payment {payment_id} not found")

    @staticmethod
    @transaction.atomic()
    def void(
        org_id: UUID,
        payment_id: UUID,
        reason: str,
        user_id: Optional[UUID] = None,
    ) -> Payment:
        """
        Void a payment.

        Args:
            org_id: Organisation UUID
            payment_id: Payment UUID
            reason: Reason for voiding
            user_id: Voiding user ID

        Returns:
            Voided Payment instance

        Raises:
            ValidationError: If payment cannot be voided
        """
        payment = PaymentService.get(org_id, payment_id)

        if payment.is_voided:
            raise ValidationError("Payment is already voided.")

        if payment.journal_entry:
            try:
                fiscal_period = FiscalPeriod.objects.get(
                    org_id=org_id,
                    start_date__lte=payment.payment_date,
                    end_date__gte=payment.payment_date,
                )
                if not fiscal_period.is_open:
                    raise ValidationError(
                        f"Cannot void payment in closed fiscal period ({fiscal_period.label})."
                    )
            except FiscalPeriod.DoesNotExist:
                raise ValidationError("No fiscal period found for payment date. Cannot void.")

            # P5/H-2: a voided payment must not stay in the ledger — mirror
            # DocumentService.void_document's reversal (corrections are
            # reversals; entries are immutable). The reversal prefers
            # today's period and falls back to the original entry's date
            # when the current period is closed (e.g. year-end).
            from apps.journal.services import JournalService

            original_entry = JournalService.get_entry(
                org_id, payment.journal_entry_id
            )
            reversal_date = timezone.now().date()
            if not JournalService._get_fiscal_period(org_id, reversal_date):
                reversal_date = original_entry.entry_date

            reversal = JournalService.create_reversal(
                org_id=org_id,
                original_entry_id=payment.journal_entry_id,
                reversal_date=reversal_date,
                reason=f"Void of payment {payment.payment_number}: {reason}",
                user_id=user_id,
            )
        else:
            reversal = None

        # P5/H-2: a voided payment no longer represents money — release its
        # allocations and recompute each document's amount_paid/status.
        affected_documents = list(
            InvoiceDocument.objects.filter(
                paymentallocation__payment_id=payment.id
            ).distinct()
        )
        PaymentAllocation.objects.filter(payment=payment).delete()
        for document in affected_documents:
            remaining = sum(
                (
                    a.allocated_amount
                    for a in PaymentAllocation.objects.filter(document=document)
                ),
                Decimal("0"),
            )
            document.amount_paid = remaining
            if remaining <= 0:
                document.status = "APPROVED"
            elif remaining < document.total_incl:
                document.status = "PARTIALLY_PAID"
            else:
                document.status = "PAID"
            document.save()

        payment.is_voided = True
        payment.notes = f"{payment.notes}\n\nVOIDED: {reason}".strip()
        payment.save()

        AuditEventLog.objects.create(
            org_id=org_id,
            user_id=user_id,
            action="VOID",
            entity_schema="banking",
            entity_table="payment",
            entity_id=payment.id,
            old_data={"is_voided": False},
            new_data={
                "is_voided": True,
                "reason": reason,
                "reversal_entry_id": str(reversal.id) if reversal else None,
                "released_allocations": len(affected_documents),
            },
        )

        _invalidate_dashboard_cache(org_id)
        return payment

    @staticmethod
    @transaction.atomic()
    def allocate(
        org_id: UUID,
        payment_id: UUID,
        allocations: List[Dict[str, Any]],
        user_id: Optional[UUID] = None,
    ) -> Payment:
        """
        Allocate a payment to one or more documents.

        Args:
            org_id: Organisation UUID
            payment_id: Payment UUID
            allocations: List of {'document_id': UUID, 'allocated_amount': Decimal}
            user_id: Allocating user ID

        Returns:
            Updated Payment instance

        Raises:
            ValidationError: If validation fails
        """
        payment = PaymentService.get(org_id, payment_id)

        if payment.is_voided:
            raise ValidationError("Cannot allocate a voided payment.")

        existing_allocations = PaymentAllocation.objects.filter(payment=payment)
        already_allocated = sum(
            (alloc.allocated_amount for alloc in existing_allocations),
            Decimal("0"),
        )

        new_allocations_total = sum(money(alloc["allocated_amount"]) for alloc in allocations)

        if already_allocated + new_allocations_total > payment.amount:
            remaining = payment.amount - already_allocated
            raise ValidationError(
                f"Total allocations ({already_allocated + new_allocations_total}) "
                f"exceed payment amount ({payment.amount}). "
                f"Remaining available: {remaining}"
            )

        for alloc_data in allocations:
            document_id = alloc_data["document_id"]
            allocated_amount = money(alloc_data["allocated_amount"])

            document = InvoiceDocument.objects.get(id=document_id, org_id=org_id)

            if document.contact.id != payment.contact.id:
                raise ValidationError(
                    f"Document {document.document_number} contact does not match payment contact."
                )

            if document.status not in ("APPROVED", "PARTIALLY_PAID"):
                raise ValidationError(
                    f"Document {document.document_number} must be APPROVED or "
                    "PARTIALLY_PAID for allocation."
                )

            existing = PaymentAllocation.objects.filter(payment=payment, document=document).first()

            if existing:
                raise ValidationError(
                    f"Payment is already allocated to {document.document_number}."
                )

            base_allocated = (allocated_amount * payment.exchange_rate).quantize(Decimal("0.0001"))

            PaymentAllocation.objects.create(
                org_id=org_id,
                payment=payment,
                document=document,
                allocated_amount=allocated_amount,
                base_allocated_amount=base_allocated,
            )

            document_allocations = PaymentAllocation.objects.filter(document=document)
            total_allocated_to_doc = sum(
                (a.allocated_amount for a in document_allocations), Decimal("0")
            )

            # P5/H-1: persist amount_paid — the allocations table is the
            # truth; the dashboard's outstanding-AR/AP filters and the
            # amount_due generated column both read it.
            document.amount_paid = total_allocated_to_doc

            if total_allocated_to_doc >= document.total_incl:
                document.status = "PAID"
            elif total_allocated_to_doc > 0:
                document.status = "PARTIALLY_PAID"
            document.save()

        AuditEventLog.objects.create(
            org_id=org_id,
            user_id=user_id,
            action="UPDATE",
            entity_schema="banking",
            entity_table="payment",
            entity_id=payment.id,
            new_data={
                "allocations": [
                    {"document_id": str(a["document_id"]), "amount": str(a["allocated_amount"])}
                    for a in allocations
                ],
                "operation": "ALLOCATE",
            },
        )

        _invalidate_dashboard_cache(org_id)
        return payment

    @staticmethod
    def get_allocations(payment_id: UUID) -> List[PaymentAllocation]:
        """
        Get all allocations for a payment.

        Args:
            payment_id: Payment UUID

        Returns:
            List of PaymentAllocation instances
        """
        return list(
            PaymentAllocation.objects.filter(payment_id=payment_id).select_related("document")
        )

    @staticmethod
    @transaction.atomic()
    def unallocate(
        org_id: UUID,
        allocation_id: UUID,
        user_id: Optional[UUID] = None,
    ) -> None:
        """
        Remove an allocation from a payment.

        Args:
            org_id: Organisation UUID
            allocation_id: PaymentAllocation UUID
            user_id: User performing the action

        Raises:
            ResourceNotFound: If allocation not found
            ValidationError: If allocation belongs to different org
        """
        try:
            allocation = PaymentAllocation.objects.get(id=allocation_id, org_id=org_id)
        except PaymentAllocation.DoesNotExist:
            raise ResourceNotFound(f"Allocation {allocation_id} not found")

        payment = allocation.payment
        document = allocation.document

        # Store old values for audit
        old_amount = allocation.allocated_amount

        # Delete allocation
        allocation.delete()

        # P6/F-7: recompute amount_paid from the surviving allocations and
        # derive the status with the same thresholds as allocate() — the
        # outstanding-AR dashboard filters and the amount_due generated
        # column both read amount_paid (P5/H-1 parity).
        total_allocated = sum(
            a.allocated_amount for a in PaymentAllocation.objects.filter(document=document)
        )
        document.amount_paid = total_allocated
        if total_allocated >= document.total_incl:
            document.status = "PAID"
        elif total_allocated > 0:
            document.status = "PARTIALLY_PAID"
        else:
            document.status = "APPROVED"
        document.save()

        # Audit log
        AuditEventLog.objects.create(
            org_id=org_id,
            user_id=user_id,
            action="DELETE",  # Using DELETE since UNALLOCATE is not in check constraint
            entity_schema="banking",
            entity_table="payment_allocation",
            entity_id=allocation_id,
            old_data={
                "payment_id": str(payment.id),
                "document_id": str(document.id),
                "allocated_amount": str(old_amount),
                "operation": "UNALLOCATE",
            },
        )

    @staticmethod
    def _create_payment_journal_entry(
        org_id: UUID,
        payment: Payment,
        user_id: Optional[UUID] = None,
    ) -> JournalEntry:
        """
        Create journal entry for a payment.

        For RECEIVED payments:
        - Debit: Bank Account (GL)
        - Credit: Accounts Receivable

        For MADE payments:
        - Debit: Accounts Payable
        - Credit: Bank Account (GL)
        """
        from apps.journal.services import JournalService

        # Get bank account's GL account
        bank_gl_account = payment.bank_account.gl_account

        # Get AR/AP account for contact
        if payment.payment_type == "RECEIVED":
            ar_account = payment.contact.receivable_account
            if not ar_account:
                # P6/F-5: exact control-account resolution, fail-closed —
                # the pre-P6 broad Q(account_type="ASSET").first() could
                # post AR to any asset (e.g. 1010 Cash on Hand). Mirrors
                # the P5/H-4 resolver used by journal_service.
                ar_account = JournalService._get_ar_account(org_id)

            lines = [
                {
                    "account_id": bank_gl_account.id,
                    "debit": payment.base_amount,
                    "credit": Decimal("0.0000"),
                    "description": f"Payment received: {payment.payment_number}",
                },
                {
                    "account_id": ar_account.id,
                    "debit": Decimal("0.0000"),
                    "credit": payment.base_amount,
                    "description": f"Payment from: {payment.contact.name}",
                },
            ]
            description = f"Payment received: {payment.payment_number} - {payment.contact.name}"

        else:  # MADE
            ap_account = payment.contact.payable_account
            if not ap_account:
                # P6/F-5: exact control-account resolution, fail-closed
                # (see the RECEIVED branch above).
                ap_account = JournalService._get_ap_account(org_id)

            lines = [
                {
                    "account_id": ap_account.id,
                    "debit": payment.base_amount,
                    "credit": Decimal("0.0000"),
                    "description": f"Payment to: {payment.contact.name}",
                },
                {
                    "account_id": bank_gl_account.id,
                    "debit": Decimal("0.0000"),
                    "credit": payment.base_amount,
                    "description": f"Payment made: {payment.payment_number}",
                },
            ]
            description = f"Payment made: {payment.payment_number} - {payment.contact.name}"

        return JournalService.create_entry(
            org_id=org_id,
            entry_date=payment.payment_date,
            entry_type="PAYMENT",
            description=description,
            lines=lines,
            user_id=user_id,
        )
