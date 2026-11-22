"""Aged receivables / payables service (P8/R-5).

Per-contact rows bucketed by days past due (current / 1-30 / 31-60 /
61-90 / 90+), mirroring the dashboard service's document-type and status
semantics so the aged totals reconcile with the dashboard's outstanding
figures on the same books.
"""

from datetime import date
from decimal import Decimal
from uuid import UUID

from django.db.models import F

from apps.core.models import InvoiceDocument

RECEIVABLE_TYPES = ["SALES_INVOICE", "SALES_DEBIT_NOTE"]
PAYABLE_TYPES = ["PURCHASE_INVOICE", "PURCHASE_DEBIT_NOTE"]
OUTSTANDING_STATUSES = ["APPROVED", "PARTIALLY_PAID", "OVERDUE"]

ZERO = Decimal("0.0000")


def _bucket(days_past_due: int) -> str:
    if days_past_due <= 0:
        return "current"
    if days_past_due <= 30:
        return "d1_30"
    if days_past_due <= 60:
        return "d31_60"
    if days_past_due <= 90:
        return "d61_90"
    return "d90_plus"


BUCKETS = ["current", "d1_30", "d31_60", "d61_90", "d90_plus"]


def get_aged_report(org_id: UUID, report_type: str, as_at: date) -> dict:
    """Return per-contact aged rows + totals for receivables or payables.

    Semantics mirror DashboardService.query_outstanding_receivables /
    query_outstanding_payables: document type sets, APPROVED/PARTIALLY_PAID/
    OVERDUE statuses, outstanding = total_incl - amount_paid > 0. Debit
    notes count at face value (credit-note netting needs an allocation
    model decision — registered debt).
    """
    doc_types = RECEIVABLE_TYPES if report_type == "receivables" else PAYABLE_TYPES

    docs = (
        InvoiceDocument.objects.filter(
            org_id=org_id,
            document_type__in=doc_types,
            status__in=OUTSTANDING_STATUSES,
        )
        .filter(amount_paid__lt=F("total_incl"))
        # P9/D-1: the statement is "as at" a date — a document issued after
        # that date did not exist for the report's reader and must not
        # appear (status/amount_paid stay current-state; the issue-date
        # bound removes the impossible history).
        .filter(issue_date__lte=as_at)
        .select_related("contact")
    )

    rows_by_contact: dict = {}
    for doc in docs:
        outstanding = (doc.total_incl or ZERO) - (doc.amount_paid or ZERO)
        if outstanding <= 0:
            continue
        days_past_due = (as_at - doc.due_date).days
        bucket = _bucket(days_past_due)

        row = rows_by_contact.setdefault(
            doc.contact_id,
            {
                "contact_id": str(doc.contact_id),
                "contact_name": doc.contact.name,
                "document_count": 0,
                "outstanding_total": ZERO,
                **dict.fromkeys(BUCKETS, ZERO),
            },
        )
        row["document_count"] += 1
        row["outstanding_total"] += outstanding
        row[bucket] += outstanding

    results = sorted(rows_by_contact.values(), key=lambda r: r["contact_name"].lower())

    totals = {
        "outstanding_total": ZERO,
        "document_count": 0,
        **dict.fromkeys(BUCKETS, ZERO),
    }
    for row in results:
        totals["outstanding_total"] += row["outstanding_total"]
        totals["document_count"] += row["document_count"]
        for b in BUCKETS:
            totals[b] += row[b]

    def _fmt(value: Decimal) -> str:
        return str(value.quantize(Decimal("0.0000")))

    for row in results:
        row["outstanding_total"] = _fmt(row["outstanding_total"])
        for b in BUCKETS:
            row[b] = _fmt(row[b])
    totals = {k: _fmt(v) if k != "document_count" else v for k, v in totals.items()}

    return {
        "type": report_type,
        "as_at": as_at.isoformat(),
        "results": results,
        "totals": totals,
    }
