"""
GST views for LedgerSG.

Tax code management, GST calculation, and GST return filing.
"""


from datetime import date as date_type
from decimal import Decimal
from uuid import UUID

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.authentication import JWTAuthentication

from apps.core.permissions import CanFileGST, IsOrgMember
from apps.gst.serializers import (
    DocumentGSTCalculationSerializer,
    GSTCalculationRequestSerializer,
    GSTReturnAmendSerializer,
    GSTReturnCreateSerializer,
    GSTReturnDetailSerializer,
    GSTReturnFileSerializer,
    GSTReturnListSerializer,
    GSTReturnPaymentSerializer,
    TaxCodeCreateSerializer,
    TaxCodeDetailSerializer,
    TaxCodeListSerializer,
    TaxCodeUpdateSerializer,
)
from apps.gst.services import (
    GSTCalculationService,
    GSTReturnService,
    TaxCodeService,
)
from common.decimal_utils import money
from common.exceptions import ResourceNotFound, ValidationError
from common.views import wrap_response


class TaxCodeListCreateView(APIView):
    """
    GET: List tax codes
    POST: Create custom tax code
    """

    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, IsOrgMember]

    @wrap_response
    def get(self, request, org_id: str) -> Response:
        """List tax codes.

        Query params: is_active, is_gst_charged, code, include_system, and
        effective_on (ISO date — restrict to the rate rows in force on that
        date, e.g. ?effective_on=2023-06-01 returns the 8% SR row only).
        """
        is_active = request.query_params.get("is_active")
        is_gst_charged = request.query_params.get("is_gst_charged")
        code = request.query_params.get("code")
        include_system = request.query_params.get("include_system", "true").lower() == "true"
        effective_on = request.query_params.get("effective_on")

        if is_active is not None:
            is_active = is_active.lower() == "true"
        if is_gst_charged is not None:
            is_gst_charged = is_gst_charged.lower() == "true"

        effective_on_date = None
        if effective_on:
            try:
                effective_on_date = date_type.fromisoformat(effective_on)
            except ValueError:
                raise ValidationError("effective_on must be an ISO date (YYYY-MM-DD).")


        tax_codes = TaxCodeService.list_tax_codes(
            org_id=org_id,
            is_active=is_active,
            is_gst_charged=is_gst_charged,
            include_system=include_system,
            code=code,
            effective_on=effective_on_date,
        )

        serializer = TaxCodeListSerializer(tax_codes, many=True)
        return Response({"results": serializer.data, "count": len(serializer.data)})

    @wrap_response
    def post(self, request, org_id: str) -> Response:
        """Create custom tax code."""
        # Check permission
        self._check_permission(request, "can_manage_coa")

        serializer = TaxCodeCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)


        data = serializer.validated_data
        rate = data.get("rate")
        if rate is not None:
            rate = Decimal(str(rate))

        tax_code = TaxCodeService.create_tax_code(
            org_id=org_id,
            code=data["code"],
            name=data["name"],
            rate=rate,
            is_gst_charged=data["is_gst_charged"],
            description=data.get("description", ""),
            f5_supply_box=data.get("f5_supply_box"),
            f5_purchase_box=data.get("f5_purchase_box"),
            f5_tax_box=data.get("f5_tax_box"),
        )

        return Response(TaxCodeDetailSerializer(tax_code).data, status=status.HTTP_201_CREATED)

    def _check_permission(self, request, permission: str) -> bool:
        """Check if user has specific permission."""
        org_role = getattr(request, "org_role", {})
        if org_role.get(permission) or getattr(request.user, "is_superadmin", False):
            return True
        from common.exceptions import UnauthorizedOrgAccess

        raise UnauthorizedOrgAccess("Insufficient permissions")


class TaxCodeDetailView(APIView):
    """
    GET: Get tax code details
    PATCH: Update tax code
    DELETE: Deactivate tax code
    """

    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, IsOrgMember]

    @wrap_response
    def get(self, request, org_id: str, tax_code_id: str) -> Response:
        """Get tax code details."""
        from uuid import UUID

        tax_code = TaxCodeService.get_tax_code(org_id, UUID(tax_code_id))
        return Response(TaxCodeDetailSerializer(tax_code).data)

    @wrap_response
    def patch(self, request, org_id: str, tax_code_id: str) -> Response:
        """Update tax code."""
        self._check_permission(request, "can_manage_coa")

        from uuid import UUID

        serializer = TaxCodeUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        tax_code = TaxCodeService.update_tax_code(
            org_id, UUID(tax_code_id), **serializer.validated_data
        )

        return Response(TaxCodeDetailSerializer(tax_code).data)

    @wrap_response
    def delete(self, request, org_id: str, tax_code_id: str) -> Response:
        """Deactivate tax code."""
        self._check_permission(request, "can_manage_coa")

        from uuid import UUID

        tax_code = TaxCodeService.deactivate_tax_code(org_id, UUID(tax_code_id))

        return Response(
            {"message": "Tax code deactivated", "tax_code": TaxCodeDetailSerializer(tax_code).data}
        )

    def _check_permission(self, request, permission: str) -> bool:
        """Check if user has specific permission."""
        org_role = getattr(request, "org_role", {})
        if org_role.get(permission) or getattr(request.user, "is_superadmin", False):
            return True
        from common.exceptions import UnauthorizedOrgAccess

        raise UnauthorizedOrgAccess("Insufficient permissions")


