"""ExchangeRate model - Multi-currency exchange rate history."""

from django.db import models

from common.models import BaseModel


class ExchangeRate(BaseModel):
    """Exchange rates for currency conversion.

    Maps to core.exchange_rate table.
    """

    from_currency = models.ForeignKey(
        "Currency",
        on_delete=models.CASCADE,
        related_name="from_rates",
        db_column="from_currency_id",
    )
    to_currency = models.ForeignKey(
        "Currency",
        on_delete=models.CASCADE,
        related_name="to_rates",
        db_column="to_currency_id",
    )
    effective_date = models.DateField()
    rate = models.DecimalField(max_digits=15, decimal_places=8)
    source = models.CharField(max_length=30, blank=True)
    is_inverse = models.BooleanField(default=False)

    class Meta:
        managed = False
        db_table = 'core"."exchange_rate'
        unique_together = [["from_currency", "to_currency", "effective_date"]]

    def __str__(self):
        return f"{self.from_currency_code} → {self.to_currency_code} @ {self.rate}"
