"""
Test rate limiting for authentication and banking endpoints.

SEC-002 Remediation: Security tests for rate limit enforcement.
"""

import pytest
import uuid
from django.contrib.auth.hashers import make_password
from django.test import override_settings
from rest_framework.test import APIClient
from rest_framework import status

from apps.core.models import AppUser, Organisation, UserOrganisation, Role, BankAccount


pytestmark = pytest.mark.django_db


@pytest.fixture
def api_client():
    """Unauthenticated API client."""
    return APIClient()


@pytest.fixture
def test_user():
    """Create and return a test user."""
    user_id = uuid.uuid4()
    user = AppUser.objects.create(
        id=user_id,
        email=f"ratelimit_test_{user_id.hex[:8]}@example.com",
        full_name="Rate Limit Test User",
        is_active=True,
    )
    user.password = make_password("testpassword123")
    user.save()
    return user


@pytest.fixture
def authenticated_client(test_user):
    """Authenticated API client."""
    client = APIClient()
    client.force_authenticate(user=test_user)
    return client, test_user


@pytest.fixture
def test_org(test_user):
    """Test organisation."""
    org_id = uuid.uuid4()
    org = Organisation.objects.create(
        id=org_id,
        name="Rate Limit Test Org",
        legal_name="Rate Limit Test Org Pte Ltd",
        uen="RLTEST01",
        entity_type="PRIVATE_LIMITED",
        gst_registered=True,
        gst_reg_number="M12345678",
        is_active=True,
    )

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

    UserOrganisation.objects.create(
        user=test_user,
        org=org,
        role=owner_role,
        is_default=True,
        accepted_at="2026-01-01T00:00:00Z",
    )

    return org


class TestRateLimitConfiguration:
    """Test that rate limiting is properly configured."""

    def test_django_ratelimit_installed(self):
        """django-ratelimit should be in INSTALLED_APPS."""
        from django.conf import settings

        assert "django_ratelimit" in settings.INSTALLED_APPS

    def test_ratelimit_settings_configured(self):
        """Rate limit settings should be configured."""
        from django.conf import settings

        assert hasattr(settings, "RATELIMIT_ENABLE")
        assert hasattr(settings, "RATELIMIT_CACHE_PREFIX")
        assert hasattr(settings, "RATELIMIT_VIEW")

    def test_custom_rate_limit_handler_defined(self):
        """Custom rate limit handler should be defined."""
        from common.exceptions import rate_limit_exceeded_view

        assert callable(rate_limit_exceeded_view)


class TestRateLimitException:
    """Test RateLimitExceeded exception."""

    def test_rate_limit_exceeded_exception_exists(self):
        """RateLimitExceeded exception should be defined."""
        from common.exceptions import RateLimitExceeded

        assert RateLimitExceeded is not None

    def test_rate_limit_exceeded_status_code(self):
        """RateLimitExceeded should return 429 status."""
        from common.exceptions import RateLimitExceeded

        exc = RateLimitExceeded()
        assert exc.status_code == 429
        assert exc.code == "rate_limit_exceeded"


class TestAuthRateLimiting:
    """Test rate limiting on authentication endpoints."""

    @pytest.mark.skip(reason="Requires Redis running - integration test")
    @override_settings(RATELIMIT_ENABLE=True)
    def test_register_rate_limit_5_per_hour(self, api_client):
        """Registration is limited to 5 per hour per IP."""
        url = "/api/v1/auth/register/"

        payload = {
            "email": "test@example.com",
            "password": "SecurePass123!",
            "full_name": "Test User",
        }

        for i in range(6):
            response = api_client.post(url, payload, format="json")
            if i < 5:
                assert response.status_code in [
                    status.HTTP_201_CREATED,
                    status.HTTP_400_BAD_REQUEST,
                ]
            else:
                assert response.status_code == status.HTTP_429_TOO_MANY_REQUESTS

    @pytest.mark.skip(reason="Requires Redis running - integration test")
    @override_settings(RATELIMIT_ENABLE=True)
    def test_login_rate_limit_10_per_minute(self, api_client):
        """Login is limited to 10 per minute per IP."""
        url = "/api/v1/auth/login/"

        payload = {
            "email": "nonexistent@example.com",
            "password": "WrongPass123!",
        }

        for i in range(11):
            response = api_client.post(url, payload, format="json")
            if i < 10:
                assert response.status_code in [
                    status.HTTP_200_OK,
                    status.HTTP_401_UNAUTHORIZED,
                ]
            else:
                assert response.status_code == status.HTTP_429_TOO_MANY_REQUESTS


class TestGlobalThrottling:
    """Test DRF global throttling on banking endpoints."""

    @pytest.mark.skip(reason="Requires Redis running - integration test")
    @override_settings(
        REST_FRAMEWORK={
            "DEFAULT_THROTTLE_CLASSES": [
                "rest_framework.throttling.UserRateThrottle",
            ],
            "DEFAULT_THROTTLE_RATES": {"user": "5/minute"},
        }
    )
    def test_banking_endpoints_throttled(self, authenticated_client, test_org):
        """Banking endpoints are subject to global throttling."""
        client, user = authenticated_client

        bank_account = BankAccount.objects.create(
            org=test_org,
            bank_name="Test Bank",
            account_name="Test Account",
            account_number="1234567890",
            currency="SGD",
            is_active=True,
        )
        url = f"/api/v1/orgs/{test_org.id}/banking/accounts/"

        for i in range(6):
            response = client.get(url)
            if i < 5:
                assert response.status_code in [
                    status.HTTP_200_OK,
                    status.HTTP_403_FORBIDDEN,
                ]
            else:
                assert response.status_code == status.HTTP_429_TOO_MANY_REQUESTS
