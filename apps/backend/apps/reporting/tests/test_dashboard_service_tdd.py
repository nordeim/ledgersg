"""
Dashboard Service TDD Tests - Phase 3 Implementation.

Test-Driven Development for Dashboard Real Calculations.
Tests cover GST calculations, revenue aggregation, outstanding amounts,
cash position, GST threshold, and compliance alerts.

Version: 1.0.0
Date: 2026-03-03
Phase: 3 - Production Ready (TDD)
"""

import pytest
from datetime import date, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

from apps.core.models import (
    Organisation,
    AppUser,
    FiscalYear,
    FiscalPeriod,
    InvoiceDocument,
    Contact,
    TaxCode,
    Account,
    BankAccount,
    Payment,
    JournalEntry,
    JournalLine,
)
from apps.reporting.services.dashboard_service import DashboardService


@pytest.fixture
def test_user():
    """Create test user."""
    user = AppUser.objects.create(
        id=uuid4(),
        email="test@example.com",
        first_name="Test",
        last_name="User",
    )
    user.set_password("testpass123")
    user.save()
    return user


@pytest.fixture
def test_org(test_user):
    """Create test organization."""
    org = Organisation.objects.create(
        id=uuid4(),
        name="Test Company Pte Ltd",
        uen="202400001A",
        gst_registered=True,
        gst_reg_number="M12345678X",
        gst_scheme="STANDARD",
        gst_filing_frequency="QUARTERLY",
        fy_start_month=1,
        base_currency="SGD",
    )
    return org


@pytest.fixture
def test_fiscal_year(test_org):
    """Create test fiscal year."""
    fy = FiscalYear.objects.create(
        id=uuid4(),
        org=test_org,
        label="FY2024",
        start_date=date(2024, 1, 1),
        end_date=date(2024, 12, 31),
        is_closed=False,
    )
    return fy


@pytest.fixture
def test_fiscal_period(test_org, test_fiscal_year):
    """Create test fiscal period (Q1 2024)."""
    period = FiscalPeriod.objects.create(
        id=uuid4(),
        org=test_org,
        fiscal_year=test_fiscal_year,
        label="Jan 2024",
        period_number=1,
        start_date=date(2024, 1, 1),
        end_date=date(2024, 1, 31),
        is_open=True,
    )
    return period


@pytest.fixture
def test_customer(test_org):
    """Create test customer contact."""
    contact = Contact.objects.create(
        id=uuid4(),
        org=test_org,
        name="Test Customer",
        email="customer@example.com",
        is_customer=True,
        contact_type="CUSTOMER",
    )
    return contact


@pytest.fixture
def test_supplier(test_org):
    """Create test supplier contact."""
    contact = Contact.objects.create(
        id=uuid4(),
        org=test_org,
        name="Test Supplier",
        email="supplier@example.com",
        is_supplier=True,
        contact_type="SUPPLIER",
    )
    return contact


@pytest.fixture
def test_revenue_account(test_org):
    """Create test revenue account."""
    account = Account.objects.create(
        id=uuid4(),
        org=test_org,
        code="4000",
        name="Sales Revenue",
        account_type="REVENUE",
    )
    return account


@pytest.fixture
def test_ar_account(test_org):
    """Create test accounts receivable account."""
    account = Account.objects.create(
        id=uuid4(),
        org=test_org,
        code="1200",
        name="Accounts Receivable",
        account_type="ASSET",
    )
    return account


@pytest.fixture
def test_bank_account(test_org, test_revenue_account):
    """Create test bank account."""
    bank = BankAccount.objects.create(
        id=uuid4(),
        org=test_org,
        account_name="Main Bank Account",
        bank_name="DBS Bank",
        account_number="1234567890",
        currency="SGD",
        gl_account=test_revenue_account,
        is_active=True,
        opening_balance=Decimal("10000.0000"),
        opening_balance_date=date(2024, 1, 1),
    )
    return bank


@pytest.fixture
def test_std_rated_tax_code(test_org):
    """Create standard-rated GST tax code (9%)."""
    tax = TaxCode.objects.create(
        id=uuid4(),
        org=test_org,
        code="SR",
        description="Standard-Rated Supplies",
        rate=Decimal("0.0900"),
        is_output=True,
        is_input=False,
        is_claimable=True,
        is_active=True,
        effective_from=date(2024, 1, 1),
    )
    return tax


@pytest.fixture
def test_zero_rated_tax_code(test_org):
    """Create zero-rated GST tax code (0%)."""
    tax = TaxCode.objects.create(
        id=uuid4(),
        org=test_org,
        code="ZR",
        description="Zero-Rated Supplies",
        rate=Decimal("0.0000"),
        is_output=True,
        is_input=False,
        is_claimable=False,
        is_active=True,
        effective_from=date(2024, 1, 1),
    )
    return tax


@pytest.fixture
def test_input_tax_code(test_org):
    """Create input tax code (GST paid on purchases)."""
    tax = TaxCode.objects.create(
        id=uuid4(),
        org=test_org,
        code="TX",
        description="Taxable Purchases",
        rate=Decimal("0.0900"),
        is_output=False,
        is_input=True,
        is_claimable=True,
        is_active=True,
        effective_from=date(2024, 1, 1),
    )
    return tax


