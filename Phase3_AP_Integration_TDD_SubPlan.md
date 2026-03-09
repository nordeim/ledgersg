# Phase 3: Access Point Integration — TDD Implementation Sub-Plan

## Overview

**Phase**: 3 of 5
**Duration**: Days 9-12
**Objective**: Create Access Point adapters and transmission service for Peppol/InvoiceNow integration
**TDD Approach**: RED → GREEN → REFACTOR for each component
**Target Tests**: 18 tests (6 adapter base + 8 Storecove adapter + 4 transmission service)

---

## Success Criteria

- [ ] Abstract AP Adapter Base created with interface methods
- [ ] Storecove Adapter implements all required methods
- [ ] Transmission Service orchestrates the complete workflow
- [ ] **18 TDD tests passing** (100% coverage)
- [ ] All error cases handled (auth, network, validation)
- [ ] Retry logic implemented with exponential backoff
- [ ] No regressions in existing 85 tests

---

## Codebase Validation Summary

### Existing Infrastructure (Verified)

**Models** (`apps/peppol/models.py`):
- `PeppolTransmissionLog` - Complete with all fields ✓
- `OrganisationPeppolSettings` - Complete with `is_configured` property ✓
- Status choices: PENDING, TRANSMITTING, DELIVERED, FAILED, REJECTED ✓

**Services** (`apps/peppol/services/`):
- `XMLMappingService` - Maps InvoiceDocument to UBL structure ✓
- `XMLGeneratorService` - Generates UBL 2.1 XML with namespaces ✓
- `XMLValidationService` - Validates against XSD and Schematron ✓

**Schema Files** (`apps/peppol/schemas/`):
- `ubl-Invoice.xsd` - Self-contained, PINT-SG compliant ✓
- `ubl-CreditNote.xsd` - Self-contained ✓
- `PINT-UBL-validation.sch` - Schematron rules ✓

**Dependencies**:
- `requests` - For HTTP API calls (verify in requirements.txt)
- `lxml` - Already available for XML validation ✓
- `hashlib` - Built-in for SHA-256 ✓

---

## Task Breakdown

### Task 3.1: Create AP Adapter Base
**Priority**: HIGH
**Duration**: 4 hours
**Dependencies**: None

#### 3.1.1 Create Abstract Base Class
**File**: `apps/backend/apps/peppol/services/ap_adapter_base.py`

**Purpose**: Define the interface that all AP providers must implement

**Structure**:
```python
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from dataclasses import dataclass
from enum import Enum

class TransmissionStatus(Enum):
    PENDING = "PENDING"
    TRANSMITTING = "TRANSMITTING"
    DELIVERED = "DELIVERED"
    FAILED = "FAILED"
    REJECTED = "REJECTED"

@dataclass
class TransmissionResult:
    success: bool
    message_id: Optional[str]
    status: TransmissionStatus
    error_code: Optional[str]
    error_message: Optional[str]
    raw_response: Optional[Dict[str, Any]]

class APAdapterBase(ABC):
    """Abstract base class for Access Point adapters."""
    
    @abstractmethod
    def authenticate(self) -> bool:
        """Authenticate with the AP provider."""
        pass
    
    @abstractmethod
    def send_invoice(self, xml_payload: str, peppol_id: str) -> TransmissionResult:
        """Send invoice XML to Peppol network."""
        pass
    
    @abstractmethod
    def check_status(self, message_id: str) -> TransmissionResult:
        """Check transmission status."""
        pass
    
    @abstractmethod
    def validate_connection(self) -> bool:
        """Validate AP connection and credentials."""
        pass
```

**TDD Tests (6 tests)**:

| Test | Purpose | Expected Result |
|------|---------|-----------------|
| `test_adapter_base_is_abstract` | Cannot instantiate directly | TypeError raised |
| `test_adapter_base_requires_authenticate` | Abstract method enforcement | NotImplementedError if not implemented |
| `test_adapter_base_requires_send_invoice` | Abstract method enforcement | NotImplementedError if not implemented |
| `test_adapter_base_requires_check_status` | Abstract method enforcement | NotImplementedError if not implemented |
| `test_adapter_base_requires_validate_connection` | Abstract method enforcement | NotImplementedError if not implemented |
| `test_transmission_result_dataclass` | Result structure | Dataclass with all fields |

**Output Structure**:
```python
# Successful transmission
TransmissionResult(
    success=True,
    message_id="0195:202312345A-20260309-001",
    status=TransmissionStatus.DELIVERED,
    error_code=None,
    error_message=None,
    raw_response={"status": "accepted", "tracking_id": "..."}
)

# Failed transmission
TransmissionResult(
    success=False,
    message_id=None,
    status=TransmissionStatus.FAILED,
    error_code="AUTH_ERROR",
    error_message="Invalid API key",
    raw_response={"error": "authentication_failed"}
)
```

