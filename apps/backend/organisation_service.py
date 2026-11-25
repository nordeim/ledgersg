"""
Organisation service for LedgerSG.

Handles organisation lifecycle management including:
- Organisation creation with CoA seeding
- Organisation updates
- GST registration toggle
- Fiscal year management
"""

import uuid
from typing import Optional
from datetime import date, timedelta

from django.db import IntegrityError, connection, transaction

from apps.core.models import (
    Organisation, 
    AppUser, 
    Role, 
    UserOrganisation,
    FiscalYear,
    FiscalPeriod,
)
from common.exceptions import ValidationError, DuplicateResource


def create_organisation(
    user: AppUser,
    name: str,
    legal_name: str = "",
    uen: str = "",
    entity_type: str = "",
    gst_registered: bool = False,
    gst_reg_number: str = "",
    gst_reg_date: Optional[date] = None,
    fy_start_month: int = 1,
    base_currency: str = "SGD",
    **kwargs
) -> Organisation:
    """
    Create a new organisation with full setup.
    """
    # Set default entity_type if empty
    if not entity_type:
        entity_type = "PRIVATE_LIMITED"
    
    with transaction.atomic():
        # Create organisation
        try:
            org = Organisation.objects.create(
                name=name,
                legal_name=legal_name or name,
                uen=uen,
            entity_type=entity_type,
            gst_registered=gst_registered,
            gst_reg_number=gst_reg_number,
            gst_reg_date=gst_reg_date,
            fy_start_month=fy_start_month,
            base_currency=base_currency,
            **kwargs
        )
        except IntegrityError:
            from rest_framework import serializers

            raise serializers.ValidationError(
                {"uen": "An organisation with this UEN already exists."}
            )

        # P14/C-1: set the RLS tenant context BEFORE any seeding. Under the
        # documented runtime role (ledgersg_app, non-superuser) every seed
        # below INSERTs tenant rows (coa.account, core.fiscal_year,
        # core.role, gst.tax_code, core.user_organisation) whose RLS
        # WITH CHECK requires app.current_org_id to be THIS org — the
        # route is non-org-scoped so the middleware's context is '' (the
        # membership cache path never sees the new org either). Without
        # this set_config the whole flow 500s with
        # InsufficientPrivilege (runtime-reproduced in the 2026-11-24
        # audit, C-1). set_config(..., true) is transaction-local — the
        # same atomic block, the same connection, no leakage.
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT set_config('app.current_org_id', %s, true)",
                [str(org.id)],
            )

        # Seed Chart of Accounts via PostgreSQL function
        _seed_chart_of_accounts(org.id, gst_registered)
        
        # Create first fiscal year
        _create_first_fiscal_year(org, fy_start_month)
        
        # Assign user as Owner
        _assign_owner_role(org, user)
        
        # Seed default tax codes
        _seed_tax_codes(org.id)
        
    return org


def _seed_chart_of_accounts(org_id: uuid.UUID, gst_registered: bool) -> None:
    """
    Seed default Chart of Accounts via PostgreSQL function.
    """
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT core.seed_default_chart_of_accounts(%s, %s)",
            [str(org_id), gst_registered]
        )


def _seed_gst_control_accounts(org_id: uuid.UUID) -> None:
    """
    Seed the GST control accounts for a newly GST-registered org.

    Mirrors the GST-conditional block of
    core.seed_default_chart_of_accounts (1600 GST Input Tax, 2600 GST
    Output Tax, 2610 GST Payable / Receivable) without re-running the
    whole (non-idempotent) chart seed. Idempotent per account code.
    """
    from apps.core.models import Account, AccountSubType, AccountType

    asset_type = AccountType.objects.get(code="ASSET")
    liability_type = AccountType.objects.get(code="LIABILITY")
    current_asset = AccountSubType.objects.get(code="CURRENT_ASSET")
    tax_payable = AccountSubType.objects.get(code="TAX_PAYABLE")

    assets_parent = Account.objects.filter(
        org_id=org_id, code="1000"
    ).first()
    liabilities_parent = Account.objects.filter(
        org_id=org_id, code="2000"
    ).first()

    definitions = [
        (
            "1600",
            "GST Input Tax",
            asset_type,
            current_asset,
            assets_parent,
            "TX",
        ),
        (
            "2600",
            "GST Output Tax",
            liability_type,
            tax_payable,
            liabilities_parent,
            "SR",
        ),
        (
            "2610",
            "GST Payable / Receivable",
            liability_type,
            tax_payable,
            liabilities_parent,
            None,
        ),
    ]

    for code, name, acc_type, sub_type, parent, tax_default in definitions:
        Account.objects.get_or_create(
            org_id=org_id,
            code=code,
            defaults={
                "name": name,
                "account_type": acc_type,
                "account_sub_type": sub_type,
                "parent": parent,
                "is_system": True,
                "tax_code_default": tax_default,
                "is_active": True,
            },
        )


def _seed_tax_codes(org_id: uuid.UUID) -> None:
    """
    Seed default IRAS tax codes.
    """
    from apps.gst.services.tax_code_service import TaxCodeService
    TaxCodeService.seed_default_tax_codes(org_id)


