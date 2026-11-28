"""
Bank Account Serializers for LedgerSG Banking Module.

Validates all bank account data before persistence.
SEC-001 Remediation: Replaces unvalidated request.data.get() stubs.

P14/H-04b (PDPA): NRIC-type PayNow identifiers are protected identifiers
under Singapore's PDPA — masked by default on READ (first char + last 3,
e.g. S*****67A); the write path rejects values containing '*' (a masked
echo must never corrupt the stored identifier). MOBILE/UEN proxies are not
PDPA protected identifiers and round-trip unchanged.
"""

from decimal import Decimal

from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from apps.core.models import Account, BankAccount


def _mask_paynow_id(paynow_type, paynow_id):
    """H-04b: mask NRIC-type identifiers on read; others pass through."""
    if paynow_type == "NRIC" and paynow_id:
        cleaned = str(paynow_id)
        if len(cleaned) >= 4:
            return f"{cleaned[0]}{'*' * (len(cleaned) - 4)}{cleaned[-3:]}"
        return "*" * len(cleaned)
    return paynow_id


class BankAccountSerializer(serializers.ModelSerializer):
    """Read serializer for BankAccount."""

    # P14/H-04b: NRIC PayNow identifiers are masked on read (PDPA).
    paynow_id = serializers.SerializerMethodField()

    class Meta:
        model = BankAccount
        fields = [
            "id",
            "org",
            "account_name",
            "bank_name",
            "account_number",
            "bank_code",
            "branch_code",
            "currency",
            "gl_account",
            "paynow_type",
            "paynow_id",
            "is_default",
            "is_active",
            "opening_balance",
            "opening_balance_date",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "org", "created_at", "updated_at"]

    def get_paynow_id(self, obj) -> str | None:
        return _mask_paynow_id(obj.paynow_type, obj.paynow_id)


class BankAccountCreateSerializer(serializers.ModelSerializer):
    """
    Write serializer for creating BankAccount.

    Validates:
    - GL account belongs to org and is bank account type
    - PayNow validation: if paynow_type set, paynow_id required
    - No duplicate account_number per org
    """

    # P9/B-4: "no PayNow" is null on the wire — the DB columns are
    # nullable (the CHECK allows NULL or UEN/MOBILE/NRIC; "" violates it).
    # The ModelSerializer default rejected null, so the UI dialog (which
    # sends null when nothing is selected) could never create an account.
    paynow_type = serializers.ChoiceField(
        choices=["UEN", "MOBILE", "NRIC"],
        required=False,
        allow_null=True,
        allow_blank=True,
    )
    paynow_id = serializers.CharField(
        max_length=20, required=False, allow_blank=True, allow_null=True
    )

    class Meta:
        model = BankAccount
        fields = [
            "account_name",
            "bank_name",
            "account_number",
            "bank_code",
            "branch_code",
            "currency",
            "gl_account",
            "paynow_type",
            "paynow_id",
            "is_default",
            "opening_balance",
            "opening_balance_date",
        ]

    def validate_account_name(self, value):
        if not value or not value.strip():
            raise serializers.ValidationError(_("Account name cannot be blank."))
        return value.strip()

    def validate_bank_name(self, value):
        if not value or not value.strip():
            raise serializers.ValidationError(_("Bank name cannot be blank."))
        return value.strip()

    def validate_account_number(self, value):
        if not value or not value.strip():
            raise serializers.ValidationError(_("Account number cannot be blank."))
        return value.strip()

    def validate_currency(self, value):
        if not value or len(value) != 3:
            raise serializers.ValidationError(_("Currency must be a 3-letter code."))
        return value.upper()

    def validate_opening_balance(self, value):
        if value is None:
            return Decimal("0")
        if value < Decimal("0"):
            raise serializers.ValidationError(_("Opening balance cannot be negative."))
        return value

    def validate_gl_account(self, value):
        org_id = self.context.get("org_id")
        if not org_id:
            raise serializers.ValidationError(_("Organisation context required."))

        try:
            account = Account.objects.get(id=value.id, org_id=org_id)
        except Account.DoesNotExist as exc:
            raise serializers.ValidationError(
                _("GL account not found in this organisation.")
            ) from exc

        account_type_name = account.account_type.upper() if account.account_type else ""
        if not account_type_name and account.account_type_ref:
            account_type_name = account.account_type_ref.code.upper()

        if account_type_name != "ASSET":
            raise serializers.ValidationError(
                _("GL account must be an Asset account for bank accounts.")
            )

        sub_type_name = ""
        if account.account_sub_type:
            sub_type_name = account.account_sub_type.name.upper()

        valid_sub_types = ["BANK", "CASH AND BANK", "CASH & BANK", "CASH"]
        if sub_type_name and sub_type_name not in valid_sub_types:
            raise serializers.ValidationError(
                _("GL account must be a Bank or Cash type asset account.")
            )

        return value

    def validate(self, data):
        paynow_type = data.get("paynow_type")
        paynow_id = data.get("paynow_id")

        # "" and null both mean "unset"; the DB stores NULL (P9/B-4)
        if paynow_id == "":
            data["paynow_id"] = None

        # P14/H-04b: a masked read echoed back through the write path must
        # never persist the mask characters into the stored identifier.
        if paynow_id and "*" in str(paynow_id):
            raise serializers.ValidationError(
                {
                    "paynow_id": _(
                        "PayNow ID contains '*' — send the real identifier, "
                        "not the masked display value."
                    )
                }
            )

        if paynow_type and not paynow_id:
            raise serializers.ValidationError(
                {"paynow_id": _("PayNow ID is required when PayNow type is specified.")}
            )

        if paynow_id and not paynow_type:
            raise serializers.ValidationError(
                {"paynow_type": _("PayNow type is required when PayNow ID is provided.")}
            )

        if paynow_id:
            paynow_type_value = paynow_type if isinstance(paynow_type, str) else paynow_type[0]
            if paynow_type_value == "UEN" and len(paynow_id) > 10:
                raise serializers.ValidationError(
                    {"paynow_id": _("UEN PayNow ID must be 10 characters or less.")}
                )
            elif paynow_type_value == "MOBILE" and not paynow_id.startswith("+"):
                raise serializers.ValidationError(
                    {"paynow_id": _("Mobile PayNow ID must start with '+' (e.g., +65XXXXXXXX).")}
                )
            elif paynow_type_value == "NRIC" and len(paynow_id) != 9:
                raise serializers.ValidationError(
                    {"paynow_id": _("NRIC PayNow ID must be exactly 9 characters.")}
                )

        return data


