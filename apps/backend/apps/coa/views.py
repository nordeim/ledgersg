"""
Chart of Accounts views for LedgerSG.

Account CRUD, hierarchy, balance retrieval, trial balance.
"""

from typing import Optional

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.authentication import JWTAuthentication

from apps.core.permissions import IsOrgMember, CanManageCoA, CanViewReports
from apps.core.models import Account
from common.exceptions import ValidationError, ResourceNotFound
from common.views import wrap_response

from .services import AccountService
from .serializers import (
    AccountListSerializer,
    AccountDetailSerializer,
    AccountCreateSerializer,
    AccountUpdateSerializer,
    AccountHierarchySerializer,
    TrialBalanceSerializer,
    AccountTypeSerializer,
)


class AccountListCreateView(APIView):
    """
    GET: List accounts with filters
    POST: Create new custom account
    """
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, IsOrgMember]
    
    @wrap_response
    def get(self, request, org_id: str) -> Response:
        """List accounts with optional filters."""
        # Parse query parameters
        account_type = request.query_params.get("account_type")
        is_active = request.query_params.get("is_active")
        is_system = request.query_params.get("is_system")
        parent_id = request.query_params.get("parent_id")
        search = request.query_params.get("search")
        order_by = request.query_params.get("order_by", "code")
        include_balance = request.query_params.get("include_balance", "false").lower() == "true"
        
        # Convert boolean strings
        if is_active is not None:
            is_active = is_active.lower() == "true"
        if is_system is not None:
            is_system = is_system.lower() == "true"
        if parent_id:
            from uuid import UUID
            try:
                parent_id = UUID(parent_id)
            except ValueError:
                parent_id = None
        
        # Get accounts
        accounts = AccountService.list_accounts(
            org_id=org_id,
            account_type=account_type,
            is_active=is_active,
            is_system=is_system,
            parent_id=parent_id,
            search=search,
            order_by=order_by
        )
        
        serializer = AccountListSerializer(
            accounts, 
            many=True,
            context={"include_balance": include_balance}
        )
        
        return Response({
            "data": serializer.data,
            "count": len(serializer.data)
        })
    
    @wrap_response
    def post(self, request, org_id: str) -> Response:
        """Create new custom account."""
        # Check permission
        self._check_permission(request, "can_manage_coa")
        
        serializer = AccountCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # Create account
        account = AccountService.create_account(
            org_id=org_id,
            **serializer.validated_data
        )
        
        return Response(
            AccountDetailSerializer(account).data,
            status=status.HTTP_201_CREATED
        )
    
    def _check_permission(self, request, permission: str) -> bool:
        """Check if user has specific permission."""
        org_role = getattr(request, "org_role", {})
        if org_role.get(permission) or getattr(request.user, "is_superadmin", False):
            return True
        from common.exceptions import UnauthorizedOrgAccess
        raise UnauthorizedOrgAccess("Insufficient permissions")


class AccountDetailView(APIView):
    """
    GET: Get account details with balance
    PATCH: Update account
    DELETE: Archive account
    """
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, IsOrgMember]
    
    @wrap_response
    def get(self, request, org_id: str, account_id: str) -> Response:
        """Get account details."""
        from uuid import UUID
        account = AccountService.get_account(UUID(org_id), UUID(account_id))
        serializer = AccountDetailSerializer(account)
        return Response(serializer.data)
    
    @wrap_response
    def patch(self, request, org_id: str, account_id: str) -> Response:
        """Update account."""
        # Check permission
        self._check_permission(request, "can_manage_coa")
        
        from uuid import UUID
        serializer = AccountUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        account = AccountService.update_account(
            org_id=UUID(org_id),
            account_id=UUID(account_id),
            **serializer.validated_data
        )
        
        return Response(AccountDetailSerializer(account).data)
    
    @wrap_response
    def delete(self, request, org_id: str, account_id: str) -> Response:
        """Archive (soft delete) account."""
        # Check permission
        self._check_permission(request, "can_manage_coa")
        
        from uuid import UUID
        account = AccountService.archive_account(UUID(org_id), UUID(account_id))
        
        return Response(
            {"message": "Account archived successfully", "account": AccountDetailSerializer(account).data},
            status=status.HTTP_200_OK
        )
    
    def _check_permission(self, request, permission: str) -> bool:
        """Check if user has specific permission."""
        org_role = getattr(request, "org_role", {})
        if org_role.get(permission) or getattr(request.user, "is_superadmin", False):
            return True
        from common.exceptions import UnauthorizedOrgAccess
        raise UnauthorizedOrgAccess("Insufficient permissions")


