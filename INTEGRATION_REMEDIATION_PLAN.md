# LedgerSG Frontend-Backend Integration Remediation Plan

> **Version**: 1.0.0  
> **Date**: 2026-03-03  
> **Status**: Analysis Complete - Remediation Pending  
> **Priority**: HIGH

---

## Executive Summary

This document identifies critical integration gaps between the LedgerSG Next.js frontend and Django backend, and provides a comprehensive remediation plan to ensure seamless API communication.

### Current Status
- ✅ CORS Configuration: Properly configured
- ✅ JWT Authentication: Structure correct
- ⚠️ **CRITICAL**: 4 endpoint path mismatches identified
- ⚠️ **HIGH**: Dashboard response format mismatch
- ⚠️ **MEDIUM**: Missing service implementations

---

## Critical Issues Found

### 🔴 CRITICAL-1: Banking Endpoint Path Mismatch

**Severity**: CRITICAL  
**Impact**: Banking module unusable from frontend  
**Status**: Confirmed

#### Problem
Frontend uses paths without `/banking/` prefix:
```typescript
// Frontend (api-client.ts:195-199)
banking: (orgId: string) => ({
  accounts: `/api/v1/${orgId}/bank-accounts/`,
  payments: `/api/v1/${orgId}/payments/`,
  receivePayment: `/api/v1/${orgId}/payments/receive/`,
  makePayment: `/api/v1/${orgId}/payments/make/`,
}),
```

Backend requires `/banking/` prefix:
```python
# Backend (banking/urls.py:28-79)
urlpatterns = [
    path("bank-accounts/", ...),  # /api/v1/{org_id}/banking/bank-accounts/
    path("payments/", ...),       # /api/v1/{org_id}/banking/payments/
    path("payments/receive/", ...),
    path("payments/make/", ...),
]
```

#### Remediation
**File**: `apps/web/src/lib/api-client.ts:193-199`

```typescript
// BEFORE (INCORRECT)
banking: (orgId: string) => ({
  accounts: `/api/v1/${orgId}/bank-accounts/`,
  payments: `/api/v1/${orgId}/payments/`,
  receivePayment: `/api/v1/${orgId}/payments/receive/`,
  makePayment: `/api/v1/${orgId}/payments/make/`,
}),

// AFTER (CORRECT)
banking: (orgId: string) => ({
  accounts: `/api/v1/${orgId}/banking/bank-accounts/`,
  payments: `/api/v1/${orgId}/banking/payments/`,
  receivePayment: `/api/v1/${orgId}/banking/payments/receive/`,
  makePayment: `/api/v1/${orgId}/banking/payments/make/`,
}),
```

#### Verification Steps
```bash
# Test banking endpoint accessibility
curl -X GET http://localhost:8000/api/v1/{org_id}/banking/bank-accounts/ \
  -H "Authorization: Bearer {token}"
```

---

### 🔴 CRITICAL-2: Dashboard Endpoint Path Mismatch

**Severity**: CRITICAL  
**Impact**: Dashboard fails to load data  
**Status**: Confirmed

#### Problem
Frontend calls wrong path:
```typescript
// Frontend (dashboard-client.tsx:67)
const { data, isLoading, error } = useQuery<DashboardData>({
  queryKey: ["dashboard", orgId],
  queryFn: () => api.get<DashboardData>(`/api/v1/${orgId}/dashboard/`),
  enabled: !!orgId,
});
```

Backend expects `/reports/` prefix:
```python
# Backend (reporting/urls.py:18-22)
urlpatterns = [
    path("dashboard/metrics/", DashboardMetricsView.as_view(), name="dashboard-metrics"),
    path("dashboard/alerts/", DashboardAlertsView.as_view(), name="dashboard-alerts"),
]
```

#### Remediation
**File**: `apps/web/src/lib/api-client.ts:188-191`

```typescript
// BEFORE (INCORRECT)
dashboard: (orgId: string) => ({
  metrics: `/api/v1/${orgId}/dashboard/metrics/`,
  alerts: `/api/v1/${orgId}/dashboard/alerts/`,
}),

// AFTER (CORRECT)
dashboard: (orgId: string) => ({
  metrics: `/api/v1/${orgId}/reports/dashboard/metrics/`,
  alerts: `/api/v1/${orgId}/reports/dashboard/alerts/`,
}),
```

Also update dashboard-client.tsx:
**File**: `apps/web/src/app/(dashboard)/dashboard/dashboard-client.tsx:67`

```typescript
// BEFORE
queryFn: () => api.get<DashboardData>(`/api/v1/${orgId}/dashboard/`),

// AFTER
queryFn: () => api.get<DashboardData>(`/api/v1/${orgId}/reports/dashboard/metrics/`),
```

---

### 🔴 CRITICAL-3: Dashboard Response Format Mismatch

**Severity**: CRITICAL  
**Impact**: Dashboard UI cannot display data  
**Status**: Confirmed

