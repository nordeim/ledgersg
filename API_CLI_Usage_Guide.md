# LedgerSG API CLI Usage Guide

> **Direct Backend API Interaction via Command Line**
> **For AI Agents and Advanced Users**
> **Version**: 2.3.0
> **Last Updated**: 2026-03-14
> **Status**: Production Ready ✅ (SEC-001/002/003, E2E Testing Complete, API Contracts Fixed)

---

## 🎉 Recent Milestone: E2E Testing Initiative Complete ✅ COMPLETE (2026-03-14)

### Summary

Successfully executed **15-phase comprehensive E2E test suite** covering the complete "Lakshmi's Kitchen" workflow from authentication through financial reporting. Critical **API contract mismatch bug fixed** affecting Banking, Invoicing, GST, COA, and Journal modules.

### Key Knowledge & Fixes (E2E Testing 2026-03-14)

| Category | Finding / Issue | Resolution / Knowledge |
|:---|:---|:---|
| **API Contract** | Backend returned arrays `[]`, frontend expected `{results, count}`. | **FIXED**: 9 list views updated to return paginated format. Banking page now functional. |
| **Session Persistence** | HttpOnly cookies break automation tools (agent-browser, Playwright). | **SOLUTION**: Use Hybrid API + UI approach. API for auth/data, UI for verification only. |
| **Journal Endpoint** | `/journal/entries/` returns 404, actual URL is `/journal-entries/entries/`. | **NOTE**: URL registered as `journal-entries/` not `journal/` in root config. |
| **List Endpoints** | All list endpoints now return `{results: [...], count: n}`. | **UPDATED**: Bank accounts, payments, transactions, invoices, contacts, tax codes, accounts, journal entries. |

### Previous Milestone: SMB Workflow Hardening ✅ COMPLETE (2026-03-10)

Successfully completed full E2E validation for **Lakshmi's Kitchen** (12-month Corporate Cycle) and **ABC Trading** (Sole Prop Smoke Test). This involved hardening the `JournalService` posting engine and ensuring models match the `database_schema.sql` exactly.

### Key Knowledge & Fixes (Workflow 1 & 2)

| Category | Finding / Issue | Resolution / Knowledge |
|:---|:---|:---|
| **Ghost Columns** | Model inheritance adding `created_at` to tables without them. | Switched `Peppol` models to inherit from `models.Model` to match SQL exactly. |
| **Logic Filter** | `is_voided` filter in `JournalService` caused 500 errors. | Removed invalid filter; posting engine now handles lines via the document's approved state. |
| **Side Effects** | Payments alone don't show revenue. | **MANDATORY**: You MUST call `/approve/` on an invoice to trigger the Revenue/AR journal entries. |

---

## Troubleshooting (Updated)

### "ProgrammingError: column organisation_peppol_settings.created_at does not exist"
**Status**: ✅ **FIXED** (2026-03-10)
**Cause**: The model was incorrectly inheriting from a base class that adds timestamp fields not present in the SQL schema.
**Solution**: Ensure models match `database_schema.sql` exactly.

### "FieldError: Cannot resolve keyword 'is_voided' into field"
**Status**: ✅ **FIXED** (2026-03-10)
**Cause**: Service layer code was trying to filter by a field that doesn't exist in the database table.
**Solution**: Refined `JournalService` to query lines directly via the parent document.

### API Contract Mismatch: List Endpoints Return Arrays
**Status**: ✅ **FIXED** (2026-03-14)
**Cause**: Backend list views returned `serializer.data` (array), but frontend expected `{results, count}` (paginated object).
**Impact**: Banking page completely broken with `TypeError: Cannot read properties of undefined (reading 'map')`
**Solution**: Updated 9 list views to return paginated format:
- ✅ `BankAccountListView` → `GET /api/v1/{orgId}/banking/bank-accounts/`
- ✅ `PaymentListView` → `GET /api/v1/{orgId}/banking/payments/`
- ✅ `BankTransactionListView` → `GET /api/v1/{orgId}/banking/bank-transactions/`
- ✅ `ContactListView` → `GET /api/v1/{orgId}/invoicing/contacts/`
- ✅ `InvoiceDocumentListView` → `GET /api/v1/{orgId}/invoicing/documents/`
- ✅ `TaxCodeListView` → `GET /api/v1/{orgId}/gst/tax-codes/`
- ✅ `GSTReturnListView` → `GET /api/v1/{orgId}/gst/returns/`
- ✅ `AccountListView` → `GET /api/v1/{orgId}/accounts/`
- ✅ `JournalEntryListView` → `GET /api/v1/{orgId}/journal-entries/entries/`

**Response Format** (all list endpoints now):
```json
{
  "results": [...],
  "count": 42
}
```

### Session Not Persisting in E2E Tests
**Status**: ⚠️ **KNOWN LIMITATION** (2026-03-14)
**Cause**: HttpOnly cookies not sent by automation tools (agent-browser, Playwright). Access tokens in memory lost on navigation.
**Impact**: Redirects to login after every page navigation in E2E tests.
**Solution**: Use **Hybrid API + UI approach**:
```bash
# 1. Authenticate via API
curl -X POST http://localhost:8000/api/v1/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.com", "password": "password"}'
# Returns: {"tokens": {"access": "...", "refresh": "..."}}

# 2. Use access token for all API calls
curl -H "Authorization: Bearer $ACCESS_TOKEN" \
  http://localhost:8000/api/v1/{orgId}/banking/bank-accounts/

# 3. Use UI only for screenshots/visual verification
# (Playwright with hybrid approach)
```

### Journal Entries Endpoint URL
**Status**: ⚠️ **CLARIFIED** (2026-03-14)
**Issue**: `/api/v1/{orgId}/journal/entries/` returns 404
**Actual URL**: `/api/v1/{orgId}/journal-entries/entries/`
**Cause**: Root URL config mounts journal URLs at `journal-entries/` not `journal/`:
```python
# config/urls.py
org_scoped_urlpatterns.append(path("journal-entries/", include("apps.journal.urls")))
```
**Correct CLI**:
```bash
# ❌ Incorrect
curl http://localhost:8000/api/v1/{orgId}/journal/entries/

# ✅ Correct
curl http://localhost:8000/api/v1/{orgId}/journal-entries/entries/
```

---

## CLI Examples

### 1. Approve an Invoice (Mandatory for GL)
```bash
curl -X POST "http://localhost:8000/api/v1/{orgId}/invoicing/documents/{id}/approve/" \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```

### 2. Verify Ledger Posting
```bash
# Check if journal entries were created
curl -X GET "http://localhost:8000/api/v1/{orgId}/journal-entries/entries/" \
  -H "Authorization: Bearer $ACCESS_TOKEN" | jq '.data'
```

---

**End of Guide**
