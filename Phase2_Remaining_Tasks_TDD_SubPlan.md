# Phase 2 Remaining Tasks: XML Generator & Validation Services
## TDD Implementation Sub-Plan

## Overview

**Phase**: 2 of 5 (Tasks 2.3 & 2.4)  
**Duration**: Days 6-8  
**Objective**: Complete XML generation and validation services  
**TDD Approach**: RED → GREEN → REFACTOR for each component  

---

## Success Criteria

- [ ] XML Generator Service creates valid UBL 2.1 XML
- [ ] XML Validation Service validates against schemas
- [ ] **32 TDD tests passing** (20 generation + 12 validation)
- [ ] XML hash calculation working
- [ ] Proper namespaces and encoding
- [ ] No regressions in existing tests

---

## Codebase Validation

### Current State (Verified)

**Phase 2.1 & 2.2 Complete**:
- ✅ Schemas downloaded (UBL Invoice, CreditNote, PINT-SG Schematron)
- ✅ XML Mapping Service implemented
- ✅ 11 tests passing

**Existing Dependencies**:
- `lxml` 6.0.2 installed ✓
- Schemas in `apps/peppol/schemas/` ✓
- Mapping service in `apps/peppol/services/` ✓

**Model Relationships**:
- InvoiceDocument → InvoiceLine (via `lines` related_name) ✓
- InvoiceDocument → Contact (via `contact` FK) ✓
- InvoiceLine → TaxCode (via `tax_code` FK) ✓
- All required fields validated ✓

---

## Task Breakdown

### Task 2.3: XML Generator Service
**Priority**: HIGH  
**Duration**: 2 days  
**Dependencies**: Task 2.1, 2.2 complete  

#### 2.3.1 Service Responsibilities

**File**: `apps/backend/apps/peppol/services/xml_generator_service.py`

**Core Functions**:
1. Generate UBL 2.1 Invoice XML from mapped dict
2. Generate UBL 2.1 CreditNote XML from mapped dict
3. Calculate SHA-256 hash of XML payload
4. Pretty-print XML with proper indentation

**Key Methods**:
```python
class XMLGeneratorService:
    NAMESPACE_UBL = 'urn:oasis:names:specification:ubl:schema:xsd:Invoice-2'
    NAMESPACE_CAC = 'urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2'
    NAMESPACE_CBC = 'urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2'
    
    def generate_invoice_xml(self, mapped_data: Dict[str, Any]) -> str:
        """Generate UBL 2.1 Invoice XML."""
        
    def generate_credit_note_xml(self, mapped_data: Dict[str, Any]) -> str:
        """Generate UBL 2.1 CreditNote XML."""
        
    def calculate_xml_hash(self, xml_string: str) -> str:
        """Calculate SHA-256 hash of XML."""
        
    def _add_element(self, parent, tag_name, value, namespace='cbc'):
        """Helper for adding namespaced elements."""
```

**XML Structure Requirements**:
```xml
<?xml version="1.0" encoding="UTF-8"?>
<Invoice xmlns="urn:oasis:names:specification:ubl:schema:xsd:Invoice-2"
         xmlns:cac="urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2"
         xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2">
    <cbc:UBLVersionID>2.1</cbc:UBLVersionID>
    <cbc:CustomizationID>urn:peppol:pint:billing-1@sg-1</cbc:CustomizationID>
    <cbc:ProfileID>urn:peppol:pint:billing-1@sg-1</cbc:ProfileID>
    <cbc:ID>INV-001</cbc:ID>
    <cbc:IssueDate>2026-03-09</cbc:IssueDate>
    <!-- Additional elements -->
</Invoice>
```

**TDD Tests (20 tests)**:

| Test ID | Test Name | Purpose | Expected Result |
|---------|-----------|---------|-----------------|
| GEN-001 | test_generate_invoice_xml_structure | Basic structure | Valid XML with Invoice root |
| GEN-002 | test_generate_invoice_customization_id | PINT-SG ID | Contains customization ID |
| GEN-003 | test_generate_invoice_has_supplier_party | Supplier | Contains AccountingSupplierParty |
| GEN-004 | test_generate_invoice_has_customer_party | Customer | Contains AccountingCustomerParty |
| GEN-005 | test_generate_invoice_has_tax_total | Tax | Contains TaxTotal element |
| GEN-006 | test_generate_invoice_has_monetary_total | Totals | Contains LegalMonetaryTotal |
| GEN-007 | test_generate_invoice_has_invoice_lines | Lines | Contains InvoiceLine elements |
| GEN-008 | test_generate_invoice_xml_namespaces | Namespaces | UBL, CAC, CBC namespaces |
| GEN-009 | test_generate_credit_note_xml | Credit Note | CreditNote root element |
| GEN-010 | test_generate_credit_note_customization_id | PINT-SG ID | Same customization ID |
| GEN-011 | test_calculate_xml_hash | Hash | 64-char SHA-256 hash |
| GEN-012 | test_xml_hash_consistency | Consistency | Same XML = same hash |
| GEN-013 | test_generate_invoice_with_sr_tax | Standard tax | TaxCategory ID 'S' |
| GEN-014 | test_generate_invoice_with_zr_tax | Zero tax | TaxCategory ID 'Z' |
| GEN-015 | test_generate_invoice_with_es_tax | Exempt tax | TaxCategory ID 'E' |
| GEN-016 | test_generate_invoice_with_os_tax | Out of scope | TaxCategory ID 'O' |
| GEN-017 | test_generate_invoice_payment_terms | Payment | PaymentTerms element |
| GEN-018 | test_generate_invoice_line_id_present | Line ID | Each InvoiceLine has ID |
| GEN-019 | test_generate_invoice_utf8_encoding | Encoding | UTF-8 declaration |
| GEN-020 | test_generate_invoice_pretty_printed | Formatting | Indented XML output |

---

### Task 2.4: XML Validation Service
**Priority**: HIGH  
**Duration**: 1 day  
**Dependencies**: Task 2.1, 2.3 complete  

#### 2.4.1 Service Responsibilities

**File**: `apps/backend/apps/peppol/services/xml_validation_service.py`

**Core Functions**:
1. Validate XML against UBL 2.1 XSD schema
2. Validate XML against PINT-SG Schematron rules
3. Return detailed error messages
4. Support both Invoice and CreditNote validation

**Key Methods**:
```python
class XMLValidationService:
    def __init__(self):
        self._load_schemas()
        
    def _load_schemas(self):
        """Load XSD and Schematron schemas."""
        
    def validate_invoice_xml(self, xml_string: str) -> Dict[str, Any]:
        """Validate Invoice XML."""
        # Returns: {'is_valid': bool, 'schema_errors': [], 'schematron_errors': []}
        
    def validate_credit_note_xml(self, xml_string: str) -> Dict[str, Any]:
        """Validate CreditNote XML."""
```

**TDD Tests (12 tests)**:

| Test ID | Test Name | Purpose | Expected Result |
|---------|-----------|---------|-----------------|
| VAL-001 | test_validate_well_formed_invoice_xml | Well-formed | is_valid=True |
| VAL-002 | test_validate_invoice_xml_invalid_structure | Invalid | is_valid=False, errors |
| VAL-003 | test_validate_invoice_xml_missing_required | Missing | is_valid=False, errors |
| VAL-004 | test_validate_credit_note_well_formed | Credit note | is_valid=True |
| VAL-005 | test_validate_pint_sg_customization_id | PINT-SG | Validates customization ID |
| VAL-006 | test_validate_invalid_xml_syntax | Malformed | Catches syntax errors |
| VAL-007 | test_validate_empty_xml | Empty | Returns error |
| VAL-008 | test_validate_invoice_with_tax_error | Tax error | Catches schematron errors |
| VAL-009 | test_validate_invoice_currency_code | Currency | Validates SGD code |
| VAL-010 | test_validate_invoice_supplier_uen | UEN | Validates UEN present |
| VAL-011 | test_validate_invoice_line_quantity | Quantity | Validates quantity > 0 |
| VAL-012 | test_validate_schematron_rules | Rules | Catches PINT-SG violations |

