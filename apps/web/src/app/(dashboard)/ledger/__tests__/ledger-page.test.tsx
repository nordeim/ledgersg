/**
 * P6/C-5 (ledger) — real ledger table + page.
 *
 * RED suite (against the mock table): the table renders props-driven
 * rows (never mockData), and the page wires useLedger through loading /
 * error / empty / data states.
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { LedgerClient } from "../ledger-client";
import * as ledgerHooks from "@/hooks/use-ledger";

vi.mock("@/providers/auth-provider", () => ({
  useAuth: () => ({
    currentOrg: { id: "org-123", name: "Test Org" },
    isLoading: false,
  }),
}));

vi.mock("@/hooks/use-ledger");

const mockLine = (overrides: Record<string, unknown> = {}) => ({
  id: "line-1",
  entry_id: "entry-1",
  entry_number: 1,
  entry_date: "2026-01-15",
  source_type: "SALES_INVOICE",
  reference: "INV-000001",
  narration: "Invoice INV-000001",
  line_number: 1,
  account_id: "acc-1200",
  account_code: "1200",
  account_name: "Accounts Receivable",
  description: "Invoice INV-000001",
  debit: "5450.0000",
  credit: "0.0000",
  ...overrides,
});

function renderPage() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <LedgerClient />
    </QueryClientProvider>
  );
}

describe("LedgerClient (real data)", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders real ledger lines from useLedger", async () => {
    vi.mocked(ledgerHooks.useLedger).mockReturnValue({
      data: {
        results: [
          mockLine(),
          mockLine({
            id: "line-2",
            line_number: 2,
            account_code: "4100",
            account_name: "Sales Revenue",
            debit: "0.0000",
            credit: "5000.0000",
          }),
        ],
        count: 2,
      },
      isLoading: false,
      isError: false,
      error: null,
    } as unknown as ReturnType<typeof ledgerHooks.useLedger>);

    renderPage();

    expect(await screen.findByText("1200")).toBeInTheDocument();
    expect(screen.getByText("Accounts Receivable")).toBeInTheDocument();
    expect(screen.getByText("Sales Revenue")).toBeInTheDocument();
    expect(screen.getByText("5,450.00")).toBeInTheDocument();
    expect(screen.getByText("5,000.00")).toBeInTheDocument();
    // the mock fixture data must be gone
    expect(screen.queryByText("Office Expenses")).not.toBeInTheDocument();
    expect(screen.queryByText("Office supplies purchase")).not.toBeInTheDocument();
  });

  it("shows the empty state when the ledger has no lines", async () => {
    vi.mocked(ledgerHooks.useLedger).mockReturnValue({
      data: { results: [], count: 0 },
      isLoading: false,
      isError: false,
      error: null,
    } as unknown as ReturnType<typeof ledgerHooks.useLedger>);

    renderPage();

    expect(await screen.findByText(/no journal entries yet/i)).toBeInTheDocument();
  });

  it("shows the error state when the ledger fails to load", async () => {
    vi.mocked(ledgerHooks.useLedger).mockReturnValue({
      data: undefined,
      isLoading: false,
      isError: true,
      error: new Error("Network error"),
    } as unknown as ReturnType<typeof ledgerHooks.useLedger>);

    renderPage();

    expect(await screen.findByText(/failed to load/i)).toBeInTheDocument();
  });

  it("shows the loading state while fetching", () => {
    vi.mocked(ledgerHooks.useLedger).mockReturnValue({
      data: undefined,
      isLoading: true,
      isError: false,
      error: null,
    } as unknown as ReturnType<typeof ledgerHooks.useLedger>);

    renderPage();

    expect(screen.getByText(/loading/i)).toBeInTheDocument();
  });
});
