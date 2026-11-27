"""
P21 contract gates — the list-envelope unification, the bank-account
default-flag locking, the dashboard-cache commit truth, the InvoiceNow
evidence stamp and the ValidateBalance 400 contract.

BE-P21-M6 (the envelope): the list layer speaks 5 shapes across 30 sites
    (19 {results, count} + 1 {results, totals} + 6 {data, count} +
    3 report-style {data: {...}} + 1 raw array). The unified contract:
    lists return {results, count}; single-report payloads keep {data}.
    Seven non-conforming list sites: organisations list, fiscal years,
    my_organisations (raw array), journal trial balance, entry types,
    IRAS tax-code info, the GST return-periods POST.
BE-P21-M1: the bank-account default flag is written by an unlocked
    plain read -> filter().update() -> full-row save() — two concurrent
    set_default calls can leave TWO defaults and the full-row save
    clobbers concurrently-committed opening_balance edits (the exact P20
    class on the banking config surface). Must lock + save(update_fields).
BE-P21-M2: the dashboard cache (dashboard:{org}, 5-min TTL) is invalidated
    by approve/payments/GST filing but NOT by void_document (which
    reverses ledger postings) nor by manual journal entries (create_entry)
    — the P5/H-3 completion.
BE-P21-M3: every mutation-path cache delete/invalidate runs INSIDE the
    open transaction (the P20 account_balance deletes, the dashboard
    invalidations) — a read in the delete->commit window re-seeds the
    pre-commit value and it survives to TTL. Must defer to
    transaction.on_commit.
BE-P21-M4: invoicenow_sent_at (the P16/L2 evidence column the
    void/unallocate restore reads: "SENT" if stamped else "APPROVED") is
    written by NOTHING — the branch is dead code. The Peppol DELIVERED
    branch must stamp the document.
BE-P21-M5: ValidateBalanceView parses raw request bodies with
    Decimal(str(line.get("debit", 0))) — "abc" -> InvalidOperation 500,
    lines-as-dict/string -> AttributeError 500. The P7/F-11 typed-400
    pattern, missed on this body.
"""

from datetime import date
from decimal import Decimal
from unittest.mock import Mock, patch
from uuid import uuid4

import pytest
from django.core.cache import cache
from rest_framework import status

from apps.banking.services import BankAccountService
from apps.core.models import BankAccount, InvoiceDocument
from apps.invoicing.services import DocumentService
from apps.journal.services import JournalService
from apps.reporting.services.dashboard_service import DashboardService

# ---------------------------------------------------------------------------
# fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def bank_accounts_fixture(
    test_organisation, test_user, test_accounts, test_tax_codes, test_fiscal_period
):
    """Two active bank accounts; the first is the current default — the
    set_default / update / deactivate surfaces."""
    from tests.conftest import create_test_contact

    org = test_organisation
    accounts = []
    for i, (name, is_default) in enumerate([("P21 Primary", True), ("P21 Second", False)]):
        accounts.append(
            BankAccount.objects.create(
                org=org,
                gl_account=test_accounts["1200"],
                account_name=name,
                bank_name="Test Bank",
                account_number=f"001-999-{i:03d}",
                currency="SGD",
                paynow_type=None,
                is_active=True,
                is_default=is_default,
                opening_balance=Decimal("100.00"),
            )
        )
    contact = create_test_contact(org, is_customer=True)
    return {"org": org, "user": test_user, "accounts": accounts, "contact": contact}


