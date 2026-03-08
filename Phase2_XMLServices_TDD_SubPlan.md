# Phase 2: XML Services — TDD Implementation Sub-Plan

## Overview

**Phase**: 2 of 5  
**Duration**: Days 4-8  
**Objective**: Create XML generation pipeline for InvoiceNow/Peppol transmission  
**TDD Approach**: RED → GREEN → REFACTOR for each component  

---

## Success Criteria

- [ ] XML schemas downloaded and stored (UBL 2.1, PINT-SG)
- [ ] XML Mapping Service converts InvoiceDocument → UBL structure
- [ ] XML Generator Service creates valid UBL 2.1 XML
- [ ] XML Validation Service validates against PINT-SG rules
- [ ] **47 TDD tests passing** (15 mapping + 20 generation + 12 validation)
- [ ] No regressions in existing tests

---

## Codebase Validation

### Model Structure (Verified)

**InvoiceDocument** (`apps/core/models/invoice_document.py`):
- `document_number` (CharField) ✓
- `issue_date` (DateField) ✓
- `due_date` (DateField) ✓
- `currency` (CharField) ✓
- `contact` (ForeignKey to Contact) ✓
- `total_excl` / `subtotal` ✓
- `gst_total` / `total_gst` ✓
- `total_incl` / `total_amount` ✓
- `amount_paid` ✓
- Related lines: `lines` (via InvoiceLine) ✓

**InvoiceLine** (`apps/core/models/invoice_line.py`):
- `line_number` ✓
- `description` ✓
- `quantity` ✓
- `unit_price` ✓
- `tax_code` (ForeignKey) ✓
- `tax_rate` ✓
- `line_amount` ✓
- `gst_amount` ✓
- `is_bcrs_deposit` ✓

**Contact** (`apps/core/models/contact.py`):
- `uen` ✓
- `legal_name` ✓
- `gst_reg_number` ✓
- `is_gst_registered` ✓
- `address_line_1`, `address_line_2` ✓
- `city`, `postal_code`, `country` ✓
- `peppol_id` ✓

**Organisation** (`apps/core/models/organisation.py`):
- `uen` ✓
- `legal_name` ✓
- `gst_reg_number` ✓
- `gst_registered` ✓
- Address fields ✓
- `peppol_participant_id` ✓

**TaxCode** (`apps/core/models/tax_code.py`):
- `code` (SR, ZR, ES, OS, etc.) ✓
- `rate` ✓

---

## Task Breakdown

### Task 2.1: Download XML Schemas
**Priority**: HIGH  
**Duration**: 1 hour  
**Dependencies**: None  

#### 2.1.1 Create Schemas Directory
```bash
mkdir -p apps/backend/apps/peppol/schemas
```

#### 2.1.2 Download UBL 2.1 and PINT-SG Schemas
**Files to download:**
- `ubl-Invoice.xsd` - UBL 2.1 Invoice schema
- `ubl-CreditNote.xsd` - UBL 2.1 Credit Note schema  
- `PINT-UBL-validation.sch` - PINT-SG Schematron rules

**Source URLs:**
- https://docs.peppol.eu/poac/sg/pint-sg/trn-invoice/syntax/ubl-Invoice.xsd
- https://docs.peppol.eu/poac/sg/pint-sg/trn-creditnote/syntax/ubl-CreditNote.xsd
- https://docs.peppol.eu/poac/sg/pint-sg/trn-invoice/rule/PINT-UBL-validation.sch

**TDD Tests (3 tests):**
- `test_schemas_directory_exists` - Verify directory created
- `test_ubl_invoice_xsd_downloaded` - Verify Invoice schema exists
- `test_pint_schematron_downloaded` - Verify PINT validation rules exist

**Validation:**
```bash
ls -la apps/backend/apps/peppol/schemas/
# Expected: ubl-Invoice.xsd, ubl-CreditNote.xsd, PINT-UBL-validation.sch
```

---

### Task 2.2: Create XML Mapping Service
**Priority**: HIGH  
**Duration**: 2 days  
**Dependencies**: Task 2.1 complete  

