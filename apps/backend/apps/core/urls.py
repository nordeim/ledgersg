"""
URL configuration for core app.

Routes for authentication (non-org-scoped) and organisation management (org-scoped).
"""

from django.urls import path

from apps.core.views.auth import (
    RegisterView,
    LoginView,
    LogoutView,
    RefreshTokenView,
    UserProfileView,
    ChangePasswordView,
)

from apps.core.views.organisations import (
    OrganisationListCreateView,
    OrganisationDetailView,
    GSTRegistrationView,
    FiscalYearListView,
    OrganisationSummaryView,
)


app_name = "core"

# Non-org-scoped URLs (authentication)
auth_urlpatterns = [
    path("auth/register/", RegisterView.as_view(), name="auth-register"),
    path("auth/login/", LoginView.as_view(), name="auth-login"),
    path("auth/logout/", LogoutView.as_view(), name="auth-logout"),
    path("auth/refresh/", RefreshTokenView.as_view(), name="auth-refresh"),
    path("auth/profile/", UserProfileView.as_view(), name="auth-profile"),
    path("auth/change-password/", ChangePasswordView.as_view(), name="auth-change-password"),
]

# Non-org-scoped organisation management
org_urlpatterns = [
    # List/create organisations
    path("organisations/", OrganisationListCreateView.as_view(), name="org-list-create"),
]

# Org-scoped URLs (require org_id in path)
org_scoped_urlpatterns = [
    # Organisation details
    path("<str:org_id>/", OrganisationDetailView.as_view(), name="org-detail"),
    
    # GST registration
    path("<str:org_id>/gst/", GSTRegistrationView.as_view(), name="org-gst"),
    
    # Fiscal years
    path("<str:org_id>/fiscal-years/", FiscalYearListView.as_view(), name="org-fiscal-years"),
    
    # Organisation summary/dashboard
    path("<str:org_id>/summary/", OrganisationSummaryView.as_view(), name="org-summary"),
]


# Export all URL patterns
urlpatterns = auth_urlpatterns + org_urlpatterns + org_scoped_urlpatterns
