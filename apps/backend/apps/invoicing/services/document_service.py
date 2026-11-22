"""
Document service for LedgerSG Invoicing module.

Handles invoices, quotes, credit notes, debit notes including:
- Document creation with line items
- GST calculation per line
- Document sequencing
- Status workflow management
- Journal posting on approval
"""

import io
from datetime import date, timedelta
from decimal import Decimal
from typing import Any
from uuid import UUID, uuid4

from django.db import connection, transaction
from django.template.loader import render_to_string
from django.utils import timezone
from weasyprint import HTML

from apps.core.models import Account, Contact, InvoiceDocument, InvoiceLine
from apps.gst.services import GSTCalculationService, TaxCodeService
from common.decimal_utils import money, sum_money
from common.exceptions import ResourceNotFound, ValidationError

# Document type definitions - matches SQL ENUM invoicing.doc_type
DOCUMENT_TYPES = {
    "SALES_INVOICE": {"prefix": "INV", "next_status": "SENT"},
    "SALES_CREDIT_NOTE": {"prefix": "CN", "next_status": "APPROVED"},
    "SALES_DEBIT_NOTE": {"prefix": "DN", "next_status": "APPROVED"},
    "SALES_QUOTE": {"prefix": "QUO", "next_status": "SENT"},
    "PURCHASE_INVOICE": {"prefix": "PINV", "next_status": "APPROVED"},
    "PURCHASE_CREDIT_NOTE": {"prefix": "PCN", "next_status": "APPROVED"},
    "PURCHASE_DEBIT_NOTE": {"prefix": "PDN", "next_status": "APPROVED"},
    "PURCHASE_ORDER": {"prefix": "PO", "next_status": "SENT"},
}

# Valid status transitions - matches SQL ENUM invoicing.doc_status
STATUS_TRANSITIONS = {
    "DRAFT": ["SENT", "VOID"],
    "SENT": ["APPROVED", "VOID"],
    "APPROVED": ["PARTIALLY_PAID", "PAID", "VOID"],
    "PARTIALLY_PAID": ["PAID", "VOID"],
    # P8/G-3: PAID no longer lists VOID — a paid invoice is remedied with a
    # credit note (voiding would orphan its payment allocations); the
    # advertised map must match what the engine enforces.
    "PAID": [],
    "VOID": [],
    "OVERDUE": ["PAID", "VOID"],
}


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


