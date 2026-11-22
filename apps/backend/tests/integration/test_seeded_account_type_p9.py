"""
P9/C-4: seeded accounts carry their account_type.

The org seed (core.seed_default_chart_of_accounts) populates only the
account_type_id FK — the account_type VARCHAR(50) the API filter reads
stays NULL on every seeded account. useRevenueAccounts sends
?account_type=REVENUE, so on a fresh org the New Invoice / New Quote
posting-account dropdown is EMPTY (the P8 live smoke had to create
account 4100 by hand before invoicing). API-created accounts work
(create_account sets both columns) — the seeded ones did not.
"""

import pytest

from apps.core.models import Account


@pytest.mark.django_db
class TestSeededAccountTypeP9:
    def _seeded_org(self, test_user):
        from apps.core.services.organisation_service import create_organisation

        return create_organisation(
            user=test_user,
            name="Seed Chart P9",
            legal_name="Seed Chart P9 Pte Ltd",
            uen="123456789B",
        )

    def test_seeded_accounts_carry_the_account_type_column(self, test_user):
        """The seed must populate the VARCHAR, not just the FK."""
        org = self._seeded_org(test_user)

        seeded = Account.objects.filter(org=org, is_system=True)
        assert seeded.exists(), "the seed must have run"
        missing = [a.code for a in seeded if not a.account_type]
        assert not missing, (
            f"seeded accounts with NULL account_type varchar: {missing[:10]} "
            f"({len(missing)} of {seeded.count()} rows)"
        )

    def test_revenue_filter_returns_seeded_rows(self, test_user):
        """The filter the invoice form's account dropdown uses
        (useRevenueAccounts → ?account_type=REVENUE) must find the
        seeded 4000-series on a fresh org."""
        from apps.coa.services import AccountService

        org = self._seeded_org(test_user)

        rows = AccountService.list_accounts(org_id=org.id, account_type="REVENUE")

        codes = [r.code for r in rows]
        assert codes, "the seeded revenue accounts must be filterable"
        assert any(c.startswith("4") for c in codes), codes

    def test_revenue_filter_matches_fk_for_pre_backfill_orgs(self, test_user, test_organisation):
        """Defense-in-depth: orgs created BEFORE the seed backfill have the
        varchar NULL but the FK set — the filter must still find them."""
        from apps.coa.services import AccountService

        # A pre-backfill row: FK set, varchar NULL (the pre-P9 seed shape).
        Account.objects.create(
            org=test_organisation,
            code="4900",
            name="Legacy Revenue",
            account_type=None,
            account_type_ref_id=4,  # coa.account_type 4 = REVENUE
            is_active=True,
        )

        rows = AccountService.list_accounts(
            org_id=test_organisation.id, account_type="REVENUE"
        )
        assert any(r.code == "4900" for r in rows), [r.code for r in rows]
