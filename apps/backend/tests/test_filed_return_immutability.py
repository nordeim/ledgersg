"""
FILED F5 return immutability invariants (P14/C-2, P14/H-3).

The statutory record of what was submitted to IRAS must be immutable:
- a FILED (or AMENDED) return cannot be recomputed — not even with
  `force=true` (the pre-P14 guard's `and not force_recalculate` made
  force bypass EVERY status, regressing FILED -> COMPUTED while
  `filed_at` stayed populated)
- review_after_file is refused the same way
- corrections go through the amendment flow, never silent recompute
"""

import uuid
from datetime import date
from decimal import Decimal

import pytest

from rest_framework.exceptions import ValidationError

from apps.core.models import GSTReturn
from apps.gst.services import GSTReturnService


@pytest.fixture
def filed_return(test_organisation, test_user):
    """A return that has been computed and FILED for January 2024."""
    ret = GSTReturn.objects.create(
        org_id=test_organisation.id,
        period_start=date(2024, 1, 1),
        period_end=date(2024, 1, 31),
        filing_due_date=date(2024, 2, 29),
        status="COMPUTED",
        box1_std_rated_supplies=Decimal("1000.00"),
        box4_total_supplies=Decimal("1000.00"),
        box6_output_tax=Decimal("90.00"),
        box8_net_gst=Decimal("90.00"),
        box13_total_revenue=Decimal("1000.00"),
    )
    return GSTReturnService.file_return(
        org_id=test_organisation.id,
        return_id=ret.id,
        filed_by_id=test_user.id,
        filing_reference="IRAS-REF-001",
    )


@pytest.mark.django_db
def test_filed_return_recompute_forced_is_refused(test_organisation, filed_return):
    """RED for C-2: `?force=true` must NOT regress a FILED return."""
    with pytest.raises(ValidationError) as excinfo:
        GSTReturnService.generate_f5(
            org_id=test_organisation.id,
            return_id=filed_return.id,
            force_recalculate=True,
        )

    message = str(excinfo.value)
    assert "FILED" in message or "filed" in message.lower()

    # The row is unchanged — boxes, status, filed_at all intact.
    persisted = GSTReturn.objects.get(id=filed_return.id)
    assert persisted.status == "FILED"
    assert persisted.box1_std_rated_supplies == Decimal("1000.00")
    assert persisted.box6_output_tax == Decimal("90.00")
    assert persisted.filed_at is not None


@pytest.mark.django_db
def test_filed_return_recompute_plain_is_refused(test_organisation, filed_return):
    """C-2: the non-forced path is refused too (already true for non-DRAFT
    statuses — locked in as a regression gate)."""
    with pytest.raises(ValidationError):
        GSTReturnService.generate_f5(
            org_id=test_organisation.id,
            return_id=filed_return.id,
            force_recalculate=False,
        )


@pytest.mark.django_db
def test_amended_return_recompute_forced_is_refused(test_organisation, filed_return):
    """C-2: AMENDED returns are statutory history too."""
    filed_return.status = "AMENDED"
    filed_return.save()

    with pytest.raises(ValidationError):
        GSTReturnService.generate_f5(
            org_id=test_organisation.id,
            return_id=filed_return.id,
            force_recalculate=True,
        )


@pytest.mark.django_db
def test_filed_return_review_is_refused(test_organisation, filed_return, test_user):
    """C-2: review-after-file is refused (the statutory review happened
    before filing)."""
    with pytest.raises(ValidationError):
        GSTReturnService.review_return(
            org_id=test_organisation.id,
            return_id=filed_return.id,
            reviewed_by_id=test_user.id,
        )


@pytest.mark.django_db
def test_filed_return_filing_again_is_refused(test_organisation, filed_return, test_user):
    """C-2: double-filing is refused (FILED not in FILEABLE_STATUSES —
    locked in as a regression gate)."""
    with pytest.raises(ValidationError):
        GSTReturnService.file_return(
            org_id=test_organisation.id,
            return_id=filed_return.id,
            filed_by_id=test_user.id,
            filing_reference="IRAS-REF-002",
        )
