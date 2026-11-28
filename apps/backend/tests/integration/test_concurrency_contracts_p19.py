"""
P19 concurrency-contract gates — the remove_line truth gap + the
locking/transaction completion.

BE-H1: remove_line() was never locked despite the P18 commit claiming
    "add_line/remove_line lock the document" — a plain get_document()
    read + DRAFT gate + delete + totals-save can interleave with
    approve_document() (which holds the lock): the approve commits
    between remove_line's read and its save, and remove_line then
    overwrites the totals (and regresses the status) of an APPROVED,
    journal-posted document (READ COMMITTED — the P14/C-2 shape,
    reopened on the line seam). The fix mirrors add_line():
    transaction.atomic() + select_for_update() + post-lock re-check.
BE-M1: archive_account()'s zero-balance gate reads through the 5-minute
    account_balance cache which journal postings never invalidate — a
    cached zero lets an account with live journal lines archive (the
    lines then vanish from the trial balance). The gate must bypass the
    cache.
BE-M2: create_entry()'s account read is a plain SELECT — it does not
    conflict with archive_account()'s row lock, so lines can land on an
    account archived a moment earlier (the P18 comment's "the pair is
    closed" claim is illusory). The read must lock.
BE-M3: unallocate() locks the allocation row BEFORE the payment row
    while void()/allocate() hold the payment lock and then write
    allocation rows — an AB-BA inversion (PG 40P01 → untyped 500). The
    lock order must be payment → allocation → document.
BE-M4: create_return_periods()' IntegrityError catch poisons the
    ATOMIC_REQUESTS transaction (no savepoint) — the next loop query
    raises TransactionManagementError (500), the exact untyped-500 the
    P18/BE-L4 fix claimed to prevent. The create must run in its own
    savepoint.
BE-M5: check_transmission_status_task() closes tenant_context() after
    the log lookup — the adapter lookup and the log.save() run outside
    the context (RLS write silently fails on a real worker). The whole
    body must run inside the context.

BE-L1 (the audit's NULL-transmitted_at cleanup finding) was INVALIDATED
    during the P19 RED verification: gst.peppol_transmission_log.
    transmitted_at is NOT NULL DEFAULT NOW() in the schema and
    auto_now_add on the model — a PENDING row with NULL transmitted_at
    cannot exist, so the cleanup filter is not missing any rows. The
    audit's assumption is recorded here so the finding is not re-raised.
"""

from datetime import date
from decimal import Decimal
from unittest.mock import patch
from uuid import uuid4

import pytest

from apps.core.models import GSTReturn, InvoiceLine
from apps.gst.services import GSTReturnService
from apps.invoicing.services import DocumentService
from common.exceptions import ValidationError as ServiceValidationError
from tests.integration.test_payment_allocation_contract_p14 import _receive


@pytest.fixture
def draft_invoice_with_line(
    test_organisation, test_user, test_accounts, test_tax_codes
):
    from tests.conftest import create_test_contact, create_test_invoice

    contact = create_test_contact(test_organisation, is_customer=True)
    invoice = create_test_invoice(test_organisation, contact, status="DRAFT")
    line = DocumentService.add_line(
        org_id=test_organisation.id,
        document_id=invoice.id,
        account_id=test_accounts["4000"].id,
        description="P19 remove-line probe",
        quantity=Decimal("1"),
        unit_price=Decimal("100.00"),
        tax_code_id=test_tax_codes["SR"].id,
    )
    return invoice, line


