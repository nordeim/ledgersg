/**
 * P8/R-7: the reports page renders real data — trial balance rows, P&L
 * lines, GST F5 lifecycle actions and the aged buckets. The pre-P8 page
 * was a static card grid with dead Generate buttons (zero data wiring).
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, cleanup } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ReportsClient } from "../reports-client";
import * as reportHooks from "@/hooks/use-reports";
import * as authModule from "@/providers/auth-provider";

vi.mock("@/providers/auth-provider", () => ({
  useAuth: vi.fn(),
}));

const reviewMutateMock = vi.fn();
const amendMutateMock = vi.fn();
const createPeriodsMutateMock = vi.fn();

vi.mock("@/hooks/use-reports", () => ({
  useFinancialReport: vi.fn(),
  useAgedReport: vi.fn(),
  useGSTReturns: vi.fn(),
  useGenerateGSTReturn: vi.fn(() => ({ mutate: vi.fn(), isPending: false })),
  useFileGSTReturn: vi.fn(() => ({ mutate: vi.fn(), isPending: false })),
  useGSTReturn: vi.fn(),
  useReviewGSTReturn: vi.fn(() => ({ mutate: reviewMutateMock, isPending: false })),
  useAmendGSTReturn: vi.fn(() => ({ mutate: amendMutateMock, isPending: false })),
  useCreateGSTReturnPeriods: vi.fn(() => ({
    mutate: createPeriodsMutateMock,
    isPending: false,
  })),
  useGSTDeadlines: vi.fn(),
}));

/* eslint-disable @typescript-eslint/no-explicit-any -- test mocks */
function mockQuery(overrides: Record<string, unknown>): any {
  return {
    data: undefined,
    isLoading: false,
    isError: false,
    error: null,
    ...overrides,
  };
}

function renderPage() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  render(
    <QueryClientProvider client={queryClient}>
      <ReportsClient />
    </QueryClientProvider>
  );
}

const ORG = { id: "org-1", name: "Reports Org", gst_registered: true };

