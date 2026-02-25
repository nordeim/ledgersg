"""
Journal Entry service for LedgerSG.

Manages double-entry bookkeeping including:
- Journal entry creation with line items
- Debit/credit balance validation
- Automatic posting from invoices
- Reversal entries for voided documents
- Fiscal period validation
"""

from typing import Optional, List, Dict, Any
from uuid import UUID
from decimal import Decimal
from datetime import date

from django.db import connection, transaction

from apps.core.models import JournalEntry, JournalLine, Account, FiscalPeriod, InvoiceDocument
from common.exceptions import ValidationError, DuplicateResource, ResourceNotFound
from common.decimal_utils import money, sum_money


# Journal entry types
ENTRY_TYPES = {
    "MANUAL": "Manual Entry",
    "INVOICE": "Invoice Posting",
    "CREDIT_NOTE": "Credit Note Posting",
    "PAYMENT": "Payment",
    "ADJUSTMENT": "Adjustment",
    "REVERSAL": "Reversal Entry",
    "OPENING": "Opening Balance",
    "CLOSING": "Closing Entry",
}


class JournalService:
    """Service class for journal entry operations."""
    
    @staticmethod
    def list_entries(
        org_id: UUID,
        entry_type: Optional[str] = None,
        fiscal_period_id: Optional[UUID] = None,
        account_id: Optional[UUID] = None,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
        source_document_id: Optional[UUID] = None
    ) -> List[JournalEntry]:
        """
        List journal entries.
        
        Args:
            org_id: Organisation ID
            entry_type: Filter by entry type
            fiscal_period_id: Filter by fiscal period
            account_id: Filter by account (lines)
            date_from: Filter from date
            date_to: Filter to date
            source_document_id: Filter by source document
            
        Returns:
            List of JournalEntry instances
        """
        queryset = JournalEntry.objects.filter(org_id=org_id)
        
        if entry_type:
            queryset = queryset.filter(entry_type=entry_type)
        
        if fiscal_period_id:
            queryset = queryset.filter(fiscal_period_id=fiscal_period_id)
        
        if date_from:
            queryset = queryset.filter(entry_date__gte=date_from)
        
        if date_to:
            queryset = queryset.filter(entry_date__lte=date_to)
        
        if source_document_id:
            queryset = queryset.filter(source_invoice_id=source_document_id)
        
        # Filter by account if specified
        if account_id:
            entry_ids = JournalLine.objects.filter(
                account_id=account_id
            ).values_list("journal_entry_id", flat=True)
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
        entry_type: str,
        description: str,
        lines: List[Dict[str, Any]],
        fiscal_period_id: Optional[UUID] = None,
        source_invoice_id: Optional[UUID] = None,
        user_id: Optional[UUID] = None
    ) -> JournalEntry:
        """
        Create a new journal entry with lines.
        
        Args:
            org_id: Organisation ID
            entry_date: Entry date
            entry_type: Entry type (MANUAL, INVOICE, etc.)
            description: Entry description
            lines: List of line dictionaries with:
                - account_id: Account UUID
                - debit: Debit amount (or 0)
                - credit: Credit amount (or 0)
                - description: Line description (optional)
            fiscal_period_id: Fiscal period ID (auto-detected if not provided)
            source_invoice_id: Source invoice document ID
            user_id: Creating user ID
            
        Returns:
            Created JournalEntry instance
        """
        if entry_type not in ENTRY_TYPES:
            valid_types = ", ".join(ENTRY_TYPES.keys())
            raise ValidationError(f"Invalid entry type. Valid: {valid_types}")
        
        # Validate lines
        if len(lines) < 2:
            raise ValidationError("Journal entry must have at least 2 lines.")
        
        # Calculate totals
        total_debits = sum_money(line.get("debit", 0) for line in lines)
        total_credits = sum_money(line.get("credit", 0) for line in lines)
        
        if abs(total_debits - total_credits) > Decimal("0.001"):
            raise ValidationError(
                f"Debits ({total_debits}) must equal credits ({total_credits})."
            )
        
        # Get fiscal period if not provided
        if not fiscal_period_id:
            fiscal_period = JournalService._get_fiscal_period(org_id, entry_date)
            if not fiscal_period:
                raise ValidationError(f"No open fiscal period found for date {entry_date}.")
            fiscal_period_id = fiscal_period.id
        else:
            # Validate fiscal period is open
            fiscal_period = JournalService._validate_fiscal_period(org_id, fiscal_period_id)
        
        with transaction.atomic():
            # Get next entry number
            entry_number = JournalService._get_next_entry_number(org_id)
            
            # Create journal entry
            journal_entry = JournalEntry.objects.create(
                org_id=org_id,
                fiscal_period_id=fiscal_period_id,
                entry_number=entry_number,
                entry_date=entry_date,
                entry_type=entry_type,
                description=description,
                source_invoice_id=source_invoice_id,
                created_by_id=user_id,
                is_posted=True,
                posted_at=timezone.now(),
            )
            
            # Create lines
            for line_data in lines:
                account_id = line_data.get("account_id")
                if not account_id:
                    raise ValidationError("Each line must have an account_id.")
                
                # Validate account
                try:
                    account = Account.objects.get(id=account_id, org_id=org_id)
                except Account.DoesNotExist:
                    raise ResourceNotFound(f"Account {account_id} not found")
                
                debit = money(line_data.get("debit", 0))
                credit = money(line_data.get("credit", 0))
                
                if debit == 0 and credit == 0:
                    raise ValidationError("Line must have either debit or credit amount.")
                
                JournalLine.objects.create(
                    journal_entry=journal_entry,
                    account=account,
                    description=line_data.get("description", ""),
                    debit=debit,
                    credit=credit,
                )
        
        return journal_entry
    
    @staticmethod
    def post_invoice(
        org_id: UUID,
        invoice: InvoiceDocument,
        user_id: Optional[UUID] = None
    ) -> JournalEntry:
        """
        Create journal entry for approved invoice.
        
        Args:
            org_id: Organisation ID
            invoice: InvoiceDocument instance
            user_id: User ID
            
        Returns:
            Created JournalEntry instance
        """
        # Get accounts for posting
        ar_account = JournalService._get_ar_account(org_id)
        
        lines = []
        
        # Group by revenue account and tax
        revenue_accounts = {}
        gst_amount = Decimal("0.00")
        
        for line in invoice.lines.filter(is_voided=False):
            account_id = line.account_id
            amount = line.amount
            
            if account_id not in revenue_accounts:
                revenue_accounts[account_id] = Decimal("0.00")
            revenue_accounts[account_id] += amount
            
            gst_amount += line.gst_amount
        
        # Debit: Accounts Receivable (total with GST)
        total_with_gst = invoice.total
        lines.append({
            "account_id": ar_account.id,
            "debit": total_with_gst,
            "credit": Decimal("0.00"),
            "description": f"AR for {invoice.document_number}"
        })
        
        # Credit: Revenue accounts
        for account_id, amount in revenue_accounts.items():
            lines.append({
                "account_id": account_id,
                "debit": Decimal("0.00"),
                "credit": amount,
                "description": f"Revenue for {invoice.document_number}"
            })
        
        # Credit: GST Output Tax
        if gst_amount > 0:
            gst_account = JournalService._get_gst_output_account(org_id)
            lines.append({
                "account_id": gst_account.id,
                "debit": Decimal("0.00"),
                "credit": gst_amount,
                "description": f"GST Output for {invoice.document_number}"
            })
        
        # Create journal entry
        entry_type = "INVOICE"
        if invoice.document_type == "CREDIT_NOTE":
            entry_type = "CREDIT_NOTE"
        
        journal_entry = JournalService.create_entry(
            org_id=org_id,
            entry_date=invoice.issue_date,
            entry_type=entry_type,
            description=f"{invoice.document_type} {invoice.document_number}",
            lines=lines,
            source_invoice_id=invoice.id,
            user_id=user_id
        )
        
        # Link invoice to journal entry
        invoice.journal_entry = journal_entry
        invoice.save()
        
        return journal_entry
    
    @staticmethod
    def create_reversal(
        org_id: UUID,
        original_entry_id: UUID,
        reversal_date: date,
        reason: str,
        user_id: Optional[UUID] = None
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
        
        # Create reversal lines (swap debits and credits)
        reversal_lines = []
        for line in original.lines.all():
            reversal_lines.append({
                "account_id": line.account_id,
                "debit": line.credit,  # Swap
                "credit": line.debit,   # Swap
                "description": f"Reversal of {original.entry_number}: {line.description}"
            })
        
        # Create reversal entry
        reversal = JournalService.create_entry(
            org_id=org_id,
            entry_date=reversal_date,
            entry_type="REVERSAL",
            description=f"Reversal of {original.entry_number}: {reason}",
            lines=reversal_lines,
            user_id=user_id
        )
        
        # Link reversal
        original.reversed_by = reversal
        original.save()
        
        return reversal
    
    @staticmethod
    def void_document_entry(
        org_id: UUID,
        invoice: InvoiceDocument,
        user_id: Optional[UUID] = None
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
            user_id=user_id
        )
    
    @staticmethod
    def get_account_balance(
        org_id: UUID,
        account_id: UUID,
        date_to: Optional[date] = None
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
            journal_entry__org_id=org_id,
            account_id=account_id,
            journal_entry__is_posted=True
        )
        
        if date_to:
            lines = lines.filter(journal_entry__entry_date__lte=date_to)
        
        totals = lines.aggregate(
            total_debits=Sum("debit"),
            total_credits=Sum("credit")
        )
        
        debits = totals["total_debits"] or Decimal("0.00")
        credits = totals["total_credits"] or Decimal("0.00")
        
        # Balance = Debits - Credits (asset/expense accounts)
        # For liability/equity/revenue, it's reversed in reporting
        return debits - credits
    
    @staticmethod
    def get_trial_balance(
        org_id: UUID,
        date_to: Optional[date] = None
    ) -> List[Dict[str, Any]]:
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
                journal_entry__org_id=org_id,
                account=account,
                journal_entry__is_posted=True
            )
            
            if date_to:
                lines = lines.filter(journal_entry__entry_date__lte=date_to)
            
            totals = lines.aggregate(
                total_debits=Sum("debit"),
                total_credits=Sum("credit")
            )
            
            debits = totals["total_debits"] or Decimal("0.00")
            credits = totals["total_credits"] or Decimal("0.00")
            balance = debits - credits
            
            result.append({
                "account_id": str(account.id),
                "account_code": account.code,
                "account_name": account.name,
                "account_type": account.account_type,
                "total_debits": str(debits),
                "total_credits": str(credits),
                "balance": str(balance),
            })
        
        return result
    
    @staticmethod
    def _get_next_entry_number(org_id: UUID) -> str:
        """
        Get next journal entry number.
        
        Args:
            org_id: Organisation ID
            
        Returns:
            Next entry number (e.g., "JE-00042")
        """
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT core.get_next_document_number(%s, %s)",
                [str(org_id), "JOURNAL_ENTRY"]
            )
            next_num = cursor.fetchone()[0]
        
        return f"JE-{next_num:05d}"
    
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
                org_id=org_id,
                start_date__lte=entry_date,
                end_date__gte=entry_date,
                is_open=True
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
    def _get_ar_account(org_id: UUID) -> Account:
        """
        Get Accounts Receivable account.
        
        Args:
            org_id: Organisation ID
            
        Returns:
            Account instance
        """
        # Try to find AR account by code
        ar_account = Account.objects.filter(
            org_id=org_id,
            code="1200"  # Standard AR code
        ).first()
        
        if not ar_account:
            # Fallback: find any current asset account
            ar_account = Account.objects.filter(
                org_id=org_id,
                account_type="ASSET_CURRENT"
            ).first()
        
        if not ar_account:
            raise ValidationError("No Accounts Receivable account found. Please set up Chart of Accounts.")
        
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
        # Try to find GST output account
        gst_account = Account.objects.filter(
            org_id=org_id,
            code__startswith="220"  # GST output codes
        ).first()
        
        if not gst_account:
            # Fallback: any liability account
            gst_account = Account.objects.filter(
                org_id=org_id,
                account_type="LIABILITY_CURRENT"
            ).first()
        
        if not gst_account:
            raise ValidationError("No GST Output Tax account found. Please set up Chart of Accounts.")
        
        return gst_account


# Import at end to avoid circular imports
from django.utils import timezone
