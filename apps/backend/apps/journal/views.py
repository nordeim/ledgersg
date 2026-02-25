"""
Journal views for LedgerSG.

Journal entry management and trial balance reporting.
"""

from typing import Optional
from datetime import date

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.authentication import JWTAuthentication

from apps.core.permissions import IsOrgMember, CanCreateJournals, CanViewReports
from apps.core.models import JournalEntry
from common.exceptions import ValidationError, ResourceNotFound
from common.views import wrap_response
from common.decimal_utils import Decimal

from apps.journal.services import JournalService, ENTRY_TYPES
from apps.journal.serializers import (
    JournalEntryListSerializer,
    JournalEntryDetailSerializer,
    JournalEntryCreateSerializer,
    JournalEntryUpdateSerializer,
    ReversalCreateSerializer,
    TrialBalanceEntrySerializer,
    AccountBalanceSerializer,
    EntryTypeSerializer,
)


class JournalEntryListCreateView(APIView):
    """
    GET: List journal entries
    POST: Create journal entry
    """
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, IsOrgMember]
    
    @wrap_response
    def get(self, request, org_id: str) -> Response:
        """List journal entries with filters."""
        entry_type = request.query_params.get("type")
        fiscal_period_id = request.query_params.get("fiscal_period_id")
        account_id = request.query_params.get("account_id")
        date_from = request.query_params.get("date_from")
        date_to = request.query_params.get("date_to")
        source_document_id = request.query_params.get("source_document_id")
        
        from uuid import UUID
        
        # Parse UUIDs
        if fiscal_period_id:
            fiscal_period_id = UUID(fiscal_period_id)
        if account_id:
            account_id = UUID(account_id)
        if source_document_id:
            source_document_id = UUID(source_document_id)
        
        entries = JournalService.list_entries(
            org_id=UUID(org_id),
            entry_type=entry_type,
            fiscal_period_id=fiscal_period_id,
            account_id=account_id,
            date_from=date_from,
            date_to=date_to,
            source_document_id=source_document_id
        )
        
        serializer = JournalEntryListSerializer(entries, many=True)
        return Response({
            "data": serializer.data,
            "count": len(serializer.data)
        })
    
    @wrap_response
    def post(self, request, org_id: str) -> Response:
        """Create new journal entry."""
        # Check permission
        self._check_permission(request, "can_create_journals")
        
        serializer = JournalEntryCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        from uuid import UUID
        data = serializer.validated_data
        
        # Parse fiscal_period_id if provided
        fiscal_period_id = data.get("fiscal_period_id")
        if fiscal_period_id:
            fiscal_period_id = UUID(str(fiscal_period_id))
        
        entry = JournalService.create_entry(
            org_id=UUID(org_id),
            entry_date=data["entry_date"],
            entry_type=data["entry_type"],
            description=data["description"],
            lines=data["lines"],
            fiscal_period_id=fiscal_period_id,
            user_id=request.user.id
        )
        
        return Response(
            JournalEntryDetailSerializer(entry).data,
            status=status.HTTP_201_CREATED
        )
    
    def _check_permission(self, request, permission: str) -> bool:
        """Check if user has specific permission."""
        org_role = getattr(request, "org_role", {})
        if org_role.get(permission) or getattr(request.user, "is_superadmin", False):
            return True
        from common.exceptions import UnauthorizedOrgAccess
        raise UnauthorizedOrgAccess("Insufficient permissions")


class JournalEntryDetailView(APIView):
    """
    GET: Get journal entry details
    """
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, IsOrgMember]
    
    @wrap_response
    def get(self, request, org_id: str, entry_id: str) -> Response:
        """Get journal entry details."""
        from uuid import UUID
        entry = JournalService.get_entry(UUID(org_id), UUID(entry_id))
        return Response(JournalEntryDetailSerializer(entry).data)


class JournalEntryReversalView(APIView):
    """
    POST: Create reversal entry
    """
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, IsOrgMember, CanCreateJournals]
    
    @wrap_response
    def post(self, request, org_id: str, entry_id: str) -> Response:
        """Create reversal for journal entry."""
        from uuid import UUID
        
        serializer = ReversalCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        data = serializer.validated_data
        
        reversal = JournalService.create_reversal(
            org_id=UUID(org_id),
            original_entry_id=UUID(entry_id),
            reversal_date=data["reversal_date"],
            reason=data["reason"],
            user_id=request.user.id
        )
        
        return Response({
            "message": "Reversal entry created",
            "reversal": JournalEntryDetailSerializer(reversal).data,
            "original_entry_id": entry_id
        }, status=status.HTTP_201_CREATED)


