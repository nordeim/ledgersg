"""
TDD Test for RLS Context Middleware Fix

Tests to verify RLS context is properly set for authenticated requests.
"""

import pytest
import uuid
from unittest.mock import Mock, patch
from django.test import RequestFactory, TestCase
from django.http import HttpResponse
from django.db import connection
from django.contrib.auth import get_user_model

from common.middleware.tenant_context import TenantContextMiddleware

User = get_user_model()


@pytest.mark.django_db
class TestRLSContextMiddleware:
    """Test RLS context is properly set in middleware."""

    def test_rls_context_not_set_when_user_unauthenticated(self):
        """
        Test 1 (FAILING): Currently RLS is NOT set when user is unauthenticated.

        This test documents the CURRENT BUG behavior.
        After fix, this should be updated to test that RLS is set to NULL
        or that authentication is properly enforced.
        """
        factory = RequestFactory()
        request = factory.get("/api/v1/test-org/banking/bank-accounts/")
        request.user = Mock()
        request.user.is_authenticated = False

        # Execute middleware
        mw = TenantContextMiddleware(lambda r: HttpResponse())
        response = mw(request)

        # Check RLS context - currently NOT set (BUG)
        with connection.cursor() as cursor:
            cursor.execute("SELECT current_setting('app.current_org_id', true)")
            result = cursor.fetchone()[0]

        # This assertion documents the current BUG
        # After fix, we expect this to be changed
        assert result is None or result == "", f"Expected no RLS set, got: {result}"

    def test_rls_context_set_when_user_authenticated(self):
        """
        Test 2 (SHOULD PASS): RLS context should be set for authenticated users.

        Currently FAILS because middleware skips RLS setup.
        After fix, this should PASS.
        """
        # Create test user and org
        user = User.objects.create_user(email="test_rls@example.com", password="testpass123")

        # Create org and membership would go here
        # For now, just test that user auth works

        factory = RequestFactory()
        request = factory.get("/api/v1/65abbcd6-6129-41ef-82ed-9e84a3442c7f/banking/bank-accounts/")
        request.user = user

        # Execute middleware
        mw = TenantContextMiddleware(lambda r: HttpResponse())
        response = mw(request)

        # Check RLS context is set
        with connection.cursor() as cursor:
            cursor.execute("SELECT current_setting('app.current_org_id', true)")
            result = cursor.fetchone()[0]

        # This SHOULD pass after fix
        # Currently will fail because middleware returns early
        assert result is not None and result != "", f"RLS context not set, got: {result}"

    def test_jwt_token_extraction_in_middleware(self):
        """
        Test 3: JWT token extraction from Authorization header.

        Currently may be failing silently.
        """
        factory = RequestFactory()
        request = factory.get("/api/v1/test-org/banking/")
        request.user = Mock()
        request.user.is_authenticated = False

        # Mock token
        request.META = {"HTTP_AUTHORIZATION": "Bearer invalid_token_for_test"}

        mw = TenantContextMiddleware(lambda r: HttpResponse())
        user = mw._get_authenticated_user(request)

        # Should return None for invalid token
        assert user is None


@pytest.mark.django_db
class TestBankingEndpointsWithRLS:
    """Test banking endpoints work with RLS."""

    def test_bank_account_list_returns_200(self):
        """
        Test 4: Bank account list should return 200, not internal_error.

        Currently FAILS with internal_error.
        """
        from rest_framework.test import APIClient
        from rest_framework_simplejwt.tokens import AccessToken

        # Create user
        user = User.objects.create_user(email="banking_test@example.com", password="testpass123")

        # Create token
        token = AccessToken.for_user(user)

        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {str(token)}")

        # Make request - this should work after RLS fix
        response = client.get("/api/v1/65abbcd6-6129-41ef-82ed-9e84a3442c7f/banking/bank-accounts/")

        # Should be 200 OK, not 500 internal_error
        assert response.status_code == 200, (
            f"Expected 200, got {response.status_code}: {response.data}"
        )

    def test_tax_code_list_returns_200(self):
        """
        Test 5: Tax code list should return 200.

        Currently FAILS with internal_error.
        """
        from rest_framework.test import APIClient
        from rest_framework_simplejwt.tokens import AccessToken

        user = User.objects.create_user(email="tax_test@example.com", password="testpass123")

        token = AccessToken.for_user(user)

        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {str(token)}")

        response = client.get("/api/v1/65abbcd6-6129-41ef-82ed-9e84a3442c7f/gst/tax-codes/")

        # Should be 200 OK
        assert response.status_code == 200, (
            f"Expected 200, got {response.status_code}: {response.data}"
        )


@pytest.mark.django_db
class TestJournalEndpointsWithRLS:
    """Test journal endpoints work with RLS."""

    def test_journal_entries_list_returns_200(self):
        """
        Test 6: Journal entries should return 200.

        Currently FAILS with internal_error.
        """
        from rest_framework.test import APIClient
        from rest_framework_simplejwt.tokens import AccessToken

        user = User.objects.create_user(email="journal_test@example.com", password="testpass123")

        token = AccessToken.for_user(user)

        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {str(token)}")

        response = client.get(
            "/api/v1/65abbcd6-6129-41ef-82ed-9e84a3442c7f/journal-entries/entries/"
        )

        # Should be 200 OK
        assert response.status_code == 200, (
            f"Expected 200, got {response.status_code}: {response.data}"
        )
