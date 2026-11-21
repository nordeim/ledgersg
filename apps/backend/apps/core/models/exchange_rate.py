"""ExchangeRate model - Multi-currency exchange rate history.

Aligned with core.exchange_rate (SQL-First: schema is the source of truth):
    id            uuid PK
    org_id        uuid NOT NULL FK core.organisation
    currency_code char(3) NOT NULL FK core.currency(code) — natural key
    rate_date     date NOT NULL
    rate          numeric(12,6) NOT NULL CHECK (rate > 0)
    source        varchar(50) NULL default 'manual'
    created_at    timestamptz NOT NULL default now()

NOTE: the table has NO updated_at column — do not inherit BaseModel
(it would inject one and every write would fail with UndefinedColumn).
"""

import uuid

from django.db import models


class ExchangeRate(models.Model):
    """Exchange rates for currency conversion.

    Maps to core.exchange_rate table.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, db_column="id")
    org = models.ForeignKey(
        "core.Organisation",
        on_delete=models.CASCADE,
        db_column="org_id",
        related_name="exchange_rates",
    )
    # Natural-key FK to core.currency(code), not a surrogate UUID FK
    currency_code = models.CharField(max_length=3, db_column="currency_code")
    rate_date = models.DateField(db_column="rate_date")
    rate = models.DecimalField(max_digits=12, decimal_places=6, db_column="rate")
    source = models.CharField(max_length=50, blank=True, default="manual", db_column="source")
    created_at = models.DateTimeField(auto_now_add=True, db_column="created_at")

    class Meta:
        managed = False
        db_table = 'core"."exchange_rate'
        unique_together = [["org", "currency_code", "rate_date"]]

    def __str__(self):
        return f"{self.currency_code} @ {self.rate} ({self.rate_date})"
