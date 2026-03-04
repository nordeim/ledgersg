"""
Dashboard service for LedgerSG.

TDD Implementation - Dashboard Real Calculations
Phase 3: Production Ready (TDD)
Phase 4: Redis Caching (TDD)
"""

from datetime import date, datetime, timedelta
from decimal import Decimal
from uuid import UUID
import logging

from django.db.models import Sum, Q, F
from django.db.models.functions import Coalesce
from django.core.cache import cache

from apps.core.models import (
    InvoiceDocument,
    FiscalYear,
    FiscalPeriod,
    BankAccount,
    Payment,
    JournalLine,
    BankTransaction,
)
from common.decimal_utils import money

logger = logging.getLogger(__name__)


class DashboardService:
    """Service for dashboard data aggregation with real database queries and Redis caching."""

    GST_THRESHOLD_LIMIT = Decimal("1000000.00")
    GST_THRESHOLD_SAFE = Decimal("0.70")
    GST_THRESHOLD_WARNING = Decimal("0.90")
    CACHE_TIMEOUT = 300  # 5 minutes

    def _get_cache_key(self, org_id: str) -> str:
        """Generate cache key for dashboard data."""
        return f"dashboard:{org_id}"

    def invalidate_dashboard_cache(self, org_id: str) -> None:
        """Invalidate dashboard cache for organization."""
        cache_key = self._get_cache_key(org_id)
        cache.delete(cache_key)
        logger.info(f"Invalidated dashboard cache for org:{org_id}")

    def get_dashboard_data(self, org_id: str) -> dict:
        """
        Get dashboard data with 5-minute Redis caching.

        Phase 4 TDD Implementation - Uses cache with fallback to database queries.
        """
        # Try to get from cache
        cache_key = self._get_cache_key(org_id)
        try:
            cached_data = cache.get(cache_key)
            if cached_data is not None:
                logger.debug(f"Cache hit for dashboard:{org_id}")
                return cached_data
        except Exception as e:
            logger.warning(f"Cache get failed for org {org_id}: {e}")

        logger.debug(f"Cache miss for dashboard:{org_id}")

        # Compute from database
        data = self._compute_dashboard_data(org_id)

        # Cache for 5 minutes
        try:
            cache.set(cache_key, data, timeout=self.CACHE_TIMEOUT)
            logger.debug(f"Cached dashboard data for org:{org_id}")
        except Exception as e:
            logger.warning(f"Failed to cache dashboard data: {e}")

        return data

    def _compute_dashboard_data(self, org_id: str) -> dict:
        """
        Compute dashboard data from database (original logic).

        Phase 3 TDD Implementation - Uses real database queries.
        """
        try:
            org_uuid = UUID(org_id) if isinstance(org_id, str) else org_id
        except (ValueError, TypeError):
            logger.error(f"Invalid org_id: {org_id}")
            return self._get_empty_dashboard()

        today = date.today()

        current_quarter = (today.month - 1) // 3 + 1
        period_start = date(today.year, (current_quarter - 1) * 3 + 1, 1)

        if current_quarter == 4:
            period_end = date(today.year, 12, 31)
        else:
            next_month = current_quarter * 3 + 1
            next_year = today.year
            if next_month > 12:
                next_month = 1
                next_year += 1
            period_end = date(next_year, next_month, 1) - timedelta(days=1)

        filing_month = period_end.month + 1
        filing_year = period_end.year
        if filing_month > 12:
            filing_month = 1
            filing_year += 1
        filing_due_date = date(filing_year, filing_month, 30)
        days_remaining = (filing_due_date - today).days

        try:
            fiscal_year = FiscalYear.objects.filter(org_id=org_uuid, is_closed=False).first()

            gst_result = self.calculate_gst_liability(org_id, period_start, period_end)

            revenue_mtd = self.query_revenue_mtd(org_id, today)
            revenue_ytd = (
                self.query_revenue_ytd(org_id, str(fiscal_year.id))
                if fiscal_year
                else Decimal("0.0000")
            )

            outstanding_receivables = self.query_outstanding_receivables(org_id)
            outstanding_payables = self.query_outstanding_payables(org_id)
            cash_on_hand = self.calculate_cash_on_hand(org_id)

            threshold_status = self.query_gst_threshold_status(org_id)
            compliance_alerts = self.generate_compliance_alerts(org_id)

            invoice_counts = self._get_invoice_counts(org_uuid)

            gst_payable = gst_result.get("net_gst", Decimal("0.0000"))

            return {
                "gst_payable": str(gst_payable),
                "gst_payable_display": self._format_display(gst_payable),
                "outstanding_receivables": self._format_display(outstanding_receivables),
                "outstanding_payables": self._format_display(outstanding_payables),
                "revenue_mtd": self._format_display(revenue_mtd),
                "revenue_ytd": self._format_display(revenue_ytd),
                "cash_on_hand": self._format_display(cash_on_hand),
                "gst_threshold_status": threshold_status.get("status", "SAFE"),
                "gst_threshold_utilization": threshold_status.get("utilization", 0),
                "gst_threshold_amount": self._format_display(
                    threshold_status.get("amount", Decimal("0.0000"))
                ),
                "gst_threshold_limit": self._format_display(self.GST_THRESHOLD_LIMIT),
                "compliance_alerts": compliance_alerts,
                "invoices_pending": invoice_counts.get("pending", 0),
                "invoices_overdue": invoice_counts.get("overdue", 0),
                "invoices_peppol_pending": invoice_counts.get("peppol_pending", 0),
                "current_gst_period": {
                    "start_date": period_start.isoformat(),
                    "end_date": period_end.isoformat(),
                    "filing_due_date": filing_due_date.isoformat(),
                    "days_remaining": max(days_remaining, 0),
                },
                "last_updated": datetime.now().isoformat(),
            }

        except Exception as e:
            logger.error(f"Error computing dashboard data for org {org_id}: {e}")
            return self._get_empty_dashboard()

    def _get_empty_dashboard(self) -> dict:
        """Return empty dashboard structure."""
        return {
            "gst_payable": "0.0000",
            "gst_payable_display": "SGD 0.00",
            "outstanding_receivables": "SGD 0.00",
            "outstanding_payables": "SGD 0.00",
            "revenue_mtd": "SGD 0.00",
            "revenue_ytd": "SGD 0.00",
            "cash_on_hand": "SGD 0.00",
            "gst_threshold_status": "SAFE",
            "gst_threshold_utilization": 0,
            "gst_threshold_amount": "SGD 0.00",
            "gst_threshold_limit": "SGD 1,000,000.00",
            "compliance_alerts": [],
            "invoices_pending": 0,
            "invoices_overdue": 0,
            "invoices_peppol_pending": 0,
            "current_gst_period": {
                "start_date": date.today().isoformat(),
                "end_date": date.today().isoformat(),
                "filing_due_date": date.today().isoformat(),
                "days_remaining": 0,
            },
            "last_updated": datetime.now().isoformat(),
        }

    def _format_display(self, amount: Decimal) -> str:
        """Format amount as SGD string with 2 decimal places."""
        try:
            amount_decimal = Decimal(str(amount))
            return f"SGD {amount_decimal:,.2f}"
        except (ValueError, TypeError):
            return "SGD 0.00"

    def query_revenue_mtd(self, org_id: str, today: date) -> Decimal:
        """Query month-to-date revenue from approved sales invoices."""
        org_uuid = UUID(org_id) if isinstance(org_id, str) else org_id
        month_start = today.replace(day=1)

        result = InvoiceDocument.objects.filter(
            org_id=org_uuid,
            document_type__in=["SALES_INVOICE", "SALES_DEBIT_NOTE"],
            status="APPROVED",
            issue_date__gte=month_start,
            issue_date__lte=today,
        ).aggregate(total=Sum("total_excl"))

        return money(result.get("total") or Decimal("0.0000"))

    def query_revenue_ytd(self, org_id: str, fiscal_year_id: str) -> Decimal:
        """Query year-to-date revenue from approved sales invoices."""
        org_uuid = UUID(org_id) if isinstance(org_id, str) else org_id

        try:
            fiscal_year = FiscalYear.objects.get(id=fiscal_year_id, org_id=org_uuid)
        except FiscalYear.DoesNotExist:
            return Decimal("0.0000")

        result = InvoiceDocument.objects.filter(
            org_id=org_uuid,
            document_type__in=["SALES_INVOICE", "SALES_DEBIT_NOTE"],
            status="APPROVED",
            issue_date__gte=fiscal_year.start_date,
            issue_date__lte=fiscal_year.end_date,
        ).aggregate(total=Sum("total_excl"))

        return money(result.get("total") or Decimal("0.0000"))

    def query_outstanding_receivables(self, org_id: str) -> Decimal:
        """Query outstanding receivables from unpaid sales invoices."""
        org_uuid = UUID(org_id) if isinstance(org_id, str) else org_id

        result = (
            InvoiceDocument.objects.filter(
                org_id=org_uuid,
                document_type__in=["SALES_INVOICE", "SALES_DEBIT_NOTE"],
                status__in=["APPROVED", "PARTIALLY_PAID", "OVERDUE"],
            )
            .filter(amount_paid__lt=F("total_incl"))
            .aggregate(total=Sum(F("total_incl") - Coalesce(F("amount_paid"), Decimal("0.0000"))))
        )

        return money(max(result.get("total") or Decimal("0.0000"), Decimal("0.0000")))

    def query_outstanding_payables(self, org_id: str) -> Decimal:
        """Query outstanding payables from unpaid purchase invoices."""
        org_uuid = UUID(org_id) if isinstance(org_id, str) else org_id

        result = (
            InvoiceDocument.objects.filter(
                org_id=org_uuid,
                document_type__in=["PURCHASE_INVOICE", "PURCHASE_DEBIT_NOTE"],
                status__in=["APPROVED", "OVERDUE"],
            )
            .filter(amount_paid__lt=F("total_incl"))
            .aggregate(total=Sum(F("total_incl") - Coalesce(F("amount_paid"), Decimal("0.0000"))))
        )

        return money(max(result.get("total") or Decimal("0.0000"), Decimal("0.0000")))

    def calculate_gst_liability(self, org_id: str, period_start: date, period_end: date) -> dict:
        """Calculate GST liability (output tax - input tax) for a period."""
        org_uuid = UUID(org_id) if isinstance(org_id, str) else org_id

        # Output tax from sales (posted entries only)
        output_result = JournalLine.objects.filter(
            org_id=org_uuid,
            entry__posted_at__isnull=False,  # Posted entries only
            entry__entry_date__gte=period_start,
            entry__entry_date__lte=period_end,
            tax_code__is_output=True,
        ).aggregate(total=Sum("tax_amount"))

        output_tax = money(output_result.get("total") or Decimal("0.0000"))

        # Input tax from purchases (posted entries only)
        input_result = JournalLine.objects.filter(
            org_id=org_uuid,
            entry__posted_at__isnull=False,  # Posted entries only
            entry__entry_date__gte=period_start,
            entry__entry_date__lte=period_end,
            tax_code__is_input=True,
        ).aggregate(total=Sum("tax_amount"))

        input_tax = money(input_result.get("total") or Decimal("0.0000"))

        net_gst = output_tax - input_tax

        return {
            "output_tax": output_tax,
            "input_tax": input_tax,
            "net_gst": net_gst,
        }

    def calculate_cash_on_hand(self, org_id: str) -> Decimal:
        """
        Calculate cash position across all bank accounts.

        Formula: opening_balance + sum(reconciled payments received) - sum(reconciled payments made)
        """
        org_uuid = UUID(org_id) if isinstance(org_id, str) else org_id

        # Get all active bank accounts
        bank_accounts = BankAccount.objects.filter(
            org_id=org_uuid,
            is_active=True,
        )

        total = Decimal("0.0000")

        for account in bank_accounts:
            # Add opening balance
            total += account.opening_balance

            # Add reconciled payments received
            received = Payment.objects.filter(
                bank_account=account,
                payment_type="RECEIVED",
                is_reconciled=True,
                is_voided=False,
            ).aggregate(total=Sum("base_amount"))

            total += received.get("total") or Decimal("0.0000")

            # Subtract reconciled payments made
            made = Payment.objects.filter(
                bank_account=account,
                payment_type="MADE",
                is_reconciled=True,
                is_voided=False,
            ).aggregate(total=Sum("base_amount"))

            total -= made.get("total") or Decimal("0.0000")

        return money(total)

    def query_gst_threshold_status(self, org_id: str) -> dict:
        """Check GST registration threshold status (12-month rolling revenue)."""
        org_uuid = UUID(org_id) if isinstance(org_id, str) else org_id
        today = date.today()
        twelve_months_ago = today - timedelta(days=365)

        result = InvoiceDocument.objects.filter(
            org_id=org_uuid,
            document_type__in=["SALES_INVOICE", "SALES_DEBIT_NOTE"],
            status="APPROVED",
            issue_date__gte=twelve_months_ago,
            issue_date__lte=today,
        ).aggregate(total=Sum("total_excl"))

        amount = money(result.get("total") or Decimal("0.0000"))
        utilization = int((amount / self.GST_THRESHOLD_LIMIT) * 100)

        if utilization >= 90:
            status = "CRITICAL"
        elif utilization >= 70:
            status = "WARNING"
        else:
            status = "SAFE"

        return {
            "status": status,
            "utilization": utilization,
            "amount": amount,
        }

    def generate_compliance_alerts(self, org_id: str) -> list:
        """Generate compliance alerts based on business rules."""
        org_uuid = UUID(org_id) if isinstance(org_id, str) else org_id
        alerts = []

        # Check for overdue invoices
        today = date.today()
        overdue_invoices = (
            InvoiceDocument.objects.filter(
                org_id=org_uuid,
                document_type__in=["SALES_INVOICE", "PURCHASE_INVOICE"],
                status="APPROVED",
                due_date__lt=today,
            )
            .filter(amount_paid__lt=F("total_incl"))
            .count()
        )

        if overdue_invoices > 0:
            alerts.append(
                {
                    "id": f"overdue_{org_id}",
                    "severity": "HIGH",
                    "title": "Overdue Invoices",
                    "message": f"{overdue_invoices} invoice(s) are overdue for payment.",
                    "action_required": "Review and follow up on overdue invoices.",
                }
            )

        # Check for GST filing deadline
        current_quarter = (today.month - 1) // 3 + 1
        if current_quarter == 4:
            period_end = date(today.year, 12, 31)
        else:
            next_month = current_quarter * 3 + 1
            period_end = date(today.year, next_month, 1) - timedelta(days=1)

        filing_month = period_end.month + 1
        filing_year = period_end.year
        if filing_month > 12:
            filing_month = 1
            filing_year += 1
        filing_due_date = date(filing_year, filing_month, 30)
        days_remaining = (filing_due_date - today).days

        if days_remaining <= 14 and days_remaining > 0:
            alerts.append(
                {
                    "id": f"gst_filing_{org_id}",
                    "severity": "MEDIUM",
                    "title": "GST Filing Approaching",
                    "message": f"GST filing due in {days_remaining} days ({filing_due_date.strftime('%d %b %Y')}).",
                    "action_required": "Prepare and submit GST return.",
                }
            )

        return alerts

    def _get_invoice_counts(self, org_uuid: UUID) -> dict:
        """Get counts of invoices by status."""
        pending = InvoiceDocument.objects.filter(
            org_id=org_uuid,
            document_type="SALES_INVOICE",
            status="DRAFT",
        ).count()

        overdue = (
            InvoiceDocument.objects.filter(
                org_id=org_uuid,
                document_type__in=["SALES_INVOICE", "PURCHASE_INVOICE"],
                status__in=["APPROVED", "PARTIALLY_PAID", "OVERDUE"],
                due_date__lt=date.today(),
            )
            .filter(amount_paid__lt=F("total_incl"))
            .count()
        )

        peppol_pending = InvoiceDocument.objects.filter(
            org_id=org_uuid,
            document_type="SALES_INVOICE",
            status="APPROVED",
            invoicenow_status="PENDING",
        ).count()

        return {
            "pending": pending,
            "overdue": overdue,
            "peppol_pending": peppol_pending,
        }
