# InvoiceNow/Peppol Implementation Plan (Updated)

## Executive Summary

**Based on**: Validation against actual LedgerSG codebase  
**Status**: Adjusted plan to align with existing implementation  
**Timeline**: 15-20 days (reduced from 25 due to existing foundation)  
**Tests**: 92 TDD tests (as per original plan)  

---

## Current State Summary

### ✅ Already Implemented
1. **Database**: `peppol_transmission_log` table exists
2. **Models**: Organisation has basic Peppol fields
3. **API**: Stub endpoints exist for transmission log and settings

### ❌ Not Implemented
1. **Services**: No XML generation, mapping, validation services
2. **Integration**: No connection between invoices and Peppol
3. **Transmission**: No actual AP integration
4. **Tests**: No TDD tests for Peppol functionality

---

## Implementation Phases

### Phase 1: Foundation (Days 1-3)

#### Task 1.1: Update SQL Schema
**File**: `apps/backend/database_schema.sql`

```sql
-- Add new fields to peppol_transmission_log
ALTER TABLE gst.peppol_transmission_log 
ADD COLUMN IF NOT EXISTS xml_payload_hash VARCHAR(64),
ADD COLUMN IF NOT EXISTS access_point_provider VARCHAR(100),
ADD COLUMN IF NOT EXISTS mlr_status VARCHAR(50),
ADD COLUMN IF NOT EXISTS mlr_received_at TIMESTAMPTZ,
ADD COLUMN IF NOT EXISTS iras_submission_id VARCHAR(100);

-- Add Organisation Peppol settings fields
ALTER TABLE core.organisation
ADD COLUMN IF NOT EXISTS access_point_provider VARCHAR(100),
ADD COLUMN IF NOT EXISTS access_point_api_url VARCHAR(500),
ADD COLUMN IF NOT EXISTS access_point_api_key VARCHAR(255),
ADD COLUMN IF NOT EXISTS access_point_client_id VARCHAR(100),
ADD COLUMN IF NOT EXISTS auto_transmit BOOLEAN DEFAULT FALSE,
ADD COLUMN IF NOT EXISTS transmission_retry_attempts INTEGER DEFAULT 3;
```

**Verification**:
```bash
psql -d ledgersg_dev -c "\d gst.peppol_transmission_log"
psql -d ledgersg_dev -c "\d core.organisation" | grep -i peppol
```

#### Task 1.2: Create Django Models
**File**: `apps/backend/apps/peppol/models.py` (NEW)

```python
"""Peppol models for InvoiceNow integration."""

from django.db import models
from common.models import TenantModel


class PeppolTransmissionLog(TenantModel):
    """
    Peppol transmission log entry.
    Maps to gst.peppol_transmission_log table.
    """
    
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('TRANSMITTING', 'Transmitting'),
        ('DELIVERED', 'Delivered'),
        ('FAILED', 'Failed'),
        ('REJECTED', 'Rejected'),
    ]
    
    # Document reference
    document = models.ForeignKey(
        'invoicing.InvoiceDocument',
        on_delete=models.CASCADE,
        db_column='document_id',
    )
    
    # Transmission status
    attempt_number = models.SmallIntegerField(default=1)
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='PENDING',
    )
    
    # Peppol identifiers
    peppol_message_id = models.UUIDField(null=True, blank=True)
    access_point_id = models.CharField(max_length=100, blank=True)
    
    # XML payload tracking
    request_hash = models.CharField(max_length=64, blank=True)
    xml_payload_hash = models.CharField(max_length=64, blank=True)
    
    # Response tracking
    response_code = models.CharField(max_length=20, blank=True)
    error_code = models.CharField(max_length=50, blank=True)
    error_message = models.TextField(blank=True)
    
    # Timestamps
    transmitted_at = models.DateTimeField(auto_now_add=True)
    response_at = models.DateTimeField(null=True, blank=True)
    
    # Access Point
    access_point_provider = models.CharField(max_length=100, blank=True)
    
    # Message Level Response
    mlr_status = models.CharField(max_length=50, blank=True)
    mlr_received_at = models.DateTimeField(null=True, blank=True)
    
    # IRAS tracking
    iras_submission_id = models.CharField(max_length=100, blank=True)
    
    class Meta:
        managed = False
        db_table = 'gst"."peppol_transmission_log'
        schema = 'gst'


class PeppolSettings(models.Model):
    """
    Peppol settings per organisation.
    Extends Organisation model for Peppol-specific config.
    """
    
    org = models.OneToOneField(
        'core.Organisation',
        on_delete=models.CASCADE,
        related_name='peppol_settings',
    )
    
    # AP Configuration
    access_point_provider = models.CharField(max_length=100, blank=True)
    access_point_api_url = models.URLField(blank=True)
    access_point_api_key = models.CharField(max_length=255, blank=True)
    access_point_client_id = models.CharField(max_length=100, blank=True)
    
    # Settings
    auto_transmit = models.BooleanField(default=False)
    transmission_retry_attempts = models.IntegerField(default=3)
    
    # Status
    is_active = models.BooleanField(default=True)
    configured_at = models.DateTimeField(auto_now_add=True)
    last_transmission_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        managed = False
        db_table = 'gst"."organisation_peppol_settings'
        schema = 'gst'
```