describe("ReportsClient (P8/R-7 — real data)", () => {
  beforeEach(() => {
    vi.mocked(reportHooks.useGSTDeadlines).mockReturnValue(
      mockQuery({ data: { results: [], count: 0 } })
    );
    vi.clearAllMocks();
    vi.mocked(authModule.useAuth).mockReturnValue({
      currentOrg: ORG,
      isLoading: false,
    } as unknown as ReturnType<typeof authModule.useAuth>);
  });

  afterEach(() => cleanup());

  it("renders the trial balance rows and the balanced badge", async () => {
    vi.mocked(reportHooks.useFinancialReport).mockImplementation(
      ((_orgId: string, type: string) => {
        if (type === "trial_balance") {
          return mockQuery({
            data: {
              report_type: "trial_balance",
              data: {
                lines: [
                  {
                    account_id: "a1",
                    account_code: "1010",
                    account_name: "Cash",
                    account_type: "ASSET_CURRENT",
                    total_debits: "139.0000",
                    total_credits: "0.0000",
                    balance: "139.0000",
                  },
                ],
                totals: {
                  total_debits: "139.0000",
                  total_credits: "139.0000",
                  balanced: true,
                },
              },
            },
          });
        }
        return mockQuery({ data: undefined });
      }) as unknown as typeof reportHooks.useFinancialReport
    );
    vi.mocked(reportHooks.useAgedReport).mockReturnValue(
      mockQuery({ data: { type: "receivables", as_at: "2024-03-31", results: [], totals: {} } })
    );
    vi.mocked(reportHooks.useGSTReturns).mockReturnValue(
      mockQuery({ data: { results: [], count: 0 } })
    );

    renderPage();

    expect(await screen.findByText("Cash")).toBeInTheDocument();
    expect(screen.getByText("Balanced")).toBeInTheDocument();
    expect(screen.getAllByText("139.00").length).toBeGreaterThanOrEqual(2);  // row + totals
  });

  it("renders the P&L per-account lines and net profit", async () => {
    vi.mocked(reportHooks.useFinancialReport).mockImplementation(
      ((_orgId: string, type: string) => {
        if (type === "profit_loss") {
          return mockQuery({
            data: {
              report_type: "profit_loss",
              data: {
                sections: {
                  revenue: [
                    { account_code: "4000", account_name: "Sales", amount: "109.0000" },
                  ],
                  expenses: [
                    { account_code: "6100", account_name: "Rent", amount: "30.0000" },
                  ],
                },
                revenue_total: "109.0000",
                expense_total: "30.0000",
                net_profit: "79.0000",
              },
            },
          });
        }
        return mockQuery({ data: undefined });
      }) as unknown as typeof reportHooks.useFinancialReport
    );
    vi.mocked(reportHooks.useAgedReport).mockReturnValue(mockQuery({ data: undefined }));
    vi.mocked(reportHooks.useGSTReturns).mockReturnValue(
      mockQuery({ data: { results: [], count: 0 } })
    );

    renderPage();
    await userEvent.click(screen.getByRole("tab", { name: /profit & loss/i }));

    expect(await screen.findByText("Sales")).toBeInTheDocument();
    expect(screen.getByText("Rent")).toBeInTheDocument();
    expect(screen.getByText("79.00")).toBeInTheDocument();
  });

  it("renders the GST F5 list with compute + file actions", async () => {
    vi.mocked(reportHooks.useFinancialReport).mockReturnValue(mockQuery({ data: undefined }));
    vi.mocked(reportHooks.useAgedReport).mockReturnValue(mockQuery({ data: undefined }));
    vi.mocked(reportHooks.useGSTReturns).mockReturnValue(
      mockQuery({
        data: {
          results: [
            {
              id: "r1",
              return_type: "F5",
              period_start: "2024-01-01",
              period_end: "2024-03-31",
              filing_due_date: "2024-04-30",
              status: "DRAFT",
              days_until_due: 10,
              net_gst: "123.4500",
            },
          ],
          count: 1,
        },
      })
    );

    renderPage();
    await userEvent.click(screen.getByRole("tab", { name: /gst f5/i }));

    expect(await screen.findByText(/2024-01-01/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /compute/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /^file$/i })).toBeInTheDocument();
  });

  it("shows the no-org state, never a fake failure", () => {
    vi.mocked(authModule.useAuth).mockReturnValue({
      currentOrg: null,
      isLoading: false,
    } as unknown as ReturnType<typeof authModule.useAuth>);

    renderPage();
    expect(screen.getByText(/no organisation selected/i)).toBeInTheDocument();
    expect(screen.queryByText(/failed to load/i)).not.toBeInTheDocument();
  });

  it("renders the aged buckets per contact", async () => {
    vi.mocked(reportHooks.useFinancialReport).mockReturnValue(mockQuery({ data: undefined }));
    vi.mocked(reportHooks.useGSTReturns).mockReturnValue(
      mockQuery({ data: { results: [], count: 0 } })
    );
    vi.mocked(reportHooks.useAgedReport).mockImplementation(
      ((_orgId: string, type: string) =>
        mockQuery({
          data: {
            type,
            as_at: "2024-03-31",
            results:
              type === "receivables"
                ? [
                    {
                      contact_id: "c1",
                      contact_name: "Acme Pte Ltd",
                      document_count: 2,
                      outstanding_total: "218.0000",
                      current: "109.0000",
                      d1_30: "109.0000",
                      d31_60: "0.0000",
                      d61_90: "0.0000",
                      d90_plus: "0.0000",
                    },
                  ]
                : [],
            totals: {
              outstanding_total: "218.0000",
              document_count: 2,
              current: "109.0000",
              d1_30: "109.0000",
              d31_60: "0.0000",
              d61_90: "0.0000",
              d90_plus: "0.0000",
            },
          },
        })) as unknown as typeof reportHooks.useAgedReport
    );

    renderPage();
    await userEvent.click(screen.getByRole("tab", { name: /aged/i }));

    expect(await screen.findByText("Acme Pte Ltd")).toBeInTheDocument();
    expect(screen.getAllByText("109.00").length).toBeGreaterThanOrEqual(2);
  });
});

