"""
P20 concurrency-contract gates — the void/transition lock completion,
the allocate sorted pre-lock, and the posting-side cache invalidation.

BE-H1: void() recomputes and saves the affected documents WITHOUT the
    document row lock (a plain filter().distinct() read, unlocked SUM,
    full-row save). allocate() (:470-479) and unallocate() (:656-675, the
    P19/BE-M3 fix) both hold the invoicing.document lock when they touch
    amount_paid — void() is the odd one out. A T2 allocate() that commits
    between void's SUM and its write is silently lost (the P14/H-1
    "allocations are the truth" invariant violated). Also AB-BA: two
    concurrent voids over shared documents lock rows at UPDATE time in
    DB-dependent orders (BE-P20-M2 — same fix).
BE-H3: transition_status() still carries the unlocked gate + stale
    full-row save that P19/BE-H1 fixed for remove_line(): a plain read,
    a transition-map check against the STALE status, then a full-row
    document.save() — a concurrent approve_document() (which locks) can
    commit DRAFT->APPROVED + the journal posting between the read and
    the save; the stale save then writes SENT over the APPROVED,
    journal-posted document and clobbers the totals with pre-add_line
    values. Must lock + re-validate post-lock + update_fields.
BE-M1: allocate() locks the documents in user-supplied order — two
    concurrent allocations against overlapping document sets in opposite
    orders deadlock (PG 40P01 -> untyped 500). The create_entry() sorted
    deduplicated pre-lock (P19/BE-M2) is the pattern.
BE-M5: the account_balance 5-minute cache is never invalidated by
    journal postings — the P19/BE-M1 fix patched the archive gate only,
    so GET /accounts/{id}/balance/ serves a pre-posting balance for up
    to 5 minutes. create_entry() must delete the cache key for every
    account it touches.
BE-L2: the allocate() service seam does not gate positive amounts —
    the DB CHECK chk_allocated_positive turns a non-DRF caller's
    zero/negative allocation into an untyped IntegrityError (the
    serializers gate it; the seam must too).
BE-L3: unreconcile()'s payment lock is the one lock in the banking
    services without the org_id= filter — defense-in-depth consistency.
"""

from datetime import date
from decimal import Decimal
from unittest.mock import patch

import pytest

from apps.banking.services import PaymentService, ReconciliationService
from apps.core.models import (
    BankAccount,
    InvoiceDocument,
    PaymentAllocation,
)
from apps.invoicing.services import DocumentService
from common.exceptions import ValidationError as ServiceValidationError
from tests.integration.test_payment_allocation_contract_p14 import (  # noqa: F401
    _receive,
    payment_fixture,
)


@pytest.fixture
def two_invoice_payment_fixture(
    test_organisation, test_user, test_accounts, test_tax_codes, test_fiscal_period
):
    """One payment allocated across TWO invoices — the void() multi-document
    surface (the sorted-lock and interleaving probes need >1 document)."""
    from apps.core.models import DocumentSequence, InvoiceDocument
    from tests.conftest import create_test_contact

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
        account_name="P20 Void Bank",
        bank_name="Test Bank",
        account_number="001-999-001",
        currency="SGD",
        paynow_type=None,
        is_active=True,
    )
    contact = create_test_contact(org, is_customer=True)
    invoices = []
    for i, total in enumerate([Decimal("100.00"), Decimal("200.00")]):
        invoices.append(
            InvoiceDocument.objects.create(
                org=org,
                document_type="SALES_INVOICE",
                contact=contact,
                document_number=f"INV-P20-{i}-{uuid4_hex()}",
                issue_date=date(2024, 1, 10),
                due_date=date(2024, 2, 10),
                status="APPROVED",
                total_excl=total,
                gst_total=Decimal("0.00"),
                total_incl=total,
                amount_paid=Decimal("0.0000"),
            )
        )
    payment = _receive(org, test_user, bank, contact, Decimal("300.00"))
    PaymentService.allocate(
        org_id=org.id,
        payment_id=payment.id,
        allocations=[
            {"document_id": str(invoices[0].id), "allocated_amount": Decimal("100.00")},
            {"document_id": str(invoices[1].id), "allocated_amount": Decimal("200.00")},
        ],
    )
    return {
        "org": org,
        "user": test_user,
        "bank": bank,
        "contact": contact,
        "invoices": invoices,
        "payment": payment,
    }


