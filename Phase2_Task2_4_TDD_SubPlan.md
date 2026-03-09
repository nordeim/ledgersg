# Phase 2 Task 2.4: XML Validation Service
## TDD Implementation Sub-Plan

## Overview

**Task**: 2.4 of Phase 2  
**Duration**: 4-6 hours  
**Objective**: Create XML validation service against UBL 2.1 XSD and PINT-SG Schematron  
**TDD Approach**: RED → GREEN → REFACTOR  

---

## Success Criteria

- [ ] XML Validation Service validates against UBL 2.1 XSD
- [ ] XML Validation Service validates against PINT-SG Schematron
- [ ] Returns detailed error messages
- [ ] **12 TDD tests passing**
- [ ] No regressions in existing 22 Phase 2 tests

---

## Codebase Validation

### Current State (Verified)

**Dependencies Available**:
- ✅ lxml 6.0.2 installed (supports XSD validation)
- ✅ Schemas in `apps/peppol/schemas/`:
  - `ubl-Invoice.xsd` - UBL 2.1 Invoice schema
  - `ubl-CreditNote.xsd` - UBL 2.1 CreditNote schema
  - `PINT-UBL-validation.sch` - PINT-SG Schematron rules

**XML Generator Service** (Task 2.3 Complete):
- ✅ Can generate Invoice XML
- ✅ Can generate CreditNote XML
- ✅ XML hash calculation working
- ✅ 11/11 tests passing

**lxml Validation Support**:
- `etree.XMLSchema()` - XSD validation ✓
- `isoschematron.Schematron()` - Schematron validation ✓

---

## Task Breakdown

### Task 2.4.1: XML Validation Service
**Priority**: HIGH  
**Duration**: 4-6 hours  
**Dependencies**: Tasks 2.1, 2.2, 2.3 complete

#### Service Responsibilities

**File**: `apps/backend/apps/peppol/services/xml_validation_service.py`

**Core Functions**:
1. Load and cache XSD schemas
2. Load and cache Schematron rules
3. Validate Invoice XML against XSD
4. Validate Invoice XML against Schematron
5. Validate CreditNote XML
6. Return structured validation results

**Key Methods**:
```python
class XMLValidationService:
    def __init__(self):
        """Initialize with schema loading."""
        self._load_schemas()
    
    def _load_schemas(self):
        """Load XSD and Schematron schemas."""
        # Cache schemas for performance
        
    def validate_invoice_xml(self, xml_string: str) -> Dict[str, Any]:
        """
        Validate Invoice XML.
        Returns: {
            'is_valid': bool,
            'schema_errors': [],
            'schematron_errors': []
        }
        
    def validate_credit_note_xml(self, xml_string: str) -> Dict[str, Any]:
        """Validate CreditNote XML."""
        
    def _validate_xsd(self, xml_doc, schema) -> List[Dict]:
        """Validate against XSD schema."""
        
    def _validate_schematron(self, xml_doc) -> List[Dict]:
        """Validate against Schematron rules."""
```

**Validation Result Structure**:
```python
{
    'is_valid': True/False,
    'document_type': 'INVOICE'/'CREDIT_NOTE',
    'schema_errors': [
        {
            'message': 'Error description',
            'line': 15,
            'column': 10,
        }
    ],
    'schematron_errors': [
        {
            'level': 'ERROR'/'WARNING',
            'message': 'Rule violation',
            'rule': 'PEPPOL-EN16931-R004-SG',
        }
    ],
    'validation_time_ms': 45.2,
}
```

---

## TDD Test Plan (12 Tests)

### Test Structure
**File**: `apps/backend/apps/peppol/tests/test_xml_validation_service.py`

### Test Categories

#### Category A: Service Structure (3 tests)
| Test ID | Test Name | Purpose |
|---------|-----------|---------|
| VAL-001 | test_service_can_be_imported | Import validation |
| VAL-002 | test_service_has_validate_invoice_method | Method exists |
| VAL-003 | test_service_has_validate_credit_note_method | Method exists |

