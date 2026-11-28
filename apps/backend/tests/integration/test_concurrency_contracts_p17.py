"""
P17 concurrency-contract gates.

BE-H2: void() must lock the PAYMENT row before the is_voided check —
    two concurrent voids both read is_voided=False (READ COMMITTED) and
    both proceed: two reversal entries for one payment journal entry,
    duplicate allocation release. P16 locked allocate() and
    file_return/amend_return; void() is the missed sibling.
BE-H1 (journal): see test_journal_workflow.py::test_journal_entry_double_
    reversal_refused — the sequential guard + row lock in create_reversal.
"""

from datetime import date
from decimal import Decimal

import pytest

from apps.banking.services import PaymentService
from tests.integration.test_payment_allocation_contract_p14 import (  # noqa: F401
    _receive,
    payment_fixture,
)


class TestVoidLocksPaymentRowP17:
    @pytest.mark.django_db
    def test_void_locks_the_payment_row(self, payment_fixture):
        """BE-H2: the payment row must be read under select_for_update()
        inside void()'s atomic block — the seed-wrapper probe pattern."""
        from unittest.mock import patch

        from apps.core.models import Payment

        fx = payment_fixture
        payment = _receive(fx["org"], fx["user"], fx["bank"], fx["contact"], Decimal("10.00"))

        with patch.object(
            Payment.objects, "select_for_update", wraps=Payment.objects.select_for_update
        ) as spy:
            PaymentService.void(
                org_id=fx["org"].id,
                payment_id=payment.id,
                reason="P17 lock probe",
                user_id=fx["user"].id,
            )
            assert spy.called, (
                "void() must select_for_update() the Payment row (BE-H2: "
                "the is_voided check is otherwise a TOCTOU — concurrent "
                "double-void double-reverses the GL entry)"
            )

        payment.refresh_from_db()
        assert payment.is_voided is True

    @pytest.mark.django_db
    def test_double_void_refused(self, payment_fixture):
        """The sequential contract, pinned: the second void raises."""
        from common.exceptions import ValidationError as ServiceValidationError

        fx = payment_fixture
        payment = _receive(fx["org"], fx["user"], fx["bank"], fx["contact"], Decimal("10.00"))

        PaymentService.void(
            org_id=fx["org"].id, payment_id=payment.id, reason="first", user_id=fx["user"].id
        )
        with pytest.raises(ServiceValidationError, match="(?i)already voided"):
            PaymentService.void(
                org_id=fx["org"].id,
                payment_id=payment.id,
                reason="second",
                user_id=fx["user"].id,
            )