@pytest.fixture
def void_fixture(
    test_organisation, test_user, test_accounts, test_tax_codes, test_fiscal_period
):
    """One approved invoice + one allocated received payment — the
    void_document surface for the cache probes."""
    from tests.conftest import create_test_contact

    org = test_organisation
    from apps.core.models import DocumentSequence

    for doc_type, prefix in [
        ("PAYMENT_RECEIVED", "PAY-"),
        ("PAYMENT_MADE", "PAYM-"),
    ]:
        DocumentSequence.objects.get_or_create(
            org=org,
            document_type=doc_type,
            defaults={"prefix": prefix, "next_number": 1},
        )
    contact = create_test_contact(org, is_customer=True)
    invoice = InvoiceDocument.objects.create(
        org=org,
        document_type="SALES_INVOICE",
        contact=contact,
        document_number=f"INV-P21-{uuid4().hex[:8]}",
        issue_date=date(2024, 1, 10),
        due_date=date(2024, 2, 10),
        status="APPROVED",
        total_excl=Decimal("100.00"),
        gst_total=Decimal("0.00"),
        total_incl=Decimal("100.00"),
        amount_paid=Decimal("0.0000"),
    )
    # No payment allocations: void_document refuses allocated documents
    # ("unallocate the payments before voiding") — an unallocated
    # APPROVED invoice is the plain voidable surface. The bank row stays
    # because the fixture also feeds the create_entry probes' org setup.
    return {"org": org, "user": test_user, "invoice": invoice}


def _manual_entry_kwargs(fx, accounts_pair):
    return {
        "org_id": fx["org"].id,
        "entry_date": date(2024, 1, 15),
        "source_type": "MANUAL",
        "narration": "P21 cache probe",
        "lines": [
            {
                "account_id": str(accounts_pair[0].id),
                "debit": Decimal("50.00"),
                "credit": Decimal("0.00"),
                "description": "dr",
            },
            {
                "account_id": str(accounts_pair[1].id),
                "debit": Decimal("0.00"),
                "credit": Decimal("50.00"),
                "description": "cr",
            },
        ],
        "user_id": fx["user"].id,
    }


# ---------------------------------------------------------------------------
# BE-P21-M6 — the list-envelope unification
# ---------------------------------------------------------------------------


class TestListEnvelopeP21:
    """Lists return {results, count} — the single envelope key on every
    list surface (reports keep their {data: {...}} payload shape)."""

    @pytest.mark.django_db
    def test_organisations_list_uses_results(self, auth_client, test_organisation):
        response = auth_client.get("/api/v1/organisations/")
        assert response.status_code == status.HTTP_200_OK
        assert "results" in response.data, response.data
        assert "data" not in response.data
        assert response.data["count"] >= 1

    @pytest.mark.django_db
    def test_fiscal_years_uses_results(self, auth_client, test_organisation):
        response = auth_client.get(f"/api/v1/{test_organisation.id}/fiscal-years/")
        assert response.status_code == status.HTTP_200_OK
        assert "results" in response.data, response.data
        assert "data" not in response.data

    @pytest.mark.django_db
    def test_my_organisations_uses_results(self, auth_client, test_organisation):
        response = auth_client.get("/api/v1/auth/organisations/")
        assert response.status_code == status.HTTP_200_OK
        assert "results" in response.data, response.data
        assert "data" not in response.data
        assert response.data["count"] >= 1
        assert any(
            row["org"]["id"] == str(test_organisation.id)
            for row in response.data["results"]
        )

    @pytest.mark.django_db
    def test_trial_balance_uses_results(self, auth_client, test_organisation):
        response = auth_client.get(
            f"/api/v1/{test_organisation.id}/journal-entries/trial-balance/"
        )
        assert response.status_code == status.HTTP_200_OK
        assert "results" in response.data, response.data
        assert "data" not in response.data
        assert "totals" in response.data, "the P20 totals survive the rename"
        assert "as_of_date" in response.data

    @pytest.mark.django_db
    def test_entry_types_uses_results(self, auth_client, test_organisation):
        response = auth_client.get(
            f"/api/v1/{test_organisation.id}/journal-entries/entries/types/"
        )
        assert response.status_code == status.HTTP_200_OK
        assert "results" in response.data, response.data
        assert "data" not in response.data
        assert response.data["count"] >= 1

    @pytest.mark.django_db
    def test_iras_tax_code_info_uses_results(self, auth_client, test_organisation):
        response = auth_client.get(
            f"/api/v1/{test_organisation.id}/gst/tax-codes/iras-info/"
        )
        assert response.status_code == status.HTTP_200_OK
        assert "results" in response.data, response.data
        assert "data" not in response.data

    @pytest.mark.django_db
    def test_gst_return_periods_post_uses_results(self, auth_client, test_organisation):
        response = auth_client.post(
            f"/api/v1/{test_organisation.id}/gst/returns/",
            {"filing_frequency": "MONTHLY", "start_date": "2024-01-01", "periods": 1},
            format="json",
        )
        assert response.status_code == status.HTTP_201_CREATED, response.data
        assert "results" in response.data, response.data
        assert "data" not in response.data
        assert "message" in response.data, "the P19 message survives the rename"


