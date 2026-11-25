"""
P14/M-4 + M-1 — document-input hardening and identity validators.

M-4: malformed document input must produce 400s, never 500s. The
pre-P14 create serializer accepted `lines: ListField(child=DictField(),
required=False)` — no line-item schema, no bounds; the view's
`data["lines"]` KeyError'd on a missing field (500), a negative
unit_price or a 10^15 magnitude crashed deeper in.

M-1 (+ audit-2 H-02): UEN validation covers the three real ACRA formats
(the pre-P14 regexes included the invalid bare ^\d{10}$ — not a UEN —
and mislabeled the others); GST registration numbers accept BOTH the
M-form (M + 8 digits + check letter) and the UEN-form (the org
serializer's startswith("M") rejected valid UEN-form GST numbers).
Format validation only — no invented checksums (the official ACRA
check-letter algorithm is not a published spec; guessing one would
reject valid numbers — registered as a P15 decision).
"""

import uuid
from datetime import date

import pytest
from rest_framework import serializers as drf_serializers

from apps.invoicing.serializers import InvoiceDocumentCreateSerializer
from apps.invoicing.services.contact_service import ContactService
from apps.core.validators import validate_uen, validate_gst_reg_number
from tests.conftest import create_test_contact


# ── M-4: the document create contract ────────────────────────────────────

class TestDocumentCreateContractP14:
    def _payload(self, fx, lines):
        return {
            "document_type": "SALES_INVOICE",
            "contact_id": str(fx["contact"].id),
            "issue_date": date(2024, 3, 10).isoformat(),
            "lines": lines,
        }

    def _line(self, fx, **overrides):
        line = {
            "account_id": str(fx["accounts"]["4000"].id),
            "description": "probe line",
            "quantity": "1.0000",
            "unit_price": "100.00",
            "tax_code_id": str(fx["tax_codes"]["SR"].id),
        }
        line.update(overrides)
        return line

    @pytest.fixture
    def fx(self, test_organisation, test_user, test_accounts, test_tax_codes, test_fiscal_period):
        contact = create_test_contact(test_organisation, is_customer=True)
        return {"org": test_organisation, "contact": contact, "accounts": test_accounts, "tax_codes": test_tax_codes}

    def test_missing_lines_is_a_400(self, fx):
        """RED for M-4: no `lines` key → 400 (was KeyError → 500 in the view)."""
        data = {
            "document_type": "SALES_INVOICE",
            "contact_id": str(fx["contact"].id),
            "issue_date": date(2024, 3, 10).isoformat(),
        }
        serializer = InvoiceDocumentCreateSerializer(data=data)
        with pytest.raises(drf_serializers.ValidationError):
            serializer.is_valid(raise_exception=True)

    def test_empty_lines_list_is_a_400(self, fx):
        """M-4: a document needs at least one line."""
        serializer = InvoiceDocumentCreateSerializer(data=self._payload(fx, []))
        with pytest.raises(drf_serializers.ValidationError):
            serializer.is_valid(raise_exception=True)

    def test_negative_unit_price_is_a_400(self, fx):
        serializer = InvoiceDocumentCreateSerializer(
            data=self._payload(fx, [self._line(fx, unit_price="-100.00")])
        )
        with pytest.raises(drf_serializers.ValidationError):
            serializer.is_valid(raise_exception=True)

    def test_huge_unit_price_is_a_400(self, fx):
        serializer = InvoiceDocumentCreateSerializer(
            data=self._payload(fx, [self._line(fx, unit_price="9999999999999999")])
        )
        with pytest.raises(drf_serializers.ValidationError):
            serializer.is_valid(raise_exception=True)

    def test_zero_quantity_is_a_400(self, fx):
        serializer = InvoiceDocumentCreateSerializer(
            data=self._payload(fx, [self._line(fx, quantity="0")])
        )
        with pytest.raises(drf_serializers.ValidationError):
            serializer.is_valid(raise_exception=True)

    def test_line_missing_account_is_a_400(self, fx):
        line = self._line(fx)
        del line["account_id"]
        serializer = InvoiceDocumentCreateSerializer(data=self._payload(fx, [line]))
        with pytest.raises(drf_serializers.ValidationError):
            serializer.is_valid(raise_exception=True)

    def test_valid_payload_passes(self, fx):
        serializer = InvoiceDocumentCreateSerializer(data=self._payload(fx, [self._line(fx)]))
        assert serializer.is_valid(), serializer.errors
        assert len(serializer.validated_data["lines"]) == 1


# ── M-1: the UEN / GST-number validators ─────────────────────────────────

@pytest.mark.parametrize(
    "uen,valid",
    [
        ("12345678A", True),      # business (ROB): 8 digits + check letter
        ("53001234K", True),      # business form
        ("202612345D", True),     # local company: 9 digits + check letter
        ("T08LL1234A", True),     # other entities: T/S + YY + 2 letters + 4 digits + letter
        ("S18FC0001B", True),     # other entities (S prefix)
        ("123456789", False),     # bare digits — not a UEN
        ("123456789012", False),  # too long
        ("12345", False),         # too short
        ("1234567A", False),      # 7 digits + letter — too short
        ("123456789AB", False),   # 11 chars
        ("1234567890", False),    # the bare ^\d{10}$ branch — NOT a UEN (branch registrations)
        ("GARBAGE!!", False),
    ],
)
def test_uen_format_validation(uen, valid):
    assert validate_uen(uen) is valid, f"UEN {uen!r} should be {'valid' if valid else 'invalid'}"


@pytest.mark.parametrize(
    "gst,valid",
    [
        ("M90345678K", True),     # M-form: M + 8 digits + check letter
        ("M1234567A", True),
        ("202612345D", True),     # UEN-form GST number (valid — the old check REJECTED these)
        ("12345678A", True),
        ("M1234567", False),      # missing check letter
        ("X1234567A", False),     # wrong prefix for M-form and not a UEN form
        ("M12345678", False),
        ("garbage", False),
    ],
)
def test_gst_reg_number_validation(gst, valid):
    assert validate_gst_reg_number(gst) is valid, f"GST {gst!r} should be {'valid' if valid else 'invalid'}"


class TestContactUenValidatorP14:
    @pytest.mark.django_db
    def test_contact_uen_uses_the_real_formats(self, test_organisation):
        """M-1: ContactService._validate_uen now delegates to the honest
        validator (the bare 10-digit branch is gone)."""
        assert ContactService._validate_uen("12345678A") is True
        assert ContactService._validate_uen("1234567890") is False

    @pytest.mark.django_db
    def test_org_serializer_accepts_uen_form_gst_number(self, test_organisation):
        """M-1: the register/update serializer accepts UEN-form GST numbers."""
        from apps.core.serializers.organisation import OrganisationUpdateSerializer

        serializer = OrganisationUpdateSerializer(
            data={"gst_reg_number": "202612345D"}, partial=True
        )
        # validation of the field alone
        field = serializer.fields["gst_reg_number"]
        assert field.run_validation("202612345D") == "202612345D"