describe("ReportsClient GST F5 — the whole truth (P10/H-3)", () => {
  const computedRow = {
    id: "r-computed",
    return_type: "F5",
    period_start: "2024-01-01",
    period_end: "2024-01-31",
    filing_due_date: "2024-02-29",
    status: "COMPUTED",
    days_until_due: 12,
    net_gst: "90.0000",
  };
  const filedRow = {
    ...computedRow,
    id: "r-filed",
    status: "FILED",
  };

  function mockGst(rows: unknown[]) {
    vi.mocked(reportHooks.useFinancialReport).mockReturnValue(mockQuery({ data: undefined }));
    vi.mocked(reportHooks.useAgedReport).mockReturnValue(mockQuery({ data: undefined }));
    vi.mocked(reportHooks.useGSTReturns).mockReturnValue(
      mockQuery({ data: { results: rows, count: rows.length } })
    );
    vi.mocked(reportHooks.useGSTDeadlines).mockReturnValue(
      mockQuery({ data: { results: [computedRow], count: 1 } })
    );
  }

  it("renders the next filing deadline banner from the deadlines endpoint", async () => {
    mockGst([]);
    renderPage();
    await userEvent.click(screen.getByRole("tab", { name: /gst f5/i }));

    expect(await screen.findByText(/next filing due/i)).toBeInTheDocument();
    expect(screen.getByText(/2024-02-29/)).toBeInTheDocument();
  });

  it("shows the computed F5 boxes before File (no more blind filing)", async () => {
    mockGst([computedRow]);
    vi.mocked(reportHooks.useGSTReturn).mockReturnValue(
      mockQuery({
        data: {
          id: "r-computed",
          return_type: "F5",
          period_start: "2024-01-01",
          period_end: "2024-01-31",
          filing_due_date: "2024-02-29",
          status: "COMPUTED",
          notes: "",
          boxes: { box1: "1000.0000", box6: "90.0000", box8: "90.0000" },
          computed_at: "2026-11-22T00:00:00Z",
          filed_at: null,
        },
      })
    );

    renderPage();
    await userEvent.click(screen.getByRole("tab", { name: /gst f5/i }));
    await userEvent.click(
      (await screen.findAllByRole("button", { name: /view boxes/i }))[0]
    );

    // The IRAS box values render — the user can inspect before filing.
    expect(await screen.findByText(/^Box 1 —/)).toBeInTheDocument();
    expect(screen.getByText("1000.0000")).toBeInTheDocument();
    expect(screen.getAllByText("90.0000").length).toBeGreaterThanOrEqual(2);
  });

  it("offers Review on a COMPUTED return (the previously-unrouted edge)", async () => {
    mockGst([computedRow]);
    renderPage();
    await userEvent.click(screen.getByRole("tab", { name: /gst f5/i }));

    expect(await screen.findByRole("button", { name: /review/i })).toBeInTheDocument();
  });

  it("offers Amend with a required reason on a FILED return", async () => {
    mockGst([filedRow]);
    renderPage();
    await userEvent.click(screen.getByRole("tab", { name: /gst f5/i }));

    await userEvent.click(await screen.findByRole("button", { name: /amend/i }));

    // The reason dialog gates the amendment (the backend requires it).
    const reason = await screen.findByLabelText(/reason/i);
    await userEvent.type(reason, "Box 1 included an exempt supply");
    await userEvent.click(screen.getByRole("button", { name: /submit amendment/i }));

    expect(amendMutateMock).toHaveBeenCalledWith(
      { returnId: "r-filed", reason: "Box 1 included an exempt supply" },
      expect.anything()
    );
  });

  it("creates return periods from the UI (the empty state's dead text replaced)", async () => {
    mockGst([]);
    renderPage();
    await userEvent.click(screen.getByRole("tab", { name: /gst f5/i }));

    expect(
      await screen.findByText(/no gst return periods/i)
    ).toBeInTheDocument();
    await userEvent.click(
      screen.getByRole("button", { name: /create return periods/i })
    );

    const start = await screen.findByLabelText(/period start/i);
    await userEvent.type(start, "2024-01-01");
    await userEvent.click(screen.getByRole("button", { name: /create periods/i }));

    expect(
      screen.queryByText(/periods are created from the api/i)
    ).toBeNull();
  });
});
