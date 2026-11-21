"""
P6/F-11 — invoice detail truth: amount_paid / amount_due.

RED suite: the detail serializer (and therefore the detail endpoint the
frontend detail page consumes) must expose the document's payment state.
The model persists amount_paid (P5/H-1) and the DB exposes amount_due as
a generated column (total_amount - amount_paid), but the detail
serializer omitted both.
"""

from decimal import Decimal

import pytest
from rest_framework import status

from apps.invoicing.serializers import InvoiceDocumentDetailSerializer
from tests.conftest import create_test_contact, create_test_invoice

pytestmark = pytest.mark.django_db


@pytest.fixture
def paid_invoice(test_organisation):
    """An APPROVED invoice with a partial payment recorded."""
    contact = create_test_contact(test_organisation)
    invoice = create_test_invoice(
        test_organisation,
        contact,
        status="APPROVED",
        total_excl=Decimal("1000.0000"),
        gst_total=Decimal("90.0000"),
        total_incl=Decimal("1090.0000"),
        amount_paid=Decimal("400.0000"),
    )
    return invoice


def test_detail_serializer_exposes_amount_paid_and_amount_due(paid_invoice):
    serializer = InvoiceDocumentDetailSerializer(paid_invoice)
    data = serializer.data

    assert "amount_paid" in data, (
        "the detail serializer must expose amount_paid — the frontend "
        "detail page needs the payment state"
    )
    assert "amount_due" in data, (
        "the detail serializer must expose amount_due (the DB generated "
        "column: total_amount - amount_paid)"
    )
    assert Decimal(data["amount_paid"]) == Decimal("400.0000")
    assert Decimal(data["amount_due"]) == Decimal("690.0000")


def test_detail_endpoint_exposes_amount_paid_and_amount_due(
    auth_client, paid_invoice, test_organisation
):
    url = f"/api/v1/{test_organisation.id}/invoicing/documents/{paid_invoice.id}/"

    response = auth_client.get(url)

    assert response.status_code == status.HTTP_200_OK, response.data
    assert "amount_paid" in response.data
    assert "amount_due" in response.data
    assert Decimal(str(response.data["amount_paid"])) == Decimal("400.0000")
    assert Decimal(str(response.data["amount_due"])) == Decimal("690.0000")
