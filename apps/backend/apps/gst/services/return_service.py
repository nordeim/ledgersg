"""
GST Return service for LedgerSG.

Handles GST return periods and F5 form generation.

Status vocabulary (matches gst.return CHECK constraint):
    DRAFT -> COMPUTED -> REVIEWED -> FILED -> AMENDED

Field names follow the model exactly (filing_due_date, iras_confirmation,
box5_total_taxable_purchases, box6_output_tax, box7_input_tax_claimable).
"""

from calendar import monthrange
from datetime import date, timedelta
from decimal import Decimal
from typing import Any
from uuid import UUID

from django.db import transaction
from django.db.utils import IntegrityError
from django.utils import timezone

from apps.core.models import GSTReturn
from apps.gst.services.calculation_service import GSTCalculationService
from common.exceptions import ResourceNotFound, ValidationError

# Box fields on GSTReturn that a filer may override (H-12 allow-list).
# Derived boxes (4, 8) are recomputed server-side and never accepted.
OVERRIDABLE_BOX_FIELDS = frozenset({
    "box1_std_rated_supplies",
    "box2_zero_rated_supplies",
    "box3_exempt_supplies",
    "box5_total_taxable_purchases",
    "box6_output_tax",
    "box7_input_tax_claimable",
    "box9_imports_under_schemes",
    "box10_tourist_refund",
    "box11_bad_debt_relief",
    "box12_pre_reg_input_tax",
    "box13_total_revenue",
    "box14_reverse_charge_supplies",
    "box15_electronic_marketplace",
})

# Allowed transitions per the DB CHECK set (H-14).
FILEABLE_STATUSES = frozenset({"DRAFT", "COMPUTED", "REVIEWED"})


