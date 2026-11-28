"""
Reporting views for LedgerSG.

Dashboard metrics and alerts API.
"""

from decimal import Decimal
from uuid import UUID

from django.db.models import F, Sum
from django.utils import timezone
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.authentication import JWTAuthentication

from apps.core.models import JournalLine
from apps.core.permissions import CanViewReports, IsOrgMember
from common.exceptions import ValidationError
from common.views import wrap_response


class DashboardMetricsView(APIView):
    """
    GET: Dashboard metrics.

    Returns key financial metrics for the dashboard.
    """

    authentication_classes = [JWTAuthentication]
    # P7/F-15: financial metrics/alerts are reports — gated like the core
    # dashboard and the financial-report endpoints (any member saw them
    # pre-P7).
    permission_classes = [IsAuthenticated, IsOrgMember, CanViewReports]

    @wrap_response
    def get(self, request, org_id: str) -> Response:
        """Return dashboard metrics matching frontend expectations."""
        from apps.reporting.services.dashboard_service import DashboardService

        service = DashboardService()
        return Response(service.get_dashboard_data(org_id))


class DashboardAlertsView(APIView):
    """
    GET: Dashboard alerts.

    Returns active alerts and warnings (P5/H-10: real computation via the
    DashboardService — was a placeholder returning fabricated zeros).
    """

    authentication_classes = [JWTAuthentication]
    # P7/F-15: financial metrics/alerts are reports — gated like the core
    # dashboard and the financial-report endpoints (any member saw them
    # pre-P7).
    permission_classes = [IsAuthenticated, IsOrgMember, CanViewReports]

    @wrap_response
    def get(self, request, org_id: str) -> Response:
        """Return dashboard alerts computed from live data."""
        from apps.core.models import BankTransaction, InvoiceDocument
        from apps.reporting.services.dashboard_service import DashboardService

        service = DashboardService()

        alerts = service.generate_compliance_alerts(org_id)
        threshold = service.query_gst_threshold_status(org_id)
        invoice_counts = service._get_invoice_counts(org_id)

        threshold_warning = threshold.get("status") in ("WARNING", "EXCEEDED")
        threshold_amount = str(service.GST_THRESHOLD_LIMIT)

        unreconciled = BankTransaction.objects.filter(
            org_id=org_id, is_reconciled=False
        ).count()

        unpaid_bills = (
            InvoiceDocument.objects.filter(
                org_id=org_id,
                document_type__in=[
                    "PURCHASE_INVOICE",
                    "PURCHASE_CREDIT_NOTE",
                    "PURCHASE_DEBIT_NOTE",
                ],
                status__in=["APPROVED", "PARTIALLY_PAID", "OVERDUE"],
            )
            .filter(amount_paid__lt=F("total_incl"))
            .count()
        )

        return Response(
            {
                "alerts": alerts,
                "gst_threshold_warning": threshold_warning,
                "gst_threshold_amount": threshold_amount,
                "overdue_invoices_count": invoice_counts.get("overdue", 0),
                "unreconciled_transactions_count": unreconciled,
                "unpaid_bills_count": unpaid_bills,
                "upcoming_deadlines": [],
            }
        )