class TrialBalanceView(APIView):
    """
    GET: Get trial balance
    """
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, IsOrgMember, CanViewReports]
    
    @wrap_response
    def get(self, request, org_id: str) -> Response:
        """Get trial balance as of date."""
        from uuid import UUID
        
        date_to = request.query_params.get("date_to")
        if date_to:
            date_to = date.fromisoformat(date_to)
        
        entries = JournalService.get_trial_balance(
            org_id=UUID(org_id),
            date_to=date_to
        )
        
        # Calculate totals
        total_debits = sum(Decimal(e["total_debits"]) for e in entries)
        total_credits = sum(Decimal(e["total_credits"]) for e in entries)
        
        return Response({
            "data": entries,
            "count": len(entries),
            "totals": {
                "total_debits": str(total_debits),
                "total_credits": str(total_credits),
                "balanced": abs(total_debits - total_credits) < Decimal("0.001")
            },
            "as_of_date": date_to.isoformat() if date_to else date.today().isoformat()
        })


class AccountBalanceView(APIView):
    """
    GET: Get account running balance
    """
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, IsOrgMember, CanViewReports]
    
    @wrap_response
    def get(self, request, org_id: str, account_id: str) -> Response:
        """Get account balance."""
        from uuid import UUID
        
        date_to = request.query_params.get("date_to")
        if date_to:
            date_to = date.fromisoformat(date_to)
        
        balance = JournalService.get_account_balance(
            org_id=UUID(org_id),
            account_id=UUID(account_id),
            date_to=date_to
        )
        
        # Get account info
        from apps.core.models import Account
        try:
            account = Account.objects.get(id=account_id, org_id=org_id)
            account_info = {
                "account_id": str(account.id),
                "account_code": account.code,
                "account_name": account.name,
                "account_type": account.account_type,
                "balance": str(balance),
                "as_of_date": date_to.isoformat() if date_to else date.today().isoformat()
            }
        except Account.DoesNotExist:
            raise ResourceNotFound(f"Account {account_id} not found")
        
        return Response(account_info)


class EntryTypesView(APIView):
    """
    GET: List available entry types
    """
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    
    @wrap_response
    def get(self, request) -> Response:
        """Get entry types."""
        types = [
            {"code": code, "name": name}
            for code, name in ENTRY_TYPES.items()
        ]
        
        return Response({
            "data": types,
            "count": len(types)
        })


class JournalEntrySummaryView(APIView):
    """
    GET: Get journal entry statistics
    """
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, IsOrgMember, CanViewReports]
    
    @wrap_response
    def get(self, request, org_id: str) -> Response:
        """Get journal summary statistics."""
        from uuid import UUID
        from django.db.models import Count, Sum
        
        org_uuid = UUID(org_id)
        
        # Count by type
        type_counts = JournalEntry.objects.filter(
            org_id=org_uuid
        ).values("entry_type").annotate(
            count=Count("id")
        )
        
        # Count by fiscal period
        period_counts = JournalEntry.objects.filter(
            org_id=org_uuid
        ).values("fiscal_period__label").annotate(
            count=Count("id")
        ).order_by("-fiscal_period__start_date")[:6]
        
        # Recent entries
        recent_entries = JournalEntry.objects.filter(
            org_id=org_uuid
        ).order_by("-created_at")[:5]
        
        return Response({
            "by_type": {t["entry_type"]: t["count"] for t in type_counts},
            "by_period": {p["fiscal_period__label"]: p["count"] for p in period_counts},
            "recent_entries": JournalEntryListSerializer(
                recent_entries, many=True
            ).data,
            "total_entries": JournalEntry.objects.filter(org_id=org_uuid).count()
        })


class ValidateBalanceView(APIView):
    """
    POST: Validate debits equal credits for proposed entry
    """
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, IsOrgMember]
    
    @wrap_response
    def post(self, request, org_id: str) -> Response:
        """Validate entry balance without creating."""
        from uuid import UUID
        
        lines = request.data.get("lines", [])
        
        if len(lines) < 2:
            return Response({
                "valid": False,
                "error": "Entry must have at least 2 lines"
            })
        
        total_debits = sum(
            Decimal(str(line.get("debit", 0))) for line in lines
        )
        total_credits = sum(
            Decimal(str(line.get("credit", 0))) for line in lines
        )
        
        difference = abs(total_debits - total_credits)
        is_valid = difference < Decimal("0.001")
        
        return Response({
            "valid": is_valid,
            "total_debits": str(total_debits),
            "total_credits": str(total_credits),
            "difference": str(difference),
            "line_count": len(lines)
        })
