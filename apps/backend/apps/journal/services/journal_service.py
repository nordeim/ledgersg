"""
Journal Entry service for LedgerSG.

Manages double-entry bookkeeping including:
- Journal entry creation with line items
- Debit/credit balance validation
- Automatic posting from invoices
- Reversal entries for voided documents
- Fiscal period validation

FIELD ALIGNMENT (SQL Schema v1.0.2):
- source_type: VARCHAR(30) - matches journal.entry.source_type
- narration: TEXT - matches journal.entry.narration
- source_id: UUID - matches journal.entry.source_id
"""

from datetime import date
from decimal import Decimal
from typing import Any
from uuid import UUID

from django.db import connection, transaction
from django.utils import timezone

from apps.core.models import Account, FiscalPeriod, InvoiceDocument, JournalEntry, JournalLine
from common.decimal_utils import money, sum_money
from common.exceptions import ResourceNotFound, ValidationError

# Journal source types (aligned with SQL schema journal.entry.source_type CHECK constraint)
SOURCE_TYPES = {
    "MANUAL": "Manual Entry",
    "SALES_INVOICE": "Sales Invoice",
    "PURCHASE_INVOICE": "Purchase Invoice",
    "SALES_CREDIT_NOTE": "Sales Credit Note",
    "PURCHASE_CREDIT_NOTE": "Purchase Credit Note",
    "SALES_DEBIT_NOTE": "Sales Debit Note",
    "PURCHASE_DEBIT_NOTE": "Purchase Debit Note",
    "PAYMENT_RECEIVED": "Payment Received",
    "PAYMENT_MADE": "Payment Made",
    "BANK_FEE": "Bank Fee",
    "FX_REVALUATION": "FX Revaluation",
    "YEAR_END": "Year End",
    "OPENING_BALANCE": "Opening Balance",
    "REVERSAL": "Reversal Entry",
}

# Backwards compatibility: map old entry_type values to new source_type
ENTRY_TYPE_TO_SOURCE_TYPE = {
    "MANUAL": "MANUAL",
    "INVOICE": "SALES_INVOICE",
    "CREDIT_NOTE": "SALES_CREDIT_NOTE",
    "PAYMENT": "PAYMENT_RECEIVED",
    "ADJUSTMENT": "MANUAL",
    "REVERSAL": "REVERSAL",
    "OPENING": "OPENING_BALANCE",
    "CLOSING": "YEAR_END",
}

# Legacy constant for backwards compatibility
ENTRY_TYPES = SOURCE_TYPES


