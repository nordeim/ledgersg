/**
 * P9/B-1: multipart uploads must go out as real multipart.
 *
 * The statement import built a FormData and posted it through the JSON
 * helper — JSON.stringify(FormData) is "{}" with Content-Type
 * application/json, so the backend's request.FILES was always empty and
 * the import could never succeed through the UI.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";

const fetchMock = vi.fn();

vi.mock("@/lib/api-client", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api-client")>(
    "@/lib/api-client"
  );
  return actual;
});

import { api } from "@/lib/api-client";

describe("api.postForm (P9/B-1)", () => {
  beforeEach(() => {
    vi.stubGlobal("fetch", fetchMock);
    fetchMock.mockReset();
    fetchMock.mockResolvedValue(
      new Response(JSON.stringify({ imported: 2, duplicates: 0 }), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      })
    );
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("sends the FormData body without a JSON Content-Type header", async () => {
    const form = new FormData();
    form.append("bank_account_id", "acc-1");
    form.append("file", new File(["a,b,c"], "statement.csv", { type: "text/csv" }));

    const result = await api.postForm<{ imported: number }>(
      "/api/v1/org-1/banking/bank-transactions/import/",
      form
    );

    expect(result.imported).toBe(2);
    expect(fetchMock).toHaveBeenCalledTimes(1);

    const [url, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(url).toContain("/bank-transactions/import/");
    // The body must be the FormData instance itself — NOT a stringified "{}".
    expect(init.body).toBeInstanceOf(FormData);
    // No Content-Type: the browser sets multipart/form-data with the
    // boundary. An explicit application/json header makes the backend
    // parse the body as JSON and request.FILES stays empty.
    const headers = init.headers as Record<string, string>;
    expect(
      Object.keys(headers).some(
        (k) => k.toLowerCase() === "content-type" && headers[k].includes("json")
      )
    ).toBe(false);
  });
});
