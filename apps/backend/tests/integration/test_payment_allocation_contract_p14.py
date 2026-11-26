"""
P14/H-1 + H-2 — the payment-allocation contract.

H-1: an allocation may never exceed the document's outstanding balance
     (`amount_due`); the pre-P14 code only checked allocations against
     the PAYMENT amount, so a 5000.00 allocation against a 109.00
     invoice settled it with `amount_due = -4891.00` (negative AR).
H-2: a PARTIALLY_PAID invoice must accept its second instalment (the
     serializer demanded status == APPROVED — instalments could never
     complete through the API; SENT/OVERDUE are also allocatable).
"""

import uuid
from datetime import date
from decimal import Decimal

import pytest

from apps.banking.serializers.payment import PaymentReceiveSerializer
from apps.banking.services import PaymentService
from apps.core.models import BankAccount, DocumentSequence, InvoiceDocument
from common.exceptions import ValidationError
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


def _receive(org, user, bank, contact, amount, allocations=None):
    payload = {
        "contact_id": str(contact.id),
        "bank_account_id": str(bank.id),
        "payment_date": date(2024, 1, 20).isoformat(),
        "amount": str(amount),
        "currency": "SGD",
        "exchange_rate": "1.000000",
        "payment_method": "BANK_TRANSFER",
    }
    if allocations:
        payload["allocations"] = allocations
    return PaymentService.create_received(org_id=org.id, data=payload, user_id=user.id)


class TestAllocationCapP14:
    @pytest.mark.django_db
    def test_allocation_exceeding_amount_due_is_refused(
        self, payment_fixture
    ):
        """RED for H-1: 5000.00 allocated against a 109.00 invoice."""
        fx = payment_fixture
        with pytest.raises(ValidationError) as excinfo:
            PaymentService.allocate(
                org_id=fx["org"].id,
                payment_id=_receive(
                    fx["org"], fx["user"], fx["bank"], fx["contact"], Decimal("5000.00")
                ).id,
                allocations=[
                    {
                        "document_id": str(fx["invoice"].id),
                        "allocated_amount": Decimal("5000.00"),
                    }
                ],
            )
        assert "amount due" in str(excinfo.value).lower() or "outstanding" in str(excinfo.value).lower()

        # The document is untouched — never a negative amount_due.
        fx["invoice"].refresh_from_db()
        assert fx["invoice"].amount_paid == Decimal("0.0000")
        assert fx["invoice"].status == "APPROVED"

    @pytest.mark.django_db
    def test_full_allocation_sets_paid(self, payment_fixture):
        """H-1 control: allocating exactly the outstanding balance is valid."""
        fx = payment_fixture
        payment = _receive(fx["org"], fx["user"], fx["bank"], fx["contact"], Decimal("109.00"))
        PaymentService.allocate(
            org_id=fx["org"].id,
            payment_id=payment.id,
            allocations=[
                {
                    "document_id": str(fx["invoice"].id),
                    "allocated_amount": Decimal("109.00"),
                }
            ],
        )
        fx["invoice"].refresh_from_db()
        assert fx["invoice"].status == "PAID"
        assert fx["invoice"].amount_paid == Decimal("109.0000")


class TestInstalmentCycleP14:
    @pytest.mark.django_db
    def test_second_instalment_on_partially_paid_succeeds(self, payment_fixture):
        """RED for H-2: 40.00 then 69.00 — the invoice must reach PAID."""
        fx = payment_fixture

        first = _receive(fx["org"], fx["user"], fx["bank"], fx["contact"], Decimal("40.00"))
        PaymentService.allocate(
            org_id=fx["org"].id,
            payment_id=first.id,
            allocations=[
                {"document_id": str(fx["invoice"].id), "allocated_amount": Decimal("40.00")}
            ],
        )
        fx["invoice"].refresh_from_db()
        assert fx["invoice"].status == "PARTIALLY_PAID"

        # The second instalment — the H-2 regression (the serializer's
        # `status != "APPROVED"` branch refused exactly this).
        serializer = PaymentReceiveSerializer(
            data={
                "contact_id": str(fx["contact"].id),
                "bank_account_id": str(fx["bank"].id),
                "payment_date": date(2024, 1, 25).isoformat(),
                "amount": "69.00",
                "currency": "SGD",
                "exchange_rate": "1.000000",
                "payment_method": "BANK_TRANSFER",
                "allocations": [
                    {
                        "document_id": str(fx["invoice"].id),
                        "allocated_amount": "69.00",
                    }
                ],
            },
            context={"org_id": str(fx["org"].id)},
        )
        assert serializer.is_valid(), serializer.errors

        second = PaymentService.create_received(
            org_id=fx["org"].id, data=serializer.validated_data, user_id=fx["user"].id
        )
        PaymentService.allocate(
            org_id=fx["org"].id,
            payment_id=second.id,
            allocations=[
                {"document_id": str(fx["invoice"].id), "allocated_amount": Decimal("69.00")}
            ],
        )
        fx["invoice"].refresh_from_db()
        assert fx["invoice"].status == "PAID"
        assert fx["invoice"].amount_paid == Decimal("109.0000")

    @pytest.mark.django_db
    def test_allocation_to_void_document_is_refused(self, payment_fixture):
        """H-1: VOID documents are not allocatable (money on a voided
        document corrupts AR)."""
        fx = payment_fixture
        fx["invoice"].status = "VOID"
        fx["invoice"].save()

        payment = _receive(fx["org"], fx["user"], fx["bank"], fx["contact"], Decimal("50.00"))
        with pytest.raises(ValidationError):
            PaymentService.allocate(
                org_id=fx["org"].id,
                payment_id=payment.id,
                allocations=[
                    {"document_id": str(fx["invoice"].id), "allocated_amount": Decimal("50.00")}
                ],
            )

    @pytest.mark.django_db
    def test_allocation_to_draft_document_is_refused(self, payment_fixture):
        """H-1: DRAFT documents are not allocatable either."""
        fx = payment_fixture
        fx["invoice"].status = "DRAFT"
        fx["invoice"].save()

        payment = _receive(fx["org"], fx["user"], fx["bank"], fx["contact"], Decimal("50.00"))
        with pytest.raises(ValidationError):
            PaymentService.allocate(
                org_id=fx["org"].id,
                payment_id=payment.id,
                allocations=[
                    {"document_id": str(fx["invoice"].id), "allocated_amount": Decimal("50.00")}
                ],
            )

    @pytest.mark.django_db
    @pytest.mark.parametrize("doc_status", ["SENT", "OVERDUE"])
    def test_serializer_accepts_sent_and_overdue(self, payment_fixture, doc_status):
        """H-2: SENT/OVERDUE invoices are allocatable (billed, awaiting
        money)."""
        fx = payment_fixture
        fx["invoice"].status = doc_status
        fx["invoice"].save()

        serializer = PaymentReceiveSerializer(
            data={
                "contact_id": str(fx["contact"].id),
                "bank_account_id": str(fx["bank"].id),
                "payment_date": date(2024, 1, 25).isoformat(),
                "amount": "50.00",
                "currency": "SGD",
                "exchange_rate": "1.000000",
                "payment_method": "BANK_TRANSFER",
                "allocations": [
                    {"document_id": str(fx["invoice"].id), "allocated_amount": "50.00"}
                ],
            },
            context={"org_id": str(fx["org"].id)},
        )
        assert serializer.is_valid(), serializer.errors


