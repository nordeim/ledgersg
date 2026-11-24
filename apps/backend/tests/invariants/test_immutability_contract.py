"""
Immutability contract (P13/B-5).

`ImmutableModel.save()` must raise the TYPED ImmutabilityError (a
LedgerSGException with status 409) so the API surfaces a clean 409
envelope — not the plain-Exception variant that falls through the
handler as a 500. The typed class already existed in
common/exceptions.py with zero raisers; this gate pins the wiring.
"""

import pytest

from common.exceptions import LedgerSGException
from common.models import ImmutableModel


class _CanaryImmutable(ImmutableModel):
    """Concrete subclass — enough to exercise the abstract save() guard."""

    class Meta:
        abstract = True
        managed = False


def test_immutable_save_raises_typed_exception():
    """
    RED for P13/B-5: saving an existing (pk set) immutable record must
    raise the LedgerSGException-typed ImmutabilityError.
    """
    from common import models as models_module

    # object.__new__ bypasses Model.__init__ (which refuses abstract
    # models); the save() guard only reads self.pk.
    canary = object.__new__(_CanaryImmutable)
    canary.pk = "00000000-0000-0000-0000-000000000001"

    with pytest.raises(models_module.ImmutabilityError) as excinfo:
        ImmutableModel.save(canary)

    assert isinstance(excinfo.value, LedgerSGException), (
        "ImmutableModel.save() raises a plain Exception variant — it must be "
        "the typed LedgerSGException (409) so the API contract holds (P13/B-5)."
    )
    assert excinfo.value.status_code == 409
    assert excinfo.value.code == "immutable_record"


def test_immutable_error_maps_to_409_envelope():
    """The typed error renders as a 409 through the DRF exception handler."""
    from rest_framework.test import APIRequestFactory

    from common.exceptions import custom_exception_handler
    from common.models import ImmutabilityError

    request = APIRequestFactory().post("/x", {})
    response = custom_exception_handler(
        ImmutabilityError("JournalEntry is immutable"), {"request": request, "view": None}
    )

    assert response is not None
    assert response.status_code == 409
    assert response.data["error"]["code"] == "immutable_record"
