"""
P5/H-4 + H-5 + H-6 — control-account resolution, money quantization and
line numbering invariants.

RED suite (against the pre-P5 code):
- H-4: the AR/AP/GST resolvers broad-match with .first() — output tax lands
  on 2200 Accrued Expenses, AR can land on a header account, and a non-GST
  org silently posts GST to a random asset instead of failing closed.
- H-5: add_line stores a 4dp line_amount while the GST base is the 2dp
  amount — subtotal/GST/total do not reconcile to the cent.
- H-6: create_entry numbers lines via list.index() — duplicate line dicts
  get the same line_number.
"""

from datetime import date
from decimal import Decimal

import pytest
from django.db import connection

from apps.core.models import (
    Account,
    Contact,
    FiscalPeriod,
    FiscalYear,
    InvoiceDocument,
    JournalLine,
    TaxCode,
)
from apps.invoicing.services import DocumentService
from apps.journal.services import JournalService
from common.exceptions import ValidationError

pytestmark = pytest.mark.django_db


def _seed_coa(org_id, gst_registered=True):
    """Seed the REAL chart via the SQL function (the live path).

    The function also seeds all document sequences, so any test-created
    sequences for this org must go first (a fresh production org gets
    everything from this one function).
    """
    from apps.core.models import DocumentSequence

    DocumentSequence.objects.filter(org_id=org_id).delete()
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT core.seed_default_chart_of_accounts(%s, %s)",
            [str(org_id), gst_registered],
        )


def _fy_and_period(org):
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
    # NB: document sequences come with _seed_coa (the SQL function seeds
    # them all) — do not create them here.


def _sr_tax_code(org):
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


def _invoice_with_line(org, tax_code, gst_amount=Decimal("9.00")):
    contact = Contact.objects.create(
        org=org, contact_type="CUSTOMER", name="Resolution Cust", email="r@x.sg"
    )
    revenue = Account.objects.get(org=org, code="4000")
    invoice = InvoiceDocument.objects.create(
        org=org,
        document_type="SALES_INVOICE",
        document_number="INV-RES-001",
        contact=contact,
        issue_date=date(2024, 1, 15),
        due_date=date(2024, 2, 14),
        total_excl=Decimal("100.0000"),
        gst_total=gst_amount,
        total_incl=Decimal("100.0000") + gst_amount,
        status="APPROVED",
    )
    from apps.core.models import InvoiceLine

    InvoiceLine.objects.create(
        org=org,
        document=invoice,
        line_number=1,
        account=revenue,
        description="Service",
        quantity=Decimal("1"),
        unit_price=Decimal("100.0000"),
        line_amount=Decimal("100.0000"),
        gst_amount=gst_amount,
        total_amount=Decimal("100.0000") + gst_amount,
        tax_code=tax_code,
        tax_rate=Decimal("0.0900"),
    )
    return invoice


class TestControlAccountResolution:
    """P5/H-4: exact control-account resolution, fail-closed."""

    def test_ar_resolver_returns_the_1200_control_account(self, test_organisation):
        _seed_coa(test_organisation.id, gst_registered=True)

        ar = JournalService._get_ar_account(test_organisation.id)

        assert ar.code == "1200", (
            f"AR must resolve to the 1200 control account, got {ar.code} "
            "(unordered .first() over a broad OR-match can return any asset)"
        )

    def test_gst_output_resolver_returns_2600_not_accrued(self, test_organisation):
        _seed_coa(test_organisation.id, gst_registered=True)

        gst = JournalService._get_gst_output_account(test_organisation.id)

        assert gst.code == "2600", (
            f"GST output must resolve to 2600 GST Output Tax, got {gst.code} "
            "(the old code__startswith='220' matched 2200 Accrued Expenses)"
        )

    def test_gst_input_resolver_returns_1600(self, test_organisation):
        _seed_coa(test_organisation.id, gst_registered=True)

        gst = JournalService._get_gst_input_account(test_organisation.id)

        assert gst.code == "1600", (
            f"GST input must resolve to 1600 GST Input Tax, got {gst.code} "
            "(the old broad ASSET match could return Cash on Hand)"
        )

    def test_posted_sales_invoice_debits_1200_and_credits_2600(
        self, test_organisation, test_user
    ):
        _seed_coa(test_organisation.id, gst_registered=True)
        _fy_and_period(test_organisation)
        tax_code = _sr_tax_code(test_organisation)
        invoice = _invoice_with_line(test_organisation, tax_code)

        entry = JournalService.post_invoice(
            test_organisation.id, invoice, user_id=test_user.id
        )

        lines = list(entry.lines.select_related("account"))
        ar_line = next(ln for ln in lines if "AR for" in ln.description)
        gst_line = next(ln for ln in lines if "GST Output" in ln.description)

        assert ar_line.account.code == "1200", (
            f"AR debit posted to {ar_line.account.code} {ar_line.account.name}"
        )
        assert gst_line.account.code == "2600", (
            f"Output tax posted to {gst_line.account.code} "
            f"{gst_line.account.name} (must be 2600 GST Output Tax)"
        )

    def test_non_gst_org_fails_closed_on_gst_lines(
        self, test_organisation, test_user
    ):
        """No GST control accounts seeded -> ValidationError, no journal."""
        _seed_coa(test_organisation.id, gst_registered=False)
        _fy_and_period(test_organisation)
        tax_code = _sr_tax_code(test_organisation)  # the line still carries GST
        invoice = _invoice_with_line(test_organisation, tax_code)

        with pytest.raises(ValidationError, match="GST"):
            JournalService.post_invoice(
                test_organisation.id, invoice, user_id=test_user.id
            )

        assert not JournalLine.objects.filter(
            entry__org_id=test_organisation.id
        ).exists(), "no journal line may be written when the GL account is unknown"