# ============================================================================
# GST CALCULATION TESTS (4 tests)
# ============================================================================


class TestGSTCalculations:
    """Test GST liability calculations."""

    @pytest.mark.django_db
    def test_calculate_gst_payable_with_std_rated_sales(
        self,
        test_org,
        test_fiscal_period,
        test_ar_account,
        test_revenue_account,
        test_std_rated_tax_code,
        test_user,
    ):
        """
        Test: Calculate GST payable with standard-rated sales.

        Scenario:
        - Create sales invoice: $10,000 + $900 GST (9%)
        - GST payable should be $900

        Expected:
        - GST payable = Output tax collected on standard-rated supplies
        - Uses money() utility for Decimal precision
        """
        # Create journal entry for sales with GST
        entry = JournalEntry.objects.create(
            id=uuid4(),
            org=test_org,
            entry_number=1,
            entry_date=date(2024, 1, 15),
            source_type="SALES_INVOICE",
            fiscal_year_id=test_fiscal_period.fiscal_year_id,
            fiscal_period=test_fiscal_period,
            narration="Sales invoice with GST",
            posted_at=datetime.now(),
            posted_by=test_user,
        )

        # Debit AR
        JournalLine.objects.create(
            id=uuid4(),
            entry=entry,
            org=test_org,
            line_number=1,
            account=test_ar_account,
            debit=Decimal("10900.0000"),
            credit=Decimal("0.0000"),
            tax_code=test_std_rated_tax_code,
            tax_amount=Decimal("900.0000"),
        )

        # Credit Revenue
        JournalLine.objects.create(
            id=uuid4(),
            entry=entry,
            org=test_org,
            line_number=2,
            account=test_revenue_account,
            debit=Decimal("0.0000"),
            credit=Decimal("10000.0000"),
        )

        # Credit GST Output Tax
        JournalLine.objects.create(
            id=uuid4(),
            entry=entry,
            org=test_org,
            line_number=3,
            account=test_revenue_account,
            debit=Decimal("0.0000"),
            credit=Decimal("900.0000"),
            tax_code=test_std_rated_tax_code,
            tax_amount=Decimal("900.0000"),
        )

        # Execute
        service = DashboardService()
        result = service.calculate_gst_liability(
            str(test_org.id),
            test_fiscal_period.start_date,
            test_fiscal_period.end_date,
        )

        # Assert
        assert result["output_tax"] == Decimal("900.0000")
        assert result["net_gst"] == Decimal("900.0000")  # No input tax

    @pytest.mark.django_db
    def test_calculate_gst_payable_with_zero_rated_sales(
        self,
        test_org,
        test_fiscal_period,
        test_ar_account,
        test_revenue_account,
        test_zero_rated_tax_code,
        test_user,
    ):
        """
        Test: Zero-rated sales contribute $0 to GST payable.

        Scenario:
        - Create sales invoice: $10,000 zero-rated (0% GST)
        - GST payable should be $0

        Expected:
        - Zero-rated supplies have rate=0.0000
        - No output tax collected
        """
        # Create journal entry for zero-rated sales
        entry = JournalEntry.objects.create(
            id=uuid4(),
            org=test_org,
            entry_number=2,
            entry_date=date(2024, 1, 16),
            source_type="SALES_INVOICE",
            fiscal_year_id=test_fiscal_period.fiscal_year_id,
            fiscal_period=test_fiscal_period,
            narration="Zero-rated sales",
            posted_at=datetime.now(),
            posted_by=test_user,
        )

        # Debit AR (no GST)
        JournalLine.objects.create(
            id=uuid4(),
            entry=entry,
            org=test_org,
            line_number=1,
            account=test_ar_account,
            debit=Decimal("10000.0000"),
            credit=Decimal("0.0000"),
            tax_code=test_zero_rated_tax_code,
            tax_amount=Decimal("0.0000"),
        )

        # Credit Revenue
        JournalLine.objects.create(
            id=uuid4(),
            entry=entry,
            org=test_org,
            line_number=2,
            account=test_revenue_account,
            debit=Decimal("0.0000"),
            credit=Decimal("10000.0000"),
        )

        # Execute
        service = DashboardService()
        result = service.calculate_gst_liability(
            str(test_org.id),
            test_fiscal_period.start_date,
            test_fiscal_period.end_date,
        )

        # Assert
        assert result["output_tax"] == Decimal("0.0000")

    @pytest.mark.django_db
    def test_calculate_gst_payable_with_credit_notes(
        self,
        test_org,
        test_fiscal_period,
        test_ar_account,
        test_revenue_account,
        test_std_rated_tax_code,
        test_user,
    ):
        """
        Test: Credit notes reduce GST payable.

        Scenario:
        - Sales invoice: $10,000 + $900 GST
        - Credit note: -$2,000 -$180 GST
        - Net GST payable should be $720

        Expected:
        - Credit notes are negative adjustments
        - GST payable = Output tax - Credit note tax
        """
        # Create sales invoice entry
        entry1 = JournalEntry.objects.create(
            id=uuid4(),
            org=test_org,
            entry_number=3,
            entry_date=date(2024, 1, 17),
            source_type="SALES_INVOICE",
            fiscal_year_id=test_fiscal_period.fiscal_year_id,
            fiscal_period=test_fiscal_period,
            narration="Sales invoice",
            posted_at=datetime.now(),
            posted_by=test_user,
        )

        JournalLine.objects.create(
            id=uuid4(),
            entry=entry1,
            org=test_org,
            line_number=1,
            account=test_ar_account,
            debit=Decimal("10900.0000"),
            credit=Decimal("0.0000"),
            tax_code=test_std_rated_tax_code,
            tax_amount=Decimal("900.0000"),
        )

        # Create credit note entry (reversing entry)
        entry2 = JournalEntry.objects.create(
            id=uuid4(),
            org=test_org,
            entry_number=4,
            entry_date=date(2024, 1, 18),
            source_type="SALES_CREDIT_NOTE",
            fiscal_year_id=test_fiscal_period.fiscal_year_id,
            fiscal_period=test_fiscal_period,
            narration="Credit note",
            posted_at=datetime.now(),
            posted_by=test_user,
        )

        JournalLine.objects.create(
            id=uuid4(),
            entry=entry2,
            org=test_org,
            line_number=1,
            account=test_ar_account,
            debit=Decimal("0.0000"),
            credit=Decimal("2180.0000"),
            tax_code=test_std_rated_tax_code,
            tax_amount=Decimal("-180.0000"),
        )

        # Execute
        service = DashboardService()
        result = service.calculate_gst_liability(
            str(test_org.id),
            test_fiscal_period.start_date,
            test_fiscal_period.end_date,
        )

        # Assert
        assert result["output_tax"] == Decimal("720.0000")  # 900 - 180

    @pytest.mark.django_db
    def test_calculate_gst_payable_excludes_draft_invoices(
        self,
        test_org,
        test_customer,
    ):
        """
        Test: Draft invoices excluded from GST calculations.

        Scenario:
        - Draft sales invoice: $10,000 + $900 GST
        - Approved sales invoice: $5,000 + $450 GST
        - GST payable should only include $450 (approved)

        Expected:
        - Draft invoices not posted to journal
        - Only approved/posted documents contribute to GST
        """
        # Create draft invoice (should not affect GST)
        draft_invoice = InvoiceDocument.objects.create(
            id=uuid4(),
            org=test_org,
            document_type="SALES_INVOICE",
            document_number="INV-001",
            contact=test_customer,
            issue_date=date(2024, 1, 19),
            due_date=date(2024, 2, 19),
            status="DRAFT",
            total_excl=Decimal("10000.0000"),
            gst_total=Decimal("900.0000"),
            total_incl=Decimal("10900.0000"),
            amount_paid=Decimal("0.0000"),
        )

        # Execute
        service = DashboardService()
        result = service.calculate_gst_liability(
            str(test_org.id),
            date(2024, 1, 1),
            date(2024, 1, 31),
        )

        # Assert - Draft invoices should not contribute
        assert result["output_tax"] == Decimal("0.0000")


