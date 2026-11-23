"""
P11/M-8 — the audit trail carries its context.

The middleware set app.client_ip/user_agent/request_path per request for
the trigger to read, but the trigger's INSERT never read them — the
columns (ip_address INET, user_agent TEXT, request_path VARCHAR(500))
stayed NULL on every row. LOGIN/LOGOUT were in the CHECK vocabulary but
never emitted by any code.
"""

import pytest
from rest_framework import status

from apps.core.models import AuditEventLog

pytestmark = pytest.mark.django_db


class TestLoginLogoutAuditEmission:
    def test_login_writes_audit_row_with_request_context(self, api_client, test_user):
        """RED for M-8: a successful login emits a LOGIN audit row with ip/path."""
        response = api_client.post(
            "/api/v1/auth/login/",
            {"email": test_user.email, "password": "testpassword123"},
            format="json",
        )

        assert response.status_code == status.HTTP_200_OK, response.content

        row = AuditEventLog.objects.filter(
            user_id=test_user.id, action="LOGIN"
        ).first()
        assert row is not None, (
            "a successful login must emit a LOGIN audit row — LOGIN is in the "
            "event_log CHECK vocabulary but no code ever emitted it"
        )
        assert str(row.ip_address) == "127.0.0.1", (
            f"the LOGIN row must carry the request's REMOTE_ADDR (got "
            f"{row.ip_address})"
        )
        assert row.request_path == "/api/v1/auth/login/"
        assert row.entity_id == test_user.id

    def test_logout_writes_audit_row(self, api_client, test_user):
        """RED for M-8: logout emits a LOGOUT audit row."""
        from rest_framework_simplejwt.tokens import RefreshToken

        api_client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {str(RefreshToken.for_user(test_user).access_token)}"
        )
        response = api_client.post("/api/v1/auth/logout/", {}, format="json")

        assert response.status_code == status.HTTP_200_OK, response.content

        row = AuditEventLog.objects.filter(
            user_id=test_user.id, action="LOGOUT"
        ).first()
        assert row is not None, "logout must emit a LOGOUT audit row"
        assert str(row.ip_address) == "127.0.0.1"

    def test_failed_login_writes_no_row(self, api_client, test_user):
        """A failed login emits nothing (audit trails record successes)."""
        response = api_client.post(
            "/api/v1/auth/login/",
            {"email": test_user.email, "password": "wrongpassword"},
            format="json",
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

        assert not AuditEventLog.objects.filter(action="LOGIN").exists()


class TestTriggerRowsCarryRequestContext:
    def test_row_level_write_carries_ip_path_user_agent(
        self, auth_client, test_organisation, test_user, test_accounts
    ):
        """RED for M-8: the trigger INSERT reads the middleware's variables.

        A contact created through the API must produce a CREATE audit row
        carrying the request's ip_address/user_agent/request_path — the
        columns existed but the trigger never populated them.
        """
        response = auth_client.post(
            f"/api/v1/{test_organisation.id}/invoicing/contacts/",
            {
                "name": "Audited Contact",
                "contact_type": "CUSTOMER",
                "is_customer": True,
            },
            format="json",
            HTTP_USER_AGENT="p11-audit-probe/1.0",
        )

        assert response.status_code == status.HTTP_201_CREATED, response.content

        row = AuditEventLog.objects.filter(
            action="CREATE", entity_table="contact"
        ).order_by("-created_at").first()
        assert row is not None, "the contact CREATE must land a trigger audit row"
        assert str(row.ip_address) == "127.0.0.1", (
            f"the trigger row must read app.client_ip (got {row.ip_address})"
        )
        assert row.user_agent == "p11-audit-probe/1.0", (
            f"the trigger row must read app.user_agent (got {row.user_agent!r})"
        )
        assert row.request_path and "contacts" in row.request_path, (
            f"the trigger row must read app.request_path (got {row.request_path!r})"
        )
