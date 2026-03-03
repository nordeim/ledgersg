"""
Peppol API View Tests (GAP-3).

Tests for Peppol/InvoiceNow endpoints:
- GET /api/v1/{orgId}/peppol/transmission-log/
- GET /api/v1/{orgId}/peppol/settings/
- PATCH /api/v1/{orgId}/peppol/settings/

Run with: pytest apps/peppol/tests/test_views.py -v
"""

import pytest
import uuid
from datetime import date
from rest_framework import status
from rest_framework.test import APIClient

from apps.core.models import (
    AppUser,
    Organisation,
    Role,
    UserOrganisation,
)


@pytest.mark.django_db
class TestPeppolTransmissionLogView:
    """Test suite for PeppolTransmissionLogView endpoint."""

    @pytest.fixture
    def peppol_test_user(self):
        """Create a test user for Peppol tests."""
        user_id = uuid.uuid4()
        user = AppUser.objects.create(
            id=user_id,
            email=f"peppol_test_{user_id.hex[:8]}@example.com",
            full_name="Peppol Test User",
            is_active=True,
        )
        user.password = "testpassword123"
        user.save()
        return user

    @pytest.fixture
    def peppol_test_org(self, peppol_test_user):
        """Create organisation with Peppol enabled."""
        org_id = uuid.uuid4()
        org = Organisation.objects.create(
            id=org_id,
            name="Peppol Test Org",
            legal_name="Peppol Test Org Pte Ltd",
            uen="PEPPOL001",
            entity_type="PRIVATE_LIMITED",
            gst_registered=True,
            gst_reg_number="M12345678",
            gst_reg_date=date(2024, 1, 1),
            fy_start_month=1,
            base_currency="SGD",
            is_active=True,
            invoicenow_enabled=True,
            peppol_participant_id="0195:SGUEN123456789",
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

        from datetime import datetime

        UserOrganisation.objects.create(
            user=peppol_test_user,
            org=org,
            role=owner_role,
            is_default=True,
            accepted_at=datetime.now(),
        )

        return org

    @pytest.fixture
    def peppol_auth_client(self, peppol_test_user):
        """Return an authenticated APIClient."""
        client = APIClient()
        from rest_framework_simplejwt.tokens import RefreshToken

        refresh = RefreshToken.for_user(peppol_test_user)
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {str(refresh.access_token)}")
        return client

    def test_transmission_log_get_success(self, peppol_auth_client, peppol_test_org):
        """Test GET transmission log returns stub response."""
        url = f"/api/v1/{peppol_test_org.id}/peppol/transmission-log/"
        response = peppol_auth_client.get(url)

        assert response.status_code == status.HTTP_200_OK

        data = response.data

        # Verify response structure
        assert "results" in data
        assert "count" in data
        assert "pending" in data
        assert "failed" in data
        assert "completed" in data
        assert "meta" in data

        # Verify stub response
        assert data["results"] == []
        assert data["count"] == 0
        assert data["pending"] == 0
        assert data["failed"] == 0
        assert data["completed"] == 0

        # Verify meta info
        meta = data["meta"]
        assert meta["stub"] is True
        assert "message" in meta

    def test_transmission_log_with_status_filter(self, peppol_auth_client, peppol_test_org):
        """Test GET with status filter parameter."""
        url = f"/api/v1/{peppol_test_org.id}/peppol/transmission-log/?status=pending"
        response = peppol_auth_client.get(url)

        assert response.status_code == status.HTTP_200_OK

        data = response.data
        assert data["meta"]["status_filter"] == "pending"

    def test_transmission_log_requires_authentication(self, peppol_test_org):
        """Test GET transmission log without auth fails."""
        client = APIClient()
        url = f"/api/v1/{peppol_test_org.id}/peppol/transmission-log/"
        response = client.get(url)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_transmission_log_requires_membership(self, peppol_auth_client):
        """Test GET transmission log without org membership fails."""
        other_org = Organisation.objects.create(
            name="Other Org",
            legal_name="Other Org Pte Ltd",
            uen="OTHER001",
            entity_type="PRIVATE_LIMITED",
            base_currency="SGD",
            is_active=True,
        )

        url = f"/api/v1/{other_org.id}/peppol/transmission-log/"
        response = peppol_auth_client.get(url)

        assert response.status_code in [status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND]

    def test_transmission_log_post_not_allowed(self, peppol_auth_client, peppol_test_org):
        """Test POST is not allowed on transmission log."""
        url = f"/api/v1/{peppol_test_org.id}/peppol/transmission-log/"
        response = peppol_auth_client.post(url, {}, format="json")

        assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED


@pytest.mark.django_db
class TestPeppolSettingsView:
    """Test suite for PeppolSettingsView endpoint."""

    @pytest.fixture
    def settings_test_user(self):
        """Create a test user."""
        user_id = uuid.uuid4()
        user = AppUser.objects.create(
            id=user_id,
            email=f"peppol_settings_{user_id.hex[:8]}@example.com",
            full_name="Peppol Settings Test User",
            is_active=True,
        )
        user.password = "testpassword123"
        user.save()
        return user

    @pytest.fixture
    def settings_test_org(self, settings_test_user):
        """Create organisation with Peppol configured."""
        org_id = uuid.uuid4()
        org = Organisation.objects.create(
            id=org_id,
            name="Peppol Settings Org",
            legal_name="Peppol Settings Org Pte Ltd",
            uen="PEPPOLSET001",
            entity_type="PRIVATE_LIMITED",
            base_currency="SGD",
            is_active=True,
            invoicenow_enabled=True,
            peppol_participant_id="0195:SGUEN987654321",
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

        from datetime import datetime

        UserOrganisation.objects.create(
            user=settings_test_user,
            org=org,
            role=owner_role,
            is_default=True,
            accepted_at=datetime.now(),
        )

        return org

    @pytest.fixture
    def settings_auth_client(self, settings_test_user):
        """Return authenticated APIClient."""
        client = APIClient()
        from rest_framework_simplejwt.tokens import RefreshToken

        refresh = RefreshToken.for_user(settings_test_user)
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {str(refresh.access_token)}")
        return client

    def test_get_settings_success(self, settings_auth_client, settings_test_org):
        """Test GET Peppol settings returns configuration."""
        url = f"/api/v1/{settings_test_org.id}/peppol/settings/"
        response = settings_auth_client.get(url)

        assert response.status_code == status.HTTP_200_OK

        data = response.data

        # Verify structure
        assert "enabled" in data
        assert "participant_id" in data
        assert "endpoint" in data
        assert "test_mode" in data
        assert "supported_formats" in data
        assert "status" in data
        assert "meta" in data

        # Verify values from organisation
        assert data["enabled"] is True
        assert data["participant_id"] == "0195:SGUEN987654321"
        assert data["test_mode"] is True
        assert data["supported_formats"] == ["UBL"]
        assert data["status"] == "configured"
        assert data["meta"]["stub"] is True

    def test_get_settings_not_configured(self, settings_auth_client, settings_test_user):
        """Test GET settings when Peppol is not configured."""
        # Create org without Peppol participant ID
        org = Organisation.objects.create(
            name="No Peppol Org",
            legal_name="No Peppol Org Pte Ltd",
            uen="NOPEPPOL01",
            entity_type="PRIVATE_LIMITED",
            base_currency="SGD",
            is_active=True,
            invoicenow_enabled=False,
            peppol_participant_id="",
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

        from datetime import datetime

        UserOrganisation.objects.create(
            user=settings_test_user,
            org=org,
            role=owner_role,
            is_default=True,
            accepted_at=datetime.now(),
        )

        url = f"/api/v1/{org.id}/peppol/settings/"
        response = settings_auth_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        data = response.data

        assert data["enabled"] is False
        assert data["participant_id"] == ""
        assert data["status"] == "not_configured"

    def test_get_settings_not_found(self, settings_auth_client):
        """Test GET settings for non-existent org returns 403/404."""
        fake_org_id = uuid.uuid4()
        url = f"/api/v1/{fake_org_id}/peppol/settings/"
        response = settings_auth_client.get(url)

        # Permission middleware returns 403 for non-existent orgs
        assert response.status_code in [status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND]
        # If 404, check error structure
        if response.status_code == status.HTTP_404_NOT_FOUND:
            assert response.data["error"]["code"] == "not_found"

    def test_patch_settings_success(self, settings_auth_client, settings_test_org):
        """Test PATCH Peppol settings updates configuration."""
        url = f"/api/v1/{settings_test_org.id}/peppol/settings/"
        update_data = {
            "enabled": False,
            "participant_id": "0195:NEWPARTICIPANT",
        }

        response = settings_auth_client.patch(url, update_data, format="json")

        assert response.status_code == status.HTTP_200_OK
        data = response.data
        assert data["message"] == "Peppol settings updated"
        assert data["enabled"] is False
        assert data["participant_id"] == "0195:NEWPARTICIPANT"
        assert "updated_fields" in data
        assert "enabled" in data["updated_fields"]
        assert "participant_id" in data["updated_fields"]

        # Verify persisted to database
        settings_test_org.refresh_from_db()
        assert settings_test_org.invoicenow_enabled is False
        assert settings_test_org.peppol_participant_id == "0195:NEWPARTICIPANT"

    def test_patch_only_enabled(self, settings_auth_client, settings_test_org):
        """Test PATCH can update only enabled field."""
        url = f"/api/v1/{settings_test_org.id}/peppol/settings/"
        update_data = {"enabled": False}

        response = settings_auth_client.patch(url, update_data, format="json")

        assert response.status_code == status.HTTP_200_OK
        assert response.data["updated_fields"] == ["enabled"]

        settings_test_org.refresh_from_db()
        assert settings_test_org.invoicenow_enabled is False
        # Participant ID unchanged
        assert settings_test_org.peppol_participant_id == "0195:SGUEN987654321"

    def test_patch_only_participant_id(self, settings_auth_client, settings_test_org):
        """Test PATCH can update only participant_id field."""
        url = f"/api/v1/{settings_test_org.id}/peppol/settings/"
        update_data = {"participant_id": "0195:NEWID123"}

        response = settings_auth_client.patch(url, update_data, format="json")

        assert response.status_code == status.HTTP_200_OK
        assert response.data["updated_fields"] == ["participant_id"]

        settings_test_org.refresh_from_db()
        assert settings_test_org.peppol_participant_id == "0195:NEWID123"

    def test_patch_empty_update(self, settings_auth_client, settings_test_org):
        """Test PATCH with no valid fields returns success but no updates."""
        url = f"/api/v1/{settings_test_org.id}/peppol/settings/"
        response = settings_auth_client.patch(url, {}, format="json")

        assert response.status_code == status.HTTP_200_OK
        assert response.data["updated_fields"] == []

    def test_patch_settings_not_found(self, settings_auth_client):
        """Test PATCH for non-existent org returns 403/404."""
        fake_org_id = uuid.uuid4()
        url = f"/api/v1/{fake_org_id}/peppol/settings/"
        response = settings_auth_client.patch(url, {"enabled": True}, format="json")

        # Permission middleware returns 403 for non-existent orgs
        assert response.status_code in [status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND]
        # If 404, check error structure
        if response.status_code == status.HTTP_404_NOT_FOUND:
            assert response.data["error"]["code"] == "not_found"

    def test_patch_requires_authentication(self, settings_test_org):
        """Test PATCH without auth fails."""
        client = APIClient()
        url = f"/api/v1/{settings_test_org.id}/peppol/settings/"
        response = client.patch(url, {"enabled": True}, format="json")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_post_not_allowed(self, settings_auth_client, settings_test_org):
        """Test POST is not allowed."""
        url = f"/api/v1/{settings_test_org.id}/peppol/settings/"
        response = settings_auth_client.post(url, {}, format="json")

        assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED

    def test_put_not_allowed(self, settings_auth_client, settings_test_org):
        """Test PUT is not allowed."""
        url = f"/api/v1/{settings_test_org.id}/peppol/settings/"
        response = settings_auth_client.put(url, {}, format="json")

        assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED

    def test_delete_not_allowed(self, settings_auth_client, settings_test_org):
        """Test DELETE is not allowed."""
        url = f"/api/v1/{settings_test_org.id}/peppol/settings/"
        response = settings_auth_client.delete(url)

        assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED


@pytest.mark.django_db
class TestPeppolPermissions:
    """Test permission-related checks for Peppol endpoints."""

    @pytest.fixture
    def perm_test_user(self):
        """Create test user."""
        user_id = uuid.uuid4()
        user = AppUser.objects.create(
            id=user_id,
            email=f"peppol_perm_{user_id.hex[:8]}@example.com",
            full_name="Peppol Permission Test User",
            is_active=True,
        )
        user.password = "testpassword123"
        user.save()
        return user

    @pytest.fixture
    def perm_test_org(self, perm_test_user):
        """Create org with user as member."""
        org_id = uuid.uuid4()
        org = Organisation.objects.create(
            id=org_id,
            name="Permission Test Org",
            legal_name="Permission Test Org Pte Ltd",
            uen="PERMTEST01",
            entity_type="PRIVATE_LIMITED",
            base_currency="SGD",
            is_active=True,
        )

        # Regular user role without special permissions
        user_role = Role.objects.create(
            org=org,
            name="User",
            description="Regular user",
            can_manage_org=False,
            can_manage_users=False,
            can_manage_coa=False,
            can_create_invoices=True,
            can_approve_invoices=False,
            can_void_invoices=False,
            can_create_journals=False,
            can_manage_banking=False,
            can_file_gst=False,
            can_view_reports=True,
            can_export_data=False,
            is_system=False,
        )

        from datetime import datetime

        UserOrganisation.objects.create(
            user=perm_test_user,
            org=org,
            role=user_role,
            is_default=True,
            accepted_at=datetime.now(),
        )

        return org

    @pytest.fixture
    def perm_auth_client(self, perm_test_user):
        """Return authenticated client."""
        client = APIClient()
        from rest_framework_simplejwt.tokens import RefreshToken

        refresh = RefreshToken.for_user(perm_test_user)
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {str(refresh.access_token)}")
        return client

    def test_regular_user_can_access_transmission_log(self, perm_auth_client, perm_test_org):
        """Test regular org member can access transmission log."""
        url = f"/api/v1/{perm_test_org.id}/peppol/transmission-log/"
        response = perm_auth_client.get(url)

        assert response.status_code == status.HTTP_200_OK

    def test_regular_user_can_access_settings(self, perm_auth_client, perm_test_org):
        """Test regular org member can access Peppol settings."""
        url = f"/api/v1/{perm_test_org.id}/peppol/settings/"
        response = perm_auth_client.get(url)

        assert response.status_code == status.HTTP_200_OK

    def test_regular_user_can_patch_settings(self, perm_auth_client, perm_test_org):
        """Test regular org member can update Peppol settings."""
        url = f"/api/v1/{perm_test_org.id}/peppol/settings/"
        response = perm_auth_client.patch(url, {"enabled": True}, format="json")

        # Current implementation allows any org member to update
        assert response.status_code == status.HTTP_200_OK
