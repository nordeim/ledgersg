"""
P25 contract gates — the pagination hardening + the fresh-substrate truth.

BE-P25-M2: a validly-typed but astronomically large `offset` (above the
    Postgres bigint bound) sailed through parse_limit_offset and hit the
    SQL-level slice as `OFFSET 99999999999999999999` -> DataError ->
    untyped 500 on the ledger (the five envelope views Python-sliced it
    into a silent empty page). The typed-400 convention (P7/F-11) demands
    a 400 with the param name, not a 500 — the offset gains the int8 cap.
BE-P25-L4: a well-formed `offset` without a `limit` was silently ignored
    (every view returned the FULL set, the offset unused) — contradicting
    the module's own "explicit beats silent" philosophy. It is now a
    typed 400: `offset` requires `limit`.
BE-P25-M3: BankTransactionListView joined the contract in P24 but no test
    exercised it (the P24 file's matrix covered entries/documents/
    contacts/payments only). The transactions surface joins the matrix
    here, over a 3-row fixture (pins existing behaviour — coverage, not
    a behaviour change).
I3: the empty-string params (`?limit=&offset=`) and the full absolute
    `next` URL shape are pinned (previously asserted by substring only).
"""

from datetime import date
from decimal import Decimal
from urllib.parse import parse_qs, urlparse

import pytest
from rest_framework import status

from apps.invoicing.services import ContactService, DocumentService
from apps.journal.services import JournalService

# ---------------------------------------------------------------------------
# fixtures
# ---------------------------------------------------------------------------


def _entry_kwargs(fx, accounts_pair, i):
    return {
        "org_id": fx["org"].id,
        "entry_date": date(2024, 1, 1 + i),
        "source_type": "MANUAL",
        "narration": f"P25 pagination probe {i}",
        "lines": [
            {
                "account_id": str(accounts_pair[0].id),
                "debit": Decimal("10.00"),
                "credit": Decimal("0.00"),
                "description": f"dr {i}",
            },
            {
                "account_id": str(accounts_pair[1].id),
                "debit": Decimal("0.00"),
                "credit": Decimal("10.00"),
                "description": f"cr {i}",
            },
        ],
        "user_id": fx["user"].id,
    }


@pytest.fixture
def pagination_fx(
    test_organisation, test_user, test_accounts, test_tax_codes, test_fiscal_period
):
    """12 ledger lines (6 entries x 2), 1 contact, 1 approved invoice,
    2 payments, 3 bank transactions — the P25 probe substrate."""
    fx = {
        "org": test_organisation,
        "user": test_user,
        "accounts": test_accounts,
    }
    from apps.core.models import DocumentSequence

    for doc_type, prefix in [
        ("SALES_INVOICE", "INV-"),
        ("SALES_CREDIT_NOTE", "CN-"),
        ("PAYMENT_RECEIVED", "PAY-"),
        ("PAYMENT_MADE", "PAYM-"),
    ]:
        DocumentSequence.objects.get_or_create(
            org=fx["org"], document_type=doc_type, defaults={"prefix": prefix, "next_number": 1}
        )
    for i in range(6):
        JournalService.create_entry(
            **_entry_kwargs(fx, (test_accounts["1200"], test_accounts["4000"]), i)
        )

    contact = ContactService.create_contact(
        org_id=fx["org"].id, name="P25 Invoice Customer", email="", is_customer=True
    )
    fx["contact"] = contact
    for i in range(1):
        DocumentService.create_document(
            org_id=fx["org"].id,
            document_type="SALES_INVOICE",
            contact_id=contact.id,
            issue_date=date(2024, 2, 1 + i),
            lines=[
                {
                    "description": "P25 pagination doc",
                    "account_id": str(test_accounts["4000"].id),
                    "quantity": "1.0000",
                    "unit_price": "100.00",
                    "tax_code_id": str(test_tax_codes["SR"].id),
                }
            ],
            user_id=fx["user"].id,
        )

    from apps.core.models import BankAccount

    bank = BankAccount.objects.create(
        org=fx["org"],
        gl_account=test_accounts["1200"],
        account_name="P25 Operating",
        bank_name="P25 Bank",
        account_number="001-258-135",
        currency="SGD",
        paynow_type=None,
        is_active=True,
    )
    fx["bank"] = bank
    from apps.banking.services import PaymentService

    for i in range(2):
        PaymentService.create_received(
            org_id=fx["org"].id,
            data={
                "contact_id": str(contact.id),
                "bank_account_id": str(bank.id),
                "payment_date": date(2024, 1, 20).isoformat(),
                "amount": "25.00",
                "currency": "SGD",
                "payment_method": "BANK_TRANSFER",
            },
            user_id=fx["user"].id,
        )

    # The transactions surface's fodder (the M3 matrix): the direct-model
    # creation shape reconciliation_service.import_csv() itself uses.
    from apps.core.models import BankTransaction

    for i in range(3):
        BankTransaction.objects.create(
            org_id=fx["org"].id,
            bank_account=bank,
            transaction_date=date(2024, 1, 5 + i),
            value_date=date(2024, 1, 6 + i),
            description=f"P25 bank feed row {i}",
            reference=f"P25-REF-{i}",
            amount=Decimal("10.00") if i % 2 == 0 else Decimal("-10.00"),
            running_balance=Decimal("30.00"),
            is_reconciled=False,
            import_batch_id=None,
            import_source="CSV",
            external_id=f"P25-EXT-{i}",
        )
    return fx


