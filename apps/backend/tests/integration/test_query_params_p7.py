"""P7/F-11: malformed query params must 400, not 500.

The audited sites parsed request.GET values with bare dt.strptime / UUID /
int — a garbage value raised and surfaced as an unhandled 500 (and
banking's tolerance probe silently DEFAULTED an invalid value via a bare
except:).
"""

import pytest
from rest_framework import status


@pytest.mark.django_db
class TestQueryParamValidation:
    """Each case posts a garbage value for a param the endpoint parses."""

    CASES = [
        # (label, url factory)
        ("banking payments date_from", lambda org: f"/api/v1/{org.id}/banking/payments/?date_from=not-a-date"),
        ("banking transactions date_to", lambda org: f"/api/v1/{org.id}/banking/bank-transactions/?date_to=not-a-date"),
        ("journal entries date_from", lambda org: f"/api/v1/{org.id}/journal-entries/entries/?date_from=not-a-date"),
        ("journal ledger account_id", lambda org: f"/api/v1/{org.id}/journal-entries/ledger/?account_id=not-a-uuid"),
        ("coa trial balance fiscal_year_id", lambda org: f"/api/v1/{org.id}/accounts/trial-balance/?fiscal_year_id=not-a-uuid"),
        ("gst deadlines days", lambda org: f"/api/v1/{org.id}/gst/returns/deadlines/?days=not-a-number"),
    ]

    @pytest.mark.parametrize("label,url_factory", CASES, ids=[c[0] for c in CASES])
    def test_garbage_params_are_400_not_500(self, auth_client, test_organisation, label, url_factory):
        url = url_factory(test_organisation)
        response = auth_client.get(url)
        assert response.status_code == status.HTTP_400_BAD_REQUEST, (
            label,
            response.status_code,
            getattr(response, "data", None),
        )

    def test_valid_params_still_work(self, auth_client, test_organisation):
        """Sanity: the same endpoints accept valid values (200) — the fix
        must not over-reject."""
        url = f"/api/v1/{test_organisation.id}/journal-entries/entries/?date_from=2024-01-01"
        response = auth_client.get(url)
        assert response.status_code == status.HTTP_200_OK, response.data
