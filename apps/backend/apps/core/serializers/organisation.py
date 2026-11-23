"""
Organisation serializers for LedgerSG.

Serializers for Organisation, FiscalYear, FiscalPeriod, Role, and UserOrganisation.
"""

from rest_framework import serializers
from datetime import date
from typing import Optional

from apps.core.models import (
    Organisation,
    FiscalYear,
    FiscalPeriod,
    Role,
    UserOrganisation,
)


def ensure_uen_available(uen, exclude_org=None):
    """P10 (found during the live e2e gate): core.organisation.uen is
    UNIQUE at the DB level, but nothing validated it — a taken UEN surfaced
    as an unhandled IntegrityError (500) on create and both PATCH paths.
    Guard at the validation layer so it is a 400 field error instead.

    Blank UENs skip the check: the DB collides on '' too (VARCHAR UNIQUE,
    and the ORM writes '' for blank), which is a schema-modeling gap
    (multiple NULLs are allowed, multiple '' are not) — deferred to the
    debt register rather than changing the wire contract here.
    """
    if not uen:
        return
    qs = Organisation.objects.filter(uen=uen)
    if exclude_org is not None:
        qs = qs.exclude(pk=exclude_org.pk)
    if qs.exists():
        raise serializers.ValidationError(
            {"uen": "An organisation with this UEN already exists."}
        )