---

### Task 3.2: Create Storecove Adapter
**Priority**: HIGH
**Duration**: 8 hours
**Dependencies**: Task 3.1 complete

#### 3.2.1 Implement Storecove Adapter
**File**: `apps/backend/apps/peppol/services/ap_storecove_adapter.py`

**Purpose**: Implement Storecove API integration for Peppol transmission

**API Reference**:
- Base URL: `https://api.storecove.com/api/v2`
- Authentication: API Key in Authorization header
- Endpoints:
  - POST `/document_submissions` - Submit invoice
  - GET `/document_submissions/{id}` - Check status

**Key Methods**:
```python
class StorecoveAdapter(APAdapterBase):
    def __init__(self, api_key: str, client_id: str, base_url: str):
        self.api_key = api_key
        self.client_id = client_id
        self.base_url = base_url
        self.session = requests.Session()
    
    def authenticate(self) -> bool:
        """Validate API key by making a test request."""
        # Make lightweight API call to validate credentials
        pass
    
    def send_invoice(self, xml_payload: str, peppol_id: str) -> TransmissionResult:
        """Send invoice via Storecove API."""
        # 1. Prepare JSON payload with XML
        # 2. POST to /document_submissions
        # 3. Parse response
        # 4. Return TransmissionResult
        pass
    
    def check_status(self, message_id: str) -> TransmissionResult:
        """Check transmission status via Storecove."""
        # GET /document_submissions/{id}
        pass
    
    def validate_connection(self) -> bool:
        """Test API connectivity."""
        # Lightweight ping to API
        pass
    
    def _prepare_payload(self, xml_payload: str, peppol_id: str) -> Dict[str, Any]:
        """Prepare Storecove API payload."""
        # Format according to Storecove API spec
        pass
    
    def _parse_response(self, response: requests.Response) -> TransmissionResult:
        """Parse Storecove API response."""
        # Handle different status codes and errors
        pass
```

**TDD Tests (8 tests)**:

| Test | Purpose | Expected Result |
|------|---------|-----------------|
| `test_storecove_adapter_inherits_base` | Inheritance | isinstance(APAdapterBase) |
| `test_storecove_adapter_init` | Initialization | All attributes set correctly |
| `test_storecove_authenticate_success` | Auth success | Returns True |
| `test_storecove_authenticate_failure` | Auth failure | Returns False on 401 |
| `test_storecove_send_invoice_success` | Successful send | TransmissionResult with message_id |
| `test_storecove_send_invoice_failure` | Send failure | TransmissionResult with error |
| `test_storecove_check_status_delivered` | Status check | Returns DELIVERED status |
| `test_storecove_validate_connection` | Connection test | Returns True if API reachable |

**Test Mocking Strategy**:
```python
# Use responses library or unittest.mock to mock HTTP calls
@responses.activate
def test_storecove_send_invoice_success():
    responses.add(
        responses.POST,
        "https://api.storecove.com/api/v2/document_submissions",
        json={"id": "msg-123", "status": "accepted"},
        status=201
    )
    # Test implementation...
```

**Error Handling**:
- `401 Unauthorized` → Authentication failure
- `400 Bad Request` → Invalid XML format
- `422 Unprocessable` → Peppol validation error
- `429 Rate Limited` → Retry after delay
- `5xx Server Error` → Retry with backoff

---

### Task 3.3: Create Transmission Service
**Priority**: HIGH
**Duration**: 8 hours
**Dependencies**: Tasks 3.1, 3.2 complete

#### 3.3.1 Implement Transmission Service
**File**: `apps/backend/apps/peppol/services/transmission_service.py`

**Purpose**: Orchestrate the complete transmission workflow

**Workflow**:
```
Invoice Approval
    ↓
Generate XML (XMLGeneratorService)
    ↓
Validate XML (XMLValidationService)
    ↓
Send to AP (AP Adapter)
    ↓
Update Transmission Log
    ↓
Handle Response/Retry
```