class TestRemoveLineLocksDocumentP19:

    @pytest.mark.django_db
    def test_remove_line_locks_the_document_row(
        self, test_organisation, test_user, draft_invoice_with_line
    ):
        """BE-H1: remove_line() must select_for_update() the document
        row (the seed-wrapper probe — the same pattern add_line() got
        in P18; the commit claimed both, only add_line landed)."""
        from apps.core.models import InvoiceDocument as Doc

        invoice, line = draft_invoice_with_line
        with patch.object(
            Doc.objects, "select_for_update", wraps=Doc.objects.select_for_update
        ) as spy:
            DocumentService.remove_line(
                org_id=test_organisation.id,
                document_id=invoice.id,
                line_id=line.id,
            )
            assert spy.called, (
                "remove_line() must select_for_update() the InvoiceDocument "
                "row (BE-H1/P19: the P18 commit 51bd46c6 claims "
                "'add_line/remove_line lock the document' — only add_line "
                "got the lock; the DRAFT gate here is a TOCTOU against "
                "approve_document())"
            )

    @pytest.mark.django_db
    def test_concurrent_approve_cannot_be_overwritten_by_remove_line(
        self, test_organisation, test_user, draft_invoice_with_line
    ):
        """BE-H1, the interleaving (Case B — the approver wins the lock):
        an approval that commits before remove_line's locked read must
        be seen by the post-lock status re-check — the removal refused
        with the typed validation error, the APPROVED document's lines
        and totals intact.

        The concurrent committer is simulated at the lock seam: the
        approval lands (a queryset UPDATE, exactly what a committed
        approve_document() leaves behind) the moment remove_line tries
        to take the row lock — the locked read then observes the
        post-approval state (READ COMMITTED's fresh snapshot). Pre-fix,
        remove_line never takes the lock: the committer never fires,
        the removal proceeds unrefused — the assertion sees the silent
        overwrite instead."""
        from apps.core.models import InvoiceDocument as Doc

        invoice, line = draft_invoice_with_line
        invoice.refresh_from_db()
        totals_before = (invoice.total_excl, invoice.gst_total, invoice.total_incl)
        real_sfu = Doc.objects.select_for_update

        def racing_sfu():
            # The concurrent approval commits here — before remove_line's
            # locked read observes the row.
            Doc.objects.filter(id=invoice.id).update(status="APPROVED")
            return real_sfu()

        with (
            patch.object(Doc.objects, "select_for_update", side_effect=racing_sfu),
            pytest.raises(ServiceValidationError, match="(?i)draft"),
        ):
            DocumentService.remove_line(
                    org_id=test_organisation.id,
                    document_id=invoice.id,
                    line_id=line.id,
                )

        invoice.refresh_from_db()
        # NOTE: the simulated concurrent update is undone by the savepoint
        # rollback of the refused remove (single-transaction simulation —
        # in production T2's COMMIT survives T1's rollback; the locked
        # re-read that refuses here is exactly what guarantees it, pinned
        # by the spy test above). The contract this test pins: the removal
        # is refused with the typed error, the line and the totals survive.
        assert InvoiceLine.objects.filter(id=line.id).exists(), (
            "remove_line() must not delete a line from an APPROVED document "
            "(BE-H1/P19)"
        )
        assert (invoice.total_excl, invoice.gst_total, invoice.total_incl) == totals_before, (
            "remove_line() must not overwrite the totals of an APPROVED, "
            "journal-posted document (BE-H1/P19 — document/ledger divergence)"
        )


class TestRemoveLineFieldBugP19:
    @pytest.mark.django_db
    def test_remove_line_uses_the_real_fk_field(self, draft_invoice_with_line):
        """Discovered during the P19 RED run: remove_line() filters
        InvoiceLine by `invoice=` — the model's FK is `document` — so
        every call raises FieldError (untyped 500). The method is not
        just unlocked, it is broken end-to-end (no existing test ever
        exercised it)."""

        # A plain DRAFT document: the happy path must simply work.
        invoice, line = draft_invoice_with_line
        DocumentService.remove_line(
            org_id=invoice.org_id,
            document_id=invoice.id,
            line_id=line.id,
        )
        assert not InvoiceLine.objects.filter(id=line.id).exists()
        invoice.refresh_from_db()
        assert invoice.total_excl == Decimal("0.00")


class TestUnallocateLockOrderP19:
    @pytest.mark.django_db
    def test_unallocate_locks_payment_before_allocation(self, payment_fixture):
        """BE-M3: the payment row lock must be acquired BEFORE the
        allocation row lock — unallocate currently locks allocation→
        payment while void()/allocate() hold payment and then write
        allocation rows (an AB-BA inversion → PG 40P01 deadlock →
        untyped 500 for one request)."""
        from apps.banking.services import PaymentService
        from apps.core.models import Payment, PaymentAllocation

        fx = payment_fixture
        payment = _receive(
            fx["org"], fx["user"], fx["bank"], fx["contact"], Decimal("109.00")
        )
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
        allocation = PaymentAllocation.objects.filter(payment=payment).first()

        order = []
        real_payment_sfu = Payment.objects.select_for_update
        real_allocation_sfu = PaymentAllocation.objects.select_for_update

        def payment_sfu():
            order.append("payment")
            return real_payment_sfu()

        def allocation_sfu():
            order.append("allocation")
            return real_allocation_sfu()

        with (
            patch.object(Payment.objects, "select_for_update", side_effect=payment_sfu),
            patch.object(
                PaymentAllocation.objects, "select_for_update", side_effect=allocation_sfu
            ),
        ):
            PaymentService.unallocate(
                org_id=fx["org"].id, allocation_id=allocation.id, user_id=fx["user"].id
            )

        assert "payment" in order and "allocation" in order, (
            f"unallocate() must lock both rows (saw {order})"
        )
        assert order.index("payment") < order.index("allocation"), (
            "unallocate() must take the payment lock BEFORE the allocation lock "
            "(BE-M3/P19: allocation→payment vs void/allocate's payment→allocation-rows "
            "is the AB-BA deadlock inversion — PG resolves it with 40P01 and an "
            "untyped 500 for one request)"
        )


