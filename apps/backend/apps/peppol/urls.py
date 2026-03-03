"""
Peppol URL configuration.

Routes for InvoiceNow/Peppol integration endpoints.
"""

from django.urls import path
from .views import PeppolTransmissionLogView, PeppolSettingsView

app_name = "peppol"

urlpatterns = [
    path("transmission-log/", PeppolTransmissionLogView.as_view(), name="peppol-transmission-log"),
    path("settings/", PeppolSettingsView.as_view(), name="peppol-settings"),
]