# ---------------------------------------------------------------------------
# BE-P21-M1 — the bank-account default-flag locking
# ---------------------------------------------------------------------------


class TestBankAccountDefaultLockP21:

    @pytest.mark.django_db
    def test_set_default_takes_the_row_lock(self, bank_accounts_fixture):
        fx = bank_accounts_fixture
        real_sfu = BankAccount.objects.select_for_update
        with patch.object(
            BankAccount.objects, "select_for_update", wraps=real_sfu
        ) as spy:
            BankAccountService.set_default(fx["org"].id, fx["accounts"][1].id)
        assert spy.called, (
            "set_default must select_for_update() the org's bank-account rows — "
            "the unlocked read->clear->save sequence lets two concurrent "
            "set_default calls leave TWO defaults (BE-P21-M1)"
        )

    @pytest.mark.django_db
    def test_set_default_save_is_scoped_no_clobber(self, bank_accounts_fixture):
        """The full-row save clobbers concurrently-committed edits: T2
        commits an opening_balance change between T1's read and save —
        T1's save must not resurrect the stale in-memory value."""
        fx = bank_accounts_fixture
        target = fx["accounts"][1]

        original_save = BankAccount.save

        def racing_save(instance, *args, **kwargs):
            if instance.id == target.id:
                # T2's committed edit lands mid-T1 (T1 holds no lock
                # pre-fix, so nothing prevents it).
                BankAccount.objects.filter(id=instance.id).update(
                    opening_balance=Decimal("999.00")
                )
            return original_save(instance, *args, **kwargs)

        with patch.object(
            BankAccount, "save", side_effect=racing_save, autospec=True
        ):
            BankAccountService.set_default(fx["org"].id, target.id)

        target.refresh_from_db()
        assert target.opening_balance == Decimal("999.00"), (
            "set_default's save must be update_fields-scoped — the full-row "
            "write clobbered T2's committed opening_balance (BE-P21-M1)"
        )
        assert target.is_default is True
        fx["accounts"][0].refresh_from_db()
        assert fx["accounts"][0].is_default is False, "exactly one default remains"

    @pytest.mark.django_db
    def test_update_save_is_scoped(self, bank_accounts_fixture):
        fx = bank_accounts_fixture
        target = fx["accounts"][0]
        original_save = BankAccount.save

        captured = {}

        def racing_save(instance, *args, **kwargs):
            captured["update_fields"] = kwargs.get("update_fields")
            if instance.id == target.id:
                BankAccount.objects.filter(id=instance.id).update(
                    account_name="T2 rename"
                )
            return original_save(instance, *args, **kwargs)

        with patch.object(
            BankAccount, "save", side_effect=racing_save, autospec=True
        ):
            BankAccountService.update(
                fx["org"].id,
                target.id,
                {"account_name": "T1 rename"},
                user_id=fx["user"].id,
            )
        assert captured["update_fields"] is not None, (
            "update() must save(update_fields=...) — the full-row write "
            "clobbers concurrent edits (BE-P21-M1)"
        )

    @pytest.mark.django_db
    def test_deactivate_takes_the_row_lock(self, bank_accounts_fixture):
        fx = bank_accounts_fixture
        real_sfu = BankAccount.objects.select_for_update
        with patch.object(
            BankAccount.objects, "select_for_update", wraps=real_sfu
        ) as spy:
            BankAccountService.deactivate(
                fx["org"].id, fx["accounts"][1].id, user_id=fx["user"].id
            )
        assert spy.called, (
            "deactivate() must select_for_update() its target — the "
            "only-active-account check + the write race the same class"
        )