#### 2.2.1 Create Service File
**File**: `apps/backend/apps/peppol/services/xml_mapping_service.py`

**Responsibilities:**
1. Map InvoiceDocument to UBL 2.1 data structure (Python dict)
2. Validate mandatory Peppol fields (UEN, document number, etc.)
3. Handle Singapore tax code mapping (SR→S, ZR→Z, ES→E, OS→O)
4. Format addresses for UBL
5. Calculate tax totals grouped by rate

**Key Methods:**
```python
class XMLMappingService:
    @staticmethod
    def map_invoice_to_ubl(invoice: InvoiceDocument) -> Dict[str, Any]:
        """Convert InvoiceDocument to UBL 2.1 data structure."""
        
    @staticmethod
    def _validate_peppol_requirements(invoice, org, contact) -> None:
        """Validate mandatory fields for Peppol compliance."""
        
    @staticmethod
    def _get_tax_category(tax_code: TaxCode) -> str:
        """Map Singapore tax code to UBL tax category."""
        # SR → 'S' (Standard-rated)
        # ZR → 'Z' (Zero-rated)
        # ES → 'E' (Exempt)
        # OS → 'O' (Out-of-scope)
        
    @staticmethod
    def _calculate_tax_totals(invoice: InvoiceDocument) -> Dict[str, Any]:
        """Calculate tax totals grouped by tax rate."""
```

**TDD Tests (15 tests):**

| Test | Purpose | Expected Result |
|------|---------|-----------------|
| `test_map_invoice_basic_structure` | Map basic invoice fields | UBL structure with version 2.1, PINT-SG customization |
| `test_map_invoice_requires_supplier_uen` | Validation | Raises ValueError if org.uen missing |
| `test_map_invoice_requires_gst_number_if_registered` | Validation | Raises ValueError if GST-registered org missing gst_reg_number |
| `test_map_invoice_requires_document_number` | Validation | Raises ValueError if document_number missing |
| `test_map_invoice_requires_issue_date` | Validation | Raises ValueError if issue_date missing |
| `test_map_invoice_tax_category_mapping_sr` | Tax mapping | SR → 'S' category |
| `test_map_invoice_tax_category_mapping_zr` | Tax mapping | ZR → 'Z' category |
| `test_map_invoice_tax_category_mapping_es` | Tax mapping | ES → 'E' category |
| `test_map_invoice_tax_category_mapping_os` | Tax mapping | OS → 'O' category |
| `test_map_invoice_calculates_tax_totals` | Tax calculation | Groups lines by tax rate, calculates totals |
| `test_map_invoice_address_formatting` | Address formatting | Formats org and contact addresses for UBL |
| `test_map_invoice_monetary_totals` | Totals | Maps subtotal, total_gst, total_amount, amount_due |
| `test_map_invoice_line_items` | Line mapping | Maps all invoice lines with quantity, price, tax |
| `test_map_credit_note` | Credit note support | Maps SALES_CREDIT_NOTE document type |
| `test_map_invoice_bcrs_deposit_excluded` | BCRS handling | Excludes BCRS deposit lines from tax totals |

**Output Structure:**
```python
{
    'ubl_version': '2.1',
    'customization_id': 'urn:peppol:pint:billing-1@sg-1',
    'profile_id': 'urn:peppol:pint:billing-1@sg-1',
    'document_id': 'INV-001',
    'issue_date': '2026-03-09',
    'due_date': '2026-04-09',
    'document_type': 'INVOICE',  # or 'CREDIT_NOTE'
    'currency': 'SGD',
    'tax_currency': 'SGD',
    'supplier': {
        'name': 'Org Name',
        'uen': '202312345A',
        'gst_registration': 'M2-1234567-8',
        'address': {...},
        'peppol_id': '0195:202312345A',
    },
    'customer': {
        'name': 'Contact Name',
        'uen': '202398765B',
        'address': {...},
        'peppol_id': '0195:202398765B',
    },
    'payment_terms': {...},
    'tax_totals': {
        'tax_categories': [...],
        'total_tax_amount': '90.00',
    },
    'monetary_totals': {
        'line_extension_amount': '1000.00',
        'tax_exclusive_amount': '1000.00',
        'tax_inclusive_amount': '1090.00',
        'payable_amount': '1090.00',
        'prepaid_amount': '0.00',
    },
    'lines': [...],
}
```

