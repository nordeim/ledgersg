"""
Integration tests for Organisation Settings API endpoint (GAP-4).

Tests GET and PATCH operations for organisation settings.
Run with: pytest tests/integration/test_organisation_settings.py -v
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
class TestOrganisationSettingsView:
    """Test suite for OrganisationSettingsView API endpoint."""

    @pytest.fixture
    def settings_test_user(self):
        """Create a test user for settings tests."""
        user_id = uuid.uuid4()
        user = AppUser.objects.create(
            id=user_id,
            email=f"settings_test_{user_id.hex[:8]}@example.com",
            full_name="Settings Test User",
            is_active=True,
        )
        user.password = "testpassword123"
        user.save()
        return user

    @pytest.fixture
    def settings_test_org(self, settings_test_user):
        """Create organisation for settings testing."""
        org_id = uuid.uuid4()
        org = Organisation.objects.create(
            id=org_id,
            name="Settings Test Org",
            legal_name="Settings Test Org Pte Ltd",
            uen="SETTINGS01",
            entity_type="PRIVATE_LIMITED",
            gst_registered=True,
            gst_reg_number="M12345678",
            gst_reg_date=date(2024, 1, 1),
            gst_scheme="STANDARD",
            gst_filing_frequency="QUARTERLY",
            fy_start_month=1,
            base_currency="SGD",
            timezone="Asia/Singapore",
            peppol_participant_id="0195:SGUEN123456789",
            invoicenow_enabled=True,
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
        """Return an authenticated APIClient."""
        client = APIClient()
        from rest_framework_simplejwt.tokens import RefreshToken

        refresh = RefreshToken.for_user(settings_test_user)
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {str(refresh.access_token)}")
        return client

    def test_get_settings_success(self, settings_auth_client, settings_test_org):
        """Test GET /api/v1/{orgId}/settings/ returns all settings."""
        url = f"/api/v1/{settings_test_org.id}/settings/"
        response = settings_auth_client.get(url)

        assert response.status_code == status.HTTP_200_OK

        data = response.data

        # Verify all 13 settings fields are present
        expected_fields = [
            "id",
            "name",
            "legal_name",
            "uen",
            "entity_type",
            "base_currency",
            "timezone",
            "fy_start_month",
            "gst_registered",
            "gst_reg_number",
            "gst_scheme",
            "gst_filing_frequency",
            "peppol_participant_id",
            "invoicenow_enabled",
        ]

        for field in expected_fields:
            assert field in data, f"Missing required field: {field}"

        # Verify values match test org
        assert data["id"] == str(settings_test_org.id)
        assert data["name"] == "Settings Test Org"
        assert data["legal_name"] == "Settings Test Org Pte Ltd"
        assert data["uen"] == "SETTINGS01"
        assert data["entity_type"] == "PRIVATE_LIMITED"
        assert data["base_currency"] == "SGD"
        assert data["timezone"] == "Asia/Singapore"
        assert data["fy_start_month"] == 1
        assert data["gst_registered"] is True
        assert data["gst_reg_number"] == "M12345678"
        assert data["gst_scheme"] == "STANDARD"
        assert data["gst_filing_frequency"] == "QUARTERLY"
        assert data["peppol_participant_id"] == "0195:SGUEN123456789"
        assert data["invoicenow_enabled"] is True

    def test_get_settings_requires_authentication(self, settings_test_org):
        """Test GET settings without authentication fails."""
        client = APIClient()
        url = f"/api/v1/{settings_test_org.id}/settings/"
        response = client.get(url)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_get_settings_requires_org_membership(self, settings_auth_client):
        """Test GET settings when not an org member fails."""
        # Create org without adding user
        other_org = Organisation.objects.create(
            name="Other Org",
            legal_name="Other Org Pte Ltd",
            uen="OTHER001",
            entity_type="PRIVATE_LIMITED",
            base_currency="SGD",
            is_active=True,
        )

        url = f"/api/v1/{other_org.id}/settings/"
        response = settings_auth_client.get(url)

        # Should be forbidden or not found
        assert response.status_code in [status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND]

    def test_get_settings_not_found(self, settings_auth_client):
        """Test GET settings for non-existent org returns 403/404."""
        fake_org_id = uuid.uuid4()
        url = f"/api/v1/{fake_org_id}/settings/"
        response = settings_auth_client.get(url)

        # Permission middleware returns 403 for non-existent orgs
        # OR the view returns 404 if the user has permission but org doesn't exist
        assert response.status_code in [status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND]
        # If 404, check error structure
        if response.status_code == status.HTTP_404_NOT_FOUND:
            assert "error" in response.data

    def test_patch_settings_success(self, settings_auth_client, settings_test_org):
        """Test PATCH /api/v1/{orgId}/settings/ updates allowed fields."""
        url = f"/api/v1/{settings_test_org.id}/settings/"
        update_data = {
            "name": "Updated Organisation Name",
            "legal_name": "Updated Legal Name Pte Ltd",
            "uen": "NEWUEN123",
            "timezone": "UTC",
            "fy_start_month": 4,
        }

        response = settings_auth_client.patch(url, update_data, format="json")

        assert response.status_code == status.HTTP_200_OK
        data = response.data
        assert data["message"] == "Settings updated successfully"
        assert "updated_fields" in data

        # Verify updated fields are listed
        updated_fields = data["updated_fields"]
        for field in update_data.keys():
            assert field in updated_fields

        # Verify changes persisted to database
        settings_test_org.refresh_from_db()
        assert settings_test_org.name == "Updated Organisation Name"
        assert settings_test_org.legal_name == "Updated Legal Name Pte Ltd"
        assert settings_test_org.uen == "NEWUEN123"
        assert settings_test_org.timezone == "UTC"
        assert settings_test_org.fy_start_month == 4

    def test_patch_gst_settings(self, settings_auth_client, settings_test_org):
        """Test PATCH can update GST-related settings."""
        url = f"/api/v1/{settings_test_org.id}/settings/"
        update_data = {
            "gst_registered": False,
            "gst_reg_number": "",
            "gst_scheme": "CASH",
            "gst_filing_frequency": "MONTHLY",
        }

        response = settings_auth_client.patch(url, update_data, format="json")

        assert response.status_code == status.HTTP_200_OK

        # Verify response structure
        data = response.data
        assert data["message"] == "Settings updated successfully"
        assert "updated_fields" in data

        # Verify changes
        settings_test_org.refresh_from_db()
        assert settings_test_org.gst_registered is False
        assert settings_test_org.gst_reg_number == ""
        assert settings_test_org.gst_scheme == "CASH"
        assert settings_test_org.gst_filing_frequency == "MONTHLY"

    def test_patch_peppol_settings(self, settings_auth_client, settings_test_org):
        """Test PATCH can update Peppol/InvoiceNow settings."""
        url = f"/api/v1/{settings_test_org.id}/settings/"
        update_data = {
            "invoicenow_enabled": False,
            "peppol_participant_id": "0195:NEWID123",
        }

        response = settings_auth_client.patch(url, update_data, format="json")

        assert response.status_code == status.HTTP_200_OK

        # Verify response structure
        data = response.data
        assert data["message"] == "Settings updated successfully"

        # Verify changes
        settings_test_org.refresh_from_db()
        assert settings_test_org.invoicenow_enabled is False
        assert settings_test_org.peppol_participant_id == "0195:NEWID123"

    def test_patch_settings_ignores_disallowed_fields(
        self, settings_auth_client, settings_test_org
    ):
        """Test PATCH ignores fields not in allowed_fields list."""
        url = f"/api/v1/{settings_test_org.id}/settings/"
        original_email = settings_test_org.email

        update_data = {
            "name": "Updated Name",
            "email": "hacker@evil.com",  # Should be ignored
            "is_active": False,  # Should be ignored
        }

        response = settings_auth_client.patch(url, update_data, format="json")

        assert response.status_code == status.HTTP_200_OK

        # Verify response only shows allowed field as updated
        data = response.data
        assert "updated_fields" in data
        assert "name" in data["updated_fields"]
        assert "email" not in data["updated_fields"]
        assert "is_active" not in data["updated_fields"]

        # Verify only allowed field was updated in database
        settings_test_org.refresh_from_db()
        assert settings_test_org.name == "Updated Name"
        assert settings_test_org.email == original_email  # Unchanged
        assert settings_test_org.is_active is True  # Unchanged

    def test_patch_settings_empty_update(self, settings_auth_client, settings_test_org):
        """Test PATCH with empty data returns success but no updates."""
        url = f"/api/v1/{settings_test_org.id}/settings/"
        response = settings_auth_client.patch(url, {}, format="json")

        assert response.status_code == status.HTTP_200_OK
        data = response.data
        assert data["message"] == "Settings updated successfully"
        assert data["updated_fields"] == []

    def test_patch_settings_not_found(self, settings_auth_client):
        """Test PATCH for non-existent org returns 403/404."""
        fake_org_id = uuid.uuid4()
        url = f"/api/v1/{fake_org_id}/settings/"
        response = settings_auth_client.patch(url, {"name": "Test"}, format="json")

        # Permission middleware returns 403 for non-existent orgs
        assert response.status_code in [status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND]
        # If 404, check error structure
        if response.status_code == status.HTTP_404_NOT_FOUND:
            assert "error" in response.data

    def test_post_not_allowed(self, settings_auth_client, settings_test_org):
        """Test POST method is not allowed."""
        url = f"/api/v1/{settings_test_org.id}/settings/"
        response = settings_auth_client.post(url, {}, format="json")

        assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED

    def test_put_not_allowed(self, settings_auth_client, settings_test_org):
        """Test PUT method is not allowed."""
        url = f"/api/v1/{settings_test_org.id}/settings/"
        response = settings_auth_client.put(url, {}, format="json")

        assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED

    def test_delete_not_allowed(self, settings_auth_client, settings_test_org):
        """Test DELETE method is not allowed."""
        url = f"/api/v1/{settings_test_org.id}/settings/"
        response = settings_auth_client.delete(url)

        assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED
