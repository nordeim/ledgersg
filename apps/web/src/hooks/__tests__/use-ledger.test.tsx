/**
 * P6/C-5 (ledger) — useLedger hook.
 *
 * RED suite: the hook must fetch the flat line-level ledger contract
 * ({results, count}) from the journal ledger endpoint, stay disabled
 * until the org context resolves, and pass through filters.
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useLedger } from "@/hooks/use-ledger";
import { api } from "@/lib/api-client";

vi.mock("@/lib/api-client", () => ({
  api: { get: vi.fn() },
  endpoints: {
    journal: (orgId: string) => ({
      ledger: `/api/v1/${orgId}/journal-entries/ledger/`,
    }),
  },
}));

const mockLedgerResponse = {
  results: [
    {
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
    },
    {
      id: "line-2",
      entry_id: "entry-1",
      entry_number: 1,
      entry_date: "2026-01-15",
      source_type: "SALES_INVOICE",
      reference: "INV-000001",
      narration: "Invoice INV-000001",
      line_number: 2,
      account_id: "acc-4100",
      account_code: "4100",
      account_name: "Sales Revenue",
      description: "Invoice INV-000001",
      debit: "0.0000",
      credit: "5000.0000",
    },
  ],
  count: 2,
};

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  const Wrapper = ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );
  return Wrapper;
}

describe("useLedger", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("fetches the flat ledger contract from the ledger endpoint", async () => {
    vi.mocked(api.get).mockResolvedValue(mockLedgerResponse);

    const { result } = renderHook(() => useLedger("org-123"), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.data).toBeDefined());

    expect(api.get).toHaveBeenCalledWith(
      "/api/v1/org-123/journal-entries/ledger/"
    );
    expect(result.current.data?.results).toHaveLength(2);
    expect(result.current.data?.results[0].account_code).toBe("1200");
    expect(result.current.data?.results[0].debit).toBe("5450.0000");
  });

  it("stays disabled until the org context resolves", async () => {
    const { result } = renderHook(() => useLedger(null), {
      wrapper: createWrapper(),
    });

    expect(result.current.isLoading).toBe(false);
    expect(api.get).not.toHaveBeenCalled();
  });

  it("passes date filters through as query parameters", async () => {
    vi.mocked(api.get).mockResolvedValue(mockLedgerResponse);

    const { result } = renderHook(
      () => useLedger("org-123", { date_from: "2026-01-01" }),
      { wrapper: createWrapper() }
    );

    await waitFor(() => expect(result.current.data).toBeDefined());

    expect(api.get).toHaveBeenCalledWith(
      "/api/v1/org-123/journal-entries/ledger/?date_from=2026-01-01"
    );
  });
});
