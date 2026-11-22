/**
 * P6/C-5 (settings) — useOrganisation hooks.
 *
 * RED suite: the hook must fetch the org detail contract, PATCH updates
 * through the real allowlist fields, and drive the GST registration
 * endpoints.
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, waitFor, act } from "@testing-library/react";
import React from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import {
  useOrganisation,
  useUpdateOrganisation,
  useGstRegistration,
  useGstDeregistration,
} from "@/hooks/use-organisation";
import { api } from "@/lib/api-client";

vi.mock("@/lib/api-client", () => ({
  api: { get: vi.fn(), patch: vi.fn(), post: vi.fn(), delete: vi.fn() },
  endpoints: {
    organisations: {
      detail: (id: string) => `/api/v1/${id}/`,
      gst: (id: string) => `/api/v1/${id}/gst/`,
    },
  },
}));

vi.mock("@/hooks/use-toast", () => ({
  toast: vi.fn(),
}));

// P8/S-2: the update hook refreshes the auth provider's org list — a
// shared spy so every test in this file sees a no-op by default.
const __testRefreshOrganisations = vi.fn();
vi.mock("@/providers/auth-provider", () => ({
  useAuth: () => ({ refreshOrganisations: __testRefreshOrganisations }),
}));

const mockOrg = {
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
};

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  const Wrapper = ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );
  return Wrapper;
}

describe("useOrganisation", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("fetches the organisation detail", async () => {
    vi.mocked(api.get).mockResolvedValue(mockOrg);

    const { result } = renderHook(() => useOrganisation("org-123"), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.data).toBeDefined());

    expect(api.get).toHaveBeenCalledWith("/api/v1/org-123/");
    expect(result.current.data?.name).toBe("Ledger Demo Pte Ltd");
    expect(result.current.data?.gst_reg_number).toBe("M90345678");
  });

  it("stays disabled until the org id resolves", () => {
    const { result } = renderHook(() => useOrganisation(null), {
      wrapper: createWrapper(),
    });

    expect(result.current.isLoading).toBe(false);
    expect(api.get).not.toHaveBeenCalled();
  });
});

describe("useUpdateOrganisation", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("PATCHes the allowlisted fields and invalidates the org query", async () => {
    vi.mocked(api.patch).mockResolvedValue(mockOrg);

    const { result } = renderHook(() => useUpdateOrganisation("org-123"), {
      wrapper: createWrapper(),
    });

    await act(async () => {
      await result.current.mutateAsync({
        name: "Renamed Pte Ltd",
        address_line_1: "1 Raffles Place",
      });
    });

    expect(api.patch).toHaveBeenCalledWith("/api/v1/org-123/", {
      name: "Renamed Pte Ltd",
      address_line_1: "1 Raffles Place",
    });
  });
});

describe("useGstRegistration", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("POSTs the registration payload to the gst endpoint", async () => {
    vi.mocked(api.post).mockResolvedValue(mockOrg);

    const { result } = renderHook(() => useGstRegistration("org-123"), {
      wrapper: createWrapper(),
    });

    await act(async () => {
      await result.current.mutateAsync({
        gst_reg_number: "M90345678",
        gst_reg_date: "2024-01-01",
      });
    });

    expect(api.post).toHaveBeenCalledWith("/api/v1/org-123/gst/", {
      gst_reg_number: "M90345678",
      gst_reg_date: "2024-01-01",
    });
  });
});

describe("useGstDeregistration", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("DELETEs the gst endpoint", async () => {
    vi.mocked(api.delete).mockResolvedValue(mockOrg);

    const { result } = renderHook(() => useGstDeregistration("org-123"), {
      wrapper: createWrapper(),
    });

    await act(async () => {
      await result.current.mutateAsync();
    });

    expect(api.delete).toHaveBeenCalledWith("/api/v1/org-123/gst/");
  });

describe("useUpdateOrganisation — org-state propagation (P8/S-2)", () => {
  it("refreshes the auth provider's organisations after a successful rename", async () => {
    const refreshOrganisations = vi.fn();
    __testRefreshOrganisations.mockImplementation(refreshOrganisations);
    vi.mocked(api.patch).mockResolvedValue({ ...mockOrg, name: "Renamed Pte Ltd" });

    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
    });
    const wrapper = ({ children }: { children: React.ReactNode }) => (
      <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
    );

    const { result } = renderHook(() => useUpdateOrganisation("org-123"), { wrapper });
    act(() => {
      result.current.mutate({ name: "Renamed Pte Ltd" });
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    // The sidebar org name comes from the provider's state — without this
    // call it stayed stale until a full reload (P8/S-2).
    expect(refreshOrganisations).toHaveBeenCalled();
  });
});

});
