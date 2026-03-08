"""
Organisation Seed Service for LedgerSG.

Seeds initial data for new organisations including:
- Tax codes (Singapore GST)
- Chart of Accounts
- Fiscal year/period
"""

from uuid import UUID
from decimal import Decimal
from django.db import transaction
from django.utils import timezone
from datetime import date
import logging

logger = logging.getLogger(__name__)

# Default effective date for tax codes
DEFAULT_EFFECTIVE_FROM = date(2024, 1, 1)


def seed_organisation_data(org_id: UUID):
    """
    Seed all required data for a new organisation.

    Args:
        org_id: The organisation UUID to seed data for
    """
    logger.info(f"Seeding data for organisation {org_id}")

    try:
        with transaction.atomic():
            _seed_tax_codes(org_id)
            _seed_chart_of_accounts(org_id)
            _seed_fiscal_data(org_id)
            logger.info(f"Successfully seeded data for organisation {org_id}")
    except Exception as e:
        logger.error(f"Failed to seed data for organisation {org_id}: {e}")
        raise


def _seed_tax_codes(org_id: UUID):
    """Seed Singapore tax codes for an organisation."""
    from apps.core.models import TaxCode

    tax_codes = [
        {
            "code": "OS",
            "name": "Out of Scope",
            "description": "Supplies outside scope of GST",
            "rate": Decimal("0.0000"),
            "is_gst_charged": False,
            "is_input": True,
            "is_output": True,
            "is_claimable": False,
            "is_reverse_charge": False,
            "effective_from": DEFAULT_EFFECTIVE_FROM,
        },
        {
            "code": "NA",
            "name": "Not Applicable",
            "description": "GST not applicable",
            "rate": Decimal("0.0000"),
            "is_gst_charged": False,
            "is_input": True,
            "is_output": True,
            "is_claimable": False,
            "is_reverse_charge": False,
            "effective_from": DEFAULT_EFFECTIVE_FROM,
        },
        {
            "code": "SR",
            "name": "Standard Rated",
            "description": "Standard rated supplies (9%)",
            "rate": Decimal("0.0900"),
            "is_gst_charged": True,
            "is_input": True,
            "is_output": True,
            "is_claimable": True,
            "is_reverse_charge": False,
            "effective_from": DEFAULT_EFFECTIVE_FROM,
        },
        {
            "code": "ZR",
            "name": "Zero Rated",
            "description": "Zero-rated supplies (0%)",
            "rate": Decimal("0.0000"),
            "is_gst_charged": True,
            "is_input": True,
            "is_output": True,
            "is_claimable": True,
            "is_reverse_charge": False,
            "effective_from": DEFAULT_EFFECTIVE_FROM,
        },
        {
            "code": "ES",
            "name": "Exempt",
            "description": "Exempt supplies",
            "rate": Decimal("0.0000"),
            "is_gst_charged": True,
            "is_input": False,
            "is_output": True,
            "is_claimable": False,
            "is_reverse_charge": False,
            "effective_from": DEFAULT_EFFECTIVE_FROM,
        },
    ]

    created_count = 0
    for tc_data in tax_codes:
        _, created = TaxCode.objects.get_or_create(
            org_id=org_id, code=tc_data["code"], defaults=tc_data
        )
        if created:
            created_count += 1

    logger.info(f"Created {created_count} tax codes for org {org_id}")


