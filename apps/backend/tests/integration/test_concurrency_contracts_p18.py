"""
P18 concurrency-contract gates — statutory-record locking.

BE-H1: generate_f5()/review_return() are unlocked TOCTOUs against the
    locked file_return()/amend_return() — the plain get_return() read +
    status gate + unconditional save() can interleave with a filing
    (READ COMMITTED): generate_f5 reads COMPUTED, file_return commits
    FILED, generate_f5.save() then regresses the statutory record to
    COMPUTED while filed_at stays populated (the P14/C-2 regression
    shape, reopened through a race). The fix mirrors file_return():
    transaction.atomic() + select_for_update() + post-lock re-check.
BE-M2: unallocate()/unreconcile() take no locks — lost-update races
    against the locked allocate()/void()/reconcile() on
    document.amount_paid/status and the reconcile flags.
"""

from datetime import date
from decimal import Decimal

import pytest

from apps.core.models import GSTReturn, InvoiceDocument
from apps.gst.services import GSTReturnService
from common.exceptions import ValidationError as ServiceValidationError


@pytest.fixture
def computed_return(test_organisation):
    ret = GSTReturn.objects.create(
        org_id=test_organisation.id,
        period_start=date(2024, 1, 1),
        period_end=date(2024, 1, 31),
        filing_due_date=date(2024, 2, 29),
        status="COMPUTED",
        box1_std_rated_supplies=Decimal("1000.00"),
        box4_total_supplies=Decimal("1000.00"),
        box6_output_tax=Decimal("90.00"),
        box7_input_tax_claimable=Decimal("0"),
        box8_net_gst=Decimal("90.00"),
        box13_total_revenue=Decimal("1000.00"),
    )
    return ret


class TestGenerateF5LocksReturnRowP18:
    @pytest.mark.django_db
    def test_generate_f5_locks_the_return_row(self, test_organisation, computed_return):
        """BE-H1: the return row must be read under select_for_update()
        inside generate_f5()'s atomic block — the seed-wrapper probe
        pattern (P17/BE-H2 precedent). Without the lock, a concurrent
        file_return() commit lands between the status gate and the save."""
        from unittest.mock import patch

        with patch.object(
            GSTReturn.objects, "select_for_update", wraps=GSTReturn.objects.select_for_update
        ) as spy:
            GSTReturnService.generate_f5(
                org_id=test_organisation.id, return_id=computed_return.id
            )
            assert spy.called, (
                "generate_f5() must select_for_update() the GSTReturn row "
                "(BE-H1: the status gate is otherwise a TOCTOU — a concurrent "
                "filing commits FILED between the check and the save, and the "
                "recompute then regresses the statutory record)"
            )

    @pytest.mark.django_db
    def test_generate_f5_after_filing_refused_and_filed_intact(
        self, test_organisation, test_user, computed_return
    ):
        """The sequential contract + the statutory record stays intact:
        file the return, then a recalculate attempt must 400 and leave
        every filed box value + filed_at + status untouched."""
        GSTReturnService.file_return(
            org_id=test_organisation.id,
            return_id=computed_return.id,
            filed_by_id=test_user.id,
            filing_reference="IRAS-P18-1",
        )
        filed = GSTReturn.objects.get(id=computed_return.id)
        assert filed.status == "FILED"
        filed_boxes = {
            "box1_std_rated_supplies": filed.box1_std_rated_supplies,
            "box6_output_tax": filed.box6_output_tax,
            "box8_net_gst": filed.box8_net_gst,
        }
        filed_at = filed.filed_at

        with pytest.raises(ServiceValidationError, match="(?i)immutable|statutory"):
            GSTReturnService.generate_f5(
                org_id=test_organisation.id, return_id=computed_return.id
            )

        after = GSTReturn.objects.get(id=computed_return.id)
        assert after.status == "FILED"
        assert after.filed_at == filed_at
        for box, value in filed_boxes.items():
            assert getattr(after, box) == value, f"{box} must not be recomputed post-filing"


