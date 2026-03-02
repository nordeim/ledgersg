"""
TDD Tests for Auth Organization Context Endpoints.

Tests cover:
1. my_organisations_view - GET /api/v1/auth/organisations/
2. set_default_org_view - POST /api/v1/auth/set-default-org/
3. JWT token claims with default_org_id
"""

import pytest
import uuid
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken
from django.utils import timezone

from apps.core.models import AppUser, Organisation, Role, UserOrganisation


pytestmark = pytest.mark.integration


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def test_user(db):
    """Create a test user with unique email."""
    unique_id = str(uuid.uuid4())[:8]
    user = AppUser.objects.create_user(
        email=f"test_{unique_id}@example.com",
        password="testpassword123",
        full_name="Test User",
    )
    return user


@pytest.fixture
def test_org_1(db):
    """Create first test organisation."""
    unique_id = str(uuid.uuid4())[:8]
    return Organisation.objects.create(
        name=f"Test Org Alpha {unique_id}",
        legal_name=f"Test Org Alpha {unique_id} Pte Ltd",
        uen=f"2024{unique_id[:7]}A",
        entity_type="PRIVATE_LIMITED",
    )


@pytest.fixture
def test_org_2(db):
    """Create second test organisation."""
    unique_id = str(uuid.uuid4())[:8]
    return Organisation.objects.create(
        name=f"Test Org Beta {unique_id}",
        legal_name=f"Test Org Beta {unique_id} Pte Ltd",
        uen=f"2024{unique_id[:7]}B",
        entity_type="PRIVATE_LIMITED",
    )


