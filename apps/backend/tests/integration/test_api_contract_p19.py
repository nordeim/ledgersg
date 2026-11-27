"""
P19 API-contract gates — the residual uuid-route islands, the journal
tolerance alignment, the display_money finite gate and the N+1 pair.

BE-M7: five routes kept <str:...> converters while every sibling got
    <uuid:...> in P17/P18 — the same client error produced a
    view-level 500 (Django ValidationError / SQL DataError) here vs a
    404 at routing on every sibling route.
BE-D1: the journal create serializer's balance gate is 0.001 while the
    service and the DB trigger enforce 0.0001 — a 0.0002..0.001
    imbalance passes the serializer then dies in the service with a
    different error shape; the detail serializer's "balanced" flag can
    report true for a trigger-violating entry.
BE-D2: display_money() has no is_finite gate — display_money("NaN")
    returns "NaN" (money() rejects non-finite; the display twin must
    match).
BE-M6: the journal list serializer runs 3 queries per row
    (lines.all() x2 + lines.count()) with no prefetch — O(3N+1) on the
    full org journal history.
BE-L5: suggest_matches() N+1s payment.contact.name (no
    select_related("contact")).
"""

from datetime import date
from decimal import Decimal

from tests.integration.test_payment_allocation_contract_p14 import (  # noqa: F401
    payment_fixture,
)

import pytest


def _auth(client, user):
    from tests.conftest import get_auth_token

    client.credentials(HTTP_AUTHORIZATION=f"Bearer {get_auth_token(user)}")
    return client


class TestUuidRouteConvertersP19:
    """BE-M7: malformed UUIDs must 404 at the routing layer on the five
    <str:...> islands, identical to every sibling route converted in
    P17/P18."""

    @pytest.mark.django_db
    def test_malformed_fiscal_year_close_id_is_a_route_404(
        self, api_client, test_user, test_organisation
    ):
        _auth(api_client, test_user)
        response = api_client.post(
            f"/api/v1/{test_organisation.id}/fiscal-years/not-a-uuid/close/"
        )
        assert response.status_code == 404, (
            "a malformed UUID must be a route-level 404 (the uuid converter); "
            f"got {response.status_code} (BE-M7/P19)"
        )

    @pytest.mark.django_db
    def test_malformed_fiscal_period_close_id_is_a_route_404(
        self, api_client, test_user, test_organisation
    ):
        _auth(api_client, test_user)
        response = api_client.post(
            f"/api/v1/{test_organisation.id}/fiscal-periods/not-a-uuid/close/"
        )
        assert response.status_code == 404, (
            f"got {response.status_code} (BE-M7/P19)"
        )

    @pytest.mark.django_db
    def test_malformed_fiscal_period_open_id_is_a_route_404(
        self, api_client, test_user, test_organisation
    ):
        _auth(api_client, test_user)
        response = api_client.post(
            f"/api/v1/{test_organisation.id}/fiscal-periods/not-a-uuid/open/"
        )
        assert response.status_code == 404, (
            f"got {response.status_code} (BE-M7/P19)"
        )

    @pytest.mark.django_db
    def test_malformed_account_id_is_a_route_404(
        self, api_client, test_user, test_organisation
    ):
        _auth(api_client, test_user)
        response = api_client.get(
            f"/api/v1/{test_organisation.id}/accounts/not-a-uuid/"
        )
        assert response.status_code == 404, (
            f"got {response.status_code} (BE-M7/P19)"
        )

    @pytest.mark.django_db
    def test_malformed_account_balance_id_is_a_route_404(
        self, api_client, test_user, test_organisation
    ):
        _auth(api_client, test_user)
        response = api_client.get(
            f"/api/v1/{test_organisation.id}/accounts/not-a-uuid/balance/"
        )
        assert response.status_code == 404, (
            f"got {response.status_code} (BE-M7/P19)"
        )


