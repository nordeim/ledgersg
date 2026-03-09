# Phase 2: Critical Schema Fixes - TDD Implementation Sub-Plan

## Overview

**Objective**: Fix 8 critical XSD schema issues for PINT-SG compliance  
**Approach**: TDD (RED → GREEN → REFACTOR) for each issue  
**Duration**: 4-6 hours  
**Target**: 100% Phase 2 tests passing with PINT-SG compliant schemas

---

## Critical Issues Summary

| # | Issue | Severity | Test Count | Files Affected |
|---|-------|----------|------------|----------------|
| 1 | Schema import paths | 🔴 Critical | 2 | ubl-Invoice.xsd, ubl-CreditNote.xsd |
| 2 | Missing mandatory elements | 🔴 Critical | 3 | ubl-Invoice.xsd |
| 3 | Monetary precision | 🔴 Critical | 2 | ubl-Invoice.xsd |
| 4 | TaxCategory restrictions | 🔴 Critical | 4 | ubl-Invoice.xsd |
| 5 | PartyTaxScheme missing | 🔴 Critical | 2 | ubl-Invoice.xsd |
| 6 | PaymentMeans missing | 🔴 Critical | 2 | ubl-Invoice.xsd |
| 7 | AllowanceCharge missing | 🔴 Critical | 2 | ubl-Invoice.xsd |
| 8 | InvoiceLine incomplete | 🟠 High | 3 | ubl-Invoice.xsd |
| **Total** | | | **20 tests** | |

---

## Codebase Validation

### Current State (Verified)

**Files to Modify:**
- ✅ `apps/peppol/schemas/ubl-Invoice.xsd` - Minimal schema (27 lines)
- ✅ `apps/peppol/schemas/ubl-CreditNote.xsd` - Minimal schema (27 lines)
- ✅ `apps/peppol/services/xml_generator_service.py` - Generates XML

**Test Files:**
- ✅ `apps/peppol/tests/test_schemas.py` - 6 tests (schemas exist)
- ✅ `apps/peppol/tests/test_xml_generator_service.py` - 11 tests
- ✅ `apps/peppol/tests/test_xml_validation_service.py` - 13 tests

**Current Test Status:**
- 35/35 Phase 2 tests passing
- Schemas are minimal but functional
- Need enhancement for PINT-SG compliance

---

## TDD Execution Plan

### Issue 1: Schema Import Paths
**Current**: References non-existent files
**Required**: Remove imports or use correct paths

**TDD Tests (2 tests):**
```python
def test_invoice_schema_loads_without_import_errors():
    """Test that Invoice XSD loads without import errors."""
    from lxml import etree
    schema_doc = etree.parse('apps/peppol/schemas/ubl-Invoice.xsd')
    schema = etree.XMLSchema(schema_doc)  # Should not raise
    assert schema is not None

def test_credit_note_schema_loads_without_import_errors():
    """Test that CreditNote XSD loads without import errors."""
    from lxml import etree
    schema_doc = etree.parse('apps/peppol/schemas/ubl-CreditNote.xsd')
    schema = etree.XMLSchema(schema_doc)
    assert schema is not None
```

**Fix:**
- Remove xs:import statements (we define all elements locally)
- Ensure schema is self-contained

---

### Issue 2: Mandatory PINT-SG Elements
**Current**: minOccurs="0" for required elements
**Required**: minOccurs="1" for CustomizationID, ProfileID, DocumentCurrencyCode

**TDD Tests (3 tests):**
```python
def test_customization_id_is_required():
    """Test that CustomizationID is mandatory."""
    # XML without CustomizationID should fail validation

def test_profile_id_is_required():
    """Test that ProfileID is mandatory."""

def test_document_currency_code_is_required():
    """Test that DocumentCurrencyCode is mandatory."""
```

**Fix:**
```xml
<xs:element ref="cbc:CustomizationID" minOccurs="1"/>
<xs:element ref="cbc:ProfileID" minOccurs="1"/>
<xs:element ref="cbc:DocumentCurrencyCode" minOccurs="1"/>
```

---

### Issue 3: Monetary Precision (AmountType)
**Current**: xs:decimal without restrictions
**Required**: 4 decimal places, 14 total digits

