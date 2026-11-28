"""
Integration tests for Organisation API endpoints.

Tests organisation CRUD, GST registration, fiscal years, and summary.
"""


import pytest
from rest_framework import status

from apps.core.models import Account, FiscalPeriod, FiscalYear, Organisation


@pytest.mark.django_db
def test_list_organisations_success(auth_client, test_user, test_organisation):
    """Test listing user's organisations."""
    url = "/api/v1/organisations/"

    response = auth_client.get(url)

    assert response.status_code == status.HTTP_200_OK
    # P21/BE-M6: the unified list envelope ({results, count}).
    assert "results" in response.data
    assert len(response.data["results"]) >= 1
    assert response.data["count"] >= 1

    # Check the test org is in the list
    org_ids = [org["id"] for org in response.data["results"]]
    assert str(test_organisation.id) in org_ids


@pytest.mark.django_db
def test_list_organisations_unauthenticated(api_client):
    """Test listing organisations without auth fails."""
    url = "/api/v1/organisations/"

    response = api_client.get(url)

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
def test_create_organisation_success(auth_client, test_user):
    """Test creating a new organisation."""
    url = "/api/v1/organisations/"
    data = {
        "name": "New Test Organisation",
        "legal_name": "New Test Organisation Pte Ltd",
        "uen": "987654321B",
        "gst_registered": False,
        "fy_start_month": 4,
        "base_currency": "SGD"
    }

    response = auth_client.post(url, data, format="json")

    assert response.status_code == status.HTTP_201_CREATED
    assert response.data["name"] == "New Test Organisation"
    assert response.data["legal_name"] == "New Test Organisation Pte Ltd"

    # Verify org was created
    org_id = response.data["id"]
    org = Organisation.objects.get(id=org_id)
    assert org.name == "New Test Organisation"
    assert org.base_currency == "SGD"

    # Verify user is Owner
    membership = org.user_memberships.filter(user=test_user).first()
    assert membership is not None
    assert membership.role.name == "Owner"


@pytest.mark.django_db
def test_get_organisation_detail_success(auth_client, test_organisation):
    """Test getting organisation details."""
    url = f"/api/v1/{test_organisation.id}/"

    response = auth_client.get(url)

    assert response.status_code == status.HTTP_200_OK
    assert response.data["id"] == str(test_organisation.id)
    assert response.data["name"] == test_organisation.name
    assert response.data["legal_name"] == test_organisation.legal_name


@pytest.mark.django_db
def test_get_organisation_detail_not_member(auth_client):
    """Test getting org details when not a member fails."""
    # Create org without adding user
    import uuid

    from apps.core.models import Organisation
    other_org = Organisation.objects.create(
        name="Other Org",
        legal_name="Other Org Pte Ltd",
        base_currency="SGD",
        uen=f"UEN{uuid.uuid4().hex[:8]}".upper()
    )

    url = f"/api/v1/{other_org.id}/"
    response = auth_client.get(url)

    # Should be forbidden or not found
    assert response.status_code in [status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND]


@pytest.mark.django_db
def test_update_organisation_success(auth_client, test_organisation):
    """Test updating organisation settings."""
    url = f"/api/v1/{test_organisation.id}/"
    data = {
        "name": "Updated Organisation Name",
        "contact_email": "new@example.com"
    }

    response = auth_client.patch(url, data, format="json")

    assert response.status_code == status.HTTP_200_OK
    assert response.data["name"] == "Updated Organisation Name"
    assert response.data["contact_email"] == "new@example.com"

    # Verify in database
    test_organisation.refresh_from_db()
    assert test_organisation.name == "Updated Organisation Name"


@pytest.mark.django_db
def test_deactivate_organisation_success(auth_client, test_organisation):
    """Test deactivating an organisation."""
    url = f"/api/v1/{test_organisation.id}/"

    response = auth_client.delete(url)

    # Should be 204 No Content or 200 OK
    assert response.status_code in [status.HTTP_204_NO_CONTENT, status.HTTP_200_OK]

    # Verify deactivated
    test_organisation.refresh_from_db()
    assert test_organisation.is_active is False


