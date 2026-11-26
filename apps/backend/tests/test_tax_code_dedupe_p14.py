"""
P14/M-10 — tax-code listing dedupes org rows over system rows.

Pre-P14, `list_tax_codes` without `effective_on` returned every history row
for both scopes: a seeded org saw the SAME code repeated (system row + the
org copy seeded at registration), so UI dropdowns showed duplicates. The
dedupe per (code, effective_from, effective_to): the org row shadows the
system row with the identical band. Rate HISTORY stays intact — the SR
code's 2007/2023/2024 bands are legitimate distinct bands, not duplicates.
"""

from datetime import date
from decimal import Decimal

import pytest

from apps.core.models import TaxCode
from apps.gst.services.tax_code_service import TaxCodeService


def _band(org, code, rate, effective_from, effective_to=None):
    return TaxCode.objects.create(
        org=org,
        code=code,
        description=f"{code} band {effective_from}",
        rate=Decimal(rate),
        is_input=False,
        is_output=True,
        is_claimable=True,
        f5_supply_box=1,
        f5_tax_box=6,
        is_active=True,
        effective_from=effective_from,
        effective_to=effective_to,
    )


def _system_band(code, rate, effective_from, effective_to=None):
    """System rows have org_id NULL — the ORM cannot create them through the
    model's manager bindings (the seed writes them via raw SQL); mirror that
    here with a raw INSERT."""
    from django.db import connection

    with connection.cursor() as cursor:
        cursor.execute(
            """
            INSERT INTO gst.tax_code
                (id, org_id, code, description, rate, is_input, is_output,
                 is_claimable, f5_supply_box, f5_tax_box, is_active,
                 effective_from, effective_to, created_at, updated_at)
            VALUES (gen_random_uuid(), NULL, %s, %s, %s, FALSE, TRUE, TRUE,
                    1, 6, TRUE, %s, %s, NOW(), NOW())
            """,
            [code, f"system {code} {effective_from}", str(rate), effective_from, effective_to],
        )


class TestTaxCodeListDedupeP14:
    @pytest.mark.django_db
    def test_org_row_shadows_the_identical_system_band(self, test_organisation):
        """RED for M-10: a (code, effective_from, effective_to) band that
        exists in BOTH scopes returns ONE row — the org row."""
        _system_band("SR", "0.0900", date(2024, 1, 1))
        org_row = _band(test_organisation, "SR", "0.0900", date(2024, 1, 1))

        rows = TaxCodeService.list_tax_codes(org_id=test_organisation.id)

        sr_rows = [r for r in rows if r.code == "SR" and r.effective_from == date(2024, 1, 1)]
        assert len(sr_rows) == 1, (
            f"an org band shadowing an identical system band must appear once "
            f"(got {len(sr_rows)} rows)"
        )
        assert sr_rows[0].id == org_row.id, "the org row wins the shadowing"

    @pytest.mark.django_db
    def test_history_bands_are_not_collapsed(self, test_organisation):
        """Control: distinct effective bands are legitimate rate history —
        SR's 2007/2023/2024 bands all stay (the dedupe is per band, not per
        code)."""
        _band(test_organisation, "SR", "0.0700", date(2007, 7, 1), date(2022, 12, 31))
        _band(test_organisation, "SR", "0.0800", date(2023, 1, 1), date(2023, 12, 31))
        _band(test_organisation, "SR", "0.0900", date(2024, 1, 1))

        rows = TaxCodeService.list_tax_codes(org_id=test_organisation.id)

        sr_bands = {(r.effective_from, r.effective_to) for r in rows if r.code == "SR"}
        assert len(sr_bands) == 3, (
            f"rate history must survive the dedupe (got {len(sr_bands)} bands: {sr_bands})"
        )

    @pytest.mark.django_db
    def test_effective_on_resolution_is_unchanged(self, test_organisation):
        """Control: the ?effective_on= resolution keeps returning one row per
        code (the pre-existing contract)."""
        _system_band("SR", "0.0900", date(2024, 1, 1))
        _band(test_organisation, "SR", "0.0900", date(2024, 1, 1))

        rows = TaxCodeService.list_tax_codes(
            org_id=test_organisation.id, effective_on=date(2025, 6, 1)
        )

        assert len([r for r in rows if r.code == "SR"]) == 1