class FinancialReportView(APIView):
    """
    GET: Financial reports (P&L, Balance Sheet).

    Returns financial reports for the organization.
    """

    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, IsOrgMember, CanViewReports]

    @wrap_response
    def get(self, request, org_id: str) -> Response:
        """Return financial reports with real calculations."""

        report_type = request.query_params.get("report_type", "profit_loss")
        start_date = request.query_params.get("start_date")
        end_date = request.query_params.get("end_date")
        as_at_date = request.query_params.get("as_at_date")

        if report_type not in ["profit_loss", "balance_sheet", "trial_balance"]:
            raise ValidationError(f"Invalid report type: {report_type}")

        # P8/R-1: dates are untrusted input — garbage is a 400 naming the
        # param (the P7/F-11 pattern), never a Django filter 500.
        from common.query_params import parse_date_param

        start_date = parse_date_param(start_date, "start_date").date() if start_date else None
        end_date = parse_date_param(end_date, "end_date").date() if end_date else None
        as_at_date = parse_date_param(as_at_date, "as_at_date").date() if as_at_date else None

        # P33/BE-P33-M1: the ledger these reports aggregate is denominated
        # in the org's base_currency — the hardcoded "SGD" lied to any
        # non-SGD-based org (the invoice PDF template already rendered the
        # truthful org.base_currency). One indexed-PK read per report
        # request, negligible beside the report's own aggregates.
        from apps.core.models import Organisation

        base_currency = (
            Organisation.objects.values_list("base_currency", flat=True).get(
                id=org_id
            )
        )

        if report_type == "profit_loss":
            return self._get_profit_loss(org_id, start_date, end_date, base_currency)
        elif report_type == "balance_sheet":
            return self._get_balance_sheet(org_id, as_at_date, base_currency)
        else:
            # P8/R-2: the stub {"data": {}} is gone — the real trial balance
            # lives in the journal service (date-based, same semantics as
            # the P2 rewrite; the coa variant keeps fiscal-year filtering).
            from apps.journal.services import JournalService

            lines = JournalService.get_trial_balance(
                UUID(str(org_id)), date_to=as_at_date
            )
            total_debits = sum(
                (Decimal(row["total_debits"]) for row in lines), Decimal("0.0000")
            )
            total_credits = sum(
                (Decimal(row["total_credits"]) for row in lines), Decimal("0.0000")
            )
            return Response({
                "report_type": "trial_balance",
                "as_at_date": as_at_date,
                "currency": base_currency,
                "data": {
                    "lines": lines,
                    "totals": {
                        "total_debits": str(total_debits),
                        "total_credits": str(total_credits),
                        "balanced": total_debits == total_credits,
                    },
                },
            })

    def _get_profit_loss(self, org_id, start_date, end_date, base_currency):
        # P8/R-3: per-account lines (not just totals) — each section lists
        # its accounts with amounts, ordered by code, plus the section
        # totals the stub-era response carried.
        lines = JournalLine.objects.filter(org_id=org_id)
        if start_date:
            lines = lines.filter(entry__entry_date__gte=start_date)
        if end_date:
            lines = lines.filter(entry__entry_date__lte=end_date)

        # Use account_type_ref__code because account_type might be null
        revenue_rows = (
            lines.filter(account__account_type_ref__code__in=["REVENUE", "OTHER_INCOME"])
            .values("account_id", "account__code", "account__name")
            .annotate(amount=Sum(F("credit") - F("debit"), default=Decimal("0.0000")))
            .order_by("account__code")
        )
        expense_rows = (
            lines.filter(account__account_type_ref__code__in=["EXPENSE", "COGS", "OTHER_EXPENSE"])
            .values("account_id", "account__code", "account__name")
            .annotate(amount=Sum(F("debit") - F("credit"), default=Decimal("0.0000")))
            .order_by("account__code")
        )

        def _row(r, positive_credit):
            amount = r["amount"] or Decimal("0.0000")
            return {
                "account_code": r["account__code"],
                "account_name": r["account__name"],
                "amount": str(amount),
            }

        revenue_lines = [_row(r, True) for r in revenue_rows if (r["amount"] or 0) != 0]
        expense_lines = [_row(r, False) for r in expense_rows if (r["amount"] or 0) != 0]
        revenue_total = sum(
            (Decimal(r["amount"]) for r in revenue_lines), Decimal("0.0000")
        )
        expense_total = sum(
            (Decimal(r["amount"]) for r in expense_lines), Decimal("0.0000")
        )

        return Response({
            "report_type": "profit_loss",
            "period_start": start_date,
            "period_end": end_date,
            "currency": base_currency,
            "data": {
                "sections": {"revenue": revenue_lines, "expenses": expense_lines},
                "revenue_total": str(revenue_total),
                "expense_total": str(expense_total),
                "net_profit": str(revenue_total - expense_total),
            }
        })

    def _get_balance_sheet(self, org_id, as_at_date, base_currency):
        # P8/R-3: the statement ties out — current-period earnings (all-time
        # revenue - expense balances up to as_at) are folded in as retained
        # earnings, so assets == liabilities + equity + retained whenever
        # the books balance (the stub-era report omitted them and never
        # balanced with P&L activity).
        lines = JournalLine.objects.filter(org_id=org_id)
        if as_at_date:
            lines = lines.filter(entry__entry_date__lte=as_at_date)

        def _section(codes, positive_credit):
            rows = (
                lines.filter(account__account_type_ref__code__startswith=codes)
                .values("account__code", "account__name")
                .annotate(
                    amount=Sum(
                        (F("credit") - F("debit"))
                        if positive_credit
                        else (F("debit") - F("credit")),
                        default=Decimal("0.0000"),
                    )
                )
                .order_by("account__code")
            )
            out = [
                {"account_code": r["account__code"], "account_name": r["account__name"],
                 "amount": str(r["amount"] or Decimal("0.0000"))}
                for r in rows
                if (r["amount"] or 0) != 0
            ]
            total = sum((Decimal(r["amount"]) for r in out), Decimal("0.0000"))
            return out, total

        asset_lines, assets_total = _section("ASSET", positive_credit=False)
        liability_lines, liabilities_total = _section("LIABILITY", positive_credit=True)
        equity_lines, equity_total = _section("EQUITY", positive_credit=True)

        # Retained earnings: all-time P&L up to as_at (revenue - expenses)
        revenue = lines.filter(
            account__account_type_ref__code__in=["REVENUE", "OTHER_INCOME"]
        ).aggregate(
            total=Sum(F("credit") - F("debit"), default=Decimal("0.0000"))
        )["total"] or Decimal("0.0000")
        expenses = lines.filter(
            account__account_type_ref__code__in=["EXPENSE", "COGS", "OTHER_EXPENSE"]
        ).aggregate(
            total=Sum(F("debit") - F("credit"), default=Decimal("0.0000"))
        )["total"] or Decimal("0.0000")
        retained = revenue - expenses

        balanced = (
            assets_total == liabilities_total + equity_total + retained
        )

        return Response({
            "report_type": "balance_sheet",
            "as_at_date": as_at_date,
            "currency": base_currency,
            "data": {
                "sections": {
                    "assets": asset_lines,
                    "liabilities": liability_lines,
                    "equity": equity_lines,
                },
                "assets_total": str(assets_total),
                "liabilities_total": str(liabilities_total),
                "equity_total": str(equity_total),
                "retained_earnings": str(retained),
                "balanced": balanced,
            }
        })


class AgedReportView(APIView):
    """
    GET: Aged receivables / payables (P8/R-5).

    Per-contact rows bucketed by days past due at `as_at`, mirroring the
    dashboard's outstanding semantics.
    """

    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, IsOrgMember, CanViewReports]

    @wrap_response
    def get(self, request, org_id: str) -> Response:
        """Return the aged report for ?type=receivables|payables&as_at=."""
        report_type = request.query_params.get("type", "receivables")
        if report_type not in ("receivables", "payables"):
            raise ValidationError(
                f"Invalid 'type' — expected receivables or payables, got '{report_type}'."
            )

        from common.query_params import parse_date_param

        as_at = parse_date_param(
            request.query_params.get("as_at", timezone.localdate().isoformat()), "as_at"
        ).date()

        from apps.reporting.services.aged_service import get_aged_report

        data = get_aged_report(UUID(str(org_id)), report_type, as_at)
        return Response(data)
