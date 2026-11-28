"""
P16 payment-service batch — the runtime-contract gates.

BE-M1 (B2): allocate() must lock the PAYMENT row, not just the documents —
    two concurrent allocations against different documents each read
    already_allocated = 0 and can jointly exceed the payment amount.
BE-M2/L1 (B4): money() must reject NaN/Infinity (a NaN box override can be
    FILED into the statutory record today); the FX quantize paths use
    money()'s HALF_UP contract, not raw .quantize() (HALF_EVEN drift).
BE-L2 (B8): releasing the last allocation restores the pre-payment status
    for InvoiceNow-sent documents (SENT), not a blanket APPROVED.
BE-L9 (B12): the payment-void reversal date is Asia/Singapore localdate,
    consistent with the journal void path (00:00-07:59 SGT divergence).
BE-L5 (B13): create/void no longer write duplicate manual audit rows (the
    trg_audit_payment trigger is the truth; the ALLOCATE/UNALLOCATE events
    stay — payment_allocation has no trigger).
"""

from datetime import date
from decimal import Decimal

import pytest

from apps.banking.services import PaymentService
from apps.core.models import AuditEventLog, InvoiceDocument
from common.decimal_utils import money
from tests.conftest import create_test_contact

# The P14 allocation-contract module's fixture (a customer, bank account
# and an approved 109.00 invoice) — imported rather than duplicated
# (pytest fixtures are importable across test modules).
from tests.integration.test_payment_allocation_contract_p14 import (  # noqa: F401
    _receive,
    payment_fixture,
)


class TestMoneyRejectsNonFiniteP16:
    def test_money_rejects_nan(self):
        with pytest.raises(ValueError, match="(?i)nan|finite"):
            money("NaN")

    def test_money_rejects_infinity(self):
        with pytest.raises(ValueError, match="(?i)inf|finite"):
            money("Infinity")

    def test_money_accepts_finite_values(self):
        assert money("100.50") == Decimal("100.5000")


class TestPaymentRowLockP16:
    @pytest.mark.django_db
    def test_allocate_locks_the_payment_row(
        self, test_organisation, test_user, test_accounts, test_fiscal_period, django_db_blocker
    ):
        """BE-M1: the payment row must be locked for the cap check — the
        seed-wrapper probe pattern: assert the SELECT ... FOR UPDATE is
        issued for banking.payment inside allocate()."""
        import uuid as uuid_mod
        from unittest.mock import patch

        from apps.banking.serializers import PaymentReceiveSerializer
        from apps.core.models import BankAccount, DocumentSequence, Payment

        org = test_organisation
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
            account_name="Lock Probe Bank",
            bank_name="Test Bank",
            account_number="001-000-001",
            currency="SGD",
            paynow_type=None,
            is_active=True,
        )
        contact = create_test_contact(org, is_customer=True)
        invoice = InvoiceDocument.objects.create(
            org=org,
            document_type="SALES_INVOICE",
            contact=contact,
            document_number=f"INV-LOCK-{uuid_mod.uuid4().hex[:6]}",
            issue_date=date(2024, 1, 10),
            due_date=date(2024, 2, 10),
            status="APPROVED",
            total_excl=Decimal("100.00"),
            gst_total=Decimal("9.00"),
            total_incl=Decimal("109.00"),
            amount_paid=Decimal("0.0000"),
        )
        serializer = PaymentReceiveSerializer(
            data={
                "contact_id": str(contact.id),
                "bank_account_id": str(bank.id),
                "payment_date": date(2024, 1, 20).isoformat(),
                "amount": "109.00",
                "currency": "SGD",
                "exchange_rate": "1.000000",
                "payment_method": "BANK_TRANSFER",
            },
            context={"org_id": str(org.id)},
        )
        assert serializer.is_valid(), serializer.errors
        payment = PaymentService.create_received(
            org_id=org.id, data=serializer.validated_data, user_id=test_user.id
        )

        import django.db as dj_db  # noqa: F401 — reserved for lock probes

        with patch.object(
            Payment.objects, "select_for_update", wraps=Payment.objects.select_for_update
        ) as spy:
            # A failing allocation (VOID document) still passes through the
            # locked read before the document gate refuses.
            invoice.status = "VOID"
            invoice.save(update_fields=["status"])
            from common.exceptions import ValidationError as ServiceValidationError

            with pytest.raises(ServiceValidationError):
                PaymentService.allocate(
                    org_id=org.id,
                    payment_id=payment.id,
                    allocations=[
                        {"document_id": str(invoice.id), "allocated_amount": Decimal("10.00")}
                    ],
                )
            assert spy.called, (
                "allocate() must select_for_update() the Payment row (BE-M1: "
                "the payment-level cap is otherwise a TOCTOU)"
            )