---

### Task 2.3: Create XML Generator Service
**Priority**: HIGH  
**Duration**: 2 days  
**Dependencies**: Task 2.2 complete  

#### 2.3.1 Create Service File
**File**: `apps/backend/apps/peppol/services/xml_generator_service.py`

**Responsibilities:**
1. Generate UBL 2.1 XML from mapped data structure
2. Use lxml for XML construction with proper namespaces
3. Support both Invoice and Credit Note
4. Calculate SHA-256 hash of XML payload
5. Pretty-print XML for readability

**Key Methods:**
```python
class XMLGeneratorService:
    NAMESPACE_UBL = 'urn:oasis:names:specification:ubl:schema:xsd:Invoice-2'
    NAMESPACE_CAC = 'urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2'
    NAMESPACE_CBC = 'urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2'

    def generate_invoice_xml(self, mapped_data: Dict[str, Any]) -> str:
        """Generate UBL 2.1 Invoice XML."""
        
    def generate_credit_note_xml(self, mapped_data: Dict[str, Any]) -> str:
        """Generate UBL 2.1 Credit Note XML."""
        
    def calculate_xml_hash(self, xml_string: str) -> str:
        """Calculate SHA-256 hash of XML payload."""
        
    def _add_element(self, parent, tag_name, value, namespace='cbc'):
        """Helper to add namespaced elements."""
```

**XML Structure (Invoice):**
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
    <cbc:DueDate>2026-04-09</cbc:DueDate>
    <cbc:InvoiceTypeCode>380</cbc:InvoiceTypeCode>
    <cbc:DocumentCurrencyCode>SGD</cbc:DocumentCurrencyCode>
    <cbc:TaxCurrencyCode>SGD</cbc:TaxCurrencyCode>
    <cac:AccountingSupplierParty>...</cac:AccountingSupplierParty>
    <cac:AccountingCustomerParty>...</cac:AccountingCustomerParty>
    <cac:PaymentTerms>...</cac:PaymentTerms>
    <cac:TaxTotal>...</cac:TaxTotal>
    <cac:LegalMonetaryTotal>...</cac:LegalMonetaryTotal>
    <cac:InvoiceLine>...</cac:InvoiceLine>
</Invoice>
```

**TDD Tests (20 tests):**

| Test | Purpose | Expected Result |
|------|---------|-----------------|
| `test_generate_invoice_xml_structure` | Basic structure | Valid XML with Invoice root element |
| `test_generate_invoice_customization_id` | PINT-SG ID | Contains `urn:peppol:pint:billing-1@sg-1` |
| `test_generate_invoice_has_supplier_party` | Supplier | Contains AccountingSupplierParty with UEN |
| `test_generate_invoice_has_customer_party` | Customer | Contains AccountingCustomerParty |
| `test_generate_invoice_has_tax_total` | Tax totals | Contains TaxTotal element |
| `test_generate_invoice_has_monetary_total` | Monetary totals | Contains LegalMonetaryTotal |
| `test_generate_invoice_has_invoice_lines` | Line items | Contains InvoiceLine elements |
| `test_generate_invoice_xml_namespaces` | Namespaces | Correct UBL, CAC, CBC namespaces |
| `test_generate_credit_note_xml` | Credit note | CreditNote root element |
| `test_generate_credit_note_customization_id` | PINT-SG ID | Same customization ID as invoice |
| `test_calculate_xml_hash` | Hash calculation | 64-character SHA-256 hash |
| `test_xml_hash_consistency` | Hash consistency | Same XML = same hash |
| `test_generate_invoice_with_sr_tax` | Standard tax | TaxCategory with ID 'S' |
| `test_generate_invoice_with_zr_tax` | Zero tax | TaxCategory with ID 'Z' |
| `test_generate_invoice_with_es_tax` | Exempt tax | TaxCategory with ID 'E' |
| `test_generate_invoice_with_os_tax` | Out of scope | TaxCategory with ID 'O' |
| `test_generate_invoice_payment_terms` | Payment | Contains PaymentTerms element |
| `test_generate_invoice_line_id_present` | Line ID | Each InvoiceLine has ID element |
| `test_generate_invoice_utf8_encoding` | Encoding | UTF-8 declaration |
| `test_generate_invoice_pretty_printed` | Formatting | Indented XML output |

---

### Task 2.4: Create XML Validation Service
**Priority**: HIGH  
**Duration**: 2 days  
**Dependencies**: Task 2.1 complete  

#### 2.4.1 Create Service File
**File**: `apps/backend/apps/peppol/services/xml_validation_service.py`

**Responsibilities:**
1. Validate XML against UBL 2.1 XSD schema
2. Validate XML against PINT-SG Schematron rules
3. Return detailed error messages
4. Support both Invoice and Credit Note validation

**Key Methods:**
```python
class XMLValidationService:
    def __init__(self):
        self._load_schemas()
        
    def _load_schemas(self):
        """Load XSD and Schematron schemas."""
        
    def validate_invoice_xml(self, xml_string: str) -> Dict[str, Any]:
        """Validate Invoice XML against schema and schematron."""
        # Returns: {'is_valid': bool, 'schema_errors': [], 'schematron_errors': []}
        
    def validate_credit_note_xml(self, xml_string: str) -> Dict[str, Any]:
        """Validate Credit Note XML."""