def _ledger_url(fx):
    return f"/api/v1/{fx['org'].id}/journal-entries/ledger/"


def _payments_url(fx):
    return f"/api/v1/{fx['org'].id}/banking/payments/"


def _contacts_url(fx):
    return f"/api/v1/{fx['org'].id}/invoicing/contacts/"


def _transactions_url(fx):
    return f"/api/v1/{fx['org'].id}/banking/bank-transactions/"


# ---------------------------------------------------------------------------
# BE-P25-M2 — the huge offset (the int8 cap; the typed 400, never a 500)
# ---------------------------------------------------------------------------


class TestHugeOffsetP25:
    """`offset` above the Postgres bigint bound (2^63 - 1) is garbage —
    the typed 400 on EVERY surface, never a DataError 500 (the ledger)
    and never a silent empty page (the envelope views)."""

    HUGE = "99999999999999999999"  # 20 nines — above int8, parses as int

    @pytest.mark.django_db
    def test_huge_offset_is_a_typed_400_on_the_ledger(self, auth_client, pagination_fx):
        response = auth_client.get(_ledger_url(pagination_fx) + f"?limit=10&offset={self.HUGE}")
        assert response.status_code == status.HTTP_400_BAD_REQUEST, (
            f"the huge offset must be a 400, got {response.status_code}: {getattr(response, 'data', '')}"
        )
        assert "offset" in str(response.data)

    @pytest.mark.django_db
    def test_huge_offset_is_a_typed_400_on_the_envelope_surfaces(
        self, auth_client, pagination_fx
    ):
        for url in (_payments_url(pagination_fx), _contacts_url(pagination_fx)):
            response = auth_client.get(url + f"?limit=1&offset={self.HUGE}")
            assert response.status_code == status.HTTP_400_BAD_REQUEST, (
                f"the huge offset must be a 400 on {url}, got {response.status_code}"
            )

    @pytest.mark.django_db
    def test_int8_boundary_offset_is_accepted(self, auth_client, pagination_fx):
        """The cap's upper edge: 2^63 - 1 IS a valid bigint — an empty
        page with a live previous, not a 400."""
        boundary = 9223372036854775807
        response = auth_client.get(
            _ledger_url(pagination_fx) + f"?limit=1&offset={boundary}"
        )
        assert response.status_code == status.HTTP_200_OK, response.data
        assert response.data["results"] == []
        assert response.data["next"] is None
        assert response.data["previous"] is not None
        assert f"offset={boundary - 1}" in response.data["previous"]


# ---------------------------------------------------------------------------
# BE-P25-L4 — offset without limit (the silent-ignore closure)
# ---------------------------------------------------------------------------


