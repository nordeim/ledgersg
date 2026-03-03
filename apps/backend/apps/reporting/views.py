"""
Reporting views for LedgerSG.

Dashboard metrics and alerts API.
"""

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework import status

from apps.core.permissions import IsOrgMember, CanViewReports
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
        """Return financial reports (stub implementation)."""

        report_type = request.query_params.get("type", "profit_loss")

        if report_type not in ["profit_loss", "balance_sheet", "trial_balance"]:
            raise ValidationError(f"Invalid report type: {report_type}")

        # TODO: Implement actual report generation
        # For now, return placeholder data

        return Response(
            {
                "report_type": report_type,
                "period_start": "2024-01-01",
                "period_end": "2024-12-31",
                "currency": "SGD",
                "generated_at": "2024-01-01T00:00:00Z",
                "data": {
                    "summary": {},
                    "accounts": [],
                    "totals": {
                        "debit": "0.00",
                        "credit": "0.00",
                    },
                },
            }
        )
