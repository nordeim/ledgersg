# LedgerSG API CLI Usage Guide

> **Direct Backend API Interaction via Command Line**
> **For AI Agents and Advanced Users**
> **Version**: 2.1.0
> **Last Updated**: 2026-03-10
> **Status**: Production Ready ✅ (SEC-001/002/003, Phase B, Phase 5.5, RLS Fix, SMB Workflow Complete)

---

## 🎉 Recent Milestone: SMB Workflow Remediation ✅ COMPLETE (2026-03-10)

### Summary

Successfully completed a full end-to-end validation of the Singapore SMB accounting workflow. This involved fixing several critical gaps in the service layer, aligning serializers with the SQL-First schema, and implementing the core double-entry posting engine.

### Key Knowledge & Fixes

| Category | Finding / Issue | Resolution / Knowledge |
|:---|:---|:---|
| **Accounting Logic** | Journal Posting was stubbed. | Implemented automatic ledger posting for Invoices and Payments. |
| **Data Consistency** | Field mismatches (e.g., `is_bank_account` vs `is_bank`). | Standardized all serializers to match the `database_schema.sql` exactly. |
| **Response Parsing** | List endpoints wrap results in a `data` key. | **CRITICAL**: Use `jq '.data'` when parsing list responses (e.g., Accounts, Tax Codes). |
| **DB Integrity** | `contact_type` constraint violations. | `ContactService` now auto-calculates type from boolean flags. |
| **Serialization** | UUID objects caused 500 errors in JSON. | Fixed `DecimalSafeJSONEncoder` to support `UUID` and `datetime`. |
| **Importing** | CSV headers were case-sensitive. | Improved `import_csv` service to normalize headers (mixed-case support). |

---

## ⚠️ Important Notice

**This guide is for direct API interaction via CLI, bypassing the frontend GUI.**

### When to Use This Guide
- ✅ AI agents automating tasks
- ✅ Testing API endpoints directly
- ✅ Bulk data operations
- ✅ CI/CD pipeline integration
- ✅ Debugging frontend-backend issues

---

## Table of Contents

1. [Authentication](#authentication)
2. [Organization Context](#organization-context)
3. [Common API Patterns](#common-api-patterns)
4. [API Endpoints Reference](#api-endpoints-reference)
5. [CLI Examples](#cli-examples)
6. [Error Handling](#error-handling)
7. [Limitations & Gotchas](#limitations--gotchas)
8. [Advanced Usage](#advanced-usage)

---

## Authentication

### Overview

LedgerSG uses **JWT Authentication** with:
- **Access Token**: 15-minute expiration (stored in memory)
- **Refresh Token**: 7-day expiration (HttpOnly cookie)

### Login

**Endpoint**: `POST /api/v1/auth/login/`

**Request:**
```bash
curl -X POST http://localhost:8000/api/v1/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "secure_password"
  }'
```

**Response:**
```json
{
  "user": { "id": "...", "email": "..." },
  "tokens": {
    "access": "eyJ...",
    "refresh": "...",
    "access_expires": "2026-03-10T10:15:00Z"
  }
}
```

---

## Organization Context

### CRITICAL: All Org-Scoped Requests Require org_id

**URL Pattern**: `/api/v1/{orgId}/...`

### Getting Your Organizations

**Endpoint**: `GET /api/v1/organisations/`

**Request:**
```bash
curl -X GET http://localhost:8000/api/v1/organisations/ \
  -H "Authorization: Bearer $LEDGERSG_ACCESS"
```

**Response (List Wrapper):**
```json
{
  "data": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440001",
      "name": "My Company Pte Ltd"
    }
  ],
  "count": 1
}
```

---

## Common API Patterns

### Standard Headers

```bash
-H "Authorization: Bearer $LEDGERSG_ACCESS" \
-H "Content-Type: application/json"
```

### Response Format (The "Data" Wrapper)

LedgerSG uses a consistent wrapper for list responses and some detail responses.

**List Response:**
```json
{
  "data": [...],
  "count": 10,
  "next": null,
  "previous": null
}
```

**Error Response:**
```json
{
  "error": {
    "code": "error_code",
    "message": "Human-readable error message"
  }
}
```

---

## API Endpoints Reference

### Chart of Accounts (CoA)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/{orgId}/accounts/` | List accounts (Use `?code=1100` for filtering) |
| GET | `/api/v1/{orgId}/accounts/{id}/` | Get account details |

### Invoicing

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/{orgId}/invoicing/contacts/` | List contacts |
| POST | `/api/v1/{orgId}/invoicing/documents/` | Create invoice/bill |
| POST | `/api/v1/{orgId}/invoicing/documents/{id}/approve/` | **Approving posts to GL** |

### Banking

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/{orgId}/banking/bank-accounts/` | Create bank account |
| POST | `/api/v1/{orgId}/banking/payments/receive/` | **Receiving posts to GL** |
| POST | `/api/v1/{orgId}/banking/bank-transactions/import/` | Import CSV statement |

---

## Troubleshooting

### "TypeError: Object of type UUID is not JSON serializable"
**Status**: ✅ FIXED (2026-03-10)
**Cause**: Earlier versions of the JSON encoder didn't handle native Python UUID or datetime objects.
**Solution**: Ensure you are running the latest codebase where `common/renderers.py` has been updated.

### "gl_account: This field is required" (Bank Account)
**Cause**: Sending `gl_account_id` instead of `gl_account`.
**Solution**: Use the key `gl_account` in the POST body for bank account creation.

### "IntegrityError: contact_type_check"
**Cause**: Creating contacts with missing or empty `contact_type`.
**Solution**: The service now auto-calculates this based on `is_customer` and `is_supplier` flags.

### "Empty Reports / Zero Revenue"
**Cause**: Invoices were created as DRAFT but not APPROVED.
**Solution**: You MUST call the `/approve/` endpoint to trigger the double-entry journal posting. Dashboard metrics only query POSTED entries.

### CSV Import Failures
**Cause**: Missing headers or mixed case (e.g., "Date" vs "date").
**Solution**: The importer now normalizes headers to lowercase. Ensure your CSV has at least `date`, `amount`, and `description`.

---

## Limitations & Gotchas

1. **Decimal Precision**: All money values MUST be strings with 4 decimal places (e.g., `"100.0000"`).
2. **Rate Limiting**: If running heavy automated tests, you may hit 429 errors. Set `RATELIMIT_ENABLE=False` in `base.py` for local testing.
3. **Filtering**: When filtering accounts by code, use `GET /accounts/?code=1100`. The response is a list, so use `jq -r '.data[0].id'`.

---

**End of Guide**