class TaxCodeIrasInfoView(APIView):
    """
    GET: Get IRAS-defined tax code information
    """

    authentication_classes = [JWTAuthentication]
    # P7/F-15: org-scoped tax-code resolution — carry IsOrgMember like every
    # sibling view (the tenant middleware already blocks non-members; this
    # is the documented second layer).
    permission_classes = [IsAuthenticated, IsOrgMember]

    @wrap_response
    def get(self, request, org_id: str) -> Response:
        """Get IRAS tax code definitions."""
        info = TaxCodeService.get_iras_tax_codes_info()
        return Response({"data": info, "count": len(info)})


class GSTCalculateView(APIView):
    """
    POST: Calculate GST for a line item
    """

    authentication_classes = [JWTAuthentication]
    # P7/F-15: org-scoped tax-code resolution — carry IsOrgMember like every
    # sibling view (the tenant middleware already blocks non-members; this
    # is the documented second layer).
    permission_classes = [IsAuthenticated, IsOrgMember]

    @wrap_response
    def post(self, request, org_id: str) -> Response:
        """Calculate GST for a line."""
        serializer = GSTCalculationRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        data = serializer.validated_data
        amount = money(data["amount"])
        is_bcrs = data.get("is_bcrs_deposit", False)

        # Get rate from tax code or use provided rate
        code = data.get("tax_code") or data.get("tax_code_id")
        if code:
            # org_id arrives as UUID (URL kwarg) — never re-wrap
            org_uuid = org_id if isinstance(org_id, UUID) else UUID(str(org_id))

            # Resolve the rate in force on document_date (default today) —
            # unknown codes fail closed with 404 instead of a silent 9%
            # fallback (B-3/H-04: a wrong rate is worse than an error).
            tax_code = TaxCodeService.get_tax_code_by_code(
                org_uuid,
                str(code),
                as_of=data.get("document_date"),
            )
            if tax_code is None:
                raise ResourceNotFound(
                    f"Tax code '{code}' is not in force on the requested date."
                )
            rate = tax_code.rate
        else:
            rate = Decimal(str(data.get("rate", "0.09")))

        result = GSTCalculationService.calculate_line_gst(
            amount=amount, rate=rate, is_bcrs_deposit=is_bcrs
        )

        # IRAS display convention: monetary amounts at 2 decimal places
        two_dp = Decimal("0.01")
        return Response(
            {
                "net_amount": str(result["net_amount"].quantize(two_dp)),
                "gst_amount": str(result["gst_amount"].quantize(two_dp)),
                "total_amount": str(result["total_amount"].quantize(two_dp)),
                "rate": str(rate) if rate else "0.00",
                "is_bcrs_exempt": result["is_bcrs_exempt"],
            }
        )


class GSTCalculateDocumentView(APIView):
    """
    POST: Calculate GST for a document with multiple lines
    """

    authentication_classes = [JWTAuthentication]
    # P7/F-15: org-scoped tax-code resolution — carry IsOrgMember like every
    # sibling view (the tenant middleware already blocks non-members; this
    # is the documented second layer).
    permission_classes = [IsAuthenticated, IsOrgMember]

    @wrap_response
    def post(self, request, org_id: str) -> Response:
        """Calculate GST for a document."""
        serializer = DocumentGSTCalculationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        data = serializer.validated_data

        default_rate = Decimal(str(data.get("default_rate", "0.09")))

        result = GSTCalculationService.calculate_document_gst(
            lines=data["lines"], default_rate=default_rate
        )

        return Response(result)


class GSTReturnListCreateView(APIView):
    """
    GET: List GST returns
    POST: Create GST return periods
    """

    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, IsOrgMember, CanFileGST]

    @wrap_response
    def get(self, request, org_id: str) -> Response:
        """List GST returns."""
        status_filter = request.query_params.get("status")
        year = request.query_params.get("year")

        if year:
            from common.query_params import parse_int_param

            # P7/F-11: garbage query params are a 400, not an unhandled 500.
            year = parse_int_param(year, "year")


        returns = GSTReturnService.list_returns(org_id=org_id, status=status_filter, year=year)

        serializer = GSTReturnListSerializer(returns, many=True)
        return Response({"results": serializer.data, "count": len(serializer.data)})

    @wrap_response
    def post(self, request, org_id: str) -> Response:
        """Create GST return periods."""

        serializer = GSTReturnCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        data = serializer.validated_data
        created = GSTReturnService.create_return_periods(
            org_id=org_id,
            filing_frequency=data["filing_frequency"],
            start_date=data["start_date"],
            periods=data["periods"],
        )

        return Response(
            {
                "message": f"Created {len(created)} return periods",
                "count": len(created),
                "data": GSTReturnListSerializer(created, many=True).data,
            },
            status=status.HTTP_201_CREATED,
        )


