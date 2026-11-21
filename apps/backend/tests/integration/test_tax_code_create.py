"""
Regression tests for custom tax-code creation (B-7).

The view passed a phantom ``box_mapping`` kwarg through to
``TaxCode.objects.create`` — every POST /gst/tax-codes/ failed with a
TypeError (500). These tests pin the working contract.
"""

from decimal import Decimal

import pytest
from rest_framework import status

pytestmark = pytest.mark.django_db


def test_create_custom_tax_code_succeeds(auth_client, test_organisation):
    """POST /api/v1/{org}/gst/tax-codes/ creates a custom code (201)."""
    response = auth_client.post(
        f"/api/v1/{test_organisation.id}/gst/tax-codes/",
        {
            "code": "SVC7",
            "name": "Service 7%",
            "rate": "0.0700",
            "is_gst_charged": True,
            "description": "Custom service rate",
        },
        format="json",
    )

    assert response.status_code == status.HTTP_201_CREATED, response.data
    data = response.data
    assert data["code"] == "SVC7"
    assert Decimal(str(data["rate"])) == Decimal("0.0700")
    assert data["is_gst_charged"] is True


def test_create_custom_tax_code_with_f5_boxes(auth_client, test_organisation):
    """Declared f5_* serializer fields are persisted, not silently dropped."""
    response = auth_client.post(
        f"/api/v1/{test_organisation.id}/gst/tax-codes/",
        {
            "code": "SVC5",
            "name": "Service 5%",
            "rate": "0.0500",
            "is_gst_charged": True,
            "f5_supply_box": 1,
            "f5_tax_box": 6,
        },
        format="json",
    )

    assert response.status_code == status.HTTP_201_CREATED, response.data
    assert response.data["f5_supply_box"] == 1
    assert response.data["f5_tax_box"] == 6


def test_create_reserved_tax_code_rejected(auth_client, test_organisation):
    """IRAS-reserved codes stay reserved (service raises ValidationError -> 400)."""
    response = auth_client.post(
        f"/api/v1/{test_organisation.id}/gst/tax-codes/",
        {
            "code": "SR",
            "name": "Duplicate of reserved",
            "rate": "0.0900",
            "is_gst_charged": True,
        },
        format="json",
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