class TestReviewReturnLocksReturnRowP18:
    @pytest.mark.django_db
    def test_review_return_locks_the_return_row(self, test_organisation, test_user, computed_return):
        """BE-H1: review_return() must take the same row lock — its
        COMPUTED->REVIEWED save can interleave with file_return() the
        same way (the gate reads, the filing commits, the save lands)."""
        from unittest.mock import patch

        with patch.object(
            GSTReturn.objects, "select_for_update", wraps=GSTReturn.objects.select_for_update
        ) as spy:
            GSTReturnService.review_return(
                org_id=test_organisation.id,
                return_id=computed_return.id,
                reviewed_by_id=test_user.id,
            )
            assert spy.called, (
                "review_return() must select_for_update() the GSTReturn row "
                "(BE-H1: same TOCTOU shape as generate_f5 — the save can "
                "land after a concurrent filing commits)"
            )

    @pytest.mark.django_db
    def test_review_after_filing_refused(
        self, test_organisation, test_user, computed_return
    ):
        """A filing that lands between the read and the review save must
        be caught by the post-lock re-check: review-after-file is refused
        with the statutory-record error, not a silent REVIEWED overwrite."""
        GSTReturnService.file_return(
            org_id=test_organisation.id,
            return_id=computed_return.id,
            filed_by_id=test_user.id,
            filing_reference="IRAS-P18-2",
        )
        with pytest.raises(ServiceValidationError):
            GSTReturnService.review_return(
                org_id=test_organisation.id,
                return_id=computed_return.id,
                reviewed_by_id=test_user.id,
            )
        assert GSTReturn.objects.get(id=computed_return.id).status == "FILED"


class TestUnallocateLocksRowsP18:
    @pytest.mark.django_db
    def test_unallocate_locks_payment_and_document(self, payment_fixture):
        """BE-M2: unallocate() must take the same locks allocate() takes
        (payment, then document) — otherwise a locked allocate() and an
        unlocked unallocate() interleave their allocation-set reads and
        amount_paid/status are computed from stale sets (the P5/H-1
        invariant 'the allocations table is the truth' breaks)."""
        from unittest.mock import patch

        from apps.banking.services import PaymentService
        from apps.core.models import InvoiceDocument, Payment
        from tests.integration.test_payment_allocation_contract_p14 import _receive

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
        from apps.core.models import PaymentAllocation

        allocation = PaymentAllocation.objects.filter(payment=payment).first()

        with (
            patch.object(
                Payment.objects, "select_for_update", wraps=Payment.objects.select_for_update
            ) as payment_spy,
            patch.object(
                InvoiceDocument.objects,
                "select_for_update",
                wraps=InvoiceDocument.objects.select_for_update,
            ) as document_spy,
        ):
            PaymentService.unallocate(
                org_id=fx["org"].id, allocation_id=allocation.id, user_id=fx["user"].id
            )
            assert payment_spy.called, (
                "unallocate() must select_for_update() the Payment row "
                "(BE-M2: serializes against allocate()/void() — the lock "
                "order payment-then-document matches allocate())"
            )
            assert document_spy.called, (
                "unallocate() must select_for_update() the Document row "
                "(BE-M2: the amount_paid/status recompute must read the "
                "locked allocation set)"
            )

        fx["invoice"].refresh_from_db()
        assert fx["invoice"].amount_paid == Decimal("0.0000")
        assert fx["invoice"].status in ("APPROVED", "SENT")