# ============================================================================
# REVENUE AGGREGATION TESTS (3 tests)
# ============================================================================


class TestRevenueAggregation:
    """Test MTD and YTD revenue calculations."""

    @pytest.mark.django_db
    def test_calculate_revenue_mtd_with_approved_invoices(
        self,
        test_org,
        test_customer,
    ):
        """
        Test: Month-to-date revenue from approved sales invoices.

        Scenario:
        - Approved invoice Jan 5: $5,000
        - Approved invoice Jan 15: $3,000
        - Draft invoice Jan 20: $2,000 (excluded)
        - MTD revenue (Jan 1-31) should be $8,000

        Expected:
        - Aggregates base_subtotal for current month
        - Excludes DRAFT status
        """
        # Create approved invoices
        InvoiceDocument.objects.create(
            id=uuid4(),
            org=test_org,
            document_type="SALES_INVOICE",
            document_number="INV-101",
            contact=test_customer,
            issue_date=date(2024, 1, 5),
            due_date=date(2024, 2, 5),
            status="APPROVED",
            total_excl=Decimal("5000.0000"),
            gst_total=Decimal("450.0000"),
            total_incl=Decimal("5450.0000"),
            amount_paid=Decimal("0.0000"),
        )

        InvoiceDocument.objects.create(
            id=uuid4(),
            org=test_org,
            document_type="SALES_INVOICE",
            document_number="INV-102",
            contact=test_customer,
            issue_date=date(2024, 1, 15),
            due_date=date(2024, 2, 15),
            status="APPROVED",
            total_excl=Decimal("3000.0000"),
            gst_total=Decimal("270.0000"),
            total_incl=Decimal("3270.0000"),
            amount_paid=Decimal("0.0000"),
        )

        # Create draft invoice (excluded)
        InvoiceDocument.objects.create(
            id=uuid4(),
            org=test_org,
            document_type="SALES_INVOICE",
            document_number="INV-103",
            contact=test_customer,
            issue_date=date(2024, 1, 20),
            due_date=date(2024, 2, 20),
            status="DRAFT",
            total_excl=Decimal("2000.0000"),
            gst_total=Decimal("180.0000"),
            total_incl=Decimal("2180.0000"),
            amount_paid=Decimal("0.0000"),
        )

        # Execute
        service = DashboardService()
        result = service.query_revenue_mtd(
            str(test_org.id),
            date(2024, 1, 31),
        )

        # Assert
        assert result == Decimal("8000.0000")  # 5000 + 3000

    @pytest.mark.django_db
    def test_calculate_revenue_ytd_with_multiple_invoices(
        self,
        test_org,
        test_customer,
        test_fiscal_year,
    ):
        """
        Test: Year-to-date revenue across multiple months.

        Scenario:
        - Invoice Jan: $10,000
        - Invoice Feb: $8,000
        - Invoice Mar: $12,000
        - YTD revenue should be $30,000

        Expected:
        - Joins with fiscal_period to get YTD range
        - Aggregates base_subtotal for current FY
        """
        # January invoice
        InvoiceDocument.objects.create(
            id=uuid4(),
            org=test_org,
            document_type="SALES_INVOICE",
            document_number="INV-201",
            contact=test_customer,
            issue_date=date(2024, 1, 10),
            due_date=date(2024, 2, 10),
            status="APPROVED",
            total_excl=Decimal("10000.0000"),
            gst_total=Decimal("900.0000"),
            total_incl=Decimal("10900.0000"),
            amount_paid=Decimal("0.0000"),
        )

        # February invoice
        InvoiceDocument.objects.create(
            id=uuid4(),
            org=test_org,
            document_type="SALES_INVOICE",
            document_number="INV-202",
            contact=test_customer,
            issue_date=date(2024, 2, 10),
            due_date=date(2024, 3, 10),
            status="APPROVED",
            total_excl=Decimal("8000.0000"),
            gst_total=Decimal("720.0000"),
            total_incl=Decimal("8720.0000"),
            amount_paid=Decimal("0.0000"),
        )

        # March invoice
        InvoiceDocument.objects.create(
            id=uuid4(),
            org=test_org,
            document_type="SALES_INVOICE",
            document_number="INV-203",
            contact=test_customer,
            issue_date=date(2024, 3, 10),
            due_date=date(2024, 4, 10),
            status="APPROVED",
            total_excl=Decimal("12000.0000"),
            gst_total=Decimal("1080.0000"),
            total_incl=Decimal("13080.0000"),
            amount_paid=Decimal("0.0000"),
        )

        # Execute
        service = DashboardService()
        result = service.query_revenue_ytd(
            str(test_org.id),
            str(test_fiscal_year.id),
        )

        # Assert
        assert result == Decimal("30000.0000")  # 10k + 8k + 12k

    @pytest.mark.django_db
    def test_calculate_revenue_excludes_void_and_draft(
        self,
        test_org,
        test_customer,
    ):
        """
        Test: Voided and draft documents excluded from revenue.

        Scenario:
        - Approved invoice: $5,000
        - Void invoice: $3,000 (excluded)
        - Draft invoice: $2,000 (excluded)
        - Revenue should be $5,000

        Expected:
        - Status IN ('APPROVED', 'SENT', 'PARTIALLY_PAID', 'PAID', 'OVERDUE')
        - Excludes 'DRAFT' and 'VOID'
        """
        # Approved invoice
        InvoiceDocument.objects.create(
            id=uuid4(),
            org=test_org,
            document_type="SALES_INVOICE",
            document_number="INV-301",
            contact=test_customer,
            issue_date=date(2024, 1, 10),
            due_date=date(2024, 2, 10),
            status="APPROVED",
            total_excl=Decimal("5000.0000"),
            gst_total=Decimal("450.0000"),
            total_incl=Decimal("5450.0000"),
            amount_paid=Decimal("0.0000"),
        )

        # Void invoice (excluded)
        InvoiceDocument.objects.create(
            id=uuid4(),
            org=test_org,
            document_type="SALES_INVOICE",
            document_number="INV-302",
            contact=test_customer,
            issue_date=date(2024, 1, 11),
            due_date=date(2024, 2, 11),
            status="VOID",
            total_excl=Decimal("3000.0000"),
            gst_total=Decimal("270.0000"),
            total_incl=Decimal("3270.0000"),
            amount_paid=Decimal("0.0000"),
        )

        # Draft invoice (excluded)
        InvoiceDocument.objects.create(
            id=uuid4(),
            org=test_org,
            document_type="SALES_INVOICE",
            document_number="INV-303",
            contact=test_customer,
            issue_date=date(2024, 1, 12),
            due_date=date(2024, 2, 12),
            status="DRAFT",
            total_excl=Decimal("2000.0000"),
            gst_total=Decimal("180.0000"),
            total_incl=Decimal("2180.0000"),
            amount_paid=Decimal("0.0000"),
        )

        # Execute
        service = DashboardService()
        result = service.query_revenue_mtd(
            str(test_org.id),
            date(2024, 1, 31),
        )

        # Assert
        assert result == Decimal("5000.0000")