```

**TDD Tests (12 tests):**

| Test | Purpose | Expected Result |
|------|---------|-----------------|
| `test_validate_well_formed_invoice_xml` | Well-formed XML | is_valid=True, no errors |
| `test_validate_invoice_xml_invalid_structure` | Invalid structure | is_valid=False, schema errors |
| `test_validate_invoice_xml_missing_required` | Missing elements | is_valid=False, error messages |
| `test_validate_credit_note_well_formed` | Credit note | is_valid=True |
| `test_validate_pint_sg_customization_id` | PINT-SG ID | Validates `urn:peppol:pint:billing-1@sg-1` |
| `test_validate_invalid_xml_syntax` | Malformed XML | Catches XML syntax errors |
| `test_validate_empty_xml` | Empty string | Returns error |
| `test_validate_invoice_with_tax_error` | Tax validation | Catches schematron tax errors |
| `test_validate_invoice_currency_code` | Currency | Validates SGD currency code |
| `test_validate_invoice_supplier_uen` | UEN presence | Validates supplier UEN present |
| `test_validate_invoice_line_quantity` | Quantity | Validates line quantity > 0 |
| `test_validate_schematron_rules` | Business rules | Catches PINT-SG rule violations |

---

## Execution Checklist

### Pre-Execution Validation
- [ ] Verify InvoiceDocument model structure
- [ ] Verify InvoiceLine model structure
- [ ] Verify Contact model has peppol_id and uen fields
- [ ] Verify Organisation model has peppol fields
- [ ] Verify TaxCode model has code and rate fields
- [ ] Check lxml is in requirements.txt
- [ ] Confirm peppol/schemas directory can be created

### Task 2.1: XML Schemas (RED → GREEN → REFACTOR)

**RED Phase:**
- [ ] Create failing test: `test_schemas_directory_exists`
- [ ] Create failing test: `test_ubl_invoice_xsd_downloaded`
- [ ] Create failing test: `test_pint_schematron_downloaded`
- [ ] Run tests, confirm failures

**GREEN Phase:**
- [ ] Create `apps/backend/apps/peppol/schemas/` directory
- [ ] Download UBL Invoice schema
- [ ] Download UBL CreditNote schema
- [ ] Download PINT-SG Schematron
- [ ] Run tests, confirm passing

**REFACTOR Phase:**
- [ ] Add schema file checksums or versions
- [ ] Document schema sources
- [ ] Verify schemas are valid XML/XSD

### Task 2.2: XML Mapping Service (RED → GREEN → REFACTOR)

**RED Phase:**
- [ ] Create test file: `apps/peppol/tests/test_xml_mapping_service.py`
- [ ] Write 15 failing tests (see table above)
- [ ] Run tests, confirm all 15 fail

**GREEN Phase:**
- [ ] Create `apps/peppol/services/xml_mapping_service.py`
- [ ] Implement `map_invoice_to_ubl()` method
- [ ] Implement validation methods
- [ ] Implement tax category mapping
- [ ] Implement tax totals calculation
- [ ] Run tests, confirm all 15 pass

**REFACTOR Phase:**
- [ ] Add comprehensive docstrings
- [ ] Optimize tax calculation logic
- [ ] Add type hints
- [ ] Review error messages for clarity

### Task 2.3: XML Generator Service (RED → GREEN → REFACTOR)

**RED Phase:**
- [ ] Create test file: `apps/peppol/tests/test_xml_generator_service.py`
- [ ] Write 20 failing tests (see table above)
- [ ] Run tests, confirm all 20 fail

**GREEN Phase:**
- [ ] Create `apps/peppol/services/xml_generator_service.py`
- [ ] Implement `generate_invoice_xml()` method
- [ ] Implement `generate_credit_note_xml()` method
- [ ] Implement hash calculation
- [ ] Add proper namespaces
- [ ] Run tests, confirm all 20 pass

**REFACTOR Phase:**
- [ ] Add XML escaping for special characters
- [ ] Optimize namespace handling
- [ ] Add XML size limits
- [ ] Document XML structure

### Task 2.4: XML Validation Service (RED → GREEN → REFACTOR)

**RED Phase:**
- [ ] Create test file: `apps/peppol/tests/test_xml_validation_service.py`
- [ ] Write 12 failing tests (see table above)
- [ ] Run tests, confirm all 12 fail

**GREEN Phase:**
- [ ] Create `apps/peppol/services/xml_validation_service.py`
- [ ] Implement XSD schema loading
- [ ] Implement Schematron loading
- [ ] Implement `validate_invoice_xml()` method
- [ ] Implement error collection
- [ ] Run tests, confirm all 12 pass

**REFACTOR Phase:**
- [ ] Add caching for loaded schemas
- [ ] Optimize validation performance
- [ ] Add detailed error context
- [ ] Document validation rules

---

## Verification Commands

### Schema Verification
```bash
# Verify schemas directory
ls -la apps/backend/apps/peppol/schemas/

