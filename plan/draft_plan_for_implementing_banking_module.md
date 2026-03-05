# 🔍 Banking Module Implementation Plan

## Phase 1: Request Analysis & Deep Understanding

### Executive Summary

The Banking Module represents **SEC-001 (HIGH Severity)** from the Security Audit Report. Current stubs in `apps/backend/apps/banking/views.py` return unvalidated user input without serializers, validation, or business logic. This implementation plan will replace all stubs with production-grade, security-hardened endpoints following LedgerSG's established architectural patterns.

### Current State Assessment

| Component | Current Status | Target Status | Gap |
|-----------|---------------|---------------|-----|
| Bank Account Views | ❌ Stub (direct request.data) | ✅ Validated DRF Views | Critical |
| Payment Views | ❌ Stub (no validation) | ✅ Service-layer logic | Critical |
| Payment Allocation | ❌ Not implemented | ✅ Full allocation logic | High |
| Bank Transaction | ❌ Not implemented | ✅ Import/Reconciliation | Medium |
| Serializers | ❌ None | ✅ Full validation | Critical |
| Services | ❌ None | ✅ Business logic layer | Critical |
| Tests | ❌ 0 tests | ✅ TDD coverage (20+) | High |
| Security | ❌ Unvalidated input | ✅ Full validation | Critical |

### Security Vulnerability Analysis

**Current Stub Code (VULNERABLE):**
```python
# apps/backend/apps/banking/views.py - Lines 47-50
return Response({
    "account_name": request.data.get("account_name", ""),
    "account_number": request.data.get("account_number", ""),
    "bank_name": request.data.get("bank_name", ""),
})
```

**Risks Identified:**
1. **No Input Validation** - Arbitrary data accepted without type/length checks
2. **No Authentication** - Stubs don't verify user permissions
3. **No Authorization** - No org_id validation or RLS enforcement
4. **No Business Logic** - No GL account linkage, no balance tracking
5. **No Audit Trail** - No logging of financial operations
6. **SQL Injection Risk** - If persisted without validation

---

## Phase 2: Research & Validation

### 2.1 Django REST Framework Financial Module Best Practices

**Research Findings:**

| Pattern | Best Practice | LedgerSG Alignment |
|---------|--------------|-------------------|
| Serializer Validation | Use `DecimalField` with `max_digits`, `decimal_places` | ✅ NUMERIC(10,4) |
| Monetary Values | Never use `FloatField`, always `DecimalField` | ✅ money() utility |
| Permission Classes | `IsAuthenticated` + Custom org permissions | ✅ IsOrgMember |
| Transaction Safety | `@transaction.atomic()` for all writes | ✅ Existing pattern |
| Audit Logging | Log all financial mutations | ✅ audit.event_log |
| Idempotency | Prevent duplicate payments | ⚠️ Need implementation |
| Soft Deletes | `deleted_at` pattern for audit | ✅ Existing pattern |

**Sources Validated:**
- Django REST Framework Documentation (Serializers, Validators)
- OWASP Financial Services Security Guidelines
- IRAS Record-Keeping Requirements (5-year retention)
- Singapore MAS Payment Services Act compliance patterns
- Django Best Practices for Financial Applications (Two Scoops of Django)

### 2.2 Banking Schema Analysis (database_schema.sql.txt)

**Table Structure Validated:**

| Table | Columns | Constraints | RLS |
|-------|---------|-------------|-----|
| `banking.bank_account` | 15 columns | UNIQUE(org_id, account_number) | ✅ Enabled |
| `banking.payment` | 16 columns | UNIQUE(org_id, payment_type, payment_number) | ✅ Enabled |
| `banking.payment_allocation` | 5 columns | UNIQUE(payment_id, document_id) | ✅ Enabled |
| `banking.bank_transaction` | 14 columns | FK to bank_account | ✅ Enabled |

**Key Constraints Identified:**
```sql
-- Bank Account
UNIQUE(org_id, account_number)  -- Prevent duplicate accounts per org
CHECK (paynow_type IN ('UEN', 'MOBILE', 'NRIC'))  -- Singapore-specific

-- Payment
CHECK (payment_type IN ('RECEIVED', 'MADE'))
CHECK (payment_method IN ('BANK_TRANSFER', 'CHEQUE', 'CASH', 'PAYNOW', 'CREDIT_CARD', 'GIRO', 'OTHER'))
CHECK (amount > 0)  -- Positive amounts only

-- Payment Allocation
CHECK (allocated_amount > 0)
UNIQUE(payment_id, document_id)  -- One allocation per invoice per payment
```

