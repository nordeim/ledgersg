"""
P32/BE-P32-M2 — the conftest fixture-placement contract.

The payment substrate fixture (an org, a bank account, a customer
contact and an APPROVED 109.00 invoice — 100.00 + 9% GST) must resolve
through pytest's OWN conftest discovery: a test in tests/integration/
that declares `payment_fixture` as a parameter gets it WITHOUT any
cross-module import.

The pre-P32 shape reached the fixture by importing it from a SIBLING
TEST MODULE (`from tests.integration.test_payment_allocation_contract_
p14 import payment_fixture`) — the import-is-the-side-effect pattern —
which shadowed the name against every consuming test's parameter
(ruff F811 ×24) and made the fixture's availability depend on an
implementation detail of another test file. The conftest placement is
the architectural fix: this spec is its gate. It failed on the base
tree (fixture 'payment_fixture' not found — no import, no resolution)
and must stay green for any future refactor of the integration tree.
"""

from decimal import Decimal

import pytest

from apps.banking.services import PaymentService
from common.exceptions import ValidationError
from tests.integration.test_payment_allocation_contract_p14 import _receive


class TestConftestFixtureResolutionP32:
    @pytest.mark.django_db
    def test_payment_fixture_resolves_without_import(self, payment_fixture):
        """The placement gate: conftest discovery, zero imports.

        RED on the base tree (the fixture lived only in the p14 module,
        reachable solely through the cross-module import); GREEN the
        moment the fixture takes its conftest home.
        """
        fx = payment_fixture

        # The substrate contract — the same shape every p14-era consumer
        # relies on (org + bank + contact + the APPROVED 109.00 invoice).
        assert fx["org"] is not None
        assert fx["user"] is not None
        assert fx["accounts"] is not None
        assert fx["bank"].account_name == "Test Operating"
        assert fx["contact"].is_customer is True
        assert fx["invoice"].status == "APPROVED"
        assert fx["invoice"].total_incl == Decimal("109.00")
        assert fx["invoice"].gst_total == Decimal("9.00")
        assert fx["invoice"].amount_paid == Decimal("0.0000")

    @pytest.mark.django_db
    def test_fixture_feeds_the_allocation_contract(self, payment_fixture):
        """The substrate still behaves: the H-1 allocation cap holds
        against the conftest-resolved fixture (a 5000.00 allocation
        against the 109.00 invoice is refused — the p14 headline)."""
        fx = payment_fixture
        payment = _receive(
            fx["org"], fx["user"], fx["bank"], fx["contact"], Decimal("5000.00")
        )
        with pytest.raises(ValidationError):
            PaymentService.allocate(
                org_id=fx["org"].id,
                payment_id=payment.id,
                allocations=[
                    {
                        "document_id": str(fx["invoice"].id),
                        "allocated_amount": "5000.00",
                    }
                ],
                user_id=fx["user"].id,
            )