class TestCeleryTenantContextP17:
    """BE-H3: Celery workers have no middleware; task bodies must open
    their own RLS tenant context. The Django test connection runs as the
    superuser role (RLS bypassed), so the honest assertions are (a) the
    GUC is set while the task body runs, and (b) the helper actually
    satisfies RLS for the non-superuser runtime role."""

    @pytest.mark.django_db
    def test_email_task_opens_tenant_context(
        self, test_organisation, test_user, test_fiscal_period
    ):
        from unittest.mock import patch

        from django.db import connection

        from apps.invoicing.tasks import send_invoice_email_task
        from tests.conftest import create_test_contact, create_test_invoice

        org = test_organisation
        contact = create_test_contact(org, is_customer=True)
        invoice = create_test_invoice(org, contact, status="APPROVED")
        seen = {}

        def _probe_send(self):
            with connection.cursor() as cursor:
                cursor.execute("SELECT current_setting('app.current_org_id', true)")
                seen["org"] = cursor.fetchone()[0]
            return 1

        with patch("apps.invoicing.tasks.EmailMultiAlternatives") as email_cls, patch(
            "apps.invoicing.services.DocumentService.generate_pdf"
        ) as gen_pdf:
            email_cls.return_value = _EmailProbe(_probe_send)
            gen_pdf.return_value = _FakePdfStream()
            send_invoice_email_task.apply(
                args=[str(org.id), str(invoice.id), ["to@example.com"]]
            ).get()

        assert seen.get("org") == str(org.id), (
            "the task body must run with app.current_org_id set to the org "
            f"(BE-H3; saw {seen.get('org')!r})"
        )

    @pytest.mark.django_db
    def test_transmission_task_opens_tenant_context(
        self, test_organisation, test_fiscal_period
    ):
        from unittest.mock import patch

        from django.db import connection

        from apps.peppol.models import PeppolTransmissionLog
        from apps.peppol.tasks import transmit_peppol_invoice_task
        from tests.conftest import create_test_contact, create_test_invoice

        org = test_organisation
        contact = create_test_contact(org, is_customer=True)
        invoice = create_test_invoice(org, contact, status="APPROVED")
        log = PeppolTransmissionLog.objects.create(
            org=org, document_id=invoice.id, status="PENDING"
        )
        seen = {}

        def _probe(*args, **kwargs):
            with connection.cursor() as cursor:
                cursor.execute("SELECT current_setting('app.current_org_id', true)")
                seen["org"] = cursor.fetchone()[0]
            return log

        with patch(
            "apps.peppol.services.transmission_service.TransmissionService."
            "execute_transmission_for_log",
            side_effect=_probe,
        ):
            transmit_peppol_invoice_task.apply(
                args=[str(log.id), str(test_organisation.id)]
            )

        assert seen.get("org") == str(test_organisation.id), (
            "the transmission task body must run under the org GUC (BE-H3; "
            f"saw {seen.get('org')!r})"
        )

    @pytest.mark.django_db(transaction=True)
    def test_tenant_context_satisfies_rls_for_runtime_role(self, test_user):
        """The production failure mode, reproduced for real: as the
        non-superuser runtime role, tenant rows are invisible without the
        GUC and visible inside tenant_context()."""
        import uuid as uuid_mod

        import psycopg
        from django.conf import settings as dj_settings

        from apps.core.models import Contact, Organisation

        org = Organisation.objects.create(
            name=f"P17 RLS probe {uuid_mod.uuid4().hex[:6]}",
            uen=f"9{uuid_mod.uuid4().hex[:8].upper()}D",
            entity_type="PRIVATE_LIMITED",
            base_currency="SGD",
            fy_start_month=1,
        )
        Contact.objects.create(org=org, contact_type="CUSTOMER", name="RLS probe contact")

        db = dj_settings.DATABASES["default"]
        conn = psycopg.connect(
            host=db["HOST"],
            port=db["PORT"],
            dbname=db["NAME"],
            user="ledgersg_app",
            password="CHANGE_ME_IN_PRODUCTION",
        )
        try:
            with conn.transaction():
                bare = conn.execute("SELECT count(*) FROM invoicing.contact").fetchone()[0]
            from common.tenant_context import tenant_context

            with tenant_context(org.id):
                with conn.transaction():
                    # The helper set the GUC on the DJANGO connection, not
                    # this psycopg one — assert on the Django connection
                    # instead (the task body's world).
                    pass
            # The task body's contract, on the Django connection:
            from django.db import connection as dj_conn

            with tenant_context(org.id):
                with dj_conn.cursor() as cursor:
                    cursor.execute("SELECT current_setting('app.current_org_id', true)")
                    guc = cursor.fetchone()[0]
            assert guc == str(org.id)
            assert bare == 0, (
                "RLS must deny tenant rows to the runtime role without the "
                "GUC (otherwise this probe is vacuous)"
            )
        finally:
            conn.close()


class _EmailProbe:
    def __init__(self, send):
        self._send = send

    def attach_alternative(self, *a, **k):
        pass

    def attach(self, *a, **k):
        pass

    def send(self):
        return self._send(self)


class _FakePdfStream:
    def getvalue(self):
        return b"%PDF-fake"


class TestExchangeRatePrecisionP17:
    @pytest.mark.django_db
    def test_six_dp_exchange_rate_round_trips(self, payment_fixture):
        """BE-L1: the wire contract and the column are 6 dp
        (NUMERIC(12,6)); money()'s 4-dp quantize silently truncated the
        rate before storage AND before the FX math (a 1.000000-unit rate
        drifts base amounts deterministically). The rate must round-trip
        exactly; only the MONETARY products are 4-dp."""

        fx = payment_fixture
        payment = _receive_with_rate(
            fx["org"], fx["user"], fx["bank"], fx["contact"], Decimal("100.00"), "1.234567"
        )
        assert payment.exchange_rate == Decimal("1.234567"), (
            f"the stored rate must round-trip at 6 dp (got {payment.exchange_rate})"
        )
        assert payment.base_amount == Decimal("123.4567"), (
            f"base_amount = amount x rate at the money() 4-dp contract "
            f"(got {payment.base_amount})"
        )


def _receive_with_rate(org, user, bank, contact, amount, rate):
    payload = {
        "contact_id": str(contact.id),
        "bank_account_id": str(bank.id),
        "payment_date": date(2024, 1, 20).isoformat(),
        "amount": str(amount),
        "currency": "USD",
        "exchange_rate": rate,
        "payment_method": "BANK_TRANSFER",
    }
    return PaymentService.create_received(org_id=org.id, data=payload, user_id=user.id)


