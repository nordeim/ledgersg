"""
Journal URL configuration.

Routes for journal entries and trial balance.
"""

from django.urls import path

from .views import (
    AccountBalanceView,
    EntryTypesView,
    JournalEntryDetailView,
    JournalEntryListCreateView,
    JournalEntryReversalView,
    JournalEntrySummaryView,
    LedgerView,
    TrialBalanceView,
    ValidateBalanceView,
)

app_name = "journal"

urlpatterns = [
    # Journal entries
    path("entries/", JournalEntryListCreateView.as_view(), name="entry-list-create"),
    path("ledger/", LedgerView.as_view(), name="ledger"),
    path("entries/summary/", JournalEntrySummaryView.as_view(), name="entry-summary"),
    path("entries/validate/", ValidateBalanceView.as_view(), name="entry-validate"),
    path("entries/types/", EntryTypesView.as_view(), name="entry-types"),
    path("entries/<uuid:entry_id>/", JournalEntryDetailView.as_view(), name="entry-detail"),
    path("entries/<uuid:entry_id>/reverse/", JournalEntryReversalView.as_view(), name="entry-reverse"),

    # Trial balance
    path("trial-balance/", TrialBalanceView.as_view(), name="trial-balance"),

    # Account balance
    path("accounts/<uuid:account_id>/balance/", AccountBalanceView.as_view(), name="account-balance"),
]
