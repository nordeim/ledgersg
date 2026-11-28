"""
P16 backend contract batch 2 — serializer/service seams.

BE-M3 (B5): quantity x unit_price must fit NUMERIC(19,4) — the individual
    P14/M-4 bounds permit a 19-integer-digit product that overflows the
    column's 15 integer digits at INSERT (unhandled 500).
BE-M5 (B6): the line-ADD endpoint must forward discount_pct (the create
    path does; the same payload yielded different line amounts per
    endpoint).
BE-M6 (B7): system tax-code rows are not PATCHable — the RLS WITH CHECK
    refuses the update under the app role (InsufficientPrivilege 500);
    deactivate already refuses system rows; update must too.
BE-L3 (B9): file_return/amend_return lock the return row (concurrent
    file/amend interleave).
BE-L4 (B10): a latin-1 CSV actually imports (the pre-P16 fallback
    re-read() a consumed stream and silently imported 0 rows).
BE-L7 (B11): the org-create path stores the NORMALIZED UEN (upper),
    so the case-sensitive UNIQUE pre-check cannot be dodged.
"""

from datetime import date

import pytest

# =============================================================================
# B5 — the line-total bound
# =============================================================================

class TestLineTotalBoundP16:
    def test_in_bounds_fields_with_out_of_bounds_product_is_refused(self):
        from apps.invoicing.serializers import InvoiceLineCreateSerializer

        serializer = InvoiceLineCreateSerializer(
            data={
                "account_id": "00000000-0000-0000-0000-000000000001",
                "description": "overflow probe",
                "quantity": "1000000",
                "unit_price": "9999999999999",
                "tax_code_id": "00000000-0000-0000-0000-000000000002",
            }
        )
        assert not serializer.is_valid(), (
            "quantity x unit_price = 10^19 overflows NUMERIC(19,4)'s 15 "
            "integer digits — the serializer must bound the product (B5)"
        )
        assert "quantity" in serializer.errors or "unit_price" in serializer.errors or (
            "non_field_errors" in serializer.errors
        )

    def test_in_bounds_product_passes(self):
        from apps.invoicing.serializers import InvoiceLineCreateSerializer

        serializer = InvoiceLineCreateSerializer(
            data={
                "account_id": "00000000-0000-0000-0000-000000000001",
                "description": "max valid line",
                "quantity": "1000000",
                "unit_price": "99999999.9999",
                "tax_code_id": "00000000-0000-0000-0000-000000000002",
            }
        )
        assert serializer.is_valid(), serializer.errors


# =============================================================================
# B7 — system tax-code rows are immutable through update
# =============================================================================

class TestSystemTaxCodeUpdateRefusedP16:
    @pytest.mark.django_db
    def test_update_tax_code_refuses_system_rows(self, test_organisation, test_tax_codes):
        from apps.core.models import TaxCode
        from apps.gst.services import TaxCodeService
        from common.exceptions import ValidationError

        system_row = TaxCode.objects.filter(org_id__isnull=True, code="SR").first()
        assert system_row is not None, "the SR system band must exist"

        with pytest.raises(ValidationError, match="(?i)system"):
            TaxCodeService.update_tax_code(
                test_organisation.id, system_row.id, description="tamper"
            )

    @pytest.mark.django_db
    def test_update_tax_code_allows_org_rows(self, test_organisation, test_tax_codes):
        from apps.core.models import TaxCode
        from apps.gst.services import TaxCodeService

        org_row = TaxCode.objects.filter(org=test_organisation).first()
        if org_row is None:
            pytest.skip("no org-specific tax code seeded")
        updated = TaxCodeService.update_tax_code(
            test_organisation.id, org_row.id, description="org-owned edit"
        )
        assert updated.description == "org-owned edit"


# =============================================================================
# B11 — the normalized UEN is stored
# =============================================================================

class TestUenNormalizationStoredP16:
    @pytest.mark.django_db
    def test_org_create_stores_the_uppercase_uen(
        self, test_organisation, test_user, test_fiscal_period
    ):
        from apps.core.serializers.organisation import OrganisationCreateSerializer

        serializer = OrganisationCreateSerializer(
            data={
                "name": "Case Probe P16",
                "entity_type": "PRIVATE_LIMITED",
                "uen": "12345678a",  # lowercase — must normalize on write
                "currency": "SGD",
            },
            context={"request_user": test_user},
        )
        assert serializer.is_valid(), serializer.errors
        assert serializer.validated_data.get("uen") == "12345678A", (
            "The validated UEN must carry the normalized (upper) form — "
            "storing the raw value dodges the case-sensitive UNIQUE "
            "pre-check (B11)"
        )


# =============================================================================
# B10 — the latin-1 CSV fallback works
# =============================================================================

class TestCsvLatin1FallbackP16:
    @pytest.mark.django_db
    def test_latin1_encoded_statement_imports_rows(
        self, test_organisation, test_user, test_accounts, test_fiscal_period
    ):
        from io import BytesIO

        from apps.banking.services import ReconciliationService
        from apps.core.models import BankAccount

        bank = BankAccount.objects.create(
            org=test_organisation,
            gl_account=test_accounts["1200"],
            account_name="CSV Probe Bank",
            bank_name="Test Bank",
            account_number="001-999-001",
            currency="SGD",
            paynow_type=None,
            is_active=True,
        )
        # latin-1 bytes with an accented description (invalid utf-8)
        csv_text = (
            "transaction_date,description,amount\n"
            "2024-01-15,Paiement café latiné,150.00\n"
        )
        latin1_bytes = csv_text.encode("latin-1")
        with pytest.raises(UnicodeDecodeError):
            latin1_bytes.decode("utf-8")  # control: NOT valid utf-8

        result = ReconciliationService.import_csv(
            org_id=test_organisation.id,
            bank_account_id=bank.id,
            csv_file=BytesIO(latin1_bytes),
            user_id=test_user.id,
        )
        assert result["imported"] >= 1, (
            "A latin-1 statement must import its rows (the pre-P16 "
            "fallback re-read() a consumed stream and imported 0 rows "
            "with a success-shaped response — B10)"
        )


# =============================================================================
# B9 — file/amend lock the return row
# =============================================================================

class TestReturnRowLockP16:
    @pytest.mark.django_db
    def test_file_return_locks_the_return_row(self, test_organisation, test_user):
        from unittest.mock import patch

        from apps.core.models import GSTReturn
        from apps.gst.services import GSTReturnService

        gst_return = GSTReturn.objects.create(
            org=test_organisation,
            return_type="F5",
            period_start=date(2024, 1, 1),
            period_end=date(2024, 1, 31),
            filing_due_date=date(2024, 2, 29),
            status="REVIEWED",
        )
        with patch.object(
            GSTReturn.objects,
            "select_for_update",
            wraps=GSTReturn.objects.select_for_update,
        ) as spy:
            try:
                GSTReturnService.file_return(
                    org_id=test_organisation.id,
                    return_id=gst_return.id,
                    filed_by_id=test_user.id,
                )
            except Exception:
                # A filing failure (missing boxes etc.) is fine — the probe
                # asserts the LOCKED read, not a successful filing.
                pass
            assert spy.called, (
                "file_return must select_for_update() the return row "
                "(B9: concurrent file/amend interleave)"
            )
