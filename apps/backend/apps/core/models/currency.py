"""
Currency model for LedgerSG.

Maps to core.currency table (reference data).
"""

from django.db import models


class Currency(models.Model):
    """ISO 4217 currency reference."""
    
    code = models.CharField(max_length=3, primary_key=True, db_column="code")
    name = models.CharField(max_length=100, db_column="name")
    symbol = models.CharField(max_length=5, db_column="symbol")
    decimal_places = models.SmallIntegerField(default=2, db_column="decimal_places")
    is_active = models.BooleanField(default=True, db_column="is_active")
    
    class Meta:
        managed = False
        db_table = 'core"."currency'
