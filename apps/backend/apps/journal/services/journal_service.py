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

from typing import Optional, List, Dict, Any
from uuid import UUID
from decimal import Decimal
from datetime import date
from django.utils import timezone

from django.db import connection, transaction

from apps.core.models import JournalEntry, JournalLine, Account, FiscalPeriod, InvoiceDocument
from common.exceptions import ValidationError, DuplicateResource, ResourceNotFound
from common.decimal_utils import money, sum_money


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
        source_type: Optional[str] = None,
        fiscal_period_id: Optional[UUID] = None,
        account_id: Optional[UUID] = None,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
        source_id: Optional[UUID] = None,
        entry_type: Optional[str] = None,
        source_document_id: Optional[UUID] = None,
    ) -> List[JournalEntry]:
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

        return list(queryset.order_by("-entry_date", "-entry_number"))

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
        source_type: Optional[str] = None,
        narration: Optional[str] = None,
        lines: Optional[List[Dict[str, Any]]] = None,
        fiscal_period_id: Optional[UUID] = None,
        source_id: Optional[UUID] = None,
        user_id: Optional[UUID] = None,
        entry_type: Optional[str] = None,
        description: Optional[str] = None,
        source_invoice_id: Optional[UUID] = None,
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

        if abs(total_debits - total_credits) > Decimal("0.001"):
            raise ValidationError(f"Debits ({total_debits}) must equal credits ({total_credits}).")

        if not fiscal_period_id:
            fiscal_period = JournalService._get_fiscal_period(org_id, entry_date)
            if not fiscal_period:
                raise ValidationError(f"No open fiscal period found for date {entry_date}.")
            fiscal_period_id = fiscal_period.id
        else:
            fiscal_period = JournalService._validate_fiscal_period(org_id, fiscal_period_id)

        with transaction.atomic():
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

            for line_data in lines:
                account_id = line_data.get("account_id")
                if not account_id:
                    raise ValidationError("Each line must have an account_id.")

                try:
                    account = Account.objects.get(id=account_id, org_id=org_id)
                except Account.DoesNotExist:
                    raise ResourceNotFound(f"Account {account_id} not found")

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
                    line_number=lines.index(line_data) + 1,
                )

            return journal_entry

    @staticmethod
    def post_invoice(
        org_id: UUID, invoice: InvoiceDocument, user_id: Optional[UUID] = None
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
            # Liability increases (Credit)
            lines.append({
                "account_id": main_account.id,
                "debit": Decimal("0.00"),
                "credit": total_with_gst,
                "description": f"AP for {invoice.document_number}",
            })
        else:
            # Asset increases (Debit)
            lines.append({
                "account_id": main_account.id,
                "debit": total_with_gst,
                "credit": Decimal("0.00"),
                "description": f"AR for {invoice.document_number}",
            })

        # Expense/Revenue lines
        for account_id, amount in expense_revenue_accounts.items():
            if is_purchase:
                # Expense increases (Debit)
                lines.append({
                    "account_id": account_id,
                    "debit": amount,
                    "credit": Decimal("0.00"),
                    "description": f"Expense for {invoice.document_number}",
                })
            else:
                # Revenue increases (Credit)
                lines.append({
                    "account_id": account_id,
                    "debit": Decimal("0.00"),
                    "credit": amount,
                    "description": f"Revenue for {invoice.document_number}",
                })

        # Tax lines
        if gst_amount > 0:
            if is_purchase:
                # Input tax (Asset increases - Debit)
                gst_account = JournalService._get_gst_input_account(org_id)
                lines.append({
                    "account_id": gst_account.id,
                    "debit": gst_amount,
                    "credit": Decimal("0.00"),
                    "description": f"GST Input for {invoice.document_number}",
                })
            else:
                # Output tax (Liability increases - Credit)
                gst_account = JournalService._get_gst_output_account(org_id)
                lines.append({
                    "account_id": gst_account.id,
                    "debit": Decimal("0.00"),
                    "credit": gst_amount,
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
        user_id: Optional[UUID] = None,
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
        original = JournalService.get_entry(org_id, original_entry_id)

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

        reversal = JournalService.create_entry(
            org_id=org_id,
            entry_date=reversal_date,
            source_type="REVERSAL",
            narration=f"Reversal of {original.entry_number}: {reason}",
            lines=reversal_lines,
            user_id=user_id,
        )

        original.reversed_by = reversal
        original.save()

        return reversal

    @staticmethod
    def void_document_entry(
        org_id: UUID, invoice: InvoiceDocument, user_id: Optional[UUID] = None
    ) -> Optional[JournalEntry]:
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

        return JournalService.create_reversal(
            org_id=org_id,
            original_entry_id=invoice.journal_entry_id,
            reversal_date=date.today(),
            reason=f"Void of {invoice.document_number}",
            user_id=user_id,
        )

    @staticmethod
    def get_account_balance(
        org_id: UUID, account_id: UUID, date_to: Optional[date] = None
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

        lines = JournalLine.objects.filter(
            journal_entry__org_id=org_id, account_id=account_id, journal_entry__is_posted=True
        )

        if date_to:
            lines = lines.filter(journal_entry__entry_date__lte=date_to)

        totals = lines.aggregate(total_debits=Sum("debit"), total_credits=Sum("credit"))

        debits = totals["total_debits"] or Decimal("0.00")
        credits = totals["total_credits"] or Decimal("0.00")

        return debits - credits

    @staticmethod
    def get_trial_balance(org_id: UUID, date_to: Optional[date] = None) -> List[Dict[str, Any]]:
        """
        Get trial balance.

        Args:
            org_id: Organisation ID
            date_to: Balance as of date

        Returns:
            List of account balances
        """
        from django.db.models import Sum

        accounts = Account.objects.filter(org_id=org_id, is_active=True)

        result = []
        for account in accounts:
            lines = JournalLine.objects.filter(
                journal_entry__org_id=org_id, account=account, journal_entry__is_posted=True
            )

            if date_to:
                lines = lines.filter(journal_entry__entry_date__lte=date_to)

            totals = lines.aggregate(total_debits=Sum("debit"), total_credits=Sum("credit"))

            debits = totals["total_debits"] or Decimal("0.00")
            credits = totals["total_credits"] or Decimal("0.00")
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
    def _get_fiscal_period(org_id: UUID, entry_date: date) -> Optional[FiscalPeriod]:
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
    def _get_ap_account(org_id: UUID) -> Account:
        """
        Get Accounts Payable account.

        Args:
            org_id: Organisation ID

        Returns:
            Account instance
        """
        from django.db.models import Q
        ap_account = Account.objects.filter(
            Q(org_id=org_id) & 
            (Q(code="2100") | Q(account_type="LIABILITY_CURRENT") | Q(account_type="LIABILITY"))
        ).first()

        if not ap_account:
            raise ValidationError(
                "No Accounts Payable account found. Please set up Chart of Accounts."
            )

        return ap_account

    @staticmethod
    def _get_gst_input_account(org_id: UUID) -> Account:
        """
        Get GST Input Tax account.

        Args:
            org_id: Organisation ID

        Returns:
            Account instance
        """
        from django.db.models import Q
        gst_account = Account.objects.filter(
            Q(org_id=org_id) & 
            (Q(code__startswith="120") | Q(account_type="ASSET_CURRENT") | Q(account_type="ASSET"))
        ).first()

        if not gst_account:
            raise ValidationError(
                "No GST Input Tax account found. Please set up Chart of Accounts."
            )

        return gst_account

    @staticmethod
    def _get_ar_account(org_id: UUID) -> Account:
        """
        Get Accounts Receivable account.

        Args:
            org_id: Organisation ID

        Returns:
            Account instance
        """
        from django.db.models import Q
        ar_account = Account.objects.filter(
            Q(org_id=org_id) & 
            (Q(code="1200") | Q(account_type="ASSET_CURRENT") | Q(account_type="ASSET"))
        ).first()

        if not ar_account:
            raise ValidationError(
                "No Accounts Receivable account found. Please set up Chart of Accounts."
            )

        return ar_account

    @staticmethod
    def _get_gst_output_account(org_id: UUID) -> Account:
        """
        Get GST Output Tax account.

        Args:
            org_id: Organisation ID

        Returns:
            Account instance
        """
        from django.db.models import Q
        gst_account = Account.objects.filter(
            Q(org_id=org_id) & 
            (Q(code__startswith="220") | Q(account_type="LIABILITY_CURRENT") | Q(account_type="LIABILITY"))
        ).first()

        if not gst_account:
            raise ValidationError(
                "No GST Output Tax account found. Please set up Chart of Accounts."
            )

        return gst_account
