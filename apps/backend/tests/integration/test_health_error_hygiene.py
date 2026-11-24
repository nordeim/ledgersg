"""
Health endpoint error hygiene (P13/B-14).

The 503 body used to embed `"error": str(e)` — raw database error strings
(hostnames, drivers, sometimes credentials in DSNs) to unauthenticated
callers. The operational detail belongs in the server log, not the
response.
"""

from unittest.mock import patch

import pytest


@pytest.mark.django_db
def test_health_503_does_not_leak_exception_details(db):
    """
    RED for P13/B-14: the unhealthy body must carry a generic message —
    the raw exception text must not reach the caller.
    """
    from django.test import RequestFactory

    from config.urls import health_check

    # A distinctive marker string that must never appear in the body.
    marker = "SECRET-HOSTNAME-LEAK-12345"
    request = RequestFactory().get("/health/")

    with patch(
        "django.db.connection.cursor",
        side_effect=RuntimeError(f"connection refused: {marker}"),
    ):
        response = health_check(request)

    assert response.status_code == 503
    import json

    body = json.loads(response.content)
    assert marker not in str(body), (
        f"The 503 body leaked the raw exception text ({body}) — operational "
        "detail belongs in the log, not the unauthenticated response."
    )
    assert body["status"] == "unhealthy"
    assert body["database"] == "disconnected"
