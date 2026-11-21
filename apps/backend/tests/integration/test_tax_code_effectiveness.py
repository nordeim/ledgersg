"""
Regression tests for GST rate-history resolution by effective date (B-3 / H-04).

Before the fix: ``get_tax_code_by_code()`` did an unordered ``.first()`` over
history rows (returning the 2007 7% row for SR instead of the current 9%),
``list_tax_codes()`` returned every history row unordered, the calculate
endpoint silently fell back to 9% for unknown codes, and ``add_line()``
snapshotted whatever rate the passed row carried without checking it was in
force on the document date.
"""

from datetime import date
from decimal import Decimal

import pytest
from rest_framework import status

from apps.core.models import Contact, TaxCode
from apps.gst.services.tax_code_service import TaxCodeService
from apps.invoicing.services.document_service import DocumentService
from common.exceptions import ValidationError

pytestmark = pytest.mark.django_db


def _seed_sr_history(org) -> dict:
    """Mirror the system SR history as org-scoped rows: 7% -> 8% -> 9%."""
    rows = {
        "old": TaxCode.objects.create(
            org=org,
            code="SR",
            name="Standard-Rated (historic 7%)",
            rate=Decimal("0.0700"),
            is_gst_charged=True,
            is_input=False,
            is_output=True,
            is_active=True,
            effective_from=date(2007, 7, 1),
            effective_to=date(2022, 12, 31),
        ),
        "mid": TaxCode.objects.create(
            org=org,
            code="SR",
            name="Standard-Rated (historic 8%)",
            rate=Decimal("0.0800"),
            is_gst_charged=True,
            is_input=False,
            is_output=True,
            is_active=True,
            effective_from=date(2023, 1, 1),
            effective_to=date(2023, 12, 31),
        ),
        "current": TaxCode.objects.create(
            org=org,
            code="SR",
            name="Standard-Rated",
            rate=Decimal("0.0900"),
            is_gst_charged=True,
            is_input=False,
            is_output=True,
            is_active=True,
            effective_from=date(2024, 1, 1),
        ),
    }
    return rows


class TestServiceRateResolution:
    def test_resolves_rate_in_force_on_as_of_date(self, test_organisation):
        _seed_sr_history(test_organisation)

        resolved = TaxCodeService.get_tax_code_by_code(
            test_organisation.id, "SR", as_of=date(2023, 6, 1)
        )

        assert resolved is not None
        assert resolved.rate == Decimal("0.0800")

    def test_resolves_current_rate_when_no_as_of_given(self, test_organisation):
        _seed_sr_history(test_organisation)

        resolved = TaxCodeService.get_tax_code_by_code(test_organisation.id, "SR")

        assert resolved is not None
        assert resolved.rate == Decimal("0.0900")

    def test_resolves_open_ended_row_after_its_effective_from(self, test_organisation):
        _seed_sr_history(test_organisation)

        resolved = TaxCodeService.get_tax_code_by_code(
            test_organisation.id, "SR", as_of=date(2024, 1, 1)
        )

        assert resolved is not None
        assert resolved.rate == Decimal("0.0900")

    def test_returns_none_when_nothing_in_force(self, test_organisation):
        _seed_sr_history(test_organisation)

        # Before the first row's effective_from.
        resolved = TaxCodeService.get_tax_code_by_code(
            test_organisation.id, "SR", as_of=date(2000, 1, 1)
        )

        assert resolved is None

    def test_org_specific_row_shadows_system_row(self, test_organisation):
        """An org-scoped effective row wins over the system row in force.

        The schema seed already provides the system SR history (org_id NULL:
        0.07 -> 0.08 -> 0.09, current row effective 2024-01-01), so only the
        org override needs creating.
        """
        org_row = TaxCode.objects.create(
            org=test_organisation,
            code="SR",
            name="Standard-Rated (org override)",
            rate=Decimal("0.0500"),
            is_gst_charged=True,
            is_input=False,
            is_output=True,
            is_active=True,
            effective_from=date(2024, 1, 1),
        )

        resolved = TaxCodeService.get_tax_code_by_code(test_organisation.id, "SR")

        assert resolved is not None
        assert resolved.id == org_row.id
        assert resolved.rate == Decimal("0.0500")


