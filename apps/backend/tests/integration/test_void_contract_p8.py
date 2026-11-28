"""
P8/G-3 + G-5: the void contract, aligned end to end.

Pre-P8: STATUS_TRANSITIONS advertised DRAFT→VOID, PAID→VOID and OVERDUE→VOID,
but void_document accepted only APPROVED/SENT/PARTIALLY_PAID — an OVERDUE
invoice could be voided through NO endpoint, DRAFT/PAID users saw a Void
button that always 400'd, voiding a PARTIALLY_PAID document orphaned its
payment allocations, and the generic status endpoint silently defaulted a
filler reason while the dedicated /void/ required one.
"""

from datetime import date
from decimal import Decimal

import pytest
from rest_framework import status

from apps.core.models import Contact, InvoiceDocument, PaymentAllocation


def _make_document(org, contact, doc_status="DRAFT"):
    doc = InvoiceDocument.objects.create(
        org=org,
        document_type="SALES_INVOICE",
        document_number=f"INV-TEST-{InvoiceDocument.objects.filter(org=org).count() + 1:05d}",
        contact=contact,
        issue_date=date(2024, 1, 15),
        due_date=date(2024, 2, 15),
        currency="SGD",
        exchange_rate=Decimal("1.000000"),
        total_excl=Decimal("100.0000"),
        total_incl=Decimal("109.0000"),
        amount_paid=Decimal("0.0000"),
        status=doc_status,
    )
    return doc


def _make_contact(org):
    return Contact.objects.create(
        org=org, contact_type="CUSTOMER", name="Void Contract C", is_customer=True, is_active=True
    )


def _make_allocation(org, doc, gl_account, amount=Decimal("40.0000")):
    """Create a PaymentAllocation row against `doc` (direct model writes —
    the allocation semantics are not under test here, only the guard)."""
    from apps.core.models import BankAccount, Payment

    bank = BankAccount.objects.create(
        org=org,
        account_name="Void Contract Bank",
        bank_name="Test Bank",
        account_number="0000-0000",
        currency="SGD",
        gl_account=gl_account,
        paynow_type=None,  # DB CHECK: NULL or UEN/MOBILE/NRIC ("" violates it)
    )
    payment = Payment.objects.create(
        org=org,
        payment_type="RECEIVED",
        payment_number=f"REC-VC-{Payment.objects.filter(org=org).count() + 1:05d}",
        payment_date=date(2024, 1, 20),
        contact=doc.contact,
        bank_account=bank,
        currency="SGD",
        exchange_rate=Decimal("1.000000"),
        amount=amount,
        base_amount=amount,
        fx_gain_loss=Decimal("0.0000"),
    )
    return PaymentAllocation.objects.create(
        org=org,
        payment=payment,
        document=doc,
        allocated_amount=amount,
        base_allocated_amount=amount,
    )


