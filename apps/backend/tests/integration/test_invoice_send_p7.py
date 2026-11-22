"""P7/F-6: send-invoice recipients — the list contract on the backend.

The frontend sent `to: "user@x.com"` (a string); the view passed it through,
the truthiness check kept it a string, and the Celery task crashed building
EmailMultiAlternatives(to=<string>) — a silent permanent failure while the
API had already returned success. The view must normalize a single string
to a one-element list and reject non-email strings with a 400.
"""

import pytest
from datetime import date
from decimal import Decimal
from unittest.mock import patch

from rest_framework import status

from apps.core.models import Contact, InvoiceDocument


def _make_approved_invoice(org):
    contact = Contact.objects.create(
        org=org, contact_type="CUSTOMER", name="Send Customer",
        email="customer@send.example", is_customer=True, is_active=True,
    )
    doc = InvoiceDocument.objects.create(
        org=org,
        document_type="SALES_INVOICE",
        document_number=f"INV-SEND-{InvoiceDocument.objects.filter(org=org).count() + 1:05d}",
        contact=contact,
        issue_date=date(2024, 1, 15),
        due_date=date(2024, 2, 15),
        currency="SGD",
        exchange_rate=Decimal("1.000000"),
        total_excl=Decimal("100.0000"),
        total_incl=Decimal("109.0000"),
        amount_paid=Decimal("0.0000"),
        status="APPROVED",
    )
    return doc


@pytest.mark.django_db
class TestInvoiceSendRecipients:
    def url(self, org, doc):
        return f"/api/v1/{org.id}/invoicing/documents/{doc.id}/send/"

    def test_string_to_is_normalized_to_list(self, auth_client, test_organisation):
        """A single string recipient is accepted and reaches the task as a
        one-element list (the pre-P7 path crashed the task)."""
        doc = _make_approved_invoice(test_organisation)
        with patch("apps.invoicing.tasks.send_invoice_email_task.delay") as task:
            response = auth_client.post(
                self.url(test_organisation, doc), {"to": "someone@example.com"}, format="json"
            )
        assert response.status_code == status.HTTP_200_OK, response.data
        task.assert_called_once()
        args = task.call_args[0]
        assert args[2] == ["someone@example.com"], args

    def test_list_to_passes_through(self, auth_client, test_organisation):
        doc = _make_approved_invoice(test_organisation)
        with patch("apps.invoicing.tasks.send_invoice_email_task.delay") as task:
            response = auth_client.post(
                self.url(test_organisation, doc),
                {"to": ["a@example.com", "b@example.com"]},
                format="json",
            )
        assert response.status_code == status.HTTP_200_OK, response.data
        args = task.call_args[0]
        assert args[2] == ["a@example.com", "b@example.com"]

    def test_non_email_recipient_rejected(self, auth_client, test_organisation):
        """A non-email string is a 400, not a queued task that will crash."""
        doc = _make_approved_invoice(test_organisation)
        with patch("apps.invoicing.tasks.send_invoice_email_task.delay") as task:
            response = auth_client.post(
                self.url(test_organisation, doc), {"to": "not-an-email"}, format="json"
            )
        assert response.status_code == status.HTTP_400_BAD_REQUEST, response.data
        task.assert_not_called()

    def test_invalid_in_list_rejected(self, auth_client, test_organisation):
        doc = _make_approved_invoice(test_organisation)
        with patch("apps.invoicing.tasks.send_invoice_email_task.delay") as task:
            response = auth_client.post(
                self.url(test_organisation, doc),
                {"to": ["a@example.com", "garbage"]},
                format="json",
            )
        assert response.status_code == status.HTTP_400_BAD_REQUEST, response.data
        task.assert_not_called()
