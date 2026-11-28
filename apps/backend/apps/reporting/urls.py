"""
Reporting URL configuration.

Dashboard and financial reporting endpoints.
"""

from django.urls import path

from .views import (
    AgedReportView,
    DashboardAlertsView,
    DashboardMetricsView,
    FinancialReportView,
)

app_name = "reporting"

urlpatterns = [
    # Dashboard endpoints
    path("dashboard/metrics/", DashboardMetricsView.as_view(), name="dashboard-metrics"),
    path("dashboard/alerts/", DashboardAlertsView.as_view(), name="dashboard-alerts"),
    # Financial reports (P8/R-2: this module is mounted under the org-scoped
    # "reports/" prefix — the historical "reports/financial/" path doubled it
    # to /reports/reports/financial/, which no client could guess; the clean
    # path is /api/v1/{org}/reports/financial/. No consumer existed.)
    path("financial/", FinancialReportView.as_view(), name="financial-report"),
    # Aged receivables / payables (P8/R-5)
    path("aged/", AgedReportView.as_view(), name="aged-report"),
]