def uuid4_hex() -> str:
    from uuid import uuid4

    return uuid4().hex[:8]


class TestVoidLocksDocumentsP20:

    @pytest.mark.django_db
    def test_void_locks_the_affected_document_rows(self, two_invoice_payment_fixture):
        """BE-H1: void() must select_for_update() the affected document
        rows BEFORE deleting the allocations and recomputing — the
        unlocked recompute is the amount_paid/status divergence seam."""
        fx = two_invoice_payment_fixture
        real_sfu = InvoiceDocument.objects.select_for_update

        with patch.object(
            InvoiceDocument.objects,
            "select_for_update",
            wraps=real_sfu,
        ) as spy:
            PaymentService.void(
                org_id=fx["org"].id,
                payment_id=fx["payment"].id,
                reason="P20 lock probe",
                user_id=fx["user"].id,
            )
        assert spy.called, (
            "void() must select_for_update() the affected documents before "
            "recomputing amount_paid (BE-P20-H1: allocate()/unallocate() "
            "hold the document lock for the same recompute — void() is the "
            "odd one out; a concurrent allocate's committed allocation is "
            "silently lost)"
        )

    @pytest.mark.django_db
    def test_void_locks_documents_in_sorted_order(self, two_invoice_payment_fixture):
        """BE-P20-H1/M2: the document locks must be taken in sorted-id
        order — the deterministic pre-lock that closes the AB-BA class
        between two concurrent voids over shared documents. The probe
        records every locked .get(id=…) call (and id__in pre-locks);
        the recorded order must be sorted."""
        fx = two_invoice_payment_fixture
        real_sfu = InvoiceDocument.objects.select_for_update
        locked_ids: list = []

        def recording_sfu():
            qs = real_sfu()
            original_get = qs.get

            def recording_get(*args, **kwargs):
                if "id" in kwargs:
                    locked_ids.append(kwargs["id"])
                elif "id__in" in kwargs:
                    locked_ids.extend(sorted(kwargs["id__in"], key=str))
                return original_get(*args, **kwargs)

            qs.get = recording_get
            return qs

        with patch.object(
            InvoiceDocument.objects, "select_for_update", side_effect=recording_sfu
        ):
            PaymentService.void(
                org_id=fx["org"].id,
                payment_id=fx["payment"].id,
                reason="P20 order probe",
                user_id=fx["user"].id,
            )
        assert locked_ids, (
            "void() must take the affected-document locks (the spy test "
            "above pins presence; this one pins order)"
        )
        assert [str(i) for i in locked_ids] == [str(i) for i in sorted(locked_ids, key=str)], (
            "void() must lock the affected documents in sorted-id order "
            "(BE-P20-H1/M2 — the AB-BA class between two concurrent voids "
            "over shared documents)"
        )
        for inv in fx["invoices"]:
            inv.refresh_from_db()
            assert inv.amount_paid == Decimal("0.0000")

    @pytest.mark.django_db
    def test_concurrent_allocate_cannot_be_overwritten_by_void(
        self, two_invoice_payment_fixture
    ):
        """BE-H1, the interleaving (Case B — the allocator wins the lock):
        an allocation that commits before void's locked re-read must be
        seen by the recompute — the document's amount_paid keeps the
        committed allocation (PARTIALLY_PAID from the surviving payment),
        never a stale regression. The concurrent committer is simulated
        at the lock seam exactly like the P19/BE-H1 probe."""
        from apps.core.models import InvoiceDocument as Doc
        from apps.core.models import PaymentAllocation

        fx = two_invoice_payment_fixture
        doc = fx["invoices"][1]
        real_sfu = Doc.objects.select_for_update
        fired = {"done": False}

        def racing_sfu():
            # T2 commits exactly ONCE — before void's FIRST locked read (the
            # seam fires per document lock; only the first is T2's commit).
            if not fired["done"]:
                fired["done"] = True
                PaymentAllocation.objects.create(
                    org_id=fx["org"].id,
                    payment=_receive(
                        fx["org"], fx["user"], fx["bank"], fx["contact"], Decimal("50.00")
                    ),
                    document=doc,
                    allocated_amount=Decimal("50.00"),
                    base_allocated_amount=Decimal("50.00"),
                )
                # ...and the allocator's own amount_paid recompute:
                Doc.objects.filter(id=doc.id).update(amount_paid=Decimal("250.00"))
            return real_sfu()

        with patch.object(Doc.objects, "select_for_update", side_effect=racing_sfu):
            PaymentService.void(
                org_id=fx["org"].id,
                payment_id=fx["payment"].id,
                reason="P20 interleaving probe",
                user_id=fx["user"].id,
            )

        doc.refresh_from_db()
        # T1's void released ITS payment's 200.00; T2's committed 50.00
        # allocation must survive the recompute (the locked re-read sees
        # it). amount_paid = 50.00 — NOT the stale 0.00 the unlocked SUM
        # would have written.
        assert doc.amount_paid == Decimal("50.0000"), (
            "void()'s recompute must observe the concurrent committed "
            "allocation (BE-P20-H1 — the unlocked SUM wrote the stale "
            "pre-T2 value and silently lost the allocation)"
        )
        assert doc.status == "PARTIALLY_PAID"


