"""
P14/H-3 — no posting into a GST-filed period.

Once an F5 return covering a period has been FILED (or AMENDED), the
ledger for that period is the statutory basis of the filed figures:
- documents must not APPROVE or VOID with dates inside the filed period
- manual journal entries must not post into it
- payment voids must not date their reversal inside it
Corrections go through the amendment flow / post-filing voluntary
disclosure, never silent back-posting.
"""

from datetime import date, timedelta
from decimal import Decimal
import uuid

import pytest

from common.exceptions import ValidationError
from apps.core.models import (
    Contact,
    FiscalPeriod,
    FiscalYear,
    GSTReturn,
    InvoiceDocument,
    DocumentSequence,
)
from apps.gst.services import GSTReturnService
from apps.invoicing.services import DocumentService
from apps.journal.services import JournalService
from tests.conftest import create_test_contact


@pytest.fixture
def filed_period_fixture(
    test_organisation, test_user, test_accounts, test_tax_codes, test_fiscal_period
):
    """An org with a FILED GST return covering January 2024 and an open
    fiscal period covering it (so ONLY the GST lock can refuse)."""
    org = test_organisation

    DocumentSequence.objects.get_or_create(
        org=org, document_type="SALES_INVOICE", defaults={"prefix": "INV-", "next_number": 1}
    )

    # A fiscal year + period covering Jan 2024 (OPEN — the only guard that
    # can refuse a Jan-2024 posting after the fix is the GST lock).
    fy = FiscalYear.objects.create(
        org=org,
        label="FY2024-lock",
        start_date=date(2024, 1, 1),
        end_date=date(2024, 12, 31),
        is_closed=False,
    )
    jan_period = FiscalPeriod.objects.create(
        org=org,
        fiscal_year=fy,
        label="Jan 2024 (lock)",
        period_number=1,
        start_date=date(2024, 1, 1),
        end_date=date(2024, 1, 31),
        is_open=True,
    )

    gst_return = GSTReturn.objects.create(
        org_id=org.id,
        period_start=date(2024, 1, 1),
        period_end=date(2024, 1, 31),
        filing_due_date=date(2024, 2, 29),
        status="COMPUTED",
        box1_std_rated_supplies=Decimal("0"),
        box4_total_supplies=Decimal("0"),
        box6_output_tax=Decimal("0"),
        box8_net_gst=Decimal("0"),
        box13_total_revenue=Decimal("0"),
    )
    filed = GSTReturnService.file_return(
        org_id=org.id,
        return_id=gst_return.id,
        filed_by_id=test_user.id,
        filing_reference="IRAS-LOCK-001",
    )

    contact = create_test_contact(org, is_customer=True)

    return {
        "org": org,
        "user": test_user,
        "accounts": test_accounts,
        "contact": contact,
        "filed_return": filed,
        "jan_period": jan_period,
        "fy": fy,
    }


def _make_invoice(fx, issue_date):
    return InvoiceDocument.objects.create(
        org=fx["org"],
        document_type="SALES_INVOICE",
        contact=fx["contact"],
        document_number=f"INV-H3-{uuid.uuid4().hex[:6]}",
        issue_date=issue_date,
        due_date=issue_date + timedelta(days=30),
        status="DRAFT",
        total_excl=Decimal("100.00"),
        gst_total=Decimal("9.00"),
        total_incl=Decimal("109.00"),
        amount_paid=Decimal("0.0000"),
    )


class TestGSTLockP14:
    @pytest.mark.django_db
    def test_document_approve_into_filed_period_is_refused(self, filed_period_fixture):
        """RED for H-3: an invoice dated inside the filed period cannot be
        approved (the posting would diverge the ledger from the filed
        figures)."""
        fx = filed_period_fixture
        doc = _make_invoice(fx, date(2024, 1, 15))

        with pytest.raises(ValidationError) as excinfo:
            DocumentService.transition_status(
                org_id=fx["org"].id, document_id=doc.id, new_status="APPROVED", user_id=fx["user"].id
            )
        assert "GST" in str(excinfo.value) or "filed" in str(excinfo.value).lower()

        doc.refresh_from_db()
        assert doc.status == "DRAFT"

    @pytest.mark.django_db
    def test_document_approve_after_filed_period_is_allowed(self, filed_period_fixture):
        """H-3 control: February postings stay green (the lock covers the
        filed period only)."""
        fx = filed_period_fixture
        # Feb period must exist for the posting
        FiscalPeriod.objects.create(
            org=fx["org"],
            fiscal_year=fx["fy"],
            label="Feb 2024 (lock)",
            period_number=2,
            start_date=date(2024, 2, 1),
            end_date=date(2024, 2, 29),
            is_open=True,
        )
        doc = _make_invoice(fx, date(2024, 2, 15))

        DocumentService.transition_status(
            org_id=fx["org"].id, document_id=doc.id, new_status="APPROVED", user_id=fx["user"].id
        )
        doc.refresh_from_db()
        assert doc.status == "APPROVED"

    @pytest.mark.django_db
    def test_manual_journal_into_filed_period_is_refused(self, filed_period_fixture):
        """RED for H-3: a manual journal dated inside the filed period is
        refused."""
        fx = filed_period_fixture
        with pytest.raises(ValidationError) as excinfo:
            JournalService.create_entry(
                org_id=fx["org"].id,
                entry_date=date(2024, 1, 10),
                source_type="MANUAL",
                narration="post-filing backpost probe",
                lines=[
                    {
                        "account_id": fx["accounts"]["4000"].id,
                        "debit": Decimal("10.00"),
                        "credit": Decimal("0"),
                    },
                    {
                        "account_id": fx["accounts"]["1200"].id,
                        "debit": Decimal("0"),
                        "credit": Decimal("10.00"),
                    },
                ],
                user_id=fx["user"].id,
            )
        assert "GST" in str(excinfo.value) or "filed" in str(excinfo.value).lower()

    @pytest.mark.django_db
    def test_document_void_inside_filed_period_is_refused(self, filed_period_fixture):
        """H-3: voiding a document dated inside the filed period is refused
        (the reversal would diverge the filed basis)."""
        fx = filed_period_fixture
        doc = _make_invoice(fx, date(2024, 1, 15))
        # Put it in a voidable pre-approved state by direct DB write (the
        # approve path is itself locked now — that's the point).
        doc.status = "SENT"
        doc.save()

        with pytest.raises(ValidationError) as excinfo:
            DocumentService.void_document(
                org_id=fx["org"].id,
                document_id=doc.id,
                user=fx["user"],
                reason="post-filing void probe",
            )
        assert "GST" in str(excinfo.value) or "filed" in str(excinfo.value).lower()
