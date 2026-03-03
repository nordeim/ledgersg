# Phase 1 Execution Plan: Quick Wins

> **Version**: 1.0.0  
> **Date**: 2026-03-03  
> **Status**: Ready for Execution  
> **Estimated Duration**: 3-4 hours  
> **Priority**: HIGH

---

## Phase 1 Overview

**Objective**: Implement quick-win integration gaps that require minimal effort but provide immediate value.

**Scope**:
1. **GAP-4**: Organisation Settings Endpoint (MEDIUM) - 1-2 hours
2. **GAP-3**: Peppol Endpoints (HIGH) - 2-3 hours

**Success Criteria**:
- [ ] Organisation settings endpoint returns 200 with correct data
- [ ] Peppol settings endpoint returns 200
- [ ] Peppol transmission-log endpoint returns 200
- [ ] All endpoints follow DRF best practices
- [ ] Code follows existing patterns in codebase

---

## Task 1: Organisation Settings Endpoint (GAP-4)

### Task Details

**Priority**: MEDIUM  
**Effort**: 1-2 hours  
**Files to Modify**: 2  
**New Files**: 0

### Implementation Steps

#### Step 1.1: Add URL Route

**File**: `apps/backend/apps/core/urls.py`

**Location**: Add to `org_detail_urlpatterns` list (around line 51-59)

**Code to Add**:
```python
path("settings/", OrganisationSettingsView.as_view(), name="org-settings"),
```

**Verification**:
```bash
curl -X GET http://localhost:8000/api/v1/{org_id}/settings/ \
  -H "Authorization: Bearer {token}"
# Should return 200 or 404 (before implementation)
```

#### Step 1.2: Import View

**File**: `apps/backend/apps/core/urls.py`

**Location**: Add to imports (around line 20-26)

**Code to Add**:
```python
from apps.core.views.organisations import (
    OrganisationListCreateView,
    OrganisationDetailView,
    GSTRegistrationView,
    FiscalYearListView,
    OrganisationSummaryView,
    OrganisationSettingsView,  # ADD THIS
)
```

#### Step 1.3: Implement View

**File**: `apps/backend/apps/core/views/organisations.py`

**Location**: Add after OrganisationSummaryView (around line 221)

**Implementation**:
```python
class OrganisationSettingsView(APIView):
    """
    GET / PATCH: Organisation settings.
    
    Returns or updates organisation configuration settings.
    """
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, IsOrgMember]
    
    def get(self, request, org_id: str) -> Response:
        """Get organisation settings."""
        try:
            org = Organisation.objects.get(id=org_id)
            return Response({
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
            })
        except Organisation.DoesNotExist:
            return Response(
                {"error": {"code": "not_found", "message": "Organisation not found"}},
                status=status.HTTP_404_NOT_FOUND
            )
    
    def patch(self, request, org_id: str) -> Response:
        """Update organisation settings."""
        try:
            org = Organisation.objects.get(id=org_id)
            
            # Update allowed fields
            allowed_fields = [
                "name", "legal_name", "uen", "entity_type",
                "base_currency", "timezone", "fy_start_month",
                "gst_registered", "gst_reg_number", "gst_scheme",
                "gst_filing_frequency", "peppol_participant_id",
                "invoicenow_enabled"
            ]
            
            for field in allowed_fields:
                if field in request.data:
                    setattr(org, field, request.data[field])
            
            org.save()
            
            return Response({
                "message": "Settings updated successfully",
                "id": str(org.id),
                "updated_fields": list(request.data.keys())
            })
        except Organisation.DoesNotExist:
            return Response(
                {"error": {"code": "not_found", "message": "Organisation not found"}},
                status=status.HTTP_404_NOT_FOUND
            )
```

**Verification**:
```bash
# Test GET
curl -X GET http://localhost:8000/api/v1/{org_id}/settings/ \
  -H "Authorization: Bearer {token}"

# Test PATCH
curl -X PATCH http://localhost:8000/api/v1/{org_id}/settings/ \
  -H "Authorization: Bearer {token}" \
  -H "Content-Type: application/json" \
  -d '{"name": "Updated Company Name"}'
```

---

## Task 2: Peppol Endpoints (GAP-3)

### Task Details

**Priority**: HIGH  
**Effort**: 2-3 hours  
**Files to Modify**: 2  
**New Files**: 1

### Implementation Steps

#### Step 2.1: Create Peppol Views

**File**: `apps/backend/apps/peppol/views.py` (NEW FILE)

