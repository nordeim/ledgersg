/**
 * P26 — useInvoices hook: the page param (the frontend pagination wiring).
 *
 * RED suite: the hook must carry `limit`/`offset` on the query string AND
 * in the queryKey (the P24/FE-L1 cache-paging trap: without the page
 * identity in the key, a page change resolves the previous page from
 * cache and the table silently shows the wrong rows — the exact bug the
 * ledger hook pinned in P24; every paginated hook gets the same pin).
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import React from "react";
import { useInvoices } from "@/hooks/use-invoices";
import { api } from "@/lib/api-client";

vi.mock("@/lib/api-client", () => ({
  api: { get: vi.fn() },
  endpoints: {
    invoices: (orgId: string) => ({
      list: `/api/v1/${orgId}/invoicing/documents/`,
    }),
  },
}));

const mockList = {
  results: [
    {
      id: "doc-1",
      document_type: "SALES_INVOICE",
      document_number: "INV-000001",
      contact_id: "c-1",
      contact_name: "ABC Pte Ltd",
      issue_date: "2026-01-15",
      due_date: "2026-02-14",
      status: "APPROVED",
      status_display: "Approved",
      total_incl: "109.0000",
      currency: "SGD",
      amount_paid: "0.0000",
      amount_due: "109.0000",
      related_document_id: null,
    },
  ],
  count: 25,
  next: "http://testserver/api/v1/org-1/invoicing/documents/?type=SALES_INVOICE&limit=20&offset=20",
  previous: null,
};

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return function Wrapper({ children }: { children: React.ReactNode }) {
    return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>;
  };
}

describe("useInvoices (P26 page param)", () => {
  const mockedGet = vi.mocked(api.get);

  beforeEach(() => {
    vi.clearAllMocks();
    mockedGet.mockResolvedValue(mockList);
  });

  it("sends limit and offset on the query string with the type filter", async () => {
    const { result } = renderHook(
      () =>
        useInvoices("org-1", { type: "SALES_INVOICE" }, undefined, {
          limit: 20,
          offset: 20,
        }),
      { wrapper: createWrapper() }
    );

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    const url = mockedGet.mock.calls[0][0] as string;
    expect(url).toContain("type=SALES_INVOICE");
    expect(url).toContain("limit=20");
    expect(url).toContain("offset=20");
  });

  it("keeps the unpaginated shape when no page is passed", async () => {
    const { result } = renderHook(
      () => useInvoices("org-1", { type: "SALES_INVOICE" }),
      { wrapper: createWrapper() }
    );

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    const url = mockedGet.mock.calls[0][0] as string;
    expect(url).toContain("type=SALES_INVOICE");
    expect(url).not.toContain("limit=");
    expect(url).not.toContain("offset=");
  });

  it("gives each page its own cache entry (the cache-paging trap)", async () => {
    // Two pages of the same list must be TWO cache entries — a page
    // change must never resolve the previous page's data from cache.
    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });
    const wrapper = function Wrapper({ children }: { children: React.ReactNode }) {
      return (
        <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
      );
    };

    const page1 = renderHook(
      () =>
        useInvoices("org-1", { type: "SALES_INVOICE" }, undefined, {
          limit: 20,
          offset: 0,
        }),
      { wrapper }
    );
    await waitFor(() => expect(page1.result.current.isSuccess).toBe(true));
    expect(mockedGet).toHaveBeenCalledTimes(1);

    const page2 = renderHook(
      () =>
        useInvoices("org-1", { type: "SALES_INVOICE" }, undefined, {
          limit: 20,
          offset: 20,
        }),
      { wrapper }
    );
    await waitFor(() => expect(page2.result.current.isSuccess).toBe(true));

    // The second page FIRED its own fetch — it was not served page 1's
    // cache entry (the P24/FE-L1 trap the ledger hook pinned).
    expect(mockedGet).toHaveBeenCalledTimes(2);
    const secondUrl = mockedGet.mock.calls[1][0] as string;
    expect(secondUrl).toContain("offset=20");
  });

  it("changes the search server-side (the hook carries the filter)", async () => {
    const { result } = renderHook(
      () => useInvoices("org-1", { type: "SALES_INVOICE", search: "INV-000042" }),
      { wrapper: createWrapper() }
    );

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    const url = mockedGet.mock.calls[0][0] as string;
    expect(url).toContain("search=INV-000042");
  });
});