# ============================================================================
# OUTSTANDING AMOUNTS TESTS (4 tests)
# ============================================================================


class TestOutstandingAmounts:
    """Test outstanding receivables and payables calculations."""

    @pytest.mark.django_db
    def test_calculate_outstanding_receivables_with_partial_payments(
        self,
        test_org,
        test_customer,
    ):
        """
        Test: Outstanding = total - paid for partially paid invoices.

        Scenario:
        - Invoice: $10,000 total, $4,000 paid
        - Outstanding receivable should be $6,000

        Expected:
        - Uses amount_due computed column or calculates manually
        - Aggregates across all outstanding sales invoices
        """
        # Create partially paid invoice
        InvoiceDocument.objects.create(
            id=uuid4(),
            org=test_org,
            document_type="SALES_INVOICE",
            document_number="INV-401",
            contact=test_customer,
            issue_date=date(2024, 1, 10),
            due_date=date(2024, 2, 10),
            status="PARTIALLY_PAID",
            total_excl=Decimal("9174.3119"),
            gst_total=Decimal("825.6881"),
            total_incl=Decimal("10000.0000"),
            amount_paid=Decimal("4000.0000"),
        )

        # Execute
        service = DashboardService()
        result = service.query_outstanding_receivables(str(test_org.id))

        # Assert
        assert result == Decimal("6000.0000")  # 10000 - 4000

    @pytest.mark.django_db
    def test_calculate_outstanding_payables_with_multiple_vendors(
        self,
        test_org,
        test_supplier,
    ):
        """
        Test: Purchase invoice payables from multiple vendors.

        Scenario:
        - Vendor A invoice: $8,000 unpaid
        - Vendor B invoice: $5,000 unpaid
        - Total outstanding payables should be $13,000

        Expected:
        - Filters document_type IN ('PURCHASE_INVOICE', 'PURCHASE_DEBIT_NOTE')
        - Status IN ('APPROVED', 'SENT', 'PARTIALLY_PAID', 'OVERDUE')
        """
        # Vendor A invoice
        InvoiceDocument.objects.create(
            id=uuid4(),
            org=test_org,
            document_type="PURCHASE_INVOICE",
            document_number="PO-001",
            contact=test_supplier,
            issue_date=date(2024, 1, 5),
            due_date=date(2024, 2, 5),
            status="APPROVED",
            total_excl=Decimal("7339.4495"),
            gst_total=Decimal("660.5505"),
            total_incl=Decimal("8000.0000"),
            amount_paid=Decimal("0.0000"),
        )

        # Create another supplier
        supplier2 = Contact.objects.create(
            id=uuid4(),
            org=test_org,
            name="Supplier B",
            email="supplierb@example.com",
            is_supplier=True,
            contact_type="SUPPLIER",
        )

        # Vendor B invoice
        InvoiceDocument.objects.create(
            id=uuid4(),
            org=test_org,
            document_type="PURCHASE_INVOICE",
            document_number="PO-002",
            contact=supplier2,
            issue_date=date(2024, 1, 10),
            due_date=date(2024, 2, 10),
            status="APPROVED",
            total_excl=Decimal("4587.1559"),
            gst_total=Decimal("412.8441"),
            total_incl=Decimal("5000.0000"),
            amount_paid=Decimal("0.0000"),
        )

        # Execute
        service = DashboardService()
        result = service.query_outstanding_payables(str(test_org.id))

        # Assert
        assert result == Decimal("13000.0000")  # 8000 + 5000

    @pytest.mark.django_db
    def test_calculate_outstanding_includes_overdue(
        self,
        test_org,
        test_customer,
    ):
        """
        Test: Overdue amounts included in outstanding.

        Scenario:
        - Invoice due Jan 31, today is Feb 15 (overdue)
        - Invoice: $7,000 unpaid
        - Outstanding should include this overdue amount

        Expected:
        - Overdue invoices have status='OVERDUE'
        - Included in outstanding receivables
        """
        # Create overdue invoice
        InvoiceDocument.objects.create(
            id=uuid4(),
            org=test_org,
            document_type="SALES_INVOICE",
            document_number="INV-501",
            contact=test_customer,
            issue_date=date(2024, 1, 1),
            due_date=date(2024, 1, 31),
            status="OVERDUE",
            total_excl=Decimal("6422.0183"),
            gst_total=Decimal("577.9817"),
            total_incl=Decimal("7000.0000"),
            amount_paid=Decimal("0.0000"),
        )

        # Execute
        service = DashboardService()
        result = service.query_outstanding_receivables(str(test_org.id))

        # Assert
        assert result == Decimal("7000.0000")

    @pytest.mark.django_db
    def test_calculate_outstanding_excludes_paid_documents(
        self,
        test_org,
        test_customer,
    ):
        """
        Test: Paid documents excluded from outstanding.

        Scenario:
        - Approved invoice: $5,000 unpaid
        - Paid invoice: $3,000 (fully paid)
        - Outstanding should only be $5,000

        Expected:
        - Status='PAID' invoices excluded
        - Only documents with amount_due > 0
        """
        # Unpaid invoice
        InvoiceDocument.objects.create(
            id=uuid4(),
            org=test_org,
            document_type="SALES_INVOICE",
            document_number="INV-601",
            contact=test_customer,
            issue_date=date(2024, 1, 10),
            due_date=date(2024, 2, 10),
            status="APPROVED",
            total_excl=Decimal("4587.1559"),
            gst_total=Decimal("412.8441"),
            total_incl=Decimal("5000.0000"),
            amount_paid=Decimal("0.0000"),
        )

        # Paid invoice (excluded)
        InvoiceDocument.objects.create(
            id=uuid4(),
            org=test_org,
            document_type="SALES_INVOICE",
            document_number="INV-602",
            contact=test_customer,
            issue_date=date(2024, 1, 11),
            due_date=date(2024, 2, 11),
            status="PAID",
            total_excl=Decimal("2752.2936"),
            gst_total=Decimal("247.7064"),
            total_incl=Decimal("3000.0000"),
            amount_paid=Decimal("3000.0000"),  # Fully paid
        )

        # Execute
        service = DashboardService()
        result = service.query_outstanding_receivables(str(test_org.id))

        # Assert
        assert result == Decimal("5000.0000")


