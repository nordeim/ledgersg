"""
P14/H-05b + H-04b — the F5 override-evidence control and NRIC masking.

H-05b (audit-2): a filer may override computed F5 boxes 6/7 and 9-15 —
legitimate judgment (bad-debt relief, tourist refunds,
pre-registration claims) but previously ungated: figures could diverge
from the subledger on a free-text trail. Filing with box overrides now
REQUIRES an override reason (>= 10 chars) and the reason + the
computed-vs-filed deltas are persisted into `notes` (the same
documented decision amend_return uses — schema unchanged).

H-04b (audit-2): NRIC-type PayNow identifiers are PDPA protected
identifiers — masked by default on read (S*****67A), and a masked echo
(containing '*') cannot be persisted back through the write path.
"""

from datetime import date
from decimal import Decimal
import uuid

import pytest

from common.exceptions import ValidationError
from apps.core.models import GSTReturn, BankAccount, Contact, InvoiceDocument
from apps.gst.services import GSTReturnService
from apps.gst.serializers import GSTReturnFileSerializer
from apps.banking.serializers.bank_account import BankAccountSerializer
from tests.conftest import create_test_contact


@pytest.fixture
def filed_base(test_organisation, test_user):
    ret = GSTReturn.objects.create(
        org_id=test_organisation.id,
        period_start=date(2024, 1, 1),
        period_end=date(2024, 1, 31),
        filing_due_date=date(2024, 2, 29),
        status="COMPUTED",
        box1_std_rated_supplies=Decimal("1000.00"),
        box4_total_supplies=Decimal("1000.00"),
        box6_output_tax=Decimal("90.00"),
        box7_input_tax_claimable=Decimal("0"),
        box8_net_gst=Decimal("90.00"),
        box13_total_revenue=Decimal("1000.00"),
    )
    return ret


class TestF5OverrideControlP14:
    @pytest.mark.django_db
    def test_file_with_boxes_but_no_reason_is_refused(self, test_organisation, test_user, filed_base):
        """RED for H-05b: overrides without a reason are a 400."""
        with pytest.raises(ValidationError) as excinfo:
            GSTReturnService.file_return(
                org_id=test_organisation.id,
                return_id=filed_base.id,
                filed_by_id=test_user.id,
                filing_reference="IRAS-OVR-1",
                boxes={"box6_output_tax": Decimal("85.00")},
            )
        assert "reason" in str(excinfo.value).lower()

    @pytest.mark.django_db
    def test_file_with_boxes_and_reason_persists_the_trail(self, test_organisation, test_user, filed_base):
        """H-05b: with a real reason the filing succeeds AND the notes carry
        the reason + the computed-vs-filed delta (auditable evidence)."""
        result = GSTReturnService.file_return(
            org_id=test_organisation.id,
            return_id=filed_base.id,
            filed_by_id=test_user.id,
            filing_reference="IRAS-OVR-2",
            boxes={"box6_output_tax": Decimal("85.00")},
            override_reason="Bad-debt relief adjustment for Feb write-off (audited schedule BD-7 attached)",
        )
        assert result.status == "FILED"
        assert result.box6_output_tax == Decimal("85.00")
        assert "box6_output_tax" in (result.notes or ""), (
            "the override trail must persist the box delta in notes"
        )
        assert "Bad-debt relief" in (result.notes or "")

    @pytest.mark.django_db
    def test_file_without_boxes_needs_no_reason(self, test_organisation, test_user, filed_base):
        """Control: filing the computed figures unchanged stays reason-free."""
        result = GSTReturnService.file_return(
            org_id=test_organisation.id,
            return_id=filed_base.id,
            filed_by_id=test_user.id,
            filing_reference="IRAS-PLAIN-1",
        )
        assert result.status == "FILED"

    @pytest.mark.django_db
    def test_short_reason_is_refused(self, test_organisation, test_user, filed_base):
        """H-05b: a 3-char 'reason' is not evidence."""
        with pytest.raises(ValidationError):
            GSTReturnService.file_return(
                org_id=test_organisation.id,
                return_id=filed_base.id,
                filed_by_id=test_user.id,
                filing_reference="IRAS-OVR-3",
                boxes={"box9_imports_under_schemes": Decimal("50.00")},
                override_reason="fix",
            )

    def test_serializer_exposes_override_reason(self):
        """The wire contract carries the new field."""
        serializer = GSTReturnFileSerializer(
            data={"filing_reference": "R", "boxes": {"box6_output_tax": "1"},
                  "override_reason": "a real reason here"}
        )
        assert serializer.is_valid(), serializer.errors
        assert serializer.validated_data["override_reason"] == "a real reason here"