**Verification**:
```bash
cd apps/backend
python -c "from apps.peppol.models import PeppolTransmissionLog; print('OK')"
```

#### Task 1.3: Update Organisation Model
**File**: `apps/backend/apps/core/models/organisation.py`

Add after line 122:
```python
# Additional Peppol settings
access_point_provider = models.CharField(max_length=100, blank=True)
access_point_api_url = models.URLField(blank=True)
access_point_api_key = models.CharField(max_length=255, blank=True)
access_point_client_id = models.CharField(max_length=100, blank=True)
auto_transmit = models.BooleanField(default=False)
transmission_retry_attempts = models.IntegerField(default=3)
```

**Verification**:
```bash
grep -A 5 "invoicenow_ap_id" apps/core/models/organisation.py
```

---

### Phase 2: XML Services (Days 4-8)

#### Task 2.1: Download XML Schemas
**Directory**: `apps/backend/apps/peppol/schemas/`

```bash
mkdir -p apps/backend/apps/peppol/schemas

# Download UBL 2.1 schemas
curl -o apps/backend/apps/peppol/schemas/ubl-Invoice.xsd \
  https://docs.peppol.eu/poac/sg/pint-sg/trn-invoice/syntax/ubl-Invoice.xsd

curl -o apps/backend/apps/peppol/schemas/ubl-CreditNote.xsd \
  https://docs.peppol.eu/poac/sg/pint-sg/trn-creditnote/syntax/ubl-CreditNote.xsd

# Download PINT-SG schematron
curl -o apps/backend/apps/peppol/schemas/PINT-UBL-validation.sch \
  https://docs.peppol.eu/poac/sg/pint-sg/trn-invoice/rule/PINT-UBL-validation.sch
```

**Verification**:
```bash
ls -la apps/backend/apps/peppol/schemas/
```

#### Task 2.2: Create Services Directory
**Directory**: `apps/backend/apps/peppol/services/`

```bash
mkdir -p apps/backend/apps/peppol/services
touch apps/backend/apps/peppol/services/__init__.py
```

#### Task 2.3: Create XML Mapping Service
**File**: `apps/backend/apps/peppol/services/xml_mapping_service.py`

See original plan for full implementation. Key requirements:
- Map InvoiceDocument to UBL 2.1 structure
- Handle Singapore tax codes (SR, ZR, ES, OS)
- Include UEN and GST registration numbers
- Validate mandatory fields

**TDD Tests**: 15 tests (see original plan)

#### Task 2.4: Create XML Generator Service
**File**: `apps/backend/apps/peppol/services/xml_generator_service.py`

Key requirements:
- Generate UBL 2.1 XML from mapped data
- Use lxml for XML construction
- Include proper namespaces
- Support both Invoice and Credit Note

**TDD Tests**: 20 tests (see original plan)

#### Task 2.5: Create XML Validation Service
**File**: `apps/backend/apps/peppol/services/xml_validation_service.py`

Key requirements:
- Validate against UBL 2.1 XSD schema
- Validate against PINT-SG schematron rules
- Return detailed error messages

**TDD Tests**: 12 tests (see original plan)

---

### Phase 3: Access Point Integration (Days 9-12)

#### Task 3.1: Create AP Adapter Base
**File**: `apps/backend/apps/peppol/services/ap_adapter_base.py`

Abstract base class for AP providers.

#### Task 3.2: Create Storecove Adapter
**File**: `apps/backend/apps/peppol/services/ap_storecove_adapter.py`

Implementation for Storecove AP provider.

Key requirements:
- REST API integration
- Authentication with API key
- Send XML payload
- Handle response

**TDD Tests**: 12 tests (see original plan)

#### Task 3.3: Create Transmission Service
**File**: `apps/backend/apps/peppol/services/transmission_service.py`

