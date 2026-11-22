"""P9/B-3b: the documents list carries the outstanding balance.

The payment forms' allocation section (and any list UI) needs
amount_paid/amount_due per row; the list serializer stopped at
total_incl, so a UI could not show what is left to settle without
fetching every document's detail.
"""
import pytest
from datetime import date
from decimal import Decimal
from rest_framework import status

from apps.core.models import Contact, InvoiceDocument


@pytest.mark.django_db
class TestListAmountsP9:
    def test_list_rows_carry_amount_paid_and_due(self, auth_client, test_organisation):
        contact = Contact.objects.create(
            org=test_organisation, contact_type="CUSTOMER", name="Alloc Customer",
            is_customer=True, is_active=True,
        )
        InvoiceDocument.objects.create(
            org=test_organisation,
            document_type="SALES_INVOICE",
            document_number="INV-ALLOC-1",
            contact=contact,
            issue_date=date(2024, 1, 15),
            due_date=date(2024, 2, 15),
            currency="SGD",
            exchange_rate=Decimal("1.000000"),
            total_excl=Decimal("100.0000"),
            total_incl=Decimal("109.0000"),
            amount_paid=Decimal("40.0000"),
            status="PARTIALLY_PAID",
        )

        response = auth_client.get(
            f"/api/v1/{test_organisation.id}/invoicing/documents/",
            {"type": "SALES_INVOICE", "contact_id": str(contact.id)},
        )

        assert response.status_code == status.HTTP_200_OK, response.data
        row = response.data["results"][0]
        assert row["amount_paid"] == "40.0000"
        assert row["amount_due"] == "69.0000"