class TestUnreconcileLocksRowsP18:
    @pytest.mark.django_db
    def test_unreconcile_locks_transaction_and_payment(self, payment_fixture):
        """BE-M2: unreconcile() must lock the transaction (then the
        matched payment) — the same order reconcile() takes — else a
        concurrent reconcile() can re-set is_reconciled=True between
        unreconcile's read and its bulk payment update, leaving the
        txn/payment flags contradictory."""
        from unittest.mock import patch

        from apps.banking.services import ReconciliationService
        from apps.core.models import BankTransaction, Payment
        from tests.integration.test_payment_allocation_contract_p14 import _receive

        fx = payment_fixture
        payment = _receive(
            fx["org"], fx["user"], fx["bank"], fx["contact"], Decimal("109.00")
        )
        txn = BankTransaction.objects.create(
            org=fx["org"],
            bank_account=fx["bank"],
            transaction_date=date(2024, 1, 21),
            description="INCOMING 109.00",
            reference="TX-P18",
            amount=Decimal("109.0000"),
            running_balance=Decimal("109.0000"),
            import_source="CSV",
        )
        ReconciliationService.reconcile(
            org_id=fx["org"].id,
            transaction_id=txn.id,
            payment_id=payment.id,
            user_id=fx["user"].id,
        )

        with (
            patch.object(
                BankTransaction.objects,
                "select_for_update",
                wraps=BankTransaction.objects.select_for_update,
            ) as txn_spy,
            patch.object(
                Payment.objects, "select_for_update", wraps=Payment.objects.select_for_update
            ) as payment_spy,
        ):
            ReconciliationService.unreconcile(
                org_id=fx["org"].id, transaction_id=txn.id, user_id=fx["user"].id
            )
            assert txn_spy.called, (
                "unreconcile() must select_for_update() the BankTransaction "
                "row (BE-M2: serializes against reconcile()'s txn lock)"
            )
            assert payment_spy.called, (
                "unreconcile() must select_for_update() the matched Payment "
                "row (BE-M2: the bulk is_reconciled update must be serialized "
                "against reconcile()'s payment lock)"
            )

        txn.refresh_from_db()
        payment.refresh_from_db()
        assert txn.is_reconciled is False
        assert payment.is_reconciled is False


class TestConvertQuoteLocksRowP18:
    """BE-M4: convert_quote_to_invoice()'s status gate runs before and
    outside any lock — two concurrent converts both pass the DRAFT/SENT
    gate and create two invoices (double journal postings once both are
    approved). The fix: select_for_update the quote inside the atomic
    block, re-check the status post-lock."""

    def _org_with_sequences(self, org):
        from apps.core.models import DocumentSequence

        for doc_type, prefix in [("SALES_QUOTE", "QT-"), ("SALES_INVOICE", "INV-")]:
            DocumentSequence.objects.get_or_create(
                org=org, document_type=doc_type, defaults={"prefix": prefix, "next_number": 1}
            )

    def _quote_with_line(self, org, test_accounts, test_tax_codes):
        from apps.core.models import Contact, InvoiceLine

        contact = Contact.objects.create(
            org=org,
            contact_type="CUSTOMER",
            name="P18 Convert Customer",
            email="p18-convert@example.com",
            is_customer=True,
            is_active=True,
            payment_terms_days=30,
        )
        quote = InvoiceDocument.objects.create(
            org=org,
            document_type="SALES_QUOTE",
            document_number="QT-P18-1",
            contact=contact,
            issue_date=date(2024, 1, 15),
            due_date=date(2024, 2, 15),
            currency="SGD",
            exchange_rate=Decimal("1.000000"),
            total_excl=Decimal("100.0000"),
            total_incl=Decimal("109.0000"),
            amount_paid=Decimal("0.0000"),
            status="DRAFT",
        )
        InvoiceLine.objects.create(
            org=org,
            document=quote,
            line_number=1,
            account=test_accounts["4000"] if isinstance(test_accounts, dict) else test_accounts,
            description="Consulting",
            quantity=Decimal("1.0000"),
            unit_price=Decimal("100.0000"),
            tax_code=test_tax_codes["SR"],
            tax_rate=Decimal("0.0900"),
            line_amount=Decimal("100.0000"),
            gst_amount=Decimal("9.0000"),
            total_amount=Decimal("109.0000"),
            base_line_amount=Decimal("100.0000"),
            base_gst_amount=Decimal("9.0000"),
            base_total_amount=Decimal("109.0000"),
        )
        return quote

    @pytest.mark.django_db
    def test_convert_locks_the_quote_row(self, test_organisation, test_user, test_accounts, test_tax_codes):
        """The lock probe: the quote row must be read under
        select_for_update() inside the convert transaction."""
        from unittest.mock import patch

        from apps.invoicing.services import DocumentService

        self._org_with_sequences(test_organisation)
        quote = self._quote_with_line(test_organisation, test_accounts, test_tax_codes)

        with patch.object(
            InvoiceDocument.objects,
            "select_for_update",
            wraps=InvoiceDocument.objects.select_for_update,
        ) as spy:
            DocumentService.convert_quote_to_invoice(
                test_organisation.id, quote.id, user_id=test_user.id
            )
            assert spy.called, (
                "convert_quote_to_invoice() must select_for_update() the "
                "quote row (BE-M4: the DRAFT/SENT gate is otherwise a "
                "TOCTOU — two concurrent converts create two invoices)"
            )

    @pytest.mark.django_db
    def test_second_convert_refused(self, test_organisation, test_user, test_accounts, test_tax_codes):
        """Sequential pin: after a successful conversion the quote is
        APPROVED — a second conversion must be refused."""
        from apps.invoicing.services import DocumentService

        self._org_with_sequences(test_organisation)
        quote = self._quote_with_line(test_organisation, test_accounts, test_tax_codes)

        DocumentService.convert_quote_to_invoice(
            test_organisation.id, quote.id, user_id=test_user.id
        )
        with pytest.raises(ServiceValidationError, match="(?i)cannot convert"):
            DocumentService.convert_quote_to_invoice(
                test_organisation.id, quote.id, user_id=test_user.id
            )