class AccountBalanceView(APIView):
    """
    GET: Get account balance
    """
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, IsOrgMember, CanViewReports]
    
    @wrap_response
    def get(self, request, org_id: str, account_id: str) -> Response:
        """Get account balance."""
        from uuid import UUID
        from decimal import Decimal
        
        balance = AccountService.get_account_balance(UUID(org_id), UUID(account_id))
        account = AccountService.get_account(UUID(org_id), UUID(account_id))
        
        return Response({
            "account_id": account_id,
            "account_code": account.code,
            "account_name": account.name,
            "balance": str(balance),
            "currency": "SGD",  # TODO: Get from org settings
        })


class AccountHierarchyView(APIView):
    """
    GET: Get account hierarchy tree
    """
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, IsOrgMember]
    
    @wrap_response
    def get(self, request, org_id: str) -> Response:
        """Get account hierarchy."""
        account_type = request.query_params.get("account_type")
        
        from uuid import UUID
        hierarchy = AccountService.get_account_hierarchy(
            UUID(org_id),
            account_type=account_type
        )
        
        return Response({
            "data": hierarchy,
            "count": len(hierarchy)
        })


class AccountTypesView(APIView):
    """
    GET: List all valid account types
    """
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    
    @wrap_response
    def get(self, request) -> Response:
        """Get all account types."""
        types = AccountService.get_account_types()
        
        data = [
            {
                "key": key,
                "name": info["name"],
                "code_prefix": info["code_prefix"],
                "category": info["category"],
            }
            for key, info in types.items()
        ]
        
        return Response({
            "data": data,
            "count": len(data)
        })


class TrialBalanceView(APIView):
    """
    GET: Get trial balance
    """
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, IsOrgMember, CanViewReports]
    
    @wrap_response
    def get(self, request, org_id: str) -> Response:
        """Get trial balance."""
        from uuid import UUID
        
        fiscal_year_id = request.query_params.get("fiscal_year_id")
        if fiscal_year_id:
            fiscal_year_id = UUID(fiscal_year_id)
        
        trial_balance = AccountService.get_trial_balance(
            UUID(org_id),
            fiscal_year_id=fiscal_year_id
        )
        
        # Calculate totals
        total_debit = sum(row["total_debit"] for row in trial_balance)
        total_credit = sum(row["total_credit"] for row in trial_balance)
        
        return Response({
            "data": trial_balance,
            "count": len(trial_balance),
            "totals": {
                "debit": str(total_debit),
                "credit": str(total_credit),
                "balanced": abs(total_debit - total_credit) < 0.0001
            }
        })


class AccountSearchView(APIView):
    """
    GET: Search accounts
    
    Quick search endpoint for autocomplete/typeahead.
    """
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, IsOrgMember]
    
    @wrap_response
    def get(self, request, org_id: str) -> Response:
        """Search accounts."""
        query = request.query_params.get("q", "").strip()
        account_type = request.query_params.get("account_type")
        limit = int(request.query_params.get("limit", 10))
        
        if not query:
            return Response({"data": [], "count": 0})
        
        # Search in code and name
        accounts = Account.objects.filter(
            org_id=org_id,
            is_active=True
        )
        
        if account_type:
            accounts = accounts.filter(account_type=account_type)
        
        accounts = accounts.filter(
            models.Q(code__icontains=query) |
            models.Q(name__icontains=query)
        )[:limit]
        
        serializer = AccountListSerializer(accounts, many=True)
        
        return Response({
            "data": serializer.data,
            "count": len(serializer.data)
        })


# Import at end to avoid circular imports
from django.db import models
