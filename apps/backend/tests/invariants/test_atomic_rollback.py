"""
Atomic rollback invariants (C-04 remediation).

Guards the transactional integrity of multi-step financial operations:
- wrap_response must let unexpected exceptions propagate so the surrounding
  ATOMIC_REQUESTS block rolls back instead of committing partial state.
- approve_document must post the journal entry inside its atomic block so a
  posting failure rolls back the APPROVED transition.
"""

from datetime import date
from decimal import Decimal

import pytest

from apps.invoicing.services import DocumentService
from tests.conftest import create_test_contact, create_test_invoice


@pytest.fixture
def period_invoice(test_organisation):
    """A DRAFT sales invoice dated inside the open fiscal period (Jan 2024)."""
    contact = create_test_contact(test_organisation)
    return create_test_invoice(
        test_organisation,
        contact,
        issue_date=date(2024, 1, 15),
        due_date=date(2024, 2, 15),
    )


@pytest.mark.django_db
def test_wrap_response_reraises_unexpected_exception():
    """
    RED for C-04: a view decorated with @wrap_response that raises an
    unexpected exception must propagate it (so Django's atomic request
    wrapper rolls the transaction back).
    """
    from common.views import wrap_response

    @wrap_response
    def boom(*args, **kwargs):
        raise RuntimeError("simulated mid-operation failure")

    with pytest.raises(RuntimeError, match="simulated mid-operation failure"):
        boom()


@pytest.mark.django_db
def test_approve_rolls_back_when_journal_post_fails(
    test_user,
    test_organisation,
    test_accounts,
    test_tax_codes,
    test_fiscal_period,
    period_invoice,
):
    """
    RED for C-04: when journal posting fails after the status transition,
    the whole approve operation must roll back — no APPROVED invoice without
    a ledger entry may persist.
    """
    from unittest.mock import patch

    from apps.core.models import InvoiceDocument, JournalEntry
    from apps.journal.services.journal_service import JournalService

    org_id = test_organisation.id
    invoice_id = period_invoice.id

    with patch.object(
        JournalService, "post_invoice", side_effect=RuntimeError("GL account missing")
    ), pytest.raises(RuntimeError, match="GL account missing"):
        DocumentService.approve_document(org_id, invoice_id, test_user)

    document = InvoiceDocument.objects.get(id=invoice_id, org_id=org_id)
    assert document.status == "DRAFT", (
        "Status transition must roll back when journal posting fails; "
        f"got '{document.status}'"
    )
    assert document.approved_at is None
    assert document.journal_entry_id is None
    assert JournalEntry.objects.filter(org_id=org_id).count() == 0


# ---------------------------------------------------------------------------
# P13/B-1: the DRF exception handler must not convert unhandled exceptions
# into committed 500 Responses. The fallback in common/exceptions.py runs
# INSIDE the request transaction (Django's ATOMIC_REQUESTS wrapper); a
# plain Response(500) makes dispatch look successful and the surrounding
# transaction COMMITS the partial writes. The handler must mark the
# transaction for rollback before returning the envelope.
# ---------------------------------------------------------------------------


@pytest.mark.django_db(transaction=True)
def test_unhandled_exception_marks_transaction_for_rollback(db):
    """
    RED for P13/B-1: custom_exception_handler's 500 fallback must call
    transaction.set_rollback(True) so the request transaction discards
    everything written before the crash.
    """
    from django.db import transaction

    from common.exceptions import custom_exception_handler

    email = "rollback-canary@ledgersg.sg"
    # idempotent pre-clean: a RED run of this test legitimately commits the
    # canary (that is the bug); scrub it so reruns stay deterministic.
    AppUser = pytest.importorskip("apps.core.models").AppUser
    AppUser.objects.filter(email=email).delete()
    with transaction.atomic():
        AppUser.objects.create_user(
            email=email, password="CanaryPass123!", full_name="Rollback Canary"
        )
        # The write is visible inside the block…
        assert AppUser.objects.filter(email=email).exists()

        from rest_framework.test import APIRequestFactory

        request = APIRequestFactory().post("/api/v1/auth/register/", {})
        response = custom_exception_handler(
            RuntimeError("simulated mid-write failure"), {"request": request, "view": None}
        )
        assert response is not None and response.status_code == 500

        # …but the handler must have marked the transaction for rollback.
        assert transaction.get_rollback() is True, (
            "custom_exception_handler returned a 500 Response without marking the "
            "transaction for rollback — the partial writes will COMMIT."
        )

    # After the atomic block: the partial write must be gone.
    assert not AppUser.objects.filter(email=email).exists(), (
        "The partial write survived — the 500 Response committed it."
    )


