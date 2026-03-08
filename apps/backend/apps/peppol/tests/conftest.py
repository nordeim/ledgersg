"""
pytest configuration for Peppol tests.

Ensures database is properly set up for tests.
"""

import pytest

# Import fixtures from main tests conftest
pytest_plugins = ["tests.conftest"]


@pytest.fixture(scope="session")
def django_db_setup():
    """Use existing test database - don't create new one."""
    pass


@pytest.fixture
def test_org(test_organisation):
    """Alias for test_organisation fixture."""
    return test_organisation


@pytest.fixture
def test_contact(test_organisation):
    """Create a test contact for Peppol tests."""
    from apps.core.models import Contact

    return Contact.objects.create(
        org=test_organisation,
        contact_type="CUSTOMER",
        name="Test Contact",
        company_name="Test Company Pte Ltd",
        legal_name="Test Company Private Limited",
        uen="202312345B",
        email="contact@example.com",
        is_customer=True,
        is_supplier=False,
        payment_terms_days=30,
        is_active=True,
    )
