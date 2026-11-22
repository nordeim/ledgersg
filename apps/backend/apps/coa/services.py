"""
Chart of Accounts service for LedgerSG.

Business logic for account management including:
- Account listing with filters and search
- Account creation with validation
- Account updates (non-system accounts only)
- Account archival (soft delete)
- Balance retrieval
- Hierarchy management
"""

from decimal import Decimal
from typing import Any
from uuid import UUID

from django.core.cache import cache
from django.db import connection

from apps.core.models import Account
from common.decimal_utils import money
from common.exceptions import DuplicateResource, ResourceNotFound, ValidationError

# Account type groups for financial statements
ACCOUNT_TYPE_GROUPS = {
    # Assets (1xxx)
    "ASSET_CURRENT": {"code_prefix": "1", "category": "ASSET", "bs_section": "current_assets"},
    "ASSET_FIXED": {"code_prefix": "15", "category": "ASSET", "bs_section": "non_current_assets"},
    "ASSET_OTHER": {"code_prefix": "18", "category": "ASSET", "bs_section": "other_assets"},

    # Liabilities (2xxx)
    "LIABILITY_CURRENT": {"code_prefix": "2", "category": "LIABILITY", "bs_section": "current_liabilities"},
    "LIABILITY_LONG_TERM": {"code_prefix": "23", "category": "LIABILITY", "bs_section": "non_current_liabilities"},

    # Equity (3xxx)
    "EQUITY": {"code_prefix": "3", "category": "EQUITY", "bs_section": "equity"},

    # Revenue (4xxx)
    "REVENUE": {"code_prefix": "4", "category": "REVENUE", "pl_section": "revenue"},
    "REVENUE_OTHER": {"code_prefix": "48", "category": "REVENUE", "pl_section": "other_income"},

    # Cost of Sales (5xxx)
    "COS": {"code_prefix": "5", "category": "EXPENSE", "pl_section": "cost_of_sales"},

    # Expenses (6xxx-7xxx)
    "EXPENSE_ADMIN": {"code_prefix": "6", "category": "EXPENSE", "pl_section": "operating_expenses"},
    "EXPENSE_SELLING": {"code_prefix": "65", "category": "EXPENSE", "pl_section": "operating_expenses"},
    "EXPENSE_OTHER": {"code_prefix": "68", "category": "EXPENSE", "pl_section": "other_expenses"},

    # Tax (8xxx)
    "TAX": {"code_prefix": "8", "category": "TAX", "pl_section": "taxation"},
}


