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
        # P8/G-2 — the gaps the P7 sweep missed in the same functions:
        ("banking payments contact_id", lambda org: f"/api/v1/{org.id}/banking/payments/?contact_id=not-a-uuid"),
        ("banking payments bank_account_id", lambda org: f"/api/v1/{org.id}/banking/payments/?bank_account_id=not-a-uuid"),
        ("banking transactions bank_account_id", lambda org: f"/api/v1/{org.id}/banking/bank-transactions/?bank_account_id=not-a-uuid"),
        ("journal ledger date_from", lambda org: f"/api/v1/{org.id}/journal-entries/ledger/?date_from=not-a-date"),
        ("journal ledger date_to", lambda org: f"/api/v1/{org.id}/journal-entries/ledger/?date_to=not-a-date"),
        ("coa search negative limit", lambda org: f"/api/v1/{org.id}/accounts/search/?q=x&limit=-1"),
        ("gst deadlines negative days", lambda org: f"/api/v1/{org.id}/gst/returns/deadlines/?days=-5"),
        ("reports financial start_date", lambda org: f"/api/v1/{org.id}/reports/financial/?report_type=profit_loss&start_date=not-a-date"),
        ("reports financial end_date", lambda org: f"/api/v1/{org.id}/reports/financial/?report_type=profit_loss&end_date=not-a-date"),
        ("reports financial as_at_date", lambda org: f"/api/v1/{org.id}/reports/financial/?report_type=balance_sheet&as_at_date=not-a-date"),
        # P9/S-1 + B-7 — the last siblings of the sweep:
        ("invoicing documents date_from", lambda org: f"/api/v1/{org.id}/invoicing/documents/?date_from=not-a-date"),
        ("invoicing documents date_to", lambda org: f"/api/v1/{org.id}/invoicing/documents/?date_to=not-a-date"),
        (
            "banking suggest-matches tolerance",
            lambda org: f"/api/v1/{org.id}/banking/bank-transactions/00000000-0000-0000-0000-000000000000/suggest-matches/?tolerance=abc",
        ),
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


class TestSuggestMatchesRoute404P18:
    """P18/BE-L2: suggest-matches moved from <str> to the uuid route
    converter (the P17 sibling parity) — a malformed transaction_id is
    now a ROUTING 404, not a view-level 400. The case was removed from
    the 400 sweep above; its contract lives here."""

    @pytest.mark.django_db
    def test_malformed_transaction_id_is_route_404(self, auth_client, test_organisation):
        url = f"/api/v1/{test_organisation.id}/banking/bank-transactions/not-a-uuid/suggest-matches/"
        response = auth_client.get(url)
        assert response.status_code == status.HTTP_404_NOT_FOUND, (
            response.status_code,
            getattr(response, "data", None),
        )