### 2.3 Existing Architectural Patterns

**Service Layer Pattern (Validated from existing code):**
```python
# apps/backend/apps/invoicing/services/document_service.py
class DocumentService:
    @staticmethod
    @transaction.atomic()
    def create_document(org_id: UUID, data: dict) -> InvoiceDocument:
        # Validation → Creation → Journal Entry → Return
```

**Thin View Pattern (Validated):**
```python
# apps/backend/apps/invoicing/views.py
class InvoiceDocumentListCreateView(APIView):
    @wrap_response
    def post(self, request, org_id: str) -> Response:
        serializer = InvoiceDocumentCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        document = DocumentService.create_document(org_id, serializer.validated_data)
        return Response(serializer.data, status=201)
```

**Decimal Utility (Validated):**
```python
# apps/backend/common/decimal_utils.py
def money(value) -> Decimal:
    if isinstance(value, float):
        raise ValueError("Float values are not allowed for monetary amounts")
    return Decimal(str(value)).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)
```

### 2.4 Competitive Analysis - Financial Module Patterns

**Research on Similar Platforms:**

| Platform | Banking Module Approach | LedgerSG Adaptation |
|----------|------------------------|---------------------|
| Xero | Bank rules + reconciliation | ✅ Bank transaction import |
| QuickBooks | Payment allocation | ✅ payment_allocation table |
| MYOB | Multi-currency payments | ✅ base_amount tracking |
| Stripe | Idempotency keys | ⚠️ Recommend adding |
| Plaid | Bank feed aggregation | ⚠️ Future enhancement |

**Key Insights:**
1. **Payment Allocation is Critical** - Must support partial payments across multiple invoices
2. **Reconciliation Workflow** - Bank transactions → Payment matching → GL posting
3. **Multi-Currency** - Exchange rate tracking at payment time (already in schema)
4. **Audit Requirements** - Every payment change must be logged (IRAS 5-year)

---

## Phase 3: Implementation Plan

### 3.1 Sequential Phases

| Phase | Objective | Deliverables | Validation | Effort |
|-------|-----------|--------------|------------|--------|
| **1** | Serializers & Validation | 8 serializers with full validation | Unit tests pass | 4 hours |
| **2** | Service Layer | 4 service classes with business logic | Integration tests | 6 hours |
| **3** | API Views | 5 validated endpoints replacing stubs | API tests pass | 4 hours |
| **4** | Journal Integration | Auto-posting payments to GL | Double-entry verified | 4 hours |
| **5** | Testing (TDD) | 20+ tests covering all scenarios | 100% critical paths | 6 hours |
| **6** | Security Hardening | Rate limiting, audit logging | Security scan pass | 2 hours |
| **7** | Documentation | API guide, runbook updated | Docs reviewed | 2 hours |

**Total Estimated Effort:** 28 hours (~3.5 days)

### 3.2 Integrated Checklist

#### Phase 1: Serializers & Validation
- [ ] `BankAccountSerializer` - All 15 fields validated
- [ ] `BankAccountCreateSerializer` - Write-specific validation
- [ ] `PaymentSerializer` - All 16 fields validated
- [ ] `PaymentReceiveSerializer` - Customer payment specific
- [ ] `PaymentMakeSerializer` - Supplier payment specific
- [ ] `PaymentAllocationSerializer` - Allocation validation
- [ ] `BankTransactionSerializer` - Import validation
- [ ] Custom validators for SG-specific fields (UEN, PayNow)

#### Phase 2: Service Layer
- [ ] `BankAccountService` - CRUD with GL linkage
- [ ] `PaymentService` - Create, validate, post
- [ ] `PaymentAllocationService` - Allocate, unallocate, reconcile
- [ ] `BankTransactionService` - Import, match, reconcile
- [ ] All services use `@transaction.atomic()`
- [ ] All services use `money()` utility
- [ ] All services trigger audit logging

