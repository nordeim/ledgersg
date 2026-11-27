/**
 * P27/FE-H1 + FE-M3 — the invoices pagination STATE-MACHINE contracts,
 * tested through the REAL useInvoices hook (only the api-client
 * transport is mocked — the ledger-org-switch.test.tsx pattern).
 *
 * Why a real-hook spec: the P26 page tests mock `useInvoices`, and a
 * module mock cannot observe a CACHE-SERVED REVERT — when the offset
 * state snaps back to 0, TanStack re-renders the hook with the page-1
 * queryKey and serves the cached entry WITHOUT a transport call. Only
 * the real hook under a real QueryClient exhibits the user-visible
 * behaviour (the rendered page-math summary flipping back to page 1).
 *
 * The contracts pinned here:
 * (a) P27/FE-H1 — a Next click inside the mount-run window of the
 *     search-debounce effect is never silently reverted to page 1 (the
 *     pre-P27 timer body called setOffset(0) on the mount-run — ~300ms
 *     after mount, doubled under React StrictMode — so a click inside
 *     the window reverted to the cached page 1 with no refetch and no
 *     feedback; the serial full-run e2e lost this race deterministically
 *     while the isolated run passed it).
 * (b) the counter-pin — a REAL search change (a debounced VALUE
 *     change) still restarts the paging: the fix may close the
 *     mount-run window but must not drop the intended reset.
 * (c) P27/FE-M3 — the organisation switch never dispatches the new
 *     org at the previous offset (the P25/FE-L3 ledger contract,
 *     applied to this surface).
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, act } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { InvoicesClient } from "../invoices-client";

const fetchedUrls: string[] = [];

vi.mock("@/lib/api-client", () => ({
  api: {
    get: vi.fn(async (url: string) => {
      fetchedUrls.push(url);
      return {
        results: [
          {
            id: `doc-${fetchedUrls.length}`,
            document_type: "SALES_INVOICE",
            document_number: "INV-000042",
            contact_id: "contact-1",
            contact_name: "ABC Pte Ltd",
            issue_date: "2026-01-15",
            due_date: "2026-02-14",
            status: "SENT",
            status_display: "Sent",
            total_incl: "5400.0000",
            currency: "SGD",
            amount_paid: "0.0000",
            amount_due: "5400.0000",
            related_document_id: null,
          },
        ],
        count: 51,
      };
    }),
  },
  endpoints: {
    invoices: (orgId: string) => ({
      list: `/api/v1/${orgId}/invoicing/documents/`,
    }),
  },
}));

const { __testAuth } = vi.hoisted(() => ({
  __testAuth: {
    currentOrg: { id: "org-123", name: "Test Org" } as
      | { id: string; name: string }
      | null,
    isLoading: false,
  },
}));

vi.mock("@/providers/auth-provider", () => ({
  useAuth: () => __testAuth,
}));

function renderPage() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <InvoicesClient />
    </QueryClientProvider>
  );
}

/** Wait out real timers under act (the P26 lesson: userEvent + fake
 * timers hangs — fireEvent + real waits is the stable combination). */
const wait = (ms: number) =>
  act(async () => {
    await new Promise((r) => setTimeout(r, ms));
  });

describe("InvoicesClient — the pagination state machine (P27)", () => {
  beforeEach(() => {
    fetchedUrls.length = 0;
    __testAuth.currentOrg = { id: "org-123", name: "Test Org" };
  });

  it("(a) a Next click inside the mount-debounce window is never reverted to page 1 (P27/FE-H1)", async () => {
    renderPage();

    // Page 1 arrives; click Next IMMEDIATELY — well inside the ~300ms
    // mount-run window of the search-debounce effect.
    expect(await screen.findByText("Showing 1–20 of 51 rows")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: /next page/i }));
    expect(await screen.findByText("Showing 21–40 of 51 rows")).toBeInTheDocument();

    // Wait PAST the mount window (the mount-run timer, plus the
    // StrictMode double-run margin). The page-2 state must HOLD —
    // the pre-P27 code snapped back to the cached page 1 here, with
    // no refetch and no feedback (the click was silently lost).
    await wait(700);
    expect(screen.getByText("Showing 21–40 of 51 rows")).toBeInTheDocument();
    expect(
      screen.queryByText("Showing 1–20 of 51 rows")
    ).not.toBeInTheDocument();
  });

  it("(b) a real search change still restarts the paging (the debounced VALUE change)", async () => {
    renderPage();

    // Walk to page 2 first.
    expect(await screen.findByText("Showing 1–20 of 51 rows")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: /next page/i }));
    expect(await screen.findByText("Showing 21–40 of 51 rows")).toBeInTheDocument();

    // Type a search while on page 2; let the 300ms debounce elapse.
    fireEvent.change(
      screen.getByLabelText("Search invoices by number or customer"),
      { target: { value: "INV-000042" } }
    );
    await wait(450);

    // The search rides the filters SERVER-SIDE and the paging
    // restarts: the searched set is fetched at offset 0 — never at
    // the stale offset 20.
    expect(
      fetchedUrls.some(
        (u) => u.includes("search=INV-000042") && u.includes("offset=0")
      )
    ).toBe(true);
    expect(
      fetchedUrls.some(
        (u) => u.includes("search=INV-000042") && u.includes("offset=20")
      )
    ).toBe(false);
    expect(
      await screen.findByText("Showing 1–20 of 51 rows")
    ).toBeInTheDocument();
  });

  it("(c) never fetches the switched organisation at the previous offset (P27/FE-M3)", async () => {
    const { rerender } = renderPage();

    // Walk to page 2 of org-123.
    expect(await screen.findByText("Showing 1–20 of 51 rows")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: /next page/i }));
    expect(await screen.findByText("Showing 21–40 of 51 rows")).toBeInTheDocument();
    expect(
      fetchedUrls.some((u) => u.includes("org-123") && u.includes("offset=20"))
    ).toBe(true);

    // Switch the organisation mid-pagination.
    __testAuth.currentOrg = { id: "org-456", name: "Switched Org" };
    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });
    rerender(
      <QueryClientProvider client={queryClient}>
        <InvoicesClient />
      </QueryClientProvider>
    );

    // The new org settles on its page 1 …
    expect(
      await screen.findByText("Showing 1–20 of 51 rows")
    ).toBeInTheDocument();

    // … and NOT ONE of its fetches carried the stale offset.
    const switchedOrgUrls = fetchedUrls.filter((u) => u.includes("org-456"));
    expect(switchedOrgUrls.length).toBeGreaterThan(0);
    expect(
      switchedOrgUrls.some((u) => u.includes("offset=20")),
      `the switched org must never be fetched at a stale offset — got: ${switchedOrgUrls.join(", ")}`
    ).toBe(false);
    expect(switchedOrgUrls.some((u) => u.includes("offset=0"))).toBe(true);
  });
});
