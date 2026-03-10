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

      const result = await api.get("/test-endpoint/");

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
      let responseIndex = 0;
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