class JournalService:
    """Service class for journal entry operations."""

    @staticmethod
    def list_entries(
        org_id: UUID,
        source_type: str | None = None,
        fiscal_period_id: UUID | None = None,
        account_id: UUID | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
        source_id: UUID | None = None,
        entry_type: str | None = None,
        source_document_id: UUID | None = None,
    ) -> list[JournalEntry]:
        """
        List journal entries.

        Args:
            org_id: Organisation ID
            source_type: Filter by source type (SQL schema field)
            fiscal_period_id: Filter by fiscal period
            account_id: Filter by account (lines)
            date_from: Filter from date
            date_to: Filter to date
            source_id: Filter by source document ID
            entry_type: (Deprecated) Use source_type instead
            source_document_id: (Deprecated) Use source_id instead

        Returns:
            List of JournalEntry instances
        """
        queryset = JournalEntry.objects.filter(org_id=org_id)

        # Handle backwards compatibility
        effective_source_type = source_type
        if entry_type and not source_type:
            effective_source_type = ENTRY_TYPE_TO_SOURCE_TYPE.get(entry_type, entry_type)

        if effective_source_type:
            queryset = queryset.filter(source_type=effective_source_type)

        if fiscal_period_id:
            queryset = queryset.filter(fiscal_period_id=fiscal_period_id)

        if date_from:
            queryset = queryset.filter(entry_date__gte=date_from)

        if date_to:
            queryset = queryset.filter(entry_date__lte=date_to)

        # Handle backwards compatibility for source_id
        effective_source_id = source_id or source_document_id
        if effective_source_id:
            queryset = queryset.filter(source_id=effective_source_id)

        if account_id:
            entry_ids = JournalLine.objects.filter(account_id=account_id).values_list(
                "entry_id", flat=True
            )
            queryset = queryset.filter(id__in=entry_ids)

        return list(
            queryset.order_by("-entry_date", "-entry_number").prefetch_related("lines")
        )

    @staticmethod
    def get_entry(org_id: UUID, entry_id: UUID) -> JournalEntry:
        """
        Get journal entry by ID.

        Args:
            org_id: Organisation ID
            entry_id: Journal entry ID

        Returns:
            JournalEntry instance
        """
        try:
            return JournalEntry.objects.get(id=entry_id, org_id=org_id)
        except JournalEntry.DoesNotExist:
            raise ResourceNotFound(f"Journal entry {entry_id} not found")

    @staticmethod
    def create_entry(
        org_id: UUID,
        entry_date: date,
        source_type: str | None = None,
        narration: str | None = None,
        lines: list[dict[str, Any]] | None = None,
        fiscal_period_id: UUID | None = None,
        source_id: UUID | None = None,
        user_id: UUID | None = None,
        entry_type: str | None = None,
        description: str | None = None,
        source_invoice_id: UUID | None = None,
    ) -> JournalEntry:
        """
        Create a new journal entry with lines.

        Args:
            org_id: Organisation ID
            entry_date: Entry date
            source_type: Source type per SQL schema (MANUAL, SALES_INVOICE, etc.)
            narration: Entry narration/description per SQL schema
            lines: List of line dictionaries with:
                - account_id: Account UUID
                - debit: Debit amount (or 0)
                - credit: Credit amount (or 0)
                - description: Line description (optional)
            fiscal_period_id: Fiscal period ID (auto-detected if not provided)
            source_id: Source document ID per SQL schema
            user_id: Creating user ID
            entry_type: (Deprecated) Use source_type instead
            description: (Deprecated) Use narration instead
            source_invoice_id: (Deprecated) Use source_id instead

        Returns:
            Created JournalEntry instance
        """
        # Handle backwards compatibility
        effective_source_type = source_type
        if entry_type and not source_type:
            effective_source_type = ENTRY_TYPE_TO_SOURCE_TYPE.get(entry_type, entry_type)

        effective_narration = narration or description or ""
        effective_source_id = source_id or source_invoice_id

        # Ensure lines is a list
        if lines is None:
            lines = []

        if effective_source_type not in SOURCE_TYPES:
            valid_types = ", ".join(SOURCE_TYPES.keys())
            raise ValidationError(f"Invalid source type. Valid: {valid_types}")

        if len(lines) < 2:
            raise ValidationError("Journal entry must have at least 2 lines.")

        total_debits = sum_money(line.get("debit", 0) for line in lines)
        total_credits = sum_money(line.get("credit", 0) for line in lines)

        # P13/B-13: the service tolerance must match the DB trigger's
        # 0.0001 (database_schema.sql journal trg_journal_line_balance).
        # The old 0.001 let a 0.0002..0.001 imbalance pass here and fail
        # at COMMIT with an unhandled database error (500) instead of this
        # typed 400.
        if abs(total_debits - total_credits) > Decimal("0.0001"):
            raise ValidationError(f"Debits ({total_debits}) must equal credits ({total_credits}).")

        if not fiscal_period_id:
            fiscal_period = JournalService._get_fiscal_period(org_id, entry_date)
            if not fiscal_period:
                raise ValidationError(f"No open fiscal period found for date {entry_date}.")
            fiscal_period_id = fiscal_period.id
        else:
            fiscal_period = JournalService._validate_fiscal_period(org_id, fiscal_period_id)

        # P14/H-3: a manual entry into a GST-filed period changes the
        # basis the filed F5 was computed from — refuse (the amendment
        # flow is the correction path, not back-posting).
        from apps.gst.services.period_lock import assert_not_gst_locked

        assert_not_gst_locked(org_id, entry_date)

        with transaction.atomic():
            # P19/BE-M2 (cont.): lock every referenced account up front,
            # in SORTED order — the per-line lock below serializes the
            # archive gate, but acquiring locks in user line order could
            # deadlock two concurrent entries posting to overlapping
            # account sets in opposite orders (AB-BA). Missing/garbage
            # ids pass through silently here; the per-line gates below
            # produce their typed errors.
            from django.core.exceptions import ValidationError as _DjangoVE

            for _pre_id in sorted(
                {str(l.get("account_id")) for l in lines if l.get("account_id")}
            ):
                try:
                    Account.objects.select_for_update().only("id").get(
                        id=_pre_id, org_id=org_id
                    )
                except (Account.DoesNotExist, ValueError, TypeError, _DjangoVE):
                    pass

            entry_number = JournalService._get_next_entry_number(org_id)

            journal_entry = JournalEntry.objects.create(
                org_id=org_id,
                fiscal_year_id=fiscal_period.fiscal_year.id,
                fiscal_period_id=fiscal_period_id,
                entry_number=entry_number,
                entry_date=entry_date,
                source_type=effective_source_type,
                narration=effective_narration,
                source_id=effective_source_id,
                posted_by_id=user_id,
                posted_at=timezone.now(),
            )

            for line_number, line_data in enumerate(lines, start=1):
                account_id = line_data.get("account_id")
                if not account_id:
                    raise ValidationError("Each line must have an account_id.")

                try:
                    # P19/BE-M2: the account row is locked (we are already
                    # inside the entry's atomic) — a plain SELECT does not
                    # conflict with archive_account()'s row lock, so lines
                    # could land on an account archived a moment earlier.
                    account = Account.objects.select_for_update().get(
                        id=account_id, org_id=org_id
                    )
                except Account.DoesNotExist:
                    raise ResourceNotFound(f"Account {account_id} not found")

                # P18/BE-M3: header accounts are groupings, not posting
                # targets (the schema's documented intent — "cannot post
                # to directly"); archived accounts vanish from the trial
                # balance (is_active=True filter) while their ledger lines
                # remain, silently unbalancing the TB/ledger reconciliation.
                if account.is_header:
                    raise ValidationError(
                        f"Account {account.code} ({account.name}) is a header "
                        "account — lines cannot be posted to it directly. "
                        "Post to one of its active child accounts."
                    )
                if not account.is_active:
                    raise ValidationError(
                        f"Account {account.code} ({account.name}) is inactive "
                        "(archived) — lines cannot be posted to it. Reactivate "
                        "the account or post to an active account."
                    )

                debit = money(line_data.get("debit", 0))
                credit = money(line_data.get("credit", 0))

                if debit == 0 and credit == 0:
                    raise ValidationError("Line must have either debit or credit amount.")

                JournalLine.objects.create(
                    entry=journal_entry,
                    org_id=org_id,
                    account=account,
                    description=line_data.get("description", ""),
                    debit=debit,
                    credit=credit,
                    line_number=line_number,
                )

            return journal_entry

    @staticmethod
    def post_invoice(
        org_id: UUID, invoice: InvoiceDocument, user_id: UUID | None = None
    ) -> JournalEntry:
        """
        Create journal entry for approved invoice or purchase.

        Args:
            org_id: Organisation ID
            invoice: InvoiceDocument instance
            user_id: User ID

        Returns:
            Created JournalEntry instance
        """
        is_purchase = invoice.document_type in ("PURCHASE_INVOICE", "PURCHASE_CREDIT_NOTE", "PURCHASE_DEBIT_NOTE")

        # P11/C-1: credit notes post REVERSED entries — a sales credit note
        # reduces what the customer owes (Cr AR, Dr revenue, Dr GST-output);
        # a purchase credit note reduces what we owe (Dr AP, Cr expense,
        # Cr GST-input). Debit notes keep invoice direction (they increase
        # the claim). Before this, every credit note posted an
        # invoice-shaped entry that INCREASED AR/revenue/GST — a balanced
        # entry, so nothing caught it.
        is_credit_note = invoice.document_type in ("SALES_CREDIT_NOTE", "PURCHASE_CREDIT_NOTE")

        if is_purchase:
            main_account = JournalService._get_ap_account(org_id)
        else:
            main_account = JournalService._get_ar_account(org_id)

        lines = []
        expense_revenue_accounts = {}
        gst_amount = Decimal("0.00")

        for line in invoice.lines.all():
            account_id = line.account_id
            amount = line.line_amount

            if account_id not in expense_revenue_accounts:
                expense_revenue_accounts[account_id] = Decimal("0.00")
            expense_revenue_accounts[account_id] += amount

            gst_amount += line.gst_amount

        total_with_gst = invoice.total_incl

        # Main AR/AP line
        if is_purchase:
            # Liability increases (Credit) — unless it is a purchase
            # credit note, which reduces the liability (Debit)
            lines.append({
                "account_id": main_account.id,
                "debit": total_with_gst if is_credit_note else Decimal("0.00"),
                "credit": Decimal("0.00") if is_credit_note else total_with_gst,
                "description": f"AP for {invoice.document_number}",
            })
        else:
            # Asset increases (Debit) — unless it is a sales credit
            # note, which reduces the receivable (Credit)
            lines.append({
                "account_id": main_account.id,
                "debit": Decimal("0.00") if is_credit_note else total_with_gst,
                "credit": total_with_gst if is_credit_note else Decimal("0.00"),
                "description": f"AR for {invoice.document_number}",
            })

        # Expense/Revenue lines
        for account_id, amount in expense_revenue_accounts.items():
            if is_purchase:
                # Expense increases (Debit) — a purchase credit note
                # reverses it (Credit)
                lines.append({
                    "account_id": account_id,
                    "debit": Decimal("0.00") if is_credit_note else amount,
                    "credit": amount if is_credit_note else Decimal("0.00"),
                    "description": f"Expense for {invoice.document_number}",
                })
            else:
                # Revenue increases (Credit) — a sales credit note
                # reverses it (Debit)
                lines.append({
                    "account_id": account_id,
                    "debit": amount if is_credit_note else Decimal("0.00"),
                    "credit": Decimal("0.00") if is_credit_note else amount,
                    "description": f"Revenue for {invoice.document_number}",
                })

        # Tax lines
        if gst_amount > 0:
            if is_purchase:
                # Input tax (Asset increases - Debit); a purchase credit
                # note reverses it (Credit)
                gst_account = JournalService._get_gst_input_account(org_id)
                lines.append({
                    "account_id": gst_account.id,
                    "debit": Decimal("0.00") if is_credit_note else gst_amount,
                    "credit": gst_amount if is_credit_note else Decimal("0.00"),
                    "description": f"GST Input for {invoice.document_number}",
                })
            else:
                # Output tax (Liability increases - Credit); a sales credit
                # note reverses it (Debit)
                gst_account = JournalService._get_gst_output_account(org_id)
                lines.append({
                    "account_id": gst_account.id,
                    "debit": gst_amount if is_credit_note else Decimal("0.00"),
                    "credit": Decimal("0.00") if is_credit_note else gst_amount,
                    "description": f"GST Output for {invoice.document_number}",
                })

        # Determine source_type
        source_type = invoice.document_type

        journal_entry = JournalService.create_entry(
            org_id=org_id,
            entry_date=invoice.issue_date,
            source_type=source_type,
            narration=f"{invoice.document_type} {invoice.document_number}",
            lines=lines,
            source_id=invoice.id,
            user_id=user_id,
        )

        invoice.journal_entry = journal_entry
        invoice.save()

        return journal_entry

    @staticmethod
    def create_reversal(
        org_id: UUID,
        original_entry_id: UUID,
        reversal_date: date,
        reason: str,
        user_id: UUID | None = None,
    ) -> JournalEntry:
        """
        Create reversal entry for a journal entry.

        Args:
            org_id: Organisation ID
            original_entry_id: Original journal entry ID
            reversal_date: Reversal date
            reason: Reversal reason
            user_id: User ID

        Returns:
            Created reversal JournalEntry instance
        """
        # P17/BE-H1: the original row is locked for the whole reversal and
        # re-checked — a second reversal of the same entry would post the
        # swap-side lines twice (every account misstated 2x) while the
        # trial balance stays balanced. The lock closes the concurrent
        # window; the is_reversed check closes the sequential one.
        with transaction.atomic():
            try:
                original = JournalEntry.objects.select_for_update().get(
                    id=original_entry_id, org_id=org_id
                )
            except JournalEntry.DoesNotExist:
                raise ResourceNotFound(f"Journal entry {original_entry_id} not found")
            if original.is_reversed:
                raise ValidationError(
                    f"Journal entry {original.entry_number} is already reversed; "
                    "a reversal of a reversal is not permitted."
                )

            reversal_lines = []
            for line in original.lines.all():
                reversal_lines.append(
                    {
                        "account_id": line.account_id,
                        "debit": line.credit,
                        "credit": line.debit,
                        "description": f"Reversal of {original.entry_number}: {line.description}",
                    }
                )

            # P13/B-11: both phases must be atomic together. create_entry owns
            # its block, but without an outer wrapper a failure in the marking
            # phase below would leave an orphan reversal next to an unmarked
            # original — permitting a SECOND reversal (double-count) from
            # Celery/shell callers outside a request transaction.
            reversal = JournalService.create_entry(
                org_id=org_id,
                entry_date=reversal_date,
                source_type="REVERSAL",
                narration=f"Reversal of {original.entry_number}: {reason}",
                lines=reversal_lines,
                user_id=user_id,
            )

            # chk_reversal_consistency requires is_reversed and reversed_by_id to
            # flip together: (is_reversed = FALSE AND reversed_by_id IS NULL) OR
            # (is_reversed = TRUE AND reversed_by_id IS NOT NULL)
            original.is_reversed = True
            original.reversed_by = reversal
            original.save()

        return reversal

    @staticmethod
    def void_document_entry(
        org_id: UUID, invoice: InvoiceDocument, user_id: UUID | None = None
    ) -> JournalEntry | None:
        """
        Create reversal entry for voided invoice.

        Args:
            org_id: Organisation ID
            invoice: InvoiceDocument to void
            user_id: User ID

        Returns:
            Reversal JournalEntry or None if no entry exists
        """
        if not invoice.journal_entry_id:
            return None

        # The reversal must land in an OPEN fiscal period. Today is preferred
        # (IRAS: corrections in the current period), but when the current
        # period is closed (e.g. year-end) fall back to the original entry's
        # date — void_document() has already verified that period is open.
        original_entry = JournalService.get_entry(org_id, invoice.journal_entry_id)
        reversal_date = timezone.localdate()
        if not JournalService._get_fiscal_period(org_id, reversal_date):
            reversal_date = original_entry.entry_date

        return JournalService.create_reversal(
            org_id=org_id,
            original_entry_id=invoice.journal_entry_id,
            reversal_date=reversal_date,
            reason=f"Void of {invoice.document_number}",
            user_id=user_id,
        )

    @staticmethod
    def get_account_balance(
        org_id: UUID, account_id: UUID, date_to: date | None = None
    ) -> Decimal:
        """
        Get running balance for an account.

        Args:
            org_id: Organisation ID
            account_id: Account ID
            date_to: Calculate balance up to this date

        Returns:
            Account balance
        """
        from django.db.models import Sum

        # H-01: the JournalLine FK is `entry` (db column entry_id), and no
        # `is_posted` field exists — posting is implied by row existence in
        # the immutable-entry design (rows are only written by create_entry).
        lines = JournalLine.objects.filter(entry__org_id=org_id, account_id=account_id)

        if date_to:
            lines = lines.filter(entry__entry_date__lte=date_to)

        totals = lines.aggregate(total_debits=Sum("debit"), total_credits=Sum("credit"))

        debits = totals["total_debits"] or Decimal("0.00")
        credits = totals["total_credits"] or Decimal("0.00")

        return debits - credits

    @staticmethod
    def get_trial_balance(org_id: UUID, date_to: date | None = None) -> list[dict[str, Any]]:
        """
        Get trial balance.

        Args:
            org_id: Organisation ID
            date_to: Balance as of date

        Returns:
            List of account balances
        """
        from django.db.models import Sum

        # H-01: same FK fix as get_account_balance (`entry`, not
        # `journal_entry`; no `is_posted` predicate). Single grouped query
        # instead of one query per account (N+1 fix).
        lines = JournalLine.objects.filter(entry__org_id=org_id).select_related("account")

        if date_to:
            lines = lines.filter(entry__entry_date__lte=date_to)

        totals = lines.values("account").annotate(
            total_debits=Sum("debit"), total_credits=Sum("credit")
        )

        totals_by_account = {row["account"]: row for row in totals}

        result = []
        for account in Account.objects.filter(org_id=org_id, is_active=True):
            row = totals_by_account.get(account.id)
            if row is None:
                continue  # accounts with no journal activity are not on the TB

            debits = row["total_debits"] or Decimal("0.00")
            credits = row["total_credits"] or Decimal("0.00")
            balance = debits - credits

            result.append(
                {
                    "account_id": str(account.id),
                    "account_code": account.code,
                    "account_name": account.name,
                    "account_type": account.account_type,
                    "total_debits": str(debits),
                    "total_credits": str(credits),
                    "balance": str(balance),
                }
            )

        return result

    @staticmethod
    def _get_next_entry_number(org_id: UUID) -> int:
        """
        Get next journal entry number.

        Args:
            org_id: Organisation ID

        Returns:
            Next entry number as integer (e.g., 42)
        """
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT core.get_next_document_number(%s, %s)", [str(org_id), "JOURNAL_ENTRY"]
            )
            next_num = cursor.fetchone()[0]

        return next_num

    @staticmethod
    def _get_fiscal_period(org_id: UUID, entry_date: date) -> FiscalPeriod | None:
        """
        Get open fiscal period for date.

        Args:
            org_id: Organisation ID
            entry_date: Entry date

        Returns:
            FiscalPeriod instance or None
        """
        try:
            return FiscalPeriod.objects.get(
                org_id=org_id, start_date__lte=entry_date, end_date__gte=entry_date, is_open=True
            )
        except FiscalPeriod.DoesNotExist:
            return None

    @staticmethod
    def _validate_fiscal_period(org_id: UUID, period_id: UUID) -> FiscalPeriod:
        """
        Validate fiscal period exists and is open.

        Args:
            org_id: Organisation ID
            period_id: Fiscal period ID

        Returns:
            FiscalPeriod instance

        Raises:
            ValidationError: If period is closed
            ResourceNotFound: If period doesn't exist
        """
        try:
            period = FiscalPeriod.objects.get(id=period_id, org_id=org_id)
            if not period.is_open:
                raise ValidationError(f"Fiscal period '{period.label}' is closed.")
            return period
        except FiscalPeriod.DoesNotExist:
            raise ResourceNotFound(f"Fiscal period {period_id} not found")

    @staticmethod
    def _resolve_control_account(
        org_id: UUID,
        *,
        code: str,
        names: tuple[str, ...],
        sub_type_code: str | None = None,
        label: str,
        hint: str,
    ) -> Account:
        """
        Resolve a control account EXACTLY and fail closed (P5/H-4).

        Order: exact code -> exact name -> account_sub_type code; header
        accounts are never eligible. The pre-P5 resolvers broad-matched
        whole account types with an unordered .first() — output tax landed
        on 2200 Accrued Expenses and AR could land on any asset. On a
        compliance path, an unknown GL account must raise, never guess.
        """
        base = Account.objects.filter(org_id=org_id, is_header=False, is_active=True)

        account = base.filter(code=code).first()
        if account:
            return account

        account = base.filter(name__in=names).first()
        if account:
            return account

        if sub_type_code:
            account = base.filter(account_sub_type__code=sub_type_code).first()
            if account:
                return account

        raise ValidationError(
            f"No {label} control account found (expected code {code}). {hint}"
        )

    @staticmethod
    def _get_ar_account(org_id: UUID) -> Account:
        """Accounts Receivable: 1200, fail-closed (P5/H-4)."""
        return JournalService._resolve_control_account(
            org_id,
            code="1200",
            names=("Accounts Receivable",),
            sub_type_code="ACCOUNTS_RECEIVABLE",
            label="Accounts Receivable",
            hint="Please set up your Chart of Accounts.",
        )

    @staticmethod
    def _get_ap_account(org_id: UUID) -> Account:
        """Accounts Payable: 2100, fail-closed (P5/H-4)."""
        return JournalService._resolve_control_account(
            org_id,
            code="2100",
            names=("Accounts Payable",),
            sub_type_code="ACCOUNTS_PAYABLE",
            label="Accounts Payable",
            hint="Please set up your Chart of Accounts.",
        )

    @staticmethod
    def _get_gst_input_account(org_id: UUID) -> Account:
        """GST Input Tax: 1600 (seeded only for GST-registered orgs)."""
        return JournalService._resolve_control_account(
            org_id,
            code="1600",
            names=("GST Input Tax",),
            label="GST Input Tax",
            hint="Is the organisation GST-registered? Seed the GST control "
            "accounts (toggle GST registration or re-run the CoA seed).",
        )

    @staticmethod
    def _get_gst_output_account(org_id: UUID) -> Account:
        """GST Output Tax: 2600 (seeded only for GST-registered orgs)."""
        return JournalService._resolve_control_account(
            org_id,
            code="2600",
            names=("GST Output Tax",),
            label="GST Output Tax",
            hint="Is the organisation GST-registered? Seed the GST control "
            "accounts (toggle GST registration or re-run the CoA seed).",
        )
