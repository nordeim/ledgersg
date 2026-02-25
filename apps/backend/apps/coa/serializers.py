"""
Chart of Accounts serializers for LedgerSG.

Serializers for Account model and related operations.
"""

from rest_framework import serializers
from decimal import Decimal
from typing import Optional, Dict, Any

from apps.core.models import Account


class AccountListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for account list views."""
    
    balance = serializers.SerializerMethodField()
    has_children = serializers.SerializerMethodField()
    
    class Meta:
        model = Account
        fields = [
            "id", "code", "name", "account_type",
            "is_system", "is_active", "is_bank_account",
            "parent_id", "has_children", "balance",
        ]
        read_only_fields = ["id", "is_system"]
    
    def get_balance(self, obj: Account) -> Optional[str]:
        """Get account balance if requested via context."""
        if self.context.get("include_balance"):
            # Import here to avoid circular import
            from .services import AccountService
            balance = AccountService.get_account_balance(obj.org_id, obj.id)
            return str(balance)
        return None
    
    def get_has_children(self, obj: Account) -> bool:
        """Check if account has children."""
        return Account.objects.filter(parent=obj).exists()


class AccountDetailSerializer(serializers.ModelSerializer):
    """Detailed serializer for account views."""
    
    balance = serializers.SerializerMethodField()
    parent = AccountListSerializer(read_only=True)
    children = serializers.SerializerMethodField()
    gst_tax_code_code = serializers.CharField(source="gst_tax_code.code", read_only=True)
    
    class Meta:
        model = Account
        fields = [
            "id", "code", "name", "account_type", "description",
            "parent", "parent_id", "children",
            "gst_tax_code_id", "gst_tax_code_code",
            "bank_account_id", "is_bank_account",
            "is_system", "is_active", "created_at", "updated_at",
            "balance",
        ]
        read_only_fields = ["id", "is_system", "created_at", "updated_at", "balance"]
    
    def get_balance(self, obj: Account) -> str:
        """Get account balance."""
        from .services import AccountService
        balance = AccountService.get_account_balance(obj.org_id, obj.id)
        return str(balance)
    
    def get_children(self, obj: Account) -> list:
        """Get child accounts."""
        children = Account.objects.filter(parent=obj, is_active=True)
        return AccountListSerializer(
            children, many=True, context=self.context
        ).data


class AccountCreateSerializer(serializers.Serializer):
    """Serializer for creating a new account."""
    
    code = serializers.CharField(max_length=10)
    name = serializers.CharField(max_length=255)
    account_type = serializers.CharField(max_length=50)
    description = serializers.CharField(max_length=500, required=False, allow_blank=True)
    parent_id = serializers.UUIDField(required=False, allow_null=True)
    gst_tax_code_id = serializers.UUIDField(required=False, allow_null=True)
    bank_account_id = serializers.UUIDField(required=False, allow_null=True)
    is_bank_account = serializers.BooleanField(default=False)
    
    def validate_code(self, value: str) -> str:
        """Validate account code format."""
        value = value.strip()
        if not value:
            raise serializers.ValidationError("Account code is required.")
        if len(value) < 4:
            raise serializers.ValidationError("Account code must be at least 4 characters.")
        if not value.isdigit():
            raise serializers.ValidationError("Account code must be numeric.")
        return value
    
    def validate_name(self, value: str) -> str:
        """Validate account name."""
        value = value.strip()
        if not value:
            raise serializers.ValidationError("Account name is required.")
        if len(value) < 2:
            raise serializers.ValidationError("Account name must be at least 2 characters.")
        return value
    
    def validate_account_type(self, value: str) -> str:
        """Validate account type."""
        from .services import ACCOUNT_TYPE_GROUPS
        if value not in ACCOUNT_TYPE_GROUPS:
            valid_types = ", ".join(ACCOUNT_TYPE_GROUPS.keys())
            raise serializers.ValidationError(f"Invalid account type. Valid types: {valid_types}")
        return value


class AccountUpdateSerializer(serializers.Serializer):
    """Serializer for updating an account."""
    
    name = serializers.CharField(max_length=255, required=False)
    code = serializers.CharField(max_length=10, required=False)
    description = serializers.CharField(max_length=500, required=False, allow_blank=True)
    gst_tax_code_id = serializers.UUIDField(required=False, allow_null=True)
    is_bank_account = serializers.BooleanField(required=False)
    is_active = serializers.BooleanField(required=False)
    
    def validate_name(self, value: str) -> str:
        """Validate account name."""
        if value:
            value = value.strip()
            if len(value) < 2:
                raise serializers.ValidationError("Account name must be at least 2 characters.")
        return value
    
    def validate_code(self, value: str) -> str:
        """Validate account code format."""
        if value:
            value = value.strip()
            if not value.isdigit():
                raise serializers.ValidationError("Account code must be numeric.")
        return value


class AccountHierarchySerializer(serializers.Serializer):
    """Serializer for account hierarchy tree."""
    
    id = serializers.CharField()
    code = serializers.CharField()
    name = serializers.CharField()
    account_type = serializers.CharField()
    is_system = serializers.BooleanField()
    description = serializers.CharField(allow_blank=True)
    children = serializers.ListField(child=serializers.DictField(), required=False)


class TrialBalanceSerializer(serializers.Serializer):
    """Serializer for trial balance entries."""
    
    id = serializers.UUIDField()
    code = serializers.CharField()
    name = serializers.CharField()
    account_type = serializers.CharField()
    total_debit = serializers.DecimalField(max_digits=15, decimal_places=4)
    total_credit = serializers.DecimalField(max_digits=15, decimal_places=4)
    balance = serializers.DecimalField(max_digits=15, decimal_places=4)


class AccountTypeSerializer(serializers.Serializer):
    """Serializer for account type information."""
    
    key = serializers.CharField()
    name = serializers.CharField()
    code_prefix = serializers.CharField()
    category = serializers.CharField()
