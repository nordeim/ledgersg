"""
P38/BE-P38-H1: the credit-note InvoiceNow gates.

The transmission pipeline has guaranteed the full credit-note truth since
P37 — the mapper threads the BillingReference, the generator emits the
PINT-SG CreditNote, the validator dispatches by root type (P34/BE-P34-H1
(b)), and BR-SG-07 pins the reference floor. But BOTH workflow entry
points refused credit notes: send_invoicenow's P9/C-3 type gate (calibrated
pre-P34, when "the transmission path maps anything non-credit-note to UBL
Invoice") and approve_document's auto-transmit condition (SALES_INVOICE
only). The UI advertised the send the whole time (canSendInvoiceNow gates
on APPROVED + !isQuote — the button renders for credit notes and always
400'd). The IRAS e-Tax Guide on the GST InvoiceNow requirement (§11.6)
expects credit note data on the InvoiceNow channel.

RED on the base tree for exactly the right reasons: the manual send raises
ValidationError "Only SALES_INVOICE" and the HTTP surface answers 400; the
approval of a credit note queues nothing. The controls (quote, inbound
types, DRAFT, missing peppol_id, unconfigured org) PASS on the base tree
and must stay green.
"""

import datetime
from unittest.mock import Mock, patch

import pytest
from rest_framework import status
from rest_framework.test import APIClient

from apps.invoicing.services.document_service import DocumentService
from apps.peppol.models import OrganisationPeppolSettings, PeppolTransmissionLog
from tests.conftest import create_test_contact, create_test_invoice

# The outbound transmittable set — the ONLY types whose UBL rendering is
# truthful (the mapper maps document_type CREDIT_NOTE for SALES_CREDIT_NOTE
# alone and renders every other type as a UBL Invoice).
OUTBOUND_TYPES = ("SALES_INVOICE", "SALES_CREDIT_NOTE")

# The fiscal window the test_fiscal_period fixture opens (January 2024).
OPEN_PERIOD_DATE = datetime.date(2024, 1, 15)


def _auth(api_client: APIClient, user):
    from rest_framework_simplejwt.tokens import RefreshToken

    refresh = RefreshToken.for_user(user)
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {str(refresh.access_token)}")
    return api_client


def _configure_peppol(org, auto_transmit=False):
    """A fully-configured OrganisationPeppolSettings row (the wiring
    convention)."""
    return OrganisationPeppolSettings.objects.create(
        org=org,
        access_point_provider="storecove",
        access_point_api_url="https://api.storecove.example",
        access_point_api_key="test-key",
        access_point_client_id="test-client",
        auto_transmit=auto_transmit,
        is_active=True,
    )


def _credit_note(org, status="APPROVED", peppol_id="0195:SG-UUID:demo-recipient"):
    """A credit note that carries everything the transmission needs: a
    contact with a Peppol participant id and — per the P14/H-4 DB contract
    every service-created credit note satisfies — the original invoice
    (related_document), the reference BR-SG-07 floors."""
    contact = create_test_contact(org, peppol_id=peppol_id)
    original = create_test_invoice(org, contact, status="APPROVED")
    return create_test_invoice(
        org,
        contact,
        status=status,
        document_type="SALES_CREDIT_NOTE",
        related_document=original,
        issue_date=OPEN_PERIOD_DATE,
        due_date=OPEN_PERIOD_DATE + datetime.timedelta(days=30),
    )


def _posting_credit_note(org, accounts, tax_codes, user):
    """A service-created DRAFT credit note with real lines — the
    P11 `_make_document` convention (issue_date inside the open fiscal
    period; lines referencing a REVENUE account and the SR tax code) — so
    approve_document's journal posting succeeds."""
    from decimal import Decimal

    contact = create_test_contact(
        org, peppol_id="0195:SG-UUID:demo-recipient"
    )
    original = DocumentService.create_document(
        org_id=org.id,
        document_type="SALES_INVOICE",
        contact_id=contact.id,
        issue_date=OPEN_PERIOD_DATE,
        lines=[
            {
                "account_id": accounts["4000"].id,
                "description": "P38 original line",
                "quantity": 1,
                "unit_price": Decimal("100.00"),
                "tax_code_id": tax_codes["SR"].id,
            }
        ],
        user_id=user.id,
    )
    return DocumentService.create_document(
        org_id=org.id,
        document_type="SALES_CREDIT_NOTE",
        contact_id=contact.id,
        issue_date=OPEN_PERIOD_DATE,
        lines=[
            {
                "account_id": accounts["4000"].id,
                "description": "P38 credit line",
                "quantity": 1,
                "unit_price": Decimal("100.00"),
                "tax_code_id": tax_codes["SR"].id,
            }
        ],
        user_id=user.id,
        related_document_id=original.id,
    )


