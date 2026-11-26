"""
P14/H-3 — the GST period lock.

A FILED (or AMENDED) GST return fixes the statutory figures for its
period: once filed, no posting may change the ledger basis inside that
period. This module provides the single shared guard used by every
posting path (document approve/void, manual journal creation, payment
void) so the ledger can never silently diverge from what was filed.

Design note: the lock is DERIVED (a runtime check against FILED/AMENDED
returns covering the date) rather than a persisted flag — no schema
change, no enum churn, and it stays correct for backdated filings. A
DB-trigger enforcement layer is the registered P15 hardening item.
"""

from datetime import date
from uuid import UUID

from apps.core.models import GSTReturn
from common.exceptions import ValidationError


def assert_not_gst_locked(org_id: UUID, the_date: date) -> None:
    """Refuse (ValidationError) when a FILED/AMENDED GST return covers
    the_date for this organisation.

    The error is a 409-grade contract violation surfaced through the
    typed envelope: corrections to a filed period go through the F5
    amendment flow / IRAS voluntary disclosure, never back-posting.
    """
    locked = GSTReturn.objects.filter(
        org_id=org_id,
        status__in=("FILED", "AMENDED"),
        period_start__lte=the_date,
        period_end__gte=the_date,
    ).exists()

    if locked:
        raise ValidationError(
            f"The period containing {the_date} is GST-locked: an F5 return "
            "covering it has already been filed. Corrections must go through "
            "the F5 amendment flow, not back-dated postings."
        )