class OrganisationSerializer(serializers.ModelSerializer):
    """Serializer for Organisation model."""
    
    fy_start_month = serializers.IntegerField(min_value=1, max_value=12)
    
    class Meta:
        model = Organisation
        fields = [
            "id", "name", "legal_name", "uen", "entity_type",
            "gst_registered", "gst_reg_number", "gst_reg_date",
            "peppol_participant_id", "invoicenow_enabled",
            "fy_start_month", "base_currency", "is_active",
            "address_line_1", "address_line_2", "city", "postal_code", "country",
            "contact_email", "contact_phone",
            "created_at", "updated_at"
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class OrganisationCreateSerializer(serializers.Serializer):
    """Serializer for creating a new organisation."""
    
    name = serializers.CharField(max_length=255)
    legal_name = serializers.CharField(max_length=255, required=False, allow_blank=True)
    uen = serializers.CharField(max_length=20, required=False, allow_blank=True)
    entity_type = serializers.CharField(max_length=50, required=False, allow_blank=True)
    gst_registered = serializers.BooleanField(default=False)
    gst_reg_number = serializers.CharField(max_length=20, required=False, allow_blank=True)
    gst_reg_date = serializers.DateField(required=False, allow_null=True)
    fy_start_month = serializers.IntegerField(min_value=1, max_value=12, default=1)
    base_currency = serializers.CharField(max_length=3, default="SGD")
    # P7/F-3: no `address` here — the Organisation model has address_line_1/2,
    # city, postal_code, country (declaring a phantom field crashed
    # Organisation.objects.create(**kwargs) with a TypeError -> 500; the
    # PATCH path fixed the same lie in P6/F-10).
    contact_email = serializers.EmailField(required=False, allow_blank=True)
    contact_phone = serializers.CharField(max_length=50, required=False, allow_blank=True)
    
    def validate(self, data):
        """Validate GST registration fields."""
        if data.get("gst_registered"):
            if not data.get("gst_reg_number"):
                raise serializers.ValidationError(
                    {"gst_reg_number": "GST registration number is required when GST is registered."}
                )
            if not data.get("gst_reg_date"):
                raise serializers.ValidationError(
                    {"gst_reg_date": "GST registration date is required when GST is registered."}
                )

        # P10: DB-level uen UNIQUE must surface as a 400 field error, not
        # an IntegrityError 500.
        ensure_uen_available(data.get("uen"))
        return data


class GSTRegistrationSerializer(serializers.Serializer):
    """Serializer for GST registration."""
    
    gst_reg_number = serializers.CharField(max_length=20)
    gst_reg_date = serializers.DateField()
    
    def validate_gst_reg_number(self, value):
        """Validate GST registration number format."""
        # Singapore GST numbers start with 'M' followed by digits
        if not value.startswith("M"):
            raise serializers.ValidationError(
                "Singapore GST registration number must start with 'M'."
            )
        return value.upper()


class FiscalYearSerializer(serializers.ModelSerializer):
    """Serializer for FiscalYear model."""
    
    class Meta:
        model = FiscalYear
        fields = [
            "id", "label", "start_date", "end_date",
            "is_closed", "closed_at", "created_at"
        ]
        read_only_fields = ["id", "created_at", "closed_at"]


class FiscalPeriodSerializer(serializers.ModelSerializer):
    """Serializer for FiscalPeriod model."""
    
    fiscal_year = FiscalYearSerializer(read_only=True)
    
    class Meta:
        model = FiscalPeriod
        fields = [
            "id", "fiscal_year", "label", "period_number",
            "start_date", "end_date", "is_open", "created_at"
        ]
        read_only_fields = ["id", "created_at"]


class RoleSerializer(serializers.ModelSerializer):
    """Serializer for Role model."""
    
    class Meta:
        model = Role
        fields = [
            "id", "name", "description",
            "can_manage_org", "can_manage_users", "can_manage_coa",
            "can_create_invoices", "can_approve_invoices", "can_void_invoices",
            "can_create_journals", "can_manage_banking",
            "can_file_gst", "can_view_reports", "can_export_data",
            "is_system", "created_at", "updated_at"
        ]
        read_only_fields = ["id", "is_system", "created_at", "updated_at"]


class UserOrganisationSerializer(serializers.ModelSerializer):
    """Serializer for UserOrganisation model."""
    
    user_email = serializers.CharField(source="user.email", read_only=True)
    user_full_name = serializers.CharField(source="user.full_name", read_only=True)
    role_name = serializers.CharField(source="role.name", read_only=True)
    
    class Meta:
        model = UserOrganisation
        fields = [
            "id", "user_email", "user_full_name", "role", "role_name",
            "is_default", "accepted_at", "created_at"
        ]
        read_only_fields = ["id", "created_at"]


class OrganisationMemberSerializer(serializers.ModelSerializer):
    """Serializer for organisation members."""
    
    user_email = serializers.CharField(source="user.email", read_only=True)
    user_full_name = serializers.CharField(source="user.full_name", read_only=True)
    role = RoleSerializer(read_only=True)
    
    class Meta:
        model = UserOrganisation
        fields = [
            "id", "user_email", "user_full_name", "role",
            "is_default", "accepted_at", "created_at"
        ]


class OrganisationSettingsSerializer(serializers.Serializer):
    """Typed, allowlisted payload for the organisation settings PATCH
    (P7/F-10 — the pre-P7 raw setattr crashed on invalid values and let
    any member change core configuration)."""

    name = serializers.CharField(max_length=255, required=False)
    legal_name = serializers.CharField(max_length=255, required=False, allow_blank=True)
    uen = serializers.CharField(max_length=20, required=False, allow_blank=True)
    entity_type = serializers.ChoiceField(choices=Organisation.ENTITY_TYPES, required=False)
    base_currency = serializers.CharField(min_length=3, max_length=3, required=False)
    fy_start_month = serializers.IntegerField(min_value=1, max_value=12, required=False)
    gst_registered = serializers.BooleanField(required=False)
    gst_reg_number = serializers.CharField(max_length=20, required=False, allow_blank=True)
    peppol_participant_id = serializers.CharField(max_length=64, required=False, allow_blank=True)
    invoicenow_enabled = serializers.BooleanField(required=False)

    # P11/M-5: vocabulary fields become ChoiceFields (free text violated
    # the DB CHECKs with IntegrityError 500s), timezone matches the DB's
    # VARCHAR(50) (the old 63 produced DataError 500s), and GST
    # registration is consistency-checked against the instance-merged
    # effective values (chk_gst_consistency 500s otherwise).
    GST_SCHEME_CHOICES = (
        "standard", "cash", "margin", "STANDARD", "CASH", "MARGIN",
    )
    GST_FILING_FREQUENCY_CHOICES = (
        "monthly", "quarterly", "semi_annual",
        "MONTHLY", "QUARTERLY", "SEMI_ANNUAL",
    )

    gst_scheme = serializers.ChoiceField(
        choices=GST_SCHEME_CHOICES, required=False
    )
    gst_filing_frequency = serializers.ChoiceField(
        choices=GST_FILING_FREQUENCY_CHOICES, required=False
    )
    # Was max_length=63 — the schema column is VARCHAR(50).
    timezone = serializers.CharField(
        max_length=50, required=False, allow_blank=True
    )
    gst_reg_date = serializers.DateField(required=False, allow_null=True)

    def validate(self, data):
        """Re-run the GST-consistency pair on instance-merged values.

        chk_gst_consistency: gst_registered requires gst_reg_number AND
        gst_reg_date. A PATCH flipping gst_registered on must carry (or
        the instance must already hold) both.
        """
        instance = self.instance
        if instance is not None:
            effective = {
                "gst_registered": instance.gst_registered,
                "gst_reg_number": instance.gst_reg_number,
                "gst_reg_date": instance.gst_reg_date,
                "gst_scheme": instance.gst_scheme,
                "gst_filing_frequency": instance.gst_filing_frequency,
            }
            effective.update(
                {k: v for k, v in data.items() if k in effective}
            )
        else:
            effective = data

        if effective.get("gst_registered"):
            if not effective.get("gst_reg_number"):
                raise serializers.ValidationError(
                    {"gst_reg_number": "GST registration number is required when GST is registered."}
                )
            if not effective.get("gst_reg_date"):
                raise serializers.ValidationError(
                    {"gst_reg_date": "GST registration date is required when GST is registered."}
                )
        return data


class OrganisationUpdateSerializer(serializers.Serializer):
    """Typed allowlist for the organisation DETAIL PATCH (P11/M-5).

    The raw allowlist let entity_type='PTE_LTD' (DB CHECK), 
    base_currency='SGDD' (CHAR(3)) and country='SGP' (CHAR(2)) reach the
    database as IntegrityError/DataError 500s.
    """

    name = serializers.CharField(max_length=255, required=False)
    legal_name = serializers.CharField(max_length=255, required=False, allow_blank=True)
    uen = serializers.CharField(max_length=20, required=False, allow_blank=True)
    entity_type = serializers.ChoiceField(
        choices=Organisation.ENTITY_TYPES, required=False
    )
    address_line_1 = serializers.CharField(max_length=255, required=False, allow_blank=True)
    address_line_2 = serializers.CharField(max_length=255, required=False, allow_blank=True)
    city = serializers.CharField(max_length=100, required=False, allow_blank=True)
    postal_code = serializers.CharField(max_length=10, required=False, allow_blank=True)
    country = serializers.CharField(min_length=2, max_length=2, required=False)
    contact_email = serializers.EmailField(required=False, allow_blank=True)
    contact_phone = serializers.CharField(max_length=50, required=False, allow_blank=True)
    base_currency = serializers.CharField(min_length=3, max_length=3, required=False)
    peppol_participant_id = serializers.CharField(max_length=64, required=False, allow_blank=True)
    invoicenow_enabled = serializers.BooleanField(required=False)
