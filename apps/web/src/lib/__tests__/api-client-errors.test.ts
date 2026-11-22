/**
 * P7/F-7: the api-client must surface the backend's REAL error messages.
 *
 * The backend error envelope (wrap_response / custom_exception_handler) is
 * {"error": {"code", "message", "details"}} and DRF serializer errors are
 * {"field": ["msg"]}. The pre-P7 reader looked only at errorData.message /
 * errorData.detail — neither key exists in the envelope — so every
 * business-rule failure surfaced as the generic "Request failed: Bad
 * Request" (which is exactly what hid the always-broken Void button).
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { api, clearAuth } from "../api-client";

function mockErrorResponse(status: number, body: unknown) {
  return {
    ok: false,
    status,
    statusText: status === 400 ? "Bad Request" : "Error",
    json: vi.fn().mockResolvedValue(body),
  };
}

describe("api-client error envelope (P7/F-7)", () => {
  beforeEach(() => {
    clearAuth();
    vi.resetAllMocks();
  });

  afterEach(() => {
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
  });

  it("extracts the message from the backend error envelope", async () => {
    global.fetch = vi.fn().mockResolvedValue(
      mockErrorResponse(400, {
        error: { code: "validation_error", message: "Void reason is required." },
      })
    );

    await expect(api.get("/api/v1/x/void/")).rejects.toMatchObject({
      status: 400,
      message: "Void reason is required.",
    });
  });

  it("extracts the message from a bare message key (legacy/simple shapes)", async () => {
    global.fetch = vi.fn().mockResolvedValue(
      mockErrorResponse(403, { message: "You do not have access to this organisation" })
    );

    await expect(api.get("/api/v1/x/")).rejects.toMatchObject({
      status: 403,
      message: "You do not have access to this organisation",
    });
  });

  it("extracts DRF field errors (first field message)", async () => {
    global.fetch = vi.fn().mockResolvedValue(
      mockErrorResponse(400, { reason: ["This field is required."] })
    );

    await expect(api.get("/api/v1/x/")).rejects.toMatchObject({
      status: 400,
      message: "reason: This field is required.",
    });
  });

  it("carries envelope details through ApiError.errors", async () => {
    global.fetch = vi.fn().mockResolvedValue(
      mockErrorResponse(400, {
        error: {
          code: "validation_error",
          message: "Invalid payload",
          details: { gst_reg_number: "must start with M" },
        },
      })
    );

    await expect(api.get("/api/v1/x/")).rejects.toMatchObject({
      status: 400,
      message: "Invalid payload",
      errors: { gst_reg_number: "must start with M" },
    });
  });

  it("falls back to the status text for non-JSON bodies", async () => {
    const response = {
      ok: false,
      status: 502,
      statusText: "Bad Gateway",
      json: vi.fn().mockRejectedValue(new Error("not json")),
    };
    global.fetch = vi.fn().mockResolvedValue(response);

    await expect(api.get("/api/v1/x/")).rejects.toMatchObject({
      status: 502,
      message: "Request failed: Bad Gateway",
    });
  });
});
