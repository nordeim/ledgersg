"""
P20 API-contract gates — the CSV import transaction poisoning.

BE-H2: import_csv()'s per-row BankTransaction.objects.create() sits
    inside a try/except Exception with NO savepoint, and the final
    AuditEventLog create runs outside the try — all inside the method's
    @transaction.atomic(). A row that fails at the DATABASE level (not
    in Python parsing) aborts the PG transaction: the per-row except
    swallows the DataError, every subsequent row fails with "current
    transaction is aborted" (also swallowed), and the audit-log INSERT
    raises outside the try -> untyped 500, full rollback, and the
    per-row errors[] contract — the entire point of the loop — never
    reaches the client. The realistic trigger: money() has no magnitude
    bound (money("1E+20") is a 21-digit Decimal) while
    banking.bank_transaction.amount is NUMERIC(19,4) (15 integer
    digits). This is byte-for-byte the class P19/BE-M4 fixed for
    gst/return_service.create_return_periods (the savepoint around
    the guarded create); the import loop never got the treatment.
"""

from io import BytesIO

import pytest

from apps.banking.services import ReconciliationService
from apps.core.models import BankAccount, BankTransaction


@pytest.fixture
def csv_bank(test_organisation, test_user, test_accounts):
    return BankAccount.objects.create(
        org=test_organisation,
        gl_account=test_accounts["1200"],
        account_name="P20 CSV Bank",
        bank_name="Test Bank",
        account_number="001-888-001",
        currency="SGD",
        paynow_type=None,
        is_active=True,
    )


class TestCsvImportPoisonRowP20:

    @pytest.mark.django_db
    def test_one_db_level_poison_row_is_a_typed_row_error(
        self, test_organisation, test_user, csv_bank
    ):
        """BE-H2: a row whose amount overflows NUMERIC(19,4) (a DB-level
        DataError, not a Python parse error) must land in errors[] while
        the surrounding rows import — the per-row loop's contract. Pre-fix:
        the DataError poisons the transaction, the audit-log create raises
        outside the try, and the whole import 500s."""
        csv_text = (
            "transaction_date,description,amount\n"
            "2024-01-15,valid row one,10.00\n"
            "2024-01-16,poison amount row,9999999999999999.99\n"  # 16 integer digits
            "2024-01-17,valid row two,20.00\n"
        )
        result = ReconciliationService.import_csv(
            org_id=test_organisation.id,
            bank_account_id=csv_bank.id,
            csv_file=BytesIO(csv_text.encode("utf-8")),
            user_id=test_user.id,
        )
        # The response is success-shaped (never a 500): the two valid rows
        # imported, the poison row is a typed row error.
        assert result["imported"] == 2, (
            "the valid rows around the poison row must import "
            "(BE-P20-H2 — the DB-level DataError aborted the whole "
            "transaction pre-fix)"
        )
        assert result["errors"], "the poison row must be reported in errors[]"
        assert any("2" in e or "amount" in e.lower() for e in result["errors"])
        rows = BankTransaction.objects.filter(
            bank_account=csv_bank, description__startswith="valid row"
        )
        assert rows.count() == 2
        assert not BankTransaction.objects.filter(
            bank_account=csv_bank, description="poison amount row"
        ).exists()

    @pytest.mark.django_db
    def test_the_poison_row_survives_a_reimport_with_a_bounded_amount(
        self, test_organisation, test_user, csv_bank
    ):
        """BE-H2 companion: the magnitude bound is a typed row error, not
        a refusal of the whole file — re-importing the same statement with
        the fat finger fixed imports the row."""
        csv_text = (
            "transaction_date,description,amount\n"
            "2024-01-15,poison row corrected,10.00\n"
        )
        result = ReconciliationService.import_csv(
            org_id=test_organisation.id,
            bank_account_id=csv_bank.id,
            csv_file=BytesIO(csv_text.encode("utf-8")),
            user_id=test_user.id,
        )
        assert result["imported"] == 1
        assert result["errors"] == []

    @pytest.mark.django_db
    def test_python_parse_errors_stay_typed_row_errors(
        self, test_organisation, test_user, csv_bank
    ):
        """Regression guard: the pre-existing Python-level row-error
        contract (bad date, bad amount string) is unchanged by the
        savepoint fix."""
        csv_text = (
            "transaction_date,description,amount\n"
            "not-a-date,bad date row,10.00\n"
            "2024-01-15,bad amount row,abc\n"
            "2024-01-15,good row,10.00\n"
        )
        result = ReconciliationService.import_csv(
            org_id=test_organisation.id,
            bank_account_id=csv_bank.id,
            csv_file=BytesIO(csv_text.encode("utf-8")),
            user_id=test_user.id,
        )
        assert result["imported"] == 1
        assert len(result["errors"]) == 2
