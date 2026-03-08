# Phase 1: Foundation — TDD Implementation Sub-Plan

## Overview

**Phase**: 1 of 5  
**Duration**: Days 1-3  
**Objective**: Establish database and model foundation for InvoiceNow/Peppol integration  
**TDD Approach**: RED → GREEN → REFACTOR for each component  

---

## Success Criteria

- [ ] All database schema changes applied successfully
- [ ] Django models created with `managed = False`
- [ ] Organisation model extended with Peppol fields
- [ ] **12 TDD tests passing** (100% coverage)
- [ ] No regressions in existing tests

---

## Task Breakdown

### Task 1.1: Update SQL Schema
**Priority**: HIGH  
**Duration**: 2 hours  
**Dependencies**: None

#### 1.1.1 Add Fields to peppol_transmission_log

**File**: `apps/backend/database_schema.sql`

**Location**: After line 1186 (after peppol_transmission_log indexes)

```sql
-- ============================================
-- PEPPOL TRANSMISSION LOG EXTENSIONS
-- For InvoiceNow Phase 1 Implementation
-- ============================================

-- Add new fields for enhanced tracking
ALTER TABLE gst.peppol_transmission_log 
ADD COLUMN IF NOT EXISTS xml_payload_hash VARCHAR(64),
ADD COLUMN IF NOT EXISTS access_point_provider VARCHAR(100),
ADD COLUMN IF NOT EXISTS mlr_status VARCHAR(50),
ADD COLUMN IF NOT EXISTS mlr_received_at TIMESTAMPTZ,
ADD COLUMN IF NOT EXISTS iras_submission_id VARCHAR(100);

COMMENT ON COLUMN gst.peppol_transmission_log.xml_payload_hash IS 'SHA-256 hash of complete XML payload for audit trail';
COMMENT ON COLUMN gst.peppol_transmission_log.access_point_provider IS 'IMDA-accredited AP provider name (e.g., Storecove)';
COMMENT ON COLUMN gst.peppol_transmission_log.mlr_status IS 'Message Level Response status from AP';
COMMENT ON COLUMN gst.peppol_transmission_log.mlr_received_at IS 'Timestamp when MLR received from AP';
COMMENT ON COLUMN gst.peppol_transmission_log.iras_submission_id IS 'IRAS submission reference for 5th corner reporting';
```

#### 1.1.2 Add Peppol Settings Table

**Location**: After peppol_transmission_log table definition

```sql
-- ============================================
-- ORGANISATION PEPPOL SETTINGS
-- ============================================

CREATE TABLE IF NOT EXISTS gst.organisation_peppol_settings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id UUID NOT NULL REFERENCES core.organisation(id) ON DELETE CASCADE,
    
    -- Access Point Configuration
    access_point_provider VARCHAR(100) NOT NULL DEFAULT '',
    access_point_api_url VARCHAR(500),
    access_point_api_key VARCHAR(255), -- Encrypted
    access_point_client_id VARCHAR(100),
    
    -- Transmission Settings
    auto_transmit BOOLEAN NOT NULL DEFAULT FALSE,
    transmission_retry_attempts SMALLINT NOT NULL DEFAULT 3,
    
    -- Status
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    configured_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_transmission_at TIMESTAMPTZ,
    
    -- Constraints
    CONSTRAINT chk_retry_positive CHECK (transmission_retry_attempts > 0),
    CONSTRAINT chk_one_settings_per_org UNIQUE (org_id)
);

COMMENT ON TABLE gst.organisation_peppol_settings IS 'Peppol/InvoiceNow configuration per organisation. One row per org.';

-- Performance indexes
CREATE INDEX IF NOT EXISTS idx_peppol_settings_org 
ON gst.organisation_peppol_settings(org_id) 
WHERE is_active = TRUE;
```

#### 1.1.3 Add Fields to Organisation Table

**Location**: After existing peppol fields in core.organisation

