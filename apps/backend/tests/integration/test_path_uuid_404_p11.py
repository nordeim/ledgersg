"""
P11/M-6 — garbage path UUIDs 404 at the routing layer.

The org-scoped detail routes bound their ids as <str:..._id> and the views
call raw UUID(...) on them — a garbage segment ('abc') raises ValueError
→ unhandled 500 across journal/gst/banking/invoicing detail routes (the
P7/F-11 sweep covered query params only). The routes now bind
<uuid:..._id> so malformed UUIDs fail routing (404) before any view code
runs.
"""

import uuid
from datetime import date

import pytest
from rest_framework import status

from apps.core.models import AppUser, Organisation, Role, UserOrganisation

pytestmark = pytest.mark.django_db

# One org-scoped detail route per module (GET, no side effects).
GARBAGE_SWEEP = [
    ("journal", "journal-entries/entries/{garbage}/"),
    ("gst", "gst/returns/{garbage}/"),
    ("banking", "banking/bank-accounts/{garbage}/"),
    ("invoicing", "invoicing/contacts/{garbage}/"),
]


def _org_with_member():
    user = AppUser.objects.create(
        id=uuid.uuid4(),
        email=f"sweep_{uuid.uuid4().hex[:8]}@example.com",
        full_name="Sweep Tester",
        is_active=True,
    )
    org = Organisation.objects.create(
        name="Sweep Org",
        entity_type="PRIVATE_LIMITED",
        base_currency="SGD",
        uen=f"T{uuid.uuid4().hex[:9].upper()}",
    )
    role = Role.objects.create(org=org, name="Owner", description="o")
    UserOrganisation.objects.create(
        user=user, org=org, role=role, is_default=True,
        invited_at=date.today(), accepted_at=date.today(),
    )
    return user, org


def _client(user):
    from rest_framework.test import APIClient
    from rest_framework_simplejwt.tokens import RefreshToken

    client = APIClient()
    refresh = RefreshToken.for_user(user)
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {str(refresh.access_token)}")
    return client


class TestGarbagePathUUIDs404:
    @pytest.mark.parametrize(
        "module, route_template", GARBAGE_SWEEP, ids=[m for m, _ in GARBAGE_SWEEP]
    )
    def test_garbage_uuid_in_path_returns_404(self, module, route_template):
        """RED for M-6: 'abc' as the id segment must 404 (today: 500)."""
        user, org = _org_with_member()
        client = _client(user)

        response = client.get(
            f"/api/v1/{org.id}/{route_template.format(garbage='abc')}", format="json"
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND, (
            f"[{module}] a garbage path UUID must fail routing with 404 — "
            f"got {response.status_code}"
        )

    def test_valid_uuid_in_path_still_routes(self):
        """Regression guard: a well-formed (nonexistent) UUID 404s via the view."""
        user, org = _org_with_member()
        client = _client(user)
        missing = uuid.uuid4()

        response = client.get(
            f"/api/v1/{org.id}/invoicing/contacts/{missing}/", format="json"
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND
