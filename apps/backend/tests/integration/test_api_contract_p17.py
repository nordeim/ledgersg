"""
P17 API-contract gates — the 400-vs-500 sweep.

BE-M1: filing with a non-numeric box override value must 400 (was an
    unhandled decimal.InvalidOperation → 500).
BE-M2: bulk allocation with a non-UUID document_id must 400 (audit
    reasoned 500; live-verified this sprint: DRF 3.18 already surfaces the
    django ValidationError as a non_field_errors 400 — this test PINS the
    contract so a serializer/DRF change cannot regress it silently).
BE-M6: PATCHing a tax code's rate outside 0..1 must 400 (was a raw DB
    CHECK violation → 500).
BE-L2: bank-transaction reconcile with a malformed id must 404 via the
    route (was raw UUID() ValueError → 500).
BE-M3: org PATCH normalizes + validates the UEN like create (was raw
    case-sensitive storage; the duplicate pre-check dodge).
BE-M5: reconciling a second bank transaction to the same payment must
    400 (was a silent double-count of the payment in bank rec).
"""

from datetime import date
from decimal import Decimal

import pytest
from rest_framework import status
from rest_framework.test import APIClient

from apps.core.models import (
    BankAccount,
    BankTransaction,
    DocumentSequence,
    GSTReturn,
    Payment,
)
from tests.conftest import create_test_contact, create_test_invoice


def _auth(client, user):
    from tests.conftest import get_auth_token

    client.credentials(HTTP_AUTHORIZATION=f"Bearer {get_auth_token(user)}")
    return client


class TestGSTFileBoxTypeContractP17:
    @pytest.mark.django_db
    def test_non_numeric_box_value_is_a_400(self, api_client, test_organisation, test_user):
        """BE-M1: `boxes: {"box1": "garbage"}` must surface as a typed
        field error, not a 500."""
        _auth(api_client, test_user)
        ret = GSTReturn.objects.create(
            org_id=test_organisation.id,
            period_start=date(2024, 1, 1),
            period_end=date(2024, 1, 31),
            filing_due_date=date(2024, 2, 29),
            status="COMPUTED",
            box1_std_rated_supplies=Decimal("1000.00"),
            box4_total_supplies=Decimal("1000.00"),
            box6_output_tax=Decimal("90.00"),
            box8_net_gst=Decimal("90.00"),
            box13_total_revenue=Decimal("1000.00"),
        )
        url = f"/api/v1/{test_organisation.id}/gst/returns/{ret.id}/file/"
        response = api_client.post(
            url,
            {
                "filing_reference": "IRAS-P17",
                "boxes": {"box1_std_rated_supplies": "garbage"},
            },
            format="json",
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST, (
            f"non-numeric box must 400, got {response.status_code}: {response.data}"
        )

    @pytest.mark.django_db
    def test_non_numeric_box_value_none_is_a_400(self, api_client, test_organisation, test_user):
        _auth(api_client, test_user)
        ret = GSTReturn.objects.create(
            org_id=test_organisation.id,
            period_start=date(2024, 2, 1),
            period_end=date(2024, 2, 29),
            filing_due_date=date(2024, 3, 31),
            status="COMPUTED",
        )
        url = f"/api/v1/{test_organisation.id}/gst/returns/{ret.id}/file/"
        response = api_client.post(
            url, {"filing_reference": "IRAS-P17", "boxes": {"box1_std_rated_supplies": None}},
            format="json",
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST, response.data


class TestBulkAllocationUUIDContractP17:
    @pytest.mark.django_db
    def test_non_uuid_document_id_is_a_400(
        self, api_client, test_organisation, test_user, test_accounts, test_fiscal_period
    ):
        """BE-M2: `"document_id": "abc"` must be a typed field error, not a
        raw Django ValidationError through the 500 handler."""
        from apps.banking.services import PaymentService

        _auth(api_client, test_user)
        org = test_organisation
        for doc_type, prefix in [
            ("SALES_INVOICE", "INV-"),
            ("PAYMENT_RECEIVED", "PAY-"),
        ]:
            DocumentSequence.objects.get_or_create(
                org=org, document_type=doc_type, defaults={"prefix": prefix, "next_number": 1}
            )
        bank = BankAccount.objects.create(
            org=org,
            gl_account=test_accounts["1200"],
            account_name="P17 Alloc Bank",
            bank_name="Test Bank",
            account_number="001-000-017",
            currency="SGD",
            paynow_type=None,
            is_active=True,
        )
        contact = create_test_contact(org, is_customer=True)
        invoice = create_test_invoice(org, contact, status="APPROVED")
        payment = PaymentService.create_received(
            org_id=org.id,
            data={
                "contact_id": str(contact.id),
                "bank_account_id": str(bank.id),
                "payment_date": date(2024, 1, 20).isoformat(),
                "amount": "109.00",
                "currency": "SGD",
                "exchange_rate": "1.000000",
                "payment_method": "BANK_TRANSFER",
            },
            user_id=test_user.id,
        )
        url = f"/api/v1/{org.id}/banking/payments/{payment.id}/allocate/"
        response = api_client.post(
            url,
            {"allocations": [{"document_id": "not-a-uuid", "allocated_amount": "10.00"}]},
            format="json",
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST, (
            f"non-UUID document_id must 400, got {response.status_code}: {response.data}"
        )


class TestTaxCodeRateRangeContractP17:
    @pytest.mark.django_db
    def test_update_rate_out_of_range_is_a_400(
        self, api_client, test_organisation, test_user, test_tax_codes
    ):
        """BE-M6: the update serializer must mirror the create-path 0..1
        rate gate; the DB CHECK (chk_rate_range) must never be the first
        line of defense (it 500s)."""
        _auth(api_client, test_user)
        sr = test_tax_codes["SR"]
        url = f"/api/v1/{test_organisation.id}/gst/tax-codes/{sr.id}/"
        response = api_client.patch(url, {"rate": "9"}, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST, (
            f"rate 9 must 400, got {response.status_code}: {response.data}"
        )
        sr.refresh_from_db()
        assert sr.rate == Decimal("0.09"), "the stored rate must be untouched"


class TestBankTransactionRouteUUIDContractP17:
    @pytest.mark.django_db
    def test_malformed_reconcile_id_is_404_not_500(
        self, api_client, test_organisation, test_user
    ):
        """BE-L2: the route must use the uuid converter — a malformed id
        is a routing 404, never a UUID() ValueError 500."""
        _auth(api_client, test_user)
        url = f"/api/v1/{test_organisation.id}/banking/bank-transactions/not-a-uuid/reconcile/"
        response = api_client.post(url, {"payment_id": "x"}, format="json")
        assert response.status_code == status.HTTP_404_NOT_FOUND, (
            f"malformed id must 404, got {response.status_code}"
        )

    @pytest.mark.django_db
    def test_malformed_unreconcile_id_is_404_not_500(
        self, api_client, test_organisation, test_user
    ):
        _auth(api_client, test_user)
        url = f"/api/v1/{test_organisation.id}/banking/bank-transactions/zzz/unreconcile/"
        response = api_client.post(url, format="json")
        assert response.status_code == status.HTTP_404_NOT_FOUND, response.status_code


class TestOrgPatchUENNormalizationP17:
    @pytest.mark.django_db
    def test_patch_normalizes_and_validates_uen(
        self, api_client, test_organisation, test_user
    ):
        """BE-M3: PATCH must run the create-path normalize+validate —
        lowercase input is stored normalized; an invalid form is a 400."""
        _auth(api_client, test_user)
        url = f"/api/v1/{test_organisation.id}/"
        response = api_client.patch(url, {"uen": " 91234567d "}, format="json")
        assert response.status_code == status.HTTP_200_OK, response.data
        test_organisation.refresh_from_db()
        assert test_organisation.uen == "91234567D", (
            f"PATCH must normalize the UEN (got {test_organisation.uen!r})"
        )

    @pytest.mark.django_db
    def test_patch_rejects_invalid_uen_form(
        self, api_client, test_organisation, test_user
    ):
        _auth(api_client, test_user)
        url = f"/api/v1/{test_organisation.id}/"
        response = api_client.patch(url, {"uen": "not-a-uen!!"}, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST, (
            f"invalid UEN form must 400, got {response.status_code}: {response.data}"
        )
        test_organisation.refresh_from_db()
        assert test_organisation.uen == "123456789A", "the stored UEN must be untouched"


class TestReconcilePaymentDoubleMatchP17:
    @pytest.mark.django_db
    def test_second_reconcile_of_same_payment_is_refused(
        self,
        api_client,
        test_organisation,
        test_user,
        test_accounts,
        test_fiscal_period,
    ):
        """BE-M5: a payment matched to bank transaction A must not be
        matchable to transaction B — the bank rec would double-count it."""
        from apps.banking.services import PaymentService

        _auth(api_client, test_user)
        org = test_organisation
        for doc_type, prefix in [("SALES_INVOICE", "INV-"), ("PAYMENT_RECEIVED", "PAY-")]:
            DocumentSequence.objects.get_or_create(
                org=org, document_type=doc_type, defaults={"prefix": prefix, "next_number": 1}
            )
        bank = BankAccount.objects.create(
            org=org,
            gl_account=test_accounts["1200"],
            account_name="P17 Rec Bank",
            bank_name="Test Bank",
            account_number="001-000-018",
            currency="SGD",
            paynow_type=None,
            is_active=True,
        )
        contact = create_test_contact(org, is_customer=True)
        create_test_invoice(org, contact, status="APPROVED")
        payment = PaymentService.create_received(
            org_id=org.id,
            data={
                "contact_id": str(contact.id),
                "bank_account_id": str(bank.id),
                "payment_date": date(2024, 1, 20).isoformat(),
                "amount": "109.00",
                "currency": "SGD",
                "exchange_rate": "1.000000",
                "payment_method": "BANK_TRANSFER",
            },
            user_id=test_user.id,
        )
        txn_a = BankTransaction.objects.create(
            org=org,
            bank_account=bank,
            transaction_date=date(2024, 1, 21),
            description="P17 match A",
            reference="REC-A",
            amount=Decimal("109.00"),
        )
        txn_b = BankTransaction.objects.create(
            org=org,
            bank_account=bank,
            transaction_date=date(2024, 1, 22),
            description="P17 match B",
            reference="REC-B",
            amount=Decimal("109.00"),
        )
        url_a = f"/api/v1/{org.id}/banking/bank-transactions/{txn_a.id}/reconcile/"
        first = api_client.post(url_a, {"payment_id": str(payment.id)}, format="json")
        assert first.status_code in (200, 201), first.data

        url_b = f"/api/v1/{org.id}/banking/bank-transactions/{txn_b.id}/reconcile/"
        second = api_client.post(url_b, {"payment_id": str(payment.id)}, format="json")
        assert second.status_code == status.HTTP_400_BAD_REQUEST, (
            f"double-matching a payment must 400, got {second.status_code}: {second.data}"
        )
