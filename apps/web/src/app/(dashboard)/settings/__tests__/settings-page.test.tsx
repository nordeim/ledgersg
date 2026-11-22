/**
 * P6/C-5 (settings) — real organisation settings page.
 *
 * RED suite (against the hardcoded page): the settings form renders the
 * REAL organisation (controlled inputs from useOrganisation), saves
 * through the update mutation, and drives the GST registration state.
 */

import { describe, it, expect, vi, afterEach, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { SettingsClient } from "../settings-client";
import * as orgHooks from "@/hooks/use-organisation";

// P7/F-12: hoisted mutable auth state so the no-org case is testable.
const { __testAuth } = vi.hoisted(() => ({
  __testAuth: {
    currentOrg: { id: "org-123", name: "Ledger Demo Pte Ltd" } as
      | { id: string; name: string }
      | null,
    user: {
      id: "user-1",
      email: "demo@ledgersg.sg",
      full_name: "Demo User",
    },
    isLoading: false,
  },
}));

vi.mock("@/providers/auth-provider", () => ({
  useAuth: () => __testAuth,
}));

vi.mock("@/hooks/use-organisation");

const mockMutation = () => ({
  mutate: vi.fn(),
  mutateAsync: vi.fn(),
  isPending: false,
  isError: false,
  error: null,
});

const mockOrg = (overrides: Record<string, unknown> = {}) => ({
  id: "org-123",
  name: "Ledger Demo Pte Ltd",
  legal_name: "Ledger Demo Private Limited",
  uen: "202612345D",
  entity_type: "PRIVATE_LIMITED",
  gst_registered: true,
  gst_reg_number: "M90345678",
  gst_reg_date: "2024-01-01",
  peppol_participant_id: "",
  invoicenow_enabled: false,
  fy_start_month: 1,
  base_currency: "SGD",
  is_active: true,
  address_line_1: "12 Marina Boulevard",
  address_line_2: "",
  city: "Singapore",
  postal_code: "018982",
  country: "SG",
  contact_email: "admin@ledgersg.sg",
  contact_phone: "",
  created_at: "2026-01-01T00:00:00Z",
  updated_at: "2026-01-01T00:00:00Z",
  ...overrides,
});

function renderPage() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <SettingsClient />
    </QueryClientProvider>
  );
}

