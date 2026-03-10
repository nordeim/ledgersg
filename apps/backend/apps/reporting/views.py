"""
Reporting views for LedgerSG.

Dashboard metrics and alerts API.
"""

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework import status
from django.db.models import Sum, F
from decimal import Decimal
from datetime import datetime

from apps.core.permissions import IsOrgMember, CanViewReports
from apps.core.models import Account, JournalLine
from common.views import wrap_response
from common.exceptions import ValidationError


class DashboardMetricsView(APIView):
    """
    GET: Dashboard metrics.

    Returns key financial metrics for the dashboard.
    """

    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, IsOrgMember]

    @wrap_response
    def get(self, request, org_id: str) -> Response:
        """Return dashboard metrics matching frontend expectations."""
        from apps.reporting.services.dashboard_service import DashboardService

        service = DashboardService()
        return Response(service.get_dashboard_data(org_id))


class DashboardAlertsView(APIView):
    """
    GET: Dashboard alerts.

    Returns active alerts and warnings.
    """

    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, IsOrgMember]

    @wrap_response
    def get(self, request, org_id: str) -> Response:
        """Return dashboard alerts (stub implementation)."""

        # TODO: Implement actual alerts calculation
        # For now, return placeholder data

        return Response(
            {
                "alerts": [],
                "gst_threshold_warning": False,
                "gst_threshold_amount": "1000000.00",
                "overdue_invoices_count": 0,
                "unreconciled_transactions_count": 0,
                "unpaid_bills_count": 0,
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

        if report_type == "profit_loss":
            return self._get_profit_loss(org_id, start_date, end_date)
        elif report_type == "balance_sheet":
            return self._get_balance_sheet(org_id, as_at_date)
        else:
            # Trial balance - simplified
            return Response({"report_type": report_type, "data": {}})

    def _get_profit_loss(self, org_id, start_date, end_date):
        # Query revenue and expenses
        lines = JournalLine.objects.filter(org_id=org_id)
        if start_date:
            lines = lines.filter(entry__entry_date__gte=start_date)
        if end_date:
            lines = lines.filter(entry__entry_date__lte=end_date)

        # Revenue (Credit positive)
        # Use account_type_ref__code because account_type might be null
        revenue_total = lines.filter(
            account__account_type_ref__code__in=["REVENUE", "OTHER_INCOME"]
        ).aggregate(
            total=Sum(F("credit") - F("debit"), default=Decimal("0.0000"))
        )["total"] or Decimal("0.0000")

        # Expenses (Debit positive)
        expense_total = lines.filter(
            account__account_type_ref__code__in=["EXPENSE", "COGS", "OTHER_EXPENSE"]
        ).aggregate(
            total=Sum(F("debit") - F("credit"), default=Decimal("0.0000"))
        )["total"] or Decimal("0.0000")

        net_profit = revenue_total - expense_total

        return Response({
            "report_type": "profit_loss",
            "period_start": start_date,
            "period_end": end_date,
            "currency": "SGD",
            "data": {
                "revenue": {"Total": str(revenue_total)},
                "expenses": {"Total": str(expense_total)},
                "net_profit": str(net_profit)
            }
        })

    def _get_balance_sheet(self, org_id, as_at_date):
        lines = JournalLine.objects.filter(org_id=org_id)
        if as_at_date:
            lines = lines.filter(entry__entry_date__lte=as_at_date)

        # Assets (Debit positive)
        assets_total = lines.filter(
            account__account_type_ref__code__startswith="ASSET"
        ).aggregate(
            total=Sum(F("debit") - F("credit"), default=Decimal("0.0000"))
        )["total"] or Decimal("0.0000")

        # Liabilities (Credit positive)
        liabilities_total = lines.filter(
            account__account_type_ref__code__startswith="LIABILITY"
        ).aggregate(
            total=Sum(F("credit") - F("debit"), default=Decimal("0.0000"))
        )["total"] or Decimal("0.0000")

        # Equity (Credit positive)
        equity_total = lines.filter(
            account__account_type_ref__code__startswith="EQUITY"
        ).aggregate(
            total=Sum(F("credit") - F("debit"), default=Decimal("0.0000"))
        )["total"] or Decimal("0.0000")

        return Response({
            "report_type": "balance_sheet",
            "as_at_date": as_at_date,
            "currency": "SGD",
            "data": {
                "assets": {"Total": str(assets_total)},
                "liabilities": {"Total": str(liabilities_total)},
                "equity": {"Total": str(equity_total)}
            }
        })
