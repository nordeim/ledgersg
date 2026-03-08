"""
TDD Tests for Organisation Peppol Fields
Phase 1: Foundation
"""

import pytest
from apps.core.models import Organisation


@pytest.mark.django_db
def test_organisation_has_access_point_provider_field():
    """Test Organisation has access_point_provider field."""
    assert hasattr(Organisation, "access_point_provider")


@pytest.mark.django_db
def test_organisation_has_access_point_api_url_field():
    """Test Organisation has access_point_api_url field."""
    assert hasattr(Organisation, "access_point_api_url")


@pytest.mark.django_db
def test_organisation_has_access_point_api_key_field():
    """Test Organisation has access_point_api_key field."""
    assert hasattr(Organisation, "access_point_api_key")


@pytest.mark.django_db
def test_organisation_has_auto_transmit_field():
    """Test Organisation has auto_transmit field."""
    assert hasattr(Organisation, "auto_transmit")


@pytest.mark.django_db
def test_organisation_has_transmission_retry_attempts_field():
    """Test Organisation has transmission_retry_attempts field."""
    assert hasattr(Organisation, "transmission_retry_attempts")