# ---------------------------------------------------------------------------
# BE-P21-M2 + M3 — the dashboard-cache invalidation + the on_commit truth
# ---------------------------------------------------------------------------


class TestDashboardCacheCommitTruthP21:

    @pytest.mark.django_db
    def test_void_registers_dashboard_invalidation_on_commit(
        self, void_fixture, django_capture_on_commit_callbacks
    ):
        fx = void_fixture

        with patch.object(DashboardService, "invalidate_dashboard_cache") as spy:
            with django_capture_on_commit_callbacks(execute=False) as callbacks:
                DocumentService.void_document(
                    fx["org"].id, fx["invoice"].id, fx["user"], reason="P21 cache probe"
                )
                assert spy.call_count == 0, (
                    "the invalidation must not run inside the transaction "
                    "(BE-P21-M3 — a read in the delete->commit window re-seeds "
                    "the stale value)"
                )

            assert callbacks, (
                "void_document must register the dashboard invalidation on "
                "commit (BE-P21-M2 — a void reverses ledger postings and "
                "changes outstanding AR the dashboard reads)"
            )
            for cb in callbacks:
                cb()
            assert spy.call_count == 1

    @pytest.mark.django_db
    def test_create_entry_registers_dashboard_invalidation_on_commit(
        self, void_fixture, test_accounts, django_capture_on_commit_callbacks
    ):
        fx = void_fixture
        with patch.object(DashboardService, "invalidate_dashboard_cache") as spy:
            with django_capture_on_commit_callbacks(execute=False) as callbacks:
                JournalService.create_entry(
                    **_manual_entry_kwargs(
                        fx, (test_accounts["1200"], test_accounts["4000"])
                    )
                )
                assert spy.call_count == 0, (
                    "the invalidation must not run inside the transaction "
                    "(BE-P21-M3)"
                )
            assert callbacks, (
                "create_entry must register the dashboard invalidation on "
                "commit (BE-P21-M2 — manual entries shift the revenue/expense "
                "totals the dashboard reads)"
            )
            for cb in callbacks:
                cb()
            assert spy.call_count == 1

    @pytest.mark.django_db
    def test_create_entry_defers_balance_cache_delete_to_commit(
        self, void_fixture, test_accounts, django_capture_on_commit_callbacks
    ):
        """The P20 account_balance delete must also move to on_commit —
        a balance GET between the delete and the commit re-seeds the
        pre-posting value and it survives to TTL."""
        fx = void_fixture
        balance_key = f"account_balance:{test_accounts['1200'].id}"
        cache.set(balance_key, "stale-balance")

        with django_capture_on_commit_callbacks(execute=False) as callbacks:
            JournalService.create_entry(
                **_manual_entry_kwargs(
                    fx, (test_accounts["1200"], test_accounts["4000"])
                )
            )
            assert cache.get(balance_key) is not None, (
                "the account_balance delete must wait for commit — running "
                "it inside the transaction re-seeds the stale value in the "
                "delete->commit window (BE-P21-M3)"
            )
        assert callbacks
        for cb in callbacks:
            cb()
        assert cache.get(balance_key) is None, (
            "executing the on_commit callbacks must delete the seeded key"
        )


# ---------------------------------------------------------------------------
# BE-P21-M4 — the InvoiceNow evidence stamp
# ---------------------------------------------------------------------------


