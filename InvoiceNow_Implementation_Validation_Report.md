# InvoiceNow/Peppol Implementation Validation Report

## Executive Summary

**Date**: 2026-03-08  
**Validator**: Claude Code Agent  
**Plan Under Review**: implementation_plan_InvoiceNow.md  

### Key Findings

The implementation plan is **comprehensive and well-researched**, but requires adjustments to align with the actual codebase. Several components mentioned in the plan are **already partially implemented**, while others need significant modifications.

---

## ✅ What's Already Implemented

### 1. Database Schema (SQL Layer)

**Status**: ✅ **COMPLETE**

The `peppol_transmission_log` table already exists in `database_schema.sql`:

```sql
CREATE TABLE gst.peppol_transmission_log (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  org_id UUID NOT NULL REFERENCES core.organisation(id) ON DELETE CASCADE,
  document_id UUID NOT NULL REFERENCES invoicing.document(id) ON DELETE CASCADE,
  attempt_number SMALLINT NOT NULL DEFAULT 1,
  status VARCHAR(20) NOT NULL CHECK (status IN ('PENDING', 'TRANSMITTING', 'DELIVERED', 'FAILED', 'REJECTED')),
  peppol_message_id UUID,
  access_point_id VARCHAR(100),
  request_hash VARCHAR(64), -- SHA-256 of XML payload
  response_code VARCHAR(20),
  error_code VARCHAR(50),
  error_message TEXT,
  transmitted_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  response_at TIMESTAMPTZ,
  CONSTRAINT chk_attempt_positive CHECK (attempt_number > 0)
);
```

**Location**: `apps/backend/database_schema.sql` lines 1161-1186

### 2. Django Models (Organisation)

**Status**: ✅ **PARTIALLY IMPLEMENTED**

The `Organisation` model already has Peppol-related fields:

```python
# InvoiceNow / Peppol
peppol_participant_id = models.CharField(max_length=64, blank=True)
peppol_scheme_id = models.CharField(max_length=10, default="0195", blank=True)
invoicenow_enabled = models.BooleanField(default=False)
invoicenow_ap_id = models.CharField(max_length=100, blank=True)
```

**Location**: `apps/backend/apps/core/models/organisation.py` lines 102-122

### 3. API Endpoints (Stub Implementation)

**Status**: ✅ **STUBS EXIST**

Two endpoints are already defined:

1. `GET /api/v1/{orgId}/peppol/transmission-log/` - Returns empty stub
2. `GET/PATCH /api/v1/{orgId}/peppol/settings/` - Basic CRUD for Organisation fields

**Location**: `apps/backend/apps/peppol/views.py`

---

## ⚠️ What's Missing / Needs Modification

### 1. Django Model for PeppolTransmissionLog

**Status**: ❌ **NOT IMPLEMENTED**

The SQL table exists, but there's no Django model mapping to it. Need to create:

- `apps/backend/apps/gst/models.py` entry for `PeppolTransmissionLog`
- Must include `managed = False` and `db_table = 'gst.peppol_transmission_log'`

### 2. OrganisationPeppolSettings Model

**Status**: ❌ **NOT IMPLEMENTED**

The plan proposes a separate settings model, but fields are currently on `Organisation`. Decision needed:

- **Option A**: Keep fields on Organisation (simpler, already implemented)
- **Option B**: Create separate model (more normalized, as per plan)

**Recommendation**: Option A for MVP, migrate to Option B later if needed.

### 3. Services Layer (Core Implementation)

**Status**: ❌ **NOT IMPLEMENTED**

Missing completely:

| Service | Plan Location | Status | Priority |
|---------|--------------|--------|----------|
| `XMLMappingService` | `apps/peppol/services/xml_mapping_service.py` | ❌ Missing | HIGH |
| `XMLGeneratorService` | `apps/peppol/services/xml_generator_service.py` | ❌ Missing | HIGH |
| `XMLValidationService` | `apps/peppol/services/xml_validation_service.py` | ❌ Missing | HIGH |
| `AccessPointAdapter` | `apps/peppol/services/ap_adapter_base.py` | ❌ Missing | HIGH |
| `TransmissionService` | (in plan) | ❌ Missing | MEDIUM |

