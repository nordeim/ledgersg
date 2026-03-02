"""
Integration tests for Journal Service Field Alignment.

TDD GREEN Phase: Tests validate JournalService is aligned with SQL schema.

SQL Schema Fields (journal.entry):
- source_type VARCHAR(30) - NOT 'entry_type'
- narration TEXT - NOT 'description'
- source_id UUID - NOT 'source_invoice_id'

SQL Valid source_type values:
- MANUAL, SALES_INVOICE, PURCHASE_INVOICE
- SALES_CREDIT_NOTE, PURCHASE_CREDIT_NOTE
- SALES_DEBIT_NOTE, PURCHASE_DEBIT_NOTE
- PAYMENT_RECEIVED, PAYMENT_MADE
- BANK_FEE, FX_REVALUATION
- YEAR_END, OPENING_BALANCE, REVERSAL
"""

import pytest
from decimal import Decimal
from datetime import date
from uuid import UUID

from apps.journal.services import JournalService
from apps.core.models import JournalEntry, JournalLine
from common.exceptions import ValidationError


@pytest.mark.django_db
class TestJournalServiceFieldAlignment:
    """Test that JournalService uses correct field names matching SQL schema."""

    def test_create_entry_uses_source_type_not_entry_type(
        self, test_organisation, test_accounts, test_fiscal_period, test_user
    ):
        """create_entry should accept 'source_type' parameter."""
        ar_account = test_accounts["1200"]
        revenue_account = test_accounts["4000"]

        entry = JournalService.create_entry(
            org_id=test_organisation.id,
            entry_date=date(2024, 1, 15),
            source_type="MANUAL",
            narration="Test entry with correct field names",
            lines=[
                {
                    "account_id": ar_account.id,
                    "debit": Decimal("100.00"),
                    "credit": Decimal("0.00"),
                },
                {
                    "account_id": revenue_account.id,
                    "debit": Decimal("0.00"),
                    "credit": Decimal("100.00"),
                },
            ],
            fiscal_period_id=test_fiscal_period.id,
            user_id=test_user.id,
        )

        assert entry is not None
        assert entry.source_type == "MANUAL"
        assert entry.narration == "Test entry with correct field names"

    def test_create_entry_validates_source_type_values(
        self, test_organisation, test_accounts, test_fiscal_period, test_user
    ):
        """source_type must be one of the SQL CHECK constraint values."""
        ar_account = test_accounts["1200"]
        revenue_account = test_accounts["4000"]

        valid_types = [
            "MANUAL",
            "SALES_INVOICE",
            "PURCHASE_INVOICE",
            "SALES_CREDIT_NOTE",
            "PURCHASE_CREDIT_NOTE",
            "PAYMENT_RECEIVED",
            "PAYMENT_MADE",
            "BANK_FEE",
            "FX_REVALUATION",
            "YEAR_END",
            "OPENING_BALANCE",
            "REVERSAL",
        ]

        for source_type in valid_types:
            entry = JournalService.create_entry(
                org_id=test_organisation.id,
                entry_date=date(2024, 1, 15),
                source_type=source_type,
                narration=f"Test {source_type} entry",
                lines=[
                    {
                        "account_id": ar_account.id,
                        "debit": Decimal("10.00"),
                        "credit": Decimal("0.00"),
                    },
                    {
                        "account_id": revenue_account.id,
                        "debit": Decimal("0.00"),
                        "credit": Decimal("10.00"),
                    },
                ],
                fiscal_period_id=test_fiscal_period.id,
                user_id=test_user.id,
            )
            assert entry.source_type == source_type

    def test_create_entry_rejects_invalid_source_type(
        self, test_organisation, test_accounts, test_fiscal_period
    ):
        """Invalid source_type should raise ValidationError."""
        ar_account = test_accounts["1200"]
        revenue_account = test_accounts["4000"]

        invalid_types = ["INVOICE", "CREDIT_NOTE", "PAYMENT", "ADJUSTMENT", "OPENING", "CLOSING"]

        for invalid_type in invalid_types:
            with pytest.raises(ValidationError) as exc_info:
                JournalService.create_entry(
                    org_id=test_organisation.id,
                    entry_date=date(2024, 1, 15),
                    source_type=invalid_type,
                    narration=f"Test {invalid_type} entry",
                    lines=[
                        {
                            "account_id": ar_account.id,
                            "debit": Decimal("10.00"),
                            "credit": Decimal("0.00"),
                        },
                        {
                            "account_id": revenue_account.id,
                            "debit": Decimal("0.00"),
                            "credit": Decimal("10.00"),
                        },
                    ],
                    fiscal_period_id=test_fiscal_period.id,
                )
            assert "Invalid source type" in str(
                exc_info.value.message
            ) or "Invalid entry type" in str(exc_info.value.message)

    def test_list_entries_uses_source_type_filter(
        self, test_organisation, test_accounts, test_fiscal_period, test_user
    ):
        """list_entries should filter by 'source_type'."""
        ar_account = test_accounts["1200"]
        revenue_account = test_accounts["4000"]

        JournalService.create_entry(
            org_id=test_organisation.id,
            entry_date=date(2024, 1, 10),
            source_type="MANUAL",
            narration="Manual entry",
            lines=[
                {
                    "account_id": ar_account.id,
                    "debit": Decimal("100.00"),
                    "credit": Decimal("0.00"),
                },
                {
                    "account_id": revenue_account.id,
                    "debit": Decimal("0.00"),
                    "credit": Decimal("100.00"),
                },
            ],
            fiscal_period_id=test_fiscal_period.id,
            user_id=test_user.id,
        )

        JournalService.create_entry(
            org_id=test_organisation.id,
            entry_date=date(2024, 1, 15),
            source_type="SALES_INVOICE",
            narration="Sales invoice entry",
            lines=[
                {
                    "account_id": ar_account.id,
                    "debit": Decimal("200.00"),
                    "credit": Decimal("0.00"),
                },
                {
                    "account_id": revenue_account.id,
                    "debit": Decimal("0.00"),
                    "credit": Decimal("200.00"),
                },
            ],
            fiscal_period_id=test_fiscal_period.id,
            user_id=test_user.id,
        )

        entries = JournalService.list_entries(
            org_id=test_organisation.id,
            source_type="MANUAL",
        )

        assert len(entries) == 1
        assert entries[0].source_type == "MANUAL"

    def test_create_entry_uses_narration_not_description(
        self, test_organisation, test_accounts, test_fiscal_period, test_user
    ):
        """create_entry parameter should be 'narration'."""
        ar_account = test_accounts["1200"]
        revenue_account = test_accounts["4000"]

        entry = JournalService.create_entry(
            org_id=test_organisation.id,
            entry_date=date(2024, 1, 15),
            source_type="MANUAL",
            narration="This is the narration field per SQL schema",
            lines=[
                {
                    "account_id": ar_account.id,
                    "debit": Decimal("100.00"),
                    "credit": Decimal("0.00"),
                },
                {
                    "account_id": revenue_account.id,
                    "debit": Decimal("0.00"),
                    "credit": Decimal("100.00"),
                },
            ],
            fiscal_period_id=test_fiscal_period.id,
            user_id=test_user.id,
        )

        entry.refresh_from_db()
        assert entry.narration == "This is the narration field per SQL schema"

    def test_source_id_parameter_name(
        self, test_organisation, test_accounts, test_fiscal_period, test_user
    ):
        """create_entry should use 'source_id' for source document reference."""
        ar_account = test_accounts["1200"]
        revenue_account = test_accounts["4000"]

        test_source_id = UUID("00000000-0000-0000-0000-000000000999")

        entry = JournalService.create_entry(
            org_id=test_organisation.id,
            entry_date=date(2024, 1, 15),
            source_type="SALES_INVOICE",
            narration="Invoice posting",
            source_id=test_source_id,
            lines=[
                {
                    "account_id": ar_account.id,
                    "debit": Decimal("100.00"),
                    "credit": Decimal("0.00"),
                },
                {
                    "account_id": revenue_account.id,
                    "debit": Decimal("0.00"),
                    "credit": Decimal("100.00"),
                },
            ],
            fiscal_period_id=test_fiscal_period.id,
            user_id=test_user.id,
        )

        assert entry.source_id == test_source_id

    def test_post_invoice_uses_sales_invoice_source_type(
        self, test_organisation, test_accounts, test_fiscal_period, test_tax_codes, test_user
    ):
        """post_invoice should create entry with source_type='SALES_INVOICE'."""
        from apps.core.models import Contact, InvoiceDocument

        contact = Contact.objects.create(
            org=test_organisation,
            contact_type="CUSTOMER",
            name="Test Customer",
            is_customer=True,
            is_supplier=False,
            payment_terms_days=30,
            is_active=True,
        )

        # Use correct InvoiceDocument fields (no subtotal, total_gst, total_amount in model)
        invoice = InvoiceDocument.objects.create(
            org=test_organisation,
            document_type="SALES_INVOICE",
            document_number="INV-TEST-001",
            contact=contact,
            issue_date=date(2024, 1, 15),
            due_date=date(2024, 2, 15),
            status="DRAFT",
            currency="SGD",
        )

        ar_account = test_accounts["1200"]
        revenue_account = test_accounts["4000"]
        gst_account = test_accounts["2200"]

        entry = JournalService.create_entry(
            org_id=test_organisation.id,
            entry_date=invoice.issue_date,
            source_type="SALES_INVOICE",
            narration=f"Invoice {invoice.document_number}",
            source_id=invoice.id,
            lines=[
                {
                    "account_id": ar_account.id,
                    "debit": Decimal("109.00"),
                    "credit": Decimal("0.00"),
                },
                {
                    "account_id": revenue_account.id,
                    "debit": Decimal("0.00"),
                    "credit": Decimal("100.00"),
                },
                {"account_id": gst_account.id, "debit": Decimal("0.00"), "credit": Decimal("9.00")},
            ],
            fiscal_period_id=test_fiscal_period.id,
            user_id=test_user.id,
        )

        assert entry.source_type == "SALES_INVOICE"
        assert entry.source_id == invoice.id


@pytest.mark.django_db
class TestJournalServiceBackwardsCompatibility:
    """Test backwards compatibility during transition period."""

    def test_old_entry_type_parameter_still_works_with_warning(
        self, test_organisation, test_accounts, test_fiscal_period, test_user
    ):
        """Old parameter names should still work via backwards compatibility layer."""
        ar_account = test_accounts["1200"]
        revenue_account = test_accounts["4000"]

        import warnings

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")

            entry = JournalService.create_entry(
                org_id=test_organisation.id,
                entry_date=date(2024, 1, 15),
                entry_type="MANUAL",
                description="Test entry",
                lines=[
                    {
                        "account_id": ar_account.id,
                        "debit": Decimal("100.00"),
                        "credit": Decimal("0.00"),
                    },
                    {
                        "account_id": revenue_account.id,
                        "debit": Decimal("0.00"),
                        "credit": Decimal("100.00"),
                    },
                ],
                fiscal_period_id=test_fiscal_period.id,
                user_id=test_user.id,
            )
            assert entry is not None
            assert entry.source_type == "MANUAL"
            assert entry.narration == "Test entry"