class TestTransitionStatusLockP20:

    @pytest.mark.django_db
    def test_transition_status_locks_the_document(self, payment_fixture):
        """BE-H3: transition_status() must select_for_update() the row —
        the generic status endpoint is a live route and its plain read +
        full-row save is the exact TOCTOU P19/BE-H1 closed for
        remove_line()."""
        from apps.core.models import InvoiceDocument as Doc

        fx = payment_fixture
        real_sfu = Doc.objects.select_for_update
        with patch.object(Doc.objects, "select_for_update", wraps=real_sfu) as spy:
            DocumentService.transition_status(
                org_id=fx["org"].id,
                document_id=fx["invoice"].id,
                new_status="PARTIALLY_PAID",
                user_id=fx["user"].id,
            )
        assert spy.called, (
            "transition_status() must select_for_update() the document "
            "(BE-P20-H3: the stale full-row save overwrites a concurrent "
            "approve_document() commit — status regression on a posted "
            "money document)"
        )

    @pytest.mark.django_db
    def test_concurrent_approve_cannot_be_overwritten_by_transition(
        self, payment_fixture
    ):
        """BE-H3, the interleaving (Case B): the approval commits at the
        lock seam; the post-lock re-validation must refuse the stale
        DRAFT->SENT transition (APPROVED->SENT is not in the map) with the
        typed error — never write SENT over the APPROVED, journal-posted
        document."""
        from apps.core.models import InvoiceDocument as Doc

        fx = payment_fixture
        fx["invoice"].status = "DRAFT"
        fx["invoice"].save(update_fields=["status"])

        real_sfu = Doc.objects.select_for_update

        def racing_sfu():
            Doc.objects.filter(id=fx["invoice"].id).update(status="APPROVED")
            return real_sfu()

        with patch.object(Doc.objects, "select_for_update", side_effect=racing_sfu):
            with pytest.raises(ServiceValidationError):
                DocumentService.transition_status(
                    org_id=fx["org"].id,
                    document_id=fx["invoice"].id,
                    new_status="SENT",
                    user_id=fx["user"].id,
                )

        fx["invoice"].refresh_from_db()
        # NOTE (the P19 single-transaction simulation): the simulated
        # concurrent UPDATE is undone by the test's savepoint rollback —
        # in production T2's COMMIT survives T1's refusal. The contract
        # this pins: the stale DRAFT->SENT transition is REFUSED with the
        # typed error (pytest.raises above) and the stale write never
        # lands — the status is never SENT.
        assert fx["invoice"].status != "SENT", (
            "the stale SENT transition must be refused post-lock — the "
            "concurrent approval survives (BE-P20-H3)"
        )

    @pytest.mark.django_db
    def test_transition_status_does_not_clobber_totals(self, payment_fixture):
        """BE-H3 (the stale full-row save half): a concurrent add_line
        totals-update that commits at the lock seam must survive the
        status transition — save(update_fields=…) only, never the full
        row."""
        from apps.core.models import InvoiceDocument as Doc

        fx = payment_fixture
        new_totals = {
            "total_excl": Decimal("500.00"),
            "gst_total": Decimal("45.00"),
            "total_incl": Decimal("545.00"),
        }
        real_sfu = Doc.objects.select_for_update

        def racing_sfu():
            Doc.objects.filter(id=fx["invoice"].id).update(**new_totals)
            return real_sfu()

        with patch.object(Doc.objects, "select_for_update", side_effect=racing_sfu):
            DocumentService.transition_status(
                org_id=fx["org"].id,
                document_id=fx["invoice"].id,
                new_status="PARTIALLY_PAID",
                user_id=fx["user"].id,
            )

        fx["invoice"].refresh_from_db()
        assert fx["invoice"].total_incl == Decimal("545.00"), (
            "transition_status() must not clobber concurrently-committed "
            "totals with its stale full-row save (BE-P20-H3)"
        )