def _seed_chart_of_accounts(org_id: UUID):
    """Seed standard Chart of Accounts for an organisation."""
    from apps.core.models import Account, AccountType, AccountSubType

    # Get account types
    account_types = {}
    for at in AccountType.objects.all():
        account_types[at.code] = at

    # Get account subtypes
    account_sub_types = {}
    for ast in AccountSubType.objects.all():
        account_sub_types[ast.code] = ast

    accounts = [
        # Assets (1000-1999)
        {
            "code": "1100",
            "name": "Bank Account",
            "account_type_code": "ASSET",
            "account_sub_type_code": 1100,
            "is_bank_account": True,
            "is_active": True,
        },
        {
            "code": "1200",
            "name": "Accounts Receivable",
            "account_type_code": "ASSET",
            "account_sub_type_code": 1200,
            "is_bank_account": False,
            "is_active": True,
        },
        {
            "code": "1300",
            "name": "Inventory",
            "account_type_code": "ASSET",
            "account_sub_type_code": 1300,
            "is_bank_account": False,
            "is_active": True,
        },
        {
            "code": "1500",
            "name": "Equipment",
            "account_type_code": "ASSET",
            "account_sub_type_code": 1500,
            "is_bank_account": False,
            "is_active": True,
        },
        # Liabilities (2000-2999)
        {
            "code": "2000",
            "name": "Accounts Payable",
            "account_type_code": "LIABILITY",
            "account_sub_type_code": 2000,
            "is_bank_account": False,
            "is_active": True,
        },
        {
            "code": "2100",
            "name": "Loans Payable",
            "account_type_code": "LIABILITY",
            "account_sub_type_code": 2100,
            "is_bank_account": False,
            "is_active": True,
        },
        # Equity (3000-3999)
        {
            "code": "3000",
            "name": "Owner's Capital",
            "account_type_code": "EQUITY",
            "account_sub_type_code": 3000,
            "is_bank_account": False,
            "is_active": True,
        },
        {
            "code": "3100",
            "name": "Retained Earnings",
            "account_type_code": "EQUITY",
            "account_sub_type_code": 3100,
            "is_bank_account": False,
            "is_active": True,
        },
        # Revenue (4000-4999)
        {
            "code": "4000",
            "name": "Sales Revenue",
            "account_type_code": "REVENUE",
            "account_sub_type_code": 4000,
            "is_bank_account": False,
            "is_active": True,
        },
        {
            "code": "4100",
            "name": "Service Revenue",
            "account_type_code": "REVENUE",
            "account_sub_type_code": 4100,
            "is_bank_account": False,
            "is_active": True,
        },
        # Cost of Goods Sold (5000-5999)
        {
            "code": "5000",
            "name": "Cost of Goods Sold",
            "account_type_code": "COGS",
            "account_sub_type_code": 5000,
            "is_bank_account": False,
            "is_active": True,
        },
        # Expenses (6000-6999)
        {
            "code": "6100",
            "name": "Rent Expense",
            "account_type_code": "EXPENSE",
            "account_sub_type_code": 6100,
            "is_bank_account": False,
            "is_active": True,
        },
        {
            "code": "6200",
            "name": "Office Supplies",
            "account_type_code": "EXPENSE",
            "account_sub_type_code": 6200,
            "is_bank_account": False,
            "is_active": True,
        },
        {
            "code": "6300",
            "name": "Utilities",
            "account_type_code": "EXPENSE",
            "account_sub_type_code": 6300,
            "is_bank_account": False,
            "is_active": True,
        },
        {
            "code": "6400",
            "name": "Salaries",
            "account_type_code": "EXPENSE",
            "account_sub_type_code": 6400,
            "is_bank_account": False,
            "is_active": True,
        },
    ]

    created_count = 0
    for acc_data in accounts:
        account_type = account_types.get(acc_data["account_type_code"])
        account_sub_type = account_sub_types.get(acc_data["account_sub_type_code"])

        if not account_type or not account_sub_type:
            logger.warning(f"Skipping account {acc_data['code']}: type/subtype not found")
            continue

    defaults = {
        "name": acc_data["name"],
        "account_type": account_type,
        "account_sub_type": account_sub_type,
        "is_bank_account": acc_data["is_bank_account"],
        "is_active": acc_data["is_active"],
        "is_system": True,
    }

_, created = Account.objects.get_or_create(
            org_id=org_id, code=acc_data["code"], defaults=defaults
        )
        if created:
            created_count += 1

    logger.info(f"Created {created_count} accounts for org {org_id}")


def _seed_fiscal_data(org_id: UUID):
    """Seed fiscal year and period for an organisation."""
    from apps.core.models import FiscalYear, FiscalPeriod
    from datetime import date

    current_year = date.today().year

    # Create fiscal year
    fy_label = f"FY{current_year}"
    fy_defaults = {
        "start_date": date(current_year, 1, 1),
        "end_date": date(current_year, 12, 31),
        "is_closed": False,
    }

    fiscal_year, created = FiscalYear.objects.get_or_create(
        org_id=org_id, label=fy_label, defaults=fy_defaults
    )

    if created:
        logger.info(f"Created fiscal year {current_year} for org {org_id}")

    # Create Q1 fiscal period (Jan-Mar)
    fp_defaults = {
        "start_date": date(current_year, 1, 1),
        "end_date": date(current_year, 3, 31),
        "is_closed": False,
        "is_open": True,
    }

    fiscal_period, created = FiscalPeriod.objects.get_or_create(
        org_id=org_id, fiscal_year=fiscal_year, period_number=1, defaults=fp_defaults
    )

    if created:
        logger.info(f"Created fiscal period Q1 for org {org_id}")


# Execute seeding if run directly
if __name__ == "__main__":
    import sys
    import django
    import os

    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.development")
    sys.path.insert(0, "/home/project/Ledger-SG/apps/backend")
    django.setup()

    import uuid

    org_id = uuid.UUID("65abbcd6-6129-41ef-82ed-9e84a3442c7f")
    seed_organisation_data(org_id)
    print(f"Seeded data for organisation {org_id}")