class TestListEndpointEffectiveFilter:
    def test_effective_on_returns_single_row_per_code(self, auth_client, test_organisation):
        _seed_sr_history(test_organisation)

        response = auth_client.get(
            f"/api/v1/{test_organisation.id}/gst/tax-codes/",
            {"effective_on": "2023-06-01"},
        )

        assert response.status_code == status.HTTP_200_OK
        sr_rows = [row for row in response.data["results"] if row["code"] == "SR"]
        assert len(sr_rows) == 1
        assert Decimal(str(sr_rows[0]["rate"])) == Decimal("0.0800")

    def test_list_orders_newest_rate_first_within_code(
        self, auth_client, test_organisation
    ):
        _seed_sr_history(test_organisation)

        response = auth_client.get(f"/api/v1/{test_organisation.id}/gst/tax-codes/")

        assert response.status_code == status.HTTP_200_OK
        sr_rows = [
            row for row in response.data["results"] if row["code"] == "SR"
        ]
        sr_rates = [Decimal(str(row["rate"])) for row in sr_rows]
        # Contract: org-scoped rows first (newest -> oldest), then system
        # rows (newest -> oldest) — the schema seed supplies the system
        # history (0.07/0.08/0.09), the fixture the org history.
        org_rates = sr_rates[:3]
        system_rates = sr_rates[3:]
        assert org_rates == sorted(org_rates, reverse=True)
        assert system_rates == sorted(system_rates, reverse=True)


class TestCalculateEndpointRateResolution:
    def test_calculates_with_rate_in_force_on_document_date(
        self, auth_client, test_organisation
    ):
        _seed_sr_history(test_organisation)

        response = auth_client.post(
            f"/api/v1/{test_organisation.id}/gst/calculate/",
            {
                "amount": "100.00",
                "tax_code": "SR",
                "document_date": "2023-06-01",
            },
            format="json",
        )

        assert response.status_code == status.HTTP_200_OK, response.data
        assert response.data["rate"] == "0.0800"
        assert response.data["gst_amount"] == "8.00"

    def test_unknown_code_is_404_not_silent_fallback(
        self, auth_client, test_organisation
    ):
        response = auth_client.post(
            f"/api/v1/{test_organisation.id}/gst/calculate/",
            {"amount": "100.00", "tax_code": "NOPE"},
            format="json",
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_legacy_tax_code_id_field_still_accepted(
        self, auth_client, test_organisation
    ):
        """The deprecated tax_code_id field (holding a code) keeps working."""
        _seed_sr_history(test_organisation)

        response = auth_client.post(
            f"/api/v1/{test_organisation.id}/gst/calculate/",
            {"amount": "100.00", "tax_code_id": "SR"},
            format="json",
        )

        assert response.status_code == status.HTTP_200_OK, response.data
        assert response.data["rate"] == "0.0900"


class TestAddLineEffectiveness:
    def _document(self, test_organisation, issue_date):
        contact = Contact.objects.create(
            org=test_organisation,
            contact_type="CUSTOMER",
            name="Rate History Customer",
            email="rates@example.sg",
        )
        return DocumentService.create_document(
            org_id=test_organisation.id,
            document_type="SALES_INVOICE",
            contact_id=contact.id,
            issue_date=issue_date,
        )

    def test_stale_tax_code_rejected_for_document_date(
        self, test_organisation, test_accounts
    ):
        rows = _seed_sr_history(test_organisation)
        document = self._document(test_organisation, date(2026, 11, 21))

        with pytest.raises(ValidationError, match="not effective"):
            DocumentService.add_line(
                org_id=test_organisation.id,
                document_id=document.id,
                account_id=test_accounts["4000"].id,
                description="Stale-rate line",
                quantity=Decimal("1"),
                unit_price=Decimal("100.00"),
                tax_code_id=rows["old"].id,
            )

    def test_effective_tax_code_snapshots_its_rate(
        self, test_organisation, test_accounts
    ):
        rows = _seed_sr_history(test_organisation)
        document = self._document(test_organisation, date(2026, 11, 21))

        line = DocumentService.add_line(
            org_id=test_organisation.id,
            document_id=document.id,
            account_id=test_accounts["4000"].id,
            description="Current-rate line",
            quantity=Decimal("1"),
            unit_price=Decimal("100.00"),
            tax_code_id=rows["current"].id,
        )

        assert line.tax_rate == Decimal("0.0900")
        assert line.gst_amount == Decimal("9.00")
