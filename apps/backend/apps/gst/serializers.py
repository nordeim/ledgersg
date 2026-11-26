"""
GST serializers for LedgerSG.

Serializers for TaxCode and GSTReturn models.
"""

from decimal import Decimal
from django.utils import timezone

from rest_framework import serializers

from apps.core.models import GSTReturn, TaxCode


class TaxCodeListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for tax code list views."""

    rate_display = serializers.SerializerMethodField()
    is_system = serializers.SerializerMethodField()

    class Meta:
        model = TaxCode
        fields = [
            "id", "code", "name", "rate", "rate_display",
            "is_gst_charged", "is_active", "is_system",
            "f5_supply_box", "f5_purchase_box", "f5_tax_box",
            "effective_from"
        ]
        read_only_fields = ["id"]

    def get_rate_display(self, obj: TaxCode) -> str:
        """Get formatted rate display."""
        if obj.rate is None:
            return "N/A"
        return f"{obj.rate * 100:.0f}%"

    def get_is_system(self, obj: TaxCode) -> bool:
        """Check if this is a system tax code (org_id is null)."""
        return obj.org_id is None


class TaxCodeDetailSerializer(serializers.ModelSerializer):
    """Detailed serializer for tax code views."""

    is_system = serializers.SerializerMethodField()

    class Meta:
        model = TaxCode
        fields = [
            "id", "code", "name", "rate", "is_gst_charged",
            "description", "is_active", "is_system",
            "f5_supply_box", "f5_purchase_box", "f5_tax_box",
            "effective_from", "effective_to",
            "created_at", "updated_at"
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def get_is_system(self, obj: TaxCode) -> bool:
        """Check if this is a system tax code (org_id is null)."""
        return obj.org_id is None


class TaxCodeCreateSerializer(serializers.Serializer):
    """Serializer for creating a tax code."""

    code = serializers.CharField(max_length=10)
    name = serializers.CharField(max_length=100)
    rate = serializers.DecimalField(
        max_digits=5, decimal_places=4,
        required=False, allow_null=True
    )
    is_gst_charged = serializers.BooleanField()
    description = serializers.CharField(max_length=500, required=False, allow_blank=True)
    f5_supply_box = serializers.IntegerField(required=False, allow_null=True)
    f5_purchase_box = serializers.IntegerField(required=False, allow_null=True)
    f5_tax_box = serializers.IntegerField(required=False, allow_null=True)

    def validate_code(self, value: str) -> str:
        """Validate tax code format."""
        value = value.upper().strip()
        if not value:
            raise serializers.ValidationError("Tax code is required.")
        if len(value) < 2:
            raise serializers.ValidationError("Tax code must be at least 2 characters.")
        return value

    def validate_rate(self, value: Decimal) -> Decimal:
        """Validate GST rate."""
        if value is not None and (value < 0 or value > 1):
            raise serializers.ValidationError("Rate must be between 0 and 1 (e.g., 0.09 for 9%).")
        return value


class TaxCodeUpdateSerializer(serializers.Serializer):
    """Serializer for updating a tax code."""

    name = serializers.CharField(max_length=100, required=False)
    rate = serializers.DecimalField(
        max_digits=5, decimal_places=4,
        required=False, allow_null=True
    )
    description = serializers.CharField(max_length=500, required=False, allow_blank=True)
    is_active = serializers.BooleanField(required=False)

    # P17/BE-M6: mirror the create path's 0..1 gate — the DB's
    # chk_rate_range must never be the first line of defense (a raw
    # CheckViolation surfaces as a 500, the exact class this repo has
    # systematically eliminated).
    def validate_rate(self, value: Decimal) -> Decimal:
        """Validate GST rate."""
        if value is not None and (value < 0 or value > 1):
            raise serializers.ValidationError(
                "Rate must be between 0 and 1 (e.g., 0.09 for 9%)."
            )
        return value


class GSTCalculationRequestSerializer(serializers.Serializer):
    """Serializer for GST calculation request."""

    amount = serializers.DecimalField(max_digits=15, decimal_places=4)
    tax_code = serializers.CharField(
        required=False,
        max_length=10,
        help_text="IRAS tax code (e.g. 'SR') — resolved to the rate in force.",
    )
    # Legacy alias: the field always held a tax CODE (never a UUID) — kept as
    # a string so existing callers are not broken by the canonical rename.
    tax_code_id = serializers.CharField(
        required=False,
        max_length=10,
        help_text="Deprecated alias of tax_code; holds the code (e.g. 'SR').",
    )
    document_date = serializers.DateField(
        required=False,
        allow_null=True,
        help_text="Resolve the rate in force on this date (default: today).",
    )
    rate = serializers.DecimalField(
        max_digits=5, decimal_places=4,
        required=False, allow_null=True
    )
    is_bcrs_deposit = serializers.BooleanField(default=False)

    def validate(self, data):
        """Validate that either a tax code or an explicit rate is provided."""
        if (
            not data.get("tax_code")
            and not data.get("tax_code_id")
            and data.get("rate") is None
        ):
            raise serializers.ValidationError(
                "Either tax_code or rate must be provided."
            )
        return data


class GSTCalculationResponseSerializer(serializers.Serializer):
    """Serializer for GST calculation response."""

    net_amount = serializers.CharField()
    gst_amount = serializers.CharField()
    total_amount = serializers.CharField()
    rate = serializers.CharField()
    is_bcrs_exempt = serializers.BooleanField()
    tax_code = serializers.CharField(required=False)


class LineGSTCalculationSerializer(serializers.Serializer):
    """Serializer for line item GST calculation."""

    id = serializers.CharField(required=False)
    amount = serializers.DecimalField(max_digits=15, decimal_places=4)
    rate = serializers.DecimalField(max_digits=5, decimal_places=4, required=False)
    is_bcrs_deposit = serializers.BooleanField(default=False)


class DocumentGSTCalculationSerializer(serializers.Serializer):
    """Serializer for document GST calculation."""

    lines = LineGSTCalculationSerializer(many=True)
    default_rate = serializers.DecimalField(
        max_digits=5, decimal_places=4,
        required=False, default=Decimal("0.09")
    )


class DocumentGSTSummarySerializer(serializers.Serializer):
    """Serializer for document GST summary."""

    lines = serializers.ListField(child=serializers.DictField())
    summary = serializers.DictField()


class GSTReturnListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for GST return list views."""

    days_until_due = serializers.SerializerMethodField()
    net_gst = serializers.SerializerMethodField()

    class Meta:
        model = GSTReturn
        fields = [
            "id", "return_type", "period_start", "period_end",
            "filing_due_date", "status", "days_until_due", "net_gst",
        ]

    def get_days_until_due(self, obj: GSTReturn) -> int:
        """Get days until due date."""
        from datetime import date
        if not obj.filing_due_date:
            return 0
        return (obj.filing_due_date - timezone.localdate()).days

    def get_net_gst(self, obj: GSTReturn) -> str:
        """Get net GST amount."""
        return str(obj.box8_net_gst or Decimal("0.00"))


