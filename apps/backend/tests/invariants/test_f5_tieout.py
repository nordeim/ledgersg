"""
GST F5 tie-out invariants (C-01 / H-14 remediation).

Treats the F5 as a statement that must tie out (statement-auditor
discipline): for a fixed fixture of documents, the persisted return must
satisfy the IRAS identities:

    Box 4 == Box 1 + Box 2 + Box 3
    Box 8 == Box 6 - Box 7
    Box 7 excludes non-claimable input tax (TX-E, BL)
    VOID documents, BCRS deposits and foreign-org documents are excluded
"""

import uuid
from datetime import date
from decimal import Decimal

import pytest

from apps.core.models import (
    GSTReturn,
    InvoiceDocument,
    InvoiceLine,
    TaxCode,
)
from apps.gst.services import GSTReturnService
from tests.conftest import create_test_contact


def _tax_code(org, **kwargs):
    code = kwargs.pop("code")
    defaults = {
        "org": org,
        "code": code,
        "name": code,
        "description": code,
        "rate": Decimal("0.09"),
        "is_gst_charged": True,
        "is_input": False,
        "is_output": True,
        "is_claimable": True,
        "is_active": True,
        "effective_from": date(2024, 1, 1),
    }
    defaults.update(kwargs)
    return TaxCode.objects.create(**defaults)


@pytest.fixture
def f5_fixture(test_organisation, test_accounts, test_fiscal_period):
    """Tax codes + documents covering every F5 box rule."""
    org = test_organisation

    sr = _tax_code(org, code=f"SR{uuid.uuid4().hex[:4]}", f5_supply_box=1, f5_tax_box=6)
    zr = _tax_code(org, code=f"ZR{uuid.uuid4().hex[:4]}", rate=Decimal("0.00"),
                   f5_supply_box=2, f5_tax_box=6)
    es = _tax_code(org, code=f"ES{uuid.uuid4().hex[:4]}", rate=Decimal("0.00"),
                   is_gst_charged=False, f5_supply_box=3)
    tx = _tax_code(org, code=f"TX{uuid.uuid4().hex[:4]}", is_input=True, is_output=False,
                   f5_purchase_box=5, f5_tax_box=7)
    txe = _tax_code(org, code=f"TE{uuid.uuid4().hex[:4]}", is_input=True, is_output=False,
                    is_claimable=False, f5_purchase_box=5)

    contact = create_test_contact(org)

    doc_line_counters: dict = {}

    def _doc(doc_type, status, number):
        doc = InvoiceDocument.objects.create(
            org=org,
            document_type=doc_type,
            contact=contact,
            document_number=number,
            issue_date=date(2024, 1, 10),
            due_date=date(2024, 2, 10),
            status=status,
        )
        doc_line_counters[doc.id] = 0
        return doc

    def _line(doc, tax_code, amount, gst, bcrs=False):
        doc_line_counters[doc.id] += 1
        InvoiceLine.objects.create(
            org=org,
            document=doc,
            line_number=doc_line_counters[doc.id],
            description="line",
            account=test_accounts["4000"],
            quantity=Decimal("1"),
            unit_price=amount,
            tax_code=tax_code,
            tax_rate=tax_code.rate,
            line_amount=amount,
            gst_amount=gst,
            total_amount=amount + gst,
            is_bcrs_deposit=bcrs,
        )

    # Sales side
    sales = _doc("SALES_INVOICE", "APPROVED", "INV-F5-001")
    _line(sales, sr, Decimal("100.00"), Decimal("9.00"))
    _line(sales, zr, Decimal("1000.00"), Decimal("0.00"))  # zero-rated
    _line(sales, es, Decimal("500.00"), Decimal("0.00"))   # exempt

    # BCRS deposit line: out of scope for GST — excluded from every box
    bcrs_doc = _doc("SALES_INVOICE", "APPROVED", "INV-F5-002")
    _line(bcrs_doc, sr, Decimal("77.00"), Decimal("0.00"), bcrs=True)

    # Purchase side
    purchase = _doc("PURCHASE_INVOICE", "APPROVED", "PUR-F5-001")
    _line(purchase, tx, Decimal("200.00"), Decimal("18.00"))
    _line(purchase, txe, Decimal("50.00"), Decimal("4.50"))  # NOT claimable

    # VOID document: excluded
    void_doc = _doc("SALES_INVOICE", "VOID", "INV-F5-VOID")
    void_doc.voided_at = date(2024, 1, 20)
    void_doc.void_reason = "test void"
    void_doc.save()
    _line(void_doc, sr, Decimal("9999.00"), Decimal("900.00"))

    # DRAFT document: excluded
    draft_doc = _doc("SALES_INVOICE", "DRAFT", "INV-F5-DRAFT")
    _line(draft_doc, sr, Decimal("8888.00"), Decimal("800.00"))

    return {
        "sr": sr, "zr": zr, "es": es, "tx": tx, "txe": txe,
        "sales": sales, "purchase": purchase,
    }


@pytest.fixture
def gst_return_period(test_organisation):
    return GSTReturn.objects.create(
        org_id=test_organisation.id,
        period_start=date(2024, 1, 1),
        period_end=date(2024, 1, 31),
        filing_due_date=date(2024, 2, 29),
        status="DRAFT",
    )


