/**
 * P27/FE-M3 — the quotes pagination state-machine contract, tested
 * through the REAL useInvoices hook (only the api-client transport is
 * mocked — the ledger-org-switch.test.tsx pattern; the rationale is
 * documented in invoices-pagination-state.test.tsx).
 *
 * The surface has no search and no filters — only the organisation-
 * switch reset applies (the P25/FE-L3 ledger contract, extended to
 * this surface): switching org mid-pagination must never dispatch the
 * new org at the previous offset.
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { QuotesClient } from "../quotes-client";

const fetchedUrls: string[] = [];

vi.mock("@/lib/api-client", () => ({
  api: {
    get: vi.fn(async (url: string) => {
      fetchedUrls.push(url);
      return {
        results: [
          {
            id: `doc-${fetchedUrls.length}`,
            document_type: "SALES_QUOTE",
            document_number: "QT-000001",
            contact_id: "contact-1",
            contact_name: "ABC Pte Ltd",
            issue_date: "2026-01-15",
            due_date: "2026-02-14",
            status: "SENT",
            status_display: "Sent",
            total_incl: "5400.0000",
            currency: "SGD",
            amount_paid: "0.0000",
            amount_due: "5400.0000",
            related_document_id: null,
          },
        ],
        count: 51,
      };
    }),
  },
  endpoints: {
    invoices: (orgId: string) => ({
      list: `/api/v1/${orgId}/invoicing/documents/`,
    }),
    quotes: (orgId: string) => ({
      list: `/api/v1/${orgId}/invoicing/documents/?type=SALES_QUOTE`,
      convert: `/api/v1/${orgId}/invoicing/quotes/convert/`,
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

// QuotesClient mounts useConvertQuote (the conversion mutation), whose
// useRouter() needs an App Router context — absent under RTL.
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn() }),
}));

function renderPage() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <QuotesClient />
    </QueryClientProvider>
  );
}

describe("QuotesClient — the pagination state machine (P27)", () => {
  beforeEach(() => {
    fetchedUrls.length = 0;
    __testAuth.currentOrg = { id: "org-123", name: "Test Org" };
  });

  it("never fetches the switched organisation at the previous offset (P27/FE-M3)", async () => {
    const { rerender } = renderPage();

    // Walk to page 2 of org-123.
    expect(await screen.findByText("Showing 1–20 of 51 rows")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: /next page/i }));
    expect(await screen.findByText("Showing 21–40 of 51 rows")).toBeInTheDocument();
    expect(
      fetchedUrls.some(
        (u) => u.includes("org-123") && u.includes("SALES_QUOTE") && u.includes("offset=20")
      )
    ).toBe(true);

    // Switch the organisation mid-pagination.
    __testAuth.currentOrg = { id: "org-456", name: "Switched Org" };
    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });
    rerender(
      <QueryClientProvider client={queryClient}>
        <QuotesClient />
      </QueryClientProvider>
    );

    // The new org settles on its page 1 …
    expect(
      await screen.findByText("Showing 1–20 of 51 rows")
    ).toBeInTheDocument();

    // … and NOT ONE of its fetches carried the stale offset.
    const switchedOrgUrls = fetchedUrls.filter((u) => u.includes("org-456"));
    expect(switchedOrgUrls.length).toBeGreaterThan(0);
    expect(
      switchedOrgUrls.some((u) => u.includes("offset=20")),
      `the switched org must never be fetched at a stale offset — got: ${switchedOrgUrls.join(", ")}`
    ).toBe(false);
    expect(switchedOrgUrls.some((u) => u.includes("offset=0"))).toBe(true);
  });
});