#### Phase 3: API Views
- [ ] `BankAccountListCreateView` - GET/POST
- [ ] `BankAccountDetailView` - GET/PUT/PATCH/DELETE
- [ ] `PaymentListCreateView` - GET/POST
- [ ] `PaymentReceiveView` - POST (customer payments)
- [ ] `PaymentMakeView` - POST (supplier payments)
- [ ] `PaymentAllocateView` - POST (allocate to invoices)
- [ ] `BankTransactionListView` - GET (imported transactions)
- [ ] All views use `TenantContextMiddleware`
- [ ] All views have proper permission classes

#### Phase 4: Journal Integration
- [ ] Payment → Journal Entry auto-creation
- [ ] Bank Account GL linkage validation
- [ ] FX gain/loss calculation for multi-currency
- [ ] Reversal support for voided payments
- [ ] Double-entry balance validation

#### Phase 5: Testing (TDD)
- [ ] 12 Bank Account tests
- [ ] 15 Payment tests
- [ ] 8 Payment Allocation tests
- [ ] 5 Bank Transaction tests
- [ ] 5 Integration tests (full workflow)
- [ ] All tests use SQL-compliant fixtures
- [ ] TDD workflow (Red → Green → Refactor)

#### Phase 6: Security Hardening
- [ ] Rate limiting on payment endpoints
- [ ] Input sanitization on all fields
- [ ] SQL injection prevention verified
- [ ] Audit logging on all mutations
- [ ] Permission verification on all endpoints

#### Phase 7: Documentation
- [ ] API_CLI_Usage_Guide.md updated with banking examples
- [ ] README.md banking section updated
- [ ] Internal runbook for payment reconciliation
- [ ] Security remediation documented (SEC-001 closed)

### 3.3 Success Criteria

| Criterion | Target | Measurement |
|-----------|--------|-------------|
| Security Score | 100% (SEC-001 closed) | Security audit re-scan |
| Test Coverage | 90%+ on banking module | pytest --cov report |
| API Response Time | <200ms p95 | Load testing |
| Validation Errors | Clear, actionable messages | Error response review |
| Journal Integrity | 100% balanced entries | Double-entry verification |
| Audit Compliance | All mutations logged | audit.event_log query |
| IRAS Compliance | 5-year retention verified | Audit trail query |

### 3.4 Risk Assessment

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Schema drift (models vs SQL) | Medium | High | Continuous model validation |
| Payment double-posting | Low | Critical | Idempotency keys, unique constraints |
| FX calculation errors | Medium | High | Use money() utility, test edge cases |
| RLS bypass | Low | Critical | Test RLS policies explicitly |
| Performance on large datasets | Medium | Medium | Add indexes, pagination |
| Audit log bloat | Low | Low | Partition audit table by date |

---

## Phase 4: Technical Specification

### 4.1 File Structure

```
apps/backend/
├── apps/
│   └── banking/
│       ├── __init__.py
│       ├── models/
│       │   ├── __init__.py
│       │   ├── bank_account.py          # ✅ Already aligned
│       │   ├── payment.py               # ✅ Already aligned
│       │   ├── payment_allocation.py    # ✅ Already aligned
│       │   └── bank_transaction.py      # ⚠️ Need to verify
│       ├── serializers/
│       │   ├── __init__.py
│       │   ├── bank_account.py          # 🆕 NEW
│       │   ├── payment.py               # 🆕 NEW
│       │   └── allocation.py            # 🆕 NEW
│       ├── services/
│       │   ├── __init__.py
│       │   ├── bank_account_service.py  # 🆕 NEW
│       │   ├── payment_service.py       # 🆕 NEW
│       │   ├── allocation_service.py    # 🆕 NEW
│       │   └── reconciliation_service.py # 🆕 NEW
│       ├── views/
│       │   ├── __init__.py
│       │   ├── bank_account_views.py    # 🆕 Replace stubs
│       │   └── payment_views.py         # 🆕 Replace stubs
│       ├── urls/
│       │   └── __init__.py              # 🆕 Update routes
│       └── tests/
│           ├── __init__.py
│           ├── test_bank_account.py     # 🆕 TDD
│           ├── test_payment.py          # 🆕 TDD
│           ├── test_allocation.py       # 🆕 TDD
│           └── test_reconciliation.py   # 🆕 TDD
├── common/
│   └── validators/
│       └── singapore_validators.py      # 🆕 UEN, PayNow validation
```

### 4.2 Serializer Specifications

