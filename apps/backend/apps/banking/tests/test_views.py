"""
Banking API View Tests (TDD)

Tests for Banking API endpoints.
Run with: pytest apps/banking/tests/test_views.py -v

SEC-001 Remediation: Tests validate serializer validation at view layer.
"""

import pytest
import uuid
from datetime import date
from decimal import Decimal
from django.contrib.auth.hashers import make_password

from apps.core.models import (
    AppUser,
    Organisation,
    Role,
    UserOrganisation,
    Account,
    BankAccount,
    BankTransaction,
    Payment,
    InvoiceDocument,
    FiscalYear,
    FiscalPeriod,
    Contact,
)
from apps.banking.serializers import (
    BankAccountCreateSerializer,
    BankAccountUpdateSerializer,
    PaymentReceiveSerializer,
    PaymentMakeSerializer,
    BankTransactionReconcileSerializer,
)

pytestmark = pytest.mark.django_db


@pytest.fixture
def test_user():
    """Create and return a test user."""
    user_id = uuid.uuid4()
    user = AppUser.objects.create(
        id=user_id,
        email=f"view_test_{user_id.hex[:8]}@example.com",
        full_name="View Test User",
        is_active=True,
    )
    user.password = make_password("testpassword123")
    user.save()
    return user


@pytest.fixture
def test_org(test_user):
    """Create organisation for testing."""
    org_id = uuid.uuid4()
    org = Organisation.objects.create(
        id=org_id,
        name="View Test Org",
        legal_name="View Test Org Pte Ltd",
        uen="VIEWTEST1",
        entity_type="PRIVATE_LIMITED",
        gst_registered=True,
        gst_reg_number="M11111111",
        gst_reg_date=date(2024, 1, 1),
        fy_start_month=1,
        base_currency="SGD",
        is_active=True,
    )

    owner_role = Role.objects.create(
        org=org,
        name="Owner",
        description="Full access",
        can_manage_org=True,
        can_manage_users=True,
        can_manage_coa=True,
        can_create_invoices=True,
        can_approve_invoices=True,
        can_void_invoices=True,
        can_create_journals=True,
        can_manage_banking=True,
        can_file_gst=True,
        can_view_reports=True,
        can_export_data=True,
        is_system=True,
    )

    UserOrganisation.objects.create(
        user=test_user,
        org=org,
        role=owner_role,
        is_default=True,
    )

    from django.db import connection

    with connection.cursor() as cursor:
        cursor.execute(
            """
            INSERT INTO core.document_sequence
            (org_id, document_type, prefix, next_number, padding)
            VALUES
                (%s, 'PAYMENT_RECEIVED', 'RCP-', 1, 5),
                (%s, 'PAYMENT_MADE', 'PAY-', 1, 5),
                (%s, 'SALES_INVOICE', 'INV-', 1, 5),
                (%s, 'JOURNAL_ENTRY', 'JE-', 1, 6)
            ON CONFLICT (org_id, document_type) DO NOTHING
            """,
            [str(org_id), str(org_id), str(org_id), str(org_id)],
        )

    fiscal_year = FiscalYear.objects.create(
        org=org,
        label="FY2024",
        start_date=date(2024, 1, 1),
        end_date=date(2024, 12, 31),
        is_closed=False,
    )
    FiscalPeriod.objects.create(
        org=org,
        fiscal_year_id=fiscal_year.id,
        label="Jan 2024",
        period_number=1,
        start_date=date(2024, 1, 1),
        end_date=date(2024, 1, 31),
        is_open=True,
    )

    return org


@pytest.fixture
def gl_account(test_org):
    """Create a GL account for bank accounts."""
    return Account.objects.create(
        org=test_org,
        code="1100",
        name="DBS Bank Account",
        account_type="ASSET",
        description="Main DBS Bank Account",
        is_active=True,
        is_bank=True,
    )


@pytest.fixture
def bank_account(test_org, gl_account, test_user):
    """Create a bank account via service."""
    from apps.banking.services import BankAccountService

    return BankAccountService.create(
        org_id=test_org.id,
        data={
            "account_name": "Main Operating Account",
            "bank_name": "DBS Bank",
            "account_number": "1234567890",
            "currency": "SGD",
            "gl_account": gl_account,
            "opening_balance": Decimal("10000.00"),
            "is_default": True,
        },
        user_id=test_user.id,
    )


@pytest.fixture
def customer(test_org):
    """Create a customer contact."""
    return Contact.objects.create(
        org=test_org,
        contact_type="CUSTOMER",
        name="Test Customer Pte Ltd",
        email="customer@test.com",
        is_active=True,
    )


@pytest.fixture
def payment(test_org, bank_account, customer, test_user):
    """Create a payment via service."""
    from apps.banking.services import PaymentService

    return PaymentService.create_received(
        org_id=test_org.id,
        data={
            "contact_id": customer.id,
            "bank_account_id": bank_account.id,
            "payment_date": date(2024, 1, 20),
            "amount": Decimal("1000.00"),
            "payment_method": "BANK_TRANSFER",
            "payment_reference": "REF-001",
        },
        user_id=test_user.id,
    )


