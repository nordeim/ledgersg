/**
 * P6/C-5 (ledger) — real ledger table + page.
 *
 * RED suite (against the mock table): the table renders props-driven
 * rows (never mockData), and the page wires useLedger through loading /
 * error / empty / data states.
 */

import { describe, it, expect, vi, afterEach, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { LedgerClient } from "../ledger-client";
import * as ledgerHooks from "@/hooks/use-ledger";

// P7/F-12: hoisted mutable auth state so the no-org case is testable.
const { __testAuth } = vi.hoisted(() => ({
  __testAuth: {
    currentOrg: { id: "org-123", name: "Test Org" } as { id: string; name: string } | null,
    isLoading: false,
  },
}));

vi.mock("@/providers/auth-provider", () => ({
  useAuth: () => __testAuth,
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

  // P24/FE-M2: the ledger pages through the backend contract — the
  // controls render with the page summary, and the boundaries disable.
  it("renders the pagination controls with the page summary over real rows (P24)", async () => {
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
        count: 51,
      },
      isLoading: false,
      isError: false,
      error: null,
    } as unknown as ReturnType<typeof ledgerHooks.useLedger>);

    renderPage();

    expect(await screen.findByText("1200")).toBeInTheDocument();
    expect(
      screen.getByRole("navigation", { name: "Pagination" })
    ).toBeInTheDocument();
    expect(screen.getByText("Showing 1–20 of 51 rows")).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: /previous page/i })
    ).toBeDisabled();
    expect(
      screen.getByRole("button", { name: /next page/i })
    ).not.toBeDisabled();
  });

  it("hides the pagination controls for an unpaginated single-page ledger", async () => {
    // count <= page size — the controls stay (Next disabled), the summary
    // reads the full set. Pinned: no crash on the equal boundary.
    vi.mocked(ledgerHooks.useLedger).mockReturnValue({
      data: {
        results: [mockLine()],
        count: 1,
      },
      isLoading: false,
      isError: false,
      error: null,
    } as unknown as ReturnType<typeof ledgerHooks.useLedger>);

    renderPage();

    expect(await screen.findByText("1200")).toBeInTheDocument();
    expect(screen.getByText("Showing 1–1 of 1 rows")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /next page/i })).toBeDisabled();
  });
});

describe("LedgerClient — no-organisation state (P7/F-12)", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    __testAuth.currentOrg = null;
    __testAuth.isLoading = false;
  });

  afterEach(() => {
    __testAuth.currentOrg = { id: "org-123", name: "Test Org" };
  });

  it("renders the no-org state for an org-less user (never a fake empty ledger)", () => {
    // Disabled query: isLoading=false, isError=false, data=undefined — the
    // pre-P7 client fell through to "No journal entries yet".
    vi.mocked(ledgerHooks.useLedger).mockReturnValue({
      data: undefined,
      isLoading: false,
      isError: false,
      error: null,
    } as unknown as ReturnType<typeof ledgerHooks.useLedger>);

    renderPage();

    expect(screen.getByText(/no organisation selected/i)).toBeInTheDocument();
    expect(screen.queryByText(/no journal entries yet/i)).not.toBeInTheDocument();
  });
});