**TDD Tests (2 tests):**
```python
def test_amount_type_enforces_4_decimals():
    """Test that AmountType enforces 4 decimal precision."""
    # Should accept: 1000.0000
    # Should reject: 1000.00000 (5 decimals)

def test_amount_type_enforces_max_digits():
    """Test that AmountType enforces max 14 digits."""
```

**Fix:**
```xml
<xs:simpleType name="AmountType">
  <xs:restriction base="xs:decimal">
    <xs:totalDigits value="14"/>
    <xs:fractionDigits value="4"/>
  </xs:restriction>
</xs:simpleType>
```

---

### Issue 4: TaxCategory ID Restrictions
**Current**: Any string allowed
**Required**: Only S, Z, E, O, K, NG allowed

**TDD Tests (4 tests):**
```python
def test_tax_category_accepts_s():
    """Test 'S' (Standard-rated) is valid."""
def test_tax_category_accepts_z():
    """Test 'Z' (Zero-rated) is valid."""
def test_tax_category_accepts_e():
    """Test 'E' (Exempt) is valid."""
def test_tax_category_rejects_invalid_code():
    """Test invalid tax category code is rejected."""
```

**Fix:**
```xml
<xs:simpleType name="TaxCategoryIDType">
  <xs:restriction base="xs:token">
    <xs:enumeration value="S"/> <!-- Standard-rated 9% -->
    <xs:enumeration value="Z"/> <!-- Zero-rated 0% -->
    <xs:enumeration value="E"/> <!-- Exempt 0% -->
    <xs:enumeration value="O"/> <!-- Out-of-scope 0% -->
    <xs:enumeration value="K"/> <!-- Reverse charge -->
    <xs:enumeration value="NG"/> <!-- Non-GST registered -->
  </xs:restriction>
</xs:simpleType>
```

---

### Issue 5: PartyTaxScheme for GST
**Current**: Missing entirely
**Required**: For GST registration numbers

**TDD Tests (2 tests):**
```python
def test_party_tax_scheme_element_exists():
    """Test PartyTaxScheme element exists in schema."""
def test_party_tax_scheme_contains_company_id():
    """Test PartyTaxScheme contains CompanyID for UEN."""
```

**Fix:**
```xml
<xs:element name="PartyTaxScheme" type="PartyTaxSchemeType"/>
<xs:complexType name="PartyTaxSchemeType">
  <xs:sequence>
    <xs:element ref="cbc:CompanyID" minOccurs="0"/>
    <xs:element ref="cac:TaxScheme" minOccurs="0"/>
  </xs:sequence>
</xs:complexType>
```

---

### Issue 6: PaymentMeans for PayNow
**Current**: Missing entirely
**Required**: For PayNow, GIRO, Bank Transfer

**TDD Tests (2 tests):**
```python
def test_payment_means_element_exists():
    """Test PaymentMeans element exists."""
def test_payment_means_code_restrictions():
    """Test PaymentMeansCode accepts valid codes (30, 42, 47, 49)."""
```

**Fix:**
```xml
<xs:element name="PaymentMeans" type="PaymentMeansType"/>
<xs:complexType name="PaymentMeansType">
  <xs:sequence>
    <xs:element ref="cbc:PaymentMeansCode"/>
    <xs:element ref="cbc:PaymentDueDate" minOccurs="0"/>
    <xs:element ref="cbc:PayeeFinancialAccount" minOccurs="0"/>
  </xs:sequence>
</xs:complexType>

<xs:simpleType name="PaymentMeansCodeType">
  <xs:restriction base="xs:token">
    <xs:enumeration value="30"/> <!-- Credit transfer -->
    <xs:enumeration value="42"/> <!-- PayNow -->
    <xs:enumeration value="47"/> <!-- PayNow Corporate -->
    <xs:enumeration value="49"/> <!-- GIRO -->
  </xs:restriction>
</xs:simpleType>
```

---

### Issue 7: AllowanceCharge
**Current**: Missing entirely
**Required**: For discounts and BCRS deposits

**TDD Tests (2 tests):**
```python
def test_allowance_charge_element_exists():
    """Test AllowanceCharge element exists."""
def test_allowance_charge_has_required_fields():
    """Test AllowanceCharge has ChargeIndicator and Amount."""
```

