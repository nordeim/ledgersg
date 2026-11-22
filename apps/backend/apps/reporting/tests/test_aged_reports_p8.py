"""
P8/R-5: aged receivables and payables.

The reports page advertises an "Aged Receivables" card, but no aged
endpoint existed anywhere — only the dashboard's single outstanding
totals. This endpoint returns per-contact rows bucketed by days past due
(current / 1-30 / 31-60 / 61-90 / 90+), mirroring the dashboard service's
document-type and status semantics.
"""

import uuid
from datetime import date
from decimal import Decimal

import pytest
from rest_framework import status
from rest_framework.test import APIClient

from apps.core.models import (
    AppUser,
    Contact,
    InvoiceDocument,
    Organisation,
    Role,
    UserOrganisation,
)

pytestmark = pytest.mark.django_db


def _make_user_org():
    user = AppUser.objects.create(
        id=uuid.uuid4(),
        email=f"aged_{uuid.uuid4().hex[:8]}@example.com",
        full_name="Aged User",
        is_active=True,
    )
    org = Organisation.objects.create(
        name="Aged Reports Org",
        entity_type="PRIVATE_LIMITED",
        base_currency="SGD",
        gst_registered=False,
    )
    role = Role.objects.create(
        org=org, name="Owner", description="owner",
        can_view_reports=True, can_manage_org=True,
        can_create_invoices=True, can_approve_invoices=True,
        can_void_invoices=True, can_create_journals=True,
        can_manage_banking=True, can_file_gst=True,
        can_manage_users=True, can_manage_coa=True, can_export_data=True,
    )
    UserOrganisation.objects.create(
        user=user, org=org, role=role, is_default=True,
        invited_at=date.today(), accepted_at=date.today(),
    )
    return user, org


def _client(user):
    from rest_framework_simplejwt.tokens import RefreshToken

    client = APIClient()
    refresh = RefreshToken.for_user(user)
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {str(refresh.access_token)}")
    return client


def _doc(org, contact, number, issue, due, doc_type="SALES_INVOICE",
         status="APPROVED", total="109.0000", paid="0.0000"):
    return InvoiceDocument.objects.create(
        org=org,
        document_type=doc_type,
        document_number=number,
        contact=contact,
        issue_date=issue,
        due_date=due,
        currency="SGD",
        exchange_rate=Decimal("1.000000"),
        total_excl=Decimal("100.0000"),
        total_incl=Decimal(total),
        amount_paid=Decimal(paid),
        status=status,
    )