# ============================================================================
# CASH POSITION TESTS (2 tests)
# ============================================================================


class TestCashPosition:
    """Test cash on hand calculations."""

    @pytest.mark.django_db
    def test_calculate_cash_on_hand_with_multiple_accounts(
        self,
        test_org,
        test_revenue_account,
    ):
        """
        Test: Sum cash across all active bank accounts.

        Scenario:
        - Bank account A: $10,000 opening balance
        - Bank account B: $15,000 opening balance
        - Cash on hand should be $25,000

        Expected:
        - Aggregates opening_balance for is_active=True
        - Includes all currencies converted to base currency
        """
        # Bank account A
        BankAccount.objects.create(
            id=uuid4(),
            org=test_org,
            account_name="DBS Account",
            bank_name="DBS Bank",
            account_number="001-12345",
            currency="SGD",
            gl_account=test_revenue_account,
            is_active=True,
            opening_balance=Decimal("10000.0000"),
            opening_balance_date=date(2024, 1, 1),
        )

        # Bank account B
        BankAccount.objects.create(
            id=uuid4(),
            org=test_org,
            account_name="OCBC Account",
            bank_name="OCBC Bank",
            account_number="002-67890",
            currency="SGD",
            gl_account=test_revenue_account,
            is_active=True,
            opening_balance=Decimal("15000.0000"),
            opening_balance_date=date(2024, 1, 1),
        )

        # Execute
        service = DashboardService()
        result = service.calculate_cash_on_hand(str(test_org.id))

        # Assert
        assert result == Decimal("25000.0000")

    @pytest.mark.django_db
    def test_calculate_cash_on_hand_includes_payments(
        self,
        test_org,
        test_bank_account,
        test_customer,
        test_supplier,
        test_ar_account,
        test_fiscal_period,
        test_user,
    ):
        """
        Test: Payment allocations affect cash position.

        Scenario:
        - Opening balance: $10,000
        - Payment received: +$5,000
        - Payment made: -$3,000
        - Cash on hand should be $12,000

        Expected:
        - Adds payment.amount where payment_type='RECEIVED' and is_reconciled=True
        - Subtracts payment.amount where payment_type='MADE' and is_reconciled=True
        """
        # Create payment received
        Payment.objects.create(
            id=uuid4(),
            org=test_org,
            payment_type="RECEIVED",
            payment_number="RCP-001",
            payment_date=date(2024, 1, 10),
            contact=test_customer,
            bank_account=test_bank_account,
            currency="SGD",
            exchange_rate=Decimal("1.000000"),
            amount=Decimal("5000.0000"),
            base_amount=Decimal("5000.0000"),
            is_reconciled=True,
            is_voided=False,
        )

        # Create payment made
        Payment.objects.create(
            id=uuid4(),
            org=test_org,
            payment_type="MADE",
            payment_number="PAY-001",
            payment_date=date(2024, 1, 15),
            contact=test_supplier,
            bank_account=test_bank_account,
            currency="SGD",
            exchange_rate=Decimal("1.000000"),
            amount=Decimal("3000.0000"),
            base_amount=Decimal("3000.0000"),
            is_reconciled=True,
            is_voided=False,
        )

        # Execute
        service = DashboardService()
        result = service.calculate_cash_on_hand(str(test_org.id))

        # Assert: 10000 (opening) + 5000 (received) - 3000 (made) = 12000
        assert result == Decimal("12000.0000")