@pytest.mark.django_db
def test_generate_f5_persists_correct_boxes(
    test_organisation, f5_fixture, gst_return_period
):
    """RED for C-01: generate_f5 must persist IRAS-correct box values."""
    result = GSTReturnService.generate_f5(
        org_id=test_organisation.id, return_id=gst_return_period.id
    )

    # Re-fetch from DB — the persisted values are what matter (the old code
    # wrote phantom attributes and silently discarded them)
    persisted = GSTReturn.objects.get(id=gst_return_period.id)

    # Supplies (net of GST)
    assert persisted.box1_std_rated_supplies == Decimal("100.00")
    assert persisted.box2_zero_rated_supplies == Decimal("1000.00")
    assert persisted.box3_exempt_supplies == Decimal("500.00")
    assert persisted.box4_total_supplies == Decimal("1600.00")  # 1+2+3

    # Purchases: total taxable purchases includes the denied TX-E amount
    assert persisted.box5_total_taxable_purchases == Decimal("250.00")

    # Output tax (SR only — ZR/ES have no output tax)
    assert persisted.box6_output_tax == Decimal("9.00")

    # Input tax claimable: TX only — TX-E is_claimable=FALSE must be excluded
    assert persisted.box7_input_tax_claimable == Decimal("18.00")

    # Net GST = Box 6 - Box 7
    assert persisted.box8_net_gst == Decimal("-9.00")

    # Total revenue == Box 4
    assert persisted.box13_total_revenue == Decimal("1600.00")

    # Reverse charge: no reverse-charge tax codes in the fixture
    assert persisted.box14_reverse_charge_supplies == Decimal("0")

    assert persisted.status == "COMPUTED"
    assert persisted.computed_at is not None

    # The returned instance must agree with the persisted one
    assert result.box8_net_gst == persisted.box8_net_gst


@pytest.mark.django_db
def test_f5_tie_out_identities(test_organisation, f5_fixture, gst_return_period):
    """Box identities enforced by the DB CHECKs must hold after generation."""
    GSTReturnService.generate_f5(
        org_id=test_organisation.id, return_id=gst_return_period.id
    )
    persisted = GSTReturn.objects.get(id=gst_return_period.id)

    assert persisted.box4_total_supplies == (
        persisted.box1_std_rated_supplies
        + persisted.box2_zero_rated_supplies
        + persisted.box3_exempt_supplies
    )
    assert persisted.box8_net_gst == (
        persisted.box6_output_tax - persisted.box7_input_tax_claimable
    )


@pytest.mark.django_db
def test_file_return_rejects_unknown_box_keys(
    test_user, test_organisation, f5_fixture, gst_return_period
):
    """RED for H-12: the boxes dict must be allow-listed — org_id must be rejected."""
    from common.exceptions import ValidationError as LedgerSGValidationError

    GSTReturnService.generate_f5(
        org_id=test_organisation.id, return_id=gst_return_period.id
    )

    with pytest.raises(LedgerSGValidationError, match="[Ii]nvalid box"):
        GSTReturnService.file_return(
            org_id=test_organisation.id,
            return_id=gst_return_period.id,
            filed_by_id=test_user.id,
            filing_reference="IRAS-REF-1",
            boxes={"org_id": "00000000-0000-0000-0000-000000000000"},
        )


@pytest.mark.django_db
def test_gst_return_state_machine(
    test_user, test_organisation, f5_fixture, gst_return_period
):
    """RED for H-14: DRAFT→COMPUTED→REVIEWED→FILED→AMENDED must all persist."""
    ret = GSTReturnService.generate_f5(
        org_id=test_organisation.id, return_id=gst_return_period.id
    )
    assert ret.status == "COMPUTED"

    ret = GSTReturnService.review_return(
        org_id=test_organisation.id, return_id=ret.id, reviewed_by_id=test_user.id
    )
    assert ret.status == "REVIEWED"
    assert ret.reviewed_at is not None

    ret = GSTReturnService.file_return(
        org_id=test_organisation.id,
        return_id=ret.id,
        filed_by_id=test_user.id,
        filing_reference="IRAS-CONF-42",
    )
    assert ret.status == "FILED"
    assert ret.filed_at is not None
    assert ret.iras_confirmation == "IRAS-CONF-42"

    ret = GSTReturnService.amend_return(
        org_id=test_organisation.id, return_id=ret.id, reason="Box 1 typo"
    )
    assert ret.status == "AMENDED"
    assert "Box 1 typo" in (ret.notes or "")


@pytest.mark.django_db
def test_gst_return_serializers_do_not_raise(
    test_organisation, f5_fixture, gst_return_period
):
    """RED for C-01f: list/detail serializers must read .data without ImproperlyConfigured."""
    from apps.gst.serializers import GSTReturnDetailSerializer, GSTReturnListSerializer

    GSTReturnService.generate_f5(
        org_id=test_organisation.id, return_id=gst_return_period.id
    )
    ret = GSTReturn.objects.get(id=gst_return_period.id)

    list_data = GSTReturnListSerializer(ret).data
    assert "filing_due_date" in list_data
    assert "period_start" in list_data

    detail_data = GSTReturnDetailSerializer(ret).data
    assert "boxes" in detail_data
    assert detail_data["boxes"]["box8_net_gst"] is not None