class GSTReturnDetailView(APIView):
    """
    GET: Get GST return details
    POST: Generate F5 data
    """

    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, IsOrgMember, CanFileGST]

    @wrap_response
    def get(self, request, org_id: str, return_id: str) -> Response:
        """Get GST return with F5 data."""
        from uuid import UUID

        gst_return = GSTReturnService.get_return(org_id, UUID(return_id))
        return Response(GSTReturnDetailSerializer(gst_return).data)

    @wrap_response
    def post(self, request, org_id: str, return_id: str) -> Response:
        """Generate/regenerate F5 data."""
        from uuid import UUID

        force = request.query_params.get("force", "false").lower() == "true"

        gst_return = GSTReturnService.generate_f5(
            org_id=org_id, return_id=UUID(return_id), force_recalculate=force
        )

        return Response(GSTReturnDetailSerializer(gst_return).data)


class GSTReturnFileView(APIView):
    """
    POST: File a GST return
    """

    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, IsOrgMember, CanFileGST]

    @wrap_response
    def post(self, request, org_id: str, return_id: str) -> Response:
        """File GST return."""
        from uuid import UUID

        serializer = GSTReturnFileSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        data = serializer.validated_data
        boxes = data.get("boxes")
        if boxes:
            boxes = {k: Decimal(str(v)) for k, v in boxes.items()}

        gst_return = GSTReturnService.file_return(
            org_id=org_id,
            return_id=UUID(return_id),
            filed_by_id=request.user.id,
            filing_reference=data.get("filing_reference"),
            boxes=boxes,
        )

        return Response(
            {
                "message": "GST return filed successfully",
                "return": GSTReturnDetailSerializer(gst_return).data,
            }
        )


class GSTReturnAmendView(APIView):
    """
    POST: Mark return for amendment
    """

    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, IsOrgMember, CanFileGST]

    @wrap_response
    def post(self, request, org_id: str, return_id: str) -> Response:
        """Amend GST return."""
        from uuid import UUID

        serializer = GSTReturnAmendSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        gst_return = GSTReturnService.amend_return(
            org_id=org_id, return_id=UUID(return_id), reason=serializer.validated_data["reason"]
        )

        return Response(
            {
                "message": "GST return marked for amendment",
                "return": GSTReturnDetailSerializer(gst_return).data,
            }
        )


class GSTReturnReviewView(APIView):
    """
    POST: Mark a computed return as reviewed (COMPUTED -> REVIEWED).

    P10/H-3: the review transition existed in the service
    (return_service.review_return) but had NO route — the F5 state
    machine (DRAFT -> COMPUTED -> REVIEWED -> FILED -> AMENDED) could not
    be walked by any client while its sibling edges (file/amend) were
    routed. Permission parity with file/amend (CanFileGST).
    """

    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, IsOrgMember, CanFileGST]

    @wrap_response
    def post(self, request, org_id: str, return_id: str) -> Response:
        """Review GST return."""
        from uuid import UUID

        gst_return = GSTReturnService.review_return(
            org_id=org_id,
            return_id=UUID(return_id),
            reviewed_by_id=request.user.id,
        )

        return Response(
            {
                "message": "GST return reviewed",
                "return": GSTReturnDetailSerializer(gst_return).data,
            }
        )


class GSTReturnPayView(APIView):
    """
    POST: Record payment for GST return
    """

    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, IsOrgMember, CanFileGST]

    @wrap_response
    def post(self, request, org_id: str, return_id: str) -> Response:
        """Record GST payment."""
        from uuid import UUID

        serializer = GSTReturnPaymentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        data = serializer.validated_data

        gst_return = GSTReturnService.pay_return(
            org_id=org_id,
            return_id=UUID(return_id),
            payment_date=data["payment_date"],
            payment_amount=Decimal(str(data["payment_amount"])),
            payment_reference=data["payment_reference"],
        )

        return Response(
            {"message": "Payment recorded", "return": GSTReturnDetailSerializer(gst_return).data}
        )


class GSTReturnDeadlinesView(APIView):
    """
    GET: Get upcoming filing deadlines
    """

    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, IsOrgMember]

    @wrap_response
    def get(self, request, org_id: str) -> Response:
        """Get upcoming deadlines."""

        from common.query_params import parse_int_param

        # P7/F-11 + P8/G-2: garbage or negative lookaheads are a 400.
        days = parse_int_param(
            request.query_params.get("days", "30"), "days", min_value=0
        )

        deadlines = GSTReturnService.get_upcoming_deadlines(org_id=org_id, days=days)

        return Response(
            {"data": GSTReturnListSerializer(deadlines, many=True).data, "count": len(deadlines)}
        )
