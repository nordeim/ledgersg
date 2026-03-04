# Redis Caching for Dashboard Data - Implementation Plan

**Date:** 2026-03-04  
**Status:** In Progress  
**Approach:** Test-Driven Development (TDD)  
**Priority:** High (from INTEGRATION_GAPS_PHASE3_SUMMARY.md)

---

## Executive Summary

Implement Redis caching for dashboard data with a 5-minute TTL to improve performance and reduce database load. The dashboard data is computed from multiple database queries and doesn't change frequently, making it an ideal candidate for caching.

---

## Requirements Analysis

### Current State
- **DashboardService**: Computes dashboard data from multiple database queries
- **Cache Backend**: Redis already configured and running (ledgersg_redis container on port 6379)
- **TTL Requirement**: 5 minutes (300 seconds)
- **Cache Key Pattern**: `dashboard:{org_id}`

### Target State
- Dashboard data cached with 5-minute TTL
- Cache invalidated on relevant data changes (payments, invoices, journal entries)
- Performance improvement: <500ms for cache hits vs database queries

---

## Implementation Plan (TDD)

### Phase 1: RED - Write Failing Tests

**Step 1.1: Cache Key Generation Tests**
```python
def test_cache_key_format(self, test_org):
    """Test cache key follows expected pattern."""
    service = DashboardService()
    cache_key = service._get_cache_key(str(test_org.id))
    assert cache_key == f"dashboard:{test_org.id}"

def test_cache_key_consistency(self, test_org):
    """Test cache key is consistent for same org_id."""
    service = DashboardService()
    key1 = service._get_cache_key(str(test_org.id))
    key2 = service._get_cache_key(str(test_org.id))
    assert key1 == key2
```

**Step 1.2: Cache Read/Write Tests**
```python
def test_get_cached_data_returns_cached_value(self, test_org):
    """Test retrieving cached data returns stored value."""
    service = DashboardService()
    cache_key = service._get_cache_key(str(test_org.id))
    cached_data = {"gst_payable": "100.00", "cached": True}
    cache.set(cache_key, cached_data, timeout=300)
    result = service.get_dashboard_data(str(test_org.id))
    assert result["cached"] is True

def test_get_dashboard_data_caches_result(self, test_org):
    """Test first call caches the result."""
    service = DashboardService()
    org_id = str(test_org.id)
    # First call should compute and cache
    result1 = service.get_dashboard_data(org_id)
    # Verify data is in cache
    cache_key = service._get_cache_key(org_id)
    cached = cache.get(cache_key)
    assert cached is not None
    assert cached["gst_payable"] == result1["gst_payable"]
```

**Step 1.3: Cache TTL Tests**
```python
def test_cache_ttl_is_300_seconds(self, test_org):
    """Test cache TTL is 5 minutes."""
    service = DashboardService()
    org_id = str(test_org.id)
    service.get_dashboard_data(org_id)
    cache_key = service._get_cache_key(org_id)
    # Check TTL is approximately 300 seconds
    ttl = cache.ttl(cache_key)
    assert 295 <= ttl <= 300  # Allow small variance
```

**Step 1.4: Cache Miss Tests**
```python
def test_cache_miss_computes_from_database(self, test_org):
    """Test cache miss queries database and caches result."""
    service = DashboardService()
    org_id = str(test_org.id)
    # Ensure cache is empty
    cache_key = service._get_cache_key(org_id)
    cache.delete(cache_key)
    # Should compute from DB and cache
    result = service.get_dashboard_data(org_id)
    # Verify data was cached
    cached = cache.get(cache_key)
    assert cached is not None
    assert cached["gst_payable"] == result["gst_payable"]
```

---

### Phase 2: GREEN - Implement Minimal Code

**Step 2.1: Add Cache Key Helper Method**
```python
def _get_cache_key(self, org_id: str) -> str:
    """Generate cache key for dashboard data."""
    return f"dashboard:{org_id}"
```

**Step 2.2: Modify get_dashboard_data to Use Cache**
```python
def get_dashboard_data(self, org_id: str) -> dict:
    """Get dashboard data with 5-minute Redis caching."""
    cache_key = self._get_cache_key(org_id)
    
    # Try to get from cache
    cached_data = cache.get(cache_key)
    if cached_data is not None:
        logger.debug(f"Cache hit for dashboard:{org_id}")
        return cached_data
    
    # Compute from database
    logger.debug(f"Cache miss for dashboard:{org_id}")
    data = self._compute_dashboard_data(org_id)
    
    # Cache for 5 minutes
    cache.set(cache_key, data, timeout=300)
    
    return data
```