```sql
-- ============================================
-- ORGANISATION PEPPOL FIELD EXTENSIONS
-- ============================================

ALTER TABLE core.organisation
ADD COLUMN IF NOT EXISTS access_point_provider VARCHAR(100) DEFAULT '',
ADD COLUMN IF NOT EXISTS access_point_api_url VARCHAR(500),
ADD COLUMN IF NOT EXISTS access_point_api_key VARCHAR(255),
ADD COLUMN IF NOT EXISTS access_point_client_id VARCHAR(100),
ADD COLUMN IF NOT EXISTS auto_transmit BOOLEAN DEFAULT FALSE,
ADD COLUMN IF NOT EXISTS transmission_retry_attempts SMALLINT DEFAULT 3;

COMMENT ON COLUMN core.organisation.access_point_provider IS 'IMDA-accredited Access Point provider';
COMMENT ON COLUMN core.organisation.access_point_api_url IS 'AP provider API endpoint URL';
COMMENT ON COLUMN core.organisation.access_point_api_key IS 'AP provider API key (should be encrypted at application level)';
```

**Verification Command**:
```bash
export PGPASSWORD=ledgersg_secret_to_change
cd /home/project/Ledger-SG/apps/backend
psql -h localhost -U ledgersg -d ledgersg_dev -f database_schema.sql 2>&1 | tail -20
```

**Expected Output**:
```
ALTER TABLE
ALTER TABLE
CREATE TABLE
CREATE INDEX
ALTER TABLE
ALTER TABLE
```

---

### Task 1.2: Create Django Models
**Priority**: HIGH  
**Duration**: 3 hours  
**Dependencies**: Task 1.1 complete

#### 1.2.1 Create Peppol Models File

**File**: `apps/backend/apps/peppol/models.py` (NEW)