class TestWireEndpointInstalmentContractP16:
    """P16/BE-H2: the dedicated allocate ENDPOINT must accept instalments.

    The P14/H-2 fix landed in the service and the embedded-path serializer
    but BulkAllocationSerializer (the POST /payments/{id}/allocate/ wire
    contract) still demanded APPROVED-only — a PARTIALLY_PAID invoice 400'd
    on the dedicated endpoint while the embedded path worked. The endpoint
    is what the standalone allocation flow (Banking → Payments → Allocate)
    uses.
    """

    @pytest.mark.django_db
    def test_bulk_serializer_accepts_partially_paid_instalment(self, payment_fixture):
        from apps.banking.serializers.allocation import BulkAllocationSerializer

        fx = payment_fixture
        first = _receive(fx["org"], fx["user"], fx["bank"], fx["contact"], Decimal("40.00"))
        PaymentService.allocate(
            org_id=fx["org"].id,
            payment_id=first.id,
            allocations=[
                {"document_id": str(fx["invoice"].id), "allocated_amount": Decimal("40.00")}
            ],
        )
        fx["invoice"].refresh_from_db()
        assert fx["invoice"].status == "PARTIALLY_PAID"

        second = _receive(fx["org"], fx["user"], fx["bank"], fx["contact"], Decimal("69.00"))
        serializer = BulkAllocationSerializer(
            data={
                "payment_id": str(second.id),
                "allocations": [
                    {
                        "document_id": str(fx["invoice"].id),
                        "allocated_amount": "69.00",
                    }
                ],
            },
            context={"org_id": str(fx["org"].id)},
        )
        assert serializer.is_valid(), serializer.errors

    @pytest.mark.django_db
    def test_bulk_serializer_accepts_sent_document(self, payment_fixture):
        from apps.banking.serializers.allocation import BulkAllocationSerializer

        fx = payment_fixture
        fx["invoice"].status = "SENT"
        fx["invoice"].save(update_fields=["status"])
        payment = _receive(fx["org"], fx["user"], fx["bank"], fx["contact"], Decimal("109.00"))
        serializer = BulkAllocationSerializer(
            data={
                "payment_id": str(payment.id),
                "allocations": [
                    {
                        "document_id": str(fx["invoice"].id),
                        "allocated_amount": "109.00",
                    }
                ],
            },
            context={"org_id": str(fx["org"].id)},
        )
        assert serializer.is_valid(), serializer.errors

    @pytest.mark.django_db
    @pytest.mark.parametrize("doc_status", ["DRAFT", "VOID"])
    def test_bulk_serializer_still_refuses_draft_and_void(self, payment_fixture, doc_status):
        from apps.banking.serializers.allocation import BulkAllocationSerializer

        fx = payment_fixture
        fx["invoice"].status = doc_status
        fx["invoice"].save(update_fields=["status"])
        payment = _receive(fx["org"], fx["user"], fx["bank"], fx["contact"], Decimal("109.00"))
        serializer = BulkAllocationSerializer(
            data={
                "payment_id": str(payment.id),
                "allocations": [
                    {
                        "document_id": str(fx["invoice"].id),
                        "allocated_amount": "109.00",
                    }
                ],
            },
            context={"org_id": str(fx["org"].id)},
        )
        assert not serializer.is_valid()
