# LedgerSG API CLI Usage Guide

> **Direct Backend API Interaction via Command Line**
> **For AI Agents and Advanced Users**
> **Version**: 2.6.0
> **Last Updated**: 2026-11-24 (P13 — contracts unchanged; the P13 backend fixes verified: sub-cent GST now rounds to IRAS 2dp, InvoiceNow missing-document 404s)
> **Status**: Production Ready ✅ (SEC-001/002/003, E2E Testing Complete, API Contracts Fixed)

---

## 2026-11-23 Live Re-Verification (P12)

Every documented contract below was re-exercised against the running stack
(post-P11 remediation) before this update:

| Contract | Result |
|:---|:---|
| `POST /api/v1/auth/login/` → `{tokens: {access, refresh}}` | ✅ Verified (live curl) |
| All 9 documented list endpoints → `{results, count}` envelope | ✅ Verified — 9/9 return HTTP 200 with the paginated object (banking×3, contacts, documents, tax-codes, returns, accounts, journal entries) |
| Journal mount: `/journal/entries/` 404 vs `/journal-entries/entries/` 200 | ✅ Verified (both directions) |
| `POST /documents/{id}/approve/` → posts the GL journal | ✅ Verified (P11 live gate); **credit notes post REVERSED entries** — AR credit, revenue/GST debit (P11/C-1 fix) |
| F5 computation | ✅ Net of credit notes, posted-types only (P11/H-3) — quotes no longer pollute Box 1 |
| Dashboard metrics | ✅ `GET /api/v1/{orgId}/reports/dashboard/metrics/` (the H-4 surface; `gst_payable` non-zero on real data) |
| Org context for CLI flows | ✅ `GET /api/v1/auth/organisations/` returns the membership list — take `[i].org.id`; note it is a bare array at the top level (no `{results, count}` envelope on this auth route) |

### Current Test Metrics (post-P11/P12)

| Suite | Count | Status |
|:---|:---|:---|
| Backend Tests | 750 passed, 5 skipped, 0 failed (755 collected) | ✅ 100% of registered |
| Frontend vitest | 530 passed (518 P12 + 12 P13) | ✅ |
| Frontend e2e | 11 always-green + 29 backend-gated; 40/40 live under `test:e2e:full` | ✅ |

### 2026-11-24 P13 verification addendum

The P13 backend sprint changed no documented request/response contract;
the behavioral deltas verified live this session:

| Contract | P13 delta |
|:---|:---|
| `POST /gst/calculate/` (and every line-GST path) | Sub-cent bases now round to IRAS 2 decimal places: `100.05 × 0.09 → gst_amount "9.00"` (was the 3-dp `"9.005"`) — verified live via curl |
| `POST /documents/{id}/send-invoicenow/` + `GET /documents/{id}/invoicenow-status/` | A missing document now returns the typed `404 {"error":{"code":"not_found"}}` envelope (was a raw 500) |
| Any unhandled server error | Still the `500 {"error":{"code":"internal_error"}}` envelope, but the request transaction now ROLLS BACK (no partial writes) |
| Health endpoints | The 503 body carries a generic message (no raw DB error strings) |

---

## 🎉 Recent Milestone: API Contract Standardization & 500 Error Investigation ✅ COMPLETE (2026-03-15)

### Summary

1. **API Contract Standardization**: 9 endpoints now return standardized `{results, count}` format
2. **500 Error Investigation**: Debunked myth - production API works correctly (verified with direct testing)

### Key Knowledge & Fixes (2026-03-15)

| Category | Finding / Issue | Resolution / Knowledge |
|:---|:---|:---|
| **API Contract** | Backend returned arrays `[]`, frontend expected `{results, count}`. | **FIXED**: 9 list views updated to return paginated format. |
| **500 Error Myth** | Documentation claimed "500 errors in journal/invoice" | **DEBUNKED**: Production API works correctly - 403s from test fixtures only |
| **Test Fixture Issue** | 67 tests fail with "User not authorized" | pytest isolation issue, not production bug |
| **Session Persistence** | HttpOnly cookies break automation tools. | **SOLUTION**: Hybrid API + UI approach. |

### Test Metrics (as of 2026-03-15 — superseded by the 2026-11-23 block above)

| Suite | Count | Status |
|:---|:---|:---|
| Backend Tests | 468 collected, 393 passing | ✅ 84% (historical) |
| Frontend Tests | 321 passing | ✅ 100% (historical) |
| API Contract Tests | 8 passing | ✅ 100% |

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
**Status**: ✅ **RESOLVED FOR PLAYWRIGHT** (2026-11-23)
**Cause**: HttpOnly refresh cookies are invisible to JS-based automation drivers.
**Resolution**: the Playwright e2e suite authenticates through the UI and the
browser context carries the HttpOnly cookie session across reloads and
client-side navigation (P4/E-1 — the `session.spec.ts` specs assert the
reload-persistence contract and run green under `test:e2e:full`). For
pure-CLI drivers without a cookie jar, the hybrid API approach below still
applies:
```bash
# 1. Authenticate via API
curl -X POST http://localhost:8000/api/v1/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.sg", "password": "password"}'
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

**P11/C-1 direction truth**: approving a **credit note** posts the journal
REVERSED — the AR line is a CREDIT (customer receivable shrinks), the revenue
and GST lines are DEBITS. Approving an invoice posts the normal direction.

### 2. Verify Ledger Posting
```bash
# Check if journal entries were created
curl -X GET "http://localhost:8000/api/v1/{orgId}/journal-entries/entries/" \
  -H "Authorization: Bearer $ACCESS_TOKEN" | jq '.results'
```

### 3. Dashboard Metrics (the H-4 surface)
```bash
curl "http://localhost:8000/api/v1/{orgId}/reports/dashboard/metrics/" \
  -H "Authorization: Bearer $ACCESS_TOKEN"
# gst_payable is computed from document lines (non-zero on real data)
```

---

**End of Guide**
