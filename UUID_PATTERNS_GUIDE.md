# UUID Handling Patterns Guide

## Overview

This guide documents the correct patterns for handling UUID parameters in LedgerSG Django views, particularly focusing on URL path parameters.

## The Issue: Django URL Path Converters

Django's URL path converters automatically convert URL parameters to the appropriate Python types BEFORE they reach the view.

```python
# urls.py
path("api/v1/<uuid:org_id>/accounts/", AccountListCreateView.as_view())

# The <uuid:org_id> converter automatically converts the URL parameter
# from a string like "550e8400-e29b-41d4-a716-446655440000"
# to a uuid.UUID object
```

## Common Mistake

**Wrong: Attempting to convert an already-converted UUID**

```python
def get(self, request, org_id: str):  # org_id is actually UUID, not str
    from uuid import UUID
    
    # This will FAIL with: 'UUID' object has no attribute 'replace'
    service.get_account(UUID(org_id), UUID(account_id))
```

**Why it fails:**
- Django passes `org_id` as a `uuid.UUID` object (not a string)
- Calling `UUID()` on a UUID object fails
- Python's UUID constructor expects a string, bytes, or another UUID constructor format

## Correct Pattern

**Right: Use the parameter directly**

```python
def get(self, request, org_id: str):  # type annotation is wrong, but harmless
    # org_id is already a UUID object from Django's URL converter
    service.get_account(org_id, account_id)
```

## Safe Conversion Patterns

### 1. URL Path Parameters (Already UUIDs)

**DON'T convert:**
```python
# ❌ WRONG
def get(self, request, org_id: str, account_id: str):
    service.get_account(UUID(org_id), UUID(account_id))  # FAILS

# ✅ RIGHT
def get(self, request, org_id: str, account_id: str):
    service.get_account(org_id, account_id)  # Works!
```

### 2. Query Parameters (Always Strings)

**DO convert:**
```python
# ✅ RIGHT
fiscal_year_id = request.query_params.get("fiscal_year_id")
if fiscal_year_id:
    fiscal_year_id = UUID(fiscal_year_id)  # String → UUID
```

### 3. Request Body Data (Always Strings)

**DO convert:**
```python
# ✅ RIGHT
contact_id = request.data.get("contact_id")
if contact_id:
    contact_id = UUID(str(contact_id))  # String → UUID
```

### 4. Defensive Pattern (Safe Either Way)

If you're unsure or working with code that might receive strings OR UUIDs:

```python
# ✅ SAFE - handles both cases
def ensure_uuid(value) -> UUID:
    """Ensure value is a UUID, converting from string if necessary."""
    if isinstance(value, UUID):
        return value
    return UUID(str(value))

# Usage
org_uuid = ensure_uuid(org_id)
```

## Files Fixed

| File | Occurrences | Status |
|------|-------------|--------|
| `apps/banking/views.py` | Multiple | ✅ Fixed |
| `apps/gst/views.py` | 13 | ✅ Fixed |
| `apps/journal/views.py` | 7 | ✅ Fixed |
| `apps/coa/views.py` | 8 | ✅ Fixed |

## Testing

To verify your changes:

```bash
# Run the specific module tests
cd apps/backend
source /opt/venv/bin/activate
pytest apps/coa/tests/ -v --reuse-db --no-migrations

# Run RLS context tests (validate UUID handling)
pytest tests/middleware/test_rls_context.py -v --reuse-db --no-migrations
```

## Migration Checklist

When updating views:

- [ ] Identify if parameter comes from URL path (don't convert) or query/body (convert)
- [ ] Remove `UUID(org_id)` for URL path parameters
- [ ] Keep `UUID(param)` for query parameters and request body
- [ ] Update type annotations to reflect actual types (optional but recommended)
- [ ] Run tests to verify

## Error Messages

If you see this error:
```
'UUID' object has no attribute 'replace'
```

**Cause:** You're calling `UUID()` on an already-converted UUID object.

**Fix:** Remove the `UUID()` wrapper for URL path parameters.

## Related Documentation

- [Django URL Dispatcher](https://docs.djangoproject.com/en/5.0/topics/http/urls/)
- [Python UUID Module](https://docs.python.org/3/library/uuid.html)
- `API_CLI_Usage_Guide.md` - Troubleshooting section

---

*Created: 2026-03-08*
*Applies to: LedgerSG Backend v0.3.3*
