/**
 * P10/M-8: the Settings "Fiscal year & periods" card. The backend has
 * years/periods list + close endpoints (plus the new open endpoint) with
 * ZERO frontend consumers — the invoice-approval error "Please open the
 * fiscal period or change the invoice date" pointed at an impossible
 * action. This card makes the control act possible.
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { FiscalCard } from "../components/fiscal-card";
import * as fiscalHooks from "@/hooks/use-fiscal";

const { __testAuth, __mocks } = vi.hoisted(() => ({
  __testAuth: {
    hasPermission: vi.fn(() => true),
  },
  __mocks: {
    open: vi.fn(),
    close: vi.fn(),
    closeYear: vi.fn(),
  },
}));

vi.mock("@/providers/auth-provider", () => ({
  useAuth: () => __testAuth,
}));

vi.mock("@/hooks/use-fiscal", () => ({
  useFiscalYears: vi.fn(),
  useFiscalPeriods: vi.fn(),
  useOpenFiscalPeriod: vi.fn().mockReturnValue({
    mutate: __mocks.open,
    isPending: false,
  }),
  useCloseFiscalPeriod: vi.fn().mockReturnValue({
    mutate: __mocks.close,
    isPending: false,
  }),
  useCloseFiscalYear: vi.fn().mockReturnValue({
    mutate: __mocks.closeYear,
    isPending: false,
  }),
}));

const { open: openMock, close: closeMock } = __mocks;

const YEAR = {
  id: "11111111-1111-4111-8111-111111111111",
  label: "FY2026",
  start_date: "2026-01-01",
  end_date: "2026-12-31",
  is_closed: false,
  closed_at: null,
  created_at: "2026-01-01T00:00:00Z",
};

const PERIODS = [
  {
    id: "22222222-2222-4222-8222-222222222221",
    name: "Jan 2026",
    start_date: "2026-01-01",
    end_date: "2026-01-31",
    status: "OPEN",
    fiscal_year_id: YEAR.id,
  },
  {
    id: "22222222-2222-4222-8222-222222222222",
    name: "Dec 2025",
    start_date: "2025-12-01",
    end_date: "2025-12-31",
    status: "CLOSED",
    fiscal_year_id: YEAR.id,
  },
];

function renderCard() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <FiscalCard orgId="org-1" />
    </QueryClientProvider>
  );
}

describe("FiscalCard (P10/M-8)", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    __testAuth.hasPermission.mockReturnValue(true);
    vi.mocked(fiscalHooks.useFiscalYears).mockReturnValue({
      // P21/BE-M6: the unified list envelope.
      data: { results: [YEAR], count: 1 },
      isLoading: false,
      error: null,
    } as unknown as ReturnType<typeof fiscalHooks.useFiscalYears>);
    vi.mocked(fiscalHooks.useFiscalPeriods).mockReturnValue({
      data: { results: PERIODS, count: 2 },
      isLoading: false,
      error: null,
    } as unknown as ReturnType<typeof fiscalHooks.useFiscalPeriods>);
  });

  it("renders years with their periods and truthful status badges", () => {
    renderCard();

    expect(screen.getByText("FY2026")).toBeInTheDocument();
    expect(screen.getByText("Jan 2026")).toBeInTheDocument();
    expect(screen.getByText("Dec 2025")).toBeInTheDocument();
    // The truthful status badges, scoped per period row.
    const janRow = screen.getByTestId(`fiscal-period-${PERIODS[0].id}`);
    const decRow = screen.getByTestId(`fiscal-period-${PERIODS[1].id}`);
    expect(within(janRow).getByText("Open")).toBeInTheDocument();
    expect(within(decRow).getByText("Closed")).toBeInTheDocument();
  });

  it("offers Close on an open period and Open on a closed one", () => {
    renderCard();

    expect(
      screen.getByRole("button", { name: /close jan 2026/i })
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: /open dec 2025/i })
    ).toBeInTheDocument();
  });

  it("the Open button fires the open mutation for that period", async () => {
    const user = userEvent.setup();
    renderCard();

    await user.click(screen.getByRole("button", { name: /open dec 2025/i }));

    expect(openMock).toHaveBeenCalledTimes(1);
    expect(closeMock).not.toHaveBeenCalled();
  });

  it("the Close button fires the close mutation for that period", async () => {
    const user = userEvent.setup();
    renderCard();

    await user.click(screen.getByRole("button", { name: /close jan 2026/i }));

    expect(closeMock).toHaveBeenCalledTimes(1);
    expect(openMock).not.toHaveBeenCalled();
  });

  it("hides the control buttons from non-managers (read-only view)", () => {
    __testAuth.hasPermission.mockReturnValue(false);
    renderCard();

    // The state is still visible — the control acts are not.
    expect(screen.getByText("Jan 2026")).toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: /close jan 2026/i })
    ).not.toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: /open dec 2025/i })
    ).not.toBeInTheDocument();
  });

  it("surfaces the loading state", () => {
    vi.mocked(fiscalHooks.useFiscalYears).mockReturnValue({
      data: undefined,
      isLoading: true,
      error: null,
    } as unknown as ReturnType<typeof fiscalHooks.useFiscalYears>);
    renderCard();

    expect(screen.getByTestId("fiscal-card-loading")).toBeInTheDocument();
  });
});
