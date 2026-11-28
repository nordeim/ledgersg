"""
P31 contract gates — the exception-chaining closure (B904).

BE-P31-H1: 66 production raise-inside-except sites relied on Python's
    IMPLICIT __context__ chaining — the "During handling of the above
    exception" wording that reads as an accident rather than a
    translation, and a chain any future refactor silently drops by
    moving the raise out of the except block. The closure makes the
    chain an explicit contract:

    Class A (62 sites) — `from exc`: the cause is preserved. Every
        lookup-miss translation (DoesNotExist -> ResourceNotFound /
        ValidationError), every race translation (IntegrityError ->
        the typed-400 bodies), the parse translations whose message
        embeds the value but not the original error string.
    Class B (4 sites) — `from None`: the raised message already embeds
        the original error's own string ({e}) — the suppressed context
        is pure duplication.

These gates pin the chaining truth the response-contract suites cannot
see (__cause__ / __suppress_context__ never touch the rendered HTTP
bodies — those bytes stay pinned by the existing suites).
"""

from uuid import uuid4

import pytest
from rest_framework import serializers

from common.decimal_utils import money
from common.exceptions import ResourceNotFound

# ---------------------------------------------------------------------------
# T1 — Class A, the service seam: a lookup-miss translation chains the
# DoesNotExist it translated (the "direct cause" rendering, never the
# ambiguous accidental-chain wording).
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestServiceLookupChainingP31:
    def test_get_document_not_found_chains_does_not_exist(self, test_organisation):
        from apps.core.models import InvoiceDocument
        from apps.invoicing.services import DocumentService

        with pytest.raises(ResourceNotFound) as exc_info:
            DocumentService.get_document(test_organisation.id, uuid4())

        cause = exc_info.value.__cause__
        assert isinstance(cause, InvoiceDocument.DoesNotExist), (
            f"ResourceNotFound must chain InvoiceDocument.DoesNotExist as "
            f"__cause__ (the P31 Class-A contract); got {cause!r}"
        )

    def test_get_transaction_not_found_chains_does_not_exist(self, test_organisation):
        from apps.banking.services import ReconciliationService
        from apps.core.models import BankTransaction

        with pytest.raises(ResourceNotFound) as exc_info:
            ReconciliationService.get_transaction(test_organisation.id, uuid4())

        cause = exc_info.value.__cause__
        assert isinstance(cause, BankTransaction.DoesNotExist), (
            f"ResourceNotFound must chain BankTransaction.DoesNotExist as "
            f"__cause__ (the P31 Class-A contract); got {cause!r}"
        )


# ---------------------------------------------------------------------------
# T2 — Class A, the serializer seam: a value-parse translation chains the
# original ValueError from money().
# ---------------------------------------------------------------------------


class TestSerializerParseChainingP31:
    def test_allocation_amount_parse_chains_value_error(self):
        from apps.banking.serializers import BulkAllocationSerializer

        with pytest.raises(serializers.ValidationError) as exc_info:
            BulkAllocationSerializer().validate_allocations(
                [{"document_id": str(uuid4()), "allocated_amount": "garbage"}]
            )

        cause = exc_info.value.__cause__
        assert isinstance(cause, ValueError), (
            f"the money-parse ValidationError must chain the original "
            f"ValueError as __cause__ (the P31 Class-A contract); got {cause!r}"
        )


# ---------------------------------------------------------------------------
# T3 — Class B, the deliberate suppression: money()'s message already
# embeds the original error string ("Cannot convert {value!r} to money:
# {e}") — the context is suppressed, not preserved.
# ---------------------------------------------------------------------------


class TestDeliberateSuppressionP31:
    def test_money_parse_error_suppresses_context(self):
        with pytest.raises(ValueError) as exc_info:
            money("garbage")

        assert exc_info.value.__cause__ is None, (
            "money() is a Class-B site: the message embeds the original "
            "error string, so __cause__ must stay None"
        )
        assert exc_info.value.__suppress_context__ is True, (
            "money() must raise from None (the P31 Class-B contract — the "
            "embedded {e} makes the implicit context pure duplication)"
        )
