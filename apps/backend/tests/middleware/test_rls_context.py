"""
TDD Test for RLS Context Middleware Fix

Tests to verify RLS context is properly set for authenticated requests.
"""

import pytest
import uuid
import json
from unittest.mock import Mock, patch
from django.test import RequestFactory, TestCase
from django.http import HttpResponse
from django.db import connection
from django.contrib.auth import get_user_model
from django.utils import timezone

from common.middleware.tenant_context import TenantContextMiddleware
from apps.core.models import Organisation, UserOrganisation, Role

User = get_user_model()


@pytest.fixture
def test_org():
    """Create a test organisation."""
    org = Organisation.objects.create(
        name="Test Organisation", base_currency="SGD", gst_registered=False
    )
    return org


@pytest.fixture
def test_role(test_org):
    """Create a test role for the organisation."""
    role = Role.objects.create(
        org=test_org,
        name="OWNER",
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
    )
    return role


@pytest.fixture
def test_user_with_org(test_org, test_role):
    """Create a test user with org membership."""
    user = User.objects.create_user(email="test_rls@example.com", password="testpass123")
    UserOrganisation.objects.create(
        user=user, org=test_org, role=test_role, accepted_at=timezone.now()
    )
    return user


@pytest.mark.django_db
class TestRLSContextMiddleware:
    """Test RLS context is properly set in middleware."""

    def test_rls_context_not_set_when_user_unauthenticated(self):
        """
        Test 1: RLS should be set to empty string for unauthenticated users.
        """
        factory = RequestFactory()
        request = factory.get("/api/v1/test-org/banking/bank-accounts/")
        request.user = Mock()
        request.user.is_authenticated = False

        mw = TenantContextMiddleware(lambda r: HttpResponse())
        response = mw(request)

        with connection.cursor() as cursor:
            cursor.execute("SELECT current_setting('app.current_org_id', true)")
            result = cursor.fetchone()[0]

        assert result is None or result == "", f"Expected no RLS set, got: {result}"

    def test_rls_context_set_when_user_authenticated(self, test_user_with_org, test_org):
        """
        Test 2: RLS context should be set for authenticated users.
        """
        factory = RequestFactory()
        request = factory.get(f"/api/v1/{test_org.id}/banking/bank-accounts/")
        request.user = test_user_with_org

        mw = TenantContextMiddleware(lambda r: HttpResponse())
        response = mw(request)

        with connection.cursor() as cursor:
            cursor.execute("SELECT current_setting('app.current_org_id', true)")
            result = cursor.fetchone()[0]

        assert result is not None and result != "", f"RLS context not set, got: {result}"
        assert result == str(test_org.id), f"Expected org_id {test_org.id}, got: {result}"

    def test_jwt_token_extraction_in_middleware(self):
        """
        Test 3: JWT token extraction from Authorization header.
        """
        factory = RequestFactory()
        request = factory.get("/api/v1/test-org/banking/")
        request.user = Mock()
        request.user.is_authenticated = False
        request.META = {"HTTP_AUTHORIZATION": "Bearer invalid_token_for_test"}

        mw = TenantContextMiddleware(lambda r: HttpResponse())
        user = mw._get_authenticated_user(request)

        assert user is None


@pytest.mark.django_db
class TestBankingEndpointsWithRLS:
    """Test banking endpoints work with RLS."""

    def test_bank_account_list_returns_200(self, test_user_with_org, test_org):
        """
        Test 4: Bank account list should return 200, not 500.
        """
        from rest_framework.test import APIClient
        from rest_framework_simplejwt.tokens import AccessToken

        token = AccessToken.for_user(test_user_with_org)

        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {str(token)}")

        response = client.get(f"/api/v1/{test_org.id}/banking/bank-accounts/")

        content = json.loads(response.content) if hasattr(response, "content") else {}
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {content}"

    def test_tax_code_list_returns_200(self, test_user_with_org, test_org):
        """
        Test 5: Tax code list should return 200.
        """
        from rest_framework.test import APIClient
        from rest_framework_simplejwt.tokens import AccessToken

        token = AccessToken.for_user(test_user_with_org)

        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {str(token)}")

        response = client.get(f"/api/v1/{test_org.id}/gst/tax-codes/")

        content = json.loads(response.content) if hasattr(response, "content") else {}
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {content}"


@pytest.mark.django_db
class TestJournalEndpointsWithRLS:
    """Test journal endpoints work with RLS."""

    def test_journal_entries_list_returns_200(self, test_user_with_org, test_org):
        """
        Test 6: Journal entries should return 200.
        """
        from rest_framework.test import APIClient
        from rest_framework_simplejwt.tokens import AccessToken

        token = AccessToken.for_user(test_user_with_org)

        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {str(token)}")

        response = client.get(f"/api/v1/{test_org.id}/journal-entries/entries/")

        content = json.loads(response.content) if hasattr(response, "content") else {}
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {content}"