@pytest.fixture
def test_role_1(test_org_1):
    """Create a role for test_org_1."""
    unique_id = str(uuid.uuid4())[:8]
    return Role.objects.create(
        org=test_org_1,
        name=f"TestOwner_{unique_id}",
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


@pytest.fixture
def test_role_2(test_org_2):
    """Create a role for test_org_2."""
    unique_id = str(uuid.uuid4())[:8]
    return Role.objects.create(
        org=test_org_2,
        name=f"TestOwner_{unique_id}",
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


@pytest.fixture
def authenticated_client(api_client, test_user):
    """Return authenticated API client."""
    refresh = RefreshToken.for_user(test_user)
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {str(refresh.access_token)}")
    return api_client


class TestMyOrganisationsView:
    """Tests for GET /api/v1/auth/organisations/"""

    def test_returns_empty_list_when_no_orgs(self, authenticated_client, test_user):
        """Test that user with no orgs returns empty list."""
        response = authenticated_client.get("/api/v1/auth/organisations/")

        assert response.status_code == 200
        assert response.data == []

    def test_returns_user_organisations_with_is_default(
        self, authenticated_client, test_user, test_org_1, test_role_1
    ):
        """Test that response includes is_default flag."""
        # Create membership with accepted_at
        UserOrganisation.objects.create(
            user=test_user,
            org=test_org_1,
            role=test_role_1,
            is_default=True,
            accepted_at=timezone.now(),
        )

        response = authenticated_client.get("/api/v1/auth/organisations/")

        assert response.status_code == 200
        assert len(response.data) == 1
        assert response.data[0]["id"] == str(test_org_1.id)
        assert "Test Org" in response.data[0]["name"]
        assert response.data[0]["is_default"] is True
        assert "role" in response.data[0]

    def test_returns_multiple_orgs_sorted_by_is_default(
        self, authenticated_client, test_user, test_org_1, test_org_2, test_role_1, test_role_2
    ):
        """Test that default org comes first in response."""
        now = timezone.now()

        # Create memberships
        UserOrganisation.objects.create(
            user=test_user,
            org=test_org_1,
            role=test_role_1,
            is_default=False,
            accepted_at=now,
        )

        UserOrganisation.objects.create(
            user=test_user,
            org=test_org_2,
            role=test_role_2,
            is_default=True,
            accepted_at=now,
        )

        response = authenticated_client.get("/api/v1/auth/organisations/")

        assert response.status_code == 200
        assert len(response.data) == 2
        # Default org should be first (sorted by -is_default in service)
        assert response.data[0]["is_default"] is True

    def test_excludes_pending_invitations(
        self, authenticated_client, test_user, test_org_1, test_role_1
    ):
        """Test that pending invitations (no accepted_at) are excluded."""
        # Create membership without accepted_at (pending)
        UserOrganisation.objects.create(
            user=test_user,
            org=test_org_1,
            role=test_role_1,
            is_default=False,
        )

        response = authenticated_client.get("/api/v1/auth/organisations/")

        assert response.status_code == 200
        assert len(response.data) == 0

    def test_requires_authentication(self, api_client):
        """Test that unauthenticated requests are rejected."""
        response = api_client.get("/api/v1/auth/organisations/")

        assert response.status_code == 401


class TestSetDefaultOrgView:
    """Tests for POST /api/v1/auth/set-default-org/"""

    def test_sets_default_org_successfully(
        self, authenticated_client, test_user, test_org_1, test_org_2, test_role_1, test_role_2
    ):
        """Test that default org can be changed."""
        now = timezone.now()

        # Create memberships
        UserOrganisation.objects.create(
            user=test_user,
            org=test_org_1,
            role=test_role_1,
            is_default=True,
            accepted_at=now,
        )

        UserOrganisation.objects.create(
            user=test_user,
            org=test_org_2,
            role=test_role_2,
            is_default=False,
            accepted_at=now,
        )

        # Set org_2 as default
        response = authenticated_client.post(
            "/api/v1/auth/set-default-org/",
            {"org_id": str(test_org_2.id)},
            format="json",
        )

        assert response.status_code == 200
        assert response.data["message"] == "Default organisation updated"
        assert response.data["default_org"]["id"] == str(test_org_2.id)

        # Verify in database
        user_org_1 = UserOrganisation.objects.get(user=test_user, org=test_org_1)
        user_org_2 = UserOrganisation.objects.get(user=test_user, org=test_org_2)

        assert user_org_1.is_default is False
        assert user_org_2.is_default is True

    def test_returns_400_for_missing_org_id(self, authenticated_client):
        """Test that missing org_id returns validation error."""
        response = authenticated_client.post(
            "/api/v1/auth/set-default-org/",
            {},
            format="json",
        )

        assert response.status_code == 400
        assert "org_id" in response.data["error"]["message"]

    def test_returns_403_for_unauthorized_org(self, authenticated_client, test_user, test_org_1):
        """Test that user cannot set default for org they don't belong to."""
        response = authenticated_client.post(
            "/api/v1/auth/set-default-org/",
            {"org_id": str(test_org_1.id)},
            format="json",
        )

        assert response.status_code == 403
        assert "unauthorized" in response.data["error"]["code"]

    def test_requires_authentication(self, api_client, test_org_1):
        """Test that unauthenticated requests are rejected."""
        response = api_client.post(
            "/api/v1/auth/set-default-org/",
            {"org_id": str(test_org_1.id)},
            format="json",
        )

        assert response.status_code == 401


class TestJWTTokenOrgClaims:
    """Tests for JWT token default_org_id claims."""

    def test_token_includes_default_org_id(self, test_user, test_org_1, test_role_1):
        """Test that JWT token includes default_org_id claim."""
        from apps.core.services.auth_service import generate_tokens

        # Create membership
        UserOrganisation.objects.create(
            user=test_user,
            org=test_org_1,
            role=test_role_1,
            is_default=True,
            accepted_at=timezone.now(),
        )

        tokens = generate_tokens(test_user)

        # Decode and verify claims
        refresh = RefreshToken(tokens["refresh"])
        assert "default_org_id" in refresh
        assert refresh["default_org_id"] == str(test_org_1.id)
        assert "default_org_name" in refresh

    def test_token_uses_first_org_if_no_default(self, test_user, test_org_1, test_role_1):
        """Test that JWT token uses first org if no default set."""
        from apps.core.services.auth_service import generate_tokens

        # Create membership without is_default
        UserOrganisation.objects.create(
            user=test_user,
            org=test_org_1,
            role=test_role_1,
            is_default=False,
            accepted_at=timezone.now(),
        )

        tokens = generate_tokens(test_user)

        # Should still include org info (first accepted org)
        refresh = RefreshToken(tokens["refresh"])
        assert "default_org_id" in refresh
        assert refresh["default_org_id"] == str(test_org_1.id)

    def test_token_no_org_claim_when_no_orgs(self, test_user):
        """Test that JWT token has no org claims when user has no orgs."""
        from apps.core.services.auth_service import generate_tokens

        tokens = generate_tokens(test_user)

        # No org claims should be present
        refresh = RefreshToken(tokens["refresh"])
        # The claims may not exist at all if user has no orgs
        assert refresh.get("default_org_id") is None or "default_org_id" not in refresh
