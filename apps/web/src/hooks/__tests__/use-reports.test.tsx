/**
 * P8/R-7 + R-8: reports hooks — the real financial/aged/GST-returns
 * contracts. The pre-P8 page had zero data wiring (dead Generate buttons)
 * and two dormant hooks pointed at endpoints that do not exist
 * (/gst/f5-compute/, /audit-log/).
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import type { ReactNode } from "react";
import * as apiClient from "@/lib/api-client";
import {
  useFinancialReport,
  useAgedReport,
  useGSTReturns,
  useGenerateGSTReturn,
} from "../use-reports";

vi.mock("@/lib/api-client", () => ({
  api: {
    get: vi.fn(),
    post: vi.fn(),
  },
  endpoints: {
    reports: (orgId: string) => ({
      financial: `/api/v1/${orgId}/reports/financial/`,
      aged: `/api/v1/${orgId}/reports/aged/`,
    }),
    gst: (orgId: string) => ({
      returns: `/api/v1/${orgId}/gst/returns/`,
      returnDetail: (id: string) => `/api/v1/${orgId}/gst/returns/${id}/`,
    }),
  },
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

describe("use-reports (P8/R-7)", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("useFinancialReport calls the financial endpoint with typed params", async () => {
    vi.mocked(apiClient.api.get).mockResolvedValue({
      report_type: "profit_loss",
      data: { sections: { revenue: [], expenses: [] }, revenue_total: "0.0000" },
    });

    const { result } = renderHook(
      () =>
        useFinancialReport("org-1", "profit_loss", {
          start_date: "2024-01-01",
          end_date: "2024-12-31",
        }),
      { wrapper: createWrapper() }
    );

    await waitFor(() => expect(result.current.data).toBeDefined());
    expect(apiClient.api.get).toHaveBeenCalledWith(
      "/api/v1/org-1/reports/financial/?report_type=profit_loss&start_date=2024-01-01&end_date=2024-12-31"
    );
  });

  it("useFinancialReport stays disabled without an org", () => {
    const { result } = renderHook(() => useFinancialReport(null, "profit_loss"), {
      wrapper: createWrapper(),
    });
    expect(result.current.data).toBeUndefined();
    expect(apiClient.api.get).not.toHaveBeenCalled();
  });

  it("useAgedReport calls the aged endpoint with type + as_at", async () => {
    vi.mocked(apiClient.api.get).mockResolvedValue({
      type: "receivables",
      results: [],
      totals: {},
    });

    const { result } = renderHook(
      () => useAgedReport("org-1", "payables", "2024-03-31"),
      { wrapper: createWrapper() }
    );

    await waitFor(() => expect(result.current.data).toBeDefined());
    expect(apiClient.api.get).toHaveBeenCalledWith(
      "/api/v1/org-1/reports/aged/?type=payables&as_at=2024-03-31"
    );
  });

  it("useGSTReturns lists returns for a year", async () => {
    vi.mocked(apiClient.api.get).mockResolvedValue({ results: [], count: 0 });

    const { result } = renderHook(() => useGSTReturns("org-1", 2024), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.data).toBeDefined());
    expect(apiClient.api.get).toHaveBeenCalledWith(
      "/api/v1/org-1/gst/returns/?year=2024"
    );
  });

  it("useGenerateGSTReturn posts to the detail endpoint with force", async () => {
    vi.mocked(apiClient.api.post).mockResolvedValue({
      message: "computed",
      return: { id: "r1", status: "COMPUTED" },
    });

    const { result } = renderHook(() => useGenerateGSTReturn("org-1"), {
      wrapper: createWrapper(),
    });
    result.current.mutate("r1");

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(apiClient.api.post).toHaveBeenCalledWith(
      "/api/v1/org-1/gst/returns/r1/?force=true",
      {}
    );
  });
});
