"""
P5/M-5 + M-6 — organisation service truth.

RED suite (against the pre-P5 code): toggle_gst_registration's GST-account
seeding branch is dead code (it tests `if not org.gst_reg_number` AFTER
assigning reg_number — always False), and update_organisation setattrs any
model attribute present on the instance.
"""

from datetime import date

import pytest

from apps.core.models import Account
from apps.core.services.organisation_service import (
    toggle_gst_registration,
    update_organisation,
)

pytestmark = pytest.mark.django_db


class TestToggleGstRegistration:
    """P5/M-5: registering for GST must seed the GST control accounts."""

    def test_new_registration_seeds_gst_control_accounts(self, test_organisation):
        # The conftest org is created gst_registered=True directly — reset to
        # a non-registered starting state to exercise the toggle.
        test_organisation.gst_registered = False
        test_organisation.gst_reg_number = ""
        test_organisation.gst_reg_date = None
        test_organisation.save()
        Account.objects.filter(
            org=test_organisation, code__in=["1600", "2600"]
        ).delete()

        org = toggle_gst_registration(
            test_organisation,
            registered=True,
            reg_number="M99999999",
            reg_date=date(2026, 1, 1),
        )

        assert org.gst_registered is True
        codes = set(
            Account.objects.filter(org=test_organisation).values_list(
                "code", flat=True
            )
        )
        assert "1600" in codes, (
            "GST Input Tax control account must be seeded on registration — "
            "journal postings for GST-bearing lines fail closed without it"
        )
        assert "2600" in codes, "GST Output Tax control account must be seeded"

    def test_unregister_keeps_accounts(self, test_organisation):
        """Historical journals reference the control accounts — keep them."""
        Account.objects.create(
            org=test_organisation,
            code="1300",
            name="Inventory",
            account_type="ASSET",
        )
        org = toggle_gst_registration(test_organisation, registered=False)

        assert org.gst_registered is False
        assert org.gst_reg_number == ""
        codes = set(
            Account.objects.filter(org=test_organisation).values_list(
                "code", flat=True
            )
        )
        assert "1300" in codes, "unregistration must never delete accounts"

    def test_missing_reg_number_rejected(self, test_organisation):
        from common.exceptions import ValidationError

        with pytest.raises(ValidationError, match="registration number"):
            toggle_gst_registration(
                test_organisation, registered=True, reg_number=""
            )


class TestUpdateOrganisationAllowlist:
    """P5/M-6: service-level allowlist — no setattr on arbitrary fields."""

    def test_protected_fields_are_ignored(self, test_organisation):
        original_id = test_organisation.id
        original_created = test_organisation.created_at

        org = update_organisation(
            test_organisation,
            id="00000000-0000-0000-0000-000000000000",
            created_at="2000-01-01",
            gst_registered=False,  # regulatory field — not patchable here
            name="Legitimate New Name",
        )

        org.refresh_from_db()
        assert org.id == original_id, "id must never be reassigned"
        assert org.created_at == original_created, "created_at is immutable"
        assert org.name == "Legitimate New Name", "allowed fields still work"

    def test_gst_reg_number_not_writable_via_update(self, test_organisation):
        """Regulatory fields belong to toggle_gst_registration, not PATCH."""
        original_reg = test_organisation.gst_reg_number

        org = update_organisation(
            test_organisation, gst_reg_number="M-EVIL-1"
        )

        org.refresh_from_db()
        assert org.gst_reg_number == original_reg