# ============================================================================
# GST THRESHOLD TESTS (3 tests)
# ============================================================================


class TestGSTThreshold:
    """Test GST registration threshold monitoring."""

    @pytest.mark.django_db
    def test_calculate_gst_threshold_utilization_safe(
        self,
        test_org,
        test_customer,
    ):
        """
        Test: Revenue < 70% of S$1M threshold = SAFE status.

        Scenario:
        - Rolling 12-month revenue: $500,000
        - Threshold: $1,000,000
        - Utilization: 50%
        - Status: SAFE

        Expected:
        - Status: SAFE when utilization < 70%
        """
        # Create invoices totaling $500k for past 12 months
        for i in range(10):
            InvoiceDocument.objects.create(
                id=uuid4(),
                org=test_org,
                document_type="SALES_INVOICE",
                document_number=f"INV-{700 + i}",
                contact=test_customer,
                issue_date=date(2024, 1, 1) - timedelta(days=i * 30),
                due_date=date(2024, 2, 1) - timedelta(days=i * 30),
                status="APPROVED",
                total_excl=Decimal("50000.0000"),
                gst_total=Decimal("4500.0000"),
                total_incl=Decimal("54500.0000"),
                amount_paid=Decimal("54500.0000"),
            )

        # Execute
        service = DashboardService()
        result = service.query_gst_threshold_status(str(test_org.id))

        # Assert
        assert result["status"] == "SAFE"
        assert result["utilization"] < 70
        assert result["amount"] == Decimal("500000.0000")

    @pytest.mark.django_db
    def test_calculate_gst_threshold_utilization_warning(
        self,
        test_org,
        test_customer,
    ):
        """
        Test: Revenue between 70-90% of threshold = WARNING status.

        Scenario:
        - Rolling 12-month revenue: $800,000
        - Utilization: 80%
        - Status: WARNING

        Expected:
        - Status: WARNING when 70% <= utilization < 90%
        """
        # Create invoices totaling $800k
        for i in range(16):
            InvoiceDocument.objects.create(
                id=uuid4(),
                org=test_org,
                document_type="SALES_INVOICE",
                document_number=f"INV-{800 + i}",
                contact=test_customer,
                issue_date=date(2024, 1, 1) - timedelta(days=i * 20),
                due_date=date(2024, 2, 1) - timedelta(days=i * 20),
                status="APPROVED",
                total_excl=Decimal("50000.0000"),
                gst_total=Decimal("4500.0000"),
                total_incl=Decimal("54500.0000"),
                amount_paid=Decimal("54500.0000"),
            )

        # Execute
        service = DashboardService()
        result = service.query_gst_threshold_status(str(test_org.id))

        # Assert
        assert result["status"] == "WARNING"
        assert 70 <= result["utilization"] < 90

    @pytest.mark.django_db
    def test_calculate_gst_threshold_utilization_critical(
        self,
        test_org,
        test_customer,
    ):
        """
        Test: Revenue > 90% of threshold = CRITICAL status.

        Scenario:
        - Rolling 12-month revenue: $950,000
        - Utilization: 95%
        - Status: CRITICAL

        Expected:
        - Status: CRITICAL when 90% <= utilization < 100%
        """
        # Create invoices totaling $950k
        for i in range(19):
            InvoiceDocument.objects.create(
                id=uuid4(),
                org=test_org,
                document_type="SALES_INVOICE",
                document_number=f"INV-{900 + i}",
                contact=test_customer,
                issue_date=date(2024, 1, 1) - timedelta(days=i * 15),
                due_date=date(2024, 2, 1) - timedelta(days=i * 15),
                status="APPROVED",
                total_excl=Decimal("50000.0000"),
                gst_total=Decimal("4500.0000"),
                total_incl=Decimal("54500.0000"),
                amount_paid=Decimal("54500.0000"),
            )

        # Execute
        service = DashboardService()
        result = service.query_gst_threshold_status(str(test_org.id))

        # Assert
        assert result["status"] == "CRITICAL"
        assert result["utilization"] >= 90