class TestArchiveAccountCacheGateP19:
    @pytest.mark.django_db
    def test_archive_gate_ignores_the_stale_balance_cache(
        self, test_organisation, test_user, test_accounts, test_fiscal_period
    ):
        """BE-M1: the archive gate must not read the 5-minute
        account_balance cache — a cached zero (seeded by a balance GET)
        lets an account with live journal lines archive, and the lines
        then silently vanish from the trial balance
        (get_trial_balance filters is_active=True)."""
        from django.core.cache import cache

        from apps.coa.services import AccountService
        from apps.core.models import Account
        from apps.journal.services import JournalService

        # A custom (non-system) account — system accounts are refused
        # before the balance gate.
        account = Account.objects.create(
            org=test_organisation,
            code="4900",
            name="P19 Cache Gate Probe",
            account_type="REVENUE",
            is_system=False,
            is_active=True,
        )
        # Seed the cache with the zero balance (a balance GET does this).
        AccountService.get_account_balance(test_organisation.id, account.id)
        assert cache.get(f"account_balance:{account.id}") is not None, (
            "test setup: the cache must be seeded for the gate probe"
        )

        # Post a journal line to the account (balance becomes non-zero).
        JournalService.create_entry(
            org_id=test_organisation.id,
            entry_date=date(2024, 1, 10),
            source_type="MANUAL",
            narration="P19-M1 cache-gate probe",
            lines=[
                {
                    "account_id": str(account.id),
                    "debit": Decimal("10.0000"),
                    "credit": Decimal("0"),
                    "description": "cache-gate probe debit",
                },
                {
                    "account_id": str(test_accounts["1200"].id),
                    "debit": Decimal("0"),
                    "credit": Decimal("10.0000"),
                    "description": "cache-gate probe credit",
                },
            ],
            user_id=test_user.id,
        )

        # The archive gate must see the live (non-zero) balance, not the
        # stale cached zero.
        with pytest.raises(ServiceValidationError, match="(?i)non-zero|balance"):
            AccountService.archive_account(
                org_id=test_organisation.id, account_id=account.id
            )
        account.refresh_from_db()
        assert account.is_active, (
            "an account with live journal lines must not archive on a stale "
            "cached zero (BE-M1/P19 — the lines would vanish from the trial "
            "balance while remaining in the ledger)"
        )


class TestCreateEntryLocksAccountP19:
    @pytest.mark.django_db
    def test_create_entry_locks_the_account_rows(
        self, test_organisation, test_user, test_accounts, test_fiscal_period
    ):
        """BE-M2: create_entry()'s account read must take the row lock
        (it already runs inside the entry's atomic) — a plain SELECT
        does not conflict with archive_account()'s lock, so lines can
        land on an account archived a moment earlier."""
        from apps.core.models import Account
        from apps.journal.services import JournalService

        with patch.object(
            Account.objects, "select_for_update", wraps=Account.objects.select_for_update
        ) as spy:
            JournalService.create_entry(
                org_id=test_organisation.id,
                entry_date=date(2024, 1, 10),
                source_type="MANUAL",
                narration="P19-M2 account-lock probe",
                lines=[
                    {
                        "account_id": str(test_accounts["4000"].id),
                        "debit": Decimal("5.0000"),
                        "credit": Decimal("0"),
                        "description": "probe debit",
                    },
                    {
                        "account_id": str(test_accounts["1200"].id),
                        "debit": Decimal("0"),
                        "credit": Decimal("5.0000"),
                        "description": "probe credit",
                    },
                ],
                user_id=test_user.id,
            )
            assert spy.called, (
                "create_entry() must select_for_update() the account rows "
                "(BE-M2/P19: a plain SELECT doesn't conflict with "
                "archive_account()'s row lock — the P18 'the pair is closed' "
                "comment is illusory without this lock)"
            )