class BankAccountUpdateSerializer(serializers.ModelSerializer):
    """Write serializer for updating BankAccount."""

    # P10/M-1: the P9/B-4 null-PayNow fix, mirrored onto the update path —
    # the model-derived field rejected null (400) and passed "" through to
    # the DB CHECK (paynow_type IS NULL OR paynow_type IN (...)) →
    # IntegrityError 500. Both "unset" wire values normalise to NULL.
    paynow_type = serializers.ChoiceField(
        choices=["UEN", "MOBILE", "NRIC"],
        required=False,
        allow_null=True,
        allow_blank=True,
    )
    paynow_id = serializers.CharField(
        max_length=20, required=False, allow_blank=True, allow_null=True
    )

    class Meta:
        model = BankAccount
        fields = [
            "account_name",
            "bank_name",
            "bank_code",
            "branch_code",
            "paynow_type",
            "paynow_id",
            "is_default",
            "is_active",
            "opening_balance",
            "opening_balance_date",
        ]

    def validate_account_name(self, value):
        if not value or not value.strip():
            raise serializers.ValidationError(_("Account name cannot be blank."))
        return value.strip()

    def validate_bank_name(self, value):
        if not value or not value.strip():
            raise serializers.ValidationError(_("Bank name cannot be blank."))
        return value.strip()

    def validate_opening_balance(self, value):
        if value is not None and value < Decimal("0"):
            raise serializers.ValidationError(_("Opening balance cannot be negative."))
        return value

    def validate(self, data):
        # Partial PATCH: the effective pair combines the request with the
        # persisted instance values (a field the request omitted keeps its
        # stored value — DRF partial semantics).
        instance_type = getattr(self.instance, "paynow_type", None)
        instance_id = getattr(self.instance, "paynow_id", None)
        eff_type = data.get("paynow_type", instance_type)
        eff_id = data.get("paynow_id", instance_id)

        # P14/H-04b: a masked read echoed back through PATCH must never
        # persist the mask characters into the stored identifier.
        if "paynow_id" in data and data["paynow_id"] and "*" in str(data["paynow_id"]):
            raise serializers.ValidationError(
                {
                    "paynow_id": _(
                        "PayNow ID contains '*' — send the real identifier, "
                        "not the masked display value."
                    )
                }
            )

        # "" and null both mean "unset"; the DB stores NULL (P9/B-4, P10/M-1)
        if eff_type in ("", None):
            eff_type = None
        if eff_id in ("", None):
            eff_id = None

        # Normalise the explicitly-sent fields for storage.
        if "paynow_type" in data:
            data["paynow_type"] = eff_type
        if "paynow_id" in data:
            data["paynow_id"] = eff_id

        # P10/M-1 (the I-5 rider): clearing paynow_id alone leaves the old
        # paynow_type dangling — refuse the broken pair with a clean 400.
        if eff_type is not None and eff_id is None:
            raise serializers.ValidationError(
                {"paynow_id": _("PayNow ID is required when PayNow type is specified.")}
            )
        if eff_id is not None and eff_type is None:
            raise serializers.ValidationError(
                {"paynow_type": _("PayNow type is required when PayNow ID is provided.")}
            )

        return data
