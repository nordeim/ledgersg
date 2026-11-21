"""
Atomic rollback invariants (C-04 remediation).

Guards the transactional integrity of multi-step financial operations:
- wrap_response must let unexpected exceptions propagate so the surrounding
  ATOMIC_REQUESTS block rolls back instead of committing partial state.
- approve_document must post the journal entry inside its atomic block so a
  posting failure rolls back the APPROVED transition.
"""

from datetime import date

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
