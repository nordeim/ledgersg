"""
P5/H-1 + H-2 — payment accounting truth.

RED suite: allocate() must persist document.amount_paid (the outstanding-AR
basis), and voiding a payment must reverse its journal entry and release
its allocations.
"""

import uuid
from datetime import date
from decimal import Decimal

import pytest
from django.contrib.auth.hashers import make_password

from apps.banking.services import PaymentService
from apps.core.models import (
    Account,
    AppUser,
    BankAccount,
    Contact,
    FiscalPeriod,
    FiscalYear,
    InvoiceDocument,
    Organisation,
    PaymentAllocation,
    Role,
    UserOrganisation,
)

pytestmark = pytest.mark.django_db


@pytest.fixture
def user():
    user_id = uuid.uuid4()
    user = AppUser.objects.create(
        id=user_id,
        email=f"truth_{user_id.hex[:8]}@example.com",
        full_name="Payment Truth User",
        is_active=True,
    )
    user.password = make_password("testpassword123")
    user.save()
    return user


@pytest.fixture
def org(user):
    org_id = uuid.uuid4()
    org = Organisation.objects.create(
        id=org_id,
        name="Payment Truth Org",
        uen="PAYTRUTH1",
        entity_type="PRIVATE_LIMITED",
        gst_registered=True,
        gst_reg_number="M12345678",
        gst_reg_date=date(2024, 1, 1),
        fy_start_month=1,
        base_currency="SGD",
        is_active=True,
    )
    role = Role.objects.create(org=org, name="Owner", description="Full access")
    UserOrganisation.objects.create(
        user=user,
        org=org,
        role=role,
        is_default=True,
        invited_at=date(2024, 1, 1),
        accepted_at=date(2024, 1, 1),
    )
    # Payment numbering requires its sequences (schema §sequences)
    from apps.core.models import DocumentSequence

    for doc_type, prefix in [
        ("PAYMENT_RECEIVED", "RCPT-"),
        ("PAYMENT_MADE", "PAY-"),
        ("JOURNAL_ENTRY", "JE-"),
    ]:
        DocumentSequence.objects.create(
            org=org,
            document_type=doc_type,
            prefix=prefix,
            next_number=1,
            padding=5,
        )
    fy = FiscalYear.objects.create(
        org=org,
        label="FY2024",
        start_date=date(2024, 1, 1),
        end_date=date(2024, 12, 31),
        is_closed=False,
    )
    FiscalPeriod.objects.create(
        org=org,
        fiscal_year=fy,
        label="Jan 2024",
        period_number=1,
        start_date=date(2024, 1, 1),
        end_date=date(2024, 1, 31),
        is_open=True,
    )
    return org


@pytest.fixture
def accounts(org):
    """Minimal chart matching the real seed's control codes."""
    bank = Account.objects.create(
        org=org, code="1100", name="Bank Account", account_type="ASSET", is_bank=True
    )
    ar = Account.objects.create(
        org=org, code="1200", name="Accounts Receivable", account_type="ASSET"
    )
    return {"bank": bank, "ar": ar}


@pytest.fixture
def bank_account(org, accounts):
    return BankAccount.objects.create(
        org=org,
        account_name="Main Operating Account",
        bank_name="DBS Bank",
        account_number="1234567890",
        gl_account=accounts["bank"],
        is_active=True,
        paynow_type=None,  # NULL required: '' violates paynow_type_check
        paynow_id=None,
    )


@pytest.fixture
def customer(org, accounts):
    return Contact.objects.create(
        org=org,
        contact_type="CUSTOMER",
        name="Truth Customer Pte Ltd",
        email="customer@truth.example",
        is_customer=True,
        is_supplier=False,
        payment_terms_days=30,
        receivable_account=accounts["ar"],
    )


def _approved_invoice(org, customer, total_incl=Decimal("1090.0000")):
    return InvoiceDocument.objects.create(
        org=org,
        document_type="SALES_INVOICE",
        document_number=f"INV-{uuid.uuid4().hex[:6].upper()}",
        contact=customer,
        issue_date=date(2024, 1, 1),
        due_date=date(2024, 1, 31),
        total_excl=(total_incl / Decimal("1.09")).quantize(Decimal("0.0001")),
        gst_total=(total_incl - total_incl / Decimal("1.09")).quantize(
            Decimal("0.0001")
        ),
        total_incl=total_incl,
        status="APPROVED",
    )


