"""
P6/C-5 (ledger) — the general-ledger endpoint.

RED suite: the ledger page needs flat line-level rows (entry joined with
line + account). The existing entries list endpoint returns aggregated
entries (totals, line counts) which cannot drive a line-level table.
"""

from datetime import date
from decimal import Decimal
from uuid import uuid4

import pytest

from apps.core.models import Organisation
from apps.journal.services import JournalService

pytestmark = pytest.mark.django_db


def _create_entry(org, fiscal_period, user, ar_account, revenue_account, day=15):
    return JournalService.create_entry(
        org_id=org.id,
        entry_date=date(2024, 1, day),
        source_type="MANUAL",
        narration="Ledger test entry",
        fiscal_period_id=fiscal_period.id,
        lines=[
            {
                "account_id": ar_account.id,
                "description": "AR increase",
                "debit": Decimal("100.00"),
                "credit": Decimal("0.00"),
            },
            {
                "account_id": revenue_account.id,
                "description": "Revenue recognition",
                "debit": Decimal("0.00"),
                "credit": Decimal("100.00"),
            },
        ],
        user_id=user.id,
    )


def test_ledger_endpoint_returns_flat_lines(
    auth_client, test_organisation, test_accounts, test_fiscal_period, test_user
):
    _create_entry(
        test_organisation,
        test_fiscal_period,
        test_user,
        test_accounts["1200"],
        test_accounts["4000"],
    )

    url = f"/api/v1/{test_organisation.id}/journal-entries/ledger/"

    response = auth_client.get(url)

    assert response.status_code == 200, response.data
    body = response.data
    assert "results" in body
    assert body["count"] == 2, "both lines of the entry must be returned"

    rows = body["results"]
    fields = {
        "id", "entry_id", "entry_number", "entry_date", "source_type",
        "reference", "narration", "line_number", "account_id",
        "account_code", "account_name", "description", "debit", "credit",
    }
    for row in rows:
        assert fields.issubset(row.keys()), f"missing: {fields - set(row.keys())}"

    ar_row = next(r for r in rows if r["account_code"] == "1200")
    assert ar_row["account_name"] == "Accounts Receivable"
    assert ar_row["debit"] == "100.0000"
    assert ar_row["credit"] == "0.0000"
    assert ar_row["entry_number"] == 1
    assert ar_row["description"] == "AR increase"

    rev_row = next(r for r in rows if r["account_code"] == "4000")
    assert rev_row["credit"] == "100.0000"


def test_ledger_endpoint_is_org_scoped(
    auth_client, test_organisation, test_accounts, test_fiscal_period, test_user
):
    """Another organisation's ledger must not leak into the response."""
    _create_entry(
        test_organisation,
        test_fiscal_period,
        test_user,
        test_accounts["1200"],
        test_accounts["4000"],
    )

    other_org = Organisation.objects.create(
        id=uuid4(),
        name="Other Org",
        uen="OTHERORG1",
        entity_type="PRIVATE_LIMITED",
        fy_start_month=1,
        base_currency="SGD",
        is_active=True,
    )

    url = f"/api/v1/{other_org.id}/journal-entries/ledger/"
    response = auth_client.get(url)

    # Not a member of other_org — the org-scope middleware guards it.
    assert response.status_code in (403, 404)


def test_ledger_endpoint_date_filter(
    auth_client, test_organisation, test_accounts, test_fiscal_period, test_user
):
    _create_entry(
        test_organisation,
        test_fiscal_period,
        test_user,
        test_accounts["1200"],
        test_accounts["4000"],
        day=10,
    )
    _create_entry(
        test_organisation,
        test_fiscal_period,
        test_user,
        test_accounts["1200"],
        test_accounts["4000"],
        day=20,
    )

    url = f"/api/v1/{test_organisation.id}/journal-entries/ledger/"

    response = auth_client.get(url, {"date_from": "2024-01-15"})

    assert response.status_code == 200, response.data
    assert response.data["count"] == 2, "only the Jan-20 entry's lines remain"
    for row in response.data["results"]:
        assert row["entry_date"] == "2024-01-20"
