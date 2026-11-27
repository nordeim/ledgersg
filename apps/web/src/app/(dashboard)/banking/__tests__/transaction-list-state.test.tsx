/**
 * P27/FE-M2 + FE-M3 — the transactions-list pagination state-machine
 * contracts, tested through the REAL useBankTransactions hook (only
 * the api-client transport is mocked — the ledger-org-switch.test.tsx
 * pattern; the rationale is documented in
 * invoices-pagination-state.test.tsx).
 *
 * The contracts pinned here (the payments-surface mirror):
 * (a) P27/FE-M2 — changing the FILTERS restarts the paging.
 * (b) P27/FE-M3 — switching the orgId prop mid-pagination never
 *     dispatches the new org at the previous offset.
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { TransactionList } from "../components/transaction-list";
import type { BankTransaction } from "@/shared/schemas";

const fetchedUrls: string[] = [];

vi.mock("@/lib/api-client", () => ({
  api: {
    get: vi.fn(async (url: string) => {
      fetchedUrls.push(url);
      return {
        results: [
          {
            id: `txn-${fetchedUrls.length}`,
            org: "org-123",
            bank_account: "bank-1",
            bank_account_name: "Test Account",
            transaction_date: "2026-01-15",
            value_date: "2026-01-15",
            description: "GIRO payment from customer",
            reference: null,
            amount: "5000.0000",
            running_balance: null,
            is_reconciled: false,
            reconciled_at: null,
            matched_payment: null,
            import_source: "CSV",
            external_id: null,
            created_at: "2026-01-15T10:00:00Z",
            updated_at: "2026-01-15T10:00:00Z",
          } satisfies BankTransaction,
        ],
        count: 51,
      };
    }),
  },
  endpoints: {
    banking: (orgId: string) => ({
      transactions: `/api/v1/${orgId}/banking/bank-transactions/`,
    }),
  },
}));

function renderList(
  orgId = "org-123",
  filters?: { bank_account_id?: string; unreconciled_only?: boolean }
) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <TransactionList orgId={orgId} filters={filters} />
    </QueryClientProvider>
  );
}

describe("TransactionList — the pagination state machine (P27)", () => {
  beforeEach(() => {
    fetchedUrls.length = 0;
  });

  it("(a) changing the filters restarts the paging (P27/FE-M2)", async () => {
    const { rerender } = renderList();

    // Walk to page 2 of the unfiltered set.
    expect(await screen.findByText("Showing 1–20 of 51 rows")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: /next page/i }));
    expect(await screen.findByText("Showing 21–40 of 51 rows")).toBeInTheDocument();

    // The user narrows the filter (a NEW filters object identity).
    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });
    rerender(
      <QueryClientProvider client={queryClient}>
        <TransactionList
          orgId="org-123"
          filters={{ unreconciled_only: true }}
        />
      </QueryClientProvider>
    );

    // The filtered set is fetched at offset 0 — never at the stale
    // offset 20.
    expect(
      await screen.findByText("Showing 1–20 of 51 rows")
    ).toBeInTheDocument();
    const filteredUrls = fetchedUrls.filter((u) =>
      u.includes("unreconciled_only=true")
    );
    expect(filteredUrls.length).toBeGreaterThan(0);
    expect(
      filteredUrls.some((u) => u.includes("offset=20")),
      `the filtered set must never be fetched at a stale offset — got: ${filteredUrls.join(", ")}`
    ).toBe(false);
    expect(filteredUrls.some((u) => u.includes("offset=0"))).toBe(true);
  });

  it("(b) switching the organisation never dispatches the new org at the previous offset (P27/FE-M3)", async () => {
    const { rerender } = renderList();

    expect(await screen.findByText("Showing 1–20 of 51 rows")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: /next page/i }));
    expect(await screen.findByText("Showing 21–40 of 51 rows")).toBeInTheDocument();

    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });
    rerender(
      <QueryClientProvider client={queryClient}>
        <TransactionList orgId="org-456" />
      </QueryClientProvider>
    );

    expect(
      await screen.findByText("Showing 1–20 of 51 rows")
    ).toBeInTheDocument();
    const switchedOrgUrls = fetchedUrls.filter((u) => u.includes("org-456"));
    expect(switchedOrgUrls.length).toBeGreaterThan(0);
    expect(
      switchedOrgUrls.some((u) => u.includes("offset=20")),
      `the switched org must never be fetched at a stale offset — got: ${switchedOrgUrls.join(", ")}`
    ).toBe(false);
    expect(switchedOrgUrls.some((u) => u.includes("offset=0"))).toBe(true);
  });
});
