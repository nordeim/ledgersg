# Phase 4: Integration — TDD Implementation Sub-Plan

## Overview

**Phase**: 4 of 5
**Duration**: Days 13-15
**Objective**: Integrate Peppol transmission with invoice approval workflow and Celery async tasks
**TDD Approach**: RED → GREEN → REFACTOR for each component
**Target Tests**: 16 tests

---

## Success Criteria

- [ ] Celery tasks created for async transmission
- [ ] Invoice approval triggers Peppol transmission when auto_transmit enabled
- [ ] API endpoints return real data (not stubs)
- [ ] **16 TDD tests passing** (100% coverage)
- [ ] Retry logic works with exponential backoff
- [ ] No regressions in existing 108 tests

---

## Codebase Validation Summary

### Existing Infrastructure (Verified)

**Document Service** (`apps/invoicing/services/document_service.py`):
- `approve_document()` function at line 530 ✓
- Creates journal entries on approval ✓
- Status workflow: DRAFT → APPROVED ✓

**Peppol Views** (`apps/peppol/views.py`):
- Stub endpoints: PeppolTransmissionLogView, PeppolSettingsView ✓
- Need to replace with real implementations ✓

**Transmission Service** (`apps/peppol/services/transmission_service.py`):
- `transmit_invoice()` method ready ✓
- `retry_transmission()` method ready ✓

**Dependencies**:
- Celery configured in `config/celery.py` ✓
- `@shared_task` decorator available ✓

---

## Task Breakdown

### Task 4.1: Create Celery Tasks
**Priority**: HIGH
**Duration**: 4 hours
**Dependencies**: Phase 3 complete

#### 4.1.1 Create Tasks File
**File**: `apps/backend/apps/peppol/tasks.py`

**Purpose**: Celery tasks for async Peppol transmission

**Tasks to Create**:
```python
@shared_task(bind=True, max_retries=3)
def transmit_peppol_invoice_task(self, transmission_log_id: str):
    """Async task to transmit invoice via Peppol."""
    pass

@shared_task(bind=True, max_retries=3)
def retry_failed_transmission_task(self, transmission_log_id: str):
    """Async task to retry failed transmission."""
    pass

@shared_task
def check_transmission_status_task(message_id: str):
    """Check status of in-flight transmission."""
    pass
```

**TDD Tests (6 tests)**:

| Test | Purpose | Expected Result |
|------|---------|-----------------|
| `test_transmit_task_exists` | Task registered | Can import and call task |
| `test_transmit_task_calls_service` | Service integration | TransmissionService.transmit_invoice called |
| `test_transmit_task_success` | Success handling | Log updated to DELIVERED |
| `test_transmit_task_failure` | Failure handling | Retry triggered |
| `test_retry_task_exists` | Task registered | retry_failed_transmission_task callable |
| `test_status_check_task_exists` | Task registered | check_transmission_status_task callable |

---

### Task 4.2: Integrate with Invoice Approval
**Priority**: HIGH
**Duration**: 6 hours
**Dependencies**: Task 4.1 complete

#### 4.2.1 Modify Document Service
**File**: `apps/backend/apps/invoicing/services/document_service.py`

**Location**: After `approve_document()` completes (around line 578)