**Implementation**:
```python
"""
Peppol/InvoiceNow integration views for LedgerSG.

Provides endpoints for Peppol transmission management and settings.
"""

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status

from apps.core.permissions import IsOrgMember
from common.exceptions import ValidationError


class PeppolTransmissionLogView(APIView):
    """
    GET: Peppol transmission log.
    
    Returns transmission history for InvoiceNow/Peppol documents.
    """
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, IsOrgMember]
    
    def get(self, request, org_id: str) -> Response:
        """Get Peppol transmission log."""
        # TODO: Implement actual query from database
        # For now, return empty stub
        
        status_filter = request.query_params.get("status")
        
        # Stub response
        transmissions = []
        
        return Response({
            "results": transmissions,
            "count": len(transmissions),
            "pending": 0,
            "failed": 0,
            "completed": 0,
            "meta": {
                "status_filter": status_filter,
                "stub": True,
                "message": "Peppol integration not yet fully implemented"
            }
        })


class PeppolSettingsView(APIView):
    """
    GET / PATCH: Peppol settings.
    
    Manage Peppol/InvoiceNow configuration for the organisation.
    """
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, IsOrgMember]
    
    def get(self, request, org_id: str) -> Response:
        """Get Peppol settings."""
        from apps.core.models import Organisation
        
        try:
            org = Organisation.objects.get(id=org_id)
            return Response({
                "enabled": org.invoicenow_enabled,
                "participant_id": org.peppol_participant_id,
                "endpoint": None,  # TODO: Add to model
                "test_mode": True,  # TODO: Add to model
                "supported_formats": ["UBL"],
                "status": "configured" if org.peppol_participant_id else "not_configured"
            })
        except Organisation.DoesNotExist:
            return Response(
                {"error": {"code": "not_found", "message": "Organisation not found"}},
                status=status.HTTP_404_NOT_FOUND
            )
    
    def patch(self, request, org_id: str) -> Response:
        """Update Peppol settings."""
        from apps.core.models import Organisation
        
        try:
            org = Organisation.objects.get(id=org_id)
            
            # Update allowed fields
            if "enabled" in request.data:
                org.invoicenow_enabled = request.data["enabled"]
            
            if "participant_id" in request.data:
                org.peppol_participant_id = request.data["participant_id"]
            
            org.save()
            
            return Response({
                "message": "Peppol settings updated",
                "enabled": org.invoicenow_enabled,
                "participant_id": org.peppol_participant_id
            })
        except Organisation.DoesNotExist:
            return Response(
                {"error": {"code": "not_found", "message": "Organisation not found"}},
                status=status.HTTP_404_NOT_FOUND
            )
```

#### Step 2.2: Update Peppol URLs

**File**: `apps/backend/apps/peppol/urls.py`

**Current State**:
```python
# apps/peppol/urls.py
urlpatterns = []
```

**New Implementation**:
```python
"""
Peppol URL configuration.

Routes for InvoiceNow/Peppol integration endpoints.
"""

from django.urls import path
from .views import PeppolTransmissionLogView, PeppolSettingsView

app_name = "peppol"

urlpatterns = [
    path(
        "transmission-log/",
        PeppolTransmissionLogView.as_view(),
        name="peppol-transmission-log"
    ),
    path(
        "settings/",
        PeppolSettingsView.as_view(),
        name="peppol-settings"
    ),
]
```

#### Step 2.3: Verify URL Inclusion

**File**: `apps/backend/config/urls.py`

**Current State**: Already includes peppol (line 108)
```python
try:
    org_scoped_urlpatterns.append(path("peppol/", include("apps.peppol.urls")))
except ImportError:
    pass
```

**Verification**:
```bash
# Test transmission-log
curl -X GET http://localhost:8000/api/v1/{org_id}/peppol/transmission-log/ \
  -H "Authorization: Bearer {token}"

# Test settings GET
curl -X GET http://localhost:8000/api/v1/{org_id}/peppol/settings/ \
  -H "Authorization: Bearer {token}"

# Test settings PATCH
curl -X PATCH http://localhost:8000/api/v1/{org_id}/peppol/settings/ \
  -H "Authorization: Bearer {token}" \
  -H "Content-Type: application/json" \
  -d '{"enabled": true, "participant_id": "0192:12345678"}'
```

---

## Implementation Checklist

### Pre-Implementation
- [ ] Review Organisation model fields
- [ ] Check existing view patterns in organisations.py
- [ ] Verify Peppol URL inclusion in main urls.py

### Task 1: Organisation Settings
- [ ] Add URL route in core/urls.py
- [ ] Add import for OrganisationSettingsView
- [ ] Implement OrganisationSettingsView in organisations.py
- [ ] Test GET endpoint
- [ ] Test PATCH endpoint
- [ ] Verify response format

### Task 2: Peppol Endpoints
- [ ] Create apps/peppol/views.py
- [ ] Implement PeppolTransmissionLogView
- [ ] Implement PeppolSettingsView
- [ ] Update apps/peppol/urls.py
- [ ] Test transmission-log endpoint
- [ ] Test settings GET endpoint
- [ ] Test settings PATCH endpoint

### Post-Implementation
- [ ] Run Django system checks
- [ ] Verify no import errors
- [ ] Update documentation
- [ ] Mark tasks complete in INTEGRATION_GAPS_CLOSURE_PLAN.md

---

## Code Review Criteria

### Organisation Settings
- [ ] Follows DRF APIView pattern
- [ ] Uses JWTAuthentication
- [ ] Uses IsOrgMember permission
- [ ] Returns proper error responses (404)
- [ ] Handles PATCH updates correctly
- [ ] Returns all relevant Organisation fields

### Peppol Endpoints
- [ ] Follows DRF APIView pattern
- [ ] Uses JWTAuthentication
- [ ] Uses IsOrgMember permission
- [ ] Returns proper error responses (404)
- [ ] Stub implementation is documented with TODOs
- [ ] Returns appropriate placeholder data

---

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| Organisation model missing fields | Check model before implementation |
| Import errors | Verify all imports exist |
| URL conflicts | Check no duplicate routes |
| Permission issues | Test with authenticated user |

---

## Rollback Plan

If issues arise:
1. Revert core/urls.py changes
2. Revert organisations.py changes
3. Delete peppol/views.py (if created)
4. Revert peppol/urls.py to empty

---

**Plan Ready for Execution**
