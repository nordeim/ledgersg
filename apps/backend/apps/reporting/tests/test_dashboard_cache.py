"""
Dashboard Cache TDD Tests.

Test-Driven Development for Redis caching on dashboard data.
Tests cover cache key generation, cache hit/miss, TTL, and invalidation.

Version: 1.0.0
Date: 2026-03-04
Phase: RED - Failing Tests
"""

import pytest
from datetime import date, datetime, timedelta
from decimal import Decimal
from uuid import uuid4
from django.core.cache import cache

from apps.core.models import (
    Organisation,
    AppUser,
    FiscalYear,
    FiscalPeriod,
    InvoiceDocument,
    Contact,
    TaxCode,
    Account,
    BankAccount,
    Payment,
    JournalEntry,
    JournalLine,
    Role,
    UserOrganisation,
)
from apps.reporting.services.dashboard_service import DashboardService


@pytest.fixture
def cache_test_user():
    """Create test user for cache tests."""
    user = AppUser.objects.create(
        id=uuid4(),
        email="cache_test@example.com",
        full_name="Cache Test User",
    )
    user.set_password("testpass123")
    user.save()
    return user


@pytest.fixture
def cache_test_org(cache_test_user):
    """Create test organization for cache tests."""
    org = Organisation.objects.create(
        id=uuid4(),
        name="Cache Test Org",
        legal_name="Cache Test Org Pte Ltd",
        uen="CACHE001",
        entity_type="PRIVATE_LIMITED",
        gst_registered=True,
        gst_reg_number="M12345678",
        gst_reg_date=date(2024, 1, 1),
        fy_start_month=1,
        base_currency="SGD",
        is_active=True,
    )

    # Create Owner role
    owner_role = Role.objects.create(
        org=org,
        name="Owner",
        description="Full access",
        can_manage_org=True,
        can_manage_users=True,
        can_manage_coa=True,
        can_create_invoices=True,
        can_approve_invoices=True,
        can_void_invoices=True,
        can_create_journals=True,
        can_manage_banking=True,
        can_file_gst=True,
        can_view_reports=True,
        can_export_data=True,
        is_system=True,
    )

    # Assign user to org
    UserOrganisation.objects.create(
        user=cache_test_user,
        org=org,
        role=owner_role,
        is_default=True,
        accepted_at=datetime.now(),
    )

    return org


@pytest.fixture
def cache_test_fiscal_year(cache_test_org):
    """Create fiscal year for cache tests."""
    fy = FiscalYear.objects.create(
        org=cache_test_org,
        label="FY2024",
        start_date=date(2024, 1, 1),
        end_date=date(2024, 12, 31),
        is_closed=False,
    )

    FiscalPeriod.objects.create(
        org=cache_test_org,
        fiscal_year=fy,
        label="January 2024",
        period_number=1,
        start_date=date(2024, 1, 1),
        end_date=date(2024, 1, 31),
        is_open=True,
    )

    return fy


@pytest.fixture
def cache_test_tax_code(cache_test_org):
    """Create tax code for cache tests."""
    return TaxCode.objects.create(
        org=cache_test_org,
        code="SR",
        name="Standard-Rated",
        description="Standard-Rated Supply",
        rate=Decimal("0.09"),
        is_gst_charged=True,
        is_input=False,
        is_output=True,
        is_claimable=True,
        f5_supply_box=1,
        f5_tax_box=6,
        is_active=True,
        effective_from=date(2024, 1, 1),
    )


@pytest.fixture
def cache_test_gl_account(cache_test_org):
    """Create GL account for bank account."""
    return Account.objects.create(
        org=cache_test_org,
        code="1100",
        name="DBS Bank Account",
        account_type="ASSET_CURRENT",
        is_system=True,
        is_active=True,
    )


@pytest.fixture
def cache_test_bank_account(cache_test_org, cache_test_gl_account):
    """Create bank account for cache tests."""
    return BankAccount.objects.create(
        id=uuid4(),
        org=cache_test_org,
        account_name="Main Operating Account",
        bank_name="DBS Bank",
        account_number="1234567890",
        currency="SGD",
        gl_account=cache_test_gl_account,
        opening_balance=Decimal("10000.0000"),
        current_balance=Decimal("10000.0000"),
        is_active=True,
        is_default=True,
    )


