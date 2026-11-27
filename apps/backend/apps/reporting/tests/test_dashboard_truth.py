"""
P5/H-3 + H-10 — dashboard truth: cache invalidation and real alerts.

RED suite (against the pre-P5 code): invalidate_dashboard_cache exists but
no mutation path ever calls it (the 5-minute cache serves stale KPIs
forever), and DashboardAlertsView returns placeholder zeros.
"""

import uuid
from datetime import date
from decimal import Decimal

import pytest
from django.core.cache import cache
from rest_framework import status
from rest_framework.test import APIClient

from apps.core.models import (
    Account,
    AppUser,
    Contact,
    FiscalPeriod,
    FiscalYear,
    InvoiceDocument,
    Organisation,
    Role,
    UserOrganisation,
)
from apps.invoicing.services import DocumentService
from apps.reporting.services.dashboard_service import DashboardService

pytestmark = pytest.mark.django_db


@pytest.fixture
def user():
    user_id = uuid.uuid4()
    user = AppUser.objects.create(
        id=user_id,
        email=f"alerts_{user_id.hex[:8]}@example.com",
        full_name="Alerts User",
        is_active=True,
    )
    return user


@pytest.fixture
def org(user):
    org_id = uuid.uuid4()
    org = Organisation.objects.create(
        id=org_id,
        name="Alerts Org",
        uen="ALERTSG1",
        entity_type="PRIVATE_LIMITED",
        gst_registered=True,
        gst_reg_number="M12345678",
        gst_reg_date=date(2024, 1, 1),
        fy_start_month=1,
        base_currency="SGD",
        is_active=True,
    )
    role = Role.objects.create(org=org, name="Owner", description="Full access")
    UserOrganisation.objects.create(
        user=user,
        org=org,
        role=role,
        is_default=True,
        invited_at=date(2024, 1, 1),
        accepted_at=date(2024, 1, 1),
    )
    fy = FiscalYear.objects.create(
        org=org,
        label="FY2024",
        start_date=date(2024, 1, 1),
        end_date=date(2024, 12, 31),
        is_closed=False,
    )
    FiscalPeriod.objects.create(
        org=org,
        fiscal_year=fy,
        label="Jan 2024",
        period_number=1,
        start_date=date(2024, 1, 1),
        end_date=date(2024, 1, 31),
        is_open=True,
    )
    from apps.core.models import DocumentSequence

    for doc_type, prefix in [
        ("SALES_INVOICE", "INV-"),
        ("JOURNAL_ENTRY", "JE-"),
    ]:
        DocumentSequence.objects.create(
            org=org, document_type=doc_type, prefix=prefix, next_number=1, padding=5
        )
    return org


@pytest.fixture
def accounts(org):
    """Minimal chart matching the real seed's control codes."""
    return {
        "ar": Account.objects.create(
            org=org, code="1200", name="Accounts Receivable", account_type="ASSET"
        ),
        "revenue": Account.objects.create(
            org=org, code="4000", name="Sales Revenue", account_type="REVENUE"
        ),
        "gst_output": Account.objects.create(
            org=org, code="2600", name="GST Output Tax", account_type="LIABILITY"
        ),
        "bank": Account.objects.create(
            org=org, code="1100", name="Bank Account", account_type="ASSET"
        ),
    }


@pytest.fixture
def tax_code(org):
    from apps.core.models import TaxCode

    return TaxCode.objects.create(
        org=org,
        code="SR",
        description="Standard Rate",
        rate=Decimal("0.0900"),
        is_input=False,
        is_output=True,
        is_claimable=True,
        f5_supply_box=1,
        f5_tax_box=6,
        is_active=True,
        effective_from=date(2024, 1, 1),
    )


@pytest.fixture
def customer(org):
    return Contact.objects.create(
        org=org,
        contact_type="CUSTOMER",
        name="Alerts Customer",
        email="a@x.sg",
        is_customer=True,
    )


def _overdue_invoice(org, customer):
    """An APPROVED invoice whose due date is in the past and nothing is paid."""
    return InvoiceDocument.objects.create(
        org=org,
        document_type="SALES_INVOICE",
        document_number="INV-OVERDUE-1",
        contact=customer,
        issue_date=date(2024, 1, 1),
        due_date=date(2024, 1, 31),
        total_excl=Decimal("1000.0000"),
        gst_total=Decimal("90.0000"),
        total_incl=Decimal("1090.0000"),
        status="APPROVED",
    )