class TestBankAccountSerializers:
    """Tests for BankAccount serializers (validates input at API layer)."""

    def test_bank_account_create_serializer_valid(self, test_org, gl_account):
        """Test BankAccountCreateSerializer validates valid data."""
        data = {
            "account_name": "New Account",
            "bank_name": "UOB Bank",
            "account_number": "9876543210",
            "currency": "SGD",
            "gl_account": gl_account.id,
            "opening_balance": "5000.00",
        }
        serializer = BankAccountCreateSerializer(data=data, context={"org_id": test_org.id})

        assert serializer.is_valid(), serializer.errors
        assert serializer.validated_data["account_name"] == "New Account"

    def test_bank_account_create_serializer_missing_field(self, test_org):
        """Test BankAccountCreateSerializer rejects missing required field."""
        data = {
            "account_name": "New Account",
            "bank_name": "UOB Bank",
        }
        serializer = BankAccountCreateSerializer(data=data, context={"org_id": test_org.id})

        assert not serializer.is_valid()
        assert "account_number" in serializer.errors

    def test_bank_account_update_serializer_valid(self, test_org):
        """Test BankAccountUpdateSerializer validates valid data."""
        data = {"account_name": "Updated Name"}
        serializer = BankAccountUpdateSerializer(
            data=data, partial=True, context={"org_id": test_org.id}
        )

        assert serializer.is_valid(), serializer.errors


class TestPaymentSerializers:
    """Tests for Payment serializers (validates input at API layer)."""

    def test_payment_receive_serializer_valid(self, test_org, bank_account, customer):
        """Test PaymentReceiveSerializer validates valid data."""
        data = {
            "contact_id": str(customer.id),
            "bank_account_id": str(bank_account.id),
            "payment_date": "2024-01-20",
            "amount": "1000.00",
            "payment_method": "BANK_TRANSFER",
        }
        serializer = PaymentReceiveSerializer(data=data, context={"org_id": test_org.id})

        assert serializer.is_valid(), serializer.errors

    def test_payment_receive_serializer_invalid_amount(self, test_org, bank_account, customer):
        """Test PaymentReceiveSerializer rejects negative amount."""
        data = {
            "contact_id": str(customer.id),
            "bank_account_id": str(bank_account.id),
            "payment_date": "2024-01-20",
            "amount": "-100.00",
            "payment_method": "BANK_TRANSFER",
        }
        serializer = PaymentReceiveSerializer(data=data, context={"org_id": test_org.id})

        assert not serializer.is_valid()

    def test_payment_make_serializer_valid(self, test_org, bank_account):
        """Test PaymentMakeSerializer validates valid data."""
        supplier = Contact.objects.create(
            org=test_org,
            contact_type="SUPPLIER",
            name="Test Supplier Pte Ltd",
            email="supplier@test.com",
            is_active=True,
            is_supplier=True,
        )
        data = {
            "contact_id": str(supplier.id),
            "bank_account_id": str(bank_account.id),
            "payment_date": "2024-01-20",
            "amount": "500.00",
            "payment_method": "GIRO",
        }
        serializer = PaymentMakeSerializer(data=data, context={"org_id": test_org.id})

        assert serializer.is_valid(), serializer.errors


class TestBankTransactionSerializers:
    """Tests for BankTransaction serializers."""

    def test_bank_transaction_reconcile_serializer_valid(self, test_org, payment):
        """Test BankTransactionReconcileSerializer validates valid data."""
        data = {
            "payment_id": str(payment.id),
        }
        serializer = BankTransactionReconcileSerializer(data=data, context={"org_id": test_org.id})

        assert serializer.is_valid(), serializer.errors


class TestViewIntegration:
    """Integration tests verifying services and serializers work together."""

    def test_full_bank_account_flow(self, test_org, gl_account, test_user):
        """Test full bank account creation flow."""
        from apps.banking.services import BankAccountService

        data = {
            "account_name": "Integration Test Account",
            "bank_name": "OCBC Bank",
            "account_number": "5555666677",
            "currency": "SGD",
            "gl_account": gl_account,
            "opening_balance": Decimal("2500.00"),
        }

        account = BankAccountService.create(
            org_id=test_org.id,
            data=data,
            user_id=test_user.id,
        )

        assert account.id is not None
        assert account.account_name == "Integration Test Account"
        assert account.bank_name == "OCBC Bank"

    def test_full_payment_flow(self, test_org, bank_account, customer, test_user):
        """Test full payment creation and allocation flow."""
        from apps.banking.services import PaymentService

        payment = PaymentService.create_received(
            org_id=test_org.id,
            data={
                "contact_id": customer.id,
                "bank_account_id": bank_account.id,
                "payment_date": date(2024, 1, 25),
                "amount": Decimal("2000.00"),
                "payment_method": "PAYNOW",
            },
            user_id=test_user.id,
        )

        assert payment.id is not None
        assert payment.payment_type == "RECEIVED"
        assert payment.amount == Decimal("2000.0000")


class TestPermissionChecks:
    """Tests for permission-related checks."""

    def test_role_has_banking_permission(self, test_org, test_user):
        """Test that Owner role has can_manage_banking=True."""
        user_org = (
            UserOrganisation.objects.filter(user=test_user, org=test_org)
            .select_related("role")
            .first()
        )

        assert user_org is not None
        assert user_org.role.can_manage_banking is True

    def test_viewer_role_no_banking_permission(self, test_org):
        """Test that Viewer role can be created without banking permission."""
        viewer_role = Role.objects.create(
            org=test_org,
            name="Viewer",
            description="Read only",
            can_manage_org=False,
            can_manage_users=False,
            can_manage_coa=False,
            can_create_invoices=False,
            can_approve_invoices=False,
            can_void_invoices=False,
            can_create_journals=False,
            can_manage_banking=False,
            can_file_gst=False,
            can_view_reports=True,
            can_export_data=False,
            is_system=True,
        )

        assert viewer_role.can_manage_banking is False