class TestNRICMaskingP14:
    @pytest.fixture
    def bank_fx(self, test_organisation, test_user, test_accounts):
        contact = create_test_contact(test_organisation, is_customer=True)
        return {"org": test_organisation, "user": test_user, "accounts": test_accounts, "contact": contact}

    def _bank(self, fx, paynow_type, paynow_id):
        return BankAccount.objects.create(
            org=fx["org"],
            gl_account=fx["accounts"]["1100"] if "1100" in fx["accounts"] else fx["accounts"]["1200"],
            account_name="Mask Probe",
            bank_name="TB",
            account_number=f"00{uuid.uuid4().hex[:8]}",
            currency="SGD",
            paynow_type=paynow_type,
            paynow_id=paynow_id,
            is_active=True,
        )

    @pytest.mark.django_db
    def test_nric_paynow_id_is_masked_on_read(self, bank_fx, rf, test_user):
        """RED for H-04b: NRIC paynow ids never round-trip in full."""
        bank = self._bank(bank_fx, "NRIC", "S1234567D")
        request = rf.get("/api/v1/x/banking/bank-accounts/")
        request.user = test_user
        data = BankAccountSerializer(bank, context={"request": request}).data
        pid = data.get("paynow_id") or ""
        assert "S1234567D" not in pid, f"NRIC leaked in full: {pid!r}"
        assert "*" in pid, f"expected a masked value, got {pid!r}"

    @pytest.mark.django_db
    def test_mobile_paynow_id_is_not_masked(self, bank_fx, rf, test_user):
        """Control: mobile/UEN proxies are not PDPA protected identifiers."""
        bank = self._bank(bank_fx, "MOBILE", "91234567")
        request = rf.get("/api/v1/x/banking/bank-accounts/")
        request.user = test_user
        data = BankAccountSerializer(bank, context={"request": request}).data
        assert data.get("paynow_id") == "91234567"

    @pytest.mark.django_db
    def test_masked_echo_cannot_be_persisted(self, bank_fx, test_user):
        """H-04b: a value containing '*' (a masked read echoed back through
        PATCH) is rejected — it would corrupt the stored identifier."""
        from apps.banking.serializers.bank_account import BankAccountCreateSerializer

        serializer = BankAccountCreateSerializer(
            data={
                "account_name": "Echo Probe",
                "bank_name": "TB",
                "account_number": "001234567",
                "currency": "SGD",
                "gl_account": (fx := bank_fx)["accounts"]["1200"].id,
                "paynow_type": "NRIC",
                "paynow_id": "S*****67D",
            }
        )
        assert not serializer.is_valid(), (
            "a masked echo must be rejected on write (it would persist the mask)"
        )
        assert "paynow_id" in serializer.errors

    @pytest.mark.django_db
    def test_fresh_nric_can_be_persisted(self, bank_fx):
        """Control: creating with a real NRIC still works (masked only on read)."""
        from apps.banking.serializers.bank_account import BankAccountCreateSerializer

        serializer = BankAccountCreateSerializer(
            data={
                "account_name": "Fresh Probe",
                "bank_name": "TB",
                "account_number": "001234568",
                "currency": "SGD",
                "gl_account": bank_fx["accounts"]["1200"].id,
                "paynow_type": "NRIC",
                "paynow_id": "S7654321B",
            }
        )
        assert serializer.is_valid(), serializer.errors
