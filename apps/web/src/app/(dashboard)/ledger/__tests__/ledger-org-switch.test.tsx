/**
 * P25/FE-L3 — the organisation-switch offset reset, tested through the
 * REAL useLedger hook (only the api-client transport is mocked).
 *
 * The pre-P25 reset lived in a useEffect — the stale-offset fetch it
 * could dispatch is TIMING-EMERGENT, not guaranteed absent: on the
 * current stack (React 19 + TanStack 5.90) notifyManager batching
 * happens to suppress it (verified: the old code never fires the
 * stale URL either). The P25 render-time reset (the React-endorsed
 * prev-state pattern) makes the guarantee EXPLICIT rather than
 * dependent on effect-order internals a library upgrade could change.
 * A module mock of useLedger cannot observe any of this (a discarded
 * render still calls the mock synchronously); the REAL TanStack hook
 * under a REAL QueryClient only fetches what a COMMITTED render asks
 * for — so this file asserts on the transport URLs themselves: no
 * fetch for the switched org may ever carry the previous org's
 * offset. This spec is the regression PIN for that contract.
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { LedgerClient } from "../ledger-client";

const fetchedUrls: string[] = [];

vi.mock("@/lib/api-client", () => ({
  api: {
    get: vi.fn(async (url: string) => {
      fetchedUrls.push(url);
      return {
        results: [
          {
            id: `line-${fetchedUrls.length}`,
            entry_id: "entry-1",
            entry_number: 1,
            entry_date: "2026-01-15",
            source_type: "MANUAL",
            reference: "",
            narration: "probe",
            line_number: 1,
            account_id: "acc-1200",
            account_code: "1200",
            account_name: "Accounts Receivable",
            description: "probe line",
            debit: "10.0000",
            credit: "0.0000",
          },
        ],
        count: 51,
      };
    }),
  },
  endpoints: {
    journal: (orgId: string) => ({
      ledger: `/api/v1/${orgId}/journal-entries/ledger/`,
    }),
  },
}));

const { __testAuth } = vi.hoisted(() => ({
  __testAuth: {
    currentOrg: { id: "org-123", name: "Test Org" } as
      | { id: string; name: string }
      | null,
    isLoading: false,
  },
}));

vi.mock("@/providers/auth-provider", () => ({
  useAuth: () => __testAuth,
}));

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

describe("LedgerClient — the organisation-switch offset reset (P25/FE-L3)", () => {
  beforeEach(() => {
    fetchedUrls.length = 0;
    __testAuth.currentOrg = { id: "org-123", name: "Test Org" };
  });

  it("never fetches the switched organisation at the previous org's offset", async () => {
    const { rerender } = renderPage();

    // Wait for page 1 of org-123, then walk to page 3 (offset 40).
    expect(await screen.findByText("Showing 1–20 of 51 rows")).toBeInTheDocument();
    const user = userEvent.setup();
    await user.click(screen.getByRole("button", { name: /next page/i }));
    expect(await screen.findByText("Showing 21–40 of 51 rows")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: /next page/i }));
    expect(await screen.findByText("Showing 41–51 of 51 rows")).toBeInTheDocument();
    expect(
      fetchedUrls.some((u) => u.includes("org-123") && u.includes("offset=40"))
    ).toBe(true);

    // Switch the organisation mid-pagination.
    __testAuth.currentOrg = { id: "org-456", name: "Switched Org" };
    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });
    rerender(
      <QueryClientProvider client={queryClient}>
        <LedgerClient />
      </QueryClientProvider>
    );

    // The new org settles on its page 1 …
    expect(await screen.findByText("Showing 1–20 of 51 rows")).toBeInTheDocument();

    // … and NOT ONE of its fetches carried the stale offset (the
    // useEffect reset committed exactly such a fetch pre-P25).
    const switchedOrgUrls = fetchedUrls.filter((u) => u.includes("org-456"));
    expect(switchedOrgUrls.length).toBeGreaterThan(0);
    expect(
      switchedOrgUrls.some(
        (u) => u.includes("offset=40") || u.includes("offset=20")
      ),
      `the switched org must never be fetched at a stale offset — got: ${switchedOrgUrls.join(", ")}`
    ).toBe(false);
    expect(switchedOrgUrls.some((u) => u.includes("offset=0"))).toBe(true);
  });
});
