"""
Organisation views for LedgerSG.

Organisation CRUD, GST registration, fiscal year management.
"""

from datetime import date
from typing import List

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.authentication import JWTAuthentication
from django.db import IntegrityError, connection

from apps.core.serializers import (
    OrganisationSerializer,
    OrganisationCreateSerializer,
    GSTRegistrationSerializer,
    FiscalYearSerializer,
)
from apps.core.services import organisation_service
from apps.core.permissions import (
    IsOrgMember,
    CanManageOrg,
    CanCreateJournals,
    CanViewReports,
)
from apps.core.models import (
    Organisation,
    FiscalYear,
    FiscalPeriod,
    Account,
)
from common.exceptions import ValidationError, DuplicateResource, UnauthorizedOrgAccess
from common.views import wrap_response


class OrganisationListCreateView(APIView):
    """
    GET: List user's organisations
    POST: Create new organisation
    """

    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    @wrap_response
    def get(self, request) -> Response:
        """List organisations where user is a member."""
        orgs = Organisation.objects.filter(user_memberships__user=request.user).distinct()

        serializer = OrganisationSerializer(orgs, many=True)
        # P21/BE-M6: the list-envelope unification — every list surface
        # speaks {results, count} (reports keep their {data: {...}}
        # payloads); the frontend + API guide read one key.
        return Response({"results": serializer.data, "count": len(serializer.data)})

    @wrap_response
    def post(self, request) -> Response:
        """Create new organisation with full setup."""
        serializer = OrganisationCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # Create organisation
        org = organisation_service.create_organisation(
            user=request.user, **serializer.validated_data
        )

        return Response(OrganisationSerializer(org).data, status=status.HTTP_201_CREATED)


class OrganisationDetailView(APIView):
    """
    GET: Get organisation details
    PATCH: Update organisation
    DELETE: Deactivate organisation (soft delete)
    """

    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, IsOrgMember]

    @wrap_response
    def get(self, request, org_id: str) -> Response:
        """Get organisation details."""
        org = self._get_org(org_id)
        serializer = OrganisationSerializer(org)

        # Add additional data
        data = serializer.data
        data["member_count"] = org.user_memberships.count()
        data["fiscal_year_count"] = org.fiscalyear_set.count()
        data["account_count"] = org.account_set.filter(is_system=False).count()

        return Response(data)

    @wrap_response
    def patch(self, request, org_id: str) -> Response:
        """Update organisation settings."""
        org = self._get_org(org_id)

        # Check permission
        self._check_permission(request, "can_manage_org")

        # P11/M-5: typed allowlist — the raw filter let entity_type /
        # base_currency / country values that violate the schema's CHECKs
        # and column sizes through to IntegrityError/DataError 500s.
        from apps.core.serializers.organisation import OrganisationUpdateSerializer

        serializer = OrganisationUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        updates = serializer.validated_data

        # P10: DB-level uen UNIQUE must surface as a 400 field error here
        # too.
        if "uen" in updates:
            from apps.core.serializers.organisation import ensure_uen_available

            ensure_uen_available(updates["uen"], exclude_org=org)

        org = organisation_service.update_organisation(org, **updates)
        return Response(OrganisationSerializer(org).data)

    @wrap_response
    def delete(self, request, org_id: str) -> Response:
        """Deactivate organisation (soft delete)."""
        org = self._get_org(org_id)

        # Check permission
        self._check_permission(request, "can_manage_org")

        # Deactivate
        org.is_active = False
        org.save()

        return Response(
            {"message": "Organisation deactivated successfully"}, status=status.HTTP_204_NO_CONTENT
        )

    def _get_org(self, org_id: str) -> Organisation:
        """Get organisation by ID or raise 404."""
        try:
            return Organisation.objects.get(id=org_id)
        except Organisation.DoesNotExist:
            raise UnauthorizedOrgAccess("Organisation not found")

    def _check_permission(self, request, permission: str) -> bool:
        """Check if user has specific permission."""
        org_role = getattr(request, "org_role", {})
        if org_role.get(permission) or getattr(request.user, "is_superadmin", False):
            return True
        raise UnauthorizedOrgAccess("Insufficient permissions")


class GSTRegistrationView(APIView):
    """
    POST: Register for GST
    DELETE: Deregister from GST
    """

    authentication_classes = [JWTAuthentication]
    # P8/G-1: this view's mutating verbs are POST/DELETE (there is no PATCH)
    # — both change core tax configuration, so the manager gate is
    # class-level. (The P7/F-10 get_permissions() pattern fits the settings
    # views, whose mutation IS PATCH; applying it here loosened these
    # write actions to any member.)
    permission_classes = [IsAuthenticated, IsOrgMember, CanManageOrg]

    @wrap_response
    def post(self, request, org_id: str) -> Response:
        """Register organisation for GST."""
        org = self._get_org(org_id)

        serializer = GSTRegistrationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        org = organisation_service.toggle_gst_registration(
            org,
            registered=True,
            reg_number=serializer.validated_data["gst_reg_number"],
            reg_date=serializer.validated_data["gst_reg_date"],
        )

        return Response(OrganisationSerializer(org).data)

    @wrap_response
    def delete(self, request, org_id: str) -> Response:
        """Deregister from GST."""
        org = self._get_org(org_id)

        org = organisation_service.toggle_gst_registration(org, registered=False)

        return Response(OrganisationSerializer(org).data)

    def _get_org(self, org_id: str) -> Organisation:
        """Get organisation by ID or raise 404."""
        try:
            return Organisation.objects.get(id=org_id)
        except Organisation.DoesNotExist:
            raise UnauthorizedOrgAccess("Organisation not found")