**Fix:**
```xml
<xs:element name="AllowanceCharge" type="AllowanceChargeType"/>
<xs:complexType name="AllowanceChargeType">
  <xs:sequence>
    <xs:element ref="cbc:ChargeIndicator" minOccurs="1"/>
    <xs:element ref="cbc:AllowanceChargeReason" minOccurs="0"/>
    <xs:element ref="cbc:ActualAmount" minOccurs="1"/>
    <xs:element ref="cac:TaxCategory" minOccurs="0"/>
  </xs:sequence>
</xs:complexType>
```

---

### Issue 8: Complete InvoiceLine
**Current**: Basic structure
**Required**: All mandatory PINT-SG elements

**TDD Tests (3 tests):**
```python
def test_invoice_line_has_required_id():
    """Test InvoiceLine requires ID element."""
def test_invoice_line_has_required_line_extension():
    """Test InvoiceLine requires LineExtensionAmount."""
def test_invoice_line_has_item_and_price():
    """Test InvoiceLine requires Item and Price."""
```

**Fix:**
```xml
<xs:complexType name="InvoiceLineType">
  <xs:sequence>
    <xs:element ref="cbc:ID" minOccurs="1"/> <!-- FIXED: Was 0 -->
    <xs:element ref="cbc:InvoicedQuantity" minOccurs="0"/>
    <xs:element ref="cbc:LineExtensionAmount" minOccurs="1"/> <!-- FIXED: Was 0 -->
    <xs:element ref="cac:Item" minOccurs="1"/> <!-- FIXED: Was 0 -->
    <xs:element ref="cac:Price" minOccurs="1"/> <!-- FIXED: Was 0 -->
  </xs:sequence>
</xs:complexType>
```

---

## Execution Checklist

### Phase 1: TDD Setup (RED)
- [ ] Create test file: `test_schema_fixes.py` (20 tests)
- [ ] Write all 20 failing tests
- [ ] Run tests to confirm they fail

### Phase 2: Schema Fixes (GREEN)
- [ ] Fix Issue 1: Remove incorrect imports
- [ ] Fix Issue 2: Make elements required
- [ ] Fix Issue 3: Add AmountType
- [ ] Fix Issue 4: Add TaxCategory restrictions
- [ ] Fix Issue 5: Add PartyTaxScheme
- [ ] Fix Issue 6: Add PaymentMeans
- [ ] Fix Issue 7: Add AllowanceCharge
- [ ] Fix Issue 8: Complete InvoiceLine
- [ ] Run tests until all pass

### Phase 3: XML Generator Updates
- [ ] Update XMLGeneratorService to generate compliant XML
- [ ] Ensure all mandatory elements are included
- [ ] Use correct tax category codes
- [ ] Include PaymentMeans when applicable
- [ ] Run all Phase 2 tests

### Phase 4: Refactor
- [ ] Optimize schema structure
- [ ] Add comprehensive documentation
- [ ] Verify no test regressions

---

## Success Metrics

| Metric | Current | Target | Verification |
|--------|---------|--------|--------------|
| Schema compliance | 65% | 95%+ | XSD validation |
| Phase 2 tests | 35/35 | 35/35+ | pytest |
| New fix tests | 0/20 | 20/20 | pytest |
| PINT-SG elements | Partial | Complete | Schema inspection |

---

## Risk Mitigation

### Risk 1: Schema becomes too complex
**Mitigation**: Keep schema self-contained, no external imports

### Risk 2: XMLGenerator breaks
**Mitigation**: Update generator alongside schema changes

### Risk 3: Test failures cascade
**Mitigation**: Fix one issue at a time, run tests after each

---

## Validation Commands

```bash
# Test schema validity
cd apps/backend
python -c "
from lxml import etree
schema_doc = etree.parse('apps/peppol/schemas/ubl-Invoice.xsd')
schema = etree.XMLSchema(schema_doc)
print('✅ Schema is valid')
"

# Test generated XML validates
cd apps/backend
pytest apps/peppol/tests/ -v --tb=short

# Expected: 55+ tests passing
```

---

**Sub-Plan Status**: READY FOR EXECUTION  
**Confidence**: High (validated against codebase)