### 4. XML Schema Files

**Status**: ❌ **NOT IMPLEMENTED**

Need to download and store:

- UBL 2.1 Invoice schema (`ubl-Invoice.xsd`)
- UBL 2.1 Credit Note schema (`ubl-CreditNote.xsd`)
- PINT-SG Schematron rules (`PINT-UBL-validation.sch`)

**Location**: `apps/backend/apps/peppol/schemas/`

### 5. Celery Tasks

**Status**: ❌ **NOT IMPLEMENTED**

Need async task for transmission:

```python
# apps/backend/apps/peppol/tasks.py
@shared_task
def transmit_peppol_invoice_task(transmission_log_id, xml_payload, api_url, api_key):
    pass
```

### 6. Integration with Invoice Approval

**Status**: ❌ **NOT IMPLEMENTED**

The plan shows integration in `DocumentService.approve_invoice()`, but currently:

- No XML generation on approval
- No transmission queuing
- No auto-transmit logic

**Location**: `apps/backend/apps/invoicing/services/document_service.py`

---

## 🔄 Required Modifications

### 1. Model Alignment

**Current State**: Organisation model has basic Peppol fields  
**Required**: Either expand Organisation model or create OrganisationPeppolSettings

**Recommended Approach** (Aligned with existing code):
```python
# Add to Organisation model (already has basic fields)
access_point_provider = models.CharField(max_length=100, blank=True)
access_point_api_url = models.URLField(blank=True)
access_point_api_key = models.CharField(max_length=255, blank=True)  # Should be encrypted
auto_transmit = models.BooleanField(default=False)
transmission_retry_attempts = models.IntegerField(default=3)
```

### 2. SQL Schema Additions

**Current State**: `peppol_transmission_log` has basic fields  
**Required**: Add fields mentioned in plan

```sql
ALTER TABLE gst.peppol_transmission_log 
ADD COLUMN IF NOT EXISTS xml_payload_hash VARCHAR(64),
ADD COLUMN IF NOT EXISTS access_point_provider VARCHAR(100),
ADD COLUMN IF NOT EXISTS mlr_status VARCHAR(50),
ADD COLUMN IF NOT EXISTS mlr_received_at TIMESTAMPTZ,
ADD COLUMN IF NOT EXISTS iras_submission_id VARCHAR(100);
```

### 3. Dependencies

**Required Packages** (not in current requirements):
```
lxml>=4.9.0  # For XML generation and validation
requests>=2.28.0  # For AP API calls
```

---

## 📊 Test Coverage Gap Analysis

| Test Category | Plan Count | Current | Gap |
|---------------|------------|---------|-----|
| XML Mapping | 15 | 0 | 15 |
| XML Generation | 20 | 0 | 20 |
| XML Validation | 12 | 0 | 12 |
| AP Integration | 15 | 0 | 15 |
| Transmission | 15 | 0 | 15 |
| End-to-End | 25 | 0 | 25 |
| **Total** | **92** | **0** | **92** |

**Current Test Files**:
- `apps/backend/apps/peppol/tests/test_views.py` - Tests stub endpoints (needs expansion)

---

## 🎯 Revised Implementation Priority

### Phase 1: Foundation (Days 1-3)
1. ✅ **Create Django model** for `PeppolTransmissionLog` (maps to existing SQL table)
2. ✅ **Add fields to Organisation model** (expand existing Peppol fields)
3. ✅ **Update SQL schema** with additional transmission log fields
4. ✅ **Add dependencies** to requirements.txt

### Phase 2: XML Generation (Days 4-8)
5. ✅ **Download XML schemas** (UBL 2.1, PINT-SG)
6. ✅ **Create XMLMappingService** (InvoiceDocument → dict)
7. ✅ **Create XMLGeneratorService** (dict → UBL XML)
8. ✅ **Create XMLValidationService** (validate against schema)