class TestAgedReportsP8:
    def url(self, org, **params):
        qs = "&".join(f"{k}={v}" for k, v in params.items())
        return f"/api/v1/{org.id}/reports/aged/{('?' + qs) if qs else ''}"

    def _fixture(self, as_at="2024-03-31"):
        """Three customers, five invoices, spanning every bucket (as_at
        2024-03-31): alpha current (due 4/15), beta 1-30 & 31-60, gamma
        61-90 & 90+, plus a PAID doc (excluded) and a DRAFT (excluded)."""
        user, org = _make_user_org()
        alpha = Contact.objects.create(
            org=org, contact_type="CUSTOMER", name="Alpha", is_customer=True, is_active=True
        )
        beta = Contact.objects.create(
            org=org, contact_type="CUSTOMER", name="Beta", is_customer=True, is_active=True
        )
        gamma = Contact.objects.create(
            org=org, contact_type="CUSTOMER", name="Gamma", is_customer=True, is_active=True
        )

        _doc(org, alpha, "INV-A1", date(2024, 3, 1), date(2024, 4, 15))          # current
        _doc(org, beta, "INV-B1", date(2024, 2, 1), date(2024, 3, 1))            # 1-30
        _doc(org, beta, "INV-B2", date(2024, 1, 1), date(2024, 1, 31))           # 31-60
        _doc(org, gamma, "INV-G1", date(2023, 12, 1), date(2024, 1, 5))         # 61-90
        _doc(org, gamma, "INV-G2", date(2023, 11, 1), date(2023, 11, 30))        # 90+
        _doc(org, alpha, "INV-A2", date(2024, 3, 1), date(2024, 4, 15),
             status="PAID", total="50.0000", paid="50.0000")                     # excluded
        _doc(org, alpha, "INV-A3", date(2024, 3, 1), date(2024, 4, 15),
             status="DRAFT")                                                     # excluded
        # partially paid: outstanding 59 of 109, current bucket
        _doc(org, alpha, "INV-A4", date(2024, 3, 1), date(2024, 4, 15),
             paid="50.0000")
        return user, org, alpha, beta, gamma

    def test_receivables_buckets_per_contact(self):
        user, org, alpha, beta, gamma = self._fixture()
        client = _client(user)

        response = client.get(
            self.url(org, type="receivables", as_at="2024-03-31")
        )
        assert response.status_code == status.HTTP_200_OK, response.data
        data = response.data

        rows = {row["contact_name"]: row for row in data["results"]}
        assert set(rows) == {"Alpha", "Beta", "Gamma"}, rows.keys()

        # INV-A1 (109 unpaid) + INV-A4 (109 total - 50 paid = 59 outstanding)
        assert Decimal(rows["Alpha"]["outstanding_total"]) == Decimal("168.0000")
        assert Decimal(rows["Alpha"]["current"]) == Decimal("168.0000")
        assert Decimal(rows["Alpha"]["d90_plus"]) == Decimal("0.0000")

        assert Decimal(rows["Beta"]["d1_30"]) == Decimal("109.0000")
        assert Decimal(rows["Beta"]["d31_60"]) == Decimal("109.0000")

        assert Decimal(rows["Gamma"]["d61_90"]) == Decimal("109.0000")
        assert Decimal(rows["Gamma"]["d90_plus"]) == Decimal("109.0000")

        totals = data["totals"]
        # 168 (alpha) + 218 (beta) + 218 (gamma)
        assert Decimal(totals["outstanding_total"]) == Decimal("604.0000"), totals
        assert Decimal(totals["current"]) == Decimal("168.0000")
        assert Decimal(totals["d90_plus"]) == Decimal("109.0000")

    def test_payables_uses_purchase_documents(self):
        user, org, alpha, beta, gamma = self._fixture()
        # A purchase bill for alpha (a supplier here) in the 90+ bucket
        supplier = Contact.objects.create(
            org=org, contact_type="SUPPLIER", name="Alpha", is_supplier=True, is_active=True
        )
        _doc(org, supplier, "BILL-S1", date(2023, 11, 1), date(2023, 11, 30),
             doc_type="PURCHASE_INVOICE")
        client = _client(user)

        response = client.get(
            self.url(org, type="payables", as_at="2024-03-31")
        )
        assert response.status_code == status.HTTP_200_OK, response.data
        rows = {row["contact_name"]: row for row in response.data["results"]}
        assert set(rows) == {"Alpha"}, rows.keys()
        assert Decimal(rows["Alpha"]["d90_plus"]) == Decimal("109.0000")

    def test_invalid_type_is_400(self):
        user, org, *_ = self._fixture()
        client = _client(user)
        response = client.get(self.url(org, type="both"))
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_invalid_as_at_is_400(self):
        user, org, *_ = self._fixture()
        client = _client(user)
        response = client.get(self.url(org, type="receivables", as_at="not-a-date"))
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_requires_reports_permission(self):
        user, org, *_ = self._fixture()
        # A member with no can_view_reports
        limited = AppUser.objects.create(
            id=uuid.uuid4(),
            email=f"limited_{uuid.uuid4().hex[:8]}@example.com",
            full_name="Limited", is_active=True,
        )
        limited_role = Role.objects.create(
            org=org, name="Viewer", description="v", can_view_reports=False
        )
        UserOrganisation.objects.create(
            user=limited, org=org, role=limited_role, is_default=True,
            invited_at=date.today(), accepted_at=date.today(),
        )
        client = _client(limited)
        response = client.get(self.url(org, type="receivables"))
        assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
class TestAgedAsAtBoundP9:
    """P9/D-1: the as_at date bounds the document set.

    Pre-P9 the queryset had no date bound — a document issued 2025-06
    appeared in an as_at=2024-12-31 report (bucketed "current"), so any
    historical date produced a materially wrong statement. The reports
    page exposes the As-at picker.
    """

    def test_document_issued_after_as_at_is_excluded(self):
        user, org = _make_user_org()
        client = _client(user)
        contact = Contact.objects.create(
            org=org, contact_type="CUSTOMER", name="AsAt Customer",
            is_customer=True, is_active=True,
        )
        # One document in force before the as-at date…
        _doc(org, contact, "INV-ASAT-1",
             issue=date(2024, 6, 1), due=date(2024, 7, 1))
        # …and one issued AFTER it.
        _doc(org, contact, "INV-ASAT-2",
             issue=date(2025, 6, 1), due=date(2025, 7, 1))

        response = client.get(
            f"/api/v1/{org.id}/reports/aged/?type=receivables&as_at=2024-12-31"
        )

        assert response.status_code == status.HTTP_200_OK, response.data
        results = response.data["results"]
        assert len(results) == 1, results
        assert results[0]["document_count"] == 1
        assert results[0]["outstanding_total"] == "109.0000"

    def test_today_still_includes_everything_outstanding(self):
        user, org = _make_user_org()
        client = _client(user)
        contact = Contact.objects.create(
            org=org, contact_type="CUSTOMER", name="AsAt Customer 2",
            is_customer=True, is_active=True,
        )
        _doc(org, contact, "INV-ASAT-3",
             issue=date(2024, 6, 1), due=date(2024, 7, 1))
        _doc(org, contact, "INV-ASAT-4",
             issue=date(2025, 6, 1), due=date(2025, 7, 1))

        response = client.get(
            f"/api/v1/{org.id}/reports/aged/?type=receivables&as_at=2026-11-22"
        )

        assert response.status_code == status.HTTP_200_OK, response.data
        results = response.data["results"]
        assert len(results) == 1
        assert results[0]["document_count"] == 2
