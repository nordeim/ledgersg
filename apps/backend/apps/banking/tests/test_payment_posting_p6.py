"""
P6/F-4 + F-5 + F-6 + F-7 — payment posting integrity.

RED suite:
- F-4: allocate() must accept PARTIALLY_PAID documents (second allocations).
- F-5: the payment journal entry must land AR/AP on the EXACT control
  accounts (1200/2100), never a broad account_type .first() match, and
  must fail closed when the control account does not exist.
- F-6: create_contact assigns default AR/AP control accounts so the
  normal path never depends on the fallback.
- F-7: unallocate() recomputes document.amount_paid / status (and thus
  the amount_due generated column) instead of only resetting at zero.
"""

import uuid
from datetime import date
from decimal import Decimal

import pytest
from django.contrib.auth.hashers import make_password
from django.db import connection

from apps.banking.services import PaymentService
from apps.core.models import (
    Account,
    AppUser,
    BankAccount,
    Contact,
    FiscalPeriod,
    FiscalYear,
    InvoiceDocument,
    JournalEntry,
    Organisation,
    PaymentAllocation,
    Role,
    UserOrganisation,
)
from apps.invoicing.services import ContactService

pytestmark = pytest.mark.django_db


@pytest.fixture
def user():
    user_id = uuid.uuid4()
    user = AppUser.objects.create(
        id=user_id,
        email=f"p6_{user_id.hex[:8]}@example.com",
        full_name="P6 Payment Posting User",
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
        name="P6 Posting Org",
        uen="P6POSTING1",
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
    """
    Chart with decoys planted BEFORE the control accounts.

    1010 'Cash on Hand' (an asset that is NOT the AR control account) and
    the 2000 'Liabilities' header are created first: the pre-P5 broad
    Q(account_type=...) .first() fallback can pick them, the P5/H-4 exact
    resolver must not.
    """
    decoy_cash = Account.objects.create(
        org=org, code="1010", name="Cash on Hand", account_type="ASSET"
    )
    bank = Account.objects.create(
        org=org, code="1100", name="Bank Account", account_type="ASSET", is_bank=True
    )
    ar = Account.objects.create(
        org=org, code="1200", name="Accounts Receivable", account_type="ASSET"
    )
    liabilities_header = Account.objects.create(
        org=org, code="2000", name="Liabilities", account_type="LIABILITY", is_header=True
    )
    ap = Account.objects.create(
        org=org, code="2100", name="Accounts Payable", account_type="LIABILITY"
    )
    return {
        "decoy_cash": decoy_cash,
        "bank": bank,
        "ar": ar,
        "liabilities_header": liabilities_header,
        "ap": ap,
    }


@pytest.fixture
def bank_account(org, accounts):
    return BankAccount.objects.create(
        org=org,
        account_name="Main Operating Account",
        bank_name="DBS Bank",
        account_number="1234567890",
        gl_account=accounts["bank"],
        is_active=True,
        paynow_type=None,
        paynow_id=None,
    )


@pytest.fixture
def customer(org):
    """API-created contact — no control accounts (the F-6 general case)."""
    return Contact.objects.create(
        org=org,
        contact_type="CUSTOMER",
        name="P6 Customer Pte Ltd",
        email="customer@p6.example",
        is_customer=True,
        is_supplier=False,
        payment_terms_days=30,
    )


@pytest.fixture
def supplier(org):
    return Contact.objects.create(
        org=org,
        contact_type="SUPPLIER",
        name="P6 Supplier Pte Ltd",
        email="supplier@p6.example",
        is_customer=False,
        is_supplier=True,
        payment_terms_days=30,
    )


def _approved_invoice(org, contact, total_incl=Decimal("1090.0000")):
    return InvoiceDocument.objects.create(
        org=org,
        document_type="SALES_INVOICE",
        document_number=f"INV-{uuid.uuid4().hex[:6].upper()}",
        contact=contact,
        issue_date=date(2024, 1, 1),
        due_date=date(2024, 1, 31),
        total_excl=(total_incl / Decimal("1.09")).quantize(Decimal("0.0001")),
        gst_total=(total_incl - total_incl / Decimal("1.09")).quantize(
            Decimal("0.0001")
        ),
        total_incl=total_incl,
        status="APPROVED",
    )


def _received_payment(org, bank_account, contact, user, amount):
    return PaymentService.create_received(
        org_id=org.id,
        data={
            "contact_id": contact.id,
            "bank_account_id": bank_account.id,
            "payment_date": date(2024, 1, 15),
            "amount": amount,
            "payment_method": "BANK_TRANSFER",
        },
        user_id=user.id,
    )


def _made_payment(org, bank_account, contact, user, amount):
    return PaymentService.create_made(
        org_id=org.id,
        data={
            "contact_id": contact.id,
            "bank_account_id": bank_account.id,
            "payment_date": date(2024, 1, 15),
            "amount": amount,
            "payment_method": "BANK_TRANSFER",
        },
        user_id=user.id,
    )


def _raw_amount_due(document):
    """amount_due is a DB generated column, not a model field."""
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT amount_due FROM invoicing.document WHERE id = %s",
            [str(document.id)],
        )
        return Decimal(cursor.fetchone()[0])