def _create_first_fiscal_year(org: Organisation, start_month: int) -> None:
    """
    Create the first fiscal year with periods.
    """
    current_year = timezone.localdate().year
    
    # Calculate fiscal year dates
    if start_month == 1:
        # Calendar year
        start_date = date(current_year, 1, 1)
        end_date = date(current_year, 12, 31)
        label = f"FY{current_year}"
    else:
        # Non-calendar year (e.g., Apr-Mar)
        start_date = date(current_year, start_month, 1)
        end_date = date(current_year + 1, start_month, 1) - timedelta(days=1)
        label = f"FY{current_year}-{current_year + 1}"
    
    # Create fiscal year
    fiscal_year = FiscalYear.objects.create(
        org=org,
        label=label,
        start_date=start_date,
        end_date=end_date,
        is_closed=False,
    )
    
    # Create fiscal periods (months)
    _create_fiscal_periods(org, fiscal_year, start_date, end_date)


def _create_fiscal_periods(
    org: Organisation,
    fiscal_year: FiscalYear,
    start_date: date,
    end_date: date
) -> None:
    """
    Create fiscal periods (months) for a fiscal year.
    """
    from calendar import month_name
    
    current_date = start_date
    period_number = 1
    
    while current_date <= end_date:
        # Calculate period end (last day of month)
        if current_date.month == 12:
            period_end = date(current_date.year, 12, 31)
        else:
            period_end = date(current_date.year, current_date.month + 1, 1) - timedelta(days=1)
        
        # Ensure we don't exceed fiscal year end
        if period_end > end_date:
            period_end = end_date
        
        # Create period
        FiscalPeriod.objects.create(
            org=org,
            fiscal_year=fiscal_year,
            label=f"{month_name[current_date.month]} {current_date.year}",
            period_number=period_number,
            start_date=current_date,
            end_date=period_end,
            is_open=True,
        )
        
        # Move to next month
        if current_date.month == 12:
            current_date = date(current_date.year + 1, 1, 1)
        else:
            current_date = date(current_date.year, current_date.month + 1, 1)
        
        period_number += 1


def _assign_owner_role(org: Organisation, user: AppUser) -> None:
    """
    Assign the user as Owner of the organisation.
    """
    # Create Owner role if it doesn't exist
    role, created = Role.objects.get_or_create(
        org=org,
        name="Owner",
        defaults={
            "description": "Full access to the organisation",
            "can_manage_org": True,
            "can_manage_users": True,
            "can_manage_coa": True,
            "can_create_invoices": True,
            "can_approve_invoices": True,
            "can_void_invoices": True,
            "can_create_journals": True,
            "can_manage_banking": True,
            "can_file_gst": True,
            "can_view_reports": True,
            "can_export_data": True,
            "is_system": True,
        }
    )
    
    # Create user-organisation membership
    UserOrganisation.objects.create(
        user=user,
        org=org,
        role=role,
        is_default=True,
        accepted_at=timezone.now(),
    )


# Fields the service layer may update (mirrors the PATCH view's allowlist;
# regulatory fields like gst_registered/gst_reg_number belong to
# toggle_gst_registration, and id/created_at/updated_at are immutable).
UPDATABLE_ORG_FIELDS = {
    "name",
    "legal_name",
    "uen",
    "entity_type",
    "address_line_1",
    "address_line_2",
    "city",
    "postal_code",
    "country",
    "contact_email",
    "contact_phone",
    "base_currency",
    "peppol_participant_id",
    "invoicenow_enabled",
}


def update_organisation(org: Organisation, **kwargs) -> Organisation:
    """
    Update organisation settings (allow-listed fields only, P5/M-6).

    Unknown or protected keys are ignored (the HTTP layer filters too —
    this is the service-boundary defence in depth; a direct caller must
    not be able to setattr id/created_at/gst_* on the model).
    """
    import logging

    logger = logging.getLogger(__name__)

    applied = False
    for key, value in kwargs.items():
        if key in UPDATABLE_ORG_FIELDS:
            setattr(org, key, value)
            applied = True
        else:
            logger.warning(
                "update_organisation ignored non-updatable field %r", key
            )

    if applied:
        try:
            org.save()
        except IntegrityError:
            from rest_framework import serializers

            raise serializers.ValidationError(
                {"uen": "An organisation with this UEN already exists."}
            )
    return org


def toggle_gst_registration(
    org: Organisation,
    registered: bool,
    reg_number: str = "",
    reg_date: Optional[date] = None
) -> Organisation:
    """
    Toggle GST registration status.
    """
    if registered:
        if not reg_number:
            raise ValidationError("GST registration number is required.")
        if not reg_date:
            raise ValidationError("GST registration date is required.")

        was_registered = org.gst_registered
        org.gst_registered = True
        org.gst_reg_number = reg_number
        org.gst_reg_date = reg_date

        # Seed the GST control accounts on a NEW registration (P5/M-5: the
        # old `if not org.gst_reg_number` guard ran AFTER the assignment
        # above and was always False — the accounts were never seeded and
        # GST-bearing journal postings failed closed). Targeted insert: the
        # full chart seed is not idempotent (sequences + accounts would
        # collide with what create_organisation already seeded).
        if not was_registered:
            _seed_gst_control_accounts(org.id)
    else:
        org.gst_registered = False
        org.gst_reg_number = ""
        org.gst_reg_date = None
    
    org.save()
    return org


# Need to import here to avoid circular dependency
from django.utils import timezone