---

## Execution Checklist

### Pre-Execution Validation
- [ ] Verify lxml is installed and working
- [ ] Verify schemas exist in peppol/schemas/
- [ ] Verify XMLMappingService is importable
- [ ] Verify InvoiceDocument model structure
- [ ] Verify InvoiceLine model with tax_code FK

### Task 2.3: XML Generator Service (RED → GREEN → REFACTOR)

#### RED Phase
- [ ] Create test file: `apps/peppol/tests/test_xml_generator_service.py`
- [ ] Write 20 failing tests (GEN-001 to GEN-020)
- [ ] Run tests, confirm all 20 fail

#### GREEN Phase
- [ ] Create `apps/peppol/services/xml_generator_service.py`
- [ ] Implement `generate_invoice_xml()` method
- [ ] Implement `generate_credit_note_xml()` method
- [ ] Implement `calculate_xml_hash()` method
- [ ] Add proper namespaces (UBL, CAC, CBC)
- [ ] Run tests, confirm all 20 pass

#### REFACTOR Phase
- [ ] Add XML escaping for special characters
- [ ] Optimize namespace handling
- [ ] Add comprehensive docstrings
- [ ] Add type hints

### Task 2.4: XML Validation Service (RED → GREEN → REFACTOR)

#### RED Phase
- [ ] Create test file: `apps/peppol/tests/test_xml_validation_service.py`
- [ ] Write 12 failing tests (VAL-001 to VAL-012)
- [ ] Run tests, confirm all 12 fail

#### GREEN Phase
- [ ] Create `apps/peppol/services/xml_validation_service.py`
- [ ] Implement XSD schema loading
- [ ] Implement Schematron loading (if lxml supports)
- [ ] Implement `validate_invoice_xml()` method
- [ ] Implement error collection
- [ ] Run tests, confirm all 12 pass

#### REFACTOR Phase
- [ ] Add caching for loaded schemas
- [ ] Optimize validation performance
- [ ] Add detailed error context
- [ ] Add comprehensive docstrings

---

## Verification Commands

### Schema Verification
```bash
# Verify schemas
ls -la apps/backend/apps/peppol/schemas/

# Verify lxml
python -c "from lxml import etree; print(f'lxml: {etree.__version__}')"
```

### Service Verification
```bash
# Import test
cd apps/backend
python -c "
from apps.peppol.services.xml_generator_service import XMLGeneratorService
from apps.peppol.services.xml_validation_service import XMLValidationService
print('✅ All services import successfully')
"
```

### Test Suite Verification
```bash
# Run all Phase 2 tests
cd apps/backend
pytest apps/peppol/tests/test_xml_generator_service.py \
      apps/peppol/tests/test_xml_validation_service.py \
      -v --reuse-db --no-migrations

# Expected: 32 tests passing
```

---

## Success Metrics

| Metric | Target | Verification |
|--------|--------|------------|
| Generator Service | 20/20 tests | pytest reports |
| Validation Service | 12/12 tests | pytest reports |
| Total Phase 2 | 43/43 tests | pytest summary |
| No Regressions | Existing tests | Full test suite |

---

## Risk Assessment

### Risk 1: lxml Schema Validation Complexity
**Mitigation**: Start with basic XML structure validation, add XSD/Schematron gradually

### Risk 2: Namespace Handling Errors
**Mitigation**: Test namespace declarations explicitly in GEN-008

### Risk 3: Hash Calculation Mismatch
**Mitigation**: Test hash consistency (GEN-012) to ensure deterministic output

### Risk 4: XML Encoding Issues
**Mitigation**: UTF-8 declaration test (GEN-019) and special character escaping

---

**Sub-Plan Status**: READY FOR EXECUTION  
**Next Step**: Begin Task 2.3 (XML Generator Service)  
**Confidence**: High (based on validated codebase)
