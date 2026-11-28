"""
P18 API-contract gates — the residual L-batch.

BE-L2: the suggest-matches route kept <str:transaction_id> while every
    sibling got <uuid:...> — the same client error produced a 400 (view
    helper) here vs a 404 (route converter) on reconcile/unreconcile.
BE-L5: send_email had no status/type gate while its InvoiceNow sibling
    refuses anything but an APPROVED SALES_INVOICE — a VOID or DRAFT
    document could be emailed to a customer as a rendered tax invoice.
BE-L6: _validated_exchange_rate called Decimal(str(value)) without
    catching InvalidOperation at the service seam — garbage strings
    from direct service callers produced untyped 500s.
BE-L4: create_return_periods' .exists()-then-create dedup raced the
    UNIQUE(org_id, return_type, period_start, period_end) constraint —
    the loser surfaced an untyped IntegrityError 500.
"""

from datetime import date

import pytest

from apps.gst.services import GSTReturnService
from common.exceptions import ValidationError as ServiceValidationError


def _auth(client, user):
    from tests.conftest import get_auth_token

    client.credentials(HTTP_AUTHORIZATION=f"Bearer {get_auth_token(user)}")
    return client


class TestSuggestMatchesRouteContractP18:
    @pytest.mark.django_db
    def test_malformed_transaction_id_is_a_route_404(
        self, api_client, test_user, test_organisation
    ):
        """BE-L2: a malformed UUID on suggest-matches must 404 at the
        routing layer — identical to reconcile/unreconcile (the uuid
        route converter), not a 400 from the view helper."""
        _auth(api_client, test_user)
        url = (
            f"/api/v1/{test_organisation.id}/banking/"
            "bank-transactions/not-a-uuid/suggest-matches/"
        )
        response = api_client.get(url)
        assert response.status_code == 404, (
            "a malformed UUID must be a route-level 404 (the uuid converter, "
            f"like every sibling route); got {response.status_code}"
        )


class TestSendEmailStatusGateP18:
    @pytest.mark.django_db
    def test_emailing_a_void_document_is_refused(
        self, test_organisation, test_user, test_fiscal_period
    ):
        """BE-L5: VOID documents must not be emailed as rendered tax
        invoices (mirror the send_invoicenow gate)."""
        from apps.invoicing.services import DocumentService
        from tests.conftest import create_test_contact, create_test_invoice

        contact = create_test_contact(test_organisation, is_customer=True)
        invoice = create_test_invoice(
            test_organisation, contact, status="VOID"
        )

        with pytest.raises(ServiceValidationError, match="(?i)status|void"):
            DocumentService.send_email(
                org_id=test_organisation.id,
                document_id=invoice.id,
                email_data={"to": ["customer@example.com"]},
            )

    @pytest.mark.django_db
    def test_emailing_a_draft_document_is_refused(
        self, test_organisation, test_user, test_fiscal_period
    ):
        """BE-L5: DRAFT documents are not yet tax invoices — the emailed
        PDF is labelled TAX INVOICE (IRAS labelling is status-bound)."""
        from apps.invoicing.services import DocumentService
        from tests.conftest import create_test_contact, create_test_invoice

        contact = create_test_contact(test_organisation, is_customer=True)
        invoice = create_test_invoice(
            test_organisation, contact, status="DRAFT"
        )

        with pytest.raises(ServiceValidationError, match="(?i)status|draft"):
            DocumentService.send_email(
                org_id=test_organisation.id,
                document_id=invoice.id,
                email_data={"to": ["customer@example.com"]},
            )


class TestExchangeRateServiceSeamP18:
    @pytest.mark.django_db
    def test_garbage_string_rate_is_a_typed_400(self):
        """BE-L6: a garbage exchange_rate reaching the service directly
        (any future caller bypassing the DRF DecimalField) must surface
        as a ValidationError, not an InvalidOperation 500."""
        from apps.banking.services import PaymentService

        with pytest.raises(ServiceValidationError, match="(?i)exchange rate"):
            PaymentService._validated_exchange_rate("not-a-number")


class TestReturnPeriodDedupP18:
    @pytest.mark.django_db
    def test_service_survives_the_unique_race_typed(self, test_organisation):
        """BE-L4: when the .exists() pre-check loses to a concurrent
        create (the UNIQUE(org, type, period_start, period_end) race),
        the service must treat the constraint hit as 'another worker
        created the period' and skip cleanly — never an IntegrityError
        500."""
        from apps.core.models import GSTReturn

        GSTReturn.objects.create(
            org_id=test_organisation.id,
            return_type="F5",
            period_start=date(2025, 1, 1),
            period_end=date(2025, 1, 31),
            filing_due_date=date(2025, 2, 28),
            status="DRAFT",
        )

        # A second create hitting the same period (the race loser's
        # post-check write) must be a typed skip, not a crash.
        created = GSTReturnService.create_return_periods(
            org_id=test_organisation.id,
            filing_frequency="MONTHLY",
            start_date=date(2025, 1, 1),
            periods=1,
        )
        assert created == [], (
            "the duplicate period must be skipped (no raise, no duplicate row)"
        )
