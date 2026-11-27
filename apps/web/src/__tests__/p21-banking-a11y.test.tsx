/**
 * P21 banking a11y + contract gates — RED first.
 *
 * FE-P21-H1: the Make-Payment form's Reference input has no accessible
 *   name (the in-file "Notes" twin carries aria-label; Reference is the
 *   miss) — WCAG 1.3.1/4.1.2 Level A on the payables money form.
 * FE-P21-H2: the CSV import file input is display:hidden — removed from
 *   the tab order and the a11y tree; the clickable label is not
 *   focusable. Keyboard-only users have no path to import a statement
 *   (WCAG 2.1.1 Level A). Fix: sr-only (focusable, labelled).
 * FE-P21-M1: duplicate DOM id "bank-account" — the import dialog's
 *   "Bank Account" label resolves to the background TransactionFilters
 *   select when both are mounted (the dialog opens from the same tab
 *   that renders the filters).
 * FE-P21-M4: the payment card is a clickable div with no keyboard
 *   contract (the P19 transaction-row class, unfixed here).
 * FE-P21-M5: the reconcile dialog's match selection is invisible to
 *   assistive tech — no aria-pressed on the toggle buttons.
 * FE-P21-M2: spinner-only loading blocks with no role="status" remain
 *   on the banking/settings surfaces P20 did not touch (WCAG 4.1.3).
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { MakePaymentForm } from "@/app/(dashboard)/banking/components/make-payment-form";
import { ImportTransactionsForm } from "@/app/(dashboard)/banking/components/import-transactions-form";
import { TransactionFilters } from "@/app/(dashboard)/banking/components/transaction-filters";
import { PaymentCard } from "@/app/(dashboard)/banking/components/payment-card";
import { ReconcileForm } from "@/app/(dashboard)/banking/components/reconcile-form";
import { AllocationSection } from "@/app/(dashboard)/banking/components/allocation-section";
import { FiscalCard } from "@/app/(dashboard)/settings/components/fiscal-card";
import { InvoiceNowSettingsCard } from "@/app/(dashboard)/settings/components/invoicenow-settings-card";
import { useMakePayment, useBankAccounts, useSuggestMatches, useReconcileTransaction, useImportBankTransactions } from "@/hooks/use-banking";
import { useContacts } from "@/hooks/use-contacts";
import { useInvoices } from "@/hooks/use-invoices";
import { useFiscalYears, useFiscalPeriods, useOpenFiscalPeriod, useCloseFiscalPeriod, useCloseFiscalYear } from "@/hooks/use-fiscal";
import { usePeppolSettings } from "@/hooks/use-peppol";
import type { Payment, BankTransaction } from "@/shared/schemas";

vi.mock("@/hooks/use-banking", () => ({
  useMakePayment: vi.fn(),
  useBankAccounts: vi.fn(),
  useSuggestMatches: vi.fn(),
  useReconcileTransaction: vi.fn(),
  useImportBankTransactions: vi.fn(),
  useBankTransactions: vi.fn(),
}));

vi.mock("@/hooks/use-contacts", () => ({
  useContacts: vi.fn(),
}));

vi.mock("@/hooks/use-invoices", () => ({
  useInvoices: vi.fn().mockReturnValue({ data: { results: [], count: 0 }, isLoading: false }),
}));

vi.mock("@/hooks/use-fiscal", () => ({
  useFiscalYears: vi.fn(),
  useFiscalPeriods: vi.fn(),
  useOpenFiscalPeriod: vi.fn(),
  useCloseFiscalPeriod: vi.fn(),
  useCloseFiscalYear: vi.fn(),
}));

vi.mock("@/hooks/use-peppol", () => ({
  usePeppolSettings: vi.fn(),
}));

// FiscalCard consumes useAuth for the permission gate.
vi.mock("@/providers/auth-provider", () => ({
  useAuth: () => ({ hasPermission: () => true }),
}));

const mockMakePayment = useMakePayment as unknown as ReturnType<typeof vi.fn>;
const mockBankAccounts = useBankAccounts as unknown as ReturnType<typeof vi.fn>;
const mockContacts = useContacts as unknown as ReturnType<typeof vi.fn>;
const mockSuggestMatches = useSuggestMatches as unknown as ReturnType<typeof vi.fn>;
const mockReconcileTransaction = useReconcileTransaction as unknown as ReturnType<typeof vi.fn>;
const mockFiscalYears = useFiscalYears as unknown as ReturnType<typeof vi.fn>;
const mockFiscalPeriods = useFiscalPeriods as unknown as ReturnType<typeof vi.fn>;
const mockOpenFiscalPeriod = useOpenFiscalPeriod as unknown as ReturnType<typeof vi.fn>;
const mockCloseFiscalPeriod = useCloseFiscalPeriod as unknown as ReturnType<typeof vi.fn>;
const mockCloseFiscalYear = useCloseFiscalYear as unknown as ReturnType<typeof vi.fn>;
const mockPeppolSettings = usePeppolSettings as unknown as ReturnType<typeof vi.fn>;
const mockInvoices = useInvoices as unknown as ReturnType<typeof vi.fn>;

const ORG_ID = "550e8400-e29b-41d4-a716-446655440001";

const SUPPLIER = {
  id: "33333333-3333-4333-8333-333333333333",
  name: "Globex Supplies",
  email: "ap@globex.example",
  contact_type: "SUPPLIER",
  is_active: true,
};

const BANK_ACCOUNTS = {
  results: [
    { id: "44444444-4444-4444-8444-444444444444", account_name: "DBS Operating" },
    { id: "55555555-5555-5555-8555-555555555555", account_name: "OCBC Savings" },
  ],
  count: 2,
};

const PAYMENT: Payment = {
  id: "550e8400-e29b-41d4-a716-446655440001",
  org: "550e8400-e29b-41d4-a716-446655440002",
  payment_type: "RECEIVED",
  payment_number: "PAY-2024-001",
  payment_date: "2024-03-01",
  contact: "550e8400-e29b-41d4-a716-446655440003",
  contact_name: "Acme Corporation",
  bank_account: "550e8400-e29b-41d4-a716-446655440004",
  bank_account_name: "DBS Operating Account",
  currency: "SGD",
  exchange_rate: "1.000000",
  amount: "5000.0000",
  base_amount: "5000.0000",
  fx_gain_loss: "0.0000",
  payment_method: "BANK_TRANSFER",
  payment_method_display: "Bank Transfer",
  payment_reference: "INV-2024-015",
  journal_entry: null,
  is_reconciled: false,
  is_voided: false,
  notes: null,
  created_at: "2024-03-01T10:00:00Z",
  updated_at: "2024-03-01T10:00:00Z",
};

const TRANSACTION: BankTransaction = {
  id: "txn-1",
  org: ORG_ID,
  bank_account: "acc-1",
  bank_account_name: "DBS Account",
  transaction_date: "2024-03-15",
  value_date: "2024-03-15",
  description: "Customer Payment",
  reference: "INV-001",
  amount: "5000.0000",
  running_balance: "10000.0000",
  is_reconciled: false,
  reconciled_at: undefined,
  matched_payment: undefined,
  import_source: "CSV",
  external_id: null,
  created_at: "2024-03-15T10:00:00Z",
  updated_at: "2024-03-15T10:00:00Z",
};

const MATCHES = [
  {
    payment_id: "pay-1",
    payment_number: "PAY-2024-001",
    amount: "5000.0000",
    contact_name: "Customer ABC",
    match_score: 95,
  },
  {
    payment_id: "pay-2",
    payment_number: "PAY-2024-002",
    amount: "4500.0000",
    contact_name: "Customer XYZ",
    match_score: 75,
  },
];

describe("P21 banking a11y (RED first)", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockMakePayment.mockReturnValue({
      mutateAsync: vi.fn().mockResolvedValue({}),
      isError: false,
      isLoading: false,
      error: null,
    });
    mockBankAccounts.mockReturnValue({
      data: BANK_ACCOUNTS,
      isLoading: false,
      error: null,
    });
    mockContacts.mockReturnValue({ data: [SUPPLIER], isLoading: false });
    mockSuggestMatches.mockReturnValue({ data: MATCHES, isLoading: false, error: null });
    mockReconcileTransaction.mockReturnValue({
      mutateAsync: vi.fn().mockResolvedValue({}),
      isLoading: false,
      error: null,
    });
    mockInvoices.mockReturnValue({ data: { results: [], count: 0 }, isLoading: false });
    vi.mocked(useImportBankTransactions).mockReturnValue({
      mutateAsync: vi.fn().mockResolvedValue({}),
      isPending: false,
      isError: false,
      error: null,
    } as unknown as ReturnType<typeof useImportBankTransactions>);
  });

  it("FE-H1: the Make-Payment Reference input has an accessible name", () => {
    render(<MakePaymentForm orgId={ORG_ID} />);

    // RED: the label has no htmlFor and the Input has no aria-label —
    // this role query cannot resolve today.
    expect(screen.getByRole("textbox", { name: "Reference" })).toBeInTheDocument();
  });

  it("FE-H2: the CSV file input is labelled and keyboard-reachable", () => {
    render(<ImportTransactionsForm orgId={ORG_ID} onCancel={vi.fn()} />);

    // RED: the input is display:hidden (className="hidden") — the fix
    // swaps it for sr-only so it stays in the tab order + a11y tree.
    const fileInput = document.getElementById("csv-file");
    expect(fileInput).not.toBeNull();
    expect(fileInput?.className).not.toContain("hidden");
    expect(fileInput?.className).toContain("sr-only");
    // The label must resolve to the input (the association survives).
    expect(screen.getByLabelText(/CSV File/i)).toBe(fileInput);
  });

  it("FE-M1: the import dialog's bank-account id is unique (co-mounted with the filters)", () => {
    const noop = vi.fn();
    render(
      <div>
        {/* The always-rendered background filters */}
        <TransactionFilters
          filters={{ bank_account_id: undefined, is_reconciled: null, unreconciled_only: false }}
          onChange={noop}
          bankAccounts={BANK_ACCOUNTS.results}
        />
        {/* The Radix-portal import dialog content (simplified co-mount) */}
        <ImportTransactionsForm orgId={ORG_ID} onCancel={noop} />
      </div>
    );

    // RED: both components use id="bank-account" — the co-mounted DOM
    // has TWO elements with the id and label association is wrong.
    const bankAccountIds = document.querySelectorAll("#bank-account");
    expect(bankAccountIds).toHaveLength(1);
    const importIds = document.querySelectorAll("#import-bank-account");
    expect(importIds).toHaveLength(1);
  });

  it("FE-M4: the payment card is keyboard-operable (Enter activates)", () => {
    const onClick = vi.fn();
    render(<PaymentCard payment={PAYMENT} onClick={onClick} />);

    const card = screen.getByTestId("payment-card");
    // RED: the Card is a plain div — no role, no tabIndex, no keydown.
    expect(card).toHaveAttribute("role", "button");
    expect(card).toHaveAttribute("tabindex", "0");
    card.focus();
    fireEvent.keyDown(card, { key: "Enter" });
    expect(onClick).toHaveBeenCalledWith(PAYMENT);
  });

  it("FE-M5: the reconcile match selection exposes aria-pressed", () => {
    render(
      <ReconcileForm orgId={ORG_ID} transaction={TRANSACTION} onClose={vi.fn()} />
    );

    const first = screen.getByRole("button", { name: /PAY-2024-001/ });
    // RED: selection is conveyed only via border/bg classes today.
    expect(first).toHaveAttribute("aria-pressed", "false");
    fireEvent.click(first);
    expect(first).toHaveAttribute("aria-pressed", "true");
  });

  it("FE-M2: the allocation-section loader is a live region", () => {
    mockInvoices.mockReturnValue({ data: { results: [], count: 0 }, isLoading: true });
    render(
      <AllocationSection
        orgId={ORG_ID}
        contactId="33333333-3333-4333-8333-333333333333"
        documentType="SALES_INVOICE"
        allocations={[]}
        onChange={vi.fn()}
      />
    );
    const loader = document.querySelector('[data-testid="open-documents-loading"]') ?? undefined;
    const statusBlocks = Array.from(document.querySelectorAll('[role="status"]'));
    // RED: the spinner block carries no role today.
    expect(statusBlocks.length).toBeGreaterThan(0);
    expect(loader?.getAttribute("role") ?? statusBlocks[0]?.getAttribute("role")).toBe("status");
  });

  it("FE-M2: the fiscal-card loader is a live region", () => {
    mockFiscalYears.mockReturnValue({ data: undefined, isLoading: true });
    mockFiscalPeriods.mockReturnValue({ data: { results: [], count: 0 } });
    mockOpenFiscalPeriod.mockReturnValue({ data: undefined, isLoading: false });
    mockCloseFiscalPeriod.mockReturnValue({ mutateAsync: vi.fn(), isLoading: false });
    mockCloseFiscalYear.mockReturnValue({ mutateAsync: vi.fn(), isLoading: false });
    render(<FiscalCard orgId={ORG_ID} />);

    expect(
      document.querySelector('[data-testid="fiscal-card-loading"]')?.getAttribute("role")
    ).toBe("status");
  });

  it("FE-M2: the invoicenow-settings-card loader is a live region", () => {
    mockPeppolSettings.mockReturnValue({ data: undefined, isLoading: true });
    render(<InvoiceNowSettingsCard orgId={ORG_ID} />);

    expect(
      document.querySelector('[data-testid="invoicenow-card-loading"]')?.getAttribute("role")
    ).toBe("status");
  });
});
