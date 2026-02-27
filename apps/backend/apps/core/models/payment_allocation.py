"""
PaymentAllocation model for LedgerSG.

Maps to banking.payment_allocation table.
"""

from django.db import models
from common.models import TenantModel


class PaymentAllocation(TenantModel):
    """Maps payments to invoices (supports partial payments)."""
    
    payment = models.ForeignKey(
        "Payment", on_delete=models.CASCADE,
        db_column="payment_id"
    )
    document = models.ForeignKey(
        "InvoiceDocument", on_delete=models.RESTRICT,
        db_column="document_id"
    )
    allocated_amount = models.DecimalField(
        max_digits=10, decimal_places=4,
        db_column="allocated_amount"
    )
    base_allocated_amount = models.DecimalField(
        max_digits=10, decimal_places=4,
        db_column="base_allocated_amount"
    )
    
    class Meta:
        managed = False
        db_table = 'banking"."payment_allocation'
        unique_together = [["payment", "document"]]
