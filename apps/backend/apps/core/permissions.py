"""
Permission classes for LedgerSG.

DRF permission classes that check user's role within current org.
"""

from rest_framework import permissions

from common.exceptions import UnauthorizedOrgAccess


class IsOrgMember(permissions.BasePermission):
    """
    Permission that checks if user belongs to the org in URL.
    
    This is enforced by TenantContextMiddleware, but this permission
    provides an extra layer of safety.
    """
    
    def has_permission(self, request, view):
        # Superadmins can access any org
        if getattr(request.user, 'is_superadmin', False):
            return True
        
        # Check if org_id is set by middleware
        org_id = getattr(request, 'org_id', None)
        if not org_id:
            return False
        
        # Check if user has org_role (set by middleware)
        org_role = getattr(request, 'org_role', None)
        return org_role is not None


class HasOrgPermission(permissions.BasePermission):
    """
    Permission that checks if user has a specific permission in the org.
    
    Usage:
        class MyView(APIView):
            permission_classes = [IsAuthenticated, IsOrgMember, CanCreateInvoices]
    """
    
    permission_field = None
    
    def has_permission(self, request, view):
        # Superadmins have all permissions
        if getattr(request.user, 'is_superadmin', False):
            return True
        
        # Get org_role from request (set by middleware)
        org_role = getattr(request, 'org_role', None)
        if not org_role:
            return False
        
        # Check specific permission
        if self.permission_field:
            return org_role.get(self.permission_field, False)
        
        return True


# Pre-defined permission classes for common operations

class CanManageOrg(HasOrgPermission):
    """Can modify organisation settings."""
    permission_field = "can_manage_org"


class CanManageUsers(HasOrgPermission):
    """Can invite and manage users."""
    permission_field = "can_manage_users"


class CanManageCoA(HasOrgPermission):
    """Can modify Chart of Accounts."""
    permission_field = "can_manage_coa"


class CanCreateInvoices(HasOrgPermission):
    """Can create and edit draft invoices."""
    permission_field = "can_create_invoices"


class CanApproveInvoices(HasOrgPermission):
    """Can approve invoices (creates journal entries)."""
    permission_field = "can_approve_invoices"


class CanVoidInvoices(HasOrgPermission):
    """Can void approved invoices."""
    permission_field = "can_void_invoices"


class CanCreateJournals(HasOrgPermission):
    """Can create manual journal entries."""
    permission_field = "can_create_journals"


class CanManageBanking(HasOrgPermission):
    """Can manage bank accounts and reconciliation."""
    permission_field = "can_manage_banking"


class CanFileGST(HasOrgPermission):
    """Can file GST returns."""
    permission_field = "can_file_gst"


class CanViewReports(HasOrgPermission):
    """Can view financial reports."""
    permission_field = "can_view_reports"


class CanExportData(HasOrgPermission):
    """Can export data (CSV, Excel, PDF)."""
    permission_field = "can_export_data"


class ReadOnly(permissions.BasePermission):
    """Only allow read operations."""
    
    def has_permission(self, request, view):
        return request.method in permissions.SAFE_METHODS
