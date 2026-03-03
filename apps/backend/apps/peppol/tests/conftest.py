"""
pytest configuration for Peppol tests.

Ensures database is properly set up for tests.
"""

import pytest


@pytest.fixture(scope="session")
def django_db_setup():
    """Use existing test database - don't create new one."""
    pass