class GSTReturnService:
    """Service class for GST return operations."""

    @staticmethod
    def list_returns(
        org_id: UUID,
        status: str | None = None,
        year: int | None = None
    ) -> list[GSTReturn]:
        """
        List GST returns for an organisation.

        Args:
            org_id: Organisation ID
            status: Filter by status
            year: Filter by calendar year

        Returns:
            List of GSTReturn instances
        """
        queryset = GSTReturn.objects.filter(org_id=org_id)

        if status:
            queryset = queryset.filter(status=status)

        if year:
            queryset = queryset.filter(period_start__year=year)

        return list(queryset.order_by("-period_start"))

    @staticmethod
    def get_return(org_id: UUID, return_id: UUID) -> GSTReturn:
        """
        Get GST return by ID.

        Args:
            org_id: Organisation ID
            return_id: GST return ID

        Returns:
            GSTReturn instance
        """
        try:
            return GSTReturn.objects.get(id=return_id, org_id=org_id)
        except GSTReturn.DoesNotExist as exc:
            raise ResourceNotFound(f"GST return {return_id} not found") from exc

    @staticmethod
    def create_return_periods(
        org_id: UUID,
        filing_frequency: str,
        start_date: date,
        periods: int = 12
    ) -> list[GSTReturn]:
        """
        Create GST return periods for an organisation.

        Args:
            org_id: Organisation ID
            filing_frequency: 'MONTHLY' or 'QUARTERLY'
            start_date: First period start date
            periods: Number of periods to create

        Returns:
            List of created GSTReturn instances
        """
        if filing_frequency not in ["MONTHLY", "QUARTERLY"]:
            raise ValidationError("Filing frequency must be MONTHLY or QUARTERLY")

        created = []
        current_date = start_date

        for _ in range(periods):
            if filing_frequency == "MONTHLY":
                # Monthly period
                period_start = current_date.replace(day=1)
                last_day = monthrange(current_date.year, current_date.month)[1]
                period_end = current_date.replace(day=last_day)

                # Due date is last day of following month
                if current_date.month == 12:
                    due_date = date(current_date.year + 1, 1, 31)
                else:
                    due_date = date(current_date.year, current_date.month + 1, 1)
                    last_day_next = monthrange(due_date.year, due_date.month)[1]
                    due_date = due_date.replace(day=last_day_next)

                # Move to next month
                if current_date.month == 12:
                    current_date = date(current_date.year + 1, 1, 1)
                else:
                    current_date = date(current_date.year, current_date.month + 1, 1)

            else:  # QUARTERLY
                # Quarterly period
                quarter = (current_date.month - 1) // 3
                quarter_start_month = quarter * 3 + 1
                period_start = date(current_date.year, quarter_start_month, 1)

                quarter_end_month = quarter_start_month + 2
                last_day = monthrange(current_date.year, quarter_end_month)[1]
                period_end = date(current_date.year, quarter_end_month, last_day)

                # Due date is last day of month following quarter end
                if quarter_end_month == 12:
                    due_date = date(current_date.year + 1, 1, 31)
                else:
                    due_month = quarter_end_month + 1
                    last_day_due = monthrange(current_date.year, due_month)[1]
                    due_date = date(current_date.year, due_month, last_day_due)

                # Move to next quarter
                if quarter == 3:
                    current_date = date(current_date.year + 1, 1, 1)
                else:
                    current_date = date(current_date.year, (quarter + 1) * 3 + 1, 1)

            # Check if period already exists
            if GSTReturn.objects.filter(
                org_id=org_id,
                period_start=period_start,
                period_end=period_end
            ).exists():
                continue

            try:
                gst_return = GSTReturn.objects.create(
                    org_id=org_id,
                    period_start=period_start,
                    period_end=period_end,
                    filing_due_date=due_date,
                    status="DRAFT",
                )
            except IntegrityError:
                # P18/BE-L4: a concurrent create won the UNIQUE(org, type,
                # period_start, period_end) race between our .exists()
                # pre-check and this insert — the period exists; treat it
                # as created-by-the-other-worker and skip cleanly.
                continue
            created.append(gst_return)

        return created

    @staticmethod
    def generate_f5(
        org_id: UUID,
        return_id: UUID,
        force_recalculate: bool = False
    ) -> GSTReturn:
        """
        Generate/update F5 form for a GST return period.

        Args:
            org_id: Organisation ID
            return_id: GST return ID
            force_recalculate: Force recalculation even if already calculated

        Returns:
            Updated GSTReturn instance
        """
        # P18/BE-H1: lock the return row for the whole recompute — the
        # pre-P18 shape (plain get_return + status gate + unconditional
        # save) was a TOCTOU against the locked file_return()/amend_return():
        # a concurrent filing could commit FILED between the gate and the
        # save, and the recompute would then regress the statutory record
        # to COMPUTED while filed_at stayed populated (the P14/C-2
        # regression shape, reopened through a race).
        with transaction.atomic():
            gst_return = GSTReturn.objects.select_for_update().get(
                org_id=org_id, id=return_id
            )

            # P14/C-2: FILED/AMENDED returns are the statutory record of what
            # was submitted to IRAS — they are immutable. `force_recalculate`
            # may only refresh a pre-filing state (DRAFT/COMPUTED/REVIEWED);
            # the pre-P14 guard's `and not force_recalculate` let force bypass
            # EVERY status, regressing a FILED return to COMPUTED while
            # filed_at stayed populated. Corrections go through the amendment
            # flow (/amend/ creates a new linked version), never a silent
            # recompute of the filed row.
            if gst_return.status in ("FILED", "AMENDED"):
                raise ValidationError(
                    f"Cannot recalculate F5 for status '{gst_return.status}': the "
                    "filed return is the statutory record and is immutable. "
                    "Use the amendment flow to correct it."
                )

            # Only recalculate if in DRAFT status or forced
            if gst_return.status not in ("DRAFT", "COMPUTED") and not force_recalculate:
                raise ValidationError(
                    f"Cannot recalculate F5 for status '{gst_return.status}'. "
                    "Use force_recalculate=true to override."
                )

            # Get box amounts
            boxes = GSTCalculationService.get_f5_box_amounts(
                org_id=org_id,
                period_start=gst_return.period_start.isoformat(),
                period_end=gst_return.period_end.isoformat()
            )

            # Explicit field assignment to the REAL model columns (C-01d: the
            # old code wrote phantom attributes that save() silently discarded).
            gst_return.box1_std_rated_supplies = Decimal(boxes["box1"])
            gst_return.box2_zero_rated_supplies = Decimal(boxes["box2"])
            gst_return.box3_exempt_supplies = Decimal(boxes["box3"])
            gst_return.box4_total_supplies = Decimal(boxes["box4"])
            gst_return.box5_total_taxable_purchases = Decimal(boxes["box5"])
            gst_return.box6_output_tax = Decimal(boxes["box6"])
            gst_return.box7_input_tax_claimable = Decimal(boxes["box7"])
            gst_return.box8_net_gst = Decimal(boxes["box8"])
            gst_return.box13_total_revenue = Decimal(boxes["box13"])
            gst_return.box14_reverse_charge_supplies = Decimal(boxes["box14"])

            gst_return.status = "COMPUTED"
            gst_return.computed_at = timezone.now()
            gst_return.save()

        return gst_return

    @staticmethod
    def review_return(
        org_id: UUID,
        return_id: UUID,
        reviewed_by_id: UUID
    ) -> GSTReturn:
        """
        Mark a computed return as reviewed (COMPUTED -> REVIEWED).
        """
        # P18/BE-H1: same TOCTOU shape as generate_f5 — the COMPUTED gate
        # + save must hold the row lock, else a concurrent file_return()
        # commit lands between them and the review save overwrites FILED.
        with transaction.atomic():
            gst_return = GSTReturn.objects.select_for_update().get(
                org_id=org_id, id=return_id
            )

            if gst_return.status != "COMPUTED":
                raise ValidationError(
                    f"Cannot review return with status '{gst_return.status}'. "
                    "Only COMPUTED returns can be reviewed."
                )

            gst_return.status = "REVIEWED"
            gst_return.reviewed_at = timezone.now()
            gst_return.reviewed_by_id = reviewed_by_id
            gst_return.save()

        return gst_return

    @staticmethod
    def file_return(
        org_id: UUID,
        return_id: UUID,
        filed_by_id: UUID,
        filing_reference: str | None = None,
        boxes: dict[str, Decimal] | None = None,
        override_reason: str | None = None
    ) -> GSTReturn:
        """
        File a GST return.

        Args:
            org_id: Organisation ID
            return_id: GST return ID
            filed_by_id: User ID who filed
            filing_reference: IRAS filing reference number
            boxes: Optional override box amounts (allow-listed)
            override_reason: REQUIRED with boxes (P14/H-05b) — the evidence
                trail; persisted into notes together with the
                computed-vs-filed deltas

        Returns:
            Filed GSTReturn instance
        """
        # P14/H-05b: box NAMES are validated first (the H-12 allow-list is
        # the older contract — an unknown key must surface as an invalid-box
        # error even when the request also lacks an override reason), then
        # overrides without a real reason are refused — the filed figures
        # may legitimately diverge from the computed subledger (bad-debt
        # relief, tourist refunds, pre-registration claims), but never
        # without an evidence trail.
        if boxes:
            for box_name in boxes:
                if box_name not in OVERRIDABLE_BOX_FIELDS:
                    raise ValidationError(
                        f"Invalid box name '{box_name}'. Only F5 box "
                        "fields may be overridden."
                    )
        override_reason = (override_reason or "").strip()
        if boxes and len(override_reason) < 10:
            raise ValidationError(
                "Filing with box overrides requires an override_reason "
                "(at least 10 characters) — the evidence trail for figures "
                "that differ from the computed subledger."
            )

        with transaction.atomic():
            # P16/BE-L3: lock the return row — concurrent file/amend on the
            # same return interleaved (FILED->AMENDED->FILED re-ordering,
            # notes lost-update).
            gst_return = GSTReturn.objects.select_for_update().get(
                org_id=org_id, id=return_id
            )

            if gst_return.status not in FILEABLE_STATUSES:
                raise ValidationError(
                    f"Cannot file return with status '{gst_return.status}'"
                )

            # P14/H-05b: snapshot the computed values BEFORE the overrides
            # apply — the delta trail needs what the subledger said.
            computed_snapshot = {
                box_name: getattr(gst_return, box_name, None)
                for box_name in (boxes or {})
            }

            # Apply box overrides from a STRICT allow-list (H-12: the old
            # hasattr() check accepted org_id, id, status, filed_by... and
            # any other model attribute — a mass-assignment hole).
            if boxes:
                for box_name, value in (boxes or {}).items():
                    if box_name not in OVERRIDABLE_BOX_FIELDS:
                        raise ValidationError(
                            f"Invalid box name '{box_name}'. Only F5 box "
                            "fields may be overridden."
                        )
                    try:
                        box_value = Decimal(str(value))
                    except (TypeError, ValueError, ArithmeticError) as exc:
                        raise ValidationError(
                            f"Invalid value for '{box_name}': {value!r}"
                        ) from exc
                    # P16/BE-M2: NaN/Infinity parse cleanly out of Decimal()
                    # and PostgreSQL numeric accepts both — without this
                    # gate a non-finite value could be FILED into the
                    # statutory record.
                    if not box_value.is_finite():
                        raise ValidationError(
                            f"Invalid value for '{box_name}': {value!r} — "
                            "box values must be finite numbers"
                        )
                    setattr(gst_return, box_name, box_value)

            # P14/H-05b: persist the override evidence BEFORE the derived
            # boxes are recomputed — capture the computed-vs-filed deltas
            # while the computed values are still on the instance.
            override_trail = ""
            if boxes:
                deltas = []
                for box_name, filed_value in boxes.items():
                    computed_value = computed_snapshot.get(box_name)
                    if computed_value is not None and Decimal(str(filed_value)) != computed_value:
                        deltas.append(
                            f"{box_name}: computed={computed_value} "
                            f"filed={Decimal(str(filed_value))}"
                        )
                override_trail = (
                    f"OVERRIDE REASON: {override_reason}\n"
                    + ("\n".join(deltas) if deltas else "no material deltas vs computed")
                )

            # Derived boxes are ALWAYS recomputed server-side — the DB
            # CHECKs (chk_box4_total, chk_box8_net) enforce the identities.
            gst_return.box4_total_supplies = (
                gst_return.box1_std_rated_supplies
                + gst_return.box2_zero_rated_supplies
                + gst_return.box3_exempt_supplies
            )
            gst_return.box8_net_gst = (
                gst_return.box6_output_tax - gst_return.box7_input_tax_claimable
            )

            # Update status (H-14: 'FILED' is in the DB CHECK set; the old
            # code also wrote a phantom filing_reference column)
            gst_return.status = "FILED"
            gst_return.filed_at = timezone.now()
            gst_return.filed_by_id = filed_by_id
            gst_return.iras_confirmation = filing_reference or ""

            if override_trail:
                gst_return.notes = (
                    f"{gst_return.notes}\n{override_trail}" if gst_return.notes else override_trail
                )

            gst_return.save()

            # P5/H-3: filing changes GST liability — drop the stale dashboard
            try:
                from apps.reporting.services.dashboard_service import (
                    DashboardService,
                )

                DashboardService().invalidate_dashboard_cache(str(org_id))
            except Exception:  # noqa: BLE001 — never fail the filing
                import logging

                logging.getLogger(__name__).exception(
                    "dashboard cache invalidation failed for org %s", org_id
                )

            return gst_return

    @staticmethod
    def amend_return(
        org_id: UUID,
        return_id: UUID,
        reason: str
    ) -> GSTReturn:
        """
        Mark a filed return for amendment (FILED -> AMENDED).

        The schema has no amendment_reason column; the reason is recorded in
        `notes` (documented decision — a dedicated column requires a
        versioned schema change; see the deferred debt register).
        """
        # P16/BE-L3: lock the return row (same rationale as file_return).
        gst_return = GSTReturn.objects.select_for_update().get(
            org_id=org_id, id=return_id
        )

        if gst_return.status != "FILED":
            raise ValidationError("Only filed returns can be amended")

        if not reason or not reason.strip():
            raise ValidationError("An amendment reason is required")

        gst_return.status = "AMENDED"
        timestamp = timezone.now().strftime("%Y-%m-%d %H:%M")
        existing_notes = gst_return.notes or ""
        gst_return.notes = (
            f"{existing_notes}\n" if existing_notes else ""
        ) + f"[{timestamp}] Amendment: {reason.strip()}"
        gst_return.save()

        return gst_return

    @staticmethod
    def pay_return(
        org_id: UUID,
        return_id: UUID,
        payment_date: date,
        payment_amount: Decimal,
        payment_reference: str
    ) -> GSTReturn:
        """
        Record payment for a GST return.

        The gst.return table has NO payment columns (paid_at,
        payment_amount, payment_reference do not exist — audit H-14). The
        old implementation wrote phantom attributes that save() silently
        discarded, presenting a false record that GST had been paid.

        Until the schema extension lands (deferred debt register,
        docs/REMEDIATION_PLAN_2026-11-21.md), this method refuses rather
        than fabricating payment evidence.
        """
        raise ValidationError(
            "GST payment tracking is not implemented: gst.return has no "
            "payment columns. Recording a payment requires a schema "
            "extension (see docs/REMEDIATION_PLAN_2026-11-21.md, deferred "
            "debt register)."
        )

    @staticmethod
    def get_f5_json(org_id: UUID, return_id: UUID) -> dict[str, Any]:
        """
        Get F5 form data as JSON for API response.
        """
        gst_return = GSTReturnService.get_return(org_id, return_id)

        return {
            "id": str(gst_return.id),
            "return_type": gst_return.return_type,
            "period_start": gst_return.period_start.isoformat(),
            "period_end": gst_return.period_end.isoformat(),
            "filing_due_date": gst_return.filing_due_date.isoformat(),
            "status": gst_return.status,
            "boxes": {
                "box1_std_rated_supplies": str(gst_return.box1_std_rated_supplies),
                "box2_zero_rated_supplies": str(gst_return.box2_zero_rated_supplies),
                "box3_exempt_supplies": str(gst_return.box3_exempt_supplies),
                "box4_total_supplies": str(gst_return.box4_total_supplies),
                "box5_total_taxable_purchases": str(gst_return.box5_total_taxable_purchases),
                "box6_output_tax": str(gst_return.box6_output_tax),
                "box7_input_tax_claimable": str(gst_return.box7_input_tax_claimable),
                "box8_net_gst": str(gst_return.box8_net_gst),
                "box9_imports_under_schemes": str(gst_return.box9_imports_under_schemes),
                "box10_tourist_refund": str(gst_return.box10_tourist_refund),
                "box11_bad_debt_relief": str(gst_return.box11_bad_debt_relief),
                "box12_pre_reg_input_tax": str(gst_return.box12_pre_reg_input_tax),
                "box13_total_revenue": str(gst_return.box13_total_revenue),
                "box14_reverse_charge_supplies": str(gst_return.box14_reverse_charge_supplies),
                "box15_electronic_marketplace": str(gst_return.box15_electronic_marketplace),
            },
            "filing": {
                "filed_at": gst_return.filed_at.isoformat() if gst_return.filed_at else None,
                "filed_by": str(gst_return.filed_by_id) if gst_return.filed_by_id else None,
                "iras_confirmation": gst_return.iras_confirmation or None,
            },
        }

    @staticmethod
    def get_upcoming_deadlines(
        org_id: UUID,
        days: int = 30
    ) -> list[GSTReturn]:
        """
        Get upcoming GST filing deadlines.

        Args:
            org_id: Organisation ID
            days: Number of days to look ahead

        Returns:
            List of GSTReturn instances with upcoming deadlines
        """
        today = timezone.localdate()
        deadline = today + timedelta(days=days)

        # P11/M-11: REVIEWED is the state between compute and file — a
        # return reviewed but not yet filed was invisible to the deadline
        # banner exactly one step before the statutory deadline.
        return list(GSTReturn.objects.filter(
            org_id=org_id,
            status__in=["DRAFT", "COMPUTED", "REVIEWED"],
            filing_due_date__lte=deadline,
            filing_due_date__gte=today
        ).order_by("filing_due_date"))