Orchestrates the transmission workflow:
1. Generate XML
2. Validate XML
3. Send to AP
4. Track status
5. Handle retries

---

### Phase 4: Integration (Days 13-15)

#### Task 4.1: Create Celery Tasks
**File**: `apps/backend/apps/peppol/tasks.py` (NEW)

```python
from celery import shared_task
from apps.peppol.services.transmission_service import TransmissionService


@shared_task(bind=True, max_retries=3)
def transmit_peppol_invoice_task(self, transmission_log_id):
    """
    Async task to transmit invoice via Peppol.
    """
    try:
        service = TransmissionService()
        service.transmit(transmission_log_id)
    except Exception as exc:
        # Retry with exponential backoff
        raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))
```

#### Task 4.2: Integrate with Invoice Approval
**File**: `apps/backend/apps/invoicing/services/document_service.py`

Add to `approve_invoice` method:

```python
def approve_invoice(self, org_id, invoice_id, user):
    """Approve invoice with Peppol integration."""
    
    # Existing approval logic...
    
    # Check if Peppol auto-transmit is enabled
    org = Organisation.objects.get(id=org_id)
    if org.invoicenow_enabled and org.auto_transmit:
        from apps.peppol.services.transmission_service import TransmissionService
        service = TransmissionService()
        service.queue_for_transmission(invoice_id, org_id)
    
    return invoice
```

#### Task 4.3: Update API Endpoints
**File**: `apps/backend/apps/peppol/views.py`

Replace stub implementations with real logic.

---

### Phase 5: Testing (Days 16-20)

#### Task 5.1: Write TDD Tests
**Files**:
- `apps/backend/apps/peppol/tests/test_xml_mapping_service.py` (15 tests)
- `apps/backend/apps/peppol/tests/test_xml_generator_service.py` (20 tests)
- `apps/backend/apps/peppol/tests/test_xml_validation_service.py` (12 tests)
- `apps/backend/apps/peppol/tests/test_ap_adapter.py` (12 tests)
- `apps/backend/apps/peppol/tests/test_transmission_service.py` (15 tests)
- `apps/backend/apps/peppol/tests/test_integration.py` (16 tests)

**Total**: 92 tests

#### Task 5.2: Run Full Test Suite

```bash
cd apps/backend
pytest apps/peppol/tests/ -v --reuse-db --no-migrations
```

---

## Testing Strategy

### Test Categories

| Category | Count | File |
|----------|-------|------|
| Unit Tests (XML Mapping) | 15 | `test_xml_mapping_service.py` |
| Unit Tests (XML Generation) | 20 | `test_xml_generator_service.py` |
| Unit Tests (XML Validation) | 12 | `test_xml_validation_service.py` |
| Unit Tests (AP Adapter) | 12 | `test_ap_adapter.py` |
| Unit Tests (Transmission) | 15 | `test_transmission_service.py` |
| Integration Tests | 18 | `test_integration.py` |
| **Total** | **92** | |

### Key Test Scenarios

1. **Tax Code Mapping**: SR → 'S', ZR → 'Z', ES → 'E', OS → 'O'
2. **Mandatory Fields**: UEN, document number, issue date
3. **GST Registration**: Required for GST-registered suppliers
4. **Credit Notes**: Same UBL format with CreditNote root
5. **Validation**: Schema and schematron rules
6. **Transmission**: Retry logic, status tracking

---

## Risk Mitigation

### Risk 1: AP Provider API Changes
**Mitigation**: Create adapter interface, support multiple providers

### Risk 2: XML Validation Failures
**Mitigation**: Comprehensive validation service with detailed error reporting

### Risk 3: UEN Missing
**Mitigation**: Validation before XML generation, clear error messages

### Risk 4: Contact Data Incomplete
**Mitigation**: Check Contact model for required fields

---

## Success Criteria

- [ ] 92/92 TDD tests passing
- [ ] XML validates against UBL 2.1 schema
- [ ] XML validates against PINT-SG schematron
- [ ] Transmission to AP successful
- [ ] Status tracking working
- [ ] Auto-transmit on invoice approval working
- [ ] API endpoints return real data (not stubs)

---

## Next Actions

1. **Immediate** (Day 1): Update SQL schema, create models
2. **Short-term** (Days 2-8): Implement XML services
3. **Medium-term** (Days 9-15): AP integration and invoice approval
4. **Final** (Days 16-20): Testing and validation

---

**Plan Updated**: 2026-03-08  
**Status**: Ready for implementation  
**Confidence**: High (based on codebase validation)
