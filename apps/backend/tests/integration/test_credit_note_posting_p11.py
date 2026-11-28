"""
P11/C-1 + H-3 — credit-note accounting truth.

Credit notes post with REVERSED direction: a SALES_CREDIT_NOTE credits AR
(and debits revenue / GST-output) instead of adding another invoice-shaped
entry. Purchase credit notes mirror. The F5 computation counts posting
document types only (quotes/POs excluded, converted quotes count once) and
nets credit notes instead of adding them.
"""

from datetime import date, timedelta
from decimal import Decimal

import pytest

from apps.core.models import (
    Contact,
    DocumentSequence,
    FiscalPeriod,
    FiscalYear,
    JournalLine,
)
from apps.gst.services.calculation_service import GSTCalculationService
from apps.invoicing.services import DocumentService


@pytest.fixture
def posting_fixtures(test_organisation):
    """Sequences for every posting type + an open period covering TODAY
    (convert_quote_to_invoice posts with issue_date=date.today())."""
    for doc_type, prefix in [
        ("PURCHASE_CREDIT_NOTE", "PCN-"),
        ("PURCHASE_DEBIT_NOTE", "PDN-"),
        ("PURCHASE_ORDER", "PO-"),
    ]:
        DocumentSequence.objects.get_or_create(
            org=test_organisation, document_type=doc_type, defaults={"prefix": prefix, "next_number": 1}
        )

    today = date.today()
    fy = FiscalYear.objects.create(
        org=test_organisation,
        label=f"FY{today.year}",
        start_date=date(today.year, 1, 1),
        end_date=date(today.year, 12, 31),
        is_closed=False,
    )
    FiscalPeriod.objects.create(
        org=test_organisation,
        fiscal_year=fy,
        label=f"Period {today.month} {today.year}",
        period_number=today.month,
        start_date=date(today.year, today.month, 1),
        end_date=(date(today.year, today.month, 28) + timedelta(days=4)).replace(day=1) - timedelta(days=1),
        is_open=True,
    )
    return test_organisation


def _make_document(org, accounts, tax_codes, user, document_type, related_document=None):
    """P14/H-4 contract update: a *_CREDIT_NOTE requires (and this helper
    now carries) the related_document — the original invoice it corrects
    (same contact, within the cumulative cap)."""
    if related_document is not None:
        contact = related_document.contact
    else:
        contact = Contact.objects.create(
            org=org,
            contact_type="CUSTOMER" if document_type.startswith("SALES") else "SUPPLIER",
            name=f"CN Fixture {document_type}",
            is_customer=document_type.startswith("SALES"),
            is_supplier=not document_type.startswith("SALES"),
            is_active=True,
        )
    lines = [
        {
            "account_id": accounts["4000"].id,
            "description": "Fixture line",
            "quantity": 1,
            "unit_price": Decimal("100.00"),
            "tax_code_id": tax_codes["SR"].id,
        }
    ]
    return DocumentService.create_document(
        org_id=org.id,
        document_type=document_type,
        contact_id=contact.id,
        issue_date=date(2024, 1, 15),
        lines=lines,
        user_id=user.id,
        related_document_id=related_document.id if related_document else None,
    )


def _approve(org, document, user):
    """DRAFT -> SENT -> APPROVED (STATUS_TRANSITIONS applies to all types)."""
    DocumentService.transition_status(
        org_id=org.id, document_id=document.id, new_status="SENT", user_id=user.id
    )
    DocumentService.transition_status(
        org_id=org.id, document_id=document.id, new_status="APPROVED", user_id=user.id
    )


def _line_for(document, account_code):
    """Return (debit, credit) of the posted line bound to the given account."""
    from apps.core.models import Account

    account = Account.objects.get(org_id=document.org_id, code=account_code)
    line = JournalLine.objects.get(
        entry_id=document.journal_entry_id, account_id=account.id
    )
    return line.debit, line.credit