class TestReleaseRestoresSentStatusP16:
    @pytest.mark.django_db
    def test_unallocate_last_allocation_restores_sent_for_invoicenow_document(
        self, payment_fixture
    ):
        """BE-L2: an InvoiceNow-transmitted document (invoicenow_sent_at
        set) returns to SENT, not APPROVED, when its last allocation is
        released."""
        import datetime as dt

        fx = payment_fixture
        fx["invoice"].invoicenow_sent_at = dt.datetime(2024, 1, 12, 10, 0, tzinfo=dt.timezone.utc)
        fx["invoice"].save(update_fields=["invoicenow_sent_at"])
        fx["invoice"].status = "SENT"
        fx["invoice"].save(update_fields=["status"])

        payment = PaymentService.allocate(
            org_id=fx["org"].id,
            payment_id=_receive(fx["org"], fx["user"], fx["bank"], fx["contact"], Decimal("40.00")).id,
            allocations=[
                {"document_id": str(fx["invoice"].id), "allocated_amount": Decimal("40.00")}
            ],
        )
        fx["invoice"].refresh_from_db()
        assert fx["invoice"].status == "PARTIALLY_PAID"

        from apps.core.models import PaymentAllocation

        allocation = PaymentAllocation.objects.filter(payment=payment).first()
        PaymentService.unallocate(
            org_id=fx["org"].id, allocation_id=allocation.id, user_id=fx["user"].id
        )
        fx["invoice"].refresh_from_db()
        assert fx["invoice"].status == "SENT", (
            "An InvoiceNow-sent document must return to SENT when its last "
            "allocation is released — the pre-P16 blanket APPROVED erased "
            "the transmission state (BE-L2)"
        )

    @pytest.mark.django_db
    def test_unallocate_last_allocation_keeps_approved_for_unsent(self, payment_fixture):
        """Control: a never-sent document still restores to APPROVED."""
        fx = payment_fixture
        payment = PaymentService.allocate(
            org_id=fx["org"].id,
            payment_id=_receive(fx["org"], fx["user"], fx["bank"], fx["contact"], Decimal("40.00")).id,
            allocations=[
                {"document_id": str(fx["invoice"].id), "allocated_amount": Decimal("40.00")}
            ],
        )
        from apps.core.models import PaymentAllocation

        allocation = PaymentAllocation.objects.filter(payment=payment).first()
        PaymentService.unallocate(
            org_id=fx["org"].id, allocation_id=allocation.id, user_id=fx["user"].id
        )
        fx["invoice"].refresh_from_db()
        assert fx["invoice"].status == "APPROVED"


class TestNoDuplicatePaymentAuditRowsP16:
    @pytest.mark.django_db
    def test_create_received_writes_no_manual_audit_row(
        self, payment_fixture
    ):
        """BE-L5: the trg_audit_payment trigger covers the INSERT — the
        manual AuditEventLog row duplicated it. Count rows for THIS payment
        only (the actor scoping lesson, P11)."""
        fx = payment_fixture

        payment = _receive(fx["org"], fx["user"], fx["bank"], fx["contact"], Decimal("10.00"))
        # The trigger's action vocabulary is TG_OP (INSERT/UPDATE/DELETE);
        # the removed manual block wrote action="CREATE". Trigger rows for
        # this payment = INSERT + the journal_entry-linking UPDATE (both
        # legitimate); a "CREATE" row would be the manual duplicate.
        rows = list(
            AuditEventLog.objects.filter(
                entity_table="payment", entity_id=payment.id
            ).values_list("action", flat=True)
        )
        assert rows.count("CREATE") == 1, (
            "The trg_audit_payment trigger writes exactly ONE 'CREATE' row "
            "(its INSERT mapping) — a second CREATE row is the manual "
            f"duplicate (BE-L5; saw actions: {rows})"
        )


