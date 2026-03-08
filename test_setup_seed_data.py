#!/usr/bin/env python3
"""
Seed test data for API workflow verification.
Creates/updates test user with known password.
"""

import os
import sys
import django

# Setup Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.development")
sys.path.insert(0, "/home/project/Ledger-SG/apps/backend")
django.setup()

from django.contrib.auth import get_user_model
from apps.core.models import Organisation, UserOrganisation
from apps.core.models import TaxCode

User = get_user_model()


def create_or_update_test_user():
    """Create or update test user with known password."""
    email = "workflow_test@ledgersg.sg"
    password = "TestPass123!"

    user, created = User.objects.update_or_create(
        email=email,
        defaults={
            "first_name": "Workflow",
            "last_name": "Test",
            "is_active": True,
        },
    )

    # Set password
    user.set_password(password)
    user.save()

    print(f"✅ Test user {'created' if created else 'updated'}: {email}")
    print(f"   Password: {password}")
    print(f"   ID: {user.id}")

    return user


def create_test_organisation(user):
    """Create test organisation for workflow testing."""
    org_data = {
        "name": "ABC Trading Test",
        "legal_name": "ABC Trading Pte Ltd",
        "entity_type": "SOLE_PROPRIETORSHIP",
        "uen": "T26SS0001A",
        "gst_registered": False,
        "base_currency": "SGD",
        "fy_start_month": 1,
        "timezone": "Asia/Singapore",
        "email": "contact@abctrading.com",
        "phone": "+65 6123 4567",
        "address_line_1": "123 Orchard Road",
        "city": "Singapore",
        "postal_code": "238858",
        "country": "SG",
    }

    org, created = Organisation.objects.update_or_create(
        uen=org_data["uen"], defaults=org_data
    )

    print(f"✅ Test organisation {'created' if created else 'updated'}: {org.name}")
    print(f"   ID: {org.id}")
    print(f"   GST Registered: {org.gst_registered}")

    # Link user to organisation
    user_org, created = UserOrganisation.objects.update_or_create(
        user=user,
        organisation=org,
        defaults={
            "role": "OWNER",
            "is_default": True,
        },
    )

    # Set accepted_at if not set
    if not user_org.accepted_at:
        from django.utils import timezone

        user_org.accepted_at = timezone.now()
        user_org.save()

    print(f"✅ User linked to organisation as OWNER")

    return org


def seed_tax_codes(org):
    """Seed essential tax codes for non-GST business."""
    tax_codes = [
        {
            "code": "OS",
            "name": "Out of Scope",
            "description": "Supplies outside scope of GST",
            "rate": "0.0000",
            "is_gst_charged": False,
            "is_input": True,
            "is_output": True,
            "is_claimable": False,
            "is_reverse_charge": False,
        },
        {
            "code": "NA",
            "name": "Not Applicable",
            "description": "Not applicable for GST",
            "rate": "0.0000",
            "is_gst_charged": False,
            "is_input": True,
            "is_output": True,
            "is_claimable": False,
            "is_reverse_charge": False,
        },
    ]

    created_count = 0
    for tc_data in tax_codes:
        tc, created = TaxCode.objects.update_or_create(
            org_id=org.id, code=tc_data["code"], defaults={**tc_data, "org": org}
        )
        if created:
            created_count += 1

    print(f"✅ Seeded {created_count} tax codes (OS, NA)")


def main():
    print("=" * 60)
    print("LEDGERSG WORKFLOW TEST SETUP")
    print("=" * 60)
    print()

    try:
        # Create test user
        user = create_or_update_test_user()

        # Create test organisation
        org = create_test_organisation(user)

        # Seed tax codes
        seed_tax_codes(org)

        print()
        print("=" * 60)
        print("SETUP COMPLETE")
        print("=" * 60)
        print()
        print("Test Credentials:")
        print(f"  Email: workflow_test@ledgersg.sg")
        print(f"  Password: TestPass123!")
        print()
        print("Test Organisation:")
        print(f"  Name: ABC Trading Test")
        print(f"  ID: {org.id}")
        print(f"  UEN: T26SS0001A")
        print()
        print("You can now run the complete workflow script.")
        print()

        return 0

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