class TestSecondAllocationOnPartiallyPaid:
    """P6/F-4: PARTIALLY_PAID must not be a dead-end state."""

    def test_second_allocation_on_partially_paid_document(
        self, org, bank_account, customer, user
    ):
        invoice = _approved_invoice(org, customer)
        payment1 = _received_payment(org, bank_account, customer, user, Decimal("2000.00"))
        payment2 = _received_payment(org, bank_account, customer, user, Decimal("2000.00"))

        PaymentService.allocate(
            org_id=org.id,
            payment_id=payment1.id,
            allocations=[{"document_id": invoice.id, "allocated_amount": Decimal("400.00")}],
            user_id=user.id,
        )
        invoice.refresh_from_db()
        assert invoice.status == "PARTIALLY_PAID"

        # The natural second payment settling the remainder.
        PaymentService.allocate(
            org_id=org.id,
            payment_id=payment2.id,
            allocations=[{"document_id": invoice.id, "allocated_amount": Decimal("690.00")}],
            user_id=user.id,
        )
        invoice.refresh_from_db()
        assert invoice.amount_paid == Decimal("1090.0000")
        assert invoice.status == "PAID"

    def test_allocation_on_paid_document_still_rejected(
        self, org, bank_account, customer, user
    ):
        invoice = _approved_invoice(org, customer)
        payment1 = _received_payment(org, bank_account, customer, user, Decimal("2000.00"))
        payment2 = _received_payment(org, bank_account, customer, user, Decimal("2000.00"))

        PaymentService.allocate(
            org_id=org.id,
            payment_id=payment1.id,
            allocations=[{"document_id": invoice.id, "allocated_amount": Decimal("1090.00")}],
            user_id=user.id,
        )

        from common.exceptions import ValidationError as AppValidationError

        with pytest.raises(AppValidationError):
            PaymentService.allocate(
                org_id=org.id,
                payment_id=payment2.id,
                allocations=[
                    {"document_id": invoice.id, "allocated_amount": Decimal("10.00")}
                ],
                user_id=user.id,
            )


class TestExactControlAccounts:
    """P6/F-5: AR/AP land on 1200/2100 exactly — never a broad match."""

    def test_received_payment_je_lands_ar_on_exact_control_account(
        self, org, bank_account, customer, user, accounts
    ):
        _received_payment(
            org, bank_account, customer, user, Decimal("500.00")
        )

        entry = JournalEntry.objects.filter(
            org_id=org.id, source_type="PAYMENT_RECEIVED"
        ).first()
        assert entry is not None, "payment JE must exist"
        lines = entry.lines.select_related("account")
        credited = [line for line in lines if line.credit > 0]
        assert len(credited) == 1
        assert credited[0].account.code == "1200", (
            "AR credit must land on 1200 Accounts Receivable — a broad "
            f"account_type match landed on {credited[0].account.code} "
            f"{credited[0].account.name}"
        )
        assert credited[0].account.id != accounts["decoy_cash"].id

    def test_made_payment_je_lands_ap_on_exact_control_account(
        self, org, bank_account, supplier, user, accounts
    ):
        _made_payment(org, bank_account, supplier, user, Decimal("500.00"))

        entry = JournalEntry.objects.filter(
            org_id=org.id, source_type="PAYMENT_RECEIVED"
        ).first()
        assert entry is not None
        lines = entry.lines.select_related("account")
        debited = [line for line in lines if line.debit > 0]
        assert len(debited) == 1
        assert debited[0].account.code == "2100", (
            "AP debit must land on 2100 Accounts Payable — a broad match "
            f"landed on {debited[0].account.code} {debited[0].account.name}"
        )
        assert debited[0].account.id != accounts["liabilities_header"].id

    def test_payment_je_fails_closed_without_control_account(
        self, org, bank_account, customer, user, accounts
    ):
        # Rename code AND name so neither the code arm nor the name arm of
        # the exact resolver can match.
        accounts["ar"].code = "9100"
        accounts["ar"].name = "Legacy Receivables"
        accounts["ar"].save()

        from common.exceptions import ValidationError as AppValidationError

        with pytest.raises(AppValidationError):
            _received_payment(org, bank_account, customer, user, Decimal("500.00"))