class TestAddLineLocksDocumentP18:
    """BE-M5: add_line()'s read-then-write line numbering
    (order_by('-line_number').first() then create) races under
    uq_docline_doc_lineno — two concurrent adds on the same DRAFT compute
    the same line_number and the loser 500s on the IntegrityError. The
    fix: lock the document row for the numbering read+insert, and surface
    any residual IntegrityError as a typed 400."""

    @pytest.mark.django_db
    def test_add_line_locks_the_document_row(
        self, payment_fixture, test_accounts, test_tax_codes
    ):
        from unittest.mock import patch

        from apps.invoicing.services import DocumentService

        fx = payment_fixture
        # The fixture invoice is APPROVED; add_line only accepts DRAFT.
        fx["invoice"].status = "DRAFT"
        fx["invoice"].save(update_fields=["status"])

        with patch.object(
            InvoiceDocument.objects,
            "select_for_update",
            wraps=InvoiceDocument.objects.select_for_update,
        ) as spy:
            DocumentService.add_line(
                org_id=fx["org"].id,
                document_id=fx["invoice"].id,
                account_id=fx["accounts"]["4000"].id,
                description="P18 line",
                quantity=Decimal("1"),
                unit_price=Decimal("10.00"),
                tax_code_id=test_tax_codes["SR"].id,
            )
            assert spy.called, (
                "add_line() must select_for_update() the document row "
                "(BE-M5: the line-number read-then-write races the "
                "uq_docline_doc_lineno constraint — the loser 500s)"
            )

    @pytest.mark.django_db
    def test_add_line_integrity_error_is_typed_400(
        self, payment_fixture, test_accounts, test_tax_codes
    ):
        """The residual constraint violation (any interleaving that still
        slips through) must surface as a typed ValidationError, never an
        untyped IntegrityError 500."""
        from unittest.mock import patch

        from django.db.utils import IntegrityError

        from apps.invoicing.services import DocumentService

        fx = payment_fixture
        fx["invoice"].status = "DRAFT"
        fx["invoice"].save(update_fields=["status"])

        with patch(
            "apps.invoicing.services.document_service.InvoiceLine.objects.create",
            side_effect=IntegrityError(
                'duplicate key value violates unique constraint "uq_docline_doc_lineno"'
            ),
        ), pytest.raises(ServiceValidationError, match="(?i)line|concurrent"):
            DocumentService.add_line(
                org_id=fx["org"].id,
                document_id=fx["invoice"].id,
                account_id=fx["accounts"]["4000"].id,
                description="P18 race line",
                quantity=Decimal("1"),
                unit_price=Decimal("10.00"),
                tax_code_id=test_tax_codes["SR"].id,
            )


