/**
 * P9/D-2 + D-3 + D-4: the dashboard tells the truth.
 *
 * The GST F5 chart hardcoded Box 1 (150,000) / Box 2 (25,000) and default
 * output/input tax (15,000 / 2,550) — only Box 8 (Net GST) was real. The
 * metric cards carried static trend claims (+8.2% GST, -2.4% cash,
 * +12.5% revenue MTD, "On track for target") that no data fed. Two CTAs
 * pointed at href="#" while a real GST F5 tab exists at /reports.
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { DashboardClient } from "../dashboard-client";
import * as apiClient from "@/lib/api-client";

vi.mock("@/lib/api-client", () => ({
  api: { get: vi.fn() },
  endpoints: {
    dashboard: (orgId: string) => ({
      metrics: `/api/v1/${orgId}/reports/dashboard/metrics/`,
    }),
  },
}));

vi.mock("@/providers/auth-provider", () => ({
  useAuth: () => ({
    currentOrg: { id: "org-1", name: "Truth Org" },
    user: { full_name: "Founder" },
    isLoading: false,
  }),
}));

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn(), replace: vi.fn(), back: vi.fn() }),
}));

vi.mock("../dashboard-actions", () => ({
  DashboardActions: () => <div data-testid="dashboard-actions" />,
}));

const METRICS = {
  gst_payable: "318.0000",
  gst_payable_display: "SGD 318.00",
  outstanding_receivables: "SGD 5,400.00",
  outstanding_payables: "SGD 0.00",
  revenue_mtd: "SGD 4,000.00",
  revenue_ytd: "SGD 40,000.00",
  cash_on_hand: "SGD 12,000.00",
  gst_threshold_status: "SAFE",
  gst_threshold_utilization: 4,
  gst_threshold_amount: "SGD 39,500.00",
  gst_threshold_limit: "SGD 1,000,000.00",
  compliance_alerts: [
    {
      title: "GST filing due",
      message: "The current period's F5 return is due soon.",
      severity: "WARNING",
      action_required: "File return",
    },
  ],
  invoices_pending: 2,
  invoices_overdue: 1,
  invoices_peppol_pending: 0,
  current_gst_period: {
    start_date: "2026-11-01",
    end_date: "2026-11-30",
    filing_due_date: "2026-12-31",
    days_remaining: 39,
  },
};

function renderDashboard() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <DashboardClient />
    </QueryClientProvider>
  );
}

describe("DashboardClient truth (P9/D-2, D-3, D-4)", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(apiClient.api.get).mockResolvedValue(METRICS);
  });

  it("renders the real metric values", async () => {
    renderDashboard();

    expect(await screen.findByText(/SGD 318.00/i)).toBeInTheDocument();
    expect(screen.getByText(/SGD 4,000.00/i)).toBeInTheDocument();
    expect(screen.getByText(/SGD 40,000.00/i)).toBeInTheDocument();
  });

  it("carries no invented trend claims (P9/D-3)", async () => {
    renderDashboard();
    await screen.findByText(/SGD 318.00/i);

    for (const invented of [
      "+8.2%",
      "-2.4%",
      "+12.5%",
      "On track for target",
      "vs last period",
      "vs last month",
    ]) {
      expect(screen.queryByText(invented)).not.toBeInTheDocument();
    }
  });

  it("carries no invented GST box figures (P9/D-2)", async () => {
    renderDashboard();
    await screen.findByText(/GST F5/i);

    // The hardcoded Box 1/2 labels and default output/input values are gone;
    // only the real Net GST figure renders.
    for (const invented of ["Box 1", "Box 2", "15,000", "2,550", "150,000"]) {
      expect(screen.queryByText(new RegExp(invented, "i"))).not.toBeInTheDocument();
    }
  });

  it("links File F5 and compliance actions to the real reports page (P9/D-4)", async () => {
    renderDashboard();
    await screen.findByText(/SGD 318.00/i);

    const fileF5 = screen.getByRole("link", { name: /file f5/i });
    expect(fileF5).toHaveAttribute("href", "/reports");

    const alertAction = screen.getByRole("link", { name: /file return/i });
    expect(alertAction).toHaveAttribute("href", "/reports");
  });
});


describe("DashboardClient GST truth (P11/H-4, M-7, L-2)", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(apiClient.api.get).mockResolvedValue(METRICS);
  });

  it("renders no double currency prefix (S$ SGD) on the money cards (L-2)", async () => {
    renderDashboard();
    await screen.findByText(/GST Payable/i);

    // The backend's display strings already carry "SGD x.xx" — the S$
    // prefixes produced "S$ SGD 318.00" on every money card.
    expect(document.body.textContent ?? "").not.toMatch(/S\$ SGD/);
    // The truthful display string itself still renders.
    expect(await screen.findByText(/SGD 318\.00/)).toBeInTheDocument();
  });

  it("the F5 chart renders a non-zero Net GST bar from the raw gst_payable (M-7)", async () => {
    renderDashboard();
    await screen.findByText(/GST Payable/i);

    // Toggle the accessible data table — the chart's parsed value shows up
    // as a row amount. parseFloat("SGD 318.00") was NaN, so every real
    // value rendered as 0.
    await userEvent.click(screen.getByRole("button", { name: /show data table/i }));
    expect(await screen.findByText(/S\$ 318/)).toBeInTheDocument();
  });
});
