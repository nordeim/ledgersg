"""
Monetary capacity invariants (C-1 / deferred H-03 remediation, P3 sprint).

The Singapore GST registration threshold is S$1M turnover, so a
GST-registered organisation's real numbers (F5 Box 13 revenue, >= S$1M
invoice lines, document totals, journal debits) must fit the monetary
columns. `NUMERIC(10,4)` capped every value at S$999,999.9999 (6 integer
digits) — verified live: ``numeric field overflow … less than 10^6``.

These gates fail if the monetary width ever regresses below what the
business model of the product requires.
"""

from datetime import date
from decimal import Decimal

import pytest
from django.db import connection

from apps.invoicing.services import DocumentService

DOMAIN_SCHEMAS = ("core", "coa", "gst", "journal", "invoicing", "banking", "audit")


def _create_seven_figure_document(test_organisation, test_user, test_accounts, test_tax_codes):
    """Create + approve a S$1.5M single-line invoice through the real service path."""
    from apps.core.models import Contact

    contact = Contact.objects.create(
        org=test_organisation,
        contact_type="CUSTOMER",
        name="Capacity Test Customer",
        is_customer=True,
        is_active=True,
    )

    lines = [
        {
            "account_id": test_accounts["4000"].id,  # Sales Revenue
            "description": "Equipment sale (capacity gate)",
            "quantity": Decimal("1"),
            "unit_price": Decimal("1500000.00"),
            "tax_code_id": test_tax_codes["SR"].id,
        }
    ]

    document = DocumentService.create_document(
        org_id=test_organisation.id,
        document_type="SALES_INVOICE",
        contact_id=contact.id,
        issue_date=date(2024, 1, 15),
        lines=lines,
        user_id=test_user.id,
    )
    return document


@pytest.mark.django_db
def test_document_line_accepts_seven_figure_amounts(
    test_organisation, test_user, test_accounts, test_tax_codes
):
    """A S$1.5M line must persist — NUMERIC(10,4) overflowed at 10^6 (H-03)."""
    document = _create_seven_figure_document(
        test_organisation, test_user, test_accounts, test_tax_codes
    )

    document.refresh_from_db()
    line = document.lines.order_by("line_number").first()
    assert line is not None
    assert line.line_amount == Decimal("1500000.0000")
    assert line.unit_price == Decimal("1500000.0000")


@pytest.mark.django_db
def test_approved_document_totals_and_journal_carry_seven_figures(
    test_organisation, test_user, test_accounts, test_tax_codes, test_fiscal_period
):
    """Document totals AND the posted journal lines must carry >= S$1M (H-03)."""
    document = _create_seven_figure_document(
        test_organisation, test_user, test_accounts, test_tax_codes
    )

    DocumentService.transition_status(
        org_id=test_organisation.id,
        document_id=document.id,
        new_status="SENT",
        user_id=test_user.id,
    )
    DocumentService.transition_status(
        org_id=test_organisation.id,
        document_id=document.id,
        new_status="APPROVED",
        user_id=test_user.id,
    )

    document.refresh_from_db()
    assert document.status == "APPROVED"
    assert document.total_incl >= Decimal("1500000.00")
    assert document.journal_entry_id is not None

    # journal.line debit/credit were NUMERIC(10,4) too — the AR debit must
    # carry the full gross amount (1.5M + 9% GST = 1,635,000).
    journal_lines = document.journal_entry.lines.all()
    gross = document.total_incl
    assert any(
        line.debit >= gross for line in journal_lines
    ), (
        f"No journal debit carries the gross {gross}: "
        f"{[(ln.debit, ln.credit) for ln in journal_lines]}"
    )


@pytest.mark.django_db
def test_add_line_applies_discount_pct(
    test_organisation, test_user, test_accounts, test_tax_codes
):
    """add_line must apply discount_pct server-side (authoritative calculator)."""
    from apps.core.models import Contact

    contact = Contact.objects.create(
        org=test_organisation,
        contact_type="CUSTOMER",
        name="Discount Test Customer",
        is_customer=True,
        is_active=True,
    )
    document = DocumentService.create_document(
        org_id=test_organisation.id,
        document_type="SALES_INVOICE",
        contact_id=contact.id,
        issue_date=date(2024, 1, 15),
        lines=[],
        user_id=test_user.id,
    )

    line = DocumentService.add_line(
        org_id=test_organisation.id,
        document_id=document.id,
        account_id=test_accounts["4000"].id,
        description="Discounted service",
        quantity=Decimal("10"),
        unit_price=Decimal("100.00"),
        tax_code_id=test_tax_codes["SR"].id,
        discount_pct=Decimal("10"),
    )
    line.refresh_from_db()

    # 10 x 100 with 10% discount -> gross 900, discount 100
    assert line.discount_pct == Decimal("10.00")
    assert line.discount_amount == Decimal("100.0000")
    assert line.line_amount == Decimal("900.0000")


@pytest.mark.django_db
def test_no_ten_six_monetary_columns_remain():
    """Zero NUMERIC(10,4) columns may remain in the domain schemas (H-03)."""
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT table_schema, table_name, column_name
            FROM information_schema.columns
            WHERE table_schema = ANY(%s)
              AND data_type = 'numeric'
              AND numeric_precision = 10
              AND numeric_scale = 4
            """,
            [list(DOMAIN_SCHEMAS)],
        )
        stragglers = cursor.fetchall()

    assert not stragglers, (
        f"{len(stragglers)} monetary column(s) still NUMERIC(10,4) "
        "(cap S$999,999.9999 — below the S$1M GST registration threshold): "
        + ", ".join(f"{'.'.join(row)}" for row in stragglers)
    )


@pytest.mark.django_db
def test_gst_return_boxes_widened():
    """All 15 gst.return box columns must be NUMERIC(19,4) (H-03)."""
    expected_boxes = {
        "box1_std_rated_supplies", "box2_zero_rated_supplies",
        "box3_exempt_supplies", "box4_total_supplies",
        "box5_total_taxable_purchases", "box6_output_tax",
        "box7_input_tax_claimable", "box8_net_gst",
        "box9_imports_under_schemes", "box10_tourist_refund",
        "box11_bad_debt_relief", "box12_pre_reg_input_tax",
        "box13_total_revenue", "box14_reverse_charge_supplies",
        "box15_electronic_marketplace",
    }
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT column_name, numeric_precision, numeric_scale
            FROM information_schema.columns
            WHERE table_schema = 'gst' AND table_name = 'return'
              AND column_name LIKE 'box%'
            """
        )
        rows = {name: (precision, scale) for name, precision, scale in cursor.fetchall()}

    missing = expected_boxes - set(rows)
    assert not missing, f"Missing box columns: {missing}"
    wrong = {name: shape for name, shape in rows.items() if shape != (19, 4)}
    assert not wrong, f"Box columns not NUMERIC(19,4): {wrong}"