class TestJournalSerializerToleranceP19:
    @pytest.mark.django_db
    def test_create_serializer_rejects_the_sub_tolerance_imbalance(
        self, test_organisation, test_accounts
    ):
        """BE-D1: a 0.0005 imbalance is above the service/DB-trigger
        tolerance (0.0001) — the serializer must reject it at the same
        boundary, not pass it into the service's differently-shaped
        error."""
        from apps.journal.serializers import JournalEntryCreateSerializer

        serializer = JournalEntryCreateSerializer(
            data={
                "entry_date": date(2024, 1, 10),
                "source_type": "MANUAL",
                "narration": "P19-D1 probe",
                "lines": [
                    {
                        "account_id": str(test_accounts["4000"].id),
                        "debit": "10.0005",
                        "credit": "0",
                        "description": "probe debit",
                    },
                    {
                        "account_id": str(test_accounts["1200"].id),
                        "debit": "0",
                        "credit": "10.0000",
                        "description": "probe credit",
                    },
                ],
            },
            context={"org_id": test_organisation.id},
        )
        assert not serializer.is_valid(), (
            "the serializer's balance gate must be 0.0001 (the service + DB "
            "trigger boundary, P13/B-13) — a 0.0005 imbalance must be "
            "rejected here (BE-D1/P19)"
        )
        assert "non_field_errors" in serializer.errors or "lines" in serializer.errors, (
            f"the rejection must come from the balance gate, not an unrelated "
            f"field (saw {list(serializer.errors)})"
        )

    def test_detail_serializer_balanced_flag_matches_the_service_tolerance(self):
        """BE-D1: the computed 'balanced' flag must use the same 0.0001
        boundary as the service/DB trigger — 0.0005 is NOT balanced."""
        from apps.journal.serializers import JournalEntryDetailSerializer

        class _FakeManager:
            def __init__(self, lines):
                self._lines = lines

            def all(self):
                return self._lines

            def count(self):
                return len(self._lines)

            def __iter__(self):
                return iter(self._lines)

        class _Line:
            def __init__(self, debit, credit):
                self.debit = Decimal(debit)
                self.credit = Decimal(credit)
                self.line_number = 1
                self.account = None
                self.account_id = None
                self.description = ""
                self.tax_code = None
                self.tax_code_id = None
                self.tax_amount = Decimal("0")

        class _Entry:
            id = "00000000-0000-0000-0000-000000000000"
            entry_number = 1
            entry_date = date(2024, 1, 10)
            source_type = "MANUAL"
            source_id = None
            reference = ""
            narration = "probe"
            posted_at = None
            posted_by = None
            is_reversed = False
            created_at = None
            lines = _FakeManager([_Line("10.0005", "0"), _Line("0", "10.0000")])
            fiscal_period = None
            fiscal_year = None
            reversal_of_entry = None

        data = JournalEntryDetailSerializer(_Entry()).data
        assert data["totals"]["balanced"] is False, (
            "a 0.0005 imbalance is above the service/trigger tolerance — "
            "the balanced flag must be False (BE-D1/P19)"
        )


class TestDisplayMoneyFiniteGateP19:
    def test_display_money_rejects_nan(self):
        """BE-D2: display_money must mirror money()'s finite gate —
        'NaN' in, typed error out (never the string 'NaN' rendered to a
        user)."""
        from common.decimal_utils import display_money

        with pytest.raises((ValueError, TypeError)):
            display_money("NaN")

    def test_display_money_rejects_infinity(self):
        from common.decimal_utils import display_money

        with pytest.raises((ValueError, TypeError)):
            display_money("Infinity")

    def test_display_money_still_formats_finite_values(self):
        from common.decimal_utils import display_money

        assert display_money("100.5") == "100.50"
        assert display_money(Decimal("100.999")) == "101.00"


class TestJournalListQueryCountP19:
    @pytest.mark.django_db
    def test_journal_list_is_not_3n_plus_one(
        self, test_organisation, test_user, test_accounts, test_fiscal_period,
        django_assert_num_queries,
    ):
        """BE-M6: the journal list must prefetch its lines — 10 entries
        must not cost 3 queries per row (the serializer's lines.all()
        x2 + lines.count())."""
        from apps.journal.services import JournalService

        for i in range(10):
            JournalService.create_entry(
                org_id=test_organisation.id,
                entry_date=date(2024, 1, 10),
                source_type="MANUAL",
                narration=f"P19-M6 probe {i}",
                lines=[
                    {
                        "account_id": str(test_accounts["4000"].id),
                        "debit": Decimal("1.0000"),
                        "credit": Decimal("0"),
                        "description": f"probe {i} debit",
                    },
                    {
                        "account_id": str(test_accounts["1200"].id),
                        "debit": Decimal("0"),
                        "credit": Decimal("1.0000"),
                        "description": f"probe {i} credit",
                    },
                ],
                user_id=test_user.id,
            )

        from apps.journal.serializers import JournalEntryListSerializer

        with django_assert_num_queries(2):
            # The unfixed list: 1 (entries) + 3N (30) = 31 queries for the
            # list + serializer pass. The fixed budget: 1 entries + 1
            # prefetch — the prefetched cache serves lines.all() AND
            # lines.count() with zero serializer residue.
            entries = JournalService.list_entries(test_organisation.id)
            list(JournalEntryListSerializer(entries, many=True).data)