class TestInvoicenowSentAtStampP21:

    @pytest.mark.django_db
    def test_delivered_transmission_stamps_the_document(self, test_organisation):
        from apps.peppol.models import PeppolTransmissionLog
        from apps.peppol.services.transmission_service import TransmissionService
        from tests.peppol.test_transmission_wiring import (
            _configure_peppol,
            _peppol_ready_invoice,
        )

        _configure_peppol(test_organisation)
        invoice = _peppol_ready_invoice(test_organisation)
        log = PeppolTransmissionLog.objects.create(
            org=test_organisation,
            document_id=invoice.id,
            status="PENDING",
            access_point_provider="storecove",
            attempt_number=1,
        )

        service = TransmissionService()
        mock_adapter = Mock()
        mock_adapter.send_invoice.return_value = _success_result()
        service.get_adapter_for_org = Mock(return_value=mock_adapter)
        service.mapping_service = Mock()
        service.mapping_service.map_invoice_to_ubl.return_value = {"demo": True}
        service.generator_service = Mock()
        service.generator_service.generate_invoice_xml.return_value = "<Invoice/>"
        service.generator_service.calculate_xml_hash.return_value = "hash"
        service.validation_service = Mock()
        service.validation_service.validate_invoice_xml.return_value = {
            "is_valid": True,
            "errors": [],
        }

        updated = service.execute_transmission_for_log(str(log.id))

        assert updated.status == "DELIVERED"
        invoice.refresh_from_db()
        assert invoice.invoicenow_sent_at is not None, (
            "a DELIVERED transmission must stamp invoicenow_sent_at — the "
            "evidence column the void/unallocate restore reads "
            '("SENT" if stamped else "APPROVED"); nothing writes it today '
            "(BE-P21-M4 — the branch is dead code)"
        )


def _success_result():
    from apps.peppol.services.ap_adapter_base import TransmissionResult

    return TransmissionResult.success(
        message_id=str(uuid4()), raw_response={"status": "accepted"}
    )


# ---------------------------------------------------------------------------
# BE-P21-M5 — the ValidateBalanceView typed-400 contract
# ---------------------------------------------------------------------------


class TestValidateBalance400P21:

    @pytest.mark.django_db
    def test_non_numeric_amount_is_a_400(self, auth_client, test_organisation):
        response = auth_client.post(
            f"/api/v1/{test_organisation.id}/journal-entries/entries/validate/",
            {
                "lines": [
                    {"debit": "abc", "credit": "0"},
                    {"debit": "0", "credit": "abc"},
                ]
            },
            format="json",
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST, (
            f"malformed numeric input must be a typed 400, got "
            f"{response.status_code} (BE-P21-M5 — InvalidOperation 500 today)"
        )

    @pytest.mark.django_db
    def test_lines_as_dict_is_a_400(self, auth_client, test_organisation):
        response = auth_client.post(
            f"/api/v1/{test_organisation.id}/journal-entries/entries/validate/",
            {"lines": {"a": 1, "b": 2}},
            format="json",
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST, (
            f"lines-as-dict must be a typed 400, got {response.status_code} "
            "(BE-P21-M5 — AttributeError 500 today)"
        )

    @pytest.mark.django_db
    def test_lines_as_string_is_a_400(self, auth_client, test_organisation):
        response = auth_client.post(
            f"/api/v1/{test_organisation.id}/journal-entries/entries/validate/",
            {"lines": "not-a-list"},
            format="json",
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    @pytest.mark.django_db
    def test_valid_body_still_validates(self, auth_client, test_organisation):
        response = auth_client.post(
            f"/api/v1/{test_organisation.id}/journal-entries/entries/validate/",
            {
                "lines": [
                    {"debit": "100.00", "credit": "0"},
                    {"debit": "0", "credit": "100.00"},
                ]
            },
            format="json",
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.data["valid"] is True
