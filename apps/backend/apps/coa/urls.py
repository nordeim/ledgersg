"""
Chart of Accounts URL configuration.

Routes for account management, hierarchy, and trial balance.
"""

from django.urls import path

from .views import (
    AccountListCreateView,
    AccountDetailView,
    AccountBalanceView,
    AccountHierarchyView,
    AccountTypesView,
    TrialBalanceView,
    AccountSearchView,
)

app_name = "coa"

urlpatterns = [
    # Account list and create
    path("", AccountListCreateView.as_view(), name="account-list-create"),
    
    # Account search (must be before detail to avoid conflict)
    path("search/", AccountSearchView.as_view(), name="account-search"),
    
    # Account types
    path("types/", AccountTypesView.as_view(), name="account-types"),
    
    # Account hierarchy
    path("hierarchy/", AccountHierarchyView.as_view(), name="account-hierarchy"),
    
    # Trial balance
    path("trial-balance/", TrialBalanceView.as_view(), name="trial-balance"),
    
    # Account detail, update, delete
    path("<str:account_id>/", AccountDetailView.as_view(), name="account-detail"),
    
    # Account balance
    path("<str:account_id>/balance/", AccountBalanceView.as_view(), name="account-balance"),
]