```python
"""
Peppol models for InvoiceNow integration.

Maps to gst schema tables for Peppol transmission tracking.
SQL-First Architecture: managed = False
"""

from django.db import models
from common.models import TenantModel


class PeppolTransmissionLog(TenantModel):
    """
    Peppol transmission log entry.
    
    Immutable log of InvoiceNow/Peppol transmission attempts.
    Each row = one attempt. Enables retry tracking and audit trail.
    
    Maps to: gst.peppol_transmission_log
    """
    
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('TRANSMITTING', 'Transmitting'),
        ('DELIVERED', 'Delivered'),
        ('FAILED', 'Failed'),
        ('REJECTED', 'Rejected'),
    ]
    
    # Document reference (foreign key to invoicing.document)
    document_id = models.UUIDField(
        db_column='document_id',
        help_text='Reference to InvoiceDocument',
    )
    
    # Transmission status
    attempt_number = models.SmallIntegerField(
        db_column='attempt_number',
        default=1,
        help_text='Attempt number for retry tracking',
    )
    status = models.CharField(
        db_column='status',
        max_length=20,
        choices=STATUS_CHOICES,
        default='PENDING',
        help_text='Current transmission status',
    )
    
    # Peppol identifiers
    peppol_message_id = models.UUIDField(
        db_column='peppol_message_id',
        null=True,
        blank=True,
        help_text='Peppol message ID from AP',
    )
    access_point_id = models.CharField(
        db_column='access_point_id',
        max_length=100,
        blank=True,
        help_text='Access Point identifier',
    )
    
    # XML payload tracking
    request_hash = models.CharField(
        db_column='request_hash',
        max_length=64,
        blank=True,
        help_text='SHA-256 hash of XML request',
    )
    xml_payload_hash = models.CharField(
        db_column='xml_payload_hash',
        max_length=64,
        blank=True,
        help_text='SHA-256 hash of complete XML payload',
    )
    
    # Response tracking
    response_code = models.CharField(
        db_column='response_code',
        max_length=20,
        blank=True,
        help_text='HTTP response code from AP',
    )
    error_code = models.CharField(
        db_column='error_code',
        max_length=50,
        blank=True,
        help_text='Error code from AP or validation',
    )
    error_message = models.TextField(
        db_column='error_message',
        blank=True,
        help_text='Detailed error message',
    )
    
    # Timestamps
    transmitted_at = models.DateTimeField(
        db_column='transmitted_at',
        auto_now_add=True,
        help_text='When transmission was initiated',
    )
    response_at = models.DateTimeField(
        db_column='response_at',
        null=True,
        blank=True,
        help_text='When response received from AP',
    )
    
    # Access Point
    access_point_provider = models.CharField(
        db_column='access_point_provider',
        max_length=100,
        blank=True,
        help_text='IMDA-accredited AP provider name',
    )
    
    # Message Level Response (MLR) Tracking
    mlr_status = models.CharField(
        db_column='mlr_status',
        max_length=50,
        blank=True,
        help_text='MLR status from recipient AP',
    )
    mlr_received_at = models.DateTimeField(
        db_column='mlr_received_at',
        null=True,
        blank=True,
        help_text='When MLR received',
    )
    
    # IRAS 5th Corner Tracking
    iras_submission_id = models.CharField(
        db_column='iras_submission_id',
        max_length=100,
        blank=True,
        help_text='IRAS submission reference ID',
    )
    
    class Meta:
        managed = False
        db_table = 'gst"."peppol_transmission_log'
        schema = 'gst'
        verbose_name = 'Peppol Transmission Log'
        verbose_name_plural = 'Peppol Transmission Logs'
    
    def __str__(self) -> str:
        return f"Transmission {self.id} - {self.status}"


class OrganisationPeppolSettings(TenantModel):
    """
    Peppol/InvoiceNow configuration per organisation.
    
    One-to-one relationship with Organisation.
    Extends Organisation with Peppol-specific configuration.
    
    Maps to: gst.organisation_peppol_settings
    """
    
    # Organisation reference (one-to-one)
    org_id = models.UUIDField(
        db_column='org_id',
        unique=True,
        help_text='Reference to Organisation',
    )
    
    # Access Point Configuration
    access_point_provider = models.CharField(
        db_column='access_point_provider',
        max_length=100,
        default='',
        help_text='IMDA-accredited AP provider (e.g., Storecove)',
    )
    access_point_api_url = models.URLField(
        db_column='access_point_api_url',
        blank=True,
        null=True,
        help_text='AP provider API endpoint',
    )
    access_point_api_key = models.CharField(
        db_column='access_point_api_key',
        max_length=255,
        blank=True,
        help_text='AP provider API key (encrypted at app level)',
    )
    access_point_client_id = models.CharField(
        db_column='access_point_client_id',
        max_length=100,
        blank=True,
        help_text='AP provider client ID',
    )
    
    # Transmission Settings
    auto_transmit = models.BooleanField(
        db_column='auto_transmit',
        default=False,
        help_text='Auto-transmit invoices on approval',
    )
    transmission_retry_attempts = models.SmallIntegerField(
        db_column='transmission_retry_attempts',
        default=3,
        help_text='Number of retry attempts on failure',
    )
    
    # Status
    is_active = models.BooleanField(
        db_column='is_active',
        default=True,
        help_text='Whether Peppol integration is active',
    )
    configured_at = models.DateTimeField(
        db_column='configured_at',
        auto_now_add=True,
        help_text='When settings were configured',
    )
    last_transmission_at = models.DateTimeField(
        db_column='last_transmission_at',
        null=True,
        blank=True,
        help_text='Last successful transmission timestamp',
    )
    
    class Meta:
        managed = False
        db_table = 'gst"."organisation_peppol_settings'
        schema = 'gst'
        verbose_name = 'Organisation Peppol Settings'
        verbose_name_plural = 'Organisation Peppol Settings'
    
    def __str__(self) -> str:
        return f"Peppol Settings for Org {self.org_id}"
    
    @property
    def is_configured(self) -> bool:
        """Check if Peppol is fully configured."""
        return (
            self.is_active and
            self.access_point_provider and
            self.access_point_api_url and
            self.access_point_api_key
        )
```

**Verification Command**:
```bash
cd /home/project/Ledger-SG/apps/backend
source /opt/venv/bin/activate
python -c "from apps.peppol.models import PeppolTransmissionLog, OrganisationPeppolSettings; print('✅ Models loaded successfully')"
```

**Expected Output**:
```
✅ Models loaded successfully
```

---