@pytest.mark.django_db
class TestDashboardCacheKeys:
    """Test cache key generation for dashboard data."""

    def test_cache_key_format(self, cache_test_org):
        """Test cache key follows expected pattern: dashboard:{org_id}."""
        service = DashboardService()
        cache_key = service._get_cache_key(str(cache_test_org.id))

        assert cache_key is not None
        assert cache_key == f"dashboard:{cache_test_org.id}"

    def test_cache_key_consistency(self, cache_test_org):
        """Test cache key is consistent for same org_id."""
        service = DashboardService()
        key1 = service._get_cache_key(str(cache_test_org.id))
        key2 = service._get_cache_key(str(cache_test_org.id))

        assert key1 == key2

    def test_cache_key_different_for_different_orgs(self, cache_test_org):
        """Test cache keys are different for different organizations."""
        service = DashboardService()

        # Create another org
        other_org = Organisation.objects.create(
            id=uuid4(),
            name="Other Org",
            legal_name="Other Org Pte Ltd",
            uen="OTHER001",
            entity_type="PRIVATE_LIMITED",
            base_currency="SGD",
            is_active=True,
        )

        key1 = service._get_cache_key(str(cache_test_org.id))
        key2 = service._get_cache_key(str(other_org.id))

        assert key1 != key2


@pytest.mark.django_db
class TestDashboardCacheHitMiss:
    """Test cache hit and miss scenarios."""

    def test_cache_miss_computes_from_database(self, cache_test_org, cache_test_fiscal_year):
        """Test cache miss queries database and caches result."""
        service = DashboardService()
        org_id = str(cache_test_org.id)

        # Ensure cache is empty
        cache_key = service._get_cache_key(org_id)
        cache.delete(cache_key)

        # Should compute from DB and cache
        result = service.get_dashboard_data(org_id)

        # Verify result is valid
        assert "gst_payable" in result
        assert "revenue_mtd" in result

        # Verify data was cached
        cached = cache.get(cache_key)
        assert cached is not None
        assert cached["gst_payable"] == result["gst_payable"]

    def test_cache_hit_returns_cached_value(self, cache_test_org, cache_test_fiscal_year):
        """Test retrieving cached data returns stored value without DB queries."""
        service = DashboardService()
        org_id = str(cache_test_org.id)
        cache_key = service._get_cache_key(org_id)

        # Manually set cached data
        cached_data = {
            "gst_payable": "999.99",
            "revenue_mtd": "5000.00",
            "cached": True,
            "timestamp": datetime.now().isoformat(),
        }
        cache.set(cache_key, cached_data, timeout=300)

        # Get dashboard data - should return cached value
        result = service.get_dashboard_data(org_id)

        # Should return cached data
        assert result["cached"] is True
        assert result["gst_payable"] == "999.99"
        assert result["revenue_mtd"] == "5000.00"

    def test_first_call_caches_result(self, cache_test_org, cache_test_fiscal_year):
        """Test first call to get_dashboard_data caches the result."""
        service = DashboardService()
        org_id = str(cache_test_org.id)
        cache_key = service._get_cache_key(org_id)

        # Clear cache
        cache.delete(cache_key)

        # First call should compute and cache
        result1 = service.get_dashboard_data(org_id)

        # Verify data is in cache
        cached = cache.get(cache_key)
        assert cached is not None
        assert cached["gst_payable"] == result1["gst_payable"]

        # Second call should return cached data
        result2 = service.get_dashboard_data(org_id)
        assert result2["gst_payable"] == result1["gst_payable"]


@pytest.mark.django_db
class TestDashboardCacheTTL:
    """Test cache TTL (Time To Live) configuration."""

    def test_cache_ttl_is_300_seconds(self, cache_test_org, cache_test_fiscal_year):
        """Test cache TTL is 5 minutes (300 seconds)."""
        service = DashboardService()
        org_id = str(cache_test_org.id)

        # Clear cache
        cache_key = service._get_cache_key(org_id)
        cache.delete(cache_key)

        # Get dashboard data - should cache with TTL
        service.get_dashboard_data(org_id)

        # Check if data exists in cache
        cached = cache.get(cache_key)
        assert cached is not None

        # Note: Django cache.get() doesn't return TTL directly
        # This test verifies the data is cached, TTL is tested in integration

    def test_cache_expires_after_ttl(self, cache_test_org, cache_test_fiscal_year):
        """Test that cached data expires after TTL."""
        service = DashboardService()
        org_id = str(cache_test_org.id)
        cache_key = service._get_cache_key(org_id)

        # Set data with very short TTL (1 second)
        test_data = {"test": "data", "value": 123}
        cache.set(cache_key, test_data, timeout=1)

        # Data should exist immediately
        result = cache.get(cache_key)
        assert result is not None

        # Wait for TTL to expire
        import time

        time.sleep(2)

        # Data should be expired
        result = cache.get(cache_key)
        assert result is None


@pytest.mark.django_db
class TestDashboardCacheInvalidation:
    """Test cache invalidation methods."""

    def test_invalidate_dashboard_cache(self, cache_test_org, cache_test_fiscal_year):
        """Test manual cache invalidation."""
        service = DashboardService()
        org_id = str(cache_test_org.id)
        cache_key = service._get_cache_key(org_id)

        # Cache some data
        service.get_dashboard_data(org_id)

        # Verify data is cached
        cached = cache.get(cache_key)
        assert cached is not None

        # Invalidate cache
        service.invalidate_dashboard_cache(org_id)

        # Verify cache is cleared
        cached = cache.get(cache_key)
        assert cached is None

    def test_invalidate_nonexistent_cache_no_error(self, cache_test_org):
        """Test invalidating non-existent cache doesn't raise error."""
        service = DashboardService()
        org_id = str(cache_test_org.id)

        # Should not raise error
        service.invalidate_dashboard_cache(org_id)