class FiscalYearListView(APIView):
    """
    GET: List fiscal years
    POST: Create new fiscal year
    """

    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, IsOrgMember, CanCreateJournals]

    @wrap_response
    def get(self, request, org_id: str) -> Response:
        """List fiscal years for organisation."""
        fiscal_years = FiscalYear.objects.filter(org_id=org_id).order_by("-start_date")

        serializer = FiscalYearSerializer(fiscal_years, many=True)
        # P21/BE-M6: the list-envelope unification ({results, count}).
        return Response({"results": serializer.data, "count": len(serializer.data)})


class OrganisationSummaryView(APIView):
    """
    GET: Get organisation summary/dashboard data
    """

    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, IsOrgMember, CanViewReports]

    @wrap_response
    def get(self, request, org_id: str) -> Response:
        """Get organisation summary."""
        org = Organisation.objects.get(id=org_id)

        # Get current fiscal year
        current_fy = (
            FiscalYear.objects.filter(org_id=org_id, is_closed=False).order_by("start_date").first()
        )

        # Get open periods count
        open_periods = FiscalPeriod.objects.filter(org_id=org_id, is_open=True).count()

        # Get account counts
        total_accounts = Account.objects.filter(org_id=org_id).count()
        active_accounts = Account.objects.filter(org_id=org_id, is_active=True).count()

        # Get member count
        member_count = org.user_memberships.count()

        return Response(
            {
                "organisation": OrganisationSerializer(org).data,
                "current_fiscal_year": FiscalYearSerializer(current_fy).data
                if current_fy
                else None,
                "open_periods": open_periods,
                "total_accounts": total_accounts,
                "active_accounts": active_accounts,
                "member_count": member_count,
            }
        )


class OrganisationSettingsView(APIView):
    """
    GET / PATCH: Organisation settings.

    Returns or updates organisation configuration settings.
    P7/F-10: PATCH is typed (entity_type from the model vocabulary,
    fy_start_month 1-12, 3-char currency) and gated on can_manage_org —
    the pre-P7 raw setattr crashed on invalid values (DB CHECK
    IntegrityError -> 500) and any member could change the base currency.
    """

    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, IsOrgMember]

    def get_permissions(self):
        """PATCH changes core organisation configuration (base currency,
        GST, fiscal year) — manager-only (P7/F-10); GET stays
        member-readable."""
        if self.request.method == "PATCH":
            return [IsAuthenticated(), IsOrgMember(), CanManageOrg()]
        return super().get_permissions()

    @wrap_response
    def get(self, request, org_id: str) -> Response:
        """Get organisation settings."""
        try:
            org = Organisation.objects.get(id=org_id)
            return Response(
                {
                    "id": str(org.id),
                    "name": org.name,
                    "legal_name": org.legal_name,
                    "uen": org.uen,
                    "entity_type": org.entity_type,
                    "base_currency": org.base_currency,
                    "timezone": org.timezone,
                    "fy_start_month": org.fy_start_month,
                    "gst_registered": org.gst_registered,
                    "gst_reg_number": org.gst_reg_number,
                    "gst_scheme": org.gst_scheme,
                    "gst_filing_frequency": org.gst_filing_frequency,
                    "peppol_participant_id": org.peppol_participant_id,
                    "invoicenow_enabled": org.invoicenow_enabled,
                }
            )
        except Organisation.DoesNotExist:
            return Response(
                {"error": {"code": "not_found", "message": "Organisation not found"}},
                status=status.HTTP_404_NOT_FOUND,
            )

    @wrap_response
    def patch(self, request, org_id: str) -> Response:
        """Update organisation settings (typed + allowlisted, P7/F-10)."""
        from apps.core.serializers.organisation import OrganisationSettingsSerializer

        try:
            org = Organisation.objects.get(id=org_id)
        except Organisation.DoesNotExist:
            return Response(
                {"error": {"code": "not_found", "message": "Organisation not found"}},
                status=status.HTTP_404_NOT_FOUND,
            )

        # P11/M-5: the instance is bound BEFORE validation so the
        # GST-consistency pair (and any instance-aware check) reads the
        # instance-merged effective values instead of the payload alone.
        serializer = OrganisationSettingsSerializer(org, data=request.data)
        serializer.is_valid(raise_exception=True)
        validated = serializer.validated_data

        # P10: DB-level uen UNIQUE must surface as a 400 field error here
        # too (the serializer has no instance context to exclude self).
        if "uen" in validated:
            from apps.core.serializers.organisation import ensure_uen_available

            ensure_uen_available(validated["uen"], exclude_org=org)

        updated_fields = []
        for field, value in validated.items():
            setattr(org, field, value)
            updated_fields.append(field)

        # P11/L-9: the UEN check-then-write is racy — the concurrent loser
        # hits the DB UNIQUE constraint; surface the same 400 field error.
        try:
            org.save()
        except IntegrityError:
            from rest_framework import serializers

            raise serializers.ValidationError(
                {"uen": "An organisation with this UEN already exists."}
            )
        return Response(
            {
                "message": "Settings updated successfully",
                "id": str(org.id),
                "updated_fields": updated_fields,
            }
        )