#### Category B: XSD Validation (4 tests)
| Test ID | Test Name | Purpose | Test Data |
|---------|-----------|---------|-----------|
| VAL-004 | test_validate_well_formed_invoice_xml | Valid XML | Generated Invoice XML |
| VAL-005 | test_validate_invoice_xml_invalid_structure | Invalid structure | Missing required elements |
| VAL-006 | test_validate_invoice_xml_missing_required | Missing elements | No ID, no IssueDate |
| VAL-007 | test_validate_credit_note_well_formed | Valid CreditNote | Generated CreditNote XML |

#### Category C: Schematron Validation (3 tests)
| Test ID | Test Name | Purpose | Expected |
|---------|-----------|---------|----------|
| VAL-008 | test_validate_pint_sg_customization_id | Customization ID | Must be PINT-SG |
| VAL-009 | test_validate_invoice_currency_code | Currency | Must be SGD |
| VAL-010 | test_validate_invoice_supplier_uen | Supplier UEN | Required field |

#### Category D: Error Handling (2 tests)
| Test ID | Test Name | Purpose | Test Case |
|---------|-----------|---------|-----------|
| VAL-011 | test_validate_invalid_xml_syntax | Malformed XML | Invalid XML string |
| VAL-012 | test_validate_empty_xml | Empty input | Empty string |

---

## Execution Checklist

### Pre-Execution Validation
- [ ] Verify lxml XMLSchema support
- [ ] Verify ubl-Invoice.xsd is valid XML
- [ ] Verify XMLGeneratorService generates valid XML
- [ ] Check isoschematron availability

### RED Phase
- [ ] Create test file: `test_xml_validation_service.py`
- [ ] Write 12 failing tests
- [ ] Run tests, confirm all 12 fail with ImportError

### GREEN Phase
- [ ] Create `xml_validation_service.py`
- [ ] Implement `__init__` with schema loading
- [ ] Implement `_load_schemas()` method
- [ ] Implement `validate_invoice_xml()` method
- [ ] Implement `validate_credit_note_xml()` method
- [ ] Implement `_validate_xsd()` helper
- [ ] Implement `_validate_schematron()` helper
- [ ] Run tests, fix until all 12 pass

### REFACTOR Phase
- [ ] Add schema caching for performance
- [ ] Optimize error message formatting
- [ ] Add comprehensive docstrings
- [ ] Add type hints throughout

---

## Validation Commands

### Service Import Test
```bash
cd apps/backend
python -c "
from apps.peppol.services.xml_validation_service import XMLValidationService
print('✅ Service imports successfully')
"
```

### Full Test Suite
```bash
cd apps/backend
pytest apps/peppol/tests/test_xml_validation_service.py -v

# Expected: 12 tests passing
```

### Integration Test
```bash
cd apps/backend
pytest apps/peppol/tests/ -v

# Expected: 34 tests passing (22 + 12)
```

---

## Success Metrics

| Metric | Target | Verification |
|--------|--------|------------|
| Validation Service Tests | 12/12 | pytest reports |
| Total Phase 2 Tests | 34/34 | pytest summary |
| XSD Validation | Working | Validate generated XML |
| Error Messages | Clear | Readable error dicts |
| No Regressions | Yes | All existing tests pass |

---

## Risk Assessment

### Risk 1: XSD Validation Complexity
**Issue**: UBL 2.1 XSD is complex and strict
**Mitigation**: Start with basic structure validation, add rules incrementally

### Risk 2: Schematron Not Loading
**Issue**: isoschematron may have dependencies
**Mitigation**: Test schema loading separately, handle gracefully

### Risk 3: XML Namespaces Causing Validation Failures
**Issue**: Namespace prefixes may confuse validator
**Mitigation**: Test with actual generated XML from Task 2.3

---

## Next Phase Readiness

**Phase 2 Complete when:**
- [ ] 34/34 tests passing
- [ ] XML generates and validates correctly
- [ ] No regressions in existing tests

**Phase 3 Prerequisites:**
- XML generation and validation working ✅
- Ready for Access Point Integration

---

**Sub-Plan Status**: READY FOR EXECUTION  
**Confidence**: High (validated against codebase)
