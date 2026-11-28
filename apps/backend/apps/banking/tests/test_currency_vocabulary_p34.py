"""
P34/BE-P34-M1: the ISO-4217 currency-input truth (banking surfaces).

Pre-P34: the banking validate_currency implementations checked only
len(value) == 3 — "XYZ" passed on bank-account create, payment receive
and payment make, and propagated into the P33 currency-truth surfaces.
The bank-account UPDATE path does not accept currency (verified — out of
scope); the document currency is a DB default, not an input.
"""

import uuid

import pytest

from apps.core.models import Account, AppUser, BankAccount, Contact, Organisation

pytestmark = pytest.mark.django_db


@pytest.fixture
def test_org():
    user_id = uuid.uuid4()
    org_id = uuid.uuid4()
    AppUser.objects.create(
        id=user_id,
        email=f"p34bank_{user_id.hex[:8]}@example.com",
        full_name="P34 Banking Tester",
        is_active=True,
    )
    return Organisation.objects.create(
        id=org_id,
        name="P34 Banking Org",
        legal_name="P34 Banking Org Pte Ltd",
        uen=f"T{org_id.hex[:9].upper()}",
        entity_type="PRIVATE_LIMITED",
        base_currency="SGD",
        gst_registered=False,
        fy_start_month=1,
    )


@pytest.fixture
def gl_account(test_org):
    return Account.objects.create(
        org=test_org,
        code="1100",
        name="DBS Bank Account",
        account_type="ASSET",
        is_active=True,
        is_bank=True,
    )


@pytest.fixture
def ar_account(test_org):
    return Account.objects.create(
        org=test_org,
        code="1200",
        name="Accounts Receivable",
        account_type="ASSET",
        is_active=True,
    )


@pytest.fixture
def ap_account(test_org):
    return Account.objects.create(
        org=test_org,
        code="2100",
        name="Accounts Payable",
        account_type="LIABILITY",
        is_active=True,
    )


@pytest.fixture
def bank_account(test_org, gl_account):
    return BankAccount.objects.create(
        org=test_org,
        account_name="Main Operating Account",
        bank_name="DBS Bank",
        account_number="1234567890",
        gl_account=gl_account,
        is_active=True,
        # the DB CHECK allows NULL or UEN/MOBILE/NRIC — the model default
        # "" violates it (the P9/B-4 contract)
        paynow_type=None,
        paynow_id=None,
    )


@pytest.fixture
def customer(test_org, ar_account):
    return Contact.objects.create(
        org=test_org,
        contact_type="CUSTOMER",
        name="P34 Customer Pte Ltd",
        email="customer@test.com",
        is_customer=True,
        is_supplier=False,
        payment_terms_days=30,
        receivable_account=ar_account,
    )


@pytest.fixture
def supplier(test_org, ap_account):
    return Contact.objects.create(
        org=test_org,
        contact_type="SUPPLIER",
        name="P34 Supplier Pte Ltd",
        email="supplier@test.com",
        is_customer=False,
        is_supplier=True,
        payment_terms_days=30,
        payable_account=ap_account,
    )


class TestBankAccountCurrencyVocabulary:
    """Bank-account create must reject out-of-vocabulary currency codes."""

    def test_bank_account_create_rejects_out_of_vocabulary_code(
        self, test_org, gl_account
    ):
        from apps.banking.serializers.bank_account import BankAccountCreateSerializer

        data = {
            "account_name": "Foreign Currency Account",
            "bank_name": "DBS Bank",
            "account_number": "9876543210",
            "currency": "XYZ",
            "gl_account": str(gl_account.id),
        }
        serializer = BankAccountCreateSerializer(
            data=data, context={"org_id": test_org.id}
        )

        assert not serializer.is_valid(), "'XYZ' is not an ISO-4217 currency"
        assert "currency" in serializer.errors

    def test_bank_account_create_normalizes_case(self, test_org, gl_account):
        from apps.banking.serializers.bank_account import BankAccountCreateSerializer

        data = {
            "account_name": "Foreign Currency Account",
            "bank_name": "DBS Bank",
            "account_number": "9876543211",
            "currency": "usd",
            "gl_account": str(gl_account.id),
        }
        serializer = BankAccountCreateSerializer(
            data=data, context={"org_id": test_org.id}
        )

        assert serializer.is_valid(), serializer.errors
        assert serializer.validated_data["currency"] == "USD"


class TestPaymentCurrencyVocabulary:
    """Payment receive/make must reject out-of-vocabulary currency codes."""

    def _receive_payload(self, bank_account, customer, currency):
        return {
            "contact_id": str(customer.id),
            "bank_account_id": str(bank_account.id),
            "payment_date": "2026-11-28",
            "amount": "1000.0000",
            "payment_method": "BANK_TRANSFER",
            "currency": currency,
        }

    def test_payment_receive_rejects_out_of_vocabulary_code(
        self, test_org, bank_account, customer
    ):
        from apps.banking.serializers.payment import PaymentReceiveSerializer

        serializer = PaymentReceiveSerializer(
            data=self._receive_payload(bank_account, customer, "XYZ"),
            context={"org_id": test_org.id},
        )

        assert not serializer.is_valid(), "'XYZ' is not an ISO-4217 currency"
        assert "currency" in serializer.errors

    def test_payment_receive_accepts_valid_code(
        self, test_org, bank_account, customer
    ):
        from apps.banking.serializers.payment import PaymentReceiveSerializer

        serializer = PaymentReceiveSerializer(
            data=self._receive_payload(bank_account, customer, "USD"),
            context={"org_id": test_org.id},
        )

        assert serializer.is_valid(), serializer.errors
        assert serializer.validated_data["currency"] == "USD"

    def test_payment_make_rejects_out_of_vocabulary_code(
        self, test_org, bank_account, supplier
    ):
        from apps.banking.serializers.payment import PaymentMakeSerializer

        data = {
            "contact_id": str(supplier.id),
            "bank_account_id": str(bank_account.id),
            "payment_date": "2026-11-28",
            "amount": "500.0000",
            "payment_method": "GIRO",
            "currency": "XYZ",
        }
        serializer = PaymentMakeSerializer(data=data, context={"org_id": test_org.id})

        assert not serializer.is_valid(), "'XYZ' is not an ISO-4217 currency"
        assert "currency" in serializer.errors
