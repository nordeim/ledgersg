"""
Core URL configuration.

Routes for authentication (non-org-scoped) and organisation management.
"""

from django.urls import path, include

from apps.core.views.organisations import (
    OrganisationDetailView,
    GSTRegistrationView,
    FiscalYearListView,
    OrganisationSummaryView,
    OrganisationSettingsView,
)
from apps.core.views.fiscal import (
    FiscalPeriodListView,
    FiscalYearCloseView,
    FiscalPeriodCloseView,
    FiscalPeriodOpenView,
)


# Non-org-scoped URLs
urlpatterns = [
    path("auth/", include("apps.core.urls.auth")),
    path("organisations/", include("apps.core.urls.organisation")),
    path("users/", include("apps.core.urls.user")),
    path("fiscal/", include("apps.core.urls.fiscal")),
]

# Org-scoped URLs (mounted under api/v1/<uuid:org_id>/ in config/urls.py)
# DO NOT include org_id in these patterns - it's already in the URL prefix
org_scoped_urlpatterns = [
    # Organisation detail - mounted at api/v1/{org_id}/
    path("", OrganisationDetailView.as_view(), name="org-detail"),
    # GST registration - mounted at api/v1/{org_id}/gst/
    path("gst/", GSTRegistrationView.as_view(), name="org-gst"),
    # Fiscal years - mounted at api/v1/{org_id}/fiscal-years/
    path("fiscal-years/", FiscalYearListView.as_view(), name="org-fiscal-years"),
    # Fiscal periods - mounted at api/v1/{org_id}/fiscal-periods/
    # (P7/F-4: previously only in the shadowed apps/core/urls.py module, so
    # the endpoint 404'd; routed here in the ACTIVE package.)
    path("fiscal-periods/", FiscalPeriodListView.as_view(), name="org-fiscal-periods"),
    # Fiscal year close - api/v1/{org_id}/fiscal-years/{year_id}/close/
    path(
        "fiscal-years/<str:year_id>/close/",
        FiscalYearCloseView.as_view(),
        name="fiscal-year-close",
    ),
    # Fiscal period close - api/v1/{org_id}/fiscal-periods/{period_id}/close/
    path(
        "fiscal-periods/<str:period_id>/close/",
        FiscalPeriodCloseView.as_view(),
        name="fiscal-period-close",
    ),
    # Fiscal period open - api/v1/{org_id}/fiscal-periods/{period_id}/open/
    # (P10/M-8: the symmetric act — the approval error named it but no
    # endpoint could perform it)
    path(
        "fiscal-periods/<str:period_id>/open/",
        FiscalPeriodOpenView.as_view(),
        name="fiscal-period-open",
    ),
    # Organisation summary - mounted at api/v1/{org_id}/summary/
    path("summary/", OrganisationSummaryView.as_view(), name="org-summary"),
    # Organisation settings - mounted at api/v1/{org_id}/settings/
    path("settings/", OrganisationSettingsView.as_view(), name="org-settings"),
]