class TestReturnPeriodsSavepointP19:
    @pytest.mark.django_db
    def test_integrityerror_branch_does_not_poison_the_transaction(
        self, test_organisation, test_user
    ):
        """BE-M4: the IntegrityError catch must run inside its own
        savepoint — without it the aborted request transaction makes
        the NEXT loop query raise TransactionManagementError (the
        untyped 500 the P18/BE-L4 fix claimed to prevent). The race is
        forced by stubbing .exists() to miss the pre-created winner."""
        from django.db.models import query

        # The concurrent winner: a period the .exists() pre-check will
        # miss (the race window), so the INSERT hits the UNIQUE.
        GSTReturn.objects.create(
            org_id=test_organisation.id,
            period_start=date(2026, 1, 1),
            period_end=date(2026, 1, 31),
            filing_due_date=date(2026, 2, 28),
            status="DRAFT",
        )

        with patch.object(query.QuerySet, "exists", return_value=False):
            # Must complete cleanly: the conflicting create is caught in
            # a savepoint, the loop's next query is unaffected.
            created = GSTReturnService.create_return_periods(
                org_id=test_organisation.id,
                filing_frequency="MONTHLY",
                start_date=date(2026, 1, 1),
                periods=3,
            )

        assert isinstance(created, list), (
            "create_return_periods() must return its list even when the "
            "IntegrityError branch fires (BE-M4/P19 — without the savepoint "
            "the next loop query raises TransactionManagementError)"
        )
        # The conflict itself is skipped (not duplicated), the other
        # periods were created.
        assert len(created) == 2, (
            f"expected the 2 non-conflicting periods, got {len(created)}"
        )


class TestCheckStatusTaskFullContextP19:
    @pytest.mark.django_db
    def test_status_task_saves_inside_tenant_context(
        self, test_organisation, test_fiscal_period
    ):
        """BE-M5: the log.save() (the RLS write) and the adapter lookup
        must run INSIDE tenant_context() — the context currently closes
        after the log lookup, so on a real worker the UPDATE matches 0
        rows under RLS and the delivery-status write never lands. The
        probe wraps tenant_context() with an enter/exit tracker and
        records whether save() fires while the context is open (the
        savepoint_state counter is monotonic, not a depth gauge — the
        first probe design passed vacuously)."""
        from contextlib import contextmanager

        from apps.peppol.models import PeppolTransmissionLog
        from apps.peppol.tasks import check_transmission_status_task
        from common import tenant_context as tc_module
        from tests.conftest import create_test_contact, create_test_invoice

        org = test_organisation
        contact = create_test_contact(org, is_customer=True)
        invoice = create_test_invoice(org, contact, status="APPROVED")
        message_id = uuid4()
        log = PeppolTransmissionLog.objects.create(
            org=org,
            document_id=invoice.id,
            status="TRANSMITTING",
            peppol_message_id=message_id,
        )

        context_depth = {"level": 0}
        save_inside = {}
        original_save = PeppolTransmissionLog.save
        real_tc = tc_module.tenant_context

        @contextmanager
        def tracking_tc(org_id, user_id=None):
            context_depth["level"] += 1
            try:
                with real_tc(org_id, user_id):
                    yield
            finally:
                context_depth["level"] -= 1

        def probing_save(self, *args, **kwargs):
            save_inside["level"] = context_depth["level"]
            return original_save(self, *args, **kwargs)

        class _ProbeAdapter:
            def check_status(self, message_id):
                return type(
                    "R",
                    (),
                    {"success": True, "status": type("S", (), {"value": "DELIVERED"})()},
                )()

        def _probe_adapter_factory(*args, **kwargs):
            return _ProbeAdapter()

        from apps.peppol.services.transmission_service import TransmissionService

        with patch.object(
            PeppolTransmissionLog, "save", probing_save
        ), patch.object(
            TransmissionService, "get_adapter_for_org", _probe_adapter_factory
        ), patch.object(
            tc_module, "tenant_context", tracking_tc
        ):
            check_transmission_status_task.apply(
                args=[str(message_id), str(org.id)]
            ).get()

        assert save_inside.get("level", -1) > 0, (
            "check_transmission_status_task must perform log.save() inside "
            "tenant_context() (BE-M5/P19 — the write is RLS-scoped; outside "
            "the context a real worker's UPDATE matches 0 rows and the "
            f"delivery-status write silently never lands; save fired at "
            f"context level {save_inside.get('level')!r})"
        )
        log.refresh_from_db()
        assert log.status == "DELIVERED"