@pytest.mark.django_db
def test_gst_registration_success(auth_client, test_organisation):
    """Test registering organisation for GST."""
    # First, create org without GST
    test_organisation.gst_registered = False
    test_organisation.gst_reg_number = ""
    test_organisation.save()

    url = f"/api/v1/{test_organisation.id}/gst/"
    data = {
        "gst_reg_number": "M87654321W",
        "gst_reg_date": "2024-06-01"
    }

    response = auth_client.post(url, data, format="json")

    assert response.status_code == status.HTTP_200_OK
    assert response.data["gst_registered"] is True
    assert response.data["gst_reg_number"] == "M87654321W"

    # Verify in database
    test_organisation.refresh_from_db()
    assert test_organisation.gst_registered is True


@pytest.mark.django_db
def test_gst_deregistration_success(auth_client, test_organisation):
    """Test deregistering from GST."""
    url = f"/api/v1/{test_organisation.id}/gst/"

    response = auth_client.delete(url)

    assert response.status_code == status.HTTP_200_OK
    assert response.data["gst_registered"] is False
    assert response.data["gst_reg_number"] == ""


@pytest.mark.django_db
def test_list_fiscal_years_success(auth_client, test_organisation, test_fiscal_period):
    """Test listing fiscal years for organisation."""
    url = f"/api/v1/{test_organisation.id}/fiscal-years/"

    response = auth_client.get(url)

    assert response.status_code == status.HTTP_200_OK
    # P21/BE-M6: the unified list envelope ({results, count}).
    assert "results" in response.data
    assert len(response.data["results"]) >= 1


@pytest.mark.django_db
def test_get_organisation_summary_success(auth_client, test_organisation, test_fiscal_period):
    """Test getting organisation summary."""
    url = f"/api/v1/{test_organisation.id}/summary/"

    response = auth_client.get(url)

    assert response.status_code == status.HTTP_200_OK
    assert "organisation" in response.data
    assert "current_fiscal_year" in response.data
    assert "member_count" in response.data
    assert response.data["organisation"]["id"] == str(test_organisation.id)


@pytest.mark.django_db
def test_organisation_creation_seeds_coa(auth_client, test_user):
    """Test that organisation creation seeds Chart of Accounts."""
    url = "/api/v1/organisations/"
    data = {
        "name": "Org With CoA",
        "legal_name": "Org With CoA Pte Ltd",
        "gst_registered": True,
        "gst_reg_number": "M11111111Z",
        "gst_reg_date": "2024-01-01",
        "base_currency": "SGD"
    }

    response = auth_client.post(url, data, format="json")

    assert response.status_code == status.HTTP_201_CREATED
    org_id = response.data["id"]

    # Verify accounts were created
    accounts = Account.objects.filter(org_id=org_id)
    assert accounts.count() > 0

    # Should have system accounts
    system_accounts = accounts.filter(is_system=True)
    assert system_accounts.count() > 0


@pytest.mark.django_db
def test_organisation_creation_creates_fiscal_year(auth_client, test_user):
    """Test that organisation creation creates fiscal year."""
    url = "/api/v1/organisations/"
    data = {
        "name": "Org With Fiscal",
        "legal_name": "Org With Fiscal Pte Ltd",
        "fy_start_month": 1,
        "base_currency": "SGD"
    }

    response = auth_client.post(url, data, format="json")

    assert response.status_code == status.HTTP_201_CREATED
    org_id = response.data["id"]

    # Verify fiscal year was created
    fiscal_years = FiscalYear.objects.filter(org_id=org_id)
    assert fiscal_years.count() >= 1

    # Verify periods were created
    fy = fiscal_years.first()
    periods = FiscalPeriod.objects.filter(fiscal_year=fy)
    assert periods.count() == 12  # Should have 12 months


@pytest.mark.django_db
def test_update_organisation_address_fields(auth_client, test_organisation):
    """P6/F-10: the real address fields must be updatable via PATCH.

    The view and service allowlists forwarded a phantom `address` key (the
    model has no such field — it was silently dropped) while the real
    address_line_1/2, city, postal_code, country fields were filtered out.
    """
    url = f"/api/v1/{test_organisation.id}/"
    data = {
        "address_line_1": "12 Marina Boulevard",
        "address_line_2": "#05-01 Marina Bay Financial Centre",
        "city": "Singapore",
        "postal_code": "018982",
        "country": "SG",
    }

    response = auth_client.patch(url, data, format="json")

    assert response.status_code == status.HTTP_200_OK, response.data
    assert response.data["address_line_1"] == "12 Marina Boulevard"
    assert response.data["address_line_2"] == "#05-01 Marina Bay Financial Centre"
    assert response.data["city"] == "Singapore"
    assert response.data["postal_code"] == "018982"
    assert response.data["country"] == "SG"

    test_organisation.refresh_from_db()
    assert test_organisation.address_line_1 == "12 Marina Boulevard"
    assert test_organisation.city == "Singapore"
    assert test_organisation.postal_code == "018982"