# Verify schema files
file apps/backend/apps/peppol/schemas/*.xsd
file apps/backend/apps/peppol/schemas/*.sch
```

### Service Verification
```bash
# Import test
cd apps/backend
python -c "
from apps.peppol.services.xml_mapping_service import XMLMappingService
from apps.peppol.services.xml_generator_service import XMLGeneratorService
from apps.peppol.services.xml_validation_service import XMLValidationService
print('✅ All services import successfully')
"
```

### Test Suite Verification
```bash
# Run all Phase 2 tests
cd apps/backend
pytest apps/peppol/tests/test_xml_mapping_service.py \
      apps/peppol/tests/test_xml_generator_service.py \
      apps/peppol/tests/test_xml_validation_service.py \
      apps/peppol/tests/test_schemas.py -v

# Expected: 47 tests passing
```

---

## Success Metrics

| Metric | Target | Verification |
|--------|--------|------------|
| XML Schemas | 3 files downloaded | File existence checks |
| Mapping Service | 15/15 tests passing | pytest reports |
| Generator Service | 20/20 tests passing | pytest reports |
| Validation Service | 12/12 tests passing | pytest reports |
| Total Coverage | 47/47 tests | pytest summary |
| No Regressions | Existing tests pass | Full test suite |

---

## Next Phase Readiness

**Phase 2 is complete when:**
- [ ] 47/47 Phase 2 tests passing
- [ ] XML generates valid UBL 2.1 structure
- [ ] Validation catches invalid XML
- [ ] All tax categories map correctly
- [ ] No regressions in existing tests

**Phase 3 Prerequisites:**
- Phase 2 complete ✅
- XML can be generated from any InvoiceDocument
- XML validates against PINT-SG rules
- Services can be imported without errors

---

**Sub-Plan Status**: READY FOR REVIEW  
**Next Step**: User review and validation before execution  
**Confidence**: High (based on thorough codebase validation)
