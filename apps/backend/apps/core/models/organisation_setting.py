"""OrganisationSetting model - Organisation-specific configuration settings."""

from django.db import models

from common.models import TenantModel


class OrganisationSetting(TenantModel):
    """Organisation configuration settings.

    Maps to core.organisation_setting table.
    """

    setting_key = models.CharField(max_length=100, db_column="key")
    setting_value = models.TextField(db_column="value")
    value_type = models.CharField(
        max_length=20,
        default="STRING",
        choices=[
            ("STRING", "String"),
            ("INTEGER", "Integer"),
            ("DECIMAL", "Decimal"),
            ("BOOLEAN", "Boolean"),
            ("JSON", "JSON"),
            ("DATE", "Date"),
        ],
    )
    category = models.CharField(max_length=50, default="GENERAL")
    description = models.TextField(blank=True)
    is_encrypted = models.BooleanField(default=False)

    class Meta:
        managed = False
        db_table = 'core"."organisation_setting'
        unique_together = [["org", "setting_key"]]

    def __str__(self):
        return f"{self.org.name}: {self.setting_key}"