### Task 1.3: Update Organisation Model
**Priority**: HIGH  
**Duration**: 1 hour  
**Dependencies**: Task 1.1 complete

#### 1.3.1 Add Peppol Fields to Organisation

**File**: `apps/backend/apps/core/models/organisation.py`

**Location**: After line 122 (after `invoicenow_ap_id`)

```python
# Additional Peppol configuration fields
access_point_provider = models.CharField(
    max_length=100,
    blank=True,
    db_column="access_point_provider",
    help_text="IMDA-accredited Access Point provider",
)
access_point_api_url = models.URLField(
    blank=True,
    null=True,
    db_column="access_point_api_url",
    help_text="AP provider API endpoint URL",
)
access_point_api_key = models.CharField(
    max_length=255,
    blank=True,
    db_column="access_point_api_key",
    help_text="AP provider API key (should be encrypted at application level)",
)
access_point_client_id = models.CharField(
    max_length=100,
    blank=True,
    db_column="access_point_client_id",
    help_text="AP provider client ID",
)
auto_transmit = models.BooleanField(
    default=False,
    db_column="auto_transmit",
    help_text="Auto-transmit invoices on approval",
)
transmission_retry_attempts = models.IntegerField(
    default=3,
    db_column="transmission_retry_attempts",
    help_text="Number of retry attempts on transmission failure",
)
```

**Verification Command**:
```bash
grep -A 2 "access_point_provider" apps/core/models/organisation.py
```

**Expected Output**:
```python
access_point_provider = models.CharField(
    max_length=100,
```

---

## TDD Test Plan

### Test Suite Structure

**Total Tests**: 12  
**Test Files**: 3  
**Coverage**: 100% of Phase 1 components

---

### Test File 1: Database Schema Tests
**File**: `apps/backend/tests/peppol/test_phase1_schema.py`

```python
"""
TDD Tests for Phase 1: Database Schema
Tests SQL schema changes for InvoiceNow foundation.
"""

import pytest
from django.db import connection


@pytest.mark.django_db
def test_peppol_transmission_log_has_xml_payload_hash():
    """Test that xml_payload_hash column exists in peppol_transmission_log."""
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_schema = 'gst' 
            AND table_name = 'peppol_transmission_log' 
            AND column_name = 'xml_payload_hash'
        """)
        result = cursor.fetchone()
        assert result is not None


@pytest.mark.django_db
def test_peppol_transmission_log_has_access_point_provider():
    """Test that access_point_provider column exists."""
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_schema = 'gst' 
            AND table_name = 'peppol_transmission_log' 
            AND column_name = 'access_point_provider'
        """)
        result = cursor.fetchone()
        assert result is not None


@pytest.mark.django_db
def test_peppol_transmission_log_has_mlr_fields():
    """Test that MLR tracking columns exist."""
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_schema = 'gst' 
            AND table_name = 'peppol_transmission_log' 
            AND column_name IN ('mlr_status', 'mlr_received_at')
        """)
        results = cursor.fetchall()
        assert len(results) == 2


@pytest.mark.django_db
def test_peppol_transmission_log_has_iras_submission_id():
    """Test that iras_submission_id column exists for 5th corner."""
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_schema = 'gst' 
            AND table_name = 'peppol_transmission_log' 
            AND column_name = 'iras_submission_id'
        """)
        result = cursor.fetchone()
        assert result is not None


@pytest.mark.django_db
def test_organisation_peppol_settings_table_exists():
    """Test that organisation_peppol_settings table was created."""
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = 'gst' 
                AND table_name = 'organisation_peppol_settings'
            )
        """)
        result = cursor.fetchone()
        assert result[0] is True


@pytest.mark.django_db
def test_organisation_has_access_point_fields():
    """Test that Organisation has new Peppol fields."""
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_schema = 'core' 
            AND table_name = 'organisation' 
            AND column_name IN (
                'access_point_provider', 
                'access_point_api_url',
                'access_point_api_key',
                'access_point_client_id',
                'auto_transmit',
                'transmission_retry_attempts'
            )
        """)
        results = cursor.fetchall()
        assert len(results) == 6
```

---

