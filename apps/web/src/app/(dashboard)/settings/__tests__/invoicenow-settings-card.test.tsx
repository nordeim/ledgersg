/**
 * P10/M-10: the InvoiceNow / Peppol settings card. GET/PATCH
 * /peppol/settings/ is backend-real (member-readable GET, manager-gated
 * typed PATCH) with zero frontend consumers — "Send via InvoiceNow" 400s
 * with "Configure an access point (Peppol settings)…" pointing users at a
 * settings surface that did not exist.
 */

import { beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { InvoiceNowSettingsCard } from "../components/invoicenow-settings-card";
import * as peppolHooks from "@/hooks/use-peppol";

const { __testAuth, __patchMock } = vi.hoisted(() => ({
  __testAuth: {
    hasPermission: vi.fn(() => true),
  },
  __patchMock: vi.fn(),
}));

vi.mock("@/providers/auth-provider", () => ({
  useAuth: () => __testAuth,
}));

const patchMock = __patchMock;

vi.mock("@/hooks/use-peppol", () => ({
  usePeppolSettings: vi.fn(),
  useUpdatePeppolSettings: vi.fn().mockReturnValue({
    mutate: __patchMock,
    isPending: false,
  }),
}));

const SETTINGS = {
  enabled: true,
  participant_id: "0209-201912345A-1234",
  is_configured: false,
  access_point_provider: "Storecove",
  auto_transmit: true,
  retry_attempts: 3,
  status: "not_configured" as const,
};

function renderCard() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <InvoiceNowSettingsCard orgId="org-1" />
    </QueryClientProvider>
  );
}

describe("InvoiceNowSettingsCard (P10/M-10)", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    __testAuth.hasPermission.mockReturnValue(true);
    vi.mocked(peppolHooks.usePeppolSettings).mockReturnValue({
      data: SETTINGS,
      isLoading: false,
      error: null,
    } as unknown as ReturnType<typeof peppolHooks.usePeppolSettings>);
  });

  it("renders the settings from GET with the truthful status badge", () => {
    renderCard();

    expect(
      (screen.getByLabelText(/enable invoicenow/i) as HTMLInputElement).checked
    ).toBe(true);
    expect(screen.getByLabelText(/peppol participant id/i)).toHaveValue(
      "0209-201912345A-1234"
    );
    expect(screen.getByLabelText(/access point provider/i)).toHaveValue(
      "Storecove"
    );
    expect(
      (screen.getByLabelText(/auto-transmit/i) as HTMLInputElement).checked
    ).toBe(true);
    const retries = screen.getByLabelText(/retry attempts/i) as HTMLInputElement;
    expect(retries).toHaveValue(3);
    // The is_configured truth: the org is enabled but not configured.
    expect(screen.getByText(/not configured/i)).toBeInTheDocument();
  });

  it("PATCHes the typed payload on save", async () => {
    const user = userEvent.setup();
    renderCard();

    const retries = screen.getByLabelText(/retry attempts/i);
    await user.clear(retries);
    await user.type(retries, "5");
    await user.click(screen.getByRole("button", { name: /save/i }));

    await waitFor(() => {
      expect(patchMock).toHaveBeenCalledWith(
        expect.objectContaining({
          enabled: true,
          participant_id: "0209-201912345A-1234",
          access_point_provider: "Storecove",
          auto_transmit: true,
          retry_attempts: 5,
        })
      );
    });
  });

  it("shows a read-only view for non-managers", () => {
    __testAuth.hasPermission.mockReturnValue(false);
    renderCard();

    expect(screen.getByLabelText(/peppol participant id/i)).toBeDisabled();
    expect(screen.getByLabelText(/access point provider/i)).toBeDisabled();
    expect(screen.getByLabelText(/retry attempts/i)).toBeDisabled();
    expect(
      screen.queryByRole("button", { name: /save/i })
    ).not.toBeInTheDocument();
  });

  it("renders the loading state", () => {
    vi.mocked(peppolHooks.usePeppolSettings).mockReturnValue({
      data: undefined,
      isLoading: true,
      error: null,
    } as unknown as ReturnType<typeof peppolHooks.usePeppolSettings>);
    renderCard();

    expect(screen.getByTestId("invoicenow-card-loading")).toBeInTheDocument();
  });
});
