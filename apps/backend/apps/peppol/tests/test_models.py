"""
TDD Tests for Peppol Django Models
Phase 1: Foundation
"""

import pytest
from uuid import uuid4
from datetime import datetime

from apps.peppol.models import PeppolTransmissionLog, OrganisationPeppolSettings


@pytest.mark.django_db
def test_peppol_transmission_log_model_exists():
    """Test that PeppolTransmissionLog model can be imported."""
    assert PeppolTransmissionLog is not None


@pytest.mark.django_db
def test_peppol_transmission_log_is_unmanaged():
    """Test that model is unmanaged (SQL-First architecture)."""
    assert PeppolTransmissionLog._meta.managed is False


@pytest.mark.django_db
def test_peppol_transmission_log_table_name():
    """Test correct database table mapping."""
    assert PeppolTransmissionLog._meta.db_table == 'gst"."peppol_transmission_log'


@pytest.mark.django_db
def test_peppol_transmission_log_no_schema_attribute():
    """Test that Meta does not have invalid schema attribute."""
    assert not hasattr(PeppolTransmissionLog._meta, "schema")


@pytest.mark.django_db
def test_organisation_peppol_settings_model_exists():
    """Test that OrganisationPeppolSettings model can be imported."""
    assert OrganisationPeppolSettings is not None


@pytest.mark.django_db
def test_organisation_peppol_settings_is_unmanaged():
    """Test that settings model is unmanaged."""
    assert OrganisationPeppolSettings._meta.managed is False


@pytest.mark.django_db
def test_organisation_peppol_settings_table_name():
    """Test correct database table mapping."""
    assert OrganisationPeppolSettings._meta.db_table == 'gst"."organisation_peppol_settings'


@pytest.mark.django_db
def test_organisation_peppol_settings_no_schema_attribute():
    """Test that Meta does not have invalid schema attribute."""
    assert not hasattr(OrganisationPeppolSettings._meta, "schema")


@pytest.mark.django_db
def test_organisation_peppol_settings_has_is_configured_property():
    """Test that is_configured property exists."""
    settings = OrganisationPeppolSettings()
    assert hasattr(settings, "is_configured")
    assert settings.is_configured is False  # Not configured by default


@pytest.mark.django_db
def test_organisation_peppol_settings_is_configured_when_active():
    """Test is_configured returns True when properly configured."""
    settings = OrganisationPeppolSettings(
        org_id=uuid4(),
        access_point_provider="Storecove",
        access_point_api_url="https://api.storecove.com",
        access_point_api_key="test-key",
        is_active=True,
    )
    assert settings.is_configured is True
