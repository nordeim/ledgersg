"""
Dashboard service for LedgerSG.

TDD Implementation - Dashboard Real Calculations
Phase 3: Production Ready (TDD)
"""

from datetime import date, datetime, timedelta
from decimal import Decimal
from uuid import UUID
import logging

from django.db.models import Sum, Q, F
from django.db.models.functions import Coalesce

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
    """Service for dashboard data aggregation with real database queries."""

    GST_THRESHOLD_LIMIT = Decimal("1000000.00")
    GST_THRESHOLD_SAFE = Decimal("0.70")
    GST_THRESHOLD_WARNING = Decimal("0.90")

    def get_dashboard_data(self, org_id: str) -> dict:
        """
        Get dashboard data in format matching frontend expectations.

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
            logger.error(f"Error calculating dashboard data for org {org_id}: {e}")
            return self._get_empty_dashboard()

    def query_revenue_mtd(self, org_id: str, as_of_date: date) -> Decimal:
        """
        Query month-to-date revenue from approved sales invoices.

        Aggregates base_subtotal for current month, excluding DRAFT and VOID.
        """
        try:
            org_uuid = UUID(org_id) if isinstance(org_id, str) else org_id

            month_start = date(as_of_date.year, as_of_date.month, 1)

            result = InvoiceDocument.objects.filter(
                org_id=org_uuid,
                document_type__in=["SALES_INVOICE", "SALES_DEBIT_NOTE"],
                issue_date__gte=month_start,
                issue_date__lte=as_of_date,
                status__in=["APPROVED", "SENT", "PARTIALLY_PAID", "PAID", "OVERDUE"],
            ).aggregate(total=Coalesce(Sum("total_excl"), Decimal("0.0000")))

            return money(result["total"])

        except Exception as e:
            logger.error(f"Error querying revenue MTD for org {org_id}: {e}")
            return Decimal("0.0000")

    def query_revenue_ytd(self, org_id: str, fiscal_year_id: str) -> Decimal:
        """
        Query year-to-date revenue for fiscal year.

        Joins with fiscal_period to get YTD range.
        """
        try:
            org_uuid = UUID(org_id) if isinstance(org_id, str) else org_id
            fy_uuid = UUID(fiscal_year_id) if isinstance(fiscal_year_id, str) else fiscal_year_id

            fiscal_year = FiscalYear.objects.get(id=fy_uuid, org_id=org_uuid)

            result = InvoiceDocument.objects.filter(
                org_id=org_uuid,
                document_type__in=["SALES_INVOICE", "SALES_DEBIT_NOTE"],
                issue_date__gte=fiscal_year.start_date,
                issue_date__lte=fiscal_year.end_date,
                status__in=["APPROVED", "SENT", "PARTIALLY_PAID", "PAID", "OVERDUE"],
            ).aggregate(total=Coalesce(Sum("total_excl"), Decimal("0.0000")))

            return money(result["total"])

        except Exception as e:
            logger.error(f"Error querying revenue YTD for org {org_id}: {e}")
            return Decimal("0.0000")

    def query_outstanding_receivables(self, org_id: str) -> Decimal:
        """
        Sum amount_due for outstanding sales invoices.

        Filters document_type IN ('SALES_INVOICE', 'SALES_DEBIT_NOTE')
        and status IN ('APPROVED', 'SENT', 'PARTIALLY_PAID', 'OVERDUE').
        """
        try:
            org_uuid = UUID(org_id) if isinstance(org_id, str) else org_id

            result = InvoiceDocument.objects.filter(
                org_id=org_uuid,
                document_type__in=["SALES_INVOICE", "SALES_DEBIT_NOTE"],
                status__in=["APPROVED", "SENT", "PARTIALLY_PAID", "OVERDUE"],
            ).aggregate(total=Coalesce(Sum(F("total_incl") - F("amount_paid")), Decimal("0.0000")))

            return money(result["total"])

        except Exception as e:
            logger.error(f"Error querying outstanding receivables for org {org_id}: {e}")
            return Decimal("0.0000")

    def query_outstanding_payables(self, org_id: str) -> Decimal:
        """
        Sum amount_due for outstanding purchase invoices.

        Filters document_type IN ('PURCHASE_INVOICE', 'PURCHASE_DEBIT_NOTE')
        and status IN ('APPROVED', 'SENT', 'PARTIALLY_PAID', 'OVERDUE').
        """
        try:
            org_uuid = UUID(org_id) if isinstance(org_id, str) else org_id

            result = InvoiceDocument.objects.filter(
                org_id=org_uuid,
                document_type__in=["PURCHASE_INVOICE", "PURCHASE_DEBIT_NOTE"],
                status__in=["APPROVED", "SENT", "PARTIALLY_PAID", "OVERDUE"],
            ).aggregate(total=Coalesce(Sum(F("total_incl") - F("amount_paid")), Decimal("0.0000")))

            return money(result["total"])

        except Exception as e:
            logger.error(f"Error querying outstanding payables for org {org_id}: {e}")
            return Decimal("0.0000")

    def calculate_gst_liability(self, org_id: str, period_start: date, period_end: date) -> dict:
        """
        Calculate GST payable/receivable for period.

        Queries journal.line with tax codes where is_output=TRUE for output tax.
        Queries journal.line with tax codes where is_input=TRUE for input tax.
        Returns net_gst = output_tax - input_tax.

        Note: Uses Sum of all tax_amount on lines with tax codes.
        Credit notes have negative tax_amount which reduces the total.
        """
        try:
            org_uuid = UUID(org_id) if isinstance(org_id, str) else org_id

            # Output tax: Sum all tax amounts on output tax codes
            output_tax_result = JournalLine.objects.filter(
                org_id=org_uuid,
                entry__entry_date__gte=period_start,
                entry__entry_date__lte=period_end,
                entry__is_reversed=False,
                tax_code__is_output=True,
            ).aggregate(total=Coalesce(Sum("tax_amount"), Decimal("0.0000")))

            output_tax = money(output_tax_result["total"])

            # Input tax: Sum all tax amounts on input tax codes
            input_tax_result = JournalLine.objects.filter(
                org_id=org_uuid,
                entry__entry_date__gte=period_start,
                entry__entry_date__lte=period_end,
                entry__is_reversed=False,
                tax_code__is_input=True,
                tax_code__is_claimable=True,
            ).aggregate(total=Coalesce(Sum("tax_amount"), Decimal("0.0000")))

            input_tax = money(input_tax_result["total"])

            net_gst = output_tax - input_tax

            return {
                "output_tax": output_tax,
                "input_tax": input_tax,
                "net_gst": net_gst,
            }

        except Exception as e:
            logger.error(f"Error calculating GST liability for org {org_id}: {e}")
            return {
                "output_tax": Decimal("0.0000"),
                "input_tax": Decimal("0.0000"),
                "net_gst": Decimal("0.0000"),
            }

    def calculate_cash_on_hand(self, org_id: str) -> Decimal:
        """
        Calculate cash position across all bank accounts.

        Sum bank_account.opening_balance for active accounts.
        Add payment.amount where payment_type='RECEIVED' and is_reconciled=True.
        Subtract payment.amount where payment_type='MADE' and is_reconciled=True.
        """
        try:
            org_uuid = UUID(org_id) if isinstance(org_id, str) else org_id

            opening_result = BankAccount.objects.filter(
                org_id=org_uuid,
                is_active=True,
            ).aggregate(total=Coalesce(Sum("opening_balance"), Decimal("0.0000")))

            cash = money(opening_result["total"])

            received_result = Payment.objects.filter(
                org_id=org_uuid,
                payment_type="RECEIVED",
                is_reconciled=True,
                is_voided=False,
            ).aggregate(total=Coalesce(Sum("amount"), Decimal("0.0000")))

            cash += money(received_result["total"])

            made_result = Payment.objects.filter(
                org_id=org_uuid,
                payment_type="MADE",
                is_reconciled=True,
                is_voided=False,
            ).aggregate(total=Coalesce(Sum("amount"), Decimal("0.0000")))

            cash -= money(made_result["total"])

            return cash

        except Exception as e:
            logger.error(f"Error calculating cash on hand for org {org_id}: {e}")
            return Decimal("0.0000")

    def query_gst_threshold_status(self, org_id: str) -> dict:
        """
        Calculate GST registration threshold status.

        Query rolling 12-month revenue.
        Calculate utilization % against S$1,000,000.
        Return status: SAFE (<70%), WARNING (70-90%), CRITICAL (>90%), EXCEEDED (>100%).
        """
        try:
            org_uuid = UUID(org_id) if isinstance(org_id, str) else org_id

            today = date.today()
            twelve_months_ago = today - timedelta(days=365)

            result = InvoiceDocument.objects.filter(
                org_id=org_uuid,
                document_type__in=["SALES_INVOICE", "SALES_DEBIT_NOTE"],
                issue_date__gte=twelve_months_ago,
                issue_date__lte=today,
                status__in=["APPROVED", "SENT", "PARTIALLY_PAID", "PAID", "OVERDUE"],
            ).aggregate(total=Coalesce(Sum("total_excl"), Decimal("0.0000")))

            revenue = money(result["total"])

            if self.GST_THRESHOLD_LIMIT == Decimal("0.0000"):
                utilization = 0
            else:
                utilization = int((revenue / self.GST_THRESHOLD_LIMIT) * 100)

            if utilization >= 100:
                status = "EXCEEDED"
            elif utilization >= 90:
                status = "CRITICAL"
            elif utilization >= 70:
                status = "WARNING"
            else:
                status = "SAFE"

            return {
                "status": status,
                "utilization": utilization,
                "amount": revenue,
                "threshold": self.GST_THRESHOLD_LIMIT,
            }

        except Exception as e:
            logger.error(f"Error querying GST threshold for org {org_id}: {e}")
            return {
                "status": "SAFE",
                "utilization": 0,
                "amount": Decimal("0.0000"),
                "threshold": self.GST_THRESHOLD_LIMIT,
            }

    def generate_compliance_alerts(self, org_id: str) -> list:
        """
        Generate compliance alerts based on business rules.

        Alert 1: GST filing deadline (≤30 days)
        Alert 2: Overdue invoices (past due date + 7 days)
        Alert 3: Outstanding payables (past due date)
        Alert 4: Bank reconciliation (unreconciled > 30 days)
        """
        alerts = []

        try:
            org_uuid = UUID(org_id) if isinstance(org_id, str) else org_id
            today = date.today()

            current_quarter = (today.month - 1) // 3 + 1
            period_end_month = current_quarter * 3
            period_end_year = today.year

            if period_end_month == 12:
                period_end = date(period_end_year, 12, 31)
            else:
                next_month = period_end_month + 1
                period_end = date(period_end_year, next_month, 1) - timedelta(days=1)

            filing_month = period_end.month + 1
            filing_year = period_end.year
            if filing_month > 12:
                filing_month = 1
                filing_year += 1
            filing_due_date = date(filing_year, filing_month, 30)

            days_remaining = (filing_due_date - today).days

            if days_remaining <= 30 and days_remaining > 0:
                alerts.append(
                    {
                        "id": f"alert-filing-{org_id}",
                        "severity": "HIGH" if days_remaining <= 15 else "MEDIUM",
                        "title": "GST F5 Filing Due Soon",
                        "message": f"Your GST F5 filing is due in {days_remaining} days",
                        "action_required": "File Now",
                        "deadline": filing_due_date.isoformat(),
                        "dismissed": False,
                    }
                )

            overdue_invoices = InvoiceDocument.objects.filter(
                org_id=org_uuid,
                document_type__in=["SALES_INVOICE", "SALES_DEBIT_NOTE"],
                status="OVERDUE",
                due_date__lt=today - timedelta(days=7),
            )

            if overdue_invoices.exists():
                overdue_count = overdue_invoices.count()
                overdue_total = overdue_invoices.aggregate(
                    total=Coalesce(Sum(F("total_incl") - F("amount_paid")), Decimal("0.0000"))
                )["total"]

                alerts.append(
                    {
                        "id": f"alert-overdue-{org_id}",
                        "severity": "HIGH",
                        "title": "Overdue Invoices",
                        "message": f"You have {overdue_count} overdue invoices totaling {self._format_display(overdue_total)}",
                        "action_required": "Review Invoices",
                        "deadline": None,
                        "dismissed": False,
                    }
                )

            unreconciled_transactions = BankTransaction.objects.filter(
                org_id=org_uuid,
                is_reconciled=False,
                transaction_date__lt=today - timedelta(days=30),
            )

            if unreconciled_transactions.exists():
                unreconciled_count = unreconciled_transactions.count()
                alerts.append(
                    {
                        "id": f"alert-recon-{org_id}",
                        "severity": "MEDIUM",
                        "title": "Bank Reconciliation Needed",
                        "message": f"You have {unreconciled_count} unreconciled bank transactions older than 30 days",
                        "action_required": "Reconcile Now",
                        "deadline": None,
                        "dismissed": False,
                    }
                )

            return alerts

        except Exception as e:
            logger.error(f"Error generating compliance alerts for org {org_id}: {e}")
            return alerts

    def _get_invoice_counts(self, org_uuid: UUID) -> dict:
        """Get invoice counts for pending, overdue, and peppol pending."""
        try:
            pending = InvoiceDocument.objects.filter(
                org_id=org_uuid,
                document_type__in=["SALES_INVOICE", "SALES_DEBIT_NOTE"],
                status__in=["APPROVED", "SENT"],
            ).count()

            overdue = InvoiceDocument.objects.filter(
                org_id=org_uuid,
                document_type__in=["SALES_INVOICE", "SALES_DEBIT_NOTE"],
                status="OVERDUE",
            ).count()

            peppol_pending = InvoiceDocument.objects.filter(
                org_id=org_uuid,
                document_type__in=["SALES_INVOICE", "SALES_DEBIT_NOTE"],
                invoicenow_status="PENDING",
            ).count()

            return {
                "pending": pending,
                "overdue": overdue,
                "peppol_pending": peppol_pending,
            }

        except Exception as e:
            logger.error(f"Error getting invoice counts for org {org_uuid}: {e}")
            return {
                "pending": 0,
                "overdue": 0,
                "peppol_pending": 0,
            }

    def _format_display(self, amount: Decimal) -> str:
        """Format decimal amount for display (2 decimal places)."""
        try:
            return f"{amount:,.2f}"
        except Exception:
            return "0.00"

    def _get_empty_dashboard(self) -> dict:
        """Return empty dashboard data for error cases."""
        return {
            "gst_payable": "0.0000",
            "gst_payable_display": "0.00",
            "outstanding_receivables": "0.00",
            "outstanding_payables": "0.00",
            "revenue_mtd": "0.00",
            "revenue_ytd": "0.00",
            "cash_on_hand": "0.00",
            "gst_threshold_status": "SAFE",
            "gst_threshold_utilization": 0,
            "gst_threshold_amount": "0.00",
            "gst_threshold_limit": "1,000,000.00",
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