class TestMoneyQuantization:
    """P5/H-5: line amounts reconcile to the cent with the GST base."""

    def test_line_amount_is_the_2dp_gst_base(self, test_organisation):
        _seed_coa(test_organisation.id, gst_registered=True)
        tax_code = _sr_tax_code(test_organisation)
        contact = Contact.objects.create(
            org=test_organisation,
            contact_type="CUSTOMER",
            name="Penny Cust",
            email="p@x.sg",
        )
        document = DocumentService.create_document(
            org_id=test_organisation.id,
            document_type="SALES_INVOICE",
            contact_id=contact.id,
            issue_date=date(2024, 1, 15),
        )
        revenue = Account.objects.get(org=test_organisation, code="4000")

        # gross = 3 x 33.335 = 100.005; discount 10% = 10.0005;
        # 2dp GST base = (100.005 - 10.0005).quantize(0.01) = 90.00
        line = DocumentService.add_line(
            org_id=test_organisation.id,
            document_id=document.id,
            account_id=revenue.id,
            description="Rounding-sensitive line",
            quantity=Decimal("3"),
            unit_price=Decimal("33.335"),
            tax_code_id=tax_code.id,
            discount_pct=Decimal("10"),
        )

        assert line.line_amount == Decimal("90.00"), (
            "line_amount must equal the 2dp GST base (the amount the GST was "
            f"calculated on); got {line.line_amount}"
        )
        assert line.gst_amount == Decimal("8.10")
        assert line.total_amount == Decimal("98.10"), (
            "total must equal line_amount + gst_amount to the cent; got "
            f"{line.total_amount}"
        )


class TestLineNumbering:
    """P5/H-6: enumerate, never list.index()."""

    def test_duplicate_line_dicts_get_distinct_line_numbers(
        self, test_organisation, test_user
    ):
        _seed_coa(test_organisation.id, gst_registered=True)
        _fy_and_period(test_organisation)
        cash = Account.objects.get(org=test_organisation, code="1010")
        revenue = Account.objects.get(org=test_organisation, code="4000")

        identical = {
            "account_id": revenue.id,
            "debit": Decimal("0.00"),
            "credit": Decimal("50.00"),
            "description": "Split revenue line",
        }
        entry = JournalService.create_entry(
            org_id=test_organisation.id,
            entry_date=date(2024, 1, 15),
            source_type="MANUAL",
            narration="Duplicate line dicts",
            lines=[
                {
                    "account_id": cash.id,
                    "debit": Decimal("100.00"),
                    "credit": Decimal("0.00"),
                    "description": "Cash",
                },
                identical,
                identical,
            ],
            user_id=test_user.id,
        )

        numbers = sorted(
            JournalLine.objects.filter(entry=entry).values_list(
                "line_number", flat=True
            )
        )
        assert numbers == [1, 2, 3], (
            f"each line needs a distinct sequential number; got {numbers} "
            "(list.index() returns the first match for duplicate dicts)"
        )
