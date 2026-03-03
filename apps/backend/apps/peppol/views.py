"""
Peppol/InvoiceNow integration views for LedgerSG.

Provides endpoints for Peppol transmission management and settings.
"""

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from rest_framework_simplejwt.authentication import JWTAuthentication

from apps.core.permissions import IsOrgMember
from common.exceptions import ValidationError
from common.views import wrap_response


class PeppolTransmissionLogView(APIView):
    """
    GET: Peppol transmission log.

    Returns transmission history for InvoiceNow/Peppol documents.
    """

    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, IsOrgMember]

    @wrap_response
    def get(self, request, org_id: str) -> Response:
        """Get Peppol transmission log."""
        # TODO: Implement actual query from database
        # For now, return empty stub

        status_filter = request.query_params.get("status")

        # Stub response
        transmissions = []

        return Response(
            {
                "results": transmissions,
                "count": len(transmissions),
                "pending": 0,
                "failed": 0,
                "completed": 0,
                "meta": {
                    "status_filter": status_filter,
                    "stub": True,
                    "message": "Peppol integration not yet fully implemented",
                },
            }
        )


class PeppolSettingsView(APIView):
    """
    GET / PATCH: Peppol settings.

    Manage Peppol/InvoiceNow configuration for the organisation.
    """

    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, IsOrgMember]

    @wrap_response
    def get(self, request, org_id: str) -> Response:
        """Get Peppol settings."""
        from apps.core.models import Organisation

        try:
            org = Organisation.objects.get(id=org_id)
            return Response(
                {
                    "enabled": org.invoicenow_enabled,
                    "participant_id": org.peppol_participant_id,
                    "endpoint": None,  # TODO: Add to model
                    "test_mode": True,  # TODO: Add to model
                    "supported_formats": ["UBL"],
                    "status": "configured" if org.peppol_participant_id else "not_configured",
                    "meta": {"stub": True, "message": "Full Peppol integration pending"},
                }
            )
        except Organisation.DoesNotExist:
            return Response(
                {"error": {"code": "not_found", "message": "Organisation not found"}},
                status=status.HTTP_404_NOT_FOUND,
            )

    @wrap_response
    def patch(self, request, org_id: str) -> Response:
        """Update Peppol settings."""
        from apps.core.models import Organisation

        try:
            org = Organisation.objects.get(id=org_id)

            # Update allowed fields
            updated_fields = []
            if "enabled" in request.data:
                org.invoicenow_enabled = request.data["enabled"]
                updated_fields.append("enabled")

            if "participant_id" in request.data:
                org.peppol_participant_id = request.data["participant_id"]
                updated_fields.append("participant_id")

            org.save()

            return Response(
                {
                    "message": "Peppol settings updated",
                    "enabled": org.invoicenow_enabled,
                    "participant_id": org.peppol_participant_id,
                    "updated_fields": updated_fields,
                }
            )
        except Organisation.DoesNotExist:
            return Response(
                {"error": {"code": "not_found", "message": "Organisation not found"}},
                status=status.HTTP_404_NOT_FOUND,
            )