class TestAllocateSortedDocumentLockP20:

    @pytest.mark.django_db
    def test_allocate_locks_documents_in_sorted_order(self, payment_fixture):
        """BE-M1: the document locks must be acquired in sorted-id order
        (the create_entry() pattern, P19/BE-M2) — the user-supplied
        allocation order is a deadlock vector for two concurrent
        allocations over overlapping document sets."""
        from apps.core.models import InvoiceDocument as Doc

        fx = payment_fixture
        # A second invoice, allocated SECOND but with a SMALLER id — the
        # user order and the sorted order disagree.
        second = InvoiceDocument.objects.create(
            org=fx["org"],
            document_type="SALES_INVOICE",
            contact=fx["contact"],
            document_number=f"INV-P20B-{uuid4_hex()}",
            issue_date=date(2024, 1, 10),
            due_date=date(2024, 2, 10),
            status="APPROVED",
            total_excl=Decimal("100.00"),
            gst_total=Decimal("0.00"),
            total_incl=Decimal("100.00"),
            amount_paid=Decimal("0.0000"),
        )
        pair = sorted([fx["invoice"].id, second.id], key=str)
        if str(second.id) == str(pair[0]):
            # Ensure the user-supplied order is the REVERSE of sorted.
            ordered = [second, fx["invoice"]]
        else:
            ordered = [fx["invoice"], second]

        payment = _receive(
            fx["org"], fx["user"], fx["bank"], fx["contact"], Decimal("209.00")
        )
        locked_order: list = []
        real_sfu = Doc.objects.select_for_update

        def recording_sfu():
            qs = real_sfu()
            original_get = qs.get

            def recording_get(*args, **kwargs):
                if "id" in kwargs:
                    locked_order.append(kwargs["id"])
                return original_get(*args, **kwargs)

            qs.get = recording_get
            return qs

        with patch.object(Doc.objects, "select_for_update", side_effect=recording_sfu):
            PaymentService.allocate(
                org_id=fx["org"].id,
                payment_id=payment.id,
                allocations=[
                    {"document_id": str(d.id), "allocated_amount": Decimal("100.00")}
                    for d in ordered
                ],
            )

        assert [str(i) for i in locked_order] == [str(i) for i in sorted(locked_order, key=str)], (
            "allocate() must pre-lock the deduplicated document ids in "
            "sorted order before the per-document validation (BE-P20-M1 — "
            "the user-supplied order is the AB-BA deadlock vector)"
        )


class TestCreateEntryInvalidatesBalanceCacheP20:

    @pytest.mark.django_db
    def test_create_entry_invalidates_the_account_balance_cache(
        self, test_organisation, test_user, test_accounts, test_tax_codes,
        test_fiscal_period, django_capture_on_commit_callbacks,
    ):
        """BE-M5: create_entry() must delete the account_balance:{id}
        cache key for every account it touches — the 5-minute cache
        otherwise serves a pre-posting balance on the user-facing
        balance endpoint (the P19 fix patched the archive gate only).

        P21/BE-M3 update: the delete is registered on COMMIT (a delete
        inside the transaction re-seeds the stale value in the
        delete->commit window) — the probe executes the callbacks the
        way a real commit would."""
        from apps.coa.services import AccountService
        from apps.journal.services import JournalService

        org = test_organisation
        account = test_accounts["4000"]

        # Seed the cache with the pre-posting balance (0).
        pre = AccountService.get_account_balance(org.id, account.id)
        assert pre == Decimal("0.00")

        with django_capture_on_commit_callbacks(execute=True):
            JournalService.create_entry(
                org_id=org.id,
                entry_date=date(2024, 1, 15),
                source_type="MANUAL",
                narration="P20 cache-invalidation probe",
                lines=[
                    {"account_id": account.id, "debit": Decimal("100.00"), "credit": Decimal("0")},
                    {"account_id": test_accounts["1200"].id, "debit": Decimal("0"), "credit": Decimal("100.00")},
                ],
                user_id=test_user.id,
            )

        post = AccountService.get_account_balance(org.id, account.id)
        assert post == Decimal("100.00"), (
            "create_entry() must invalidate the account_balance cache for "
            "the touched accounts (BE-P20-M5 — the balance endpoint served "
            "the stale pre-posting 0 for up to 5 minutes)"
        )