**BankAccountSerializer:**
```python
class BankAccountSerializer(serializers.ModelSerializer):
    account_number = serializers.CharField(
        max_length=30,
        validators=[UnicodeValidator()]
    )
    paynow_id = serializers.CharField(
        max_length=20,
        required=False,
        allow_blank=True
    )
    paynow_type = serializers.ChoiceField(
        choices=['UEN', 'MOBILE', 'NRIC'],
        required=False,
        allow_null=True
    )
    opening_balance = serializers.DecimalField(
        max_digits=10,
        decimal_places=4,
        validators=[MinValueValidator(Decimal('0'))]
    )
    
    class Meta:
        model = BankAccount
        fields = '__all__'
        read_only_fields = ['id', 'org_id', 'created_at', 'updated_at']
    
    def validate(self, data):
        # PayNow validation: if paynow_type set, paynow_id required
        if data.get('paynow_type') and not data.get('paynow_id'):
            raise serializers.ValidationError({
                'paynow_id': 'PayNow ID required when PayNow type is specified'
            })
        return data
```

**PaymentReceiveSerializer:**
```python
class PaymentReceiveSerializer(serializers.Serializer):
    contact_id = serializers.UUIDField()
    bank_account_id = serializers.UUIDField()
    payment_date = serializers.DateField()
    amount = serializers.DecimalField(
        max_digits=10,
        decimal_places=4,
        validators=[MinValueValidator(Decimal('0.0001'))]
    )
    currency = serializers.CharField(max_length=3, default='SGD')
    exchange_rate = serializers.DecimalField(
        max_digits=12,
        decimal_places=6,
        default=Decimal('1.000000'),
        validators=[MinValueValidator(Decimal('0.000001'))]
    )
    payment_method = serializers.ChoiceField(
        choices=[
            'BANK_TRANSFER', 'CHEQUE', 'CASH', 'PAYNOW',
            'CREDIT_CARD', 'GIRO', 'OTHER'
        ]
    )
    payment_reference = serializers.CharField(max_length=100, required=False)
    allocations = serializers.ListField(
        child=PaymentAllocationSerializer(),
        required=False
    )
    notes = serializers.CharField(required=False, allow_blank=True)
    
    def validate(self, data):
        # Validate contact is customer type
        contact = Contact.objects.get(id=data['contact_id'])
        if not contact.is_customer:
            raise serializers.ValidationError({
                'contact_id': 'Contact must be a customer for received payments'
            })
        
        # Validate bank account belongs to org
        bank_account = BankAccount.objects.get(id=data['bank_account_id'])
        org_id = self.context['org_id']
        if bank_account.org_id != org_id:
            raise serializers.ValidationError({
                'bank_account_id': 'Bank account does not belong to this organisation'
            })
        
        # Validate total allocations don't exceed payment amount
        if data.get('allocations'):
            total_allocated = sum(
                Decimal(str(a.get('allocated_amount', 0)))
                for a in data['allocations']
            )
            if total_allocated > Decimal(str(data['amount'])):
                raise serializers.ValidationError({
                    'allocations': 'Total allocations cannot exceed payment amount'
                })
        
        return data
```

### 4.3 Service Layer Specifications