class TestOffsetRequiresLimitP25:
    """A well-formed `offset` without a `limit` is a caller paging bug —
    the typed 400 (explicit beats silent), on every surface."""

    @pytest.mark.django_db
    def test_offset_without_limit_is_a_typed_400_on_the_ledger(
        self, auth_client, pagination_fx
    ):
        response = auth_client.get(_ledger_url(pagination_fx) + "?offset=5")
        assert response.status_code == status.HTTP_400_BAD_REQUEST, (
            f"offset without limit must be a 400, got {response.status_code}"
        )
        assert "limit" in str(response.data)

    @pytest.mark.django_db
    def test_offset_without_limit_is_a_typed_400_on_the_envelope_surfaces(
        self, auth_client, pagination_fx
    ):
        for url in (_payments_url(pagination_fx), _contacts_url(pagination_fx)):
            response = auth_client.get(url + "?offset=5")
            assert response.status_code == status.HTTP_400_BAD_REQUEST, (
                f"offset without limit must be a 400 on {url}, got {response.status_code}"
            )


# ---------------------------------------------------------------------------
# I3 — the empty-string pins + the full absolute next-URL shape
# ---------------------------------------------------------------------------


class TestEnvelopeShapePinsP25:
    @pytest.mark.django_db
    def test_empty_string_limit_and_offset_behave_as_absent(
        self, auth_client, pagination_fx
    ):
        """`?limit=&offset=` is the unpaginated mode — the byte-identical
        {results, count} with NO next/previous keys, count == the full set."""
        response = auth_client.get(_ledger_url(pagination_fx) + "?limit=&offset=")
        assert response.status_code == status.HTTP_200_OK, response.data
        assert set(response.data.keys()) == {"results", "count"}
        assert response.data["count"] == len(response.data["results"])
        assert response.data["count"] > 0

    @pytest.mark.django_db
    def test_next_is_a_full_absolute_url_carrying_the_callers_filters(
        self, auth_client, pagination_fx
    ):
        account_id = str(pagination_fx["accounts"]["1200"].id)
        response = auth_client.get(
            _ledger_url(pagination_fx) + f"?account_id={account_id}&limit=2"
        )
        assert response.status_code == status.HTTP_200_OK, response.data
        nxt = response.data["next"]
        assert nxt is not None
        parsed = urlparse(nxt)
        assert parsed.scheme in ("http", "https"), "next must be absolute"
        query = parse_qs(parsed.query)
        assert query["limit"] == ["2"]
        assert query["offset"] == ["2"]
        assert query["account_id"] == [account_id], "the caller's filter must survive"


# ---------------------------------------------------------------------------
# BE-P25-M3 — the transactions surface joins the matrix
# ---------------------------------------------------------------------------


class TestTransactionsPaginationP25:
    """BankTransactionListView's slice/envelope path (the P24 contract,
    previously untested — the coverage gap the P24 commit overstated)."""

    @pytest.mark.django_db
    def test_limit_slices_and_counts_the_total(self, auth_client, pagination_fx):
        response = auth_client.get(_transactions_url(pagination_fx) + "?limit=1")
        assert response.status_code == status.HTTP_200_OK, response.data
        assert response.data["count"] == 3
        assert len(response.data["results"]) == 1
        assert response.data["previous"] is None
        assert response.data["next"] is not None
        assert "limit=1" in response.data["next"] and "offset=1" in response.data["next"]

    @pytest.mark.django_db
    def test_offset_pages_forward_to_the_last_page(self, auth_client, pagination_fx):
        response = auth_client.get(_transactions_url(pagination_fx) + "?limit=2&offset=2")
        assert response.status_code == status.HTTP_200_OK, response.data
        assert response.data["count"] == 3
        assert len(response.data["results"]) == 1
        assert response.data["next"] is None
        assert response.data["previous"] is not None

    @pytest.mark.django_db
    def test_unpaginated_envelope_is_unchanged(self, auth_client, pagination_fx):
        response = auth_client.get(_transactions_url(pagination_fx))
        assert response.status_code == status.HTTP_200_OK, response.data
        assert set(response.data.keys()) == {"results", "count"}
        assert len(response.data["results"]) == 3

    @pytest.mark.django_db
    @pytest.mark.parametrize("bad_limit", ["abc", "0", "-5", "1001"])
    def test_garbage_limit_is_a_typed_400(self, auth_client, pagination_fx, bad_limit):
        response = auth_client.get(_transactions_url(pagination_fx) + f"?limit={bad_limit}")
        assert response.status_code == status.HTTP_400_BAD_REQUEST, (
            f"limit={bad_limit} must be a 400"
        )