class AccountService:
    """Service class for account operations."""

    @staticmethod
    def list_accounts(
        org_id: UUID,
        account_type: str | None = None,
        is_active: bool | None = None,
        is_system: bool | None = None,
        parent_id: UUID | None = None,
        code: str | None = None,
        search: str | None = None,
        order_by: str = "code"
    ) -> list[Account]:
        """
        List accounts with optional filters.
        """
        queryset = Account.objects.filter(org_id=org_id)

        if account_type:
            # P9/C-4: match the VARCHAR or the coarse FK code. Orgs seeded
            # before the P9 seed backfill carry only the FK; API-created
            # accounts carry both. Either way the filter must find the row.
            from django.db.models import Q

            queryset = queryset.filter(
                Q(account_type=account_type) | Q(account_type_ref__code=account_type)
            )

        if is_active is not None:
            queryset = queryset.filter(is_active=is_active)

        if is_system is not None:
            queryset = queryset.filter(is_system=is_system)

        if code:
            queryset = queryset.filter(code=code)

        if parent_id:
            queryset = queryset.filter(parent_id=parent_id)
        elif not code and not search:
            # Default: only top-level accounts if no specific filter provided
            queryset = queryset.filter(parent__isnull=True)

        if search:
            queryset = queryset.filter(
                models.Q(code__icontains=search) |
                models.Q(name__icontains=search)
            )

        # Valid ordering fields
        valid_order_by = ["code", "name", "account_type", "created_at"]
        if order_by.lstrip("-") in valid_order_by:
            queryset = queryset.order_by(order_by)
        else:
            queryset = queryset.order_by("code")

        return list(queryset)

    @staticmethod
    def get_account(org_id: UUID, account_id: UUID) -> Account:
        """
        Get account by ID.
        
        Args:
            org_id: Organisation ID
            account_id: Account ID
            
        Returns:
            Account instance
            
        Raises:
            ResourceNotFound: If account doesn't exist
        """
        try:
            return Account.objects.get(id=account_id, org_id=org_id)
        except Account.DoesNotExist:
            raise ResourceNotFound(f"Account {account_id} not found")

    @staticmethod
    def get_account_by_code(org_id: UUID, code: str) -> Account | None:
        """
        Get account by code.
        
        Args:
            org_id: Organisation ID
            code: Account code
            
        Returns:
            Account instance or None
        """
        try:
            return Account.objects.get(org_id=org_id, code=code)
        except Account.DoesNotExist:
            return None

    @staticmethod
    def create_account(
        org_id: UUID,
        code: str,
        name: str,
        account_type: str,
        parent_id: UUID | None = None,
        description: str = "",
        gst_tax_code_id: UUID | None = None,
        bank_account_id: UUID | None = None,
        is_bank_account: bool = False,
        **kwargs
    ) -> Account:
        """
        Create a new custom account.
        
        Args:
            org_id: Organisation ID
            code: Account code (must be unique within org)
            name: Account name
            account_type: Account type (e.g., 'ASSET_CURRENT')
            parent_id: Parent account ID (optional)
            description: Account description
            gst_tax_code_id: Default GST tax code
            bank_account_id: Linked bank account
            is_bank_account: Whether this is a bank account
            **kwargs: Additional fields
            
        Returns:
            Created Account instance
            
        Raises:
            ValidationError: If validation fails
            DuplicateResource: If code already exists
        """
        # Validate code format
        code = code.strip()
        if not code:
            raise ValidationError("Account code is required.")

        if len(code) < 4 or len(code) > 10:
            raise ValidationError("Account code must be between 4 and 10 characters.")

        # Check code uniqueness
        if Account.objects.filter(org_id=org_id, code=code).exists():
            raise DuplicateResource(f"Account with code '{code}' already exists.")

        # Validate account type
        if account_type not in ACCOUNT_TYPE_GROUPS:
            valid_types = ", ".join(ACCOUNT_TYPE_GROUPS.keys())
            raise ValidationError(f"Invalid account type. Valid types: {valid_types}")

        # Validate code prefix matches account type
        expected_prefix = ACCOUNT_TYPE_GROUPS[account_type]["code_prefix"]
        if not code.startswith(expected_prefix):
            raise ValidationError(
                f"Account code must start with '{expected_prefix}' for type {account_type}."
            )

        # Validate parent if provided
        parent = None
        if parent_id:
            try:
                parent = Account.objects.get(id=parent_id, org_id=org_id)
                # Ensure parent is same account type category
                parent_category = ACCOUNT_TYPE_GROUPS.get(parent.account_type, {}).get("category")
                new_category = ACCOUNT_TYPE_GROUPS[account_type].get("category")
                if parent_category != new_category:
                    raise ValidationError(
                        f"Parent account must be of the same category ({parent_category})."
                    )
            except Account.DoesNotExist:
                raise ValidationError("Parent account not found.")

        # Validate hierarchy depth (max 3 levels)
        if parent:
            depth = 1
            current = parent
            while current.parent:
                depth += 1
                current = current.parent
                if depth >= 3:
                    raise ValidationError("Maximum account hierarchy depth (3) exceeded.")

        # Create account
        # NOTE: coa.account has no gst_tax_code_id / bank_account_id columns
        # (conformance gate). The model provides tax_code_default (a code
        # string) and is_bank; the phantom kwargs previously raised
        # TypeError on every custom-account create.
        # `is_bank` may arrive either as the explicit is_bank_account arg
        # (service API) or via kwargs from the serializer's field of the
        # same name — normalise to a single value before create().
        kwargs.setdefault("is_bank", is_bank_account)

        # P8/R-4: link the coarse account_type_ref FK — the financial
        # statements (P&L / balance sheet) aggregate via
        # account_type_ref__code, and a custom account without the FK was
        # invisible to them while seeded accounts showed up fine. The
        # group's `category` is too coarse (COS's category is EXPENSE),
        # so the mapping is by group name; TAX has no coarse counterpart
        # and stays unlinked (documented).
        from apps.coa.type_mapping import GROUP_TO_COARSE_TYPE

        coarse_code = GROUP_TO_COARSE_TYPE.get(account_type)
        type_ref = None
        if coarse_code:
            from apps.core.models import AccountType

            type_ref = AccountType.objects.filter(code=coarse_code).first()

        account = Account.objects.create(
            org_id=org_id,
            code=code,
            name=name.strip(),
            account_type_ref=type_ref,
            account_type=account_type,
            parent=parent,
            description=description.strip(),
            is_system=False,  # Custom accounts are never system
            is_active=True,
            **kwargs
        )

        return account

    @staticmethod
    def update_account(
        org_id: UUID,
        account_id: UUID,
        **updates
    ) -> Account:
        """
        Update account fields.
        
        Note: System accounts cannot be modified except for description.
        
        Args:
            org_id: Organisation ID
            account_id: Account ID
            **updates: Fields to update
            
        Returns:
            Updated Account instance
        """
        account = AccountService.get_account(org_id, account_id)

        # System accounts have limited update capability
        if account.is_system:
            allowed_fields = {"description", "gst_tax_code_id", "is_active"}
            for key in list(updates.keys()):
                if key not in allowed_fields:
                    raise ValidationError(
                        f"Cannot modify '{key}' on system accounts. "
                        f"Only description, GST tax code, and active status can be changed."
                    )

        # Validate name if provided
        if "name" in updates:
            name = updates["name"].strip()
            if not name:
                raise ValidationError("Account name cannot be empty.")
            updates["name"] = name

        # Validate code if provided (and account is not system)
        if "code" in updates and not account.is_system:
            new_code = updates["code"].strip()
            if new_code != account.code:
                if Account.objects.filter(org_id=org_id, code=new_code).exists():
                    raise DuplicateResource(f"Account with code '{new_code}' already exists.")

                # Validate code prefix matches account type
                expected_prefix = ACCOUNT_TYPE_GROUPS.get(account.account_type, {}).get("code_prefix", "")
                if expected_prefix and not new_code.startswith(expected_prefix):
                    raise ValidationError(
                        f"Account code must start with '{expected_prefix}' for type {account.account_type}."
                    )
            updates["code"] = new_code

        # Update fields
        for key, value in updates.items():
            if hasattr(account, key):
                setattr(account, key, value)

        account.save()

        # Clear balance cache
        cache.delete(f"account_balance:{account_id}")

        return account

    @staticmethod
    def archive_account(org_id: UUID, account_id: UUID) -> Account:
        """
        Archive (soft delete) a custom account.
        
        System accounts cannot be archived.
        Accounts with transactions cannot be archived.
        Accounts with children cannot be archived.
        
        Args:
            org_id: Organisation ID
            account_id: Account ID
            
        Returns:
            Archived Account instance
        """
        account = AccountService.get_account(org_id, account_id)

        # Cannot archive system accounts
        if account.is_system:
            raise ValidationError("System accounts cannot be archived.")

        # Check for children
        if Account.objects.filter(parent=account).exists():
            raise ValidationError("Cannot archive account with sub-accounts. Archive sub-accounts first.")

        # Check for transactions (balance must be zero)
        balance = AccountService.get_account_balance(org_id, account_id)
        if balance != Decimal("0.0000"):
            raise ValidationError(
                f"Cannot archive account with non-zero balance ({balance}). "
                "Transfer balance to another account first."
            )

        # Soft delete
        account.is_active = False
        account.save()

        return account

    @staticmethod
    def get_account_balance(org_id: UUID, account_id: UUID) -> Decimal:
        """
        Get current balance for an account.

        Aggregates journal lines directly — the schema has no
        coa.account_balance view (the old query referenced a phantom object
        and raised UndefinedTable on first call).

        Args:
            org_id: Organisation ID
            account_id: Account ID

        Returns:
            Account balance as Decimal
        """
        # Check cache first
        cache_key = f"account_balance:{account_id}"
        cached = cache.get(cache_key)
        if cached is not None:
            return Decimal(cached)

        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT COALESCE(SUM(l.debit), 0), COALESCE(SUM(l.credit), 0)
                FROM journal.line l
                JOIN journal.entry e ON e.id = l.entry_id
                WHERE e.org_id = %s AND l.account_id = %s
                """,
                [str(org_id), str(account_id)]
            )
            row = cursor.fetchone()
            balance = money(row[0] - row[1]) if row else Decimal("0.0000")
            # Cache for 5 minutes
            cache.set(cache_key, str(balance), 300)
            return balance

    @staticmethod
    def get_account_hierarchy(org_id: UUID, account_type: str | None = None) -> list[dict[str, Any]]:
        """
        Get account hierarchy tree.
        
        Args:
            org_id: Organisation ID
            account_type: Optional filter by account type
            
        Returns:
            List of account trees with children
        """
        # Get all accounts for org
        queryset = Account.objects.filter(org_id=org_id, is_active=True)
        if account_type:
            # P9/C-4: match the VARCHAR or the coarse FK code. Orgs seeded
            # before the P9 seed backfill carry only the FK; API-created
            # accounts carry both. Either way the filter must find the row.
            from django.db.models import Q

            queryset = queryset.filter(
                Q(account_type=account_type) | Q(account_type_ref__code=account_type)
            )

        accounts = list(queryset)

        # Build hierarchy
        account_map = {acc.id: {
            "id": str(acc.id),
            "code": acc.code,
            "name": acc.name,
            "account_type": acc.account_type,
            "is_system": acc.is_system,
            "description": acc.description,
            "children": [],
        } for acc in accounts}

        roots = []
        for acc in accounts:
            node = account_map[acc.id]
            if acc.parent_id and acc.parent_id in account_map:
                account_map[acc.parent_id]["children"].append(node)
            else:
                roots.append(node)

        return roots

    @staticmethod
    def get_account_types() -> dict[str, Any]:
        """
        Get all valid account types with metadata.
        
        Returns:
            Dictionary of account type information
        """
        return {
            type_key: {
                "name": type_key.replace("_", " ").title(),
                "code_prefix": info["code_prefix"],
                "category": info["category"],
            }
            for type_key, info in ACCOUNT_TYPE_GROUPS.items()
        }

    @staticmethod
    def get_trial_balance(org_id: UUID, fiscal_year_id: UUID | None = None) -> list[dict[str, Any]]:
        """
        Get trial balance for organisation.

        Aggregates journal.line joined to journal.entry directly — the schema
        has no coa.account_balance view (A-3: the old LEFT JOIN raised
        UndefinedTable on first call, 500-ing GET /accounts/trial-balance/).
        Mirrors the get_account_balance() pattern from the P0 sprint.

        Args:
            org_id: Organisation ID
            fiscal_year_id: Optional fiscal year filter (journal.entry.fiscal_year_id)

        Returns:
            List of account balances
        """
        with connection.cursor() as cursor:
            query = """
                SELECT
                    a.id,
                    a.code,
                    a.name,
                    a.account_type::text AS account_type,
                    COALESCE(SUM(l.debit), 0)  AS total_debit,
                    COALESCE(SUM(l.credit), 0) AS total_credit,
                    COALESCE(SUM(l.debit) - SUM(l.credit), 0) AS balance
                FROM coa.account a
                LEFT JOIN journal.line l
                    ON l.account_id = a.id
                LEFT JOIN journal.entry e
                    ON e.id = l.entry_id AND e.org_id = a.org_id
                WHERE a.org_id = %s AND a.is_active = true
            """
            params = [str(org_id)]

            if fiscal_year_id:
                query += " AND e.fiscal_year_id = %s"
                params.append(str(fiscal_year_id))

            query += " GROUP BY a.id, a.code, a.name, a.account_type ORDER BY a.code"

            cursor.execute(query, params)

            columns = [col[0] for col in cursor.description]
            return [
                dict(zip(columns, row))
                for row in cursor.fetchall()
            ]


# Import models at end to avoid circular imports
from django.db import models
