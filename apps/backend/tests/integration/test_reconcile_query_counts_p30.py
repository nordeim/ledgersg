"""
P30 contract gates — the fourth-surface walk completion (reconcile /
unreconcile).

BE-P30-M2: ReconciliationService.reconcile / unreconcile returned the
    bank-transaction row from a select_for_update() fetch with no
    select_related, and the views serialise it with
    BankTransactionSerializer whose bank_account_name walks
    bank_account.account_name — one extra query per mutation response
    (the P29 class on the fourth surface: this surface has no detail
    GET, so the mutation responses ARE the serialising consumers).
    These gates pin the query-level truth the response tests cannot
    see: the locked fetch carries the bank_account JOIN, never a
    separate walk.
Counter-pins (the fix must not change them): the response payload —
is_reconciled flips, bank_account_name present — stays byte-identical.
"""

from datetime import date

import pytest
from django.db import connection
from django.test.utils import CaptureQueriesContext
from rest_framework import status

from apps.invoicing.services import ContactService

# ---------------------------------------------------------------------------
# fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def reconcile_fx(test_organisation, test_user, test_accounts, test_fiscal_period):
    """One bank account, one received payment, one matching bank
    transaction — the reconcile contract's prerequisites (same bank
    account, amounts within the 1.00 tolerance)."""
    fx = {
        "org": test_organisation,
        "user": test_user,
        "accounts": test_accounts,
    }

    from apps.core.models import DocumentSequence

    DocumentSequence.objects.get_or_create(
        org=fx["org"],
        document_type="PAYMENT_RECEIVED",
        defaults={"prefix": "PAY-", "next_number": 1},
    )

    contact = ContactService.create_contact(
        org_id=fx["org"].id, name="P30 Rec Customer", email="", is_customer=True
    )
    fx["contact"] = contact

    from apps.core.models import BankAccount

    bank = BankAccount.objects.create(
        org=fx["org"],
        gl_account=test_accounts["1200"],
        account_name="P30 Operating",
        bank_name="P30 Bank",
        account_number="001-246-810",
        currency="SGD",
        paynow_type=None,
        is_active=True,
    )
    fx["bank"] = bank

    from apps.banking.services import PaymentService

    fx["payment"] = PaymentService.create_received(
        org_id=fx["org"].id,
        data={
            "contact_id": str(contact.id),
            "bank_account_id": str(bank.id),
            "payment_date": date(2024, 1, 20).isoformat(),
            "amount": "50.00",
            "currency": "SGD",
            "payment_method": "BANK_TRANSFER",
        },
        user_id=fx["user"].id,
    )

    from apps.core.models import BankTransaction

    fx["transaction"] = BankTransaction.objects.create(
        org=fx["org"],
        bank_account=bank,
        transaction_date=date(2024, 1, 21),
        description="P30 reconcile probe",
        reference="P30-1",
        amount="50.0000",
        import_source="CSV",
    )
    return fx


# ---------------------------------------------------------------------------
# the shared probes
# ---------------------------------------------------------------------------


def _selects_touching(ctx, anchor):
    """The SELECT queries whose SQL mentions the anchor table."""
    sqls = [q["sql"] for q in ctx.captured_queries]
    return [s for s in sqls if anchor in s and s.lstrip().upper().startswith("SELECT")]


def _locked_txn_fetches(ctx):
    """The FOR UPDATE SELECTs that fetch the bank-transaction row."""
    return [
        s
        for s in _selects_touching(ctx, 'banking"."bank_transaction')
        if "for update" in s.lower()
    ]


# ---------------------------------------------------------------------------
# BE-P30-M2 — the reconcile / unreconcile responses
# ---------------------------------------------------------------------------