### Phase 3: Transmission (Days 9-12)
9. ✅ **Create AccessPointAdapter** (REST API integration)
10. ✅ **Create TransmissionService** (orchestration)
11. ✅ **Create Celery tasks** (async transmission)

### Phase 4: Integration (Days 13-15)
12. ✅ **Integrate with DocumentService** (auto-transmit on approval)
13. ✅ **Update API endpoints** (replace stubs with real implementation)
14. ✅ **Create status tracking** (webhook handlers)

### Phase 5: Testing (Days 16-20)
15. ✅ **Write 92 TDD tests** (following plan's test structure)
16. ✅ **End-to-end testing** with sandbox AP

---

## 🚨 Critical Blockers

### 1. Access Point Provider Selection
**Issue**: Plan mentions multiple AP providers (Storecove, Pagero, EDICOM) but no decision made.

**Impact**: Cannot implement AP adapter without knowing provider API structure.

**Recommendation**: 
- Start with Storecove (Singapore-based, IMDA-accredited)
- Create adapter interface that supports multiple providers

### 2. UEN Data Source
**Issue**: Organisation model has `uen` field, but need to validate:
- Is it populated during org creation?
- Format validation (e.g., "202312345A")?
- Required for Peppol transmission?

**Impact**: XML generation will fail if UEN missing.

### 3. Contact Model Peppol Fields
**Issue**: Plan references `contact.peppol_id` and `contact.uen` but these may not exist.

**Required**: Check Contact model for:
- `peppol_id` field
- `uen` field
- `is_gst_registered` flag
- `gst_reg_number` field

---

## 📝 Notes for Implementation

### 1. Model Location

The plan suggests putting `PeppolTransmissionLog` in `apps/gst/models.py`, but it's in `gst` schema. Current pattern:

- Models should be in their app, not gst app
- **Recommendation**: Create `apps/peppol/models.py` with:
```python
class PeppolTransmissionLog(TenantModel):
    class Meta:
        managed = False
        db_table = 'gst"."peppol_transmission_log'
        schema = 'gst'
```

### 2. UUID Handling

Remember the UUID double-conversion issue! Django URL converters already convert `<uuid:org_id>` to UUID objects. **Do NOT wrap in `UUID(org_id)`**.

### 3. SQL-First Compliance

Any new tables MUST be added to `database_schema.sql` FIRST, then create Django models with `managed = False`.

---

## ✅ Validation Checklist

### Pre-Implementation
- [ ] Verify Contact model has required Peppol fields
- [ ] Verify Organisation model has all needed fields
- [ ] Download UBL 2.1 and PINT-SG schemas
- [ ] Select Access Point provider
- [ ] Update requirements.txt with lxml and requests

### Implementation
- [ ] Create/update SQL schema
- [ ] Create PeppolTransmissionLog Django model
- [ ] Create services layer
- [ ] Create XML generation pipeline
- [ ] Create AP adapter
- [ ] Integrate with invoice approval
- [ ] Write 92 TDD tests

### Post-Implementation
- [ ] Test with sandbox AP
- [ ] Validate XML against PINT-SG rules
- [ ] End-to-end invoice transmission test
- [ ] Update API documentation

---

## 📚 Reference Documents

| Document | Purpose |
|----------|---------|
| `implementation_plan_InvoiceNow.md` | Original comprehensive plan |
| `database_schema.sql` lines 1161-1186 | Peppol transmission log table |
| `apps/core/models/organisation.py` lines 102-122 | Existing Peppol fields |
| `apps/peppol/views.py` | Stub API endpoints |
| PINT-SG Specification | Official Peppol Singapore profile |

---

**Report Generated**: 2026-03-08  
**Validation Status**: COMPLETE - Plan requires adjustments for codebase alignment  
**Next Action**: Create updated implementation plan based on findings