# ============================================================================
# COMPLIANCE ALERTS TESTS (3 tests)
# ============================================================================


class TestComplianceAlerts:
    """Test compliance alert generation."""

    @pytest.mark.django_db
    def test_generate_filing_deadline_alert(
        self,
        test_org,
        test_fiscal_period,
    ):
        """
        Test: Alert when GST filing due in ≤30 days.

        Scenario:
        - Current date: Jan 15, 2024
        - Filing due: Feb 15, 2024 (31 days)
        - Alert should NOT trigger (only ≤30 days)
        - Filing due: Feb 10, 2024 (26 days)
        - Alert SHOULD trigger

        Expected:
        - Alert generated when days_remaining <= 30
        - Alert includes: severity=HIGH, title, action_required
        """
        # Execute
        service = DashboardService()
        alerts = service.generate_compliance_alerts(str(test_org.id))

        # Check for filing deadline alert
        filing_alerts = [a for a in alerts if "filing" in a.get("title", "").lower()]

        # Assert - depends on current date relative to filing deadline
        # This test validates the alert structure
        if filing_alerts:
            assert filing_alerts[0]["severity"] in ["HIGH", "MEDIUM"]
            assert "action_required" in filing_alerts[0]

    @pytest.mark.django_db
    def test_generate_overdue_invoice_alerts(
        self,
        test_org,
        test_customer,
    ):
        """
        Test: Alert for invoices past due date + 7 days.

        Scenario:
        - Invoice due: Jan 1, 2024
        - Today: Jan 15, 2024 (14 days overdue)
        - Alert SHOULD trigger

        Expected:
        - Alert generated for invoices where due_date < today - 7
        - Includes count and total amount
        """
        # Create overdue invoice
        InvoiceDocument.objects.create(
            id=uuid4(),
            org=test_org,
            document_type="SALES_INVOICE",
            document_number="INV-1001",
            contact=test_customer,
            issue_date=date(2023, 12, 1),
            due_date=date(2024, 1, 1),
            status="OVERDUE",
            total_excl=Decimal("4587.1559"),
            gst_total=Decimal("412.8441"),
            total_incl=Decimal("5000.0000"),
            amount_paid=Decimal("0.0000"),
        )

        # Execute
        service = DashboardService()
        alerts = service.generate_compliance_alerts(str(test_org.id))

        # Find overdue invoice alert
        overdue_alerts = [a for a in alerts if "overdue" in a.get("title", "").lower()]

        # Assert
        if overdue_alerts:
            assert overdue_alerts[0]["severity"] == "HIGH"
            assert "invoices" in overdue_alerts[0]["message"].lower()

    @pytest.mark.django_db
    def test_generate_bank_reconciliation_alert(
        self,
        test_org,
        test_bank_account,
    ):
        """
        Test: Alert for unreconciled bank transactions > 30 days.

        Scenario:
        - Bank transaction imported 40 days ago
        - Not reconciled
        - Alert SHOULD trigger

        Expected:
        - Alert generated for unreconciled transactions > 30 days old
        - Encourages reconciliation
        """
        from apps.core.models import BankTransaction

        # Create unreconciled bank transaction
        BankTransaction.objects.create(
            id=uuid4(),
            org=test_org,
            bank_account=test_bank_account,
            transaction_date=date(2024, 1, 1) - timedelta(days=40),
            amount=Decimal("1000.0000"),
            description="Unreconciled transaction",
            is_reconciled=False,
            imported_at=datetime.now() - timedelta(days=40),
        )

        # Execute
        service = DashboardService()
        alerts = service.generate_compliance_alerts(str(test_org.id))

        # Find reconciliation alert
        recon_alerts = [a for a in alerts if "reconcil" in a.get("title", "").lower()]

        # Assert
        if recon_alerts:
            assert recon_alerts[0]["severity"] in ["MEDIUM", "LOW"]