class TestAllocatePositiveAmountGuardP20:

    @pytest.mark.django_db
    def test_allocate_refuses_non_positive_amounts_at_the_service_seam(
        self, payment_fixture
    ):
        """BE-L2: the service seam must gate allocated_amount > 0 (the DB
        CHECK turns zero/negative into an untyped IntegrityError for
        non-DRF callers; the serializers gate it, the seam must too)."""
        fx = payment_fixture
        payment = _receive(
            fx["org"], fx["user"], fx["bank"], fx["contact"], Decimal("109.00")
        )
        with pytest.raises(ServiceValidationError):
            PaymentService.allocate(
                org_id=fx["org"].id,
                payment_id=payment.id,
                allocations=[
                    {
                        "document_id": str(fx["invoice"].id),
                        "allocated_amount": Decimal("0.00"),
                    }
                ],
            )
        # Nothing was written.
        assert PaymentAllocation.objects.filter(payment=payment).count() == 0


class TestUnreconcilePaymentLockOrgFilterP20:

    @pytest.mark.django_db
    def test_unreconcile_payment_lock_carries_the_org_filter(
        self, test_organisation, test_user, test_accounts, test_fiscal_period
    ):
        """BE-L3: the payment lock in unreconcile() must filter by org_id
        like every sibling lock (defense-in-depth: a NULL-context read
        must not lock a cross-org payment row)."""
        from apps.core.models import DocumentSequence, Payment
        from tests.conftest import create_test_contact

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
            account_name="P20 Unrec Bank",
            bank_name="Test Bank",
            account_number="001-999-002",
            currency="SGD",
            paynow_type=None,
            is_active=True,
        )
        contact = create_test_contact(org, is_customer=True)
        payment = _receive(org, test_user, bank, contact, Decimal("10.00"))
        transaction = ReconciliationService.record_manual_transaction(
            org_id=org.id,
            bank_account_id=bank.id,
            transaction_date=date(2024, 1, 20),
            description="P20 unreconcile probe",
            amount=Decimal("10.00"),
            user_id=test_user.id,
        ) if hasattr(ReconciliationService, "record_manual_transaction") else None
        if transaction is None:
            from apps.core.models import BankTransaction

            transaction = BankTransaction.objects.create(
                org=org,
                bank_account=bank,
                transaction_date=date(2024, 1, 20),
                description="P20 unreconcile probe",
                amount=Decimal("10.00"),
                is_reconciled=True,
                matched_payment=payment,
                reconciled_at=date(2024, 1, 21),
            )

        captured: dict = {}
        real_sfu = Payment.objects.select_for_update

        class _LockedQS:
            def __init__(self, qs):
                self._qs = qs

            def get(self, *args, **kwargs):
                captured.update(kwargs)
                return self._qs.get(*args, **kwargs)

            def __getattr__(self, item):
                return getattr(self._qs, item)

        def capturing_sfu():
            return _LockedQS(real_sfu())

        with patch.object(Payment.objects, "select_for_update", side_effect=capturing_sfu):
            ReconciliationService.unreconcile(
                org_id=org.id,
                transaction_id=transaction.id,
                user_id=test_user.id,
            )
        assert "org_id" in captured, (
            "unreconcile()'s payment lock must carry the org_id filter "
            "(BE-P20-L3 — the only lock in the banking services without it)"
        )
