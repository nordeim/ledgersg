/**
 * Tax Code Hooks Tests (TDD — P3/D-3)
 *
 * Tests validate:
 * - useTaxCodes fetches the rate rows in force on the document date
 *   (?effective_on= query param — the P2 backend contract)
 * - rate overrides from the server drive the client-side preview
 * - graceful fallback: no org / API error -> undefined data (callers fall
 *   back to the static TAX_CODES list; the backend-less e2e stays green)
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, waitFor } from "@/__tests__/utils";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import React from "react";
import { useTaxCodes, FALLBACK_TAX_CODES } from "../use-tax-codes";
import * as apiClient from "@/lib/api-client";

const mockedGet = vi.mocked(apiClient.api.get);

vi.mock("@/lib/api-client", () => ({
  api: {
    get: vi.fn(),
    post: vi.fn(),
    patch: vi.fn(),
    delete: vi.fn(),
  },
  endpoints: {
    gst: (orgId: string) => ({
      taxCodes: `/api/v1/${orgId}/gst/tax-codes/`,
    }),
  },
}));

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  const Wrapper = ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );
  return Wrapper;
}

describe("useTaxCodes", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("fetches tax codes effective on the given date", async () => {
    mockedGet.mockResolvedValueOnce({
      results: [
        { id: "sr-row", code: "SR", name: "Standard-Rated Supply", rate: "0.0800" },
      ],
      count: 1,
    });

    const { result } = renderHook(
      () => useTaxCodes("org-1", "2023-06-01"),
      { wrapper: createWrapper() }
    );

    await waitFor(() => expect(result.current.data).toBeDefined());

    expect(mockedGet).toHaveBeenCalledWith(
      "/api/v1/org-1/gst/tax-codes/?effective_on=2023-06-01"
    );
    expect(result.current.data?.[0]).toMatchObject({
      code: "SR",
      rate: "0.0800",
    });
  });

  it("omits effective_on when no date is given (today's rows)", async () => {
    mockedGet.mockResolvedValueOnce({ results: [], count: 0 });

    renderHook(() => useTaxCodes("org-1"), { wrapper: createWrapper() });

    await waitFor(() => expect(mockedGet).toHaveBeenCalled());
    expect(mockedGet).toHaveBeenCalledWith("/api/v1/org-1/gst/tax-codes/");
  });

  it("is disabled without an org id (no fetch)", async () => {
    renderHook(() => useTaxCodes(null), { wrapper: createWrapper() });

    await new Promise((r) => setTimeout(r, 20));
    expect(mockedGet).not.toHaveBeenCalled();
  });

  it("surfaces errors as undefined data so callers can fall back statically", async () => {
    mockedGet.mockRejectedValueOnce(new Error("backend down"));

    const { result } = renderHook(
      () => useTaxCodes("org-1", "2023-06-01"),
      { wrapper: createWrapper() }
    );

    await waitFor(() => expect(result.current.isError).toBe(true));
    expect(result.current.data).toBeUndefined();
  });
});

describe("FALLBACK_TAX_CODES", () => {
  it("mirrors the static schema list (backend-less default)", () => {
    const codes = FALLBACK_TAX_CODES.map((tc) => tc.code).sort();
    expect(codes).toEqual(["BL", "ES", "OS", "RS", "SR", "TX", "ZR"]);
    const sr = FALLBACK_TAX_CODES.find((tc) => tc.code === "SR");
    expect(sr?.rate).toBe("0.09");
  });
});
