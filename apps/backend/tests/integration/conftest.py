"""
Shared fixtures for the integration tree.

P32/BE-P32-M2: the payment substrate fixture's conftest home. The
pre-P32 shape DEFINED it inside a sibling test module
(test_payment_allocation_contract_p14.py) and every consumer reached
it through a cross-module import — the import-is-the-side-effect
pattern that shadowed the fixture name against each consuming test's
parameter (ruff F811 ×24) and tied the fixture's availability to an
implementation detail of another test file. The conftest placement is
pytest's own resolution model: every test under tests/integration/
declares `payment_fixture` as a parameter and gets it, zero imports.

The fixture body is moved VERBATIM from its p14 birthplace (the
P14-era substrate contract: an org, a bank account, a customer
contact, an APPROVED 109.00 invoice — 100.00 + 9% GST) — the gate is
tests/integration/test_conftest_fixture_resolution_p32.py.
"""

import uuid
from datetime import date
from decimal import Decimal

import pytest

from apps.core.models import BankAccount, DocumentSequence, InvoiceDocument
from tests.conftest import create_test_contact


@pytest.fixture
def payment_fixture(test_organisation, test_user, test_accounts, test_tax_codes, test_fiscal_period):
    """A customer, a bank account, an approved 109.00 invoice (100 + 9% GST)."""
    org = test_organisation

    DocumentSequence.objects.get_or_create(
        org=org, document_type="SALES_INVOICE", defaults={"prefix": "INV-", "next_number": 1}
    )
    for doc_type, prefix in [
        ("SALES_INVOICE", "INV-"),
        ("SALES_CREDIT_NOTE", "CN-"),
        ("PAYMENT_RECEIVED", "PAY-"),
        ("PAYMENT_MADE", "PAYM-"),
    ]:
        DocumentSequence.objects.get_or_create(
            org=org, document_type=doc_type, defaults={"prefix": prefix, "next_number": 1}
        )

    bank = BankAccount.objects.create(
        org=org,
        gl_account=test_accounts["1200"],
        account_name="Test Operating",
        bank_name="Test Bank",
        account_number="001-234-567",
        currency="SGD",
        paynow_type=None,  # the DB CHECK rejects '' — NULL is "no PayNow" (P9/B-4)
        is_active=True,
    )

    contact = create_test_contact(org, is_customer=True)

    invoice = InvoiceDocument.objects.create(
        org=org,
        document_type="SALES_INVOICE",
        contact=contact,
        document_number=f"INV-P14-{uuid.uuid4().hex[:6]}",
        issue_date=date(2024, 1, 10),
        due_date=date(2024, 2, 10),
        status="APPROVED",
        total_excl=Decimal("100.00"),
        gst_total=Decimal("9.00"),
        total_incl=Decimal("109.00"),
        amount_paid=Decimal("0.0000"),
    )

    return {
        "org": org,
        "user": test_user,
        "accounts": test_accounts,
        "bank": bank,
        "contact": contact,
        "invoice": invoice,
    }