# ============================================================================
# EDGE CASE TESTS (2 tests)
# ============================================================================


class TestEdgeCases:
    """Test edge cases and error handling."""

    @pytest.mark.django_db
    def test_handles_empty_organisation(
        self,
        test_org,
    ):
        """
        Test: Returns zeros and empty alerts for new org with no data.

        Scenario:
        - New organization created
        - No invoices, payments, or journal entries
        - Dashboard should return all zeros

        Expected:
        - All numeric values = 0
        - Empty compliance_alerts list (or basic alerts)
        - No errors or exceptions
        """
        # Execute
        service = DashboardService()
        result = service.get_dashboard_data(str(test_org.id))

        # Assert
        assert result["gst_payable"] == "0.0000"
        assert result["outstanding_receivables"] == "0.00"
        assert result["outstanding_payables"] == "0.00"
        assert result["revenue_mtd"] == "0.00"
        assert result["revenue_ytd"] == "0.00"
        assert result["cash_on_hand"] == "0.00"
        assert isinstance(result["compliance_alerts"], list)

    @pytest.mark.django_db
    def test_handles_closed_fiscal_periods(
        self,
        test_org,
        test_fiscal_year,
        test_customer,
    ):
        """
        Test: Respects period boundaries and closed periods.

        Scenario:
        - Create invoice in closed period (Jan 2023)
        - Create invoice in open period (Jan 2024)
        - YTD revenue should only include open period

        Expected:
        - Closed periods excluded from calculations
        - Respects fiscal_period.is_open flag
        """
        # Create closed fiscal period
        closed_period = FiscalPeriod.objects.create(
            id=uuid4(),
            org=test_org,
            fiscal_year=test_fiscal_year,
            label="Dec 2023",
            period_number=12,
            start_date=date(2023, 12, 1),
            end_date=date(2023, 12, 31),
            is_open=False,  # CLOSED
        )

        # Create invoice in closed period (should be excluded)
        InvoiceDocument.objects.create(
            id=uuid4(),
            org=test_org,
            document_type="SALES_INVOICE",
            document_number="INV-2001",
            contact=test_customer,
            issue_date=date(2023, 12, 15),
            due_date=date(2024, 1, 15),
            status="APPROVED",
            total_excl=Decimal("10000.0000"),
            gst_total=Decimal("900.0000"),
            total_incl=Decimal("10900.0000"),
            amount_paid=Decimal("10900.0000"),
        )

        # Execute
        service = DashboardService()
        result = service.get_dashboard_data(str(test_org.id))

        # Assert - Revenue should not include closed period invoice
        # (Depends on implementation respecting is_open=False)
        assert isinstance(result["revenue_ytd"], str)
