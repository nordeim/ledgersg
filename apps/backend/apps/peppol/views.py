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
        """Get Peppol transmission log with real data from database."""
        from apps.peppol.models import PeppolTransmissionLog

        queryset = PeppolTransmissionLog.objects.filter(org_id=org_id)

        # Apply filters
        status_filter = request.query_params.get("status")
        if status_filter:
            queryset = queryset.filter(status=status_filter)

        # Serialize and return
        transmissions = [
            {
                "id": str(t.id),
                "document_id": str(t.document_id),
                "status": t.status,
                "attempt_number": t.attempt_number,
                "peppol_message_id": t.peppol_message_id,
                "error_message": t.error_message,
                "transmitted_at": t.transmitted_at.isoformat() if t.transmitted_at else None,
                "access_point_provider": t.access_point_provider,
            }
            for t in queryset.order_by("-transmitted_at")
        ]

        return Response(
            {
                "results": transmissions,
                "count": len(transmissions),
                "pending": queryset.filter(status="PENDING").count(),
                "failed": queryset.filter(status="FAILED").count(),
                "completed": queryset.filter(status="DELIVERED").count(),
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
        """Get Peppol settings from database."""
        from apps.core.models import Organisation
        from apps.peppol.models import OrganisationPeppolSettings

        try:
            org = Organisation.objects.get(id=org_id)
            settings = OrganisationPeppolSettings.objects.filter(org_id=org_id).first()

            return Response(
                {
                    "enabled": org.invoicenow_enabled,
                    "participant_id": org.peppol_participant_id,
                    "is_configured": settings.is_configured if settings else False,
                    "access_point_provider": settings.access_point_provider if settings else None,
                    "auto_transmit": settings.auto_transmit if settings else False,
                    "retry_attempts": settings.transmission_retry_attempts if settings else 3,
                    "status": "configured"
                    if (settings and settings.is_configured)
                    else "not_configured",
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
        from apps.peppol.models import OrganisationPeppolSettings

        try:
            org = Organisation.objects.get(id=org_id)
            settings, created = OrganisationPeppolSettings.objects.get_or_create(
                org_id=org_id,
                defaults={
                    "access_point_provider": "Storecove",
                    "access_point_api_key": "",
                    "access_point_client_id": "",
                    "access_point_api_url": "https://api.storecove.com",
                    "auto_transmit": False,
                    "transmission_retry_attempts": 3,
                },
            )

            # Update allowed fields
            updated_fields = []

            if "enabled" in request.data:
                org.invoicenow_enabled = request.data["enabled"]
                updated_fields.append("enabled")

            if "participant_id" in request.data:
                org.peppol_participant_id = request.data["participant_id"]
                updated_fields.append("participant_id")

            if "auto_transmit" in request.data:
                settings.auto_transmit = request.data["auto_transmit"]
                updated_fields.append("auto_transmit")

            if "access_point_provider" in request.data:
                settings.access_point_provider = request.data["access_point_provider"]
                updated_fields.append("access_point_provider")

            if "retry_attempts" in request.data:
                settings.transmission_retry_attempts = request.data["retry_attempts"]
                updated_fields.append("retry_attempts")

            org.save()
            settings.save()

            return Response(
                {
                    "message": "Peppol settings updated",
                    "enabled": org.invoicenow_enabled,
                    "participant_id": org.peppol_participant_id,
                    "is_configured": settings.is_configured,
                    "auto_transmit": settings.auto_transmit,
                    "updated_fields": updated_fields,
                }
            )
        except Organisation.DoesNotExist:
            return Response(
                {"error": {"code": "not_found", "message": "Organisation not found"}},
                status=status.HTTP_404_NOT_FOUND,
            )