class TestSuggestMatchesQueryCountP19:
    @pytest.mark.django_db
    def test_suggest_matches_does_not_n_plus_one_contacts(
        self, payment_fixture, django_assert_num_queries
    ):
        """BE-L5: suggest_matches must select_related('contact') — N
        payments must not cost N contact queries."""
        from apps.core.models import BankTransaction
        from tests.integration.test_payment_allocation_contract_p14 import _receive

        fx = payment_fixture
        # 8 unreconciled received payments, all contact-linked.
        for i in range(8):
            _receive(
                fx["org"], fx["user"], fx["bank"], fx["contact"], Decimal("109.00")
            )
        txn = BankTransaction.objects.create(
            org=fx["org"],
            bank_account=fx["bank"],
            transaction_date=date(2024, 1, 21),
            description="P19 SUGGEST 109.00",
            reference="TX-P19",
            amount=Decimal("109.0000"),
            running_balance=Decimal("109.0000"),
        )

        from apps.banking.services import ReconciliationService

        with django_assert_num_queries(2):
            # Fixed: 1 transaction fetch + 1 candidates fetch (contact
            # joined). Unfixed: 1 + 1 + N contact lookups.
            suggestions = ReconciliationService.suggest_matches(
                org_id=fx["org"].id,
                transaction_id=txn.id,
                tolerance=Decimal("1.00"),
            )
        assert suggestions, "test setup: matches must exist for the probe"


class TestCsvImportSizeCapP19:
    @pytest.mark.django_db
    def test_oversized_csv_is_a_typed_refusal(
        self, test_organisation, test_user, test_accounts
    ):
        """X-M2: the whole-file read + decode loads the entire upload into
        memory (doubled) — an authenticated CanManageBanking user could
        OOM a worker with one oversized statement. A >5MB upload must be
        a typed refusal before any row processing."""
        from io import BytesIO

        from apps.banking.services import ReconciliationService
        from apps.core.models import BankAccount
        from common.exceptions import ValidationError as ServiceValidationError

        bank = BankAccount.objects.create(
            org=test_organisation,
            gl_account=test_accounts["1200"],
            account_name="CSV Cap Bank",
            bank_name="Test Bank",
            account_number="001-999-002",
            currency="SGD",
            paynow_type=None,
            is_active=True,
        )
        oversize = BytesIO(b"a" * (5 * 1024 * 1024 + 1))
        with pytest.raises(ServiceValidationError, match="(?i)too large|size|5"):
            ReconciliationService.import_csv(
                org_id=test_organisation.id,
                bank_account_id=bank.id,
                csv_file=oversize,
                user_id=test_user.id,
            )

    @pytest.mark.django_db
    def test_row_count_ceiling_is_a_typed_refusal(
        self, test_organisation, test_user, test_accounts
    ):
        """X-M2: the per-row check-then-insert loop is bounded — a
        statement beyond the row ceiling is refused up front."""
        from io import BytesIO

        from apps.banking.services import ReconciliationService
        from apps.core.models import BankAccount
        from common.exceptions import ValidationError as ServiceValidationError

        bank = BankAccount.objects.create(
            org=test_organisation,
            gl_account=test_accounts["1200"],
            account_name="CSV Rows Bank",
            bank_name="Test Bank",
            account_number="001-999-003",
            currency="SGD",
            paynow_type=None,
            is_active=True,
        )
        # 10001 data rows: one over the 10k ceiling.
        rows = ["transaction_date,description,amount"]
        rows.extend(
            f"2024-01-15,row {i},1.00" for i in range(10_001)
        )
        csv_text = "\n".join(rows) + "\n"
        with pytest.raises(ServiceValidationError, match="(?i)rows|too many|10"):
            ReconciliationService.import_csv(
                org_id=test_organisation.id,
                bank_account_id=bank.id,
                csv_file=BytesIO(csv_text.encode("utf-8")),
                user_id=test_user.id,
            )

    @pytest.mark.django_db
    def test_at_limit_files_import_normally(
        self, test_organisation, test_user, test_accounts
    ):
        """X-M2: the ceiling refuses only BEYOND-limit files — a
        small statement imports exactly as before."""
        from io import BytesIO

        from apps.banking.services import ReconciliationService
        from apps.core.models import BankAccount

        bank = BankAccount.objects.create(
            org=test_organisation,
            gl_account=test_accounts["1200"],
            account_name="CSV Small Bank",
            bank_name="Test Bank",
            account_number="001-999-004",
            currency="SGD",
            paynow_type=None,
            is_active=True,
        )
        csv_text = (
            "transaction_date,description,amount\n2024-01-15,ok row,1.00\n"
        )
        result = ReconciliationService.import_csv(
            org_id=test_organisation.id,
            bank_account_id=bank.id,
            csv_file=BytesIO(csv_text.encode("utf-8")),
            user_id=test_user.id,
        )
        assert result["imported"] >= 1