### Test File 2: Django Model Tests
**File**: `apps/backend/apps/peppol/tests/test_models.py`

```python
"""
TDD Tests for Peppol Django Models
Phase 1: Foundation
"""

import pytest
from uuid import uuid4
from datetime import datetime

from apps.peppol.models import PeppolTransmissionLog, OrganisationPeppolSettings


@pytest.mark.django_db
def test_peppol_transmission_log_model_exists():
    """Test that PeppolTransmissionLog model can be imported."""
    assert PeppolTransmissionLog is not None


@pytest.mark.django_db
def test_peppol_transmission_log_is_unmanaged():
    """Test that model is unmanaged (SQL-First architecture)."""
    assert PeppolTransmissionLog._meta.managed is False


@pytest.mark.django_db
def test_peppol_transmission_log_table_name():
    """Test correct database table mapping."""
    assert PeppolTransmissionLog._meta.db_table == 'gst"."peppol_transmission_log'


@pytest.mark.django_db
def test_peppol_transmission_log_schema():
    """Test correct schema assignment."""
    assert PeppolTransmissionLog._meta.schema == 'gst'


@pytest.mark.django_db
def test_organisation_peppol_settings_model_exists():
    """Test that OrganisationPeppolSettings model can be imported."""
    assert OrganisationPeppolSettings is not None


@pytest.mark.django_db
def test_organisation_peppol_settings_is_unmanaged():
    """Test that settings model is unmanaged."""
    assert OrganisationPeppolSettings._meta.managed is False


@pytest.mark.django_db
def test_organisation_peppol_settings_has_is_configured_property():
    """Test that is_configured property exists."""
    settings = OrganisationPeppolSettings()
    assert hasattr(settings, 'is_configured')
    assert settings.is_configured is False  # Not configured by default


@pytest.mark.django_db
def test_organisation_peppol_settings_is_configured_when_active(
    test_organisation, test_org
):
    """Test is_configured returns True when properly configured."""
    settings = OrganisationPeppolSettings(
        org_id=test_organisation.id,
        access_point_provider='Storecove',
        access_point_api_url='https://api.storecove.com',
        access_point_api_key='test-key',
        is_active=True,
    )
    assert settings.is_configured is True
```

---

### Test File 3: Organisation Model Tests
**File**: `apps/backend/apps/core/tests/test_organisation_peppol.py`

```python
"""
TDD Tests for Organisation Peppol Fields
Phase 1: Foundation
"""

import pytest
from apps.core.models import Organisation


@pytest.mark.django_db
def test_organisation_has_access_point_provider_field(test_organisation):
    """Test Organisation has access_point_provider field."""
    assert hasattr(test_organisation, 'access_point_provider')


@pytest.mark.django_db
def test_organisation_has_access_point_api_url_field(test_organisation):
    """Test Organisation has access_point_api_url field."""
    assert hasattr(test_organisation, 'access_point_api_url')


@pytest.mark.django_db
def test_organisation_has_auto_transmit_field(test_organisation):
    """Test Organisation has auto_transmit field."""
    assert hasattr(test_organisation, 'auto_transmit')
    assert test_organisation.auto_transmit is False  # Default value


@pytest.mark.django_db
def test_organisation_has_transmission_retry_attempts_field(test_organisation):
    """Test Organisation has transmission_retry_attempts field."""
    assert hasattr(test_organisation, 'transmission_retry_attempts')
    assert test_organisation.transmission_retry_attempts == 3  # Default
```

---

## Execution Checklist

### Pre-Execution Validation
- [ ] Back up current database schema
- [ ] Verify no pending migrations in other modules
- [ ] Check for existing peppol models (should be none)
- [ ] Confirm PostgreSQL version >= 16

### Task 1.1: SQL Schema (RED → GREEN → REFACTOR)

**RED Phase**:
- [ ] Run schema validation test (should fail initially)
  ```bash
  pytest tests/peppol/test_phase1_schema.py -v
  ```
- [ ] Confirm tests fail with "column does not exist"

**GREEN Phase**:
- [ ] Apply SQL schema changes
  ```bash
  export PGPASSWORD=ledgersg_secret_to_change
  psql -h localhost -U ledgersg -d ledgersg_dev -f database_schema.sql
  ```
