"""
P28 contract gates — the SQL-level push-down for the service-driven lists.

BE-P28-H1: the four service-driven list surfaces (contacts, documents,
    payments, bank transactions) materialised the ENTIRE filtered set in
    Python (`return list(queryset...)`) and the views Python-sliced +
    `len()`-counted it — every 20-row page of an organisation with N
    documents fetched all N rows. The P24 envelope paged the RESPONSE,
    not the QUERY. These gates pin the query-level truth the envelope
    tests cannot see: a paginated request issues a LIMIT-bounded SELECT
    (the requested page size) and a SQL COUNT(*) for the total — never
    an unbounded fetch.
Counter-pins (the fix must not change them): the envelope contract —
    `count` is the TOTAL matching rows, `results` carries exactly the
    requested page, `next`/`previous` per the P24 semantics.
"""

from datetime import date
from decimal import Decimal

import pytest
from django.db import connection
from django.test.utils import CaptureQueriesContext
from rest_framework import status

from apps.invoicing.services import ContactService, DocumentService

# ---------------------------------------------------------------------------
# fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def pushdown_fx(
    test_organisation, test_user, test_accounts, test_tax_codes, test_fiscal_period
):
    """6 contacts, 3 invoices, 3 received payments, 3 bank transactions —
    every surface carries MORE rows than the limit=2 probe, so the LIMIT
    actually binds (the P24 pagination_fx conventions + the P25 direct-
    model bank-feed fodder)."""
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

    names = [
        "P28 Alpha Trading",
        "P28 Alpha Trading",
        "P28 Beta Supplies",
        "P28 Gamma Pte",
        "P28 Delta Traders",
    ]
    for name in names:
        ContactService.create_contact(
            org_id=fx["org"].id, name=name, email="", is_customer=True
        )
    contact = ContactService.create_contact(
        org_id=fx["org"].id, name="P28 Invoice Customer", email="", is_customer=True
    )

    for i in range(3):
        DocumentService.create_document(
            org_id=fx["org"].id,
            document_type="SALES_INVOICE",
            contact_id=contact.id,
            issue_date=date(2024, 2, 1 + i),
            lines=[
                {
                    "description": "P28 pushdown doc",
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
        account_name="P28 Operating",
        bank_name="P28 Bank",
        account_number="001-246-828",
        currency="SGD",
        paynow_type=None,
        is_active=True,
    )
    fx["bank"] = bank

    from apps.banking.services import PaymentService

    for _ in range(3):
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

    from apps.core.models import BankTransaction

    for i in range(3):
        BankTransaction.objects.create(
            org_id=fx["org"].id,
            bank_account=bank,
            transaction_date=date(2024, 1, 5 + i),
            value_date=date(2024, 1, 6 + i),
            description=f"P28 bank feed row {i}",
            reference=f"P28-REF-{i}",
            amount=Decimal("10.00") if i % 2 == 0 else Decimal("-10.00"),
            running_balance=Decimal("30.00"),
            is_reconciled=False,
            import_batch_id=None,
            import_source="CSV",
            external_id=f"P28-EXT-{i}",
        )
    return fx


# ---------------------------------------------------------------------------
# the shared probe
# ---------------------------------------------------------------------------


def _assert_pushdown(auth_client, url, table_anchor, fx, total, page_size=2):
    """The query-level contract: the request issues (a) a LIMIT-bounded
    SELECT on the surface's table and (b) a SQL COUNT(*) for the total —
    plus the envelope counter-pin (count=total, results=page_size)."""
    with CaptureQueriesContext(connection) as ctx:
        response = auth_client.get(url + f"?limit={page_size}")
    assert response.status_code == status.HTTP_200_OK, response.data

    sqls = [q["sql"] for q in ctx.captured_queries]
    surface_sqls = [s for s in sqls if table_anchor in s]
    assert surface_sqls, (
        f"no query touched {table_anchor} — the surface's queries: "
        f"{[s[:120] for s in sqls]}"
    )

    # (a) the row fetch is LIMIT-bounded at the REQUESTED page size
    bounded = [s for s in surface_sqls if f"LIMIT {page_size}" in s]
    assert bounded, (
        f"the paginated fetch on {table_anchor} is not LIMIT-{page_size}-bounded "
        f"(the full-table fetch BE-P28-H1): {[s[:200] for s in surface_sqls]}"
    )

    # (b) the total comes from a SQL COUNT(*), not a Python len()
    counted = [s for s in surface_sqls if "COUNT(*)" in s]
    assert counted, (
        f"no COUNT(*) query ran against {table_anchor} — the count is a "
        f"Python len() over the fetched rows (BE-P28-H1): "
        f"{[s[:200] for s in surface_sqls]}"
    )

    # the envelope counter-pin: count is the TOTAL, results the page
    assert response.data["count"] == total, response.data["count"]
    assert len(response.data["results"]) == page_size
    assert response.data["next"] is not None
    assert response.data["previous"] is None
    return bounded, counted


# ---------------------------------------------------------------------------
# BE-P28-H1 — the four service-driven surfaces
# ---------------------------------------------------------------------------


class TestContactsPushdownP28:
    TABLE = 'invoicing"."contact'

    @pytest.mark.django_db
    def test_paginated_request_is_sql_bounded(self, auth_client, pushdown_fx):
        _assert_pushdown(
            auth_client,
            f"/api/v1/{pushdown_fx['org'].id}/invoicing/contacts/",
            self.TABLE,
            pushdown_fx,
            total=6,
        )


class TestDocumentsPushdownP28:
    TABLE = 'invoicing"."document'

    @pytest.mark.django_db
    def test_paginated_request_is_sql_bounded(self, auth_client, pushdown_fx):
        _assert_pushdown(
            auth_client,
            f"/api/v1/{pushdown_fx['org'].id}/invoicing/documents/",
            self.TABLE,
            pushdown_fx,
            total=3,
        )


class TestPaymentsPushdownP28:
    TABLE = 'banking"."payment'

    @pytest.mark.django_db
    def test_paginated_request_is_sql_bounded(self, auth_client, pushdown_fx):
        _assert_pushdown(
            auth_client,
            f"/api/v1/{pushdown_fx['org'].id}/banking/payments/",
            self.TABLE,
            pushdown_fx,
            total=3,
        )


class TestBankTransactionsPushdownP28:
    TABLE = 'banking"."bank_transaction'

    @pytest.mark.django_db
    def test_paginated_request_is_sql_bounded(self, auth_client, pushdown_fx):
        _assert_pushdown(
            auth_client,
            f"/api/v1/{pushdown_fx['org'].id}/banking/bank-transactions/",
            self.TABLE,
            pushdown_fx,
            total=3,
        )