**PaymentService.create_payment():**
```python
class PaymentService:
    @staticmethod
    @transaction.atomic()
    def create_payment(
        org_id: UUID,
        payment_type: str,
        data: dict,
        user: AppUser
    ) -> Payment:
        """
        Create payment with journal entry and audit logging.
        
        Args:
            org_id: Organisation UUID
            payment_type: 'RECEIVED' or 'MADE'
            data: Validated serializer data
            user: Creating user
            
        Returns:
            Payment object with journal entry linked
            
        Raises:
            ValidationError: If validation fails
            IntegrityError: If database constraints violated
        """
        # 1. Validate payment amount
        amount = money(data['amount'])
        
        # 2. Get exchange rate if multi-currency
        if data.get('currency') != 'SGD':
            exchange_rate = get_exchange_rate(
                org_id=org_id,
                currency=data['currency'],
                date=data['payment_date']
            )
            base_amount = money(amount * exchange_rate)
        else:
            exchange_rate = Decimal('1.000000')
            base_amount = amount
        
        # 3. Generate payment number
        payment_number = core.next_document_number(
            org_id=org_id,
            document_type=f'PAYMENT_{payment_type}'
        )
        
        # 4. Create payment record
        payment = Payment.objects.create(
            org_id=org_id,
            payment_type=payment_type,
            payment_number=payment_number,
            contact_id=data['contact_id'],
            bank_account_id=data['bank_account_id'],
            payment_date=data['payment_date'],
            amount=amount,
            base_amount=base_amount,
            currency=data.get('currency', 'SGD'),
            exchange_rate=exchange_rate,
            payment_method=data['payment_method'],
            payment_reference=data.get('payment_reference'),
            notes=data.get('notes'),
            # FX gain/loss calculated on allocation
            fx_gain_loss=Decimal('0.0000'),
        )
        
        # 5. Create journal entry
        journal_entry = JournalService.post_payment(
            org_id=org_id,
            payment=payment,
            user=user
        )
        payment.journal_entry_id = journal_entry.id
        payment.save(update_fields=['journal_entry_id'])
        
        # 6. Process allocations if provided
        if data.get('allocations'):
            PaymentAllocationService.allocate_payment(
                payment=payment,
                allocations=data['allocations'],
                user=user
            )
        
        # 7. Audit log
        AuditService.log_event(
            org_id=org_id,
            user=user,
            action='CREATE',
            entity_schema='banking',
            entity_table='payment',
            entity_id=payment.id,
            new_data=PaymentSerializer(payment).data
        )
        
        return payment
```

### 4.4 API Endpoint Specifications

| Method | Endpoint | Permission | Service | Test Count |
|--------|----------|------------|---------|------------|
| GET | `/api/v1/{orgId}/bank-accounts/` | IsOrgMember | BankAccountService.list() | 3 |
| POST | `/api/v1/{orgId}/bank-accounts/` | CanManageBanking | BankAccountService.create() | 4 |
| GET | `/api/v1/{orgId}/bank-accounts/{id}/` | IsOrgMember | BankAccountService.get() | 2 |
| PUT | `/api/v1/{orgId}/bank-accounts/{id}/` | CanManageBanking | BankAccountService.update() | 3 |
| DELETE | `/api/v1/{orgId}/bank-accounts/{id}/` | CanManageBanking | BankAccountService.delete() | 2 |
| GET | `/api/v1/{orgId}/payments/` | IsOrgMember | PaymentService.list() | 3 |
| POST | `/api/v1/{orgId}/payments/receive/` | CanManageBanking | PaymentService.create_payment('RECEIVED') | 5 |
| POST | `/api/v1/{orgId}/payments/make/` | CanManageBanking | PaymentService.create_payment('MADE') | 5 |
| POST | `/api/v1/{orgId}/payments/allocate/` | CanManageBanking | PaymentAllocationService.allocate() | 4 |
| GET | `/api/v1/{orgId}/bank-transactions/` | IsOrgMember | BankTransactionService.list() | 2 |
| POST | `/api/v1/{orgId}/bank-transactions/import/` | CanManageBanking | BankTransactionService.import_csv() | 3 |
| POST | `/api/v1/{orgId}/bank-transactions/{id}/reconcile/` | CanManageBanking | BankTransactionService.reconcile() | 4 |

### 4.5 Test Specifications (TDD)

**Test File Structure:**
```python
# apps/backend/apps/banking/tests/test_payment.py

class TestPaymentService:
    """TDD tests for PaymentService - Red → Green → Refactor"""
    
    def test_create_received_payment_success(self):
        """Red: Test fails initially, Green: Implement, Refactor: Clean up"""
        pass
    
    def test_create_payment_invalid_amount(self):
        """Negative amount should raise ValidationError"""
        pass
    
    def test_create_payment_contact_not_customer(self):
        """Customer payment to supplier contact should fail"""
        pass
    
    def test_create_payment_bank_account_wrong_org(self):
        """Cross-org bank account access should fail (RLS)"""
        pass
    
    def test_create_payment_with_allocations(self):
        """Payment with invoice allocations should create allocation records"""
        pass
    
    def test_create_payment_journal_entry_created(self):
        """Payment creation should auto-create journal entry"""
        pass
    
    def test_create_payment_audit_logged(self):
        """Payment creation should be logged in audit.event_log"""
        pass
    
    def test_void_payment_reverses_journal(self):
        """Voiding payment should create reversal journal entry"""
        pass
    
    def test_multi_currency_payment_fx_calculated(self):
        """Multi-currency payment should calculate FX gain/loss"""
        pass
    
    def test_payment_number_unique_per_org(self):
        """Payment numbers should be unique per organisation"""
        pass
```

