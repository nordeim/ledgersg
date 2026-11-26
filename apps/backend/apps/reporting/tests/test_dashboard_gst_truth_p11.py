"""
P11/H-4 — the dashboard's GST liability is real.

`calculate_gst_liability` sourced its output/input tax from
JournalLine.tax_code/tax_amount — but the only JournalLine creation site
(journal_service.post_invoice) never sets them, so every real org reported
GST Payable = SGD 0.00 on the dashboard, forever. The computation now
mirrors get_f5_box_amounts' semantics over document lines: posting
document types only (quotes/POs excluded), credit notes netted.
"""

import uuid
from datetime import date
from decimal import Decimal

import pytest
from django.core.cache import cache

from apps.core.models import (
    Account,
    AppUser,
    Contact,
    FiscalPeriod,
    FiscalYear,
    Organisation,
    Role,
    TaxCode,
    UserOrganisation,
    DocumentSequence,
)
from apps.invoicing.services import DocumentService
from apps.reporting.services.dashboard_service import DashboardService

pytestmark = pytest.mark.django_db


@pytest.fixture
def org():
    user = AppUser.objects.create(
        id=uuid.uuid4(),
        email=f"dashgst_{uuid.uuid4().hex[:8]}@example.com",
        full_name="Dashboard GST Tester",
        is_active=True,
    )
    org = Organisation.objects.create(
        name="Dashboard GST Org",
        uen="DASHGST1",
        entity_type="PRIVATE_LIMITED",
        gst_registered=True,
        gst_reg_number="M12345678",
        gst_reg_date=date(2024, 1, 1),
        fy_start_month=1,
        base_currency="SGD",
        is_active=True,
    )
    Role.objects.create(org=org, name="Owner", description="Full access")
    UserOrganisation.objects.create(
        user=user, org=org, role=Role.objects.get(org=org),
        is_default=True, invited_at=date(2024, 1, 1), accepted_at=date(2024, 1, 1),
    )
    fy = FiscalYear.objects.create(
        org=org, label="FY2024",
        start_date=date(2024, 1, 1), end_date=date(2024, 12, 31),
        is_closed=False,
    )
    FiscalPeriod.objects.create(
        org=org, fiscal_year=fy, label="Jan 2024", period_number=1,
        start_date=date(2024, 1, 1), end_date=date(2024, 1, 31), is_open=True,
    )
    for doc_type, prefix in [
        ("SALES_INVOICE", "INV-"),
        ("SALES_CREDIT_NOTE", "CN-"),
        ("PURCHASE_INVOICE", "PUR-"),
        ("PURCHASE_CREDIT_NOTE", "PCN-"),
        ("JOURNAL_ENTRY", "JE-"),
    ]:
        DocumentSequence.objects.create(
            org=org, document_type=doc_type, prefix=prefix, next_number=1, padding=5
        )
    return org


@pytest.fixture
def accounts(org):
    """Revenue/expense lines + the control accounts the posting engine resolves."""
    return {
        "4000": Account.objects.create(
            org=org, code="4000", name="Sales Revenue", account_type="REVENUE"
        ),
        "5000": Account.objects.create(
            org=org, code="5000", name="Operating Expenses", account_type="EXPENSE"
        ),
        "1200": Account.objects.create(
            org=org, code="1200", name="Accounts Receivable", account_type="ASSET"
        ),
        "2100": Account.objects.create(
            org=org, code="2100", name="Accounts Payable", account_type="LIABILITY"
        ),
        "2600": Account.objects.create(
            org=org, code="2600", name="GST Output Tax", account_type="LIABILITY"
        ),
        "1600": Account.objects.create(
            org=org, code="1600", name="GST Input Tax", account_type="ASSET"
        ),
    }


@pytest.fixture
def tax_codes(org):
    return {
        "SR": TaxCode.objects.create(
            org=org, code="SR", description="Standard Rate",
            rate=Decimal("0.0900"), is_input=False, is_output=True,
            is_claimable=True, f5_supply_box=1, f5_tax_box=6,
            is_active=True, effective_from=date(2024, 1, 1),
        ),
        "TX": TaxCode.objects.create(
            org=org, code="TX", description="Taxable Purchase",
            rate=Decimal("0.0900"), is_input=True, is_output=False,
            is_claimable=True, f5_purchase_box=5, f5_tax_box=7,
            is_active=True, effective_from=date(2024, 1, 1),
        ),
    }