class DocumentService:
    """Service class for invoice document operations."""

    @staticmethod
    def list_documents(
        org_id: UUID,
        document_type: str | None = None,
        status: str | None = None,
        contact_id: UUID | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
        search: str | None = None,
    ) -> list[InvoiceDocument]:
        """
        List invoice documents.

        Args:
            org_id: Organisation ID
            document_type: Filter by type (INVOICE, QUOTE, etc.)
            status: Filter by status
            contact_id: Filter by contact
            date_from: Filter from date
            date_to: Filter to date
            search: Search document number

        Returns:
            List of InvoiceDocument instances
        """
        queryset = InvoiceDocument.objects.filter(org_id=org_id)

        if document_type:
            queryset = queryset.filter(document_type=document_type)

        if status:
            queryset = queryset.filter(status=status)

        if contact_id:
            queryset = queryset.filter(contact_id=contact_id)

        if date_from:
            queryset = queryset.filter(issue_date__gte=date_from)

        if date_to:
            queryset = queryset.filter(issue_date__lte=date_to)

        if search:
            queryset = queryset.filter(document_number__icontains=search)

        return list(queryset.order_by("-issue_date", "-document_number"))

    @staticmethod
    def get_document(org_id: UUID, document_id: UUID) -> InvoiceDocument:
        """
        Get document by ID.

        Args:
            org_id: Organisation ID
            document_id: Document ID

        Returns:
            InvoiceDocument instance
        """
        try:
            return InvoiceDocument.objects.get(id=document_id, org_id=org_id)
        except InvoiceDocument.DoesNotExist:
            raise ResourceNotFound(f"Document {document_id} not found")

    @staticmethod
    def create_document(
        org_id: UUID,
        document_type: str,
        contact_id: UUID,
        issue_date: date,
        due_date: date | None = None,
        reference: str = "",
        notes: str = "",
        lines: list[dict[str, Any]] = None,
        user_id: UUID | None = None,
    ) -> InvoiceDocument:
        """
        Create a new invoice document with lines.

        Args:
            org_id: Organisation ID
            document_type: Type (INVOICE, QUOTE, CREDIT_NOTE, DEBIT_NOTE)
            contact_id: Contact ID
            issue_date: Issue date
            due_date: Due date (default: issue_date + contact payment terms)
            reference: Customer reference
            notes: Internal notes
            lines: List of line items
            user_id: Creating user ID

        Returns:
            Created InvoiceDocument instance
        """
        if document_type not in DOCUMENT_TYPES:
            valid_types = ", ".join(DOCUMENT_TYPES.keys())
            raise ValidationError(f"Invalid document type. Valid: {valid_types}")

        # Get contact
        try:
            contact = Contact.objects.get(id=contact_id, org_id=org_id)
        except Contact.DoesNotExist:
            raise ResourceNotFound(f"Contact {contact_id} not found")

        # Calculate due date if not provided
        if due_date is None:
            due_date = issue_date + timedelta(days=contact.payment_terms_days)

        # Get next document number
        document_number = DocumentService._get_next_document_number(org_id, document_type)

        with transaction.atomic():
            # Create document
            document = InvoiceDocument.objects.create(
                org_id=org_id,
                document_type=document_type,
                document_number=document_number,
                contact=contact,
                issue_date=issue_date,
                due_date=due_date,
                reference=reference,
                notes=notes,
                status="DRAFT",
            )

            # Add lines
            if lines:
                DocumentService._add_lines(org_id, document, lines)
                DocumentService._recalculate_totals(document)

        return document

    @staticmethod
    def update_document(org_id: UUID, document_id: UUID, **updates) -> InvoiceDocument:
        """
        Update document (only in DRAFT status).

        Args:
            org_id: Organisation ID
            document_id: Document ID
            **updates: Fields to update

        Returns:
            Updated InvoiceDocument instance
        """
        document = DocumentService.get_document(org_id, document_id)

        if document.status != "DRAFT":
            raise ValidationError(
                f"Cannot update document in status '{document.status}'. Only DRAFT documents can be modified."
            )

        allowed_fields = ["due_date", "reference", "notes"]

        for key, value in updates.items():
            if key in allowed_fields and hasattr(document, key):
                setattr(document, key, value)

        document.save()
        return document

    @staticmethod
    def add_line(
        org_id: UUID,
        document_id: UUID,
        account_id: UUID,
        description: str,
        quantity: Decimal,
        unit_price: Decimal,
        tax_code_id: UUID,
        is_bcrs_deposit: bool = False,
        discount_pct: Decimal | None = None,
        **kwargs,
    ) -> InvoiceLine:
        """
        Add a line to a document.

        Args:
            org_id: Organisation ID
            document_id: Document ID
            account_id: Revenue account ID
            description: Line description
            quantity: Quantity
            unit_price: Unit price (gross of discount)
            tax_code_id: Tax code ID
            is_bcrs_deposit: Whether BCRS deposit
            discount_pct: Line discount percent 0-100 (applied server-side —
                the authoritative calculator; matches the client preview)
            **kwargs: Additional fields

        Returns:
            Created InvoiceLine instance
        """
        document = DocumentService.get_document(org_id, document_id)

        if document.status != "DRAFT":
            raise ValidationError("Can only add lines to DRAFT documents.")

        # Validate account
        try:
            account = Account.objects.get(id=account_id, org_id=org_id)
        except Account.DoesNotExist:
            raise ResourceNotFound(f"Account {account_id} not found")

        # Get next line number
        last_line = document.lines.order_by("-line_number").first()
        line_number = (last_line.line_number + 1) if last_line else 1

        # Calculate line totals
        quantity = Decimal(str(quantity))
        unit_price = money(unit_price)

        # Apply the line discount server-side (P3: the client preview always
        # discounted; the persisted line must match — the server is the
        # authoritative calculator). discount_amount is 4dp; the GST base is
        # the discounted net amount.
        discount_pct = (
            money(discount_pct) if discount_pct is not None else Decimal("0.0000")
        )
        if discount_pct < 0 or discount_pct > 100:
            raise ValidationError(
                f"discount_pct must be between 0 and 100 (got {discount_pct})."
            )
        gross_amount = quantity * unit_price
        discount_amount = (gross_amount * discount_pct / Decimal("100")).quantize(
            Decimal("0.0001")
        )
        amount = (gross_amount - discount_amount).quantize(Decimal("0.01"))

        # Get tax code and calculate GST
        tax_code = TaxCodeService.get_tax_code(org_id, tax_code_id)

        # Fail closed on stale rate rows: the snapshot must reflect a code in
        # force on the document's own date (B-3/H-04).
        if not TaxCodeService.is_effective(tax_code, document.issue_date):
            raise ValidationError(
                f"Tax code {tax_code.code} is not effective on the document "
                f"date {document.issue_date.isoformat()}; use the rate row in "
                "force on that date."
            )

        gst_result = GSTCalculationService.calculate_line_gst(
            amount=amount, rate=tax_code.rate or Decimal("0.00"), is_bcrs_deposit=is_bcrs_deposit
        )

        # Calculate line amounts (P5/H-5): the stored subtotal is the SAME
        # 2dp number the GST was calculated on, and the total reconciles to
        # the cent — the pre-P5 code stored a 4dp line_amount (gross -
        # discount) next to a 2dp GST base, so printed subtotals and totals
        # could disagree with the GST by fractions of a cent.
        line_amount = amount
        gst_amount = gst_result["gst_amount"]
        total_amount = (line_amount + gst_amount).quantize(Decimal("0.01"))

        line = InvoiceLine.objects.create(
            org_id=org_id,
            document=document,
            line_number=line_number,
            account=account,
            description=description.strip(),
            quantity=quantity,
            unit_price=unit_price,
            discount_pct=discount_pct,
            discount_amount=discount_amount,
            line_amount=line_amount,
            gst_amount=gst_amount,
            total_amount=total_amount,
            tax_code=tax_code,
            tax_rate=tax_code.rate or Decimal("0.00"),
            is_bcrs_deposit=is_bcrs_deposit,
            **kwargs,
        )

        # Recalculate document totals
        DocumentService._recalculate_totals(document)

        return line

    @staticmethod
    def remove_line(org_id: UUID, document_id: UUID, line_id: UUID) -> None:
        """
        Remove a line from a document.

        Args:
            org_id: Organisation ID
            document_id: Document ID
            line_id: Line ID
        """
        document = DocumentService.get_document(org_id, document_id)

        if document.status != "DRAFT":
            raise ValidationError("Can only remove lines from DRAFT documents.")

        try:
            line = InvoiceLine.objects.get(id=line_id, invoice=document)
            line.delete()
        except InvoiceLine.DoesNotExist:
            raise ResourceNotFound(f"Line {line_id} not found")

        # Recalculate totals
        DocumentService._recalculate_totals(document)

    @staticmethod
    def transition_status(
        org_id: UUID, document_id: UUID, new_status: str, user_id: UUID | None = None
    ) -> InvoiceDocument:
        """
        Transition document status.

        Args:
            org_id: Organisation ID
            document_id: Document ID
            new_status: Target status
            user_id: User making the transition

        Returns:
            Updated InvoiceDocument instance
        """
        document = DocumentService.get_document(org_id, document_id)

        # Validate transition
        valid_transitions = STATUS_TRANSITIONS.get(document.status, [])
        if new_status not in valid_transitions:
            raise ValidationError(
                f"Cannot transition from '{document.status}' to '{new_status}'. "
                f"Valid transitions: {', '.join(valid_transitions) or 'none'}"
            )

        with transaction.atomic():
            old_status = document.status
            document.status = new_status

            # Status-specific actions
            if new_status == "APPROVED":
                document.approved_at = timezone.now()
                document.approved_by_id = user_id

                # Post journal entry (for invoices/credit notes)
                if document.document_type in [
                    "SALES_INVOICE",
                    "SALES_CREDIT_NOTE",
                    "SALES_DEBIT_NOTE",
                    "PURCHASE_INVOICE",
                    "PURCHASE_CREDIT_NOTE",
                    "PURCHASE_DEBIT_NOTE",
                ]:
                    DocumentService._post_journal_entry(org_id, document, user_id)

            elif new_status == "VOID":
                document.voided_at = timezone.now()
                document.voided_by_id = user_id

                # Reverse journal entry if posted (user_id required: journal.entry.posted_by is NOT NULL)
                if document.journal_entry_id:
                    DocumentService._reverse_journal_entry(org_id, document, user_id)

            document.save()

        return document

    @staticmethod
    def convert_quote_to_invoice(
        org_id: UUID, quote_id: UUID, user_id: UUID | None = None
    ) -> InvoiceDocument:
        """
        Convert a quote to an invoice.

        Args:
            org_id: Organisation ID
            quote_id: Quote document ID
            user_id: User converting

        Returns:
            Created InvoiceDocument instance
        """
        quote = DocumentService.get_document(org_id, quote_id)

        if quote.document_type != "SALES_QUOTE":
            raise ValidationError("Only quotes can be converted to invoices.")

        if quote.status not in ["DRAFT", "SENT"]:
            raise ValidationError(f"Cannot convert quote in status '{quote.status}'.")

        with transaction.atomic():
            # Get lines from quote
            lines = []
            for line in quote.lines.all():
                lines.append(
                    {
                        "account_id": line.account_id,
                        "description": line.description,
                        "quantity": line.quantity,
                        "unit_price": line.unit_price,
                        "tax_code_id": line.tax_code_id,
                        "is_bcrs_deposit": line.is_bcrs_deposit,
                    }
                )

            # Create invoice
            invoice = DocumentService.create_document(
                org_id=org_id,
                document_type="SALES_INVOICE",
                contact_id=quote.contact_id,
                issue_date=date.today(),
                due_date=date.today() + timedelta(days=quote.contact.payment_terms_days),
                reference=f"Quote {quote.document_number}",
                notes=quote.notes,
                lines=lines,
                user_id=user_id,
            )

            # Mark quote as approved (converted) - use valid status from SQL enum
            quote.status = "APPROVED"
            quote.converted_to_id = invoice.id
            quote.save()

        return invoice

    @staticmethod
    def _get_next_document_number(org_id: UUID, document_type: str) -> str:
        """
        Get next document number from sequence.

        Args:
            org_id: Organisation ID
            document_type: Document type

        Returns:
            Next document number (e.g., "INV-00042")
        """
        prefix = DOCUMENT_TYPES[document_type]["prefix"]

        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT core.get_next_document_number(%s, %s)", [str(org_id), document_type]
            )
            next_num = cursor.fetchone()[0]

        return f"{prefix}-{next_num:05d}"

    @staticmethod
    def _add_lines(org_id: UUID, document: InvoiceDocument, lines: list[dict[str, Any]]) -> None:
        """
        Add multiple lines to a document.

        Args:
            org_id: Organisation ID
            document: InvoiceDocument instance
            lines: List of line dictionaries
        """
        for line_data in lines:
            account_id = line_data.get("account_id")
            if not account_id:
                raise ValidationError("Line must have an account_id.")

            DocumentService.add_line(
                org_id=org_id,
                document_id=document.id,
                account_id=UUID(str(account_id)),
                description=line_data.get("description", ""),
                quantity=Decimal(str(line_data.get("quantity", 1))),
                unit_price=money(line_data.get("unit_price", 0)),
                tax_code_id=UUID(str(line_data.get("tax_code_id"))),
                is_bcrs_deposit=line_data.get("is_bcrs_deposit", False),
                discount_pct=(
                    Decimal(str(line_data["discount_pct"]))
                    if line_data.get("discount_pct") is not None
                    else None
                ),
            )

    @staticmethod
    def _recalculate_totals(document: InvoiceDocument) -> None:
        """
        Recalculate document totals from lines.

        Args:
            document: InvoiceDocument instance
        """
        lines = document.lines.all()

        subtotal = sum_money(line.line_amount for line in lines)
        gst_total = sum_money(line.gst_amount for line in lines)
        total = subtotal + gst_total

        document.total_excl = subtotal
        document.gst_total = gst_total
        document.total_incl = total
        document.save()

    @staticmethod
    def _post_journal_entry(org_id: UUID, document: InvoiceDocument, user_id: UUID | None = None) -> None:
        """
        Post journal entry for approved document.

        Args:
            org_id: Organisation ID
            document: InvoiceDocument instance
            user_id: User ID performing the action
        """
        from apps.journal.services.journal_service import JournalService
        JournalService.post_invoice(org_id, document, user_id)

    @staticmethod
    def _reverse_journal_entry(org_id: UUID, document: InvoiceDocument, user_id: UUID | None = None) -> None:
        """
        Reverse journal entry for voided document.

        Args:
            org_id: Organisation ID
            document: InvoiceDocument instance
            user_id: User ID performing the action
        """
        from apps.journal.services.journal_service import JournalService
        JournalService.void_document_entry(org_id, document, user_id)

    @staticmethod
    def approve_document(org_id: UUID, document_id: UUID, user) -> InvoiceDocument:
        """
        Approve a document (DRAFT → APPROVED).

        Creates journal entries for the approved document.

        Args:
            org_id: Organisation ID
            document_id: Document ID to approve
            user: User performing the approval

        Returns:
            Approved InvoiceDocument

        Raises:
            ResourceNotFound: If document doesn't exist
            ValidationError: If document is not in DRAFT status
        """
        from apps.core.models import FiscalPeriod

        with transaction.atomic():
            document = InvoiceDocument.objects.select_for_update().get(
                id=document_id, org_id=org_id
            )

            if document.status != "DRAFT":
                raise ValidationError(
                    f"Cannot approve document with status '{document.status}'. "
                    "Only DRAFT documents can be approved."
                )

            # Verify fiscal period is open
            try:
                fiscal_period = FiscalPeriod.objects.get(
                    org_id=org_id,
                    start_date__lte=document.issue_date,
                    end_date__gte=document.issue_date,
                    is_open=True,
                )
            except FiscalPeriod.DoesNotExist:
                raise ValidationError(
                    "No open fiscal period found for the invoice date. "
                    "Please open the fiscal period or change the invoice date."
                )

            # Update document status
            document.status = "APPROVED"
            document.approved_by = user
            document.approved_at = timezone.now()
            document.save()

            # Create journal entries INSIDE the atomic block (C-04):
            # a posting failure must roll back the APPROVED transition so no
            # approved document can exist without its ledger entry.
            DocumentService._post_journal_entry(org_id, document, user.id)

            # Queue for Peppol transmission if configured (InvoiceNow
            # integration) — also inside the transaction so a queueing
            # failure does not leave an inconsistent approval state.
            if document.document_type == "SALES_INVOICE":
                DocumentService._queue_peppol_transmission(document, org_id)

        _invalidate_dashboard_cache(org_id)
        return document

    @staticmethod
    def void_document(org_id: UUID, document_id: UUID, user, reason: str) -> InvoiceDocument:
        """
        Void an approved document (APPROVED → VOID).

        Creates reversal journal entries for the voided document.

        Args:
            org_id: Organisation ID
            document_id: Document ID to void
            user: User performing the void operation
            reason: Reason for voiding

        Returns:
            Voided InvoiceDocument

        Raises:
            ResourceNotFound: If document doesn't exist
            ValidationError: If document is not in APPROVED status
        """
        with transaction.atomic():
            document = InvoiceDocument.objects.select_for_update().get(
                id=document_id, org_id=org_id
            )

            # P8/G-3: the accepted set mirrors STATUS_TRANSITIONS — every
            # source that advertises VOID can actually void (DRAFT is
            # journal-safe: no entry exists to reverse). PAID is refused
            # outright: the accounting remedy for a paid invoice is a credit
            # note, not a void (its allocations would be orphaned).
            if document.status == "PAID":
                raise ValidationError(
                    "A paid invoice cannot be voided. Issue a credit note "
                    "instead, or unallocate the payments first."
                )
            if document.status not in ["DRAFT", "SENT", "APPROVED", "OVERDUE", "PARTIALLY_PAID"]:
                raise ValidationError(
                    f"Cannot void document with status '{document.status}'."
                )

            # P8/G-3: voiding must never orphan payment allocations — the
            # allocation service owns them; refuse until they are released.
            from apps.core.models import PaymentAllocation

            if PaymentAllocation.objects.filter(document_id=document.id).exists():
                raise ValidationError(
                    "This document has payment allocations. Unallocate the "
                    "payments before voiding it."
                )

            # Verify fiscal period is open — but only when there is a
            # journal entry to reverse (P8/G-3: a DRAFT void is a pure
            # status retirement; the period check exists so the REVERSAL
            # lands in an open period, and a draft has none to place).
            if document.journal_entry_id:
                from apps.core.models import FiscalPeriod

                try:
                    FiscalPeriod.objects.get(
                        org_id=org_id,
                        start_date__lte=document.issue_date,
                        end_date__gte=document.issue_date,
                        is_open=True,
                    )
                except FiscalPeriod.DoesNotExist:
                    raise ValidationError(
                        "No open fiscal period found for the invoice date. "
                        "Cannot void invoice in a closed period."
                    )

            # Update document status (C-02: persist void_reason — the DB
            # CHECK chk_void_reason requires it whenever voided_at is set)
            document.status = "VOID"
            document.voided_by = user
            document.voided_at = timezone.now()
            document.void_reason = reason
            document.save()

            # Reverse journal entries (user passed: posted_by is NOT NULL)
            DocumentService._reverse_journal_entry(org_id, document, user.id)

            return document

    @staticmethod
    def generate_pdf(org_id: UUID, document_id: UUID) -> io.BytesIO:
        """
        Generate PDF for a document using WeasyPrint.

        Args:
            org_id: Organisation ID
            document_id: Document ID

        Returns:
            io.BytesIO: In-memory PDF stream

        Raises:
            ResourceNotFound: If document doesn't exist
        """
        context = DocumentService._get_pdf_context(org_id, document_id)

        # Render HTML string
        html_string = render_to_string("invoicing/invoice_pdf.html", context)

        # Create PDF in memory
        output = io.BytesIO()
        HTML(string=html_string).write_pdf(target=output)
        output.seek(0)

        return output

    @staticmethod
    def _get_pdf_context(org_id: UUID, document_id: UUID) -> dict[str, Any]:
        """Gather all data needed for PDF rendering."""
        from apps.core.models import Organisation

        document = DocumentService.get_document(org_id, document_id)
        org = Organisation.objects.get(id=org_id)
        contact = document.contact
        lines = document.lines.all().order_by("line_number")

        return {
            "document": document,
            "org": org,
            "contact": contact,
            "lines": lines,
            "generated_at": timezone.now(),
        }

    @staticmethod
    def send_email(org_id: UUID, document_id: UUID, email_data: dict) -> dict:
        """
        Send document via email.

        Args:
            org_id: Organisation ID
            document_id: Document ID
            email_data: Dictionary with 'to', 'cc', 'bcc', 'message' keys

        Returns:
            Dictionary with email sending result

        Raises:
            ResourceNotFound: If document doesn't exist
            ValidationError: If email data is invalid
        """
        from apps.invoicing.tasks import send_invoice_email_task

        document = DocumentService.get_document(org_id, document_id)

        # Validate recipients
        to_emails = email_data.get("to", [])
        if not to_emails:
            if document.contact.email:
                to_emails = [document.contact.email]
            else:
                raise ValidationError("At least one recipient email is required.")

        # Trigger background task (P8/G-6: cc/bcc travel with the send —
        # they were validated by the serializer since P7 but never reached
        # the task).
        send_invoice_email_task.delay(
            str(org_id), str(document_id), to_emails,
            cc=email_data.get("cc") or [],
            bcc=email_data.get("bcc") or [],
        )

        return {
            "document_id": str(document_id),
            "sent": True,
            "recipients": to_emails,
            "sent_at": timezone.now().isoformat(),
            "message": "Invoice email has been queued for sending.",
        }

    @staticmethod
    def send_invoicenow(org_id: UUID, document_id: UUID, user) -> dict:
        """
        Queue document for InvoiceNow (Peppol) transmission.

        Creates a real PeppolTransmissionLog row and queues the Celery task
        (retry-backed, non-blocking) — the same execution path the approval
        auto-transmit flow uses (P5/C-2: this was a TODO stub returning
        fabricated uuid4s and never touching the transmission pipeline).

        Args:
            org_id: Organisation ID
            document_id: Document ID
            user: User initiating transmission

        Returns:
            Dictionary with transmission status and the REAL log id

        Raises:
            ResourceNotFound: If document doesn't exist
            ValidationError: If document is not approved, customer has no
                Peppol ID, or the organisation has no Peppol configuration
        """
        from apps.peppol.models import (
            OrganisationPeppolSettings,
            PeppolTransmissionLog,
        )
        from apps.peppol.tasks import transmit_peppol_invoice_task

        document = InvoiceDocument.objects.get(id=document_id, org_id=org_id)

        if document.status != "APPROVED":
            raise ValidationError(
                f"Cannot send via InvoiceNow. Document status is '{document.status}'. "
                "Only APPROVED documents can be transmitted."
            )

        # Check if customer has Peppol ID
        if not document.contact.peppol_id:
            raise ValidationError(
                f"Contact '{document.contact.name}' does not have a Peppol ID configured."
            )

        # Organisation must be configured for Peppol before anything is queued
        settings = OrganisationPeppolSettings.objects.filter(org_id=org_id).first()
        if not settings or not settings.is_configured:
            raise ValidationError(
                "InvoiceNow is not configured for this organisation. "
                "Configure an access point (Peppol settings) before transmitting."
            )

        log = PeppolTransmissionLog.objects.create(
            org_id=org_id,
            document_id=document.id,
            status="PENDING",
            access_point_provider=settings.access_point_provider,
            attempt_number=1,
        )

        task = transmit_peppol_invoice_task.delay(str(log.id), str(org_id))

        return {
            "document_id": str(document_id),
            "status": "QUEUED",
            "message_id": None,  # assigned by the access point when it answers
            "transmission_log_id": str(log.id),
            "task_id": task.id if task else None,
            "queued_at": timezone.now().isoformat(),
            "message": "Invoice queued for InvoiceNow transmission",
        }

    @staticmethod
    def get_invoicenow_status(org_id: UUID, document_id: UUID) -> dict:
        """
        Get InvoiceNow transmission status.

        Reports the REAL PeppolTransmissionLog rows for the document
        (P5/C-2: this was a stub always answering NOT_APPLICABLE).

        Args:
            org_id: Organisation ID
            document_id: Document ID

        Returns:
            Dictionary with the latest status and the full log history

        Raises:
            ResourceNotFound: If document doesn't exist
        """
        from apps.peppol.models import (
            OrganisationPeppolSettings,
            PeppolTransmissionLog,
        )

        document = InvoiceDocument.objects.get(id=document_id, org_id=org_id)

        logs = (
            PeppolTransmissionLog.objects.filter(
                org_id=org_id, document_id=document.id
            )
            .order_by("-transmitted_at", "-id")
        )

        settings = OrganisationPeppolSettings.objects.filter(org_id=org_id).first()
        if not settings or not settings.is_configured:
            return {
                "document_id": str(document_id),
                "status": "NOT_CONFIGURED",
                "message_id": None,
                "transmitted_at": None,
                "delivered_at": None,
                "logs": [],
                "message": (
                    "InvoiceNow is not configured for this organisation. "
                    "Configure an access point (Peppol settings) first."
                ),
            }

        if not logs.exists():
            return {
                "document_id": str(document_id),
                "status": "NOT_TRANSMITTED",
                "message_id": None,
                "transmitted_at": None,
                "delivered_at": None,
                "logs": [],
                "message": "This document has not been transmitted via InvoiceNow.",
            }

        latest = logs.first()

        def _iso(value):
            return value.isoformat() if value else None

        return {
            "document_id": str(document_id),
            "status": latest.status,
            "message_id": str(latest.peppol_message_id) if latest.peppol_message_id else None,
            "transmitted_at": _iso(latest.transmitted_at),
            "delivered_at": _iso(latest.response_at) if latest.status == "DELIVERED" else None,
            "logs": [
                {
                    "id": str(log.id),
                    "status": log.status,
                    "attempt_number": log.attempt_number,
                    "timestamp": _iso(log.response_at) or _iso(log.transmitted_at),
                    "error_message": log.error_message or None,
                }
                for log in logs
            ],
            "message": f"Latest transmission status: {latest.status}",
        }

    @staticmethod
    def _queue_peppol_transmission(document, org_id):
        """
        Queue document for Peppol transmission if configured.

        Called automatically when a sales invoice is approved.
        Creates transmission log and queues async task if Peppol
        is enabled and configured for the organization.

        Args:
            document: InvoiceDocument instance (must be SALES_INVOICE)
            org_id: Organisation ID

        Returns:
            str: Celery task ID if queued, None otherwise
        """
        from apps.peppol.models import OrganisationPeppolSettings, PeppolTransmissionLog
        from apps.peppol.tasks import transmit_peppol_invoice_task

        # Check if Peppol enabled and configured
        settings = OrganisationPeppolSettings.objects.filter(org_id=org_id).first()

        if not settings or not settings.is_configured:
            return None

        if not settings.auto_transmit:
            return None

        # Check if recipient has Peppol ID
        if not document.contact or not document.contact.peppol_id:
            return None

        # Create transmission log
        log = PeppolTransmissionLog.objects.create(
            org_id=org_id,
            document_id=document.id,
            status="PENDING",
            access_point_provider=settings.access_point_provider,
            attempt_number=1,
        )

        # Queue async task
        task = transmit_peppol_invoice_task.delay(str(log.id), str(org_id))
        return task.id