describe("SettingsClient (real data)", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(orgHooks.useUpdateOrganisation).mockReturnValue(
      mockMutation() as unknown as ReturnType<typeof orgHooks.useUpdateOrganisation>
    );
    vi.mocked(orgHooks.useGstRegistration).mockReturnValue(
      mockMutation() as unknown as ReturnType<typeof orgHooks.useGstRegistration>
    );
    vi.mocked(orgHooks.useGstDeregistration).mockReturnValue(
      mockMutation() as unknown as ReturnType<typeof orgHooks.useGstDeregistration>
    );
  });

  it("renders the real organisation fields from useOrganisation", async () => {
    vi.mocked(orgHooks.useOrganisation).mockReturnValue({
      data: mockOrg(),
      isLoading: false,
      isError: false,
      error: null,
    } as unknown as ReturnType<typeof orgHooks.useOrganisation>);

    renderPage();

    expect(
      await screen.findByDisplayValue("Ledger Demo Pte Ltd")
    ).toBeInTheDocument();
    expect(
      screen.getByDisplayValue("Ledger Demo Private Limited")
    ).toBeInTheDocument();
    expect(screen.getByDisplayValue("202612345D")).toBeInTheDocument();
    expect(screen.getByDisplayValue("12 Marina Boulevard")).toBeInTheDocument();
    expect(screen.getByDisplayValue("018982")).toBeInTheDocument();
    // the mock defaults must be gone
    expect(screen.queryByDisplayValue("Demo Company Pte Ltd")).not.toBeInTheDocument();
    expect(screen.queryByDisplayValue("201912345A")).not.toBeInTheDocument();
  });

  it("saves edits through the update mutation", async () => {
    vi.mocked(orgHooks.useOrganisation).mockReturnValue({
      data: mockOrg(),
      isLoading: false,
      isError: false,
      error: null,
    } as unknown as ReturnType<typeof orgHooks.useOrganisation>);

    const update = mockMutation();
    vi.mocked(orgHooks.useUpdateOrganisation).mockReturnValue(
      update as unknown as ReturnType<typeof orgHooks.useUpdateOrganisation>
    );

    renderPage();

    const nameInput = await screen.findByDisplayValue("Ledger Demo Pte Ltd");
    await userEvent.clear(nameInput);
    await userEvent.type(nameInput, "Renamed Demo Pte Ltd");

    await userEvent.click(screen.getByRole("button", { name: /save changes/i }));

    await waitFor(() => expect(update.mutate).toHaveBeenCalled());
    const payload = update.mutate.mock.calls[0][0];
    expect(payload.name).toBe("Renamed Demo Pte Ltd");
  });

  it("shows the GST registration state and the deregister action", async () => {
    vi.mocked(orgHooks.useOrganisation).mockReturnValue({
      data: mockOrg(),
      isLoading: false,
      isError: false,
      error: null,
    } as unknown as ReturnType<typeof orgHooks.useOrganisation>);

    renderPage();

    expect(await screen.findByDisplayValue("M90345678")).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: /deregister/i })
    ).toBeInTheDocument();
  });

  it("offers registration when the org is not GST-registered", async () => {
    vi.mocked(orgHooks.useOrganisation).mockReturnValue({
      data: mockOrg({
        gst_registered: false,
        gst_reg_number: "",
        gst_reg_date: null,
      }),
      isLoading: false,
      isError: false,
      error: null,
    } as unknown as ReturnType<typeof orgHooks.useOrganisation>);

    renderPage();

    expect(
      await screen.findByRole("button", { name: /register for gst/i })
    ).toBeInTheDocument();
  });

  it("shows the loading state while the organisation is fetching", () => {
    vi.mocked(orgHooks.useOrganisation).mockReturnValue({
      data: undefined,
      isLoading: true,
      isError: false,
      error: null,
    } as unknown as ReturnType<typeof orgHooks.useOrganisation>);

    renderPage();

    expect(screen.getByText(/loading/i)).toBeInTheDocument();
  });

  it("shows the error state when the organisation fails to load", async () => {
    vi.mocked(orgHooks.useOrganisation).mockReturnValue({
      data: undefined,
      isLoading: false,
      isError: true,
      error: new Error("Network error"),
    } as unknown as ReturnType<typeof orgHooks.useOrganisation>);

    renderPage();

    expect(await screen.findByText(/failed to load/i)).toBeInTheDocument();
  });
});

describe("SettingsClient — no-organisation state (P7/F-12)", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    __testAuth.currentOrg = null;
    __testAuth.isLoading = false;
  });

  afterEach(() => {
    __testAuth.currentOrg = { id: "org-123", name: "Ledger Demo Pte Ltd" };
  });

  it("renders the no-org state for an org-less user (never 'Failed to load settings')", () => {
    // Disabled query: isLoading=false, isError=false — the pre-P7
    // `isError || !org` branch rendered a load FAILURE for an org-less user.
    vi.mocked(orgHooks.useOrganisation).mockReturnValue({
      data: undefined,
      isLoading: false,
      isError: false,
      error: null,
    } as unknown as ReturnType<typeof orgHooks.useOrganisation>);
    vi.mocked(orgHooks.useUpdateOrganisation).mockReturnValue(
      mockMutation() as unknown as ReturnType<typeof orgHooks.useUpdateOrganisation>
    );
    vi.mocked(orgHooks.useGstRegistration).mockReturnValue(
      mockMutation() as unknown as ReturnType<typeof orgHooks.useGstRegistration>
    );
    vi.mocked(orgHooks.useGstDeregistration).mockReturnValue(
      mockMutation() as unknown as ReturnType<typeof orgHooks.useGstDeregistration>
    );

    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });
    render(
      <QueryClientProvider client={queryClient}>
        <SettingsClient />
      </QueryClientProvider>
    );

    expect(screen.getByText(/no organisation selected/i)).toBeInTheDocument();
    expect(screen.queryByText(/failed to load settings/i)).not.toBeInTheDocument();
  });
});