class TestSalesCreditNotePosting:
    @pytest.mark.django_db
    def test_sales_credit_note_reverses_ar_revenue_gst(
        self, test_organisation, test_user, test_accounts, test_tax_codes, test_fiscal_period
    ):
        """SALES_CREDIT_NOTE: Cr AR, Dr Revenue, Dr GST-output (the reversal)."""
        original = _make_document(
            test_organisation, test_accounts, test_tax_codes, test_user, "SALES_INVOICE"
        )
        doc = _make_document(
            test_organisation, test_accounts, test_tax_codes, test_user,
            "SALES_CREDIT_NOTE", related_document=original,
        )
        _approve(test_organisation, doc, test_user)
        doc.refresh_from_db()
        assert doc.status == "APPROVED"
        assert doc.journal_entry_id is not None, "credit note must post a journal entry"

        # AR (1200): the receivable is REDUCED -> credit side
        ar_debit, ar_credit = _line_for(doc, "1200")
        assert ar_credit > 0 and ar_debit == 0, (
            f"SALES_CREDIT_NOTE must CREDIT AR (got debit={ar_debit}, credit={ar_credit})"
        )

        # Revenue (4000): reduced -> debit side
        rev_debit, rev_credit = _line_for(doc, "4000")
        assert rev_debit > 0 and rev_credit == 0, (
            f"SALES_CREDIT_NOTE must DEBIT revenue (got debit={rev_debit}, credit={rev_credit})"
        )

        # GST output (2600): reduced -> debit side
        gst_debit, gst_credit = _line_for(doc, "2600")
        assert gst_debit > 0 and gst_credit == 0, (
            f"SALES_CREDIT_NOTE must DEBIT GST-output (got debit={gst_debit}, credit={gst_credit})"
        )

    @pytest.mark.django_db
    def test_sales_credit_note_entry_is_balanced(
        self, test_organisation, test_user, test_accounts, test_tax_codes, test_fiscal_period
    ):
        """The reversed entry still balances (the invariant the suite enforces)."""
        original = _make_document(
            test_organisation, test_accounts, test_tax_codes, test_user, "SALES_INVOICE"
        )
        doc = _make_document(
            test_organisation, test_accounts, test_tax_codes, test_user,
            "SALES_CREDIT_NOTE", related_document=original,
        )
        _approve(test_organisation, doc, test_user)
        doc.refresh_from_db()

        lines = JournalLine.objects.filter(entry_id=doc.journal_entry_id)
        debits = sum((line.debit for line in lines), Decimal("0"))
        credit_total = sum((line.credit for line in lines), Decimal("0"))
        assert debits == credit_total, (
            f"unbalanced credit-note entry: D={debits} C={credit_total}"
        )

    @pytest.mark.django_db
    def test_sales_invoice_keeps_invoice_direction(
        self, test_organisation, test_user, test_accounts, test_tax_codes, test_fiscal_period
    ):
        """Regression guard: SALES_INVOICE keeps Dr AR / Cr Revenue / Cr GST-output."""
        doc = _make_document(
            test_organisation, test_accounts, test_tax_codes, test_user, "SALES_INVOICE"
        )
        _approve(test_organisation, doc, test_user)
        doc.refresh_from_db()

        ar_debit, ar_credit = _line_for(doc, "1200")
        assert ar_debit > 0 and ar_credit == 0, "SALES_INVOICE must DEBIT AR"

        rev_debit, rev_credit = _line_for(doc, "4000")
        assert rev_credit > 0 and rev_debit == 0, "SALES_INVOICE must CREDIT revenue"

        gst_debit, gst_credit = _line_for(doc, "2600")
        assert gst_credit > 0 and gst_debit == 0, "SALES_INVOICE must CREDIT GST-output"


class TestPurchaseCreditNotePosting:
    @pytest.mark.django_db
    def test_purchase_credit_note_reverses_ap_expense_gst(
        self, test_organisation, test_user, test_accounts, test_tax_codes, test_fiscal_period, posting_fixtures
    ):
        """PURCHASE_CREDIT_NOTE: Dr AP, Cr expense, Cr GST-input."""
        original = _make_document(
            test_organisation, test_accounts, test_tax_codes, test_user, "PURCHASE_INVOICE"
        )
        doc = _make_document(
            test_organisation, test_accounts, test_tax_codes, test_user,
            "PURCHASE_CREDIT_NOTE", related_document=original,
        )
        _approve(test_organisation, doc, test_user)
        doc.refresh_from_db()
        assert doc.journal_entry_id is not None

        # AP (2100): the payable is REDUCED -> debit side
        ap_debit, ap_credit = _line_for(doc, "2100")
        assert ap_debit > 0 and ap_credit == 0, (
            f"PURCHASE_CREDIT_NOTE must DEBIT AP (got debit={ap_debit}, credit={ap_credit})"
        )

        # Expense/revenue line (the fixture's 4000 account): reduced -> credit side
        rev_debit, rev_credit = _line_for(doc, "4000")
        assert rev_credit > 0 and rev_debit == 0, (
            f"PURCHASE_CREDIT_NOTE must CREDIT the expense line (got debit={rev_debit}, credit={rev_credit})"
        )

        # GST input (1600): reduced -> credit side
        gst_debit, gst_credit = _line_for(doc, "1600")
        assert gst_credit > 0 and gst_debit == 0, (
            f"PURCHASE_CREDIT_NOTE must CREDIT GST-input (got debit={gst_debit}, credit={gst_credit})"
        )


