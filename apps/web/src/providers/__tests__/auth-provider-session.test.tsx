/**
 * P9/S-2: checkSession tells transport faults from auth expiry.
 *
 * The catch treated EVERYTHING (network TypeError, 500s) like a 401:
 * clearAuth + redirect — a transient outage on page load bounced a
 * logged-in user to /login. Only auth failures (401/403) may clear the
 * session; transport faults keep the state (P8 gave refreshOrganisations
 * the same split).
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, waitFor } from "@testing-library/react";
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
