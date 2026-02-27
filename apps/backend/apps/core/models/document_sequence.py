"""
DocumentSequence model for LedgerSG.

Maps to core.document_sequence table.
"""

from django.db import models
from common.models import TenantModel


class DocumentSequence(TenantModel):
    """Auto-numbering sequence for documents."""
    
    document_type = models.CharField(max_length=30, db_column="document_type")
    prefix = models.CharField(max_length=20, default="", db_column="prefix")
    next_number = models.BigIntegerField(default=1, db_column="next_number")
    padding = models.SmallIntegerField(default=5, db_column="padding")
    fiscal_year_reset = models.BooleanField(default=False, db_column="fiscal_year_reset")
    
    class Meta:
        managed = False
        db_table = 'core"."document_sequence'
        unique_together = [["org", "document_type"]]