class TestContactControlAccountDefaults:
    """P6/F-6: create_contact assigns default AR/AP control accounts."""

    def test_create_contact_assigns_default_ar_account(self, org, accounts):
        contact = ContactService.create_contact(
            org_id=org.id,
            name="New Customer Pte Ltd",
            email="new.customer@p6.example",
            is_customer=True,
            is_supplier=False,
        )
        assert contact.receivable_account is not None
        assert contact.receivable_account.code == "1200"
        assert contact.payable_account is None

    def test_create_contact_assigns_default_ap_account(self, org, accounts):
        contact = ContactService.create_contact(
            org_id=org.id,
            name="New Supplier Pte Ltd",
            email="new.supplier@p6.example",
            is_customer=False,
            is_supplier=True,
        )
        assert contact.payable_account is not None
        assert contact.payable_account.code == "2100"
        assert contact.receivable_account is None

    def test_create_contact_both_types_get_both_accounts(self, org, accounts):
        contact = ContactService.create_contact(
            org_id=org.id,
            name="Both Ways Pte Ltd",
            email="both.ways@p6.example",
            is_customer=True,
            is_supplier=True,
        )
        assert contact.receivable_account is not None
        assert contact.receivable_account.code == "1200"
        assert contact.payable_account is not None
        assert contact.payable_account.code == "2100"


class TestUnallocateRecomputesAmountPaid:
    """P6/F-7: unallocate keeps amount_paid/status/amount_due truthful."""

    def test_unallocate_recomputes_amount_paid_and_status(
        self, org, bank_account, customer, user
    ):
        invoice = _approved_invoice(org, customer)
        payment = _received_payment(org, bank_account, customer, user, Decimal("2000.00"))

        PaymentService.allocate(
            org_id=org.id,
            payment_id=payment.id,
            allocations=[{"document_id": invoice.id, "allocated_amount": Decimal("400.00")}],
            user_id=user.id,
        )
        invoice.refresh_from_db()
        assert invoice.amount_paid == Decimal("400.0000")
        assert invoice.status == "PARTIALLY_PAID"
        assert _raw_amount_due(invoice) == Decimal("690.0000")

        allocation = PaymentAllocation.objects.get(payment=payment, document=invoice)
        PaymentService.unallocate(
            org_id=org.id, allocation_id=allocation.id, user_id=user.id
        )

        invoice.refresh_from_db()
        assert invoice.amount_paid == Decimal("0.0000"), (
            "unallocate must recompute amount_paid from the surviving "
            f"allocations (got {invoice.amount_paid})"
        )
        assert invoice.status == "APPROVED"
        assert _raw_amount_due(invoice) == Decimal("1090.0000")

    def test_unallocate_with_remaining_stays_partially_paid(
        self, org, bank_account, customer, user
    ):
        invoice = _approved_invoice(org, customer)
        payment1 = _received_payment(org, bank_account, customer, user, Decimal("2000.00"))
        payment2 = _received_payment(org, bank_account, customer, user, Decimal("2000.00"))

        PaymentService.allocate(
            org_id=org.id,
            payment_id=payment1.id,
            allocations=[{"document_id": invoice.id, "allocated_amount": Decimal("400.00")}],
            user_id=user.id,
        )
        PaymentService.allocate(
            org_id=org.id,
            payment_id=payment2.id,
            allocations=[{"document_id": invoice.id, "allocated_amount": Decimal("300.00")}],
            user_id=user.id,
        )
        invoice.refresh_from_db()
        assert invoice.amount_paid == Decimal("700.0000")

        allocation2 = PaymentAllocation.objects.get(payment=payment2, document=invoice)
        PaymentService.unallocate(
            org_id=org.id, allocation_id=allocation2.id, user_id=user.id
        )

        invoice.refresh_from_db()
        assert invoice.amount_paid == Decimal("400.0000")
        assert invoice.status == "PARTIALLY_PAID"
        assert _raw_amount_due(invoice) == Decimal("690.0000")