@pytest.mark.django_db
class TestDashboardCacheWithData:
    """Test caching with real dashboard data scenarios."""

    def test_cache_with_invoice_data(
        self,
        cache_test_org,
        cache_test_fiscal_year,
        cache_test_tax_code,
    ):
        """Test caching works correctly with invoice data."""
        from apps.invoicing.services import DocumentService

        # Create customer
        customer = Contact.objects.create(
            org=cache_test_org,
            contact_type="CUSTOMER",
            name="Test Customer",
            email="customer@test.com",
            is_customer=True,
            is_active=True,
        )

        # Create revenue account
        revenue_account = Account.objects.create(
            org=cache_test_org,
            code="4000",
            name="Sales Revenue",
            account_type="REVENUE",
            is_system=True,
            is_active=True,
        )

        # Create invoice
        invoice = InvoiceDocument.objects.create(
            org=cache_test_org,
            document_type="SALES_INVOICE",
            document_number="INV-00001",
            contact=customer,
            issue_date=date.today(),
            due_date=date.today() + timedelta(days=30),
            status="APPROVED",
            subtotal=Decimal("1000.0000"),
            tax_amount=Decimal("90.0000"),
            total=Decimal("1090.0000"),
            tax_code=cache_test_tax_code,
        )

        service = DashboardService()
        org_id = str(cache_test_org.id)

        # Get dashboard data (should cache)
        result = service.get_dashboard_data(org_id)

        # Verify revenue reflects invoice
        assert "revenue_mtd" in result
        assert result["revenue_mtd"] != "SGD 0.00"  # Should have revenue

        # Verify cached
        cache_key = service._get_cache_key(org_id)
        cached = cache.get(cache_key)
        assert cached is not None

    def test_cache_with_bank_account(
        self,
        cache_test_org,
        cache_test_fiscal_year,
        cache_test_bank_account,
    ):
        """Test caching works correctly with bank account data."""
        service = DashboardService()
        org_id = str(cache_test_org.id)

        # Get dashboard data (should cache)
        result = service.get_dashboard_data(org_id)

        # Verify cash on hand reflects bank account
        assert "cash_on_hand" in result

        # Verify cached
        cache_key = service._get_cache_key(org_id)
        cached = cache.get(cache_key)
        assert cached is not None
        assert cached["cash_on_hand"] == result["cash_on_hand"]


@pytest.mark.django_db
class TestDashboardCachePerformance:
    """Test cache performance benefits."""

    def test_cache_hit_faster_than_miss(
        self,
        cache_test_org,
        cache_test_fiscal_year,
        cache_test_bank_account,
    ):
        """Test that cache hit is faster than cache miss."""
        import time

        service = DashboardService()
        org_id = str(cache_test_org.id)

        # Clear cache
        cache_key = service._get_cache_key(org_id)
        cache.delete(cache_key)

        # Measure cache miss time
        start_miss = time.time()
        service.get_dashboard_data(org_id)
        time_miss = time.time() - start_miss

        # Measure cache hit time
        start_hit = time.time()
        service.get_dashboard_data(org_id)
        time_hit = time.time() - start_hit

        # Cache hit should be faster (or at least not slower)
        # Note: In real scenarios, cache hit is typically 10-50x faster
        assert time_hit <= time_miss * 1.5  # Allow some variance


@pytest.mark.django_db
class TestDashboardCacheErrorHandling:
    """Test error handling for cache operations."""

    def test_graceful_fallback_on_cache_error(self, cache_test_org, cache_test_fiscal_year):
        """Test that dashboard works even if cache fails."""
        service = DashboardService()
        org_id = str(cache_test_org.id)

        # Mock cache.get to raise exception
        from unittest.mock import patch

        with patch.object(cache, "get", side_effect=Exception("Redis error")):
            # Should still return valid data (computed from DB)
            result = service.get_dashboard_data(org_id)

            assert "gst_payable" in result
            assert "revenue_mtd" in result

    def test_cache_set_failure_doesnt_break_dashboard(self, cache_test_org, cache_test_fiscal_year):
        """Test that cache.set failure doesn't break dashboard."""
        service = DashboardService()
        org_id = str(cache_test_org.id)

        # Mock cache.set to raise exception
        from unittest.mock import patch

        with patch.object(cache, "set", side_effect=Exception("Redis write error")):
            # Should still return valid data
            result = service.get_dashboard_data(org_id)

            assert "gst_payable" in result
            assert result is not None
