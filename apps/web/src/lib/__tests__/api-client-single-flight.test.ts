/**
 * P15/F-B(a) — single-flight token refresh.
 *
 * The live e2e suite exposed the race: two parallel requests hit their 401
 * handlers at the same moment; both call tryRefreshToken. Refresh #1
 * rotates the token pair (the old refresh token is blacklisted server-side
 * — rotation is the P4 contract); the concurrent refresh #2 still carries
 * the pre-rotation cookie, gets 401, returns false, and its failure path
 * fires clearAuth() + a hard redirect to /login — the session dies
 * mid-suite for no user-visible reason.
 *
 * The fix: ONE in-flight refresh promise shared by every concurrent 401 —
 * the second caller awaits the same refresh instead of firing its own.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { api, setAccessToken, clearAuth } from "../api-client";

describe("Single-flight refresh (P15/F-B a)", () => {
  beforeEach(() => {
    clearAuth();
    vi.resetAllMocks();
    // session evidence so the 401 handler attempts the refresh
    document.cookie = "session_hint=1; path=/";
    setAccessToken("stale-access-token");
  });

  afterEach(() => {
    document.cookie = "session_hint=; expires=Thu, 01 Jan 1970 00:00:00 GMT; path=/";
    vi.restoreAllMocks();
  });

  function installFetchMock(nthCallIs401: (dataCallNumber: number) => boolean) {
    const calls: string[] = [];
    const fetchMock = vi.fn().mockImplementation((url: RequestInfo | URL) => {
      const u = String(url);
      if (u.includes("/auth/refresh/")) {
        calls.push("refresh");
        return Promise.resolve(
          new Response(
            JSON.stringify({
              tokens: { access: `fresh-${calls.filter((c) => c === "refresh").length}`, refresh: "r" },
            }),
            { status: 200, headers: { "Content-Type": "application/json" } }
          )
        );
      }
      calls.push(`data:${u}`);
      const dataCallNumber = calls.filter((c) => c.startsWith("data:")).length;
      const is401 = nthCallIs401(dataCallNumber);
      return Promise.resolve(
        new Response(
          is401 ? JSON.stringify({ error: { code: "authentication_failed" } }) : "{}",
          { status: is401 ? 401 : 200, headers: { "Content-Type": "application/json" } }
        )
      );
    });
    global.fetch = fetchMock as unknown as typeof fetch;
    return calls;
  }

  it("fires exactly ONE refresh for two parallel 401s", async () => {
    // data calls 1-2: the parallel pair 401s; 3-4: the retries after refresh
    const calls = installFetchMock((n) => n <= 2);

    const [a, b] = await Promise.all([
      api.get("/api/v1/ping-a/").catch((e) => {
        console.log("A failed:", String(e));
        return null;
      }),
      api.get("/api/v1/ping-b/").catch((e) => {
        console.log("B failed:", String(e));
        return null;
      }),
    ]);

    const refreshes = calls.filter((c) => c === "refresh").length;
    expect(refreshes).toBe(1);
    expect(a).not.toBeNull();
    expect(b).not.toBeNull();
  });

  it("a second 401 AFTER a completed refresh fires a new refresh (per-window, not forever)", async () => {
    // data calls 1-2: the parallel pair 401s; 3-4: their retries (200);
    // 5: a LATER request whose new token expired 401s again.
    const calls = installFetchMock((n) => n <= 2 || n === 5);

    await Promise.all([
      api.get("/api/v1/first/").catch(() => null),
      api.get("/api/v1/second/").catch(() => null),
    ]);
    expect(calls.filter((c) => c === "refresh").length).toBe(1);

    // the later 401 refreshes again — not blocked forever
    await api.get("/api/v1/third/");
    expect(calls.filter((c) => c === "refresh").length).toBe(2);
  });
});