**Add**:
```python
def approve_document(org_id: UUID, document_id: UUID, user) -> InvoiceDocument:
    """
    Approve invoice with Peppol integration.
    
    After approval:
    1. Create journal entries
    2. Check if Peppol auto-transmit enabled
    3. Queue for transmission if enabled
    """
    # Existing approval logic...
    
    # NEW: Peppol auto-transmit integration
    if document.document_type == "SALES_INVOICE":
        _queue_peppol_transmission(document, org_id)
    
    return document

def _queue_peppol_transmission(document: InvoiceDocument, org_id: UUID) -> Optional[str]:
    """
    Queue document for Peppol transmission if configured.
    
    Returns Celery task ID or None if not queued.
    """
    from apps.peppol.models import OrganisationPeppolSettings
    from apps.peppol.tasks import transmit_peppol_invoice_task
    
    # Check if Peppol enabled and configured
    settings = OrganisationPeppolSettings.objects.filter(
        org_id=org_id
    ).first()
    
    if not settings or not settings.is_configured:
        return None
    
    if not settings.auto_transmit:
        return None
    
    # Check if recipient has Peppol ID
    if not document.contact or not document.contact.peppol_id:
        return None
    
    # Create transmission log and queue task
    from apps.peppol.models import PeppolTransmissionLog
    log = PeppolTransmissionLog.objects.create(
        org_id=org_id,
        document_id=document.id,
        status="PENDING",
        access_point_provider=settings.access_point_provider
    )
    
    # Queue async task
    task = transmit_peppol_invoice_task.delay(str(log.id))
    return task.id
```

**TDD Tests (6 tests)**:

| Test | Purpose | Expected Result |
|------|---------|-----------------|
| `test_approval_queues_peppol_when_configured` | Auto-transmit | Task queued, log created |
| `test_approval_skips_peppol_when_not_configured` | No settings | No task queued |
| `test_approval_skips_when_auto_transmit_false` | Disabled | No task queued |
| `test_approval_skips_when_no_peppol_id` | No recipient | No task queued |
| `test_approval_skips_non_invoice_documents` | Quotes | No task queued |
| `test_approval_creates_transmission_log` | Log creation | PeppolTransmissionLog created |

---

### Task 4.3: Update API Endpoints
**Priority**: MEDIUM
**Duration**: 4 hours
**Dependencies**: Task 4.2 complete

#### 4.3.1 Replace Stub Implementations
**File**: `apps/backend/apps/peppol/views.py`

**Current**: Stub implementations with "TODO" comments

**Update**:
```python
class PeppolTransmissionLogView(APIView):
    """GET: Peppol transmission log with real data."""
    
    @wrap_response
    def get(self, request, org_id: str) -> Response:
        """Get real transmission log from database."""
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
            }
            for t in queryset.order_by("-transmitted_at")
        ]
        
        return Response({
            "results": transmissions,
            "count": len(transmissions),
            "pending": queryset.filter(status="PENDING").count(),
            "failed": queryset.filter(status="FAILED").count(),
            "completed": queryset.filter(status="DELIVERED").count(),
        })

class PeppolSettingsView(APIView):
    """GET / PATCH: Real Peppol settings management."""
    
    @wrap_response
    def get(self, request, org_id: str) -> Response:
        """Get real Peppol settings from database."""
        from apps.peppol.models import OrganisationPeppolSettings
        from apps.core.models import Organisation
        
        try:
            org = Organisation.objects.get(id=org_id)
            settings = OrganisationPeppolSettings.objects.filter(
                org_id=org_id
            ).first()
            
            return Response({
                "enabled": org.invoicenow_enabled,
                "participant_id": org.peppol_participant_id,
                "is_configured": settings.is_configured if settings else False,
                "access_point_provider": settings.access_point_provider if settings else None,
                "auto_transmit": settings.auto_transmit if settings else False,
                "retry_attempts": settings.transmission_retry_attempts if settings else 3,
            })
        except Organisation.DoesNotExist:
            return Response(
                {"error": {"code": "not_found", "message": "Organisation not found"}},
                status=status.HTTP_404_NOT_FOUND
            )
```

**TDD Tests (4 tests)**:

| Test | Purpose | Expected Result |
|------|---------|-----------------|
| `test_transmission_log_returns_real_data` | Real data | Returns actual logs |
| `test_transmission_log_filters_by_status` | Filtering | Returns filtered results |
| `test_settings_returns_real_configuration` | Real settings | Returns actual settings |
| `test_settings_404_when_org_not_found` | Error handling | Returns 404 |

---

## Execution Checklist

