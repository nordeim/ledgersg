"""
Fiscal year and period management views for LedgerSG.

TDD Implementation - Fiscal Periods Endpoints
Phase 2: Integration Gaps Closure
"""


from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.authentication import JWTAuthentication

from apps.core.models import FiscalPeriod, FiscalYear
from apps.core.permissions import CanManageOrg, IsOrgMember
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
    Requires all periods to be closed first — P8/S-1: enforced (the
    validation was "TBD" since the view was written; closing a year with
    open periods silently locked accounting history inconsistently).
    P7/F-4: routed (was only in the shadowed urls module), gated on
    can_manage_org, and stamps with timezone-aware now().
    """

    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, IsOrgMember, CanManageOrg]

    @wrap_response
    def post(self, request, org_id: str, year_id: str) -> Response:
        """Close fiscal year."""
        try:
            year = FiscalYear.objects.get(id=year_id, org_id=org_id)

            if year.is_closed:
                raise ValidationError("Fiscal year is already closed")

            # P8/S-1: every period must be closed before the year closes —
            # the 400 names the open periods so the manager can close them.
            open_periods = list(
                year.periods.filter(is_open=True).values_list("label", flat=True)
            )
            if open_periods:
                raise ValidationError(
                    "All periods must be closed before closing the fiscal "
                    f"year. Open periods: {', '.join(open_periods)}."
                )

            # Close the year
            year.is_closed = True
            year.closed_at = timezone.now()
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
    P7/F-4: routed (was only in the shadowed urls module), gated on
    can_manage_org, and stamps with timezone-aware now().
    """

    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, IsOrgMember, CanManageOrg]

    @wrap_response
    def post(self, request, org_id: str, period_id: str) -> Response:
        """Close fiscal period."""
        try:
            period = FiscalPeriod.objects.get(id=period_id, org_id=org_id)

            if not period.is_open:
                raise ValidationError("Fiscal period is already closed")

            # Close the period
            period.is_open = False
            period.locked_at = timezone.now()
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


class FiscalPeriodOpenView(APIView):
    """
    POST: Open a fiscal period.

    P10/M-8: the symmetric control act — the invoice-approval error
    ("Please open the fiscal period or change the invoice date") pointed
    at an action no endpoint could perform; back-dated invoices outside
    the seeded open periods were a hard dead end.

    Manager-gated like close; clears the close stamp (locked_at/locked_by).
    Refuses an already-open period and refuses periods under a closed
    fiscal year (a closed year is history — the close precondition must
    not be circumventable by reopening a period).
    """

    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, IsOrgMember, CanManageOrg]

    @wrap_response
    def post(self, request, org_id: str, period_id: str) -> Response:
        """Open fiscal period."""
        try:
            period = FiscalPeriod.objects.select_related("fiscal_year").get(
                id=period_id, org_id=org_id
            )

            if period.is_open:
                raise ValidationError("Fiscal period is already open")

            if period.fiscal_year.is_closed:
                raise ValidationError(
                    "The fiscal year is closed — its periods cannot be reopened"
                )

            period.is_open = True
            period.locked_at = None
            period.locked_by = None
            period.save()

            return Response(
                {
                    "message": "Fiscal period opened successfully",
                    "period_id": str(period.id),
                }
            )
        except FiscalPeriod.DoesNotExist:
            return Response(
                {"error": {"code": "not_found", "message": "Fiscal period not found"}},
                status=status.HTTP_404_NOT_FOUND,
            )
