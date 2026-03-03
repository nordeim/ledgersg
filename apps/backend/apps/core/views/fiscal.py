"""
Fiscal year and period management views for LedgerSG.

TDD Implementation - Fiscal Periods Endpoints
Phase 2: Integration Gaps Closure
"""

from datetime import datetime
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from rest_framework_simplejwt.authentication import JWTAuthentication

from apps.core.permissions import IsOrgMember
from apps.core.models import FiscalYear, FiscalPeriod
from common.exceptions import ValidationError
from common.views import wrap_response


class FiscalPeriodListView(APIView):
    """
    GET: List fiscal periods for organization.

    Returns all fiscal periods for the organization, ordered by start date descending.
    """

    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, IsOrgMember]

    @wrap_response
    def get(self, request, org_id: str) -> Response:
        """List fiscal periods for organisation."""
        periods = (
            FiscalPeriod.objects.filter(org_id=org_id)
            .select_related("fiscal_year")
            .order_by("-start_date")
        )

        return Response(
            {
                "results": [
                    {
                        "id": str(p.id),
                        "name": p.label,
                        "start_date": p.start_date.isoformat(),
                        "end_date": p.end_date.isoformat(),
                        "status": "OPEN" if p.is_open else "CLOSED",
                        "fiscal_year_id": str(p.fiscal_year_id),
                    }
                    for p in periods
                ],
                "count": len(periods),
            }
        )


class FiscalYearCloseView(APIView):
    """
    POST: Close a fiscal year.

    Closes the fiscal year and prevents further entries.
    Requires all periods to be closed first (validation TBD).
    """

    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, IsOrgMember]

    @wrap_response
    def post(self, request, org_id: str, year_id: str) -> Response:
        """Close fiscal year."""
        try:
            year = FiscalYear.objects.get(id=year_id, org_id=org_id)

            if year.is_closed:
                raise ValidationError("Fiscal year is already closed")

            # Close the year
            year.is_closed = True
            year.closed_at = datetime.now()
            year.closed_by = request.user.id
            year.save()

            return Response(
                {
                    "message": "Fiscal year closed successfully",
                    "year_id": str(year.id),
                    "closed_at": year.closed_at.isoformat() if year.closed_at else None,
                }
            )
        except FiscalYear.DoesNotExist:
            return Response(
                {"error": {"code": "not_found", "message": "Fiscal year not found"}},
                status=status.HTTP_404_NOT_FOUND,
            )


class FiscalPeriodCloseView(APIView):
    """
    POST: Close a fiscal period.

    Closes the fiscal period and prevents entries in that period.
    """

    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, IsOrgMember]

    @wrap_response
    def post(self, request, org_id: str, period_id: str) -> Response:
        """Close fiscal period."""
        try:
            period = FiscalPeriod.objects.get(id=period_id, org_id=org_id)

            if not period.is_open:
                raise ValidationError("Fiscal period is already closed")

            # Close the period
            period.is_open = False
            period.locked_at = datetime.now()
            period.locked_by = request.user.id
            period.save()

            return Response(
                {
                    "message": "Fiscal period closed successfully",
                    "period_id": str(period.id),
                    "closed_at": period.locked_at.isoformat() if period.locked_at else None,
                }
            )
        except FiscalPeriod.DoesNotExist:
            return Response(
                {"error": {"code": "not_found", "message": "Fiscal period not found"}},
                status=status.HTTP_404_NOT_FOUND,
            )
