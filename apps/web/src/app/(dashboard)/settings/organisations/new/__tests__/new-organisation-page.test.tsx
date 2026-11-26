/**
 * P9/O-1: organisation creation — the onboarding dead end closed.
 *
 * Registration creates a user with NO organisation, and the dashboard's
 * only CTA pointed at /settings/organisations/new — a route that did not
 * exist — while POST /api/v1/organisations/ had zero frontend consumers.
 * A self-registered user hit a 404 and could not use the product. This
 * page is the route the dashboard already targets.
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor, act } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import type { ReactNode } from "react";
import * as apiClient from "@/lib/api-client";
import { toast } from "@/hooks/use-toast";

function withProviders(ui: ReactNode) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>
  );
}

vi.mock("@/lib/api-client", () => ({
  api: {
    post: vi.fn(),
  },
  endpoints: {
    organisations: {
      list: "/api/v1/auth/organisations/",
      create: "/api/v1/organisations/",
    },
  },
}));

const push = vi.fn();
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push, replace: vi.fn(), back: vi.fn() }),
}));

const refreshOrganisations = vi.fn().mockResolvedValue(undefined);
const selectOrgById = vi.fn();

vi.mock("@/providers/auth-provider", () => ({
  useAuth: () => ({
    user: { id: "u-1", email: "founder@example.com", full_name: "Founder" },
    currentOrg: null,
    organisations: [],
    isLoading: false,
    refreshOrganisations,
    switchOrg: vi.fn(),
    selectOrgById,
  }),
}));

vi.mock("@/hooks/use-toast", () => ({
  toast: vi.fn(),
}));

import { NewOrganisationClient } from "../new-organisation-client";

describe("NewOrganisationClient (P9/O-1)", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders the form fields", () => {
    withProviders(<NewOrganisationClient />);

    expect(screen.getByLabelText(/organisation name/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/legal name/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/uen/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /create organisation/i })).toBeInTheDocument();
  });

  it("submits the create payload to POST /api/v1/organisations/", async () => {
    const user = userEvent.setup();
    vi.mocked(apiClient.api.post).mockResolvedValueOnce({
      id: "org-new-1",
      name: "Mama Shop Pte Ltd",
      gst_registered: false,
    });

    withProviders(<NewOrganisationClient />);

    await user.type(screen.getByLabelText(/organisation name/i), "Mama Shop Pte Ltd");
    await user.type(screen.getByLabelText(/uen/i), "53312345A");
    await user.click(screen.getByRole("button", { name: /create organisation/i }));

    await waitFor(() => {
      expect(apiClient.api.post).toHaveBeenCalledWith("/api/v1/organisations/", {
        name: "Mama Shop Pte Ltd",
        legal_name: "Mama Shop Pte Ltd",
        uen: "53312345A",
        entity_type: "PRIVATE_LIMITED",
        gst_registered: false,
        gst_reg_number: "",
        base_currency: "SGD",
        fy_start_month: 1,
      });
    });
  });

  it("requires a GST registration number when GST-registered is on", async () => {
    const user = userEvent.setup();
    withProviders(<NewOrganisationClient />);

    await user.type(screen.getByLabelText(/organisation name/i), "GST Shop");
    await user.click(screen.getByLabelText(/gst-registered/i));

    await user.click(screen.getByRole("button", { name: /create organisation/i }));

    // Client mirrors the backend's validate(): no number, no request.
    expect(apiClient.api.post).not.toHaveBeenCalled();
    expect(screen.getByText(/gst registration number is required/i)).toBeInTheDocument();
  });

  it("refreshes the org list, switches to the new org, and navigates home", async () => {
    const user = userEvent.setup();
    vi.mocked(apiClient.api.post).mockResolvedValueOnce({
      id: "org-new-2",
      name: "Fresh Books",
      gst_registered: false,
    });

    withProviders(<NewOrganisationClient />);

    await user.type(screen.getByLabelText(/organisation name/i), "Fresh Books");
    await user.click(screen.getByRole("button", { name: /create organisation/i }));

    await waitFor(() => {
      expect(refreshOrganisations).toHaveBeenCalled();
    });
    await waitFor(() => {
      expect(selectOrgById).toHaveBeenCalledWith("org-new-2");
      expect(push).toHaveBeenCalledWith("/dashboard");
    });
    expect(toast).toHaveBeenCalledWith(
      expect.objectContaining({ variant: "success" })
    );
  });

  it("surfaces the backend error without navigating", async () => {
    const user = userEvent.setup();
    vi.mocked(apiClient.api.post).mockRejectedValueOnce(
      new Error("Organisation with this UEN already exists")
    );

    withProviders(<NewOrganisationClient />);

    await user.type(screen.getByLabelText(/organisation name/i), "Dup UEN Ltd");
    await user.click(screen.getByRole("button", { name: /create organisation/i }));

    await waitFor(() => {
      expect(toast).toHaveBeenCalledWith(
        expect.objectContaining({ variant: "error" })
      );
    });
    expect(refreshOrganisations).not.toHaveBeenCalled();
    expect(push).not.toHaveBeenCalled();
    await act(async () => {});
  });
});