**Key Methods**:
```python
class TransmissionService:
    def __init__(self):
        self.mapping_service = XMLMappingService()
        self.generator_service = XMLGeneratorService()
        self.validation_service = XMLValidationService()
    
    def transmit_invoice(self, invoice_id: str, org_id: str) -> PeppolTransmissionLog:
        """
        Main method to transmit an invoice via Peppol.
        
        Returns:
            PeppolTransmissionLog: The transmission log entry
        """
        # 1. Get invoice and org
        # 2. Check if Peppol configured
        # 3. Create transmission log entry
        # 4. Generate XML
        # 5. Validate XML
        # 6. Get AP adapter
        # 7. Send to AP
        # 8. Update log with result
        # 9. Handle retry if failed
        pass
    
    def queue_for_transmission(self, invoice_id: str, org_id: str) -> str:
        """
        Queue invoice for async transmission (returns Celery task ID).
        """
        # Create PENDING log entry
        # Queue Celery task
        # Return task ID
        pass
    
    def retry_transmission(self, transmission_log_id: str) -> PeppolTransmissionLog:
        """
        Retry a failed transmission.
        """
        # Get transmission log
        # Increment attempt_number
        # Re-transmit
        pass
    
    def get_adapter_for_org(self, org_id: str) -> APAdapterBase:
        """
        Get appropriate AP adapter for organization.
        """
        # Look up OrganisationPeppolSettings
        # Return StorecoveAdapter (or other adapters in future)
        pass
    
    def _should_retry(self, error_code: str, attempt_number: int, max_retries: int) -> bool:
        """Determine if transmission should be retried."""
        # Check error type and attempt count
        pass
```

**TDD Tests (4 tests)**:

| Test | Purpose | Expected Result |
|------|---------|-----------------|
| `test_transmit_invoice_success` | Full flow | TransmissionLog with DELIVERED status |
| `test_transmit_invoice_validation_fails` | Validation error | TransmissionLog with FAILED status, error logged |
| `test_transmit_invoice_not_configured` | Org not configured | Raises ValueError |
| `test_retry_transmission` | Retry logic | Incremented attempt_number, new status |

**Transmission Status Flow**:
```
PENDING → TRANSMITTING → DELIVERED (success)
                    ↘ FAILED (retryable error) → PENDING (retry)
                    ↘ REJECTED (permanent error)
```

**Retry Strategy**:
- Attempt 1: Immediate
- Attempt 2: After 60 seconds
- Attempt 3: After 300 seconds
- Max attempts: From OrganisationPeppolSettings.transmission_retry_attempts

**Error Categories**:
- **Retryable**: Network errors, rate limits, temporary AP failures
- **Permanent**: Authentication errors, validation failures, Peppol rejections

---

## Execution Checklist

### Pre-Execution Validation
- [ ] Verify `requests` library in requirements.txt
- [ ] Verify all Phase 2 tests pass (85/85)
- [ ] Verify PeppolTransmissionLog model is importable
- [ ] Verify OrganisationPeppolSettings model is importable
- [ ] Verify XML services are importable

### Task 3.1: AP Adapter Base (RED → GREEN → REFACTOR)

**RED Phase:**
- [ ] Create test file: `apps/backend/apps/peppol/tests/test_ap_adapter_base.py`
- [ ] Write 6 failing tests (see table above)
- [ ] Run tests, confirm all 6 fail

**GREEN Phase:**
- [ ] Create `apps/peppol/services/ap_adapter_base.py`
- [ ] Define `TransmissionStatus` enum
- [ ] Define `TransmissionResult` dataclass
- [ ] Define `APAdapterBase` abstract class
- [ ] Implement abstract methods
- [ ] Run tests, confirm all 6 pass

**REFACTOR Phase:**
- [ ] Add comprehensive docstrings
- [ ] Add type hints to all methods
- [ ] Review error handling patterns
- [ ] Document adapter interface

### Task 3.2: Storecove Adapter (RED → GREEN → REFACTOR)

**RED Phase:**
- [ ] Create test file: `apps/backend/apps/peppol/tests/test_ap_storecove.py`
- [ ] Write 8 failing tests (see table above)
- [ ] Mock HTTP responses using `responses` library or `unittest.mock`
- [ ] Run tests, confirm all 8 fail

**GREEN Phase:**
- [ ] Create `apps/peppol/services/ap_storecove_adapter.py`
- [ ] Inherit from `APAdapterBase`
- [ ] Implement `__init__`, `authenticate`, `send_invoice`, `check_status`, `validate_connection`
- [ ] Implement helper methods `_prepare_payload`, `_parse_response`
- [ ] Add error handling for HTTP status codes
- [ ] Run tests, confirm all 8 pass

**REFACTOR Phase:**
- [ ] Add comprehensive docstrings
- [ ] Add logging for API calls
- [ ] Review error message clarity
- [ ] Add timeout configuration
- [ ] Document Storecove API specifics

### Task 3.3: Transmission Service (RED → GREEN → REFACTOR)

