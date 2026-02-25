"""
Journal serializers for LedgerSG.

Serializers for JournalEntry and JournalLine models.
"""

from rest_framework import serializers
from decimal import Decimal

from apps.core.models import JournalEntry, JournalLine


class JournalLineSerializer(serializers.ModelSerializer):
    """Serializer for journal lines."""
    
    account_code = serializers.CharField(source="account.code", read_only=True)
    account_name = serializers.CharField(source="account.name", read_only=True)
    
    class Meta:
        model = JournalLine
        fields = [
            "id", "account_id", "account_code", "account_name",
            "description", "debit", "credit"
        ]


class JournalLineCreateSerializer(serializers.Serializer):
    """Serializer for creating journal lines."""
    
    account_id = serializers.UUIDField()
    description = serializers.CharField(max_length=500, required=False, allow_blank=True)
    debit = serializers.DecimalField(max_digits=15, decimal_places=4, default=0)
    credit = serializers.DecimalField(max_digits=15, decimal_places=4, default=0)
    
    def validate(self, data):
        """Validate that line has either debit or credit."""
        debit = Decimal(str(data.get("debit", 0)))
        credit = Decimal(str(data.get("credit", 0)))
        
        if debit == 0 and credit == 0:
            raise serializers.ValidationError(
                "Line must have either debit or credit amount."
            )
        
        if debit != 0 and credit != 0:
            raise serializers.ValidationError(
                "Line cannot have both debit and credit."
            )
        
        return data


class JournalEntryListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for journal entry list views."""
    
    total_debits = serializers.SerializerMethodField()
    total_credits = serializers.SerializerMethodField()
    line_count = serializers.SerializerMethodField()
    
    class Meta:
        model = JournalEntry
        fields = [
            "id", "entry_number", "entry_date", "entry_type",
            "description", "is_posted", "posted_at",
            "total_debits", "total_credits", "line_count"
        ]
    
    def get_total_debits(self, obj: JournalEntry) -> str:
        """Get total debits."""
        total = sum(line.debit for line in obj.lines.all())
        return str(total)
    
    def get_total_credits(self, obj: JournalEntry) -> str:
        """Get total credits."""
        total = sum(line.credit for line in obj.lines.all())
        return str(total)
    
    def get_line_count(self, obj: JournalEntry) -> int:
        """Get number of lines."""
        return obj.lines.count()


class JournalEntryDetailSerializer(serializers.ModelSerializer):
    """Detailed serializer for journal entry views."""
    
    lines = JournalLineSerializer(many=True, read_only=True)
    totals = serializers.SerializerMethodField()
    source_document = serializers.SerializerMethodField()
    
    class Meta:
        model = JournalEntry
        fields = [
            "id", "entry_number", "fiscal_period_id",
            "entry_date", "entry_type", "description",
            "lines", "totals",
            "source_invoice_id", "source_document",
            "is_posted", "posted_at", "posted_by_id",
            "reversed_by_id",
            "created_by_id", "created_at", "updated_at"
        ]
        read_only_fields = [
            "id", "entry_number", "is_posted", "posted_at",
            "created_at", "updated_at"
        ]
    
    def get_totals(self, obj: JournalEntry) -> dict:
        """Get entry totals."""
        lines = obj.lines.all()
        total_debits = sum(line.debit for line in lines)
        total_credits = sum(line.credit for line in lines)
        
        return {
            "total_debits": str(total_debits),
            "total_credits": str(total_credits),
            "balanced": abs(total_debits - total_credits) < Decimal("0.001")
        }
    
    def get_source_document(self, obj: JournalEntry) -> dict:
        """Get source document info if exists."""
        if obj.source_invoice_id:
            # Import here to avoid circular import
            from apps.core.models import InvoiceDocument
            try:
                invoice = InvoiceDocument.objects.get(id=obj.source_invoice_id)
                return {
                    "id": str(invoice.id),
                    "document_number": invoice.document_number,
                    "document_type": invoice.document_type,
                }
            except InvoiceDocument.DoesNotExist:
                pass
        return None


class JournalEntryCreateSerializer(serializers.Serializer):
    """Serializer for creating journal entries."""
    
    entry_date = serializers.DateField()
    entry_type = serializers.ChoiceField(choices=[
        ("MANUAL", "Manual Entry"),
        ("ADJUSTMENT", "Adjustment"),
        ("OPENING", "Opening Balance"),
    ])
    description = serializers.CharField(max_length=500)
    lines = JournalLineCreateSerializer(many=True, min_length=2)
    fiscal_period_id = serializers.UUIDField(required=False, allow_null=True)
    
    def validate(self, data):
        """Validate that debits equal credits."""
        lines = data.get("lines", [])
        
        total_debits = sum(
            Decimal(str(line.get("debit", 0))) for line in lines
        )
        total_credits = sum(
            Decimal(str(line.get("credit", 0))) for line in lines
        )
        
        if abs(total_debits - total_credits) > Decimal("0.001"):
            raise serializers.ValidationError(
                f"Debits ({total_debits}) must equal credits ({total_credits})."
            )
        
        return data


class JournalEntryUpdateSerializer(serializers.Serializer):
    """Serializer for updating journal entries (DRAFT only)."""
    
    description = serializers.CharField(max_length=500, required=False)


class ReversalCreateSerializer(serializers.Serializer):
    """Serializer for creating reversal entries."""
    
    reversal_date = serializers.DateField()
    reason = serializers.CharField(max_length=500)


class TrialBalanceEntrySerializer(serializers.Serializer):
    """Serializer for trial balance entries."""
    
    account_id = serializers.CharField()
    account_code = serializers.CharField()
    account_name = serializers.CharField()
    account_type = serializers.CharField()
    total_debits = serializers.CharField()
    total_credits = serializers.CharField()
    balance = serializers.CharField()


class TrialBalanceSerializer(serializers.Serializer):
    """Serializer for trial balance."""
    
    entries = TrialBalanceEntrySerializer(many=True)
    totals = serializers.DictField()
    is_balanced = serializers.BooleanField()


class AccountBalanceSerializer(serializers.Serializer):
    """Serializer for account balance."""
    
    account_id = serializers.CharField()
    account_code = serializers.CharField()
    account_name = serializers.CharField()
    balance = serializers.CharField()
    as_of_date = serializers.DateField(required=False)


class EntryTypeSerializer(serializers.Serializer):
    """Serializer for entry type information."""
    
    code = serializers.CharField()
    name = serializers.CharField()
