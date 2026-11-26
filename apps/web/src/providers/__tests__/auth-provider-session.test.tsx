/**
 * P9/S-2: checkSession tells transport faults from auth expiry.
 *
 * The catch treated EVERYTHING (network TypeError, 500s) like a 401:
 * clearAuth + redirect — a transient outage on page load bounced a
 * logged-in user to /login. Only auth failures (401/403) may clear the
 * session; transport faults keep the state (P8 gave refreshOrganisations
 * the same split).
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import * as apiClient from "@/lib/api-client";
import { AuthProvider, useAuth } from "../auth-provider";

const push = vi.fn();
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push, replace: vi.fn(), back: vi.fn(), prefetch: vi.fn() }),
}));

vi.mock("@/lib/api-client", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api-client")>(
    "@/lib/api-client"
  );
  return {
    ...actual,
    api: { get: vi.fn() },
  };
});

import { ApiError } from "@/lib/api-client";

function Probe() {
  const auth = useAuth();
  return (
    <div data-testid="probe">
      {auth.isLoading ? "loading" : "ready"}|{auth.user ? "user" : "anon"}
    </div>
  );
}

describe("checkSession transport-vs-auth (P9/S-2)", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    push.mockReset();
  });

  it("a network fault does NOT redirect to login", async () => {
    vi.mocked(apiClient.api.get).mockRejectedValue(new TypeError("Failed to fetch"));

    render(
      <AuthProvider>
        <Probe />
      </AuthProvider>
    );

    await waitFor(
      () => {
        expect(document.body.textContent).toContain("ready");
      },
      { timeout: 3000 }
    );

    expect(push).not.toHaveBeenCalled();
  });

  it("an auth failure (401) clears and redirects to login", async () => {
    vi.mocked(apiClient.api.get).mockRejectedValue(new ApiError(401, "Token expired"));

    render(
      <AuthProvider>
        <Probe />
      </AuthProvider>
    );

    await waitFor(
      () => {
        expect(push).toHaveBeenCalledWith(expect.stringContaining("/login"));
      },
      { timeout: 3000 }
    );
  });
});

describe("checkSession public-route guard (P10/H-2)", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    push.mockReset();
    window.history.pushState({}, "", "/register");
  });

  afterEach(() => {
    window.history.pushState({}, "", "/");
  });

  it("an anonymous 401 on /register does NOT bounce the visitor to login", async () => {
    // The mount-time session check fires on every page — including public
    // ones. An anonymous visitor on /register gets a plain 401 from
    // /auth/me; treating it like session expiry raced the form (the
    // e2e register test's button click landed mid-navigation) and in
    // production bounced self-serve signups to /login.
    vi.mocked(apiClient.api.get).mockRejectedValue(
      new ApiError(401, "Authentication credentials were not provided.")
    );

    render(
      <AuthProvider>
        <Probe />
      </AuthProvider>
    );

    await waitFor(
      () => {
        expect(document.body.textContent).toContain("ready");
      },
      { timeout: 3000 }
    );

    expect(push).not.toHaveBeenCalled();
  });
});

// ---------------------------------------------------------------------------
// P10/M-3: the chosen organisation survives the refresh — switchOrg
// persists via POST /auth/set-default-org/ (the endpoint existed with zero
// callers; the choice was local state that reset on every reload).
// ---------------------------------------------------------------------------

describe("switchOrg persists the choice (P10/M-3)", () => {
  const orgA = "11111111-1111-4111-8111-111111111111";
  const orgB = "22222222-2222-4222-8222-222222222222";
  const orgsPayload = [
    {
      org: { id: orgA, name: "Org A" },
      role: { can_manage_org: true },
      is_default: true,
    },
    {
      org: { id: orgB, name: "Org B" },
      role: { can_manage_org: true },
      is_default: false,
    },
  ];

  beforeEach(() => {
    vi.clearAllMocks();
    push.mockReset();
  });

  it("switchOrg fires the set-default-org endpoint (fire-and-forget)", async () => {
    vi.mocked(apiClient.api.get).mockImplementation(async (url: string) => {
      if (url.includes("/organisations/")) return orgsPayload;
      return { id: "u1", email: "u@example.sg", full_name: "U" };
    });
    const postMock = vi.fn().mockResolvedValue({});
    (apiClient.api as unknown as { post: unknown }).post = postMock;

    // A holder object (not a bare outer variable) — the lint rule forbids
    // reassigning outer-scope let bindings inside a component.
    const holder: { switch: ((orgId: string) => void) | null } = { switch: null };
    function SwitchProbe() {
      const auth = useAuth();
      holder.switch = auth.switchOrg;
      return <div data-testid="switch-probe">{auth.currentOrg?.id ?? "none"}</div>;
    }

    render(
      <AuthProvider>
        <SwitchProbe />
      </AuthProvider>
    );

    // Wait for checkSession to resolve the org list.
    await waitFor(() => {
      expect(document.body.textContent).toContain(orgA);
    });

    holder.switch?.(orgB);

    await waitFor(() => {
      expect(postMock).toHaveBeenCalledWith(
        expect.stringContaining("set-default-org"),
        expect.objectContaining({ org_id: orgB })
      );
    });
    // The local state switches immediately too.
    await waitFor(() => {
      expect(document.body.textContent).toContain(orgB);
    });
  });

  it("a failed persistence POST keeps the local switch (fire-and-forget)", async () => {
    vi.mocked(apiClient.api.get).mockImplementation(async (url: string) => {
      if (url.includes("/organisations/")) return orgsPayload;
      return { id: "u1", email: "u@example.sg", full_name: "U" };
    });
    const postMock = vi.fn().mockRejectedValue(new Error("offline"));
    vi.mocked(apiClient.api).post = postMock;

    // A holder object (not a bare outer variable) — the lint rule forbids
    // reassigning outer-scope let bindings inside a component.
    const holder: { switch: ((orgId: string) => void) | null } = { switch: null };
    function SwitchProbe() {
      const auth = useAuth();
      holder.switch = auth.switchOrg;
      return <div data-testid="switch-probe">{auth.currentOrg?.id ?? "none"}</div>;
    }

    render(
      <AuthProvider>
        <SwitchProbe />
      </AuthProvider>
    );

    await waitFor(() => {
      expect(document.body.textContent).toContain(orgA);
    });

    holder.switch?.(orgB);

    await waitFor(() => {
      expect(document.body.textContent).toContain(orgB);
    });
    expect(push).not.toHaveBeenCalled();
  });
});

describe("selectOrgById selects without list state (P16/FE-H2)", () => {
  // The org-CREATION flow calls switchOrg(org.id) right after creating
  // the org — but switchOrg reads the `organisations` list from the
  // closure captured at mutation time (the pre-creation list). For a
  // fresh registrant that list is EMPTY, so the `if (org)` guard skipped
  // setCurrentOrgId, the query invalidation AND the set-default-org
  // persist — the dashboard rendered the "No Organisation Selected"
  // dead-end until a manual reload. The provider needs a selection
  // method that does not read list state.
  const freshOrgId = "33333333-3333-4333-8333-333333333333";

  beforeEach(() => {
    vi.clearAllMocks();
    push.mockReset();
  });

  it("selects an org that is not yet in the loaded list (the just-created org)", async () => {
    // Fresh registrant: NO organisations loaded yet.
    vi.mocked(apiClient.api.get).mockImplementation(async (url: string) => {
      if (url.includes("/organisations/")) return [];
      return { id: "u1", email: "fresh@ledgersg.sg", full_name: "Fresh" };
    });
    const postMock = vi.fn().mockResolvedValue({});
    (apiClient.api as unknown as { post: unknown }).post = postMock;

    // No outer-variable mutation (the lint register's immutability class):
    // the probe triggers the selection through a click handler.
    function SelectProbe() {
      const auth = useAuth();
      return (
        <button data-testid="select-btn" onClick={() => auth.selectOrgById(freshOrgId)}>
          select
        </button>
      );
    }

    render(
      <AuthProvider>
        <SelectProbe />
      </AuthProvider>
    );

    const button = await screen.findByTestId("select-btn");
    fireEvent.click(button);

    // The selection fires the persistence POST with the new org id —
    // the exact call the stale switchOrg guard skipped.
    await waitFor(() => {
      expect(postMock).toHaveBeenCalledWith(
        expect.stringContaining("set-default-org"),
        expect.objectContaining({ org_id: freshOrgId })
      );
    });
  });
});