@pytest.mark.django_db
class TestVoidContractP8:
    """void_document, the generic /status/ endpoint, the advertised map and
    the allocation guard must agree on ONE contract."""

    def _status_url(self, org, doc):
        return f"/api/v1/{org.id}/invoicing/documents/{doc.id}/status/"

    def _void_url(self, org, doc):
        return f"/api/v1/{org.id}/invoicing/documents/{doc.id}/void/"

    # --- the state-machine contradictions -------------------------------

    def test_overdue_can_be_voided(self, auth_client, test_organisation, test_user,
                                   test_fiscal_period, test_accounts):
        """OVERDUE is an approved invoice past due — the advertised map lists
        OVERDUE→VOID, so both endpoints must accept it (pre-P8: NO endpoint
        could void an overdue invoice)."""
        doc = _make_document(test_organisation, _make_contact(test_organisation), "OVERDUE")

        response = auth_client.post(
            self._status_url(test_organisation, doc),
            {"status": "VOID", "reason": "wrong customer"},
            format="json",
        )
        assert response.status_code == status.HTTP_200_OK, response.data
        doc.refresh_from_db()
        assert doc.status == "VOID"

    def test_draft_can_be_voided_without_journal_side_effects(
        self, auth_client, test_organisation, test_user
    ):
        """DRAFT→VOID is advertised (and is how a wrong draft is retired) —
        a draft has no journal entry, so the void is a pure status flip."""
        doc = _make_document(test_organisation, _make_contact(test_organisation), "DRAFT")

        response = auth_client.post(
            self._status_url(test_organisation, doc),
            {"status": "VOID", "reason": "created by mistake"},
            format="json",
        )
        assert response.status_code == status.HTTP_200_OK, response.data
        doc.refresh_from_db()
        assert doc.status == "VOID"
        assert doc.journal_entry_id is None  # nothing to reverse

    def test_paid_void_refused_with_credit_note_guidance(
        self, auth_client, test_organisation, test_user
    ):
        """A paid invoice is remedied with a credit note, not a void — both
        endpoints refuse with the same actionable message (pre-P8: generic
        'Only APPROVED, SENT, or PARTIALLY_PAID' noise)."""
        doc = _make_document(test_organisation, _make_contact(test_organisation), "PAID")

        response = auth_client.post(
            self._status_url(test_organisation, doc),
            {"status": "VOID", "reason": "x"},
            format="json",
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "credit note" in str(response.data).lower()

        response = auth_client.post(
            self._void_url(test_organisation, doc), {"reason": "x"}, format="json"
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "credit note" in str(response.data).lower()

    def test_advertised_map_matches_enforced_contract(self, auth_client, test_organisation):
        """ValidStatusTransitionsView must not advertise transitions the
        engine refuses: PAID no longer lists VOID (remedy = credit note)."""
        response = auth_client.get(
            f"/api/v1/{test_organisation.id}/invoicing/documents/status-transitions/"
        )
        assert response.status_code == status.HTTP_200_OK
        transitions = response.data["transitions"]
        assert "VOID" not in transitions["PAID"], transitions["PAID"]
        # The reachable void sources stay advertised.
        for src in ("DRAFT", "SENT", "APPROVED", "OVERDUE", "PARTIALLY_PAID"):
            assert "VOID" in transitions[src], (src, transitions[src])

    # --- the allocation guard ---------------------------------------------

    def test_void_with_allocations_refused(
        self, auth_client, test_organisation, test_user, test_accounts, test_fiscal_period
    ):
        """Voiding must not orphan payment allocations — refuse until they
        are unallocated (pre-P8: the void succeeded and left allocations
        pointing at a VOID document)."""
        doc = _make_document(test_organisation, _make_contact(test_organisation), "PARTIALLY_PAID")
        doc.amount_paid = Decimal("40.0000")
        doc.save()
        _make_allocation(test_organisation, doc, test_accounts["1200"])

        response = auth_client.post(
            self._status_url(test_organisation, doc),
            {"status": "VOID", "reason": "x"},
            format="json",
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "unallocate" in str(response.data).lower()
        doc.refresh_from_db()
        assert doc.status == "PARTIALLY_PAID"

        response = auth_client.post(
            self._void_url(test_organisation, doc), {"reason": "x"}, format="json"
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "unallocate" in str(response.data).lower()

    # --- the reason contract (G-5) -----------------------------------------

    def test_generic_endpoint_requires_reason_for_void(
        self, auth_client, test_organisation, test_user
    ):
        """The generic endpoint must not persist a filler reason — the
        dedicated /void/ requires one; same operation, same contract."""
        doc = _make_document(test_organisation, _make_contact(test_organisation), "APPROVED")

        response = auth_client.post(
            self._status_url(test_organisation, doc), {"status": "VOID"}, format="json"
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "reason" in str(response.data).lower()
        doc.refresh_from_db()
        assert doc.status == "APPROVED"
