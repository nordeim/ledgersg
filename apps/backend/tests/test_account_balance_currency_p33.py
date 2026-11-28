"""
P33/BE-P33-M2: the account-balance currency truth.

Pre-P33: AccountBalanceView hardcoded "currency": "SGD" behind a literal
TODO while the Account model carries its own currency field — the
balance is the account's own balance, and the account's currency is the
truthful denomination. (For the default SGD chart the byte is unchanged.)
"""

import pytest

from apps.core.models import Account, AccountType

pytestmark = pytest.mark.django_db


class TestAccountBalanceCurrencyTruth:
    """The balance endpoint must carry the account's own currency."""

    def test_usd_account_balance_carries_usd(self, auth_client, test_organisation):
        at = AccountType.objects.get(code="ASSET")
        account = Account.objects.create(
            org=test_organisation,
            code="1990",
            name="USD Cash Account",
            account_type="ASSET_CURRENT",
            account_type_ref=at,
            currency="USD",
            is_system=True,
            is_active=True,
        )

        response = auth_client.get(
            f"/api/v1/{test_organisation.id}/accounts/{account.id}/balance/"
        )
        assert response.status_code == 200
        assert response.data["currency"] == "USD", (
            f"account balance claims currency={response.data['currency']!r} "
            f"while the account's own currency is USD"
        )

    def test_default_account_balance_still_carries_sgd(
        self, auth_client, test_organisation, test_accounts
    ):
        """The SGD default path is byte-stable (the model default)."""
        revenue = test_accounts["4000"]

        response = auth_client.get(
            f"/api/v1/{test_organisation.id}/accounts/{revenue.id}/balance/"
        )
        assert response.status_code == 200
        assert response.data["currency"] == "SGD"
