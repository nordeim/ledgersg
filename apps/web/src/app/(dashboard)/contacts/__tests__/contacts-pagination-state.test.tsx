/**
 * P27/FE-H1 + FE-M3 — the contacts pagination STATE-MACHINE contracts,
 * tested through the REAL useContacts hook (only the api-client
 * transport is mocked — the ledger-org-switch.test.tsx pattern; the
 * rationale is documented in invoices-pagination-state.test.tsx).
 *
 * The contracts pinned here:
 * (a) P27/FE-H1 — a Next click inside the mount-run window of the
 *     search-debounce effect is never silently reverted to page 1.
 * (b) the counter-pin — a REAL search change still restarts the paging.
 * (c) the counter-pin — the type-filter click still restarts the paging
 *     (the intended reset at the click handler — the fix must keep it).
 * (d) P27/FE-M3 — the organisation switch never dispatches the new org
 *     at the previous offset.
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, act } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import ContactsClient from "../contacts-client";

const fetchedUrls: string[] = [];

vi.mock("@/lib/api-client", () => ({
  api: {
    get: vi.fn(async (url: string) => {
      fetchedUrls.push(url);
      return {
        results: [
          {
            id: `contact-${fetchedUrls.length}`,
            org_id: "org-123",
            contact_type: "CUSTOMER",
            name: "ABC Pte Ltd",
            legal_name: null,
            email: "billing@abc.example",
            phone: null,
            address_line_1: null,
            address_line_2: null,
            postal_code: null,
            country: "SG",
            uen: null,
            gst_reg_number: null,
            peppol_id: null,
            is_peppol_enabled: false,
            payment_terms_days: 30,
            currency: "SGD",
            is_active: true,
            created_at: "2026-01-15T00:00:00Z",
            updated_at: "2026-01-15T00:00:00Z",
          },
        ],
        count: 51,
      };
    }),
  },
  endpoints: {
    contacts: (orgId: string) => ({
      list: `/api/v1/${orgId}/invoicing/contacts/`,
      detail: (id: string) => `/api/v1/${orgId}/invoicing/contacts/${id}/`,
    }),
  },
}));

const { __testAuth } = vi.hoisted(() => ({
  __testAuth: {
    currentOrg: { id: "org-123", name: "Test Org" } as
      | { id: string; name: string }
      | null,
    isLoading: false,
    // ContactRow gates the edit/deactivate buttons on the permission.
    hasPermission: () => true,
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
      <ContactsClient />
    </QueryClientProvider>
  );
}

const wait = (ms: number) =>
  act(async () => {
    await new Promise((r) => setTimeout(r, ms));
  });

describe("ContactsClient — the pagination state machine (P27)", () => {
  beforeEach(() => {
    fetchedUrls.length = 0;
    __testAuth.currentOrg = { id: "org-123", name: "Test Org" };
  });

  it("(a) a Next click inside the mount-debounce window is never reverted to page 1 (P27/FE-H1)", async () => {
    renderPage();

    expect(await screen.findByText("Showing 1–20 of 51 rows")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: /next page/i }));
    expect(await screen.findByText("Showing 21–40 of 51 rows")).toBeInTheDocument();

    // Past the mount window: the page-2 state must HOLD (the pre-P27
    // code snapped back to the cached page 1 — the click was lost).
    await wait(700);
    expect(screen.getByText("Showing 21–40 of 51 rows")).toBeInTheDocument();
    expect(
      screen.queryByText("Showing 1–20 of 51 rows")
    ).not.toBeInTheDocument();
  });

  it("(b) a real search change still restarts the paging (the debounced VALUE change)", async () => {
    renderPage();

    expect(await screen.findByText("Showing 1–20 of 51 rows")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: /next page/i }));
    expect(await screen.findByText("Showing 21–40 of 51 rows")).toBeInTheDocument();

    fireEvent.change(screen.getByLabelText("Search contacts"), {
      target: { value: "ABC" },
    });
    await wait(450);

    expect(
      fetchedUrls.some((u) => u.includes("search=ABC") && u.includes("offset=0"))
    ).toBe(true);
    expect(
      fetchedUrls.some((u) => u.includes("search=ABC") && u.includes("offset=20"))
    ).toBe(false);
    expect(
      await screen.findByText("Showing 1–20 of 51 rows")
    ).toBeInTheDocument();
  });

  it("(c) the type-filter click still restarts the paging (the intended click reset)", async () => {
    renderPage();

    expect(await screen.findByText("Showing 1–20 of 51 rows")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: /next page/i }));
    expect(await screen.findByText("Showing 21–40 of 51 rows")).toBeInTheDocument();

    // Clicking a type filter while on page 2 restarts the paging.
    fireEvent.click(screen.getByRole("button", { name: /customers only/i }));

    expect(
      fetchedUrls.some(
        (u) => u.includes("is_customer=true") && u.includes("offset=0")
      )
    ).toBe(true);
    expect(
      fetchedUrls.some(
        (u) => u.includes("is_customer=true") && u.includes("offset=20")
      )
    ).toBe(false);
    expect(
      await screen.findByText("Showing 1–20 of 51 rows")
    ).toBeInTheDocument();
  });

  it("(d) never fetches the switched organisation at the previous offset (P27/FE-M3)", async () => {
    const { rerender } = renderPage();

    expect(await screen.findByText("Showing 1–20 of 51 rows")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: /next page/i }));
    expect(await screen.findByText("Showing 21–40 of 51 rows")).toBeInTheDocument();

    __testAuth.currentOrg = { id: "org-456", name: "Switched Org" };
    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });
    rerender(
      <QueryClientProvider client={queryClient}>
        <ContactsClient />
      </QueryClientProvider>
    );

    expect(
      await screen.findByText("Showing 1–20 of 51 rows")
    ).toBeInTheDocument();

    const switchedOrgUrls = fetchedUrls.filter((u) => u.includes("org-456"));
    expect(switchedOrgUrls.length).toBeGreaterThan(0);
    expect(
      switchedOrgUrls.some((u) => u.includes("offset=20")),
      `the switched org must never be fetched at a stale offset — got: ${switchedOrgUrls.join(", ")}`
    ).toBe(false);
    expect(switchedOrgUrls.some((u) => u.includes("offset=0"))).toBe(true);
  });
});