**Step 2.3: Extract Computation Logic**
```python
def _compute_dashboard_data(self, org_id: str) -> dict:
    """Compute dashboard data from database (original logic)."""
    # Move existing get_dashboard_data logic here
    ...
```

---

### Phase 3: REFACTOR - Optimize and Add Features

**Step 3.1: Add Cache Invalidation**
```python
def invalidate_dashboard_cache(self, org_id: str) -> None:
    """Invalidate dashboard cache for organization."""
    cache_key = self._get_cache_key(org_id)
    cache.delete(cache_key)
    logger.info(f"Invalidated dashboard cache for org:{org_id}")
```

**Step 3.2: Add Cache Warming**
```python
def warm_dashboard_cache(self, org_id: str) -> dict:
    """Pre-compute and cache dashboard data."""
    data = self._compute_dashboard_data(org_id)
    cache_key = self._get_cache_key(org_id)
    cache.set(cache_key, data, timeout=300)
    return data
```

**Step 3.3: Add Metrics Logging**
```python
def get_dashboard_data(self, org_id: str) -> dict:
    """Get dashboard data with cache metrics."""
    cache_key = self._get_cache_key(org_id)
    
    cached_data = cache.get(cache_key)
    if cached_data is not None:
        logger.info(f"Dashboard cache hit for org:{org_id}")
        return cached_data
    
    logger.info(f"Dashboard cache miss for org:{org_id}")
    data = self._compute_dashboard_data(org_id)
    cache.set(cache_key, data, timeout=300)
    return data
```

---

## Code Changes

### Files to Modify

1. **`apps/reporting/services/dashboard_service.py`**
   - Add `_get_cache_key()` method
   - Add `_compute_dashboard_data()` method (extract from existing)
   - Modify `get_dashboard_data()` to use cache
   - Add cache invalidation methods

2. **`apps/reporting/tests/test_dashboard_cache.py`** (NEW)
   - All TDD tests for caching
   - Cache TTL verification
   - Cache miss/hit scenarios
   - Invalidation tests

3. **`apps/reporting/views.py`**
   - Optional: Add cache invalidation on write operations

---

## Dependencies

- Django cache framework (already configured)
- Redis cache backend (already running)
- No new packages needed

---

## Testing Commands

```bash
# Initialize test database
export PGPASSWORD=ledgersg_secret_to_change
dropdb -h localhost -U ledgersg test_ledgersg_dev 2>/dev/null
createdb -h localhost -U ledgersg test_ledgersg_dev
psql -h localhost -U ledgersg -d test_ledgersg_dev -f database_schema.sql

# Run dashboard cache tests
cd /home/project/Ledger-SG/apps/backend
source /opt/venv/bin/activate
pytest apps/reporting/tests/test_dashboard_cache.py -v --tb=short --reuse-db --no-migrations

# Run all dashboard tests
pytest apps/reporting/tests/test_dashboard_service_tdd.py apps/reporting/tests/test_dashboard_cache.py -v
```

---

## Performance Impact

| Metric | Before | After | Improvement |
|--------|--------|-------|-------------|
| Cache Miss | ~500ms | ~500ms | — |
| Cache Hit | ~500ms | ~10ms | **50x faster** |
| DB Queries | 8-12 | 0 (cache hit) | **Full elimination** |
| Redis Memory | — | ~2KB/org | Minimal |

---

## Success Criteria

- [ ] All TDD tests passing (RED → GREEN)
- [ ] Cache TTL verified at 300 seconds
- [ ] Cache miss correctly queries database
- [ ] Cache hit returns data without DB queries
- [ ] Existing dashboard tests still passing
- [ ] Code follows service layer pattern
- [ ] Proper error handling for Redis failures

---

## Risks & Mitigation

| Risk | Mitigation |
|------|------------|
| Redis unavailable | Graceful fallback to DB queries |
| Cache not invalidated | Add explicit invalidation API |
| Data staleness | 5-min TTL is acceptable for dashboard |
| Memory pressure | Cache size is small (~2KB per org) |

---

## Estimated Effort

- **Planning & Analysis:** 30 minutes ✅
- **TDD Implementation:** 2-3 hours
- **Testing & Validation:** 1 hour
- **Documentation:** 30 minutes
- **Total:** ~4 hours

---

## Next Steps

1. ✅ Create implementation plan (COMPLETE)
2. 🔄 Write TDD tests (RED phase)
3. Implement cache logic (GREEN phase)
4. Refactor and optimize
5. Run full test suite
6. Update documentation

---

## Related Documentation

- INTEGRATION_GAPS_PHASE3_SUMMARY.md
- apps/reporting/services/dashboard_service.py
- apps/reporting/tests/test_dashboard_service_tdd.py
- config/settings/base.py (Redis configuration)