# ---------------------------------------------------------------------------
# RED gates — the manual send
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestSendInvoiceNowCreditNoteGate:
    """The P9/C-3 gate widens to the outbound transmittable set."""

    def test_approved_credit_note_is_transmittable(self, test_organisation):
        """The service-level gate: an APPROVED SALES_CREDIT_NOTE queues a
        REAL transmission log (RED on the base tree: the Only-SALES_INVOICE
        refusal)."""
        _configure_peppol(test_organisation)
        cn = _credit_note(test_organisation)

        with patch("apps.peppol.tasks.transmit_peppol_invoice_task.delay") as mock_delay:
            mock_delay.return_value = Mock(id="task-123")
            result = DocumentService.send_invoicenow(
                test_organisation.id, cn.id, user=None
            )

        log = PeppolTransmissionLog.objects.get(id=result["transmission_log_id"])
        assert log.document_id == cn.id
        assert log.org_id == test_organisation.id
        assert log.status in ("PENDING", "TRANSMITTING")
        assert mock_delay.called, "the real Celery task must be queued"
        assert result["status"] == "QUEUED"

    def test_http_send_invoicenow_on_credit_note_is_200(
        self, api_client, test_user, test_organisation
    ):
        """The HTTP-level gate: POST send-invoicenow on the APPROVED credit
        note answers 200 with the log id (RED on the base tree: 400 — the
        live-probe-confirmed P9/C-3 refusal)."""
        _configure_peppol(test_organisation)
        cn = _credit_note(test_organisation)
        _auth(api_client, test_user)

        url = (
            f"/api/v1/{test_organisation.id}/invoicing/"
            f"documents/{cn.id}/send-invoicenow/"
        )
        with patch("apps.peppol.tasks.transmit_peppol_invoice_task.delay") as mock_delay:
            mock_delay.return_value = Mock(id="task-123")
            response = api_client.post(url)

        assert response.status_code == status.HTTP_200_OK, response.data
        assert response.data["status"] == "QUEUED"
        assert response.data["transmission_log_id"]
        assert mock_delay.called


# ---------------------------------------------------------------------------
# RED gate — the auto-transmit on approval
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestApprovalAutoTransmitCreditNote:
    """Approving a credit note under an auto_transmit org queues the
    transmission exactly as an invoice approval does."""

    def test_approving_credit_note_queues_transmission(
        self, test_organisation, test_user, test_accounts, test_tax_codes,
        test_fiscal_period,
    ):
        """DRAFT -> APPROVED under auto_transmit=True creates the PENDING
        log row (RED on the base tree: the queue condition only fires for
        SALES_INVOICE — no log is created)."""
        _configure_peppol(test_organisation, auto_transmit=True)
        cn = _posting_credit_note(
            test_organisation, test_accounts, test_tax_codes, test_user
        )

        with patch("apps.peppol.tasks.transmit_peppol_invoice_task.delay") as mock_delay:
            mock_delay.return_value = Mock(id="task-123")
            approved = DocumentService.approve_document(
                test_organisation.id, cn.id, user=test_user
            )

        assert approved.status == "APPROVED"
        log = PeppolTransmissionLog.objects.get(document_id=cn.id)
        assert log.org_id == test_organisation.id
        assert log.status in ("PENDING", "TRANSMITTING")
        assert mock_delay.called, "the auto-transmit task must be queued"


# ---------------------------------------------------------------------------
# Control gates — the surrounding contracts must not move
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestSendInvoiceNowControls:
    """The gates that must NOT widen: the P9/C-3 quote hazard, the inbound
    types, the status gate, the recipient gate, the configuration gate."""

    def test_approved_quote_is_still_refused(
        self, api_client, test_user, test_organisation
    ):
        """P9/C-3's own contract: an APPROVED quote must not be delivered as
        a tax invoice (the mapper renders every non-credit-note as UBL
        Invoice)."""
        _configure_peppol(test_organisation)
        contact = create_test_contact(
            test_organisation, peppol_id="0195:SG-UUID:demo-recipient"
        )
        quote = create_test_invoice(
            test_organisation, contact, status="APPROVED", document_type="SALES_QUOTE"
        )
        _auth(api_client, test_user)

        url = (
            f"/api/v1/{test_organisation.id}/invoicing/"
            f"documents/{quote.id}/send-invoicenow/"
        )
        response = api_client.post(url)

        assert response.status_code == status.HTTP_400_BAD_REQUEST, response.data
        assert "SALES_QUOTE" in str(response.data)

    @pytest.mark.parametrize(
        "inbound_type", ["PURCHASE_INVOICE", "PURCHASE_CREDIT_NOTE"]
    )
    def test_inbound_document_types_are_still_refused(
        self, test_organisation, inbound_type
    ):
        """Purchase documents are RECEIVED by this org — the pipeline
        renders them as outbound UBL, so they must never be sent."""
        _configure_peppol(test_organisation)
        contact = create_test_contact(
            test_organisation, peppol_id="0195:SG-UUID:demo-recipient"
        )
        original = create_test_invoice(test_organisation, contact, status="APPROVED")
        doc = create_test_invoice(
            test_organisation,
            contact,
            status="APPROVED",
            document_type=inbound_type,
            related_document=original,
        )

        from apps.invoicing.services.document_service import ValidationError

        with pytest.raises(ValidationError, match="InvoiceNow"):
            DocumentService.send_invoicenow(
                test_organisation.id, doc.id, user=None
            )

    def test_draft_credit_note_is_still_refused(self, test_organisation):
        """The status gate: only APPROVED documents may transmit."""
        _configure_peppol(test_organisation)
        cn = _credit_note(test_organisation, status="DRAFT")

        from apps.invoicing.services.document_service import ValidationError

        with pytest.raises(ValidationError, match="APPROVED"):
            DocumentService.send_invoicenow(
                test_organisation.id, cn.id, user=None
            )

    def test_credit_note_without_contact_peppol_id_is_refused(
        self, test_organisation
    ):
        """The recipient gate: a contact without a Peppol participant id
        cannot receive a transmission."""
        _configure_peppol(test_organisation)
        cn = _credit_note(test_organisation, peppol_id=None)

        from apps.invoicing.services.document_service import ValidationError

        with pytest.raises(ValidationError, match="Peppol ID"):
            DocumentService.send_invoicenow(
                test_organisation.id, cn.id, user=None
            )

    def test_credit_note_without_peppol_config_is_refused(self, test_organisation):
        """The configuration gate: an unconfigured org queues nothing."""
        cn = _credit_note(test_organisation)

        from apps.invoicing.services.document_service import ValidationError

        with pytest.raises(ValidationError, match="[Cc]onfigured"):
            DocumentService.send_invoicenow(
                test_organisation.id, cn.id, user=None
            )