class TestCreditNoteCapLocksOriginalP18:
    """BE-M6: the cumulative credit-note cap check reads the original
    document + existing credits with no lock — two concurrent credit
    notes each see the same headroom and jointly exceed the original
    total (P14/H-4's cap defeated by racing). The fix: lock the original
    document row inside the create transaction."""

    @pytest.mark.django_db
    def test_cap_check_locks_the_original_row(self, payment_fixture):
        from unittest.mock import patch

        from apps.invoicing.services import DocumentService

        fx = payment_fixture
        original = fx["invoice"]

        with patch.object(
            InvoiceDocument.objects,
            "select_for_update",
            wraps=InvoiceDocument.objects.select_for_update,
        ) as spy:
            DocumentService._validate_credit_note_reference(
                org_id=fx["org"].id,
                document_type="SALES_CREDIT_NOTE",
                contact_id=original.contact_id,
                lines=[
                    {
                        "quantity": Decimal("1"),
                        "unit_price": Decimal("10.00"),
                        "tax_rate": Decimal("0.09"),
                    }
                ],
                related_document_id=original.id,
            )
            assert spy.called, (
                "_validate_credit_note_reference() must select_for_update() "
                "the ORIGINAL document row (BE-M6: the cumulative cap read "
                "is otherwise a TOCTOU — racing credit notes jointly exceed "
                "the cap)"
            )


class TestJournalPostingAccountGateP18:
    """BE-M3: manual journal lines could post to HEADER and ARCHIVED
    accounts — the ledger then diverges from the trial balance (the TB
    filters is_active=True, so lines on archived accounts vanish while
    remaining in the ledger). The schema documents the intent
    ("is_header ... cannot post to directly"); the service now enforces
    it with typed 400s."""

    def _entry_payload(self, org, account):
        return {
            "entry_date": date(2024, 1, 31),
            "description": "P18 account gate",
            "reference": "P18-AG",
            "lines": [
                {"account_id": str(account.id), "debit": Decimal("10.00"), "credit": Decimal("0")},
                {
                    "account_id": None,  # filled by the caller
                    "debit": Decimal("0"),
                    "credit": Decimal("10.00"),
                },
            ],
        }

    @pytest.mark.django_db
    def test_posting_to_a_header_account_is_refused(
        self, test_organisation, test_user, test_accounts, test_fiscal_period
    ):
        from apps.core.models import Account
        from apps.journal.services import JournalService

        header = Account.objects.create(
            org=test_organisation,
            code="1000",
            name="Assets (header)",
            account_type="ASSET",
            is_header=True,
            is_active=True,
        )
        payload = self._entry_payload(test_organisation, header)
        payload["lines"][1]["account_id"] = str(test_accounts["1200"].id)

        with pytest.raises(ServiceValidationError, match="(?i)header"):
            JournalService.create_entry(
                org_id=test_organisation.id,
                entry_date=payload["entry_date"],
                source_type="MANUAL",
                narration=payload["description"],
                lines=payload["lines"],
                user_id=test_user.id,
            )

    @pytest.mark.django_db
    def test_posting_to_an_archived_account_is_refused(
        self, test_organisation, test_user, test_accounts, test_fiscal_period
    ):
        from apps.core.models import Account
        from apps.journal.services import JournalService

        archived = Account.objects.create(
            org=test_organisation,
            code="1999",
            name="Old account",
            account_type="ASSET",
            is_header=False,
            is_active=False,
        )
        payload = self._entry_payload(test_organisation, archived)
        payload["lines"][1]["account_id"] = str(test_accounts["1200"].id)

        with pytest.raises(ServiceValidationError, match="(?i)inactive|archived|not active"):
            JournalService.create_entry(
                org_id=test_organisation.id,
                entry_date=payload["entry_date"],
                source_type="MANUAL",
                narration=payload["description"],
                lines=payload["lines"],
                user_id=test_user.id,
            )
