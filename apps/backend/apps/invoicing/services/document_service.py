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
from uuid import UUID

from django.db import connection, transaction
from django.db.models import Prefetch, QuerySet
from django.db.utils import IntegrityError
from django.template.loader import render_to_string
from django.utils import timezone
from weasyprint import HTML

from apps.core.models import Account, Contact, InvoiceDocument, InvoiceLine, Organisation, TaxCode
from apps.gst.services import GSTCalculationService, TaxCodeService
from common.decimal_utils import money, sum_money
from common.exceptions import ResourceNotFound, ValidationError

# Document type definitions - matches SQL ENUM invoicing.doc_type
# Prefixes match the seeded core.document_sequence config exactly
# (P8/Q-3: the schema file is the source of truth — SALES_QUOTE was QUO
# while the seeded sequence promised QT-, PURCHASE_INVOICE PINV vs BILL-).
# Already-issued numbers are stored values and unaffected.
DOCUMENT_TYPES = {
    "SALES_INVOICE": {"prefix": "INV", "next_status": "SENT"},
    "SALES_CREDIT_NOTE": {"prefix": "CN", "next_status": "APPROVED"},
    "SALES_DEBIT_NOTE": {"prefix": "DN", "next_status": "APPROVED"},
    "SALES_QUOTE": {"prefix": "QT", "next_status": "SENT"},
    "PURCHASE_INVOICE": {"prefix": "BILL", "next_status": "APPROVED"},
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
    ) -> QuerySet[InvoiceDocument]:
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
            Lazy InvoiceDocument queryset (P28/BE-H1: the LAZY queryset
            — the view counts via .count() and pages at the SQL level;
            the pre-P28 list() materialisation fetched the entire
            filtered set on every page)
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

        # P17/BE-M7: the list serializer reads contact.name per row —
        # select_related keeps the list O(1) queries.
        # P28/BE-H1: returned LAZY — evaluate inside the request (the
        # RLS tenant context holds there).
        return queryset.select_related("contact").order_by(
            "-issue_date", "-document_number"
        )

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
            # P29/BE-H1: the detail seam fetches the related rows in a
            # bounded, line-count-independent set — the contact rides
            # the document SELECT (select_related) and the lines arrive
            # in ONE joined SELECT carrying account + tax_code (the
            # pre-P29 plain .get() walked both FKs on every line:
            # a 5-line detail paid 14 queries where 3 would do).
            # No order_by on the prefetch — the related manager's
            # default order is the serialized-line contract.
            return (
                InvoiceDocument.objects.select_related("contact")
                .prefetch_related(
                    Prefetch(
                        "lines",
                        queryset=InvoiceLine.objects.select_related(
                            "account", "tax_code"
                        ),
                    )
                )
                .get(id=document_id, org_id=org_id)
            )
        except InvoiceDocument.DoesNotExist as exc:
            raise ResourceNotFound(f"Document {document_id} not found") from exc

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
        related_document_id: UUID | None = None,
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
            related_document_id: The original invoice a credit note
                corrects (REQUIRED for *_CREDIT_NOTE — P14/H-4)

        Returns:
            Created InvoiceDocument instance
        """
        if document_type not in DOCUMENT_TYPES:
            valid_types = ", ".join(DOCUMENT_TYPES.keys())
            raise ValidationError(f"Invalid document type. Valid: {valid_types}")

        # Get contact
        try:
            contact = Contact.objects.get(id=contact_id, org_id=org_id)
        except Contact.DoesNotExist as exc:
            raise ResourceNotFound(f"Contact {contact_id} not found") from exc

        # P14/H-5: only a GST-registered organisation may charge GST, and
        # only within its registration window. The line-level rate is
        # resolved from the dated tax-code row (date-aware since P2); a
        # positive-rate output-tax code on a line is "charging GST".
        org = Organisation.objects.get(id=org_id)
        if lines:
            DocumentService._validate_gst_registration(
                org, issue_date, lines
            )

        # Calculate due date if not provided
        if due_date is None:
            due_date = issue_date + timedelta(days=contact.payment_terms_days)

        # Get next document number
        document_number = DocumentService._get_next_document_number(org_id, document_type)

        with transaction.atomic():
            # P14/H-4: a credit note is the CORRECTION of an original tax
            # invoice (IRAS: "A credit note must show the number and date of
            # the original tax invoice") — the reference is required, the
            # contact must match, and the cumulative credit may not exceed
            # the original total (incl. GST).
            # P18/BE-M6: the call runs INSIDE this atomic block so the
            # original-row lock the validation takes is held until the
            # credit note itself is inserted and committed (a nested atomic
            # is a savepoint; row locks survive savepoint release).
            if document_type in ("SALES_CREDIT_NOTE", "PURCHASE_CREDIT_NOTE"):
                DocumentService._validate_credit_note_reference(
                    org_id=org_id,
                    document_type=document_type,
                    contact_id=contact_id,
                    lines=lines or [],
                    related_document_id=related_document_id,
                )
            # Create document
            document = InvoiceDocument.objects.create(
                org_id=org_id,
                document_type=document_type,
                document_number=document_number,
                contact=contact,
                related_document_id=related_document_id,
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
        # P18/BE-M5: the line-number read (order_by('-line_number').first())
        # and the insert must run under the document row lock — two
        # concurrent adds on the same DRAFT computed the same line_number
        # and the loser hit uq_docline_doc_lineno as an untyped 500. The
        # lock serializes the numbering; any residual constraint violation
        # surfaces as a typed ValidationError.
        with transaction.atomic():
            try:
                document = InvoiceDocument.objects.select_for_update().get(
                    id=document_id, org_id=org_id
                )
            except InvoiceDocument.DoesNotExist as exc:
                raise ResourceNotFound(f"Document {document_id} not found") from exc

            if document.status != "DRAFT":
                raise ValidationError("Can only add lines to DRAFT documents.")

            # Validate account
            try:
                account = Account.objects.get(id=account_id, org_id=org_id)
            except Account.DoesNotExist as exc:
                raise ResourceNotFound(f"Account {account_id} not found") from exc

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

            try:
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
            except IntegrityError as exc:
                # An interleaved write beat us to the computed line_number —
                # the typed contract, never an untyped 500.
                raise ValidationError(
                    "The document changed while the line was being added "
                    "(concurrent line numbering) — reload and retry."
                ) from exc

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
        # P19/BE-H1: the line-number read, the delete and the totals
        # recompute must run under the document row lock — the pre-P19
        # shape (plain get_document() + DRAFT gate + delete + save)
        # interleaved with approve_document() (which holds the lock): a
        # concurrent approval committed between the gate read and the
        # save, and remove_line then overwrote the totals — and
        # regressed the status — of an APPROVED, journal-posted
        # document. Mirrors add_line()'s P18/BE-M5 structure. (The
        # filter also fixed a latent FieldError: the InvoiceLine FK is
        # `document`, not `invoice` — the pre-P19 method 500'd on
        # every call.)
        with transaction.atomic():
            try:
                document = InvoiceDocument.objects.select_for_update().get(
                    id=document_id, org_id=org_id
                )
            except InvoiceDocument.DoesNotExist as exc:
                raise ResourceNotFound(f"Document {document_id} not found") from exc

            if document.status != "DRAFT":
                raise ValidationError("Can only remove lines from DRAFT documents.")

            try:
                line = InvoiceLine.objects.get(id=line_id, document=document)
                line.delete()
            except InvoiceLine.DoesNotExist as exc:
                raise ResourceNotFound(f"Line {line_id} not found") from exc

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
        # P20/BE-H3: lock the row and re-validate post-lock — the plain
        # read + stale full-row save could overwrite a concurrent
        # approve_document() commit (which holds the lock): the stale
        # save wrote SENT over an APPROVED, journal-posted document and
        # clobbered totals with pre-add_line values (the exact TOCTOU
        # P19/BE-H1 closed for remove_line()).
        with transaction.atomic():
            try:
                document = InvoiceDocument.objects.select_for_update().get(
                    id=document_id, org_id=org_id
                )
            except InvoiceDocument.DoesNotExist as exc:
                raise ResourceNotFound(f"Document {document_id} not found") from exc

            # Validate transition — POST-LOCK against the current status
            valid_transitions = STATUS_TRANSITIONS.get(document.status, [])
            if new_status not in valid_transitions:
                raise ValidationError(
                    f"Cannot transition from '{document.status}' to '{new_status}'. "
                    f"Valid transitions: {', '.join(valid_transitions) or 'none'}"
                )
            # P32/BE-P32-H1: the old_status binding was dead (a refactor
            # leftover — nothing consumed the pre-transition snapshot).
            document.status = new_status

            # P14/H-3: APPROVE posts and VOID reverses into the ledger —
            # both change the basis a filed F5 was computed from. Refuse
            # when the document's issue date falls inside a GST-filed
            # period (corrections go through the amendment flow).
            if new_status in ("APPROVED", "VOID"):
                from apps.gst.services.period_lock import assert_not_gst_locked

                assert_not_gst_locked(org_id, document.issue_date)

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
                # P9/K-1: one engine, one contract — the generic endpoint
                # delegates to void_document (allocation guard, reason
                # requirement, credit-note guidance for PAID). The inline
                # branch bypassed all of it.
                #
                # P10/M-2: fail CLOSED on a missing/unknown poster — the
                # reversing journal entry's posted_by is NOT NULL, so a
                # void without an accountable user must refuse with a
                # clean error, never post anonymously (and never crash
                # with AttributeError/DoesNotExist).
                from apps.core.models import AppUser

                if user_id is None:
                    raise ValidationError(
                        "A user_id is required to void a document — the "
                        "reversing journal entry needs a poster."
                    )
                try:
                    void_user = AppUser.objects.get(id=user_id)
                except AppUser.DoesNotExist as exc:
                    raise ValidationError(
                        f"User {user_id} does not exist — the reversing "
                        "journal entry needs a valid poster."
                    ) from exc
                return DocumentService.void_document(
                    org_id, document.id, user=void_user, reason="Voided via status transition"
                )

            # P20/BE-H3: update_fields only — the stale full-row save
            # clobbered concurrently-committed totals (add_line/remove_line
            # recompute them under the same lock; a full-row save here
            # reverted them).
            update_fields = ["status"]
            if new_status == "APPROVED":
                update_fields += ["approved_at", "approved_by_id"]
            document.save(update_fields=update_fields)

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
        # P18/BE-M4: the status gate + the conversion must run under the
        # quote row lock — the pre-P18 shape checked DRAFT/SENT before and
        # outside any transaction, so two concurrent converts both passed
        # the gate and created two invoices (double journal postings once
        # both are approved). The lock + post-lock re-check mirror
        # approve_document.
        with transaction.atomic():
            quote = InvoiceDocument.objects.select_for_update().get(
                id=quote_id, org_id=org_id
            )

            if quote.document_type != "SALES_QUOTE":
                raise ValidationError("Only quotes can be converted to invoices.")

            if quote.status not in ["DRAFT", "SENT"]:
                raise ValidationError(
                    f"Cannot convert quote in status '{quote.status}'."
                )
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
                issue_date=timezone.localdate(),
                due_date=timezone.localdate() + timedelta(days=quote.contact.payment_terms_days),
                reference=f"Quote {quote.document_number}",
                notes=quote.notes,
                lines=lines,
                user_id=user_id,
            )

            # Mark quote as approved (converted) - use valid status from SQL enum
            # P8/Q-1: persist the link through the REAL field — the old
            # converted_to_id assignment set a transient attribute that
            # save() silently discarded, so the quote→invoice link never
            # existed in the database.
            quote.status = "APPROVED"
            quote.related_document = invoice
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
    def _validate_gst_registration(
        org: Organisation, issue_date: date, lines: list[dict[str, Any]]
    ) -> None:
        """P14/H-5 — refuse GST-charging lines for an organisation that is
        not GST-registered, or outside its registration window.

        "Charging GST" = a line whose tax code resolves a positive rate
        for an output/supply box. Zero-rated (ZR) and exempt (ES) codes
        carry rate 0 and stay valid for unregistered orgs.
        """
        gst_charging = False
        for line_data in lines:
            tax_code_id = line_data.get("tax_code_id")
            if not tax_code_id:
                continue
            try:
                tax_code = TaxCode.objects.get(id=tax_code_id, org_id=org.id)
            except TaxCode.DoesNotExist:
                # system rows (org_id IS NULL)
                try:
                    tax_code = TaxCode.objects.get(id=tax_code_id, org_id__isnull=True)
                except TaxCode.DoesNotExist:
                    continue
            if tax_code.rate and tax_code.rate > 0:
                gst_charging = True
                break

        if not gst_charging:
            return

        if not org.gst_registered:
            raise ValidationError(
                "This organisation is not GST-registered and cannot charge "
                "GST. Use a zero-rated or out-of-scope tax code."
            )
        if org.gst_reg_date and issue_date < org.gst_reg_date:
            raise ValidationError(
                f"Cannot charge GST before the GST registration date "
                f"({org.gst_reg_date})."
            )
        if getattr(org, "gst_dereg_date", None) and issue_date > org.gst_dereg_date:
            raise ValidationError(
                f"Cannot charge GST after the GST deregistration date "
                f"({org.gst_dereg_date})."
            )

    @staticmethod
    def _validate_credit_note_reference(
        org_id: UUID,
        document_type: str,
        contact_id: UUID,
        lines: list[dict[str, Any]],
        related_document_id: UUID | None,
    ) -> None:
        """P14/H-4 — a credit note corrects a specific original invoice.

        Requires: the original document reference, same contact, same
        direction (SALES corrects SALES, PURCHASE corrects PURCHASE),
        non-VOID original, and the cumulative credited amount (incl. GST)
        capped at the original total (incl. GST).
        """
        if not related_document_id:
            raise ValidationError(
                "A credit note must reference the original invoice it "
                "corrects (related_document_id)."
            )

        # P18/BE-M2/M6: the whole check+cap read must run under the
        # ORIGINAL document row lock — the pre-P18 shape read the original
        # and summed existing credits with no lock, so two concurrent credit
        # notes each saw the same headroom and jointly exceeded the cap
        # (P14/H-4 defeated by racing). create_document calls this INSIDE its
        # own atomic block, so the lock holds until the note is inserted and
        # committed; the self-wrapped atomic keeps standalone calls valid
        # (a nested atomic becomes a savepoint; row locks survive savepoint
        # release until the outer commit).
        with transaction.atomic():
            try:
                original = InvoiceDocument.objects.select_for_update().get(
                    id=related_document_id, org_id=org_id
                )
            except InvoiceDocument.DoesNotExist as exc:
                raise ResourceNotFound(
                    f"Original document {related_document_id} not found in this organisation."
                ) from exc

            original_prefix = "SALES" if document_type == "SALES_CREDIT_NOTE" else "PURCHASE"
            if not original.document_type.startswith(original_prefix):
                raise ValidationError(
                    f"A {document_type} must reference a {original_prefix} document "
                    f"(got {original.document_type})."
                )

            if str(original.contact_id) != str(contact_id):
                raise ValidationError(
                    "The credit note contact must match the original invoice's contact."
                )

            if original.status == "VOID":
                raise ValidationError(
                    "Cannot issue a credit note against a VOID document."
                )

            # Cumulative cap: existing approved-or-better credit notes against
            # the original + this one's gross total (incl. GST).
            existing_credits = InvoiceDocument.objects.filter(
                org_id=org_id,
                related_document_id=related_document_id,
                document_type=document_type,
            ).exclude(status="VOID")
            already_credited = sum(
                (d.total_incl or Decimal("0") for d in existing_credits),
                Decimal("0"),
            )

            # This note's total: compute from the line payloads (the same
            # arithmetic _add_lines will apply) — quantity × unit_price, GST
            # at the line's tax rate.
            this_total = Decimal("0")
            for line_data in lines:
                quantity = Decimal(str(line_data.get("quantity", 1)))
                unit_price = money(line_data.get("unit_price", 0))
                line_amount = quantity * unit_price
                tax_code_id = line_data.get("tax_code_id")
                rate = Decimal("0")
                if tax_code_id:
                    tax_code = TaxCode.objects.filter(id=tax_code_id).first()
                    if tax_code and tax_code.rate:
                        rate = tax_code.rate
                this_total += line_amount * (Decimal("1") + rate)

            if already_credited + this_total > (original.total_incl or Decimal("0")):
                raise ValidationError(
                    f"Cumulative credit ({already_credited + this_total}) exceeds the "
                    f"original invoice total ({original.total_incl})."
                )

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
            # P32/BE-P32-H1: the fiscal_period binding was dead (the
            # membership check is the point — the guard-query get).
            try:
                FiscalPeriod.objects.get(
                    org_id=org_id,
                    start_date__lte=document.issue_date,
                    end_date__gte=document.issue_date,
                    is_open=True,
                )
            except FiscalPeriod.DoesNotExist as exc:
                raise ValidationError(
                    "No open fiscal period found for the invoice date. "
                    "Please open the fiscal period or change the invoice date."
                ) from exc

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
            # P38/BE-P38-H1: both OUTBOUND transmittable types queue on
            # approval (the pipeline has dispatched credit notes through
            # the type-aware seam since P34; the SALES_INVOICE-only
            # condition here was the other half of the workflow block).
            if document.document_type in ("SALES_INVOICE", "SALES_CREDIT_NOTE"):
                DocumentService._queue_peppol_transmission(document, org_id)

        _invalidate_dashboard_cache(org_id)
        return document

    @staticmethod
    def void_document(org_id: UUID, document_id: UUID, user, reason: str) -> InvoiceDocument:
        """
        Void a document (P8/G-3: DRAFT/SENT/APPROVED/OVERDUE/PARTIALLY_PAID
        → VOID; PAID is refused — a credit note is the remedy).

        Creates a reversal journal entry when one exists (drafts have
        nothing to reverse), refuses while payment allocations exist, and
        requires a non-empty reason.

        Args:
            org_id: Organisation ID
            document_id: Document ID to void
            user: User performing the void operation
            reason: Reason for voiding (required, non-empty)

        Returns:
            Voided InvoiceDocument

        Raises:
            ResourceNotFound: If document doesn't exist
            ValidationError: If the status is not in the accepted set, the
                document is PAID, or allocations still exist
        """
        with transaction.atomic():
            document = InvoiceDocument.objects.select_for_update().get(
                id=document_id, org_id=org_id
            )

            # P14/H-3: voiding reverses the posting — the ledger basis of
            # a filed F5 covering the issue date must not change.
            from apps.gst.services.period_lock import assert_not_gst_locked

            assert_not_gst_locked(org_id, document.issue_date)

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
                except FiscalPeriod.DoesNotExist as exc:
                    raise ValidationError(
                        "No open fiscal period found for the invoice date. "
                        "Cannot void invoice in a closed period."
                    ) from exc

            # Update document status (C-02: persist void_reason — the DB
            # CHECK chk_void_reason requires it whenever voided_at is set)
            document.status = "VOID"
            document.voided_by = user
            document.voided_at = timezone.now()
            document.void_reason = reason
            document.save()

            # Reverse journal entries (user passed: posted_by is NOT NULL)
            DocumentService._reverse_journal_entry(org_id, document, user.id)

            # P21/BE-M2: a void reverses ledger postings and changes
            # outstanding AR the dashboard reads — the mutation contract
            # (P5/H-3) requires the invalidation here too (approve had it;
            # void did not). Registered on commit (BE-M3).
            _invalidate_dashboard_cache(org_id)

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

        # P8/Q-4b: quotations render their own template — the invoice
        # template titles every document "TAX INVOICE", which is materially
        # wrong for a quote (IRAS labelling is invoice-specific).
        template = (
            "invoicing/quote_pdf.html"
            if context["document"].document_type == "SALES_QUOTE"
            else "invoicing/invoice_pdf.html"
        )

        # Render HTML string
        html_string = render_to_string(template, context)

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

        # P37/BE-P37-H1: the credit-note reference block — the IRAS
        # requirement ("a credit note must show the number and date of the
        # original tax invoice"). The read is type-gated so invoice PDFs
        # keep their exact query count (the P29 discipline); the DB layer
        # guarantees the FK on every credit note (P14/H-4).
        related_document = None
        if document.document_type in ("SALES_CREDIT_NOTE", "PURCHASE_CREDIT_NOTE"):
            related_document = document.related_document

        return {
            "document": document,
            "org": org,
            "contact": contact,
            "lines": lines,
            "related_document": related_document,
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
        from common.tenant_context import queue_task

        document = DocumentService.get_document(org_id, document_id)

        # P18/BE-L5: the emailed PDF is a rendered TAX INVOICE (IRAS
        # labelling is status-bound) — the same gate send_invoicenow
        # carries. VOID/DRAFT/quote documents must not reach a customer's
        # inbox as an invoice.
        if document.document_type != "SALES_INVOICE":
            raise ValidationError(
                f"Cannot email document. Document type is "
                f"'{document.document_type}'. Only SALES_INVOICE documents "
                "can be emailed as tax invoices."
            )
        if document.status not in ("APPROVED", "PARTIALLY_PAID", "PAID"):
            raise ValidationError(
                f"Cannot email document. Document status is '{document.status}'. "
                "Only APPROVED (or settled) documents can be emailed."
            )

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
        # P17/BE-H3: queue_task defers dispatch past the request commit in
        # non-eager mode (a worker must never race the uncommitted row);
        # eager mode keeps the synchronous contract the tests pin.
        queue_task(
            send_invoice_email_task,
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

        # P13/B-10: typed 404 contract — a missing document must surface
        # ResourceNotFound (404 envelope), not a raw DoesNotExist 500.
        document = DocumentService.get_document(org_id, document_id)

        # P9/C-3: InvoiceNow is an outbound fiscal-document transmission
        # channel. The mapping layer renders anything non-credit-note as a
        # UBL Invoice, so a quote sent here would be delivered as a tax
        # invoice into the recipient's AP pipeline. Refuse everything
        # outside the outbound transmittable set before anything is
        # queued.
        # P38/BE-P38-H1: the gate was calibrated pre-P34, when the credit-
        # note transmission path was hollow (header-only UBL — P34/BE-P34
        # H1(a)) — at that time accepting a credit note here would have
        # transmitted a meaningless document. The pipeline has been
        # type-aware end-to-end since P34 (the generator + the validator
        # dispatch by root) and reference-truthful since P37
        # (cac:BillingReference + BR-SG-07, sound because the DB layer
        # enforces related_document_id on every credit note — P14/H-4),
        # so the outbound set now includes SALES_CREDIT_NOTE — the IRAS
        # e-Tax Guide on the GST InvoiceNow requirement (§11.6) expects
        # credit note data on the InvoiceNow channel when the business
        # transmits invoices that way.
        if document.document_type not in ("SALES_INVOICE", "SALES_CREDIT_NOTE"):
            raise ValidationError(
                f"Cannot send via InvoiceNow. Document type is "
                f"'{document.document_type}'. Only SALES_INVOICE and "
                "SALES_CREDIT_NOTE documents can be transmitted."
            )

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

        from common.tenant_context import queue_task

        task = queue_task(transmit_peppol_invoice_task, str(log.id), str(org_id))

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

        # P13/B-10: typed 404 contract — same as send_invoicenow.
        document = DocumentService.get_document(org_id, document_id)

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

        Called automatically when an outbound transmittable document
        (SALES_INVOICE or SALES_CREDIT_NOTE — the set the caller gates
        on, P38/BE-P38-H1) is approved. Creates transmission log and
        queues async task if Peppol is enabled and configured for the
        organization.

        Args:
            document: InvoiceDocument instance (must be an outbound
                transmittable type — SALES_INVOICE or SALES_CREDIT_NOTE;
                the caller owns the type gate)
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

        # Queue async task (P17/BE-H3: past the commit in non-eager mode)
        from common.tenant_context import queue_task

        task = queue_task(transmit_peppol_invoice_task, str(log.id), str(org_id))
        return task.id if task else None
