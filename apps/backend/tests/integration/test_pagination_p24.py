"""
P24 contract gates — the server-side list pagination.

BE-P24-M1: every list endpoint returns the FULL matching set — the
    response payload grows without bound (the ledger endpoint returns
    the org's entire journal-line history in one response). The P21
    envelope ({results, count}) was registered as exactly this
    prerequisite. The additive contract: `?limit=N&offset=M` paginates;
    the envelope gains `next`/`previous` (absolute URLs carrying
    limit+offset+filters) and `count` reads as the TOTAL matching rows;
    with `limit` absent the response stays byte-identical {results,
    count} (every existing consumer keeps working).
FE-P24-M2: the ledger UI paginates (the frontend slice is gated in the
    web tree); this file pins the backend contract the UI consumes.
I1 (ordering): contacts (`name`) and payments (`-payment_date,
    -created_at`) lack a unique final tiebreaker — a cross-page
    skip/dup hazard once paginated (Postgres tie order is not stable
    across executions). The tiebreakers are pinned here.
"""

from datetime import date
from decimal import Decimal

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
        "narration": f"P24 pagination probe {i}",
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
    """24 ledger lines (12 entries x 2), 5 contacts (2 sharing a name),
    3 invoices, 2 received payments — real pagination fodder."""
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
    for i in range(12):
        JournalService.create_entry(
            **_entry_kwargs(fx, (test_accounts["1200"], test_accounts["4000"]), i)
        )

    # 5 contacts; index 0 and 1 share the SAME name (the tiebreaker probe)
    names = ["Acme Trading", "Acme Trading", "Beta Supplies", "Gamma Pte", "Delta Traders"]
    for name in names:
        ContactService.create_contact(
            org_id=fx["org"].id, name=name, email="", is_customer=True
        )

    contact = ContactService.create_contact(
        org_id=fx["org"].id, name="Invoice Customer", email="", is_customer=True
    )
    for i in range(3):
        DocumentService.create_document(
            org_id=fx["org"].id,
            document_type="SALES_INVOICE",
            contact_id=contact.id,
            issue_date=date(2024, 2, 1 + i),
            lines=[
                {
                    "description": "P24 pagination doc",
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
        account_name="P24 Operating",
        bank_name="P24 Bank",
        account_number="001-246-810",
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
    return fx


def _ledger_url(fx):
    return f"/api/v1/{fx['org'].id}/journal-entries/ledger/"


# ---------------------------------------------------------------------------
# BE-P24-M1 — the ledger endpoint (the SQL-level first target)
# ---------------------------------------------------------------------------


class TestLedgerPaginationP24:
    """The ledger fixture posts 28 lines in total: the 12 manual entries
    (2 lines each) + the 2 received payments (2 GL lines each) — the
    worked example the counts below pin."""

    @pytest.mark.django_db
    def test_unpaginated_envelope_is_unchanged(self, auth_client, pagination_fx):
        """The back-compat pin: with no `limit`, the response is exactly
        {results, count} — no new keys, every row present."""
        response = auth_client.get(_ledger_url(pagination_fx))
        assert response.status_code == status.HTTP_200_OK
        assert set(response.data.keys()) == {"results", "count"}, response.data.keys()
        assert response.data["count"] == 28
        assert len(response.data["results"]) == 28

    @pytest.mark.django_db
    def test_limit_slices_and_counts_the_total(self, auth_client, pagination_fx):
        """limit=10 -> a 10-row page, count=28 (the TOTAL, not the page
        size — the frontend pages on it), next carries offset=10,
        previous is null on the first page."""
        response = auth_client.get(_ledger_url(pagination_fx) + "?limit=10")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["count"] == 28
        assert len(response.data["results"]) == 10
        assert "next" in response.data and "previous" in response.data
        assert response.data["previous"] is None
        next_url = response.data["next"]
        assert next_url is not None
        assert "limit=10" in next_url and "offset=10" in next_url

    @pytest.mark.django_db
    def test_offset_pages_forward_to_the_last_page(
        self, auth_client, pagination_fx
    ):
        """limit=10&offset=20 -> the last 8 rows; next is null;
        previous carries offset=10."""
        response = auth_client.get(_ledger_url(pagination_fx) + "?limit=10&offset=20")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["count"] == 28
        assert len(response.data["results"]) == 8
        assert response.data["next"] is None
        assert response.data["previous"] is not None
        assert "offset=10" in response.data["previous"]

    @pytest.mark.django_db
    def test_offset_beyond_the_end_is_an_empty_page(self, auth_client, pagination_fx):
        """offset=100 -> 0 rows, count stays 28 (the total), next is
        null, previous stays valid (offset=90)."""
        response = auth_client.get(_ledger_url(pagination_fx) + "?limit=10&offset=100")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["count"] == 28
        assert response.data["results"] == []
        assert response.data["next"] is None
        assert response.data["previous"] is not None
        assert "offset=90" in response.data["previous"]

    @pytest.mark.django_db
    def test_pages_are_stable_and_disjoint(self, auth_client, pagination_fx):
        """Paging limit=10 across the set yields every row exactly once,
        in the endpoint's documented order (no skip, no dup)."""
        seen = []
        offset = 0
        while True:
            response = auth_client.get(
                _ledger_url(pagination_fx) + f"?limit=10&offset={offset}"
            )
            page = response.data["results"]
            seen.extend(row["id"] for row in page)
            if response.data["next"] is None:
                break
            offset += 10
        assert len(seen) == 28
        assert len(set(seen)) == 28, "pagination must not skip or duplicate rows"

    @pytest.mark.django_db
    def test_next_previous_carry_the_callers_filters(
        self, auth_client, pagination_fx
    ):
        """The account filter survives into the next/previous URLs —
        paging within a filtered set must not widen it."""
        account_id = str(pagination_fx["accounts"]["1200"].id)
        response = auth_client.get(
            _ledger_url(pagination_fx) + f"?limit=5&account_id={account_id}"
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.data["count"] == 16
        assert len(response.data["results"]) == 5
        assert f"account_id={account_id}" in response.data["next"]
        assert "limit=5" in response.data["next"] and "offset=5" in response.data["next"]

    @pytest.mark.django_db
    @pytest.mark.parametrize("bad_limit", ["abc", "0", "-5", "1001"])
    def test_garbage_limit_is_a_typed_400(self, auth_client, pagination_fx, bad_limit):
        """The P7/F-11 convention: garbage query params are 400s, never
        500s; limit must be an integer in [1, 1000]."""
        response = auth_client.get(_ledger_url(pagination_fx) + f"?limit={bad_limit}")
        assert response.status_code == status.HTTP_400_BAD_REQUEST, (
            f"limit={bad_limit} must be a 400"
        )

    @pytest.mark.django_db
    @pytest.mark.parametrize("bad_offset", ["abc", "-1"])
    def test_garbage_offset_is_a_typed_400(self, auth_client, pagination_fx, bad_offset):
        response = auth_client.get(_ledger_url(pagination_fx) + f"?offset={bad_offset}")
        assert response.status_code == status.HTTP_400_BAD_REQUEST, (
            f"offset={bad_offset} must be a 400"
        )

    @pytest.mark.django_db
    def test_limit_1000_is_accepted(self, auth_client, pagination_fx):
        """The clamp boundary: 1000 is the documented max — accepted."""
        response = auth_client.get(_ledger_url(pagination_fx) + "?limit=1000")
        assert response.status_code == status.HTTP_200_OK


# ---------------------------------------------------------------------------
# BE-P24-M1 — the five service-driven lists (the sequence-level helper)
# ---------------------------------------------------------------------------


class TestOtherListsPaginationP24:
    """The same additive contract on the entries / documents / contacts /
    payments / transactions lists (the envelope-level slice this
    sprint)."""

    URL_BUILDERS = {
        "entries": lambda fx: f"/api/v1/{fx['org'].id}/journal-entries/entries/",
        "documents": lambda fx: f"/api/v1/{fx['org'].id}/invoicing/documents/",
        "contacts": lambda fx: f"/api/v1/{fx['org'].id}/invoicing/contacts/",
        "payments": lambda fx: f"/api/v1/{fx['org'].id}/banking/payments/",
    }

    TOTALS = {"entries": 14, "documents": 3, "contacts": 6, "payments": 2}

    @pytest.mark.django_db
    @pytest.mark.parametrize(
        "surface", ["entries", "documents", "contacts", "payments"]
    )
    def test_limit_slices_and_counts_the_total(
        self, auth_client, pagination_fx, surface
    ):
        url = self.URL_BUILDERS[surface](pagination_fx)
        response = auth_client.get(url + "?limit=1")
        assert response.status_code == status.HTTP_200_OK, response.data
        assert response.data["count"] == self.TOTALS[surface]
        assert len(response.data["results"]) == 1
        assert response.data["previous"] is None
        assert response.data["next"] is not None
        assert "limit=1" in response.data["next"] and "offset=1" in response.data["next"]

    @pytest.mark.django_db
    @pytest.mark.parametrize(
        "surface", ["entries", "documents", "contacts", "payments"]
    )
    def test_unpaginated_envelope_is_unchanged(
        self, auth_client, pagination_fx, surface
    ):
        url = self.URL_BUILDERS[surface](pagination_fx)
        response = auth_client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert set(response.data.keys()) == {"results", "count"}, (
            response.data.keys()
        )
        assert response.data["count"] == self.TOTALS[surface]
        assert len(response.data["results"]) == self.TOTALS[surface]

    @pytest.mark.django_db
    @pytest.mark.parametrize(
        "surface", ["entries", "documents", "contacts", "payments"]
    )
    def test_garbage_limit_is_a_typed_400(self, auth_client, pagination_fx, surface):
        url = self.URL_BUILDERS[surface](pagination_fx)
        response = auth_client.get(url + "?limit=abc")
        assert response.status_code == status.HTTP_400_BAD_REQUEST, (
            f"{surface}: limit=abc must be a 400"
        )


# ---------------------------------------------------------------------------
# I1 — the ordering tiebreakers (the cross-page skip/dup hazard)
# ---------------------------------------------------------------------------


class TestPaginationOrderingP24:
    @pytest.mark.django_db
    def test_same_name_contacts_page_without_skip_or_dup(
        self, auth_client, pagination_fx
    ):
        """Two contacts share the exact same name; paging limit=1 across
        the set must carry BOTH exactly once (the `id` tiebreaker —
        without it Postgres may return the tie in either order per
        execution and a page boundary can skip or duplicate a row)."""
        url = f"/api/v1/{pagination_fx['org'].id}/invoicing/contacts/"
        seen = []
        offset = 0
        while True:
            response = auth_client.get(url + f"?limit=1&offset={offset}")
            assert response.status_code == status.HTTP_200_OK, response.data
            page = response.data["results"]
            if not page:
                break
            seen.append(page[0]["id"])
            if response.data["next"] is None:
                break
            offset += 1
        assert response.data["count"] == 6
        assert len(seen) == 6
        assert len(set(seen)) == 6, "the tie must not skip or duplicate rows"