class TestF5ComputationDocumentTypes:
    """P11/H-3 — get_f5_box_amounts counts posting types only + nets credit notes."""

    @pytest.mark.django_db
    def test_quotes_and_purchase_orders_never_count(
        self, test_organisation, test_user, test_accounts, test_tax_codes, test_fiscal_period
    ):
        quote = _make_document(
            test_organisation, test_accounts, test_tax_codes, test_user, "SALES_QUOTE"
        )
        # A SENT quote has status in the F5 status filter but is NOT a posting type
        DocumentService.transition_status(
            org_id=test_organisation.id, document_id=quote.id, new_status="SENT", user_id=test_user.id
        )
        boxes = GSTCalculationService.get_f5_box_amounts(
            org_id=test_organisation.id,
            period_start=date(2024, 1, 1),
            period_end=date(2024, 12, 31),
        )
        assert Decimal(boxes["box1"]) == Decimal("0.00"), (
            f"a SENT quote must NOT feed Box 1 (got {boxes['box1']})"
        )
        assert Decimal(boxes["box13"]) == Decimal("0.00"), (
            f"a SENT quote must NOT feed Box 13 (got {boxes['box13']})"
        )

    @pytest.mark.django_db
    def test_converted_quote_counts_once(
        self, test_organisation, test_user, test_accounts, test_tax_codes, test_fiscal_period, posting_fixtures
    ):
        """Quote APPROVED by conversion + the converted invoice = ONE contribution, not two.

        The window spans the quote's date (2024-01-15) AND the converted
        invoice's date (today — conversion posts with issue_date=today),
        so the pre-fix double-count (quote + invoice, same lines) is
        observable inside ONE query window."""
        quote = _make_document(
            test_organisation, test_accounts, test_tax_codes, test_user, "SALES_QUOTE"
        )
        # convert_quote_to_invoice leaves the quote APPROVED with the same lines
        converted = DocumentService.convert_quote_to_invoice(
            org_id=test_organisation.id, quote_id=quote.id, user_id=test_user.id
        )
        DocumentService.transition_status(
            org_id=test_organisation.id,
            document_id=converted.id,
            new_status="SENT",
            user_id=test_user.id,
        )
        DocumentService.transition_status(
            org_id=test_organisation.id,
            document_id=converted.id,
            new_status="APPROVED",
            user_id=test_user.id,
        )

        boxes = GSTCalculationService.get_f5_box_amounts(
            org_id=test_organisation.id,
            period_start=date(2024, 1, 1),
            period_end=date.today(),
        )
        # One line of 100.00 SR: Box 1 must be 100.00 exactly (not 200.00)
        assert Decimal(boxes["box1"]) == Decimal("100.00"), (
            f"converted quote must count once: Box 1 = {boxes['box1']} (expected 100.00)"
        )

    @pytest.mark.django_db
    def test_sales_credit_note_nets_box1_box6(
        self, test_organisation, test_user, test_accounts, test_tax_codes, test_fiscal_period
    ):
        """An invoice (100 SR) + a credit note (100 SR) nets Box 1/6/13 to zero."""
        invoice = _make_document(
            test_organisation, test_accounts, test_tax_codes, test_user, "SALES_INVOICE"
        )
        _approve(test_organisation, invoice, test_user)
        credit_note = _make_document(
            test_organisation, test_accounts, test_tax_codes, test_user,
            "SALES_CREDIT_NOTE", related_document=invoice,
        )
        _approve(test_organisation, credit_note, test_user)

        boxes = GSTCalculationService.get_f5_box_amounts(
            org_id=test_organisation.id,
            period_start=date(2024, 1, 1),
            period_end=date(2024, 12, 31),
        )
        assert Decimal(boxes["box1"]) == Decimal("0.00"), (
            f"invoice + equal credit note must net Box 1 to 0 (got {boxes['box1']})"
        )
        assert Decimal(boxes["box6"]) == Decimal("0.00"), (
            f"invoice + equal credit note must net Box 6 to 0 (got {boxes['box6']})"
        )

    @pytest.mark.django_db
    def test_sales_invoice_alone_counts_as_before(
        self, test_organisation, test_user, test_accounts, test_tax_codes, test_fiscal_period
    ):
        """Regression guard: one invoice contributes 100.00 to Box 1 and 9.00 to Box 6."""
        invoice = _make_document(
            test_organisation, test_accounts, test_tax_codes, test_user, "SALES_INVOICE"
        )
        _approve(test_organisation, invoice, test_user)

        boxes = GSTCalculationService.get_f5_box_amounts(
            org_id=test_organisation.id,
            period_start=date(2024, 1, 1),
            period_end=date(2024, 12, 31),
        )
        assert Decimal(boxes["box1"]) == Decimal("100.00"), f"Box 1 = {boxes['box1']}"
        assert Decimal(boxes["box6"]) == Decimal("9.00"), f"Box 6 = {boxes['box6']}"
        assert Decimal(boxes["box13"]) == Decimal("100.00"), f"Box 13 = {boxes['box13']}"
