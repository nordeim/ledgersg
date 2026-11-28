"""
P29 contract gates — the detail-view N+1 closure.

BE-P29-H1: the three detail surfaces (document detail, journal entry
    detail, payment detail) fetched the row with a plain
    `.objects.get(...)` while the serializers walked the related FKs
    PER LINE (the invoice/quote lines walk account + tax_code; the
    journal lines walk account) or per related object (the payment
    walks contact + bank_account) — a detail page cost one detail PER
    LINE, the detail-surface sibling of the P28 list push-down. These
    gates pin the query-level truth the response tests cannot see: a
    detail request issues a bounded, line-count-independent set of
    SELECTs — never a per-line FK walk.
Counter-pins (the fix must not change them): the detail payload — the
    line count, the account codes, the totals — stays byte-identical.
"""

from datetime import date

import pytest
from django.db import connection
from django.test.utils import CaptureQueriesContext
from rest_framework import status

from apps.invoicing.services import ContactService, DocumentService

# ---------------------------------------------------------------------------
# fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def detail_fx(
    test_organisation, test_user, test_accounts, test_tax_codes, test_fiscal_period
):
    """A 3-line invoice, a 3-line journal entry, one received payment —
    every surface carries MORE lines than the bounded-query probe, so a
    per-line walk actually multiplies (the P28 pushdown_fx conventions,
    with the line counts raised to make the N visible)."""
    fx = {
        "org": test_organisation,
        "user": test_user,
        "accounts": test_accounts,
    }
    from apps.core.models import DocumentSequence

    for doc_type, prefix in [
        ("SALES_INVOICE", "INV-"),
        ("PAYMENT_RECEIVED", "PAY-"),
    ]:
        DocumentSequence.objects.get_or_create(
            org=fx["org"], document_type=doc_type, defaults={"prefix": prefix, "next_number": 1}
        )

    contact = ContactService.create_contact(
        org_id=fx["org"].id, name="P29 Detail Customer", email="", is_customer=True
    )
    fx["contact"] = contact

    # the 3-line document — every line walks account + tax_code in the
    # detail serializer (the RED probe's multiplication source)
    fx["document"] = DocumentService.create_document(
        org_id=fx["org"].id,
        document_type="SALES_INVOICE",
        contact_id=contact.id,
        issue_date=date(2024, 3, 1),
        lines=[
            {
                "description": f"P29 detail line {i}",
                "account_id": str(test_accounts["4000"].id),
                "quantity": "1.0000",
                "unit_price": "100.00",
                "tax_code_id": str(test_tax_codes["SR"].id),
            }
            for i in range(3)
        ],
        user_id=fx["user"].id,
    )

    # the 3-line journal entry — every line walks account in the detail
    # serializer (balanced: one debit, two credits). NOTE: the fiscal
    # period fixture opens JANUARY 2024 only — the entry date must fall
    # inside it.
    from apps.journal.services import JournalService

    fx["entry"] = JournalService.create_entry(
        org_id=fx["org"].id,
        entry_date=date(2024, 1, 15),
        source_type="MANUAL",
        narration="P29 detail query probe",
        lines=[
            {
                "account_id": str(test_accounts["1200"].id),
                "debit": "100.00",
                "credit": "0",
                "description": "P29 debit line",
            },
            {
                "account_id": str(test_accounts["4000"].id),
                "debit": "0",
                "credit": "60.00",
                "description": "P29 credit line 1",
            },
            {
                "account_id": str(test_accounts["4000"].id),
                "debit": "0",
                "credit": "40.00",
                "description": "P29 credit line 2",
            },
        ],
        user_id=fx["user"].id,
    )

    # the received payment — the detail serializer walks contact +
    # bank_account on the plain .get()
    from apps.core.models import BankAccount

    bank = BankAccount.objects.create(
        org=fx["org"],
        gl_account=test_accounts["1200"],
        account_name="P29 Operating",
        bank_name="P29 Bank",
        account_number="001-135-790",
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
    return fx


# ---------------------------------------------------------------------------
# the shared probes
# ---------------------------------------------------------------------------


def _selects_touching(ctx, anchor):
    """The SELECT queries whose SQL mentions the anchor table."""
    sqls = [q["sql"] for q in ctx.captured_queries]
    return [s for s in sqls if anchor in s and s.lstrip().upper().startswith("SELECT")]


# ---------------------------------------------------------------------------
# BE-P29-H1 — the three detail surfaces
# ---------------------------------------------------------------------------


class TestDocumentDetailQueryCountP29:
    """A document detail page costs one detail, not one detail per line."""

    ACCOUNT = 'coa"."account'
    TAX_CODE = 'gst"."tax_code'
    CONTACT = 'invoicing"."contact'
    DOCUMENT = 'invoicing"."document'

    @pytest.mark.django_db
    def test_detail_lines_fetch_is_bounded_not_per_line(self, auth_client, detail_fx):
        url = f"/api/v1/{detail_fx['org'].id}/invoicing/documents/{detail_fx['document'].id}/"
        with CaptureQueriesContext(connection) as ctx:
            response = auth_client.get(url)
        assert response.status_code == status.HTTP_200_OK, response.data

        # (a) the account rows arrive via ONE joined SELECT, not a
        # per-line walk (RED now: 3 separate SELECTs on a 3-line doc)
        account_selects = _selects_touching(ctx, self.ACCOUNT)
        assert len(account_selects) <= 1, (
            f"the document detail walked the account table "
            f"{len(account_selects)} times on a 3-line document — the "
            f"per-line N+1 (BE-P29-H1): "
            f"{[s[:160] for s in account_selects]}"
        )

        # (b) the tax-code rows the same (RED now: 3)
        tax_selects = _selects_touching(ctx, self.TAX_CODE)
        assert len(tax_selects) <= 1, (
            f"the document detail walked the tax_code table "
            f"{len(tax_selects)} times on a 3-line document — the "
            f"per-line N+1 (BE-P29-H1): "
            f"{[s[:160] for s in tax_selects]}"
        )

        # (c) the contact rides the main document query (select_related),
        # not its own walk
        doc_selects = [
            s
            for s in _selects_touching(ctx, self.DOCUMENT)
            if "invoice_line" not in s
        ]
        assert doc_selects, "no query touched the document table"
        assert self.CONTACT in doc_selects[0], (
            "the document fetch is single-table — the contact rides its "
            f"own walk (BE-P29-H1): {doc_selects[0][:200]}"
        )

        # the counter-pin: the payload is unchanged
        assert len(response.data["lines"]) == 3
        assert response.data["contact"]["name"] == "P29 Detail Customer"
        assert {line["account_code"] for line in response.data["lines"]} == {"4000"}


class TestJournalEntryDetailQueryCountP29:
    """A journal entry detail page costs one detail, not one per line."""

    ACCOUNT = 'coa"."account'

    @pytest.mark.django_db
    def test_detail_lines_fetch_is_bounded_not_per_line(self, auth_client, detail_fx):
        url = f"/api/v1/{detail_fx['org'].id}/journal-entries/entries/{detail_fx['entry'].id}/"
        with CaptureQueriesContext(connection) as ctx:
            response = auth_client.get(url)
        assert response.status_code == status.HTTP_200_OK, response.data

        # the account rows arrive via ONE joined SELECT, not a per-line
        # walk (RED now: 3 separate SELECTs on a 3-line entry)
        account_selects = _selects_touching(ctx, self.ACCOUNT)
        assert len(account_selects) <= 1, (
            f"the journal entry detail walked the account table "
            f"{len(account_selects)} times on a 3-line entry — the "
            f"per-line N+1 (BE-P29-H1): "
            f"{[s[:160] for s in account_selects]}"
        )

        # the counter-pin: the payload is unchanged
        assert len(response.data["lines"]) == 3
        assert {line["account_code"] for line in response.data["lines"]} == {"1200", "4000"}


class TestPaymentDetailQueryCountP29:
    """A payment detail page joins its related rows, never walks them."""

    PAYMENT = 'banking"."payment'
    CONTACT = 'invoicing"."contact'
    BANK_ACCOUNT = 'banking"."bank_account'

    @pytest.mark.django_db
    def test_detail_related_rows_ride_the_payment_query(self, auth_client, detail_fx):
        url = f"/api/v1/{detail_fx['org'].id}/banking/payments/{detail_fx['payment'].id}/"
        with CaptureQueriesContext(connection) as ctx:
            response = auth_client.get(url)
        assert response.status_code == status.HTTP_200_OK, response.data

        # exactly ONE query fetches the payment row, and it carries the
        # contact + bank_account JOINs (RED now: the payment query is
        # single-table and each related row rides its own walk)
        payment_selects = [
            s
            for s in _selects_touching(ctx, self.PAYMENT)
            if "payment_allocation" not in s
        ]
        assert len(payment_selects) == 1, (
            f"expected exactly 1 payment-row SELECT, got "
            f"{len(payment_selects)}: {[s[:160] for s in payment_selects]}"
        )
        assert self.CONTACT in payment_selects[0], (
            "the payment fetch is single-table — the contact rides its "
            f"own walk (BE-P29-H1): {payment_selects[0][:200]}"
        )
        assert self.BANK_ACCOUNT in payment_selects[0], (
            "the payment fetch is single-table — the bank_account rides "
            f"its own walk (BE-P29-H1): {payment_selects[0][:200]}"
        )

        # the counter-pin: the payload is unchanged
        assert response.data["contact_name"] == "P29 Detail Customer"
        assert response.data["bank_account_name"] == "P29 Operating"
        assert response.data["amount"] == "50.0000" or response.data["amount"] == "50.00"
