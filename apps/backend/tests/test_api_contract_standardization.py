"""
TDD Suite for API Contract Standardization.

Verifies that all list/collection endpoints return {"results": [...], "count": n}.
"""

import pytest
import uuid
from rest_framework import status
from apps.core.models import Account, BankAccount, BankTransaction
from decimal import Decimal
from datetime import date

@pytest.mark.django_db
class TestAPIContractStandardization:
    """Test suite to ensure consistent API response structure."""

    def test_account_list_contract(self, auth_client, test_organisation):
        """GET /api/v1/{org_id}/accounts/ - Should use 'results' and 'count'."""
        response = auth_client.get(f"/api/v1/{test_organisation.id}/accounts/")
        assert response.status_code == status.HTTP_200_OK
        assert "results" in response.data
        assert "count" in response.data
        assert isinstance(response.data["results"], list)

    def test_account_hierarchy_contract(self, auth_client, test_organisation):
        """GET /api/v1/{org_id}/accounts/hierarchy/ - Should use 'results' and 'count'."""
        response = auth_client.get(f"/api/v1/{test_organisation.id}/accounts/hierarchy/")
        assert response.status_code == status.HTTP_200_OK
        assert "results" in response.data
        assert "count" in response.data
        assert isinstance(response.data["results"], list)

    def test_account_types_contract(self, auth_client, test_organisation):
        """GET /api/v1/{org_id}/accounts/types/ - Should use 'results' and 'count'."""
        response = auth_client.get(f"/api/v1/{test_organisation.id}/accounts/types/")
        assert response.status_code == status.HTTP_200_OK
        assert "results" in response.data
        assert "count" in response.data
        assert isinstance(response.data["results"], list)

    @pytest.mark.skip(reason="Requires coa.account_balance view not present in test DB")
    def test_trial_balance_contract(self, auth_client, test_organisation):
        """GET /api/v1/{org_id}/accounts/trial-balance/ - Should use 'results' and 'count'."""
        response = auth_client.get(f"/api/v1/{test_organisation.id}/accounts/trial-balance/")
        assert response.status_code == status.HTTP_200_OK
        assert "results" in response.data
        assert "count" in response.data
        assert isinstance(response.data["results"], list)

    def test_account_search_contract(self, auth_client, test_organisation):
        """GET /api/v1/{org_id}/accounts/search/ - Should use 'results' and 'count'."""
        # Create a test account to ensure we have results
        # code must be numeric string 3-10 digits
        Account.objects.create(
            org=test_organisation,
            code="9999",
            name="Search Test Account",
            account_type="ASSET_CURRENT"
        )
        response = auth_client.get(f"/api/v1/{test_organisation.id}/accounts/search/?q=Search")
        assert response.status_code == status.HTTP_200_OK
        assert "results" in response.data
        assert "count" in response.data
        assert isinstance(response.data["results"], list)

    def test_bank_account_list_contract(self, auth_client, test_organisation):
        """GET /api/v1/{org_id}/banking/bank-accounts/ - Should use 'results' and 'count'."""
        response = auth_client.get(f"/api/v1/{test_organisation.id}/banking/bank-accounts/")
        assert response.status_code == status.HTTP_200_OK
        assert "results" in response.data
        assert "count" in response.data
        assert isinstance(response.data["results"], list)

    def test_payment_list_contract(self, auth_client, test_organisation):
        """GET /api/v1/{org_id}/banking/payments/ - Should use 'results' and 'count'."""
        response = auth_client.get(f"/api/v1/{test_organisation.id}/banking/payments/")
        assert response.status_code == status.HTTP_200_OK
        assert "results" in response.data
        assert "count" in response.data
        assert isinstance(response.data["results"], list)

    def test_bank_transaction_list_contract(self, auth_client, test_organisation):
        """GET /api/v1/{org_id}/banking/bank-transactions/ - Should use 'results' and 'count'."""
        response = auth_client.get(f"/api/v1/{test_organisation.id}/banking/bank-transactions/")
        assert response.status_code == status.HTTP_200_OK
        assert "results" in response.data
        assert "count" in response.data
        assert isinstance(response.data["results"], list)

    def test_bank_transaction_suggest_matches_contract(self, auth_client, test_organisation):
        """GET /api/v1/{org_id}/banking/bank-transactions/{id}/suggest-matches/ - Should use 'results' and 'count'."""
        
        # Create a COA account for the bank account
        gl_acc = Account.objects.create(
            org=test_organisation,
            code="1100",
            name="Bank GL Account",
            account_type="ASSET_CURRENT"
        )
        
        bank_acc = BankAccount.objects.create(
            org=test_organisation,
            account_name="Test Bank",
            account_number="123456789",
            bank_name="Test Bank",
            currency="SGD",
            gl_account=gl_acc,
            paynow_type=None,
            paynow_id=None
        )
        tx = BankTransaction.objects.create(
            org=test_organisation,
            bank_account=bank_acc,
            transaction_date=date.today(),
            amount=Decimal("100.00"),
            description="Test Tx"
        )
        
        response = auth_client.get(f"/api/v1/{test_organisation.id}/banking/bank-transactions/{tx.id}/suggest-matches/")
        assert response.status_code == status.HTTP_200_OK
        assert "results" in response.data
        assert "count" in response.data
        assert isinstance(response.data["results"], list)