def _contact(org, document_type):
    return Contact.objects.create(
        org=org,
        contact_type="CUSTOMER" if document_type.startswith("SALES") else "SUPPLIER",
        name=f"GST Fixture {document_type}",
        is_customer=document_type.startswith("SALES"),
        is_supplier=not document_type.startswith("SALES"),
    )


def _make_and_approve(org, accounts, tax_codes, user, document_type, account_code, tax_code, related_document=None):
    """P14/H-4 contract update: credit notes carry the original invoice."""
    if related_document is not None:
        contact = related_document.contact
    else:
        contact = _contact(org, document_type)
    doc = DocumentService.create_document(
        org_id=org.id,
        document_type=document_type,
        contact_id=contact.id,
        issue_date=date(2024, 1, 15),
        lines=[
            {
                "account_id": accounts[account_code].id,
                "description": "Fixture line",
                "quantity": 1,
                "unit_price": Decimal("1000.00"),
                "tax_code_id": tax_codes[tax_code].id,
            }
        ],
        user_id=user.id,
        related_document_id=related_document.id if related_document else None,
    )
    DocumentService.transition_status(
        org_id=org.id, document_id=doc.id, new_status="SENT", user_id=user.id
    )
    DocumentService.transition_status(
        org_id=org.id, document_id=doc.id, new_status="APPROVED", user_id=user.id
    )
    return doc


def _owner(org):
    return UserOrganisation.objects.get(org=org).user


class TestDashboardGSTLiabilityIsReal:
    def test_approved_invoice_reports_non_zero_output_tax(self, org, accounts, tax_codes):
        """RED for H-4: a real approved invoice must produce non-zero GST.

        Before: the journal lines never carried tax_code/tax_amount, so
        GST Payable was structurally SGD 0.00 on every real org.
        """
        cache.delete(f"dashboard:{org.id}")
        _make_and_approve(org, accounts, tax_codes, _owner(org), "SALES_INVOICE", "4000", "SR")

        liability = DashboardService().calculate_gst_liability(
            str(org.id), date(2024, 1, 1), date(2024, 12, 31)
        )

        assert liability["output_tax"] == Decimal("90.00"), (
            f"one 1000.00 SR invoice must report 90.00 output tax "
            f"(got {liability['output_tax']})"
        )
        assert liability["input_tax"] == Decimal("0.00")
        assert liability["net_gst"] == Decimal("90.00"), (
            f"net GST must be 90.00 (got {liability['net_gst']})"
        )

    def test_credit_note_nets_the_liability(self, org, accounts, tax_codes):
        """An equal credit note nets the period's GST to zero (H-4 + C-1)."""
        cache.delete(f"dashboard:{org.id}")
        invoice = _make_and_approve(org, accounts, tax_codes, _owner(org), "SALES_INVOICE", "4000", "SR")
        _make_and_approve(
            org, accounts, tax_codes, _owner(org), "SALES_CREDIT_NOTE", "4000", "SR",
            related_document=invoice,
        )

        liability = DashboardService().calculate_gst_liability(
            str(org.id), date(2024, 1, 1), date(2024, 12, 31)
        )

        assert liability["output_tax"] == Decimal("0.00"), (
            f"invoice + equal credit note must net output tax to 0 "
            f"(got {liability['output_tax']})"
        )

    def test_claimable_purchase_reports_input_tax(self, org, accounts, tax_codes):
        """A claimable TX purchase reports input tax (Box 7 semantics)."""
        cache.delete(f"dashboard:{org.id}")
        _make_and_approve(org, accounts, tax_codes, _owner(org), "PURCHASE_INVOICE", "5000", "TX")

        liability = DashboardService().calculate_gst_liability(
            str(org.id), date(2024, 1, 1), date(2024, 12, 31)
        )

        assert liability["input_tax"] == Decimal("90.00"), (
            f"one 1000.00 TX purchase must report 90.00 input tax "
            f"(got {liability['input_tax']})"
        )
        assert liability["net_gst"] == Decimal("-90.00")