@pytest.mark.django_db(transaction=True)
def test_unhandled_exception_through_dispatch_rolls_back_partial_writes(db):
    """
    RED for P13/B-1 (full DRF dispatch): a view that writes and then raises
    an unhandled exception must leave NOTHING committed — the 500 envelope
    must not be a "successful" response for the transaction wrapper.
    """
    from unittest.mock import patch

    from rest_framework.test import APIClient

    from apps.core.models import AppUser

    email = "dispatch-canary@ledgersg.sg"
    # idempotent pre-clean (a RED run commits this canary — the bug itself)
    AppUser.objects.filter(email=email).delete()
    client = APIClient()

    with patch(
        "apps.core.views.auth.auth_service.generate_tokens",
        side_effect=RuntimeError("simulated token-service failure"),
    ):
        response = client.post(
            "/api/v1/auth/register/",
            {
                "email": email,
                "password": "CanaryPass123!",
                "full_name": "Dispatch Canary",
            },
            format="json",
        )

    # The documented JSON envelope is preserved…
    assert response.status_code == 500
    assert response.json()["error"]["code"] == "internal_error"

    # …but the user (+ the org/membership the register flow created) must
    # NOT have committed.
    assert not AppUser.objects.filter(email=email).exists(), (
        "register_user's writes committed despite the unhandled exception — "
        "partial state persists (P13/B-1)."
    )


# ---------------------------------------------------------------------------
# P13/B-11: create_reversal is a two-phase write (create the reversal entry,
# then mark the original). The phases must be atomic together — a failure
# in the second phase must not leave an orphan reversal next to an unmarked
# original (which would permit a SECOND reversal and double-count the books).
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_reversal_second_phase_failure_leaves_no_orphan(
    test_organisation, test_accounts, test_fiscal_period, test_user
):
    """
    RED for P13/B-11: when the original-marking phase fails, the reversal
    entry must roll back with it.
    """
    from unittest.mock import patch

    from apps.core.models import JournalEntry
    from apps.journal.services import JournalService

    ar_account = test_accounts["1200"]
    revenue_account = test_accounts["4000"]

    original = JournalService.create_entry(
        org_id=test_organisation.id,
        entry_date=date(2024, 1, 15),
        source_type="MANUAL",
        narration="B-11 canary original",
        lines=[
            {
                "account_id": ar_account.id,
                "debit": Decimal("100.00"),
                "credit": Decimal("0.00"),
                "description": "AR",
            },
            {
                "account_id": revenue_account.id,
                "debit": Decimal("0.00"),
                "credit": Decimal("100.00"),
                "description": "Revenue",
            },
        ],
        fiscal_period_id=test_fiscal_period.id,
        user_id=test_user.id,
    )

    orphan_probe = JournalEntry.objects.filter(
        org_id=test_organisation.id,
        source_type="REVERSAL",
        narration__contains=original.entry_number,
    )

    assert orphan_probe.count() == 0

    # Patch the marking phase: the original's save raises once the
    # is_reversed/reversed_by flip is attempted.
    real_save = JournalEntry.save

    def failing_mark_save(self, *args, **kwargs):
        if getattr(self, "is_reversed", False):
            raise RuntimeError("simulated original-marking failure")
        return real_save(self, *args, **kwargs)

    with patch.object(JournalEntry, "save", failing_mark_save):
        with pytest.raises(RuntimeError, match="original-marking failure"):
            JournalService.create_reversal(
                org_id=test_organisation.id,
                original_entry_id=original.id,
                reversal_date=date(2024, 1, 20),
                reason="B-11 canary",
                user_id=test_user.id,
            )

    # The reversal entry must NOT have persisted (no orphan).
    assert orphan_probe.count() == 0, (
        "The reversal entry persisted while the original stayed unmarked — "
        "an orphan reversal that permits a second reversal (double-count)."
    )
    original.refresh_from_db()
    assert original.is_reversed is False


# ---------------------------------------------------------------------------
# P13/B-13: the service balance tolerance must match the DB trigger's
# (0.0001). The service allowed <= 0.001 — an imbalance of 0.0002..0.001
# passed the service check and then failed at COMMIT with an unhandled
# database error (500) instead of the typed 400.
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_submil_imbalance_is_typed_400_not_commit_500(
    test_organisation, test_accounts, test_fiscal_period, test_user
):
    """
    RED for P13/B-13: an imbalance within the service's old tolerance
    (0.0005) but outside the DB trigger's (0.0001) must be rejected by the
    SERVICE with a typed 400, not blow up at COMMIT.
    """
    from apps.journal.services import JournalService
    from common.exceptions import ValidationError as LedgerValidationError

    ar_account = test_accounts["1200"]
    revenue_account = test_accounts["4000"]

    with pytest.raises(LedgerValidationError, match="equal credits"):
        JournalService.create_entry(
            org_id=test_organisation.id,
            entry_date=date(2024, 1, 15),
            source_type="MANUAL",
            narration="B-13 tolerance canary",
            lines=[
                {
                    "account_id": ar_account.id,
                    "debit": Decimal("100.0005"),
                    "credit": Decimal("0.00"),
                    "description": "AR",
                },
                {
                    "account_id": revenue_account.id,
                    "debit": Decimal("0.00"),
                    "credit": Decimal("100.0000"),
                    "description": "Revenue",
                },
            ],
            fiscal_period_id=test_fiscal_period.id,
            user_id=test_user.id,
        )
