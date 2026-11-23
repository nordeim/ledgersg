/**
 * Auth Token Refresh Tests - TDD RED Phase
 *
 * These tests validate that token refresh correctly extracts
 * the access token from the nested response structure.
 *
 * Issue: Frontend expects data.access but backend returns data.tokens.access
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import {
  api,
  setAccessToken,
  getAccessToken,
  clearAuth,
} from "../api-client";

describe("Token Refresh - Issue #1", () => {
  beforeEach(() => {
    clearAuth();
    vi.resetAllMocks();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  describe("Response Structure Parsing", () => {
    it("should extract token from nested structure (BACKEND FORMAT)", async () => {
      // Backend returns: {"tokens": {"access": "...", "refresh": "..."}}
      const mockResponse = {
        ok: true,
        json: vi.fn().mockResolvedValue({
          tokens: {
            access: "new-access-token-12345",
            refresh: "new-refresh-token-67890",
          },
        }),
      };

      global.fetch = vi.fn().mockResolvedValue(mockResponse);

      // Make a request that will trigger token refresh
      // We need to simulate a 401 followed by successful refresh
      const responses = [
        // First request: 401 (token expired)
        {
          status: 401,
          ok: false,
          json: vi.fn().mockResolvedValue({ detail: "Token expired" }),
        },
        // Token refresh request: success
        mockResponse,
        // Retry original request: success
        {
          ok: true,
          json: vi.fn().mockResolvedValue({ success: true }),
        },
      ];

      let responseIndex = 0;
      global.fetch = vi.fn().mockImplementation(() => {
        return Promise.resolve(responses[responseIndex++]);
      });

      // Set initial token
      setAccessToken("old-token");

      // Make request
      try {
        await api.get("/test-endpoint/");
      } catch {
        // Expected to fail if refresh doesn't work
      }

      // Fixed code should extract token from nested structure
      const currentToken = getAccessToken();

      // After fix, this should correctly extract "new-access-token-12345"
      // from data.tokens.access
      expect(currentToken).toBe("new-access-token-12345");
    });

    it("should handle flat structure for backward compatibility", async () => {
      // Some APIs might still return flat structure
      const mockResponse = {
        ok: true,
        json: vi.fn().mockResolvedValue({
          access: "flat-access-token",
          refresh: "flat-refresh-token",
        }),
      };

      global.fetch = vi.fn().mockResolvedValue(mockResponse);

      // Simulate 401 -> refresh -> success
      const responses = [
        { status: 401, ok: false, json: vi.fn().mockResolvedValue({}) },
        mockResponse,
        { ok: true, json: vi.fn().mockResolvedValue({}) },
      ];

      let responseIndex = 0;
      global.fetch = vi.fn().mockImplementation(() => {
        return Promise.resolve(responses[responseIndex++]);
      });

      setAccessToken("old-token");

      try {
        await api.get("/test-endpoint/");
      } catch {}

      // Flat structure should work with current code
      // But will fail after fix if we don't handle both
      expect(getAccessToken()).toBe("flat-access-token");
    });

    it("should fail gracefully when token is missing", async () => {
      const mockResponse = {
        ok: true,
        json: vi.fn().mockResolvedValue({
          // Missing access token
          other: "data",
        }),
      };

      global.fetch = vi.fn().mockResolvedValue(mockResponse);

      const responses = [
        { status: 401, ok: false, json: vi.fn().mockResolvedValue({}) },
        mockResponse,
      ];

      let responseIndex = 0;
      global.fetch = vi.fn().mockImplementation(() => {
        return Promise.resolve(responses[responseIndex++]);
      });

      setAccessToken("old-token");

      // Should not throw, just fail to refresh
      await expect(api.get("/test/")).rejects.toThrow();

      // Token should be cleared on complete auth failure
      expect(getAccessToken()).toBeNull();
    });
  });

  describe("Token Refresh Retry Logic", () => {
    it("should retry original request with new token after refresh", async () => {
      const newToken = "refreshed-token-abc123";

      const responses = [
        // First request: 401
        {
          status: 401,
          ok: false,
          json: vi.fn().mockResolvedValue({ detail: "Expired" }),
        },
        // Refresh: success
        {
          ok: true,
          json: vi.fn().mockResolvedValue({
            tokens: {
              access: newToken,
              refresh: "new-refresh",
            },
          }),
        },
        // Retry: success
        {
          ok: true,
          json: vi.fn().mockResolvedValue({ data: "success" }),
        },
      ];

      let responseIndex = 0;
      const fetchCalls: string[][] = [];

      global.fetch = vi.fn().mockImplementation((url: string, options: any) => {
        fetchCalls.push([url, options?.headers?.Authorization || "no-auth"]);
        return Promise.resolve(responses[responseIndex++]);
      });

      setAccessToken("old-token");

      await api.get("/test-endpoint/");

      // Should have made 3 calls
      expect(fetchCalls.length).toBe(3);

      // First call with old token
      expect(fetchCalls[0][1]).toBe("Bearer old-token");

      // Last call should have new token
      // This will fail with current code because token extraction is broken
      expect(fetchCalls[2][1]).toBe(`Bearer ${newToken}`);
    });

    it("should redirect to login when refresh fails", async () => {
      // Mock window.location
      const mockLocation = { href: "" };
      Object.defineProperty(window, "location", {
        value: mockLocation,
        writable: true,
      });

      const responses = [
        // Request: 401
        { status: 401, ok: false, json: vi.fn().mockResolvedValue({}) },
        // Refresh: fails
        { ok: false, status: 401, json: vi.fn().mockResolvedValue({}) },
      ];

      let responseIndex = 0;
      global.fetch = vi.fn().mockImplementation(() => {
        return Promise.resolve(responses[responseIndex++]);
      });

      setAccessToken("old-token");

      try {
        await api.get("/test/");
      } catch {}

      // Should redirect to login
      expect(window.location.href).toBe("/login");

      // Token should be cleared
      expect(getAccessToken()).toBeNull();
    });

    it("P4/E-1: refreshes on a cold-reload 401 (no in-memory access token) — the refresh cookie path", async () => {
      // The cross-reload regression test: after a full page reload the
      // api-client holds NO access token. The backend's session_hint
      // marker cookie (set at login, JS-readable) is the evidence that a
      // session exists — the first request 401s, the client attempts the
      // refresh POST (the browser replays the HttpOnly refresh cookie via
      // credentials:"include") and retries with the new token. The pre-P4
      // guard (`response.status === 401 && accessToken`) never fired in
      // this state — every reload dropped the session.
      const newToken = "cold-reload-token-42";

      // The realistic post-login browser state: the hint cookie is present.
      document.cookie = "session_hint=1; path=/";
      try {
        const responses = [
          // First request: 401 with NO in-memory token
          {
            status: 401,
            ok: false,
            json: vi.fn().mockResolvedValue({ detail: "Unauthorized" }),
          },
          // Refresh POST (cookie-based, no body): success
          {
            ok: true,
            json: vi.fn().mockResolvedValue({
              tokens: {
                access: newToken,
                refresh: "rotated-refresh",
              },
            }),
          },
          // Retry: success
          {
            ok: true,
            json: vi.fn().mockResolvedValue({ data: "recovered" }),
          },
        ];

        let responseIndex = 0;
        const fetchCalls: string[][] = [];
        global.fetch = vi.fn().mockImplementation(
          (url: string, options?: { headers?: Record<string, string> }) => {
            fetchCalls.push([url, options?.headers?.Authorization || "no-auth"]);
            return Promise.resolve(responses[responseIndex++]);
          }
        );

        // Cold reload state: no token in module memory
        clearAuth();

        const result = await api.get("/cold-reload-endpoint/");

        // must attempt refresh then retry (3 calls total)
        expect(fetchCalls.length).toBe(3);
        expect(fetchCalls[0][1]).toBe("no-auth");
        expect(fetchCalls[1][0]).toContain("/api/v1/auth/refresh/");
        expect(fetchCalls[1][1]).toBe("no-auth");
        expect(fetchCalls[2][1]).toBe(`Bearer ${newToken}`);
        expect(result).toEqual({ data: "recovered" });
      } finally {
        document.cookie =
          "session_hint=; path=/; expires=Thu, 01 Jan 1970 00:00:00 GMT";
      }
    });

    it("P4/E-1: clear-reload refresh failure clears auth and throws 401", async () => {
      document.cookie = "session_hint=1; path=/";
      try {
        const mockLocation = { href: "" };
        Object.defineProperty(window, "location", {
          value: mockLocation,
          writable: true,
        });

        const responses = [
          // First request: 401, no in-memory token
          { status: 401, ok: false, json: vi.fn().mockResolvedValue({}) },
          // Refresh: fails (cookie absent/expired)
          { ok: false, status: 401, json: vi.fn().mockResolvedValue({}) },
        ];

        let responseIndex = 0;
        global.fetch = vi.fn().mockImplementation(() => {
          return Promise.resolve(responses[responseIndex++]);
        });

        clearAuth();

        await expect(api.get("/cold-failure/")).rejects.toMatchObject({
          name: "ApiError",
          status: 401,
        });
        expect(getAccessToken()).toBeNull();
      } finally {
        document.cookie =
          "session_hint=; path=/; expires=Thu, 01 Jan 1970 00:00:00 GMT";
      }
    });
  });

  describe("Session-hint evidence gate (P4/E-1 refinement)", () => {
    // Discovered in the e2e run: refreshing on EVERY 401 turned an anonymous
    // failure (bad login credentials) into a pointless refresh POST that
    // flooded the refresh rate limit and swallowed the login form's error
    // behind a hard redirect. The gate: attempt the refresh only when there
    // is evidence a session exists (in-memory access token OR the backend's
    // JS-readable session_hint marker cookie); an anonymous 401 propagates
    // untouched to the caller.

    const HINT_COOKIE = "session_hint";

    function setHintCookie() {
      document.cookie = `${HINT_COOKIE}=1; path=/`;
    }

    function clearHintCookie() {
      document.cookie = `${HINT_COOKIE}=; path=/; expires=Thu, 01 Jan 1970 00:00:00 GMT`;
    }

    beforeEach(() => {
      clearAuth();
      clearHintCookie();
      vi.resetAllMocks();
    });

    afterEach(() => {
      clearHintCookie();
      vi.restoreAllMocks();
    });

    it("an anonymous 401 (no token, no hint cookie) does NOT attempt a refresh and propagates the 401", async () => {
      // The login-form regression: a bad-credentials POST must reach the
      // caller as ApiError(401) so the form can show its own message —
      // exactly one network call, no hard redirect.
      const mockLocation = { href: "" };
      Object.defineProperty(window, "location", {
        value: mockLocation,
        writable: true,
      });

      global.fetch = vi.fn().mockImplementation(() =>
        Promise.resolve({
          status: 401,
          ok: false,
          json: vi.fn().mockResolvedValue({
            error: {
              code: "invalid_credentials",
              message: "Invalid email or password",
            },
          }),
        })
      );

      await expect(
        api.post("/api/v1/auth/login/", { email: "x@y.z", password: "wrong" })
      ).rejects.toMatchObject({ name: "ApiError", status: 401 });

      // exactly ONE request — no refresh attempt, no retry
      expect(global.fetch).toHaveBeenCalledTimes(1);

      // no hard redirect — the caller (the login form) keeps control
      expect(window.location.href).toBe("");
    });

    it("a 401 WITH the hint cookie (cold reload, no in-memory token) still refreshes and retries", async () => {
      const newToken = "hint-gated-token";
      setHintCookie();

      const responses = [
        {
          status: 401,
          ok: false,
          json: vi.fn().mockResolvedValue({ detail: "Unauthorized" }),
        },
        {
          ok: true,
          json: vi.fn().mockResolvedValue({
            tokens: { access: newToken, refresh: "rotated" },
          }),
        },
        { ok: true, json: vi.fn().mockResolvedValue({ data: "recovered" }) },
      ];
      let responseIndex = 0;
      const fetchCalls: string[][] = [];
      global.fetch = vi.fn().mockImplementation(
        (url: string, options?: { headers?: Record<string, string> }) => {
          fetchCalls.push([url, options?.headers?.Authorization || "no-auth"]);
          return Promise.resolve(responses[responseIndex++]);
        }
      );

      const result = await api.get("/hint-gated-endpoint/");

      expect(fetchCalls.length).toBe(3);
      expect(fetchCalls[1][0]).toContain("/api/v1/auth/refresh/");
      expect(fetchCalls[2][1]).toBe(`Bearer ${newToken}`);
      expect(result).toEqual({ data: "recovered" });
    });

    it("refresh failure WITH the hint cookie clears auth and redirects (the session is dead)", async () => {
      setHintCookie();
      const mockLocation = { href: "" };
      Object.defineProperty(window, "location", {
        value: mockLocation,
        writable: true,
      });

      const responses = [
        { status: 401, ok: false, json: vi.fn().mockResolvedValue({}) },
        { ok: false, status: 401, json: vi.fn().mockResolvedValue({}) },
      ];
      let responseIndex = 0;
      global.fetch = vi.fn().mockImplementation(() =>
        Promise.resolve(responses[responseIndex++])
      );

      await expect(api.get("/dead-session/")).rejects.toMatchObject({
        name: "ApiError",
        status: 401,
      });
      expect(getAccessToken()).toBeNull();
      expect(window.location.href).toBe("/login");
    });
  });

  describe("Expected Behavior After Fix", () => {
    it("[EXPECTED AFTER FIX] should extract token from nested structure", async () => {
      // This test documents what SHOULD happen after fix
      // It will fail now (RED), pass after fix (GREEN)

      const responses = [
        { status: 401, ok: false, json: vi.fn().mockResolvedValue({}) },
        {
          ok: true,
          json: vi.fn().mockResolvedValue({
            tokens: {
              access: "nested-token-123",
              refresh: "refresh-456",
            },
          }),
        },
        { ok: true, json: vi.fn().mockResolvedValue({}) },
      ];

      let responseIndex = 0;
      global.fetch = vi.fn().mockImplementation(() => {
        return Promise.resolve(responses[responseIndex++]);
      });

      setAccessToken("old");

      try {
        await api.get("/test/");
      } catch {}

      // After fix, this should be "nested-token-123"
      // Currently null (RED)
      expect(getAccessToken()).toBe("nested-token-123");
    });

    it("[EXPECTED AFTER FIX] should support both structures", async () => {
      // Test that both flat and nested structures work after fix

      // Test 1: Nested structure
      global.fetch = vi
        .fn()
        .mockImplementationOnce(() =>
          Promise.resolve({
            status: 401,
            ok: false,
            json: vi.fn().mockResolvedValue({}),
          })
        )
        .mockImplementationOnce(() =>
          Promise.resolve({
            ok: true,
            json: vi.fn().mockResolvedValue({
              tokens: { access: "nested" },
            }),
          })
        )
        .mockImplementationOnce(() =>
          Promise.resolve({
            ok: true,
            json: vi.fn().mockResolvedValue({}),
          })
        );

      clearAuth();
      setAccessToken("old");

      try {
        await api.get("/test/");
      } catch {}

      // Should extract from tokens.access
      expect(getAccessToken()).toBe("nested");
    });
  });
});

describe("api.blob — authorized binary downloads (P3/D-2)", () => {
  beforeEach(() => {
    clearAuth();
    vi.resetAllMocks();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("attaches the in-memory bearer token and returns the blob", async () => {
    const blob = new Blob(["%PDF-1.4 fake"], { type: "application/pdf" });
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      blob: vi.fn().mockResolvedValue(blob),
    });

    setAccessToken("memory-token");
    const result = await api.blob("/api/v1/org/documents/doc-1/pdf/");

    expect(result).toBe(blob);
    const [url, init] = (global.fetch as ReturnType<typeof vi.fn>).mock.calls[0];
    expect(url).toContain("/pdf/");
    expect((init as RequestInit).headers).toMatchObject({
      Authorization: "Bearer memory-token",
    });
  });

  it("surfaces the backend error envelope on a failed download (P8/G-7)", async () => {
    // A 404 from the backend arrives in the wrap_response envelope — the
    // pre-P8 blob path read only top-level message/detail and fell back to
    // the generic "Download failed: Not Found".
    global.fetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 404,
      statusText: "Not Found",
      json: vi.fn().mockResolvedValue({
        error: { code: "not_found", message: "Document not found." },
      }),
    });

    await expect(
      api.blob("/api/v1/org/documents/doc-1/pdf/")
    ).rejects.toMatchObject({
      name: "ApiError",
      status: 404,
      message: "Document not found.",
    });
  });

  it("falls back to the download-specific message when the body is not JSON (P8/G-7)", async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 502,
      statusText: "Bad Gateway",
      json: vi.fn().mockRejectedValue(new Error("not json")),
    });

    await expect(
      api.blob("/api/v1/org/documents/doc-1/pdf/")
    ).rejects.toMatchObject({
      name: "ApiError",
      status: 502,
      message: "Download failed: Bad Gateway",
    });
  });

  it("refreshes and retries once on 401 (same auth path as JSON requests)", async () => {
    const blob = new Blob(["%PDF retry"], { type: "application/pdf" });
    const responses = [
      { ok: false, status: 401, json: vi.fn().mockResolvedValue({}) },
      // refresh response
      { ok: true, json: vi.fn().mockResolvedValue({ tokens: { access: "fresh" } }) },
      // retried download
      { ok: true, status: 200, blob: vi.fn().mockResolvedValue(blob) },
    ];
    let i = 0;
    global.fetch = vi.fn().mockImplementation(() => Promise.resolve(responses[i++]));

    setAccessToken("expired-token");
    const result = await api.blob("/api/v1/org/documents/doc-2/pdf/");

    expect(result).toBe(blob);
    expect(getAccessToken()).toBe("fresh");
    expect(global.fetch).toHaveBeenCalledTimes(3);
  });

  it("throws ApiError with the status on non-OK responses", async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 404,
      statusText: "Not Found",
      json: vi.fn().mockResolvedValue({ detail: "No such document" }),
    });

    setAccessToken("memory-token");
    await expect(api.blob("/api/v1/org/documents/nope/pdf/")).rejects.toMatchObject({
      status: 404,
      name: "ApiError",
    });
  });
});