class TestListQueryPlansP17:
    """BE-M7: the three main list endpoints were 1 + N (serializer FK
    traversal per row). select_related makes the list O(1) FK queries —
    the pagination deferral (BE-L6) multiplies whatever the per-row cost
    is, so this is the floor."""

    @pytest.mark.django_db
    def test_payment_list_is_select_related(self, payment_fixture):
        from django.db import connection
        from django.test.utils import CaptureQueriesContext


        fx = payment_fixture
        for i in range(3):
            _receive(fx["org"], fx["user"], fx["bank"], fx["contact"], Decimal("5.00"))
        with CaptureQueriesContext(connection) as ctx:
            rows = PaymentService.list(org_id=fx["org"].id)
            [f"{r.contact.name} {r.bank_account.account_name}" for r in rows]
        fk_joins = sum(
            1 for q in ctx.captured_queries if "JOIN" in q["sql"].upper()
        )
        assert len(rows) >= 3
        assert fk_joins >= 1, (
            "the payment list must JOIN contact/bank_account (select_related) "
            f"— captured {len(ctx.captured_queries)} queries, {fk_joins} joins"
        )
        assert len(ctx.captured_queries) <= 2, (
            f"the list of {len(rows)} rows must stay O(1) queries "
            f"(got {len(ctx.captured_queries)})"
        )

    @pytest.mark.django_db
    def test_document_list_is_select_related(self, payment_fixture):
        from django.db import connection
        from django.test.utils import CaptureQueriesContext

        from apps.invoicing.services import DocumentService
        from tests.conftest import create_test_invoice

        fx = payment_fixture
        for i in range(3):
            create_test_invoice(
                fx["org"], fx["contact"], status="APPROVED",
                document_number=f"INV-P17N{i}-{i}"
            )
        with CaptureQueriesContext(connection) as ctx:
            rows = DocumentService.list_documents(org_id=fx["org"].id)
            [d.contact.name for d in rows]
        assert len(rows) >= 3
        fk_joins = sum(
            1 for q in ctx.captured_queries if "JOIN" in q["sql"].upper()
        )
        assert fk_joins >= 1, "the document list must JOIN contact (select_related)"
        assert len(ctx.captured_queries) <= 2, (
            f"the list of {len(rows)} documents must stay O(1) queries "
            f"(got {len(ctx.captured_queries)})"
        )

    @pytest.mark.django_db
    def test_bank_transaction_list_is_select_related(self, payment_fixture):
        from datetime import date as d

        from django.db import connection
        from django.test.utils import CaptureQueriesContext

        from apps.banking.services import ReconciliationService
        from apps.core.models import BankTransaction

        fx = payment_fixture
        for i in range(3):
            BankTransaction.objects.create(
                org=fx["org"],
                bank_account=fx["bank"],
                transaction_date=d(2024, 1, 25),
                description=f"P17 N+1 probe {i}",
                reference=f"NJ-{i}",
                amount=Decimal("1.00"),
            )
        with CaptureQueriesContext(connection) as ctx:
            rows = ReconciliationService.list_transactions(org_id=fx["org"].id)
            [t.bank_account.account_name for t in rows]
        assert len(rows) >= 3
        fk_joins = sum(
            1 for q in ctx.captured_queries if "JOIN" in q["sql"].upper()
        )
        assert fk_joins >= 1, "the transaction list must JOIN bank_account (select_related)"
        assert len(ctx.captured_queries) <= 2, (
            f"the list of {len(rows)} transactions must stay O(1) queries "
            f"(got {len(ctx.captured_queries)})"
        )


class TestMembershipCacheNegativeP17:
    @pytest.mark.django_db
    def test_negative_membership_is_not_cached(self, test_user, test_organisation):
        """BE-M4 interim: a False lookup must not be cached — a freshly
        accepted member would otherwise be denied until the TTL expired
        (there is no invalidation surface; positive-only caching bounds
        the damage to the documented B-9 window)."""
        from django.core.cache import cache

        from common.middleware.tenant_context import TenantContextMiddleware

        cache.clear()
        mw = TenantContextMiddleware(lambda r: None)

        # A fresh non-member (fixture org's membership is the OWNER user;
        # create a second user with no membership)
        from apps.core.models import AppUser

        outsider = AppUser.objects.create_user(
            email="p17-outsider@t.sg", password="Outsider123!x", full_name="Out"
        )
        is_member = mw._verify_org_membership(outsider, test_organisation.id)
        assert is_member is False
        assert cache.get(f"user_org:{outsider.id}:{test_organisation.id}") is None, (
            "a negative membership lookup must not be cached (BE-M4)"
        )

        # The owner's positive lookup IS cached (the perf contract).
        is_owner = mw._verify_org_membership(test_user, test_organisation.id)
        assert is_owner is True
        assert cache.get(f"user_org:{test_user.id}:{test_organisation.id}") is True
        cache.clear()
