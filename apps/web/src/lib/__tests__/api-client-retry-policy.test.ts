/**
 * QueryClient mutation retry policy (P13/M-3).
 *
 * The client shipped `mutations: { retry: 1 }` — every failed mutation
 * re-fired once, including 4xx on non-idempotent POSTs
 * (/banking/payments/receive/, make/, allocate/). A network timeout after
 * the server processed a payment would re-send the payment (double
 * submission). Queries have a 401/403 carve-out; mutations got none.
 * React Query's default (retry: 0 for mutations) is the correct policy
 * for a financial client — the gate pins it.
 */

import { describe, expect, it } from "vitest";
import { queryClient } from "../api-client";

describe("QueryClient mutation retry policy (P13/M-3)", () => {
  it("mutations do NOT retry (double-submission hazard)", () => {
    const retry = queryClient.getDefaultOptions().mutations?.retry;
    // React Query's default for mutations is 0 (false); anything else
    // re-fires non-idempotent POSTs.
    expect(retry === 0 || retry === false).toBe(true);
  });

  it("queries keep their retry policy (the carve-out is untouched)", () => {
    const retry = queryClient.getDefaultOptions().queries?.retry;
    expect(typeof retry).toBe("function");
  });
});