#### Problem
Frontend expects:
```typescript
interface DashboardData {
  gst_payable: string;
  gst_payable_display: string;
  outstanding_receivables: string;
  outstanding_payables: string;
  revenue_mtd: string;
  revenue_ytd: string;
  cash_on_hand: string;
  gst_threshold_status: "SAFE" | "WARNING" | "CRITICAL" | "EXCEEDED";
  gst_threshold_utilization: number;
  gst_threshold_amount: string;
  gst_threshold_limit: string;
  compliance_alerts: ComplianceAlert[];
  invoices_pending: number;
  invoices_overdue: number;
  invoices_peppol_pending: number;
  current_gst_period: GSTPeriod;
  last_updated: string;
}
```

Backend returns stub:
```python
{
    "period": {"start": "...", "end": "..."},
    "revenue": {"current_month": "0.00", ...},
    "expenses": {"current_month": "0.00", ...},
    "profit": {"current_month": "0.00", ...},
    "outstanding": {"total": "0.00", "count": 0, ...},
    "bank_balance": {"total": "0.00", "accounts": []},
    "gst_summary": {"registered": False, ...},
    "invoice_summary": {"draft": 0, "sent": 0, ...},
}
```

#### Remediation

**Option A**: Update frontend to match backend (Recommended for MVP)
Update dashboard-client.tsx types and data mapping

**Option B**: Implement proper DashboardService (Recommended for Production)
Create comprehensive dashboard service in backend

**Decision**: Implement Option A first, then Option B

**File**: `apps/backend/apps/core/services/dashboard_service.py`

Needs to be updated to return format matching frontend expectations.

---

### 🟠 HIGH-1: Fiscal Periods Endpoints Not Implemented

**Severity**: HIGH  
**Impact**: Frontend fiscal year/period features broken  
**Status**: Confirmed

#### Problem
Frontend expects:
```typescript
fiscal: (orgId: string) => ({
  years: `/api/v1/${orgId}/fiscal-years/`,
  periods: `/api/v1/${orgId}/fiscal-periods/`,
  closeYear: (id: string) => `/api/v1/${orgId}/fiscal-years/${id}/close/`,
  closePeriod: (id: string) => `/api/v1/${orgId}/fiscal-periods/${id}/close/`,
}),
```

Backend has limited implementation:
```python
# core/urls.py:57 only has:
path("fiscal-years/", FiscalYearListView.as_view(), name="org-fiscal-years"),

# Missing:
# - fiscal-periods/
# - fiscal-years/{id}/close/
# - fiscal-periods/{id}/close/
```

#### Remediation

**Step 1**: Implement missing endpoints in backend

**File**: `apps/backend/apps/core/urls.py`

Add to `org_detail_urlpatterns`:
```python
path("fiscal-periods/", FiscalPeriodListView.as_view(), name="org-fiscal-periods"),
path("fiscal-years/<str:year_id>/close/", FiscalYearCloseView.as_view(), name="fiscal-year-close"),
path("fiscal-periods/<str:period_id>/close/", FiscalPeriodCloseView.as_view(), name="fiscal-period-close"),
```

**Step 2**: Create view implementations

**File**: `apps/backend/apps/core/views/fiscal.py` (NEW)

```python
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from apps.core.permissions import IsOrgMember
from apps.core.models import FiscalYear, FiscalPeriod


class FiscalPeriodListView(APIView):
    """List fiscal periods for organization."""
    permission_classes = [IsAuthenticated, IsOrgMember]
    
    def get(self, request, org_id):
        periods = FiscalPeriod.objects.filter(org_id=org_id).order_by("-start_date")
        return Response([{
            "id": str(p.id),
            "name": p.name,
            "start_date": p.start_date.isoformat(),
            "end_date": p.end_date.isoformat(),
            "status": p.status,
        } for p in periods])


class FiscalYearCloseView(APIView):
    """Close a fiscal year."""
    permission_classes = [IsAuthenticated, IsOrgMember]
    
    def post(self, request, org_id, year_id):
        # TODO: Implement fiscal year closing logic
        return Response({"message": "Fiscal year closed successfully"})


class FiscalPeriodCloseView(APIView):
    """Close a fiscal period."""
    permission_classes = [IsAuthenticated, IsOrgMember]
    
    def post(self, request, org_id, period_id):
        # TODO: Implement fiscal period closing logic
        return Response({"message": "Fiscal period closed successfully"})
```

---

### 🟠 HIGH-2: Peppol Endpoints Not Implemented

**Severity**: HIGH  
**Impact**: Peppol features cannot be used  
**Status**: Confirmed

#### Problem
Frontend expects:
```typescript
peppol: (orgId: string) => ({
  transmissionLog: `/api/v1/${orgId}/peppol/transmission-log/`,
  settings: `/api/v1/${orgId}/peppol/settings/`,
}),
```

Backend has empty implementation:
```python
# apps/peppol/urls.py
urlpatterns = []  # Empty!
```

#### Remediation

**Step 1**: Create stub endpoints