def _received_payment(org, bank_account, customer, user, amount):
    return PaymentService.create_received(
        org_id=org.id,
        data={
            "contact_id": customer.id,
            "bank_account_id": bank_account.id,
            "payment_date": date(2024, 1, 15),
            "amount": amount,
            "payment_method": "BANK_TRANSFER",
        },
        user_id=user.id,
    )


class TestAllocateWritesAmountPaid:
    """P5/H-1: allocate() must persist document.amount_paid."""

    def test_partial_allocation_writes_amount_paid(
        self, org, bank_account, customer, user
    ):
        invoice = _approved_invoice(org, customer)
        payment = _received_payment(
            org, bank_account, customer, user, Decimal("2000.00")
        )

        PaymentService.allocate(
            org_id=org.id,
            payment_id=payment.id,
            allocations=[
                {
                    "document_id": invoice.id,
                    "allocated_amount": Decimal("400.00"),
                }
            ],
            user_id=user.id,
        )

        invoice.refresh_from_db()
        assert invoice.amount_paid == Decimal("400.0000"), (
            "amount_paid must equal the sum of allocations — the dashboard's "
            f"outstanding-AR filter depends on it (got {invoice.amount_paid})"
        )
        assert invoice.status == "PARTIALLY_PAID"

    def test_full_allocation_writes_amount_paid(
        self, org, bank_account, customer, user
    ):
        invoice = _approved_invoice(org, customer)
        payment = _received_payment(
            org, bank_account, customer, user, Decimal("2000.00")
        )

        PaymentService.allocate(
            org_id=org.id,
            payment_id=payment.id,
            allocations=[
                {
                    "document_id": invoice.id,
                    "allocated_amount": Decimal("1090.00"),
                }
            ],
            user_id=user.id,
        )

        invoice.refresh_from_db()
        assert invoice.amount_paid == Decimal("1090.0000")
        assert invoice.status == "PAID"


class TestVoidReversesJournal:
    """P5/H-2: voiding a payment must reverse its journal entry."""

    def test_void_creates_reversal_entry(self, org, bank_account, customer, user):
        payment = _received_payment(
            org, bank_account, customer, user, Decimal("500.00")
        )
        assert payment.journal_entry_id, "fixture: create_received posts a GL entry"

        PaymentService.void(
            org_id=org.id, payment_id=payment.id, reason="wrong amount", user_id=user.id
        )

        payment.refresh_from_db()
        original = payment.journal_entry
        original.refresh_from_db()
        assert original.is_reversed, "the voided payment's GL entry must be reversed"
        assert original.reversed_by_id, "a reversal entry must exist and be linked"

        reversal = original.reversed_by
        assert reversal.source_type == "REVERSAL"
        # mirrored lines: the reversal balances the original to net zero
        original_sum = sum(
            (line.debit - line.credit) for line in original.lines.all()
        )
        reversal_sum = sum(
            (line.debit - line.credit) for line in reversal.lines.all()
        )
        assert original_sum + reversal_sum == Decimal("0")

    def test_void_releases_allocations_and_restores_amount_paid(
        self, org, bank_account, customer, user
    ):
        invoice = _approved_invoice(org, customer)
        payment = _received_payment(
            org, bank_account, customer, user, Decimal("2000.00")
        )
        PaymentService.allocate(
            org_id=org.id,
            payment_id=payment.id,
            allocations=[
                {
                    "document_id": invoice.id,
                    "allocated_amount": Decimal("400.00"),
                }
            ],
            user_id=user.id,
        )

        PaymentService.void(
            org_id=org.id,
            payment_id=payment.id,
            reason="chargeback",
            user_id=user.id,
        )

        invoice.refresh_from_db()
        assert invoice.amount_paid == Decimal("0.0000"), (
            "a voided payment's allocations must be released — the money "
            "never landed (got amount_paid="
            f"{invoice.amount_paid})"
        )
        assert invoice.status == "APPROVED", (
            "fully-released documents return to APPROVED "
            f"(got {invoice.status})"
        )
        assert not PaymentAllocation.objects.filter(payment_id=payment.id).exists(), (
            "the voided payment's allocation rows must be removed"
        )

    def test_double_void_still_rejected(self, org, bank_account, customer, user):
        from common.exceptions import ValidationError

        payment = _received_payment(
            org, bank_account, customer, user, Decimal("500.00")
        )
        PaymentService.void(
            org_id=org.id, payment_id=payment.id, reason="first", user_id=user.id
        )
        with pytest.raises(ValidationError, match="already voided"):
            PaymentService.void(
                org_id=org.id,
                payment_id=payment.id,
                reason="second",
                user_id=user.id,
            )