### Pre-Execution Validation
- [ ] Verify Celery is configured
- [ ] Verify `approve_document` function exists
- [ ] Verify Peppol models are importable
- [ ] Verify TransmissionService is importable

### Task 4.1: Celery Tasks (RED → GREEN → REFACTOR)

**RED Phase:**
- [ ] Create test file: `apps/backend/apps/peppol/tests/test_tasks.py`
- [ ] Write 6 failing tests (see table above)
- [ ] Run tests, confirm all 6 fail

**GREEN Phase:**
- [ ] Create `apps/backend/apps/peppol/tasks.py`
- [ ] Implement `transmit_peppol_invoice_task`
- [ ] Implement `retry_failed_transmission_task`
- [ ] Implement `check_transmission_status_task`
- [ ] Run tests, confirm all 6 pass

**REFACTOR Phase:**
- [ ] Add comprehensive docstrings
- [ ] Add retry configuration
- [ ] Add error logging

### Task 4.2: Invoice Approval Integration (RED → GREEN → REFACTOR)

**RED Phase:**
- [ ] Create test file: `apps/backend/apps/invoicing/tests/test_peppol_integration.py`
- [ ] Write 6 failing tests (see table above)
- [ ] Run tests, confirm all 6 fail

**GREEN Phase:**
- [ ] Modify `apps/invoicing/services/document_service.py`
- [ ] Add `_queue_peppol_transmission` helper
- [ ] Modify `approve_document` to call helper
- [ ] Run tests, confirm all 6 pass

**REFACTOR Phase:**
- [ ] Add logging for transmission queuing
- [ ] Review error handling
- [ ] Document integration points

### Task 4.3: API Endpoints (RED → GREEN → REFACTOR)

**RED Phase:**
- [ ] Create test file: `apps/backend/apps/peppol/tests/test_views.py`
- [ ] Write 4 failing tests (see table above)
- [ ] Run tests, confirm all 4 fail

**GREEN Phase:**
- [ ] Update `apps/peppol/views.py`
- [ ] Replace stub implementations
- [ ] Add real database queries
- [ ] Run tests, confirm all 4 pass

**REFACTOR Phase:**
- [ ] Add pagination for transmission log
- [ ] Add filtering options
- [ ] Document API responses

---

## Verification Commands

### Task Verification
```bash
# Run Phase 4 tests only
cd apps/backend
pytest apps/peppol/tests/test_tasks.py \
       apps/invoicing/tests/test_peppol_integration.py \
       apps/peppol/tests/test_views.py \
       -v --reuse-db --no-migrations

# Expected: 16 tests passing
```

### Full Integration Test
```bash
# Run all Peppol tests
cd apps/backend
pytest apps/peppol/tests/ apps/invoicing/tests/ -v --reuse-db --no-migrations

# Expected: 124 tests passing (108 + 16 new)
```

---

## Success Metrics

| Metric | Target | Verification |
|--------|--------|------------|
| Celery Tasks | 3 tasks created | Importable and testable |
| Task Tests | 6/6 passing | pytest reports |
| Integration Tests | 6/6 passing | pytest reports |
| View Tests | 4/4 passing | pytest reports |
| Total Coverage | 16/16 tests | pytest summary |
| No Regressions | Existing tests | Full test suite passes |

---

## Next Phase Readiness

**Phase 4 is complete when:**
- [ ] 16/16 Phase 4 tests passing
- [ ] Celery tasks can be queued
- [ ] Invoice approval triggers transmission
- [ ] API endpoints return real data
- [ ] No regressions in existing 108 tests

**Phase 5 Prerequisites:**
- Phase 4 complete ✅
- Async transmission working
- API endpoints returning real data
- Ready for end-to-end testing

---

**Sub-Plan Status**: READY FOR EXECUTION
**Next Step**: Create Celery tasks (Task 4.1)
**Confidence**: High (based on solid Phase 1-3 foundation)
**Estimated Duration**: 2 days (14 hours total)