class GSTReturnDetailSerializer(serializers.ModelSerializer):
    """Detailed serializer for GST return views."""

    boxes = serializers.SerializerMethodField()
    filing = serializers.SerializerMethodField()

    class Meta:
        model = GSTReturn
        fields = [
            "id", "return_type", "period_start", "period_end",
            "filing_due_date", "status", "notes",
            "boxes", "filing",
            "computed_at", "reviewed_at", "filed_at",
            "created_at", "updated_at",
        ]

    def get_boxes(self, obj: GSTReturn) -> dict:
        """Get F5 box values (IRAS convention; see return_service)."""
        return {
            "box1_std_rated_supplies": str(obj.box1_std_rated_supplies or 0),
            "box2_zero_rated_supplies": str(obj.box2_zero_rated_supplies or 0),
            "box3_exempt_supplies": str(obj.box3_exempt_supplies or 0),
            "box4_total_supplies": str(obj.box4_total_supplies or 0),
            "box5_total_taxable_purchases": str(obj.box5_total_taxable_purchases or 0),
            "box6_output_tax": str(obj.box6_output_tax or 0),
            "box7_input_tax_claimable": str(obj.box7_input_tax_claimable or 0),
            "box8_net_gst": str(obj.box8_net_gst or 0),
            "box9_imports_under_schemes": str(obj.box9_imports_under_schemes or 0),
            "box10_tourist_refund": str(obj.box10_tourist_refund or 0),
            "box11_bad_debt_relief": str(obj.box11_bad_debt_relief or 0),
            "box12_pre_reg_input_tax": str(obj.box12_pre_reg_input_tax or 0),
            "box13_total_revenue": str(obj.box13_total_revenue or 0),
            "box14_reverse_charge_supplies": str(obj.box14_reverse_charge_supplies or 0),
            "box15_electronic_marketplace": str(obj.box15_electronic_marketplace or 0),
        }

    def get_filing(self, obj: GSTReturn) -> dict:
        """Get filing information."""
        return {
            "filed_at": obj.filed_at.isoformat() if obj.filed_at else None,
            "filed_by": str(obj.filed_by_id) if obj.filed_by_id else None,
            "iras_confirmation": obj.iras_confirmation or None,
        }


class GSTReturnCreateSerializer(serializers.Serializer):
    """Serializer for creating GST return periods."""

    filing_frequency = serializers.ChoiceField(choices=["MONTHLY", "QUARTERLY"])
    start_date = serializers.DateField()
    periods = serializers.IntegerField(min_value=1, max_value=24, default=12)


class GSTReturnFileSerializer(serializers.Serializer):
    """Serializer for filing a GST return."""

    filing_reference = serializers.CharField(max_length=50, required=False, allow_blank=True)
    boxes = serializers.DictField(required=False)
    # P14/H-05b: REQUIRED (>= 10 chars at the service layer) whenever box
    # overrides are present — the evidence trail for filed figures that
    # diverge from the computed subledger.
    override_reason = serializers.CharField(
        max_length=500, required=False, allow_blank=True
    )


class GSTReturnAmendSerializer(serializers.Serializer):
    """Serializer for amending a GST return."""

    reason = serializers.CharField(max_length=500)


class GSTReturnPaymentSerializer(serializers.Serializer):
    """Serializer for recording GST payment."""

    payment_date = serializers.DateField()
    payment_amount = serializers.DecimalField(max_digits=15, decimal_places=2)
    payment_reference = serializers.CharField(max_length=100)


class F5BoxDataSerializer(serializers.Serializer):
    """Serializer for F5 box data."""

    box1_standard_rated_supplies = serializers.CharField()
    box2_zero_rated_supplies = serializers.CharField()
    box3_exempt_supplies = serializers.CharField()
    box4_total_supplies = serializers.CharField()
    box5_output_tax = serializers.CharField()
    box6_taxable_purchases = serializers.CharField()
    box7_input_tax = serializers.CharField()
    box8_net_gst = serializers.CharField()
    box9_goods_imported = serializers.CharField(required=False)
    box10_gst_imports_mg_igds = serializers.CharField(required=False)
    box11_service_imports = serializers.CharField(required=False)
    box12_output_tax_reverse_charge = serializers.CharField(required=False)
    box13_revenue = serializers.CharField()
    box14_exempt_supplies = serializers.CharField()
    box15_indicator = serializers.CharField(required=False)