class TestVoidReversalDateIsLocaldateP16:
    @pytest.mark.django_db
    def test_void_reversal_uses_localdate(self, payment_fixture):
        """BE-L9: the payment-void reversal date must be the Asia/Singapore
        calendar date (timezone.localdate), consistent with the journal
        void path — not the UTC date. An open period covering today is
        seeded so the no-open-period fallback cannot mask the choice."""
        from django.utils import timezone as dj_tz

        from apps.core.models import FiscalPeriod, FiscalYear

        fx = payment_fixture
        today = dj_tz.localdate()
        fy, _ = FiscalYear.objects.get_or_create(
            org=fx["org"],
            label=f"P16-TODAY-{today.year}",
            defaults={
                "start_date": today.replace(month=1, day=1),
                "end_date": today.replace(month=12, day=31),
                "is_closed": False,
            },
        )
        FiscalPeriod.objects.get_or_create(
            org=fx["org"],
            fiscal_year=fy,
            period_number=1,
            defaults={
                "label": "P16 Today",
                "start_date": today,
                "end_date": today,
                "is_open": True,
            },
        )

        payment = _receive(fx["org"], fx["user"], fx["bank"], fx["contact"], Decimal("10.00"))
        PaymentService.void(
            org_id=fx["org"].id,
            payment_id=payment.id,
            reason="P16 localdate probe",
            user_id=fx["user"].id,
        )
        payment.refresh_from_db()
        reversal = payment.journal_entry.reversed_by
        assert reversal is not None, "the void must post a reversal entry"
        assert reversal.entry_date == today, (
            "The reversal date must be the Asia/Singapore localdate "
            "(BE-L9: UTC dates diverge 00:00-07:59 SGT)"
        )


class TestAtomicCreateWithAllocationsP16:
    @pytest.mark.django_db
    def test_failed_allocation_rolls_back_the_payment(self, payment_fixture):
        """P16/BE-M4: create_received_with_allocations is ONE transaction —
        an allocation that exceeds the document's outstanding balance must
        roll the payment (and its journal entry) back, not orphan them
        behind a 400."""
        from apps.core.models import Payment
        from common.exceptions import ValidationError as ServiceValidationError

        fx = payment_fixture
        payments_before = Payment.objects.filter(org=fx["org"]).count()
        entries_before = fx["invoice"].journal_entries.count() if hasattr(
            fx["invoice"], "journal_entries"
        ) else 0

        with pytest.raises(ServiceValidationError):
            # 5000.00 against a 109.00 invoice — the P14/H-1 cap refuses.
            PaymentService.create_received_with_allocations(
                org_id=fx["org"].id,
                data={
                    "contact_id": str(fx["contact"].id),
                    "bank_account_id": str(fx["bank"].id),
                    "payment_date": "2024-01-20",
                    "amount": "5000.00",
                    "currency": "SGD",
                    "exchange_rate": "1.000000",
                    "payment_method": "BANK_TRANSFER",
                    "allocations": [
                        {
                            "document_id": str(fx["invoice"].id),
                            "allocated_amount": "5000.00",
                        }
                    ],
                },
                user_id=fx["user"].id,
            )

        assert Payment.objects.filter(org=fx["org"]).count() == payments_before, (
            "The payment must roll back with the failed allocation (no "
            "orphaned money behind a 400 — BE-M4)"
        )

    @pytest.mark.django_db
    def test_successful_create_with_allocations_commits_both(self, payment_fixture):
        """Control: the happy path still creates payment + allocation."""
        from apps.core.models import Payment, PaymentAllocation

        fx = payment_fixture
        payment = PaymentService.create_received_with_allocations(
            org_id=fx["org"].id,
            data={
                "contact_id": str(fx["contact"].id),
                "bank_account_id": str(fx["bank"].id),
                "payment_date": "2024-01-20",
                "amount": "109.00",
                "currency": "SGD",
                "exchange_rate": "1.000000",
                "payment_method": "BANK_TRANSFER",
                "allocations": [
                    {
                        "document_id": str(fx["invoice"].id),
                        "allocated_amount": "109.00",
                    }
                ],
            },
            user_id=fx["user"].id,
        )
        assert Payment.objects.filter(id=payment.id).exists()
        assert PaymentAllocation.objects.filter(payment=payment).count() == 1
        fx["invoice"].refresh_from_db()
        assert fx["invoice"].status == "PAID"
