"""Regression tests for the DocumentSummaryView endpoint (A-2, 2026-11-21 P1 sprint).

The view previously referenced a phantom ``DOCUMENT_TYPE_CHOICES`` attribute,
filtered with the invalid ``PAID_PARTIAL`` enum literal, summed a phantom
``total`` attribute (real field: ``total_incl``) and would crash on
``.quantize()`` when no outstanding documents exist. These tests pin the
corrected contract.
"""

from datetime import date, timedelta
from decimal import Decimal

import pytest

from tests.conftest import create_test_contact

pytestmark = pytest.mark.django_db


@pytest.fixture
def _seeded_documents(test_organisation):
    """Three invoices exercising the summary semantics:

    - APPROVED, due in the future  -> outstanding, not overdue
    - PARTIALLY_PAID, due in the past -> outstanding AND overdue
    - DRAFT                        -> neither (excluded everywhere)
    """
    from apps.core.models import InvoiceDocument

    contact = create_test_contact(test_organisation)

    def _make(number, **kwargs):
        defaults = {
            "document_type": "SALES_INVOICE",
            "contact": contact,
            "issue_date": date.today() - timedelta(days=5),
            "due_date": date.today() + timedelta(days=25),
            "status": "DRAFT",
            "total_incl": Decimal("0.0000"),
        }
        defaults.update(kwargs)
        return InvoiceDocument.objects.create(
            org=test_organisation, document_number=number, **defaults
        )

    return {
        "approved": _make(
            "INV-SUM-001", status="APPROVED", total_incl=Decimal("100.0000")
        ),
        "partially_paid": _make(
            "INV-SUM-002",
            status="PARTIALLY_PAID",
            issue_date=date.today() - timedelta(days=60),
            due_date=date.today() - timedelta(days=30),
            total_incl=Decimal("50.0000"),
        ),
        "draft": _make(
            "INV-SUM-003", status="DRAFT", total_incl=Decimal("999.0000")
        ),
    }


class TestDocumentSummary:
    def test_summary_returns_200(self, auth_client, test_organisation, _seeded_documents):
        response = auth_client.get(f"/api/v1/{test_organisation.id}/invoicing/documents/summary/")
        assert response.status_code == 200

    def test_summary_counts_by_status(self, auth_client, test_organisation, _seeded_documents):
        response = auth_client.get(f"/api/v1/{test_organisation.id}/invoicing/documents/summary/")
        body = response.json()
        assert body["by_status"] == {"APPROVED": 1, "PARTIALLY_PAID": 1, "DRAFT": 1}
        assert body["by_type"] == {"SALES_INVOICE": 3}
        assert body["total_count"] == 3

    def test_summary_outstanding_sums_unpaid_statuses(
        self, auth_client, test_organisation, _seeded_documents
    ):
        """Outstanding must cover every post-approval, not-fully-paid status
        (APPROVED, SENT, PARTIALLY_PAID, OVERDUE) — the old code used the
        invalid literal PAID_PARTIAL and matched nothing."""
        response = auth_client.get(f"/api/v1/{test_organisation.id}/invoicing/documents/summary/")
        body = response.json()
        assert Decimal(body["total_outstanding"]) == Decimal("150.00")

    def test_summary_overdue_respects_due_date(
        self, auth_client, test_organisation, _seeded_documents
    ):
        response = auth_client.get(f"/api/v1/{test_organisation.id}/invoicing/documents/summary/")
        body = response.json()
        assert body["overdue_count"] == 1

    def test_summary_with_no_documents_does_not_crash(self, auth_client, test_organisation):
        """Empty org: sum() must start at Decimal zero so .quantize() works."""
        response = auth_client.get(f"/api/v1/{test_organisation.id}/invoicing/documents/summary/")
        assert response.status_code == 200
        body = response.json()
        assert body["total_outstanding"] == "0.00"
        assert body["overdue_count"] == 0
