"""
Payment Service for LedgerSG Banking Module.

Business logic for payment creation, allocation, and voiding.
SEC-001 Remediation: All operations validated and logged.
"""

from datetime import date
from decimal import Decimal
from typing import Any, Dict, List, Optional
from uuid import UUID

from django.db import connection, transaction
from django.db.models import QuerySet
from django.utils import timezone

from apps.core.models import (
    AuditEventLog,
    BankAccount,
    Contact,
    FiscalPeriod,
    InvoiceDocument,
    JournalEntry,
    Payment,
    PaymentAllocation,
)
from common.decimal_utils import money
from common.exceptions import ResourceNotFound, ValidationError


def _invalidate_dashboard_cache(org_id) -> None:
    """
    Invalidate the 5-minute dashboard cache after a mutation (P5/H-3).

    The cache existed but nothing ever invalidated it, so every approve /
    payment / filing left the dashboard serving stale KPIs until TTL.
    Local import: reporting must not be a hard dependency of the
    transactional services.

    P21/BE-M3: the invalidation is registered on COMMIT — running it
    inside the open transaction re-seeds the stale value in the
    delete->commit window (a concurrent read re-populates the cache from
    the still-pre-commit DB and it survives to TTL). In autocommit
    contexts on_commit fires immediately, so non-transactional callers
    keep the old behavior.
    """
    try:
        from apps.reporting.services.dashboard_service import DashboardService

        def _invalidate() -> None:
            DashboardService().invalidate_dashboard_cache(str(org_id))

        transaction.on_commit(_invalidate)
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
        exchange_rate = PaymentService._validated_exchange_rate(
            data.get("exchange_rate", Decimal("1.000000"))
        )
        currency = data.get("currency", "SGD")

        # P16/L1: money() (HALF_UP, 4dp) — the raw .quantize() default
        # is HALF_EVEN and drifted sub-cent on FX conversions.
        base_amount = money(amount * exchange_rate)

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
        exchange_rate = PaymentService._validated_exchange_rate(
            data.get("exchange_rate", Decimal("1.000000"))
        )
        currency = data.get("currency", "SGD")

        # P16/L1: money() (HALF_UP, 4dp) — the raw .quantize() default
        # is HALF_EVEN and drifted sub-cent on FX conversions.
        base_amount = money(amount * exchange_rate)

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
    ) -> QuerySet[Payment]:
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
            Lazy Payment queryset (P28/BE-H1: the LAZY queryset — the
            view counts via .count() and pages at the SQL level; the
            pre-P28 list() materialisation fetched the entire filtered
            set on every page)
        """
        # P17/BE-M7: the serializer traverses contact + bank_account per
        # row — select_related keeps the list O(1) queries instead of 1+2N.
        queryset = Payment.objects.filter(org_id=org_id).select_related(
            "contact", "bank_account"
        )

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

        # P24/I1: the id tiebreaker — same-date payments tie, and Postgres
        # tie order is not stable across executions (a paginated page
        # boundary could skip or duplicate a row).
        # P28/BE-H1: returned LAZY — evaluate inside the request (the
        # RLS tenant context holds there).
        return queryset.order_by("-payment_date", "-created_at", "-id")

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
            # P29/BE-H1: the detail seam joins the related rows — the
            # pre-P29 plain .get() left the serializer walking contact
            # and bank_account as two extra per-row SELECTs on every
            # serialisation (the detail GET, the create/void/make/
            # receive responses).
            return Payment.objects.select_related(
                "contact", "bank_account"
            ).get(id=payment_id, org_id=org_id)
        except Payment.DoesNotExist:
            raise ResourceNotFound(f"Payment {payment_id} not found")


    @staticmethod
    def _validated_exchange_rate(value) -> Decimal:
        """P17/BE-L1: the FX rate contract is 6 dp (wire DecimalField and
        NUMERIC(12,6) column). money() quantizes to the 4-dp MONEY contract
        and silently truncated the rate before storage and before the FX
        math; only the MONETARY products are 4-dp. Validates finite +
        positive at full 6-dp precision.
        """
        if value is None:
            return Decimal("1.000000")
        # P18/BE-L6: the service seam must be typed like every other
        # entry point — a garbage string from a direct (non-DRF) caller
        # is a 400-class ValidationError, not an InvalidOperation 500.
        try:
            rate = Decimal(str(value))
        except (ArithmeticError, TypeError, ValueError) as exc:
            raise ValidationError(
                f"Exchange rate must be a valid decimal number (got {value!r})."
            ) from exc
        if not rate.is_finite():
            raise ValidationError("Exchange rate must be a finite number.")
        if rate <= 0:
            raise ValidationError("Exchange rate must be positive.")
        return rate.quantize(Decimal("0.000001"))

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
        # P17/BE-H2: the payment row is locked for the whole void — the
        # is_voided check is otherwise a TOCTOU (two concurrent voids both
        # read False and both post reversals). Mirrors the P16/BE-M1
        # allocate() lock; ResourceNotFound keeps the not-found contract.
        try:
            payment = Payment.objects.select_for_update().get(id=payment_id, org_id=org_id)
        except Payment.DoesNotExist:
            raise ResourceNotFound(f"Payment {payment_id} not found")

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
            # P16/L9: the Asia/Singapore calendar date (consistent with
            # the journal void path; UTC dates diverge 00:00-07:59 SGT).
            reversal_date = timezone.localdate()
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
        # P20/BE-H1: lock the affected documents FIRST (sorted-id order —
        # the deterministic sequence that closes the AB-BA class between
        # two concurrent voids over shared documents) and recompute under
        # the locks. allocate() and unallocate() (the P19/BE-M3 fix) both
        # hold the invoicing.document lock for this same recompute; the
        # unlocked SUM here could silently lose a concurrently-committed
        # allocation (the P14/H-1 "allocations are the truth" invariant —
        # amount_paid/status diverge until the next allocation event).
        affected_ids = sorted(
            set(
                InvoiceDocument.objects.filter(
                    paymentallocation__payment_id=payment.id
                ).values_list("id", flat=True)
            ),
            key=str,
        )
        affected_documents = []
        for doc_id in affected_ids:
            affected_documents.append(
                InvoiceDocument.objects.select_for_update().get(
                    id=doc_id, org_id=org_id
                )
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
                # P16/L2: restore the pre-payment lifecycle status where
                # evidence exists — an InvoiceNow-transmitted document
                # returns to SENT, not a blanket APPROVED (the
                # transmission state must survive an allocate-void cycle).
                # Email-only sends restore to APPROVED pending a lifecycle
                # evidence column (registered debt).
                document.status = (
                    "SENT" if document.invoicenow_sent_at else "APPROVED"
                )
            elif remaining < document.total_incl:
                document.status = "PARTIALLY_PAID"
            else:
                document.status = "PAID"
            document.save()

        payment.is_voided = True
        payment.notes = f"{payment.notes}\n\nVOIDED: {reason}".strip()
        payment.save()


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
        # P16/BE-M1: lock the PAYMENT row for the payment-level cap check —
        # the document rows are locked below, but without this lock two
        # concurrent allocations against DIFFERENT documents each read
        # already_allocated = 0 and can jointly exceed the payment amount.
        payment = Payment.objects.select_for_update().get(
            id=payment_id, org_id=org_id
        )

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

        # P20/BE-L2: the service seam must gate positive amounts — the DB
        # CHECK chk_allocated_positive turns zero/negative into an
        # untyped IntegrityError for non-DRF callers (the serializers
        # gate it; the seam must too).
        for alloc in allocations:
            if money(alloc["allocated_amount"]) <= 0:
                raise ValidationError(
                    "Allocated amounts must be positive (greater than zero)."
                )

        # P20/BE-M1: pre-lock the deduplicated document ids in sorted
        # order — the user-supplied allocation order is an AB-BA deadlock
        # vector for two concurrent allocations over overlapping document
        # sets (PG 40P01 → untyped 500). The create_entry() sorted
        # account pre-lock (P19/BE-M2) is the pattern.
        document_ids = sorted(
            {str(alloc["document_id"]) for alloc in allocations}
        )
        locked_documents = {}
        for doc_id in document_ids:
            locked_documents[doc_id] = InvoiceDocument.objects.select_for_update().get(
                id=doc_id, org_id=org_id
            )

        for alloc_data in allocations:
            document_id = str(alloc_data["document_id"])
            allocated_amount = money(alloc_data["allocated_amount"])

            # P14/H-1: lock the document row for the balance check + the
            # recompute below — the row was pre-locked in sorted order
            # above (P20/BE-M1); the per-document gates read the locked
            # instance.
            document = locked_documents[document_id]

            if document.contact.id != payment.contact.id:
                raise ValidationError(
                    f"Document {document.document_number} contact does not match payment contact."
                )

            # P14/H-1: allocation-eligible statuses — the same set the
            # serializer now accepts (previously APPROVED/PARTIALLY_PAID
            # here and APPROVED-only at the serializer; a SENT/OVERDUE
            # invoice is billed money-not-yet-received and MUST be
            # allocatable, and VOID/DRAFT never are).
            if document.status not in ("APPROVED", "SENT", "PARTIALLY_PAID", "OVERDUE"):
                raise ValidationError(
                    f"Document {document.document_number} must be APPROVED, SENT, "
                    "PARTIALLY_PAID or OVERDUE for allocation."
                )

            # P14/H-1: an allocation may never exceed the document's
            # outstanding balance. amount_due is the GENERATED
            # (total_incl - amount_paid) column — the pre-P14 code checked
            # only allocations-vs-payment-amount, so a 5000.00 allocation
            # against a 109.00 invoice settled it with amount_due = -4891.
            # (Voided payments release their allocations by DELETE — the
            # same convention the recompute below relies on.)
            already_allocated_to_doc = sum(
                (
                    a.allocated_amount
                    for a in PaymentAllocation.objects.filter(document=document)
                ),
                Decimal("0"),
            )
            outstanding = document.total_incl - already_allocated_to_doc
            if allocated_amount > outstanding:
                raise ValidationError(
                    f"Allocation of {allocated_amount} for document "
                    f"{document.document_number} exceeds its outstanding balance "
                    f"of {outstanding}."
                )

            existing = PaymentAllocation.objects.filter(payment=payment, document=document).first()

            if existing:
                raise ValidationError(
                    f"Payment is already allocated to {document.document_number}."
                )

            # P16/L1: money() (HALF_UP) — consistency with every other
            # money path.
            base_allocated = money(allocated_amount * payment.exchange_rate)

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
    @transaction.atomic()
    def create_received_with_allocations(
        org_id: UUID,
        data: Dict[str, Any],
        user_id: Optional[UUID] = None,
    ) -> Payment:
        """P16/BE-M4: create a received payment AND its allocations in ONE
        transaction. The pre-P16 view called create_received (commits the
        payment + its journal entry) then allocate as a separate
        transaction — an allocation failure (e.g. exceeding a document's
        outstanding) left an orphaned payment behind a 400 response.
        Inner @atomic blocks become savepoints; the outer block is the
        single commit boundary."""
        payment = PaymentService.create_received(org_id=org_id, data=data, user_id=user_id)
        if data.get("allocations"):
            PaymentService.allocate(
                org_id=org_id,
                payment_id=payment.id,
                allocations=data["allocations"],
                user_id=user_id,
            )
        return payment

    @staticmethod
    @transaction.atomic()
    def create_made_with_allocations(
        org_id: UUID,
        data: Dict[str, Any],
        user_id: Optional[UUID] = None,
    ) -> Payment:
        """P16/BE-M4: the make-payment twin of create_received_with_allocations."""
        payment = PaymentService.create_made(org_id=org_id, data=data, user_id=user_id)
        if data.get("allocations"):
            PaymentService.allocate(
                org_id=org_id,
                payment_id=payment.id,
                allocations=data["allocations"],
                user_id=user_id,
            )
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
        # P18/BE-M2 + P19/BE-M3: the payment row lock comes FIRST, then
        # the allocation row, then the document — the pre-P19 shape
        # locked the allocation first, inverting against void()/allocate()
        # (which hold the payment lock and then write allocation rows):
        # T1 unallocate holds the allocation row and waits for the
        # payment; T2 void holds the payment and waits to delete the
        # allocation — the AB-BA deadlock (PG 40P01 → untyped 500).
        # The initial allocation read is unlocked (ids only, stable);
        # the row is re-fetched under the payment lock for current
        # state before any mutation.
        try:
            allocation_ref = PaymentAllocation.objects.get(id=allocation_id, org_id=org_id)
        except PaymentAllocation.DoesNotExist:
            raise ResourceNotFound(f"Allocation {allocation_id} not found")

        payment = Payment.objects.select_for_update().get(id=allocation_ref.payment_id)
        try:
            allocation = PaymentAllocation.objects.select_for_update().get(
                id=allocation_id, org_id=org_id
            )
        except PaymentAllocation.DoesNotExist:
            # Deleted between the unlocked id read and the lock — a
            # concurrent unallocate won; the typed contract holds.
            raise ResourceNotFound(f"Allocation {allocation_id} not found")
        document = InvoiceDocument.objects.select_for_update().get(
            id=allocation_ref.document_id
        )

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
            # P16/L2: same evidence-based restoration as the void path.
            document.status = (
                "SENT" if document.invoicenow_sent_at else "APPROVED"
            )
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
        # P7/F-5 defense-in-depth: the schema (NOT NULL) and the bank-account
        # service already guarantee a GL account, but this money path must
        # fail closed with a clear message if that ever changes — never an
        # AttributeError crash mid-transaction.
        bank_gl_account = payment.bank_account.gl_account
        if bank_gl_account is None:
            raise ValidationError(
                f"Bank account '{payment.bank_account.account_name}' has no GL "
                "account configured — payments cannot be posted to the ledger."
            )

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