**RED Phase:**
- [ ] Create test file: `apps/backend/apps/peppol/tests/test_transmission_service.py`
- [ ] Write 4 failing tests (see table above)
- [ ] Mock dependencies (XML services, AP adapter)
- [ ] Run tests, confirm all 4 fail

**GREEN Phase:**
- [ ] Create `apps/peppol/services/transmission_service.py`
- [ ] Implement `transmit_invoice` method
- [ ] Implement `queue_for_transmission` method
- [ ] Implement `retry_transmission` method
- [ ] Implement `get_adapter_for_org` method
- [ ] Add error handling and logging
- [ ] Run tests, confirm all 4 pass

**REFACTOR Phase:**
- [ ] Add comprehensive docstrings
- [ ] Review transaction boundaries
- [ ] Add metrics/logging hooks
- [ ] Document transmission workflow

---

## Verification Commands

### Dependencies Verification
```bash
cd apps/backend
source /opt/venv/bin/activate

# Verify requests library
python -c "import requests; print(f'requests version: {requests.__version__}')"

# If not installed:
# pip install requests responses
```

### Service Verification
```bash
# Import test
cd apps/backend
python -c "
from apps.peppol.services.ap_adapter_base import APAdapterBase, TransmissionResult, TransmissionStatus
from apps.peppol.services.ap_storecove_adapter import StorecoveAdapter
from apps.peppol.services.transmission_service import TransmissionService
print('✅ All Phase 3 services import successfully')
"
```

### Test Suite Verification
```bash
# Run all Phase 3 tests
cd apps/backend
pytest apps/peppol/tests/test_ap_adapter_base.py \
       apps/peppol/tests/test_ap_storecove.py \
       apps/peppol/tests/test_transmission_service.py \
       -v --reuse-db --no-migrations

# Expected: 18 tests passing
```

### Full Peppol Test Suite
```bash
# Run all Peppol tests (Phase 1, 2, 3)
cd apps/backend
pytest apps/peppol/tests/ -v --reuse-db --no-migrations

# Expected: 103 tests passing (85 Phase 1+2 + 18 Phase 3)
```

---

## Success Metrics

| Metric | Target | Verification |
|--------|--------|------------|
| AP Adapter Base | 6/6 tests passing | pytest reports |
| Storecove Adapter | 8/8 tests passing | pytest reports |
| Transmission Service | 4/4 tests passing | pytest reports |
| Total Coverage | 18/18 tests | pytest summary |
| HTTP Mocking | 100% | All external calls mocked |
| Error Handling | 100% | All error cases tested |
| No Regressions | Existing tests | Full test suite passes |

---

## Next Phase Readiness

**Phase 3 is complete when:**
- [ ] 18/18 Phase 3 tests passing
- [ ] Storecove adapter can authenticate (tested with mocks)
- [ ] Transmission service orchestrates workflow
- [ ] Retry logic handles failures correctly
- [ ] No regressions in existing 85 tests

**Phase 4 Prerequisites:**
- Phase 3 complete ✅
- Transmission service can be called with invoice_id
- Celery installed and configured
- API endpoints defined

---

## Risk Mitigation

### Risk 1: Storecove API Changes
**Mitigation**: Create adapter interface, easy to add other AP providers

### Risk 2: Network Failures in Tests
**Mitigation**: All HTTP calls mocked, no external dependencies in tests

### Risk 3: XML Payload Too Large
**Mitigation**: Add size validation before transmission (in service layer)

### Risk 4: Authentication Token Expiry
**Mitigation**: Storecove uses static API keys, no token refresh needed

---

## Documentation Requirements

### Code Documentation
- [ ] Docstrings for all classes and methods
- [ ] Type hints for all method signatures
- [ ] Inline comments for complex logic
- [ ] Error code documentation

### API Documentation
- [ ] Storecove API endpoints documented
- [ ] Request/response format examples
- [ ] Error response handling

---

## Sub-Plan Status: READY FOR REVIEW

**Next Step**: User review and validation before execution
**Confidence**: High (based on solid Phase 1-2 foundation)
**Estimated Duration**: 2-3 days (20 hours total)

---

## Post-Execution Checklist

After completing Phase 3:
- [ ] Update InvoiceNow_Implementation_Status_Report.md
- [ ] Verify all tests pass in CI
- [ ] Document any deviations from plan
- [ ] Prepare for Phase 4 (Celery integration)

---

**Sub-Plan Created**: 2026-03-09
**Validated Against**: Existing codebase, Phase 1-2 completion status
**Test Target**: 18 TDD tests (100% new code coverage)