**File**: `apps/backend/apps/peppol/urls.py`

```python
from django.urls import path
from .views import PeppolTransmissionLogView, PeppolSettingsView

urlpatterns = [
    path("transmission-log/", PeppolTransmissionLogView.as_view(), name="peppol-transmission-log"),
    path("settings/", PeppolSettingsView.as_view(), name="peppol-settings"),
]
```

**Step 2**: Create stub views

**File**: `apps/backend/apps/peppol/views.py` (UPDATE)

```python
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from apps.core.permissions import IsOrgMember


class PeppolTransmissionLogView(APIView):
    """Get Peppol transmission log."""
    permission_classes = [IsAuthenticated, IsOrgMember]
    
    def get(self, request, org_id):
        return Response({
            "transmissions": [],
            "total": 0,
            "pending": 0,
            "failed": 0,
        })


class PeppolSettingsView(APIView):
    """Get/set Peppol settings."""
    permission_classes = [IsAuthenticated, IsOrgMember]
    
    def get(self, request, org_id):
        return Response({
            "enabled": False,
            "participant_id": None,
            "endpoint": None,
        })
    
    def patch(self, request, org_id):
        return Response({"message": "Settings updated"})
```

---

### 🟡 MEDIUM-1: Organisation Settings Endpoint Not Verified

**Severity**: MEDIUM  
**Impact**: Organisation settings cannot be saved  
**Status**: Needs Verification

#### Problem
Frontend defines:
```typescript
organisations: {
  detail: (id: string) => `/api/v1/${id}/`,
  settings: (id: string) => `/api/v1/${id}/settings/`,  # Does this exist?
}
```

Need to verify if `/api/v1/{org_id}/settings/` exists in backend.

#### Verification Steps
```bash
# Check if settings endpoint exists
curl -X GET http://localhost:8000/api/v1/{org_id}/settings/ \
  -H "Authorization: Bearer {token}"
```

If 404, implement stub endpoint:

**File**: `apps/backend/apps/core/urls.py`

Add to `org_detail_urlpatterns`:
```python
path("settings/", OrganisationSettingsView.as_view(), name="org-settings"),
```

**File**: `apps/backend/apps/core/views/organisations.py`

```python
class OrganisationSettingsView(APIView):
    """Get/set organisation settings."""
    permission_classes = [IsAuthenticated, IsOrgMember]
    
    def get(self, request, org_id):
        org = Organisation.objects.get(id=org_id)
        return Response({
            "fy_start_month": org.fy_start_month,
            "base_currency": org.base_currency,
            "timezone": org.timezone,
            "gst_scheme": org.gst_scheme,
            "gst_filing_frequency": org.gst_filing_frequency,
        })
    
    def patch(self, request, org_id):
        # TODO: Implement settings update
        return Response({"message": "Settings updated"})
```

---

## Implementation Priority

### Phase 1: Critical Fixes (Day 1)
1. ✅ Fix banking endpoint paths in api-client.ts
2. ✅ Fix dashboard endpoint paths in api-client.ts and dashboard-client.tsx
3. ✅ Update dashboard-client.tsx to use api-client endpoints

### Phase 2: High Priority (Day 2-3)
4. Implement fiscal periods endpoints
5. Implement Peppol stub endpoints

### Phase 3: Medium Priority (Week 1)
6. Implement organisation settings endpoint
7. Implement proper DashboardService

### Phase 4: Validation (Week 1)
8. Run integration tests
9. Verify all endpoints respond correctly
10. Test end-to-end workflows

---

## Verification Checklist

- [ ] Banking endpoints return 200 with correct data
- [ ] Dashboard loads without errors
- [ ] Fiscal years/periods endpoints accessible
- [ ] Peppol endpoints return stub data
- [ ] Organisation settings can be fetched
- [ ] Auth refresh works correctly
- [ ] CORS headers present on all responses
- [ ] No 404 errors in browser console

---

## Testing Commands

```bash
# Test authentication
curl -X POST http://localhost:8000/api/v1/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"email": "test@example.com", "password": "password123"}'

# Test banking endpoint
curl -X GET http://localhost:8000/api/v1/{org_id}/banking/bank-accounts/ \
  -H "Authorization: Bearer {token}"

# Test dashboard endpoint
curl -X GET http://localhost:8000/api/v1/{org_id}/reports/dashboard/metrics/ \
  -H "Authorization: Bearer {token}"

# Test fiscal periods
curl -X GET http://localhost:8000/api/v1/{org_id}/fiscal-periods/ \
  -H "Authorization: Bearer {token}"

# Test Peppol
curl -X GET http://localhost:8000/api/v1/{org_id}/peppol/settings/ \
  -H "Authorization: Bearer {token}"
```

---

## Documentation Updates Required

- [ ] Update API_CLI_Usage_Guide.md with correct endpoint paths
- [ ] Update CLAUDE.md integration section
- [ ] Update README.md with integration status
- [ ] Add troubleshooting guide for common integration issues

---

**End of Remediation Plan**