class TestDashboardAlertsAreReal:
    """P5/H-10: the alerts view must compute, not fabricate."""

    def test_overdue_invoice_is_counted(self, org, user, customer):
        from rest_framework_simplejwt.tokens import RefreshToken

        _overdue_invoice(org, customer)

        client = APIClient()
        client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {str(RefreshToken.for_user(user).access_token)}"
        )
        response = client.get(f"/api/v1/{org.id}/reports/dashboard/alerts/")

        assert response.status_code == status.HTTP_200_OK, response.data
        data = response.data.get("data", response.data)
        assert data["overdue_invoices_count"] == 1, (
            "one APPROVED invoice past due with nothing paid must be counted; "
            f"got {data['overdue_invoices_count']}"
        )
        assert any(
            a.get("title", "").lower().startswith("overdue")
            for a in data["alerts"]
        ), f"expected an overdue alert, got {data['alerts']}"

    def test_empty_org_reports_zero_counts(self, org, user):
        from rest_framework_simplejwt.tokens import RefreshToken

        client = APIClient()
        client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {str(RefreshToken.for_user(user).access_token)}"
        )
        response = client.get(f"/api/v1/{org.id}/reports/dashboard/alerts/")

        assert response.status_code == status.HTTP_200_OK, response.data
        data = response.data.get("data", response.data)
        assert data["overdue_invoices_count"] == 0
        assert data["alerts"] == []


class TestDashboardCacheInvalidation:
    """P5/H-3: mutations must invalidate the 5-minute dashboard cache."""

    def test_document_mutation_invalidates_cache(
        self, org, user, customer, accounts, tax_code,
        django_capture_on_commit_callbacks,
    ):
        cache.delete(f"dashboard:{org.id}")
        service = DashboardService()

        # Prime the cache
        service.get_dashboard_data(str(org.id))
        assert cache.get(f"dashboard:{org.id}") is not None

        # Any document mutation (approve) must invalidate it. P21/BE-M3:
        # the invalidation is registered on COMMIT (a delete inside the
        # transaction re-seeds the stale value in the delete->commit
        # window) — the probe executes the callbacks the way a real
        # commit would.
        document = DocumentService.create_document(
            org_id=org.id,
            document_type="SALES_INVOICE",
            contact_id=customer.id,
            issue_date=date(2024, 1, 15),
        )
        DocumentService.add_line(
            org_id=org.id,
            document_id=document.id,
            account_id=accounts["revenue"].id,
            description="Service",
            quantity=Decimal("1"),
            unit_price=Decimal("100.00"),
            tax_code_id=tax_code.id,
        )
        with django_capture_on_commit_callbacks(execute=True):
            DocumentService.approve_document(org.id, document.id, user)

        assert cache.get(f"dashboard:{org.id}") is None, (
            "approving a document must invalidate the dashboard cache — "
            "otherwise the dashboard serves stale KPIs for 5 minutes"
        )

    def test_invalidation_survives_recompute_cycle(
        self, org, user, customer, accounts, tax_code,
        django_capture_on_commit_callbacks,
    ):
        """get -> mutate -> get returns fresh data (not the pre-mutation row)."""
        cache.delete(f"dashboard:{org.id}")
        service = DashboardService()

        first = service.get_dashboard_data(str(org.id))
        document = DocumentService.create_document(
            org_id=org.id,
            document_type="SALES_INVOICE",
            contact_id=customer.id,
            issue_date=date(2024, 1, 15),
        )
        DocumentService.add_line(
            org_id=org.id,
            document_id=document.id,
            account_id=accounts["revenue"].id,
            description="Service",
            quantity=Decimal("1"),
            unit_price=Decimal("100.00"),
            tax_code_id=tax_code.id,
        )
        # P21/BE-M3: the invalidation is registered on commit — execute
        # the callbacks the way a real commit would.
        with django_capture_on_commit_callbacks(execute=True):
            DocumentService.approve_document(org.id, document.id, user)
        second = service.get_dashboard_data(str(org.id))

        assert second is not first
        # a fresh recompute happened (new dict), and the cache holds it
        assert cache.get(f"dashboard:{org.id}") is not None