---

## Phase 5: Validation Checkpoint

### 5.1 Pre-Implementation Validation

Before writing any code, confirm:

- [ ] **Schema Alignment Verified** - All 4 banking tables have corresponding Django models
- [ ] **Model Import Test Passed** - `from apps.banking.models import *` works without errors
- [ ] **Existing Tests Reviewed** - No conflicting test expectations
- [ ] **Security Requirements Understood** - SEC-001 remediation scope clear
- [ ] **IRAS Requirements Documented** - 5-year audit retention, payment records
- [ ] **Stakeholder Approval** - Plan reviewed and approved

### 5.2 Implementation Validation Gates

| Gate | Criteria | Validation Method |
|------|----------|-------------------|
| Gate 1 | Serializers complete | Unit tests pass (100%) |
| Gate 2 | Services complete | Integration tests pass |
| Gate 3 | Views complete | API tests pass |
| Gate 4 | Journal integration | Double-entry balance verified |
| Gate 5 | Security hardened | Security scan passes |
| Gate 6 | Documentation complete | Docs reviewed |
| Gate 7 | SEC-001 closed | Audit re-scan confirms |

### 5.3 Rollback Plan

If implementation encounters critical issues:

1. **Revert Code Changes** - Git revert to pre-implementation commit
2. **Restore Database** - `psql -f database_schema.sql` if schema modified
3. **Disable Endpoints** - Comment out new URL routes temporarily
4. **Document Issues** - Record blockers in ACCOMPLISHMENTS.md
5. **Replan** - Return to Phase 1 with lessons learned

---

## Phase 6: Execution Timeline

### 6.1 Day-by-Day Breakdown

| Day | Focus | Deliverables | Validation |
|-----|-------|--------------|------------|
| **Day 1** | Serializers | 8 serializers + validators | Unit tests pass |
| **Day 2** | Services | 4 service classes | Integration tests |
| **Day 3** | Views + URLs | 12 endpoints | API tests pass |
| **Day 4** | Journal + Audit | GL posting, audit logging | Double-entry verified |
| **Day 5** | Testing + Docs | 40+ tests, docs updated | Coverage report |

### 6.2 Milestone Checkpoints

| Milestone | Target Date | Success Criteria |
|-----------|-------------|------------------|
| Serializers Complete | Day 1 EOD | All 8 serializers pass unit tests |
| Services Complete | Day 2 EOD | All 4 services pass integration tests |
| API Endpoints Live | Day 3 EOD | All 12 endpoints respond correctly |
| Journal Integration | Day 4 EOD | All payments create balanced entries |
| SEC-001 Closed | Day 5 EOD | Security audit confirms remediation |

---

## Phase 7: Risk Mitigation

### 7.1 Technical Risks

| Risk | Probability | Impact | Mitigation Strategy |
|------|-------------|--------|---------------------|
| Model-SQL drift | Medium | High | Run model validation after each change |
| RLS policy bypass | Low | Critical | Test RLS explicitly in every test |
| Payment double-posting | Low | Critical | Unique constraints + idempotency keys |
| FX calculation errors | Medium | High | Use money() utility, test edge cases |
| Performance degradation | Medium | Medium | Add indexes, implement pagination |

### 7.2 Security Risks

| Risk | Probability | Impact | Mitigation Strategy |
|------|-------------|--------|---------------------|
| Input validation bypass | Low | High | Serializer validation + service validation |
| Auth bypass | Low | Critical | Permission classes on all views |
| Audit log tampering | Low | Critical | Append-only table, no UPDATE/DELETE grants |
| Rate limit bypass | Medium | Medium | Implement django-ratelimit |

---

## ✅ Validation Checkpoint - Ready to Proceed

**Before beginning with the implementation, confirm:**

1. ✅ The file structure and component breakdown
2. ✅ Adopt Test-Driven Development (TDD) approch/methodology TDD approach for all banking services
3. ✅ Ensure SEC-001 security remediation as primary priority
4. ✅ Ensure 40+ test target for comprehensive coverage