@pytest.mark.django_db
def test_update_organisation_phantom_address_is_noop(auth_client, test_organisation):
    """P6/F-10: a PATCH carrying the old phantom `address` key must not
    corrupt anything — the key does not map to a model field."""
    url = f"/api/v1/{test_organisation.id}/"
    original_line_1 = test_organisation.address_line_1

    response = auth_client.patch(
        url, {"address": "123 Nowhere Street"}, format="json"
    )

    assert response.status_code == status.HTTP_200_OK, response.data
    test_organisation.refresh_from_db()
    assert test_organisation.address_line_1 == original_line_1


@pytest.mark.django_db
def test_create_organisation_with_address_field_is_no_crash(auth_client):
    """P7/F-3: the create serializer advertised an `address` field the
    Organisation model does not have — POSTing it (a field the API itself
    declared) crashed with TypeError -> 500. The phantom field is gone;
    sending it is a clean no-op exactly like the PATCH path (P6/F-10)."""
    url = "/api/v1/organisations/"
    data = {
        "name": "Address Sender Org",
        "legal_name": "Address Sender Pte Ltd",
        "uen": "53012345X",
        "address": "12 Marina Boulevard",
        "contact_email": "ops@address-sender.sg",
        "contact_phone": "+65 6555 0000",
    }

    response = auth_client.post(url, data, format="json")

    assert response.status_code == status.HTTP_201_CREATED, response.data
    org = Organisation.objects.get(id=response.data["id"])
    # The phantom key is ignored (no crash, no phantom attribute write).
    assert not hasattr(org, "address")
    # Real contact fields round-trip.
    assert org.contact_email == "ops@address-sender.sg"
    assert org.contact_phone == "+65 6555 0000"


@pytest.mark.django_db
def test_create_organisation_serializer_has_no_address_field():
    """The serializer must not declare a field the model lacks (schema-truth
    gate for the P7/F-3 fix)."""
    from apps.core.serializers.organisation import OrganisationCreateSerializer

    fields = OrganisationCreateSerializer().fields
    assert "address" not in fields, fields.keys()
    for real_field in ("name", "legal_name", "uen", "gst_registered"):
        assert real_field in fields


def _org_create_payload(**overrides):
    base = {
        "name": "UEN Guard Org",
        "uen": "202312345D",
        "entity_type": "PRIVATE_LIMITED",
        "gst_registered": False,
        "fy_start_month": 1,
        "base_currency": "SGD",
    }
    base.update(overrides)
    return base


@pytest.mark.django_db
def test_create_organisation_duplicate_uen_is_a_clean_400(auth_client, test_user):
    """P10 (found during the live e2e gate): the DB enforces uen UNIQUE
    (core.organisation.uen) but the create serializer never checked, so a
    taken UEN surfaced as an unhandled IntegrityError -> 500 instead of a
    client error the org-create form can show."""
    url = "/api/v1/organisations/"

    first = auth_client.post(url, _org_create_payload(), format="json")
    assert first.status_code == status.HTTP_201_CREATED

    second = auth_client.post(url, _org_create_payload(name="UEN Guard Org 2"), format="json")
    assert second.status_code == status.HTTP_400_BAD_REQUEST, second.data
    assert "uen" in second.data, second.data


@pytest.mark.django_db
def test_update_organisation_duplicate_uen_is_a_clean_400(auth_client, test_organisation):
    """Same guard on the settings PATCH: pointing an org's UEN at another
    org's UEN must be a 400 field error, not an IntegrityError 500."""
    Organisation.objects.create(
        name="Other Org",
        legal_name="Other Org Pte Ltd",
        uen="202399999X",
        fy_start_month=1,
        base_currency="SGD",
        is_active=True,
    )

    response = auth_client.patch(
        f"/api/v1/{test_organisation.id}/",
        {"uen": "202399999X"},
        format="json",
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST, response.data
    assert "uen" in response.data, response.data
