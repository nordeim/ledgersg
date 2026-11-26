"""
LedgerSG API URL Configuration.

Root URL configuration. Mounts API version namespace /api/v1/,
health check endpoint, admin (development only).
"""

import logging

from django.contrib import admin
from django.urls import path, include
from django.http import JsonResponse
from django.db import connection
from django.conf import settings
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny

logger = logging.getLogger("ledgersg")

# CSP violation reporting endpoint (SEC-003)
from apps.core.views.security import csp_report_view

# Debug toolbar URLs — P11/H-5: gated on INSTALLED_APPS membership, the
# SAME knob development.py uses (the DEBUG_TOOLBAR env). The old
# settings.DEBUG gate crashed the documented DEBUG=true +
# DEBUG_TOOLBAR=false combination: the toolbar URLconf imported while
# the app was absent from INSTALLED_APPS ("Model class ... isn't in an
# application in INSTALLED_APPS" on every manage.py command).
if "debug_toolbar" in settings.INSTALLED_APPS:
    import debug_toolbar

    debug_urlpatterns = [path("__debug__/", include(debug_toolbar.urls))]
else:
    debug_urlpatterns = []


@api_view(["GET"])
@permission_classes([AllowAny])
def health_check(request):
    """
    Health check endpoint.

    Returns:
        200 OK if database and services are healthy
        503 Service Unavailable if any dependency is down
    """
    try:
        # Test database connection
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()

        return JsonResponse(
            {
                "status": "healthy",
                "database": "connected",
                "version": "1.0.0",
            },
            status=200,
        )
    except Exception as e:
        # P13/B-14: the operational detail goes to the log; the
        # unauthenticated 503 body carries only the generic status.
        logger.exception("Health check failed")
        return JsonResponse(
            {
                "status": "unhealthy",
                "database": "disconnected",
                "error": "A database error occurred. Check server logs for details.",
            },
            status=503,
        )


@api_view(["GET"])
@permission_classes([AllowAny])
def api_root(request):
    """
    API root endpoint.

    Returns available API endpoints.
    """
    return JsonResponse(
        {
            "name": "LedgerSG API",
            "version": "1.0.0",
            "endpoints": {
                "health": "/api/v1/health/",
                "auth": "/api/v1/auth/",
                "organisations": "/api/v1/organisations/",
                "docs": "https://docs.ledgersg.sg/api",
            },
        }
    )


# Org-scoped URLs - will be expanded as modules are built
org_scoped_urlpatterns = []

# Core module org-scoped URLs (org detail, gst, fiscal-years, summary)
try:
    from apps.core.urls import org_scoped_urlpatterns as core_org_urls

    # Include core org-scoped URLs at root of org_id path
    org_scoped_urlpatterns.append(path("", include(core_org_urls)))
except ImportError:
    pass

# Try to include app URLs if they exist
try:
    from apps.coa import urls as coa_urls

    org_scoped_urlpatterns.append(path("accounts/", include("apps.coa.urls")))
except ImportError:
    pass

try:
    org_scoped_urlpatterns.append(path("journal-entries/", include("apps.journal.urls")))
except ImportError:
    pass

try:
    org_scoped_urlpatterns.append(path("peppol/", include("apps.peppol.urls")))
except ImportError:
    pass

try:
    org_scoped_urlpatterns.append(path("reports/", include("apps.reporting.urls")))
except ImportError:
    pass

try:
    from apps.gst import urls as gst_urls

    org_scoped_urlpatterns.append(path("gst/", include("apps.gst.urls")))
except ImportError:
    pass

try:
    from apps.invoicing import urls as invoicing_urls

    org_scoped_urlpatterns.append(path("invoicing/", include("apps.invoicing.urls")))
except ImportError:
    pass

try:
    org_scoped_urlpatterns.append(path("banking/", include("apps.banking.urls")))
except ImportError:
    pass


urlpatterns = debug_urlpatterns + [
    # Health check
    path("health/", health_check, name="health"),
    # API v1
    path("api/v1/", api_root, name="api-root"),
    path("api/v1/health/", health_check, name="api-health"),
    # CSP violation reporting (SEC-003)
    path("api/v1/security/csp-report/", csp_report_view, name="csp-report"),
    # Core module (auth + organisations)
    path("api/v1/", include("apps.core.urls")),
    # Org-scoped modules (handled by tenant middleware)
    path("api/v1/<uuid:org_id>/", include(org_scoped_urlpatterns)),
]


# Admin — gated (P17/BE-L3): the comment said "development only in
# production" for three sprints while the route mounted unconditionally
# in every mode (a session-auth + password-reset attack surface in
# production). ENABLE_ADMIN=true opts in explicitly (e.g. a private ops
# network); production and testing boot with it OFF.
if getattr(settings, "ENABLE_ADMIN", False):
    urlpatterns.append(path("admin/", admin.site.urls))

