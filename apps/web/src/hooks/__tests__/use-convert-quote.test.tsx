/**
 * P9/C-1: useConvertQuote must read the REAL convert envelope.
 *
 * The endpoint POSTs back {"message", "invoice": {...}} (nested — pinned by
 * tests/integration/test_quotes_p8.py::TestQuoteConvertEndpointEnvelopeP9),
 * but the hook read the response FLAT, so every conversion toasted
 * "Invoice undefined created" and routed to /invoices/undefined.
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, waitFor, act } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import type { ReactNode } from "react";
import * as apiClient from "@/lib/api-client";
import { useConvertQuote } from "../use-invoices";

vi.mock("@/lib/api-client", () => ({
  api: {
    post: vi.fn(),
  },
  endpoints: {
    quotes: (orgId: string) => ({
      convert: `/api/v1/${orgId}/invoicing/quotes/convert/`,
    }),
  },
}));

const push = vi.fn();
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push, replace: vi.fn(), back: vi.fn() }),
}));

vi.mock("@/hooks/use-toast", () => ({
  toast: vi.fn(),
}));

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return function Wrapper({ children }: { children: ReactNode }) {
    return (
      <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
    );
  };
}

describe("useConvertQuote (P9/C-1)", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("unwraps the nested invoice and routes to the created invoice", async () => {
    // The REAL backend shape: the invoice is nested under "invoice".
    vi.mocked(apiClient.api.post).mockResolvedValue({
      message: "Quote converted to invoice",
      invoice: {
        id: "b7f3b1e0-0000-4000-8000-000000000001",
        document_number: "INV-00042",
        document_type: "SALES_INVOICE",
      },
    });

    const { result } = renderHook(() => useConvertQuote("org-1"), {
      wrapper: createWrapper(),
    });

    await act(async () => {
      result.current.mutate("quote-id-1");
    });

    await waitFor(() => {
      expect(push).toHaveBeenCalled();
    });

    // The failing assertion pre-fix: the flat read produced undefined.
    expect(push).toHaveBeenCalledWith(
      "/invoices/b7f3b1e0-0000-4000-8000-000000000001"
    );
  });
});
