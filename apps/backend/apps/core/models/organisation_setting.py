"""OrganisationSetting model - Organisation-specific configuration settings.

Aligned with core.organisation_setting (SQL-First: schema is the source of
truth):
    id            uuid PK
    org_id        uuid NOT NULL FK core.organisation
    setting_key   varchar(100) NOT NULL
    setting_value jsonb NOT NULL default '{}'
    description   text NULL
    created_at    timestamptz NOT NULL default now()
    updated_at    timestamptz NOT NULL default now()
    UNIQUE (org_id, setting_key)

The previous model declared value_type / category / is_encrypted columns
that do not exist in the schema and mis-typed setting_value as TextField —
the conformance gate (tests/invariants/test_schema_conformance.py) caught
this drift.
"""

from django.db import models

from common.models import TenantModel


class OrganisationSetting(TenantModel):
    """Organisation configuration settings.

    Maps to core.organisation_setting table.
    """

    setting_key = models.CharField(max_length=100, db_column="setting_key")
    setting_value = models.JSONField(db_column="setting_value", default=dict)
    description = models.TextField(blank=True, db_column="description")

    class Meta:
        managed = False
        db_table = 'core"."organisation_setting'
        unique_together = [["org", "setting_key"]]

    def __str__(self):
        return f"{self.org_id}: {self.setting_key}"
