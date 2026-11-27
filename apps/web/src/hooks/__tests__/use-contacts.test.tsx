/**
 * P26 — useContacts hook: the envelope + the page param.
 *
 * RED suite: the hook must return the FULL list envelope
 * ({results, count}) — the pre-P26 hook unwrapped `results` and threw
 * the count away, so no consumer could ever render a truthful "of N"
 * line or paginate. Plus the page param on the query string AND in the
 * queryKey (the P24/FE-L1 cache-paging trap — every paginated hook
 * gets the same pin the ledger set).
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import React from "react";
import { useContacts } from "@/hooks/use-contacts";
import { api } from "@/lib/api-client";

vi.mock("@/lib/api-client", () => ({
  api: { get: vi.fn() },
  endpoints: {
    contacts: (orgId: string) => ({
      list: `/api/v1/${orgId}/invoicing/contacts/`,
      detail: (id: string) => `/api/v1/${orgId}/invoicing/contacts/${id}/`,
    }),
  },
}));

const mockContact = (id: string) => ({
  id,
  org_id: "org-1",
  contact_type: "CUSTOMER" as const,
  name: `Contact ${id}`,
  country: "SG",
  is_peppol_enabled: false,
  payment_terms_days: 30,
  currency: "SGD",
  is_active: true,
  created_at: "2026-01-01T00:00:00Z",
  updated_at: "2026-01-01T00:00:00Z",
});

const mockEnvelope = {
  results: [mockContact("c-1"), mockContact("c-2")],
  count: 2,
};

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return function Wrapper({ children }: { children: React.ReactNode }) {
    return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>;
  };
}

describe("useContacts (P26 envelope + page param)", () => {
  const mockedGet = vi.mocked(api.get);

  beforeEach(() => {
    vi.clearAllMocks();
    mockedGet.mockResolvedValue(mockEnvelope);
  });

  it("returns the FULL envelope (results + count), never the bare array", async () => {
    const { result } = renderHook(() => useContacts("org-1"), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    // RED: the pre-P26 hook returned response.results (the bare array).
    expect(result.current.data).toHaveProperty("results");
    expect(result.current.data).toHaveProperty("count", 2);
    expect(Array.isArray(result.current.data?.results)).toBe(true);
  });

  it("sends limit and offset on the query string with the filters", async () => {
    const { result } = renderHook(
      () =>
        useContacts(
          "org-1",
          { is_customer: true },
          { limit: 20, offset: 20 }
        ),
      { wrapper: createWrapper() }
    );

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    const url = mockedGet.mock.calls[0][0] as string;
    expect(url).toContain("is_customer=true");
    expect(url).toContain("limit=20");
    expect(url).toContain("offset=20");
  });

  it("keeps the unpaginated shape when no page is passed (the picker contract)", async () => {
    const { result } = renderHook(
      () => useContacts("org-1", { search: "demo" }),
      { wrapper: createWrapper() }
    );

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    const url = mockedGet.mock.calls[0][0] as string;
    expect(url).toContain("search=demo");
    expect(url).not.toContain("limit=");
    expect(url).not.toContain("offset=");
    // The picker consumes data.results — the envelope keeps that key.
    expect(result.current.data?.results).toHaveLength(2);
  });

  it("gives each page its own cache entry (the cache-paging trap)", async () => {
    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });
    const wrapper = function Wrapper({ children }: { children: React.ReactNode }) {
      return (
        <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
      );
    };

    const page1 = renderHook(
      () => useContacts("org-1", undefined, { limit: 20, offset: 0 }),
      { wrapper }
    );
    await waitFor(() => expect(page1.result.current.isSuccess).toBe(true));
    expect(mockedGet).toHaveBeenCalledTimes(1);

    const page2 = renderHook(
      () => useContacts("org-1", undefined, { limit: 20, offset: 20 }),
      { wrapper }
    );
    await waitFor(() => expect(page2.result.current.isSuccess).toBe(true));

    expect(mockedGet).toHaveBeenCalledTimes(2);
    const secondUrl = mockedGet.mock.calls[1][0] as string;
    expect(secondUrl).toContain("offset=20");
  });
});