- [ ] Verify schema changes applied
- [ ] Re-run tests (should pass)

**REFACTOR Phase**:
- [ ] Add comments to new columns
- [ ] Verify indexes created
- [ ] Document schema changes

### Task 1.2: Django Models (RED → GREEN → REFACTOR)

**RED Phase**:
- [ ] Run model tests (should fail - models don't exist)
  ```bash
  pytest apps/peppol/tests/test_models.py -v
  ```

**GREEN Phase**:
- [ ] Create `apps/peppol/models.py`
- [ ] Define `PeppolTransmissionLog` model
- [ ] Define `OrganisationPeppolSettings` model
- [ ] Re-run tests (should pass)

**REFACTOR Phase**:
- [ ] Add model docstrings
- [ ] Add help_text to all fields
- [ ] Verify `managed = False` on both models
- [ ] Check schema alignment

### Task 1.3: Organisation Model (RED → GREEN → REFACTOR)

**RED Phase**:
- [ ] Run Organisation model tests
  ```bash
  pytest apps/core/tests/test_organisation_peppol.py -v
  ```

**GREEN Phase**:
- [ ] Add new fields to Organisation model
- [ ] Re-run tests (should pass)

**REFACTOR Phase**:
- [ ] Add help_text to new fields
- [ ] Verify db_column names
- [ ] Check default values

---

## Verification Commands

### Schema Verification
```bash
# Verify peppol_transmission_log columns
psql -h localhost -U ledgersg -d ledgersg_dev -c "
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_schema = 'gst'
AND table_name = 'peppol_transmission_log'
ORDER BY ordinal_position;
"

# Verify organisation_peppol_settings exists
psql -h localhost -U ledgersg -d ledgersg_dev -c "
SELECT EXISTS (
    SELECT FROM information_schema.tables
    WHERE table_schema = 'gst'
    AND table_name = 'organisation_peppol_settings'
);
"

# Verify Organisation columns
psql -h localhost -U ledgersg -d ledgersg_dev -c "
SELECT column_name, data_type
FROM information_schema.columns
WHERE table_schema = 'core'
AND table_name = 'organisation'
AND column_name LIKE '%peppol%'
OR column_name LIKE '%access_point%'
OR column_name LIKE '%transmit%';
"
```

### Model Verification
```bash
# Import test
cd /home/project/Ledger-SG/apps/backend
source /opt/venv/bin/activate
python -c "
from apps.peppol.models import PeppolTransmissionLog, OrganisationPeppolSettings
from apps.core.models import Organisation

# Test model attributes
assert PeppolTransmissionLog._meta.managed is False
assert OrganisationPeppolSettings._meta.managed is False
assert hasattr(Organisation, 'access_point_provider')

print('✅ All Phase 1 models validated successfully!')
"
```

### Test Suite Verification
```bash
# Run all Phase 1 tests
cd /home/project/Ledger-SG/apps/backend
pytest tests/peppol/test_phase1_schema.py apps/peppol/tests/test_models.py apps/core/tests/test_organisation_peppol.py -v

# Expected: 12 tests passing
```

---

## Success Metrics

| Metric | Target | Verification |
|--------|--------|--------------|
| SQL Schema Changes | 100% Applied | Schema tests pass |
| Django Models | 2 Models Created | Import tests pass |
| Organisation Fields | 6 Fields Added | Model tests pass |
| Test Coverage | 12/12 Tests | pytest reports 12 passed |
| No Regressions | Existing tests | Full test suite passes |

---

## Next Phase Readiness

**Phase 1 is complete when:**
- [ ] 12/12 Phase 1 tests passing
- [ ] No regressions in existing 651 tests
- [ ] SQL schema changes documented
- [ ] Models reviewed and approved

**Phase 2 Prerequisites:**
- Phase 1 complete ✅
- XML schemas downloaded
- Services directory created
- TDD tests for Phase 2 defined

---

**Sub-Plan Status**: READY FOR REVIEW  
**Next Step**: User review and validation before execution
