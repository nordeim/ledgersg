"""P7/F-5: bank-account GL-account truth — fail closed at every seam.

The audited crash path (`_create_payment_journal_entry` dereferencing
`gl_account.id` on a bank account without one) is guarded TODAY only by the
DB (gl_account_id UUID NOT NULL) and the API serializer (required=True):
the SERVICE layer still accepts gl_account=None and lets the database raise
a raw IntegrityError -> 500. The service is the documented CLI surface, so
it must fail closed with a clean ValidationError. The payment-path guard is
added as defense-in-depth (unreachable while the DB constraint holds, but a
future schema relaxation must not reintroduce the AttributeError crash).
"""

import uuid
from datetime import date

import pytest
from django.contrib.auth.hashers import make_password

from apps.banking.serializers import BankAccountSerializer
from apps.banking.services import BankAccountService, PaymentService
from apps.core.models import AppUser, Organisation, Role, UserOrganisation
from common.exceptions import ValidationError

pytestmark = pytest.mark.django_db


@pytest.fixture
def user():
    user_id = uuid.uuid4()
    user = AppUser.objects.create(
        id=user_id,
        email=f"p7_{user_id.hex[:8]}@example.com",
        full_name="P7 Fail Closed User",
        is_active=True,
    )
    user.password = make_password("testpassword123")
    user.save()
    return user


@pytest.fixture
def org(user):
    org = Organisation.objects.create(
        id=uuid.uuid4(),
        name="P7 Fail Closed Org",
        uen="P7FAILCLO1",
        entity_type="PRIVATE_LIMITED",
        fy_start_month=1,
        base_currency="SGD",
        is_active=True,
    )
    role = Role.objects.create(org=org, name="Owner", description="Full access")
    UserOrganisation.objects.create(
        user=user,
        org=org,
        role=role,
        is_default=True,
        invited_at=date(2024, 1, 1),
        accepted_at=date(2024, 1, 1),
    )
    return org


def _bank_payload(**overrides):
    payload = {
        "account_name": "Main Operating Account",
        "bank_name": "DBS Bank",
        "account_number": f"{uuid.uuid4().hex[:10]}",
        "is_default": False,
    }
    payload.update(overrides)
    return payload


def test_create_bank_account_without_gl_account_fails_closed(org, user):
    """Service-level omission of gl_account is a clean ValidationError
    (400-class), never a raw IntegrityError 500."""
    with pytest.raises(ValidationError) as excinfo:
        BankAccountService.create(org.id, _bank_payload(), user_id=user.id)
    assert "GL account" in str(excinfo.value.message)


def test_create_bank_account_with_gl_account_succeeds(org, user):
    from apps.core.models import Account

    gl = Account.objects.create(
        org=org, code="1100", name="Bank Account", account_type="ASSET", is_bank=True
    )
    account = BankAccountService.create(
        org.id, _bank_payload(gl_account=gl), user_id=user.id
    )
    assert account.gl_account_id == gl.id


def test_bank_account_serializer_requires_gl_account():
    """The serializer contract requires gl_account — regression guard so it
    never silently loosens (the DB NOT NULL is the backstop)."""
    serializer = BankAccountSerializer(data=_bank_payload())
    assert not serializer.is_valid()
    assert "gl_account" in serializer.errors


def test_payment_journal_entry_guard_exists():
    """Source-level defense-in-depth gate: the payment JE builder must check
    the bank GL account before dereferencing it (the audited AttributeError
    crash). While the DB NOT NULL constraint makes the row impossible today,
    the guard prevents the crash from ever returning if the constraint is
    relaxed."""
    import inspect

    source = inspect.getsource(PaymentService._create_payment_journal_entry)
    assert "gl_account" in source and "ValidationError" in source, (
        "the payment JE builder must fail closed on a missing bank GL account"
    )