class TestReconcileQueryCountP30:
    """A reconcile response joins the bank_account row, never walks it."""

    BANK_TXN = 'banking"."bank_transaction'
    BANK_ACCOUNT = 'banking"."bank_account'

    @pytest.mark.django_db
    def test_reconcile_fetch_carries_the_bank_account_join(self, auth_client, reconcile_fx):
        fx = reconcile_fx
        url = f"/api/v1/{fx['org'].id}/banking/bank-transactions/{fx['transaction'].id}/reconcile/"
        with CaptureQueriesContext(connection) as ctx:
            response = auth_client.post(url, {"payment_id": str(fx["payment"].id)}, format="json")
        assert response.status_code == status.HTTP_200_OK, response.data

        # (a) the locked fetch carries the bank_account JOIN (RED now:
        # the fetch is single-table and the bank_account row rides its
        # own walk during serialization)
        locked = _locked_txn_fetches(ctx)
        assert locked, "no FOR UPDATE bank-transaction SELECT captured"
        assert self.BANK_ACCOUNT in locked[0], (
            "the locked bank-transaction fetch is single-table — the "
            "bank_account rides its own walk (BE-P30-M2): "
            f"{locked[0][:200]}"
        )

        # (b) the walk is gone: no SELECT touches bank_account OUTSIDE
        # the joined fetch (the pre-fix serializer walk)
        bank_account_selects = _selects_touching(ctx, self.BANK_ACCOUNT)
        separate_walks = [s for s in bank_account_selects if "bank_transaction" not in s]
        assert not separate_walks, (
            f"the bank_account table was walked {len(separate_walks)} "
            f"time(s) outside the joined fetch (BE-P30-M2): "
            f"{[s[:160] for s in separate_walks]}"
        )

        # the counter-pins: the payload is unchanged
        assert response.data["is_reconciled"] is True
        assert response.data["bank_account_name"] == "P30 Operating"
        assert response.data["matched_payment"] == fx["payment"].id


class TestUnreconcileQueryCountP30:
    """An unreconcile response joins the bank_account row, never walks it."""

    BANK_TXN = 'banking"."bank_transaction'
    BANK_ACCOUNT = 'banking"."bank_account'

    @pytest.mark.django_db
    def test_unreconcile_fetch_carries_the_bank_account_join(self, auth_client, reconcile_fx):
        fx = reconcile_fx
        # reconcile first (outside the capture) so the unreconcile has
        # its prerequisite state
        reconcile_url = (
            f"/api/v1/{fx['org'].id}/banking/bank-transactions/{fx['transaction'].id}/reconcile/"
        )
        first = auth_client.post(reconcile_url, {"payment_id": str(fx["payment"].id)}, format="json")
        assert first.status_code == status.HTTP_200_OK, first.data

        url = f"/api/v1/{fx['org'].id}/banking/bank-transactions/{fx['transaction'].id}/unreconcile/"
        with CaptureQueriesContext(connection) as ctx:
            response = auth_client.post(url)
        assert response.status_code == status.HTTP_200_OK, response.data

        # (a) the locked fetch carries the bank_account JOIN (RED now:
        # single-table)
        locked = _locked_txn_fetches(ctx)
        assert locked, "no FOR UPDATE bank-transaction SELECT captured"
        assert self.BANK_ACCOUNT in locked[0], (
            "the locked bank-transaction fetch is single-table — the "
            "bank_account rides its own walk (BE-P30-M2): "
            f"{locked[0][:200]}"
        )

        # (b) the walk is gone
        bank_account_selects = _selects_touching(ctx, self.BANK_ACCOUNT)
        separate_walks = [s for s in bank_account_selects if "bank_transaction" not in s]
        assert not separate_walks, (
            f"the bank_account table was walked {len(separate_walks)} "
            f"time(s) outside the joined fetch (BE-P30-M2): "
            f"{[s[:160] for s in separate_walks]}"
        )

        # the counter-pins: the payload is unchanged
        assert response.data["is_reconciled"] is False
        assert response.data["bank_account_name"] == "P30 Operating"
        assert response.data["matched_payment"] is None
