/**
 * P27/FE-M2 + FE-M3 — the payments-list pagination state-machine
 * contracts, tested through the REAL usePayments hook (only the
 * api-client transport is mocked — the ledger-org-switch.test.tsx
 * pattern; the rationale is documented in
 * invoices-pagination-state.test.tsx).
 *
 * The contracts pinned here:
 * (a) P27/FE-M2 — changing the FILTERS restarts the paging: the new
 *     filter set is fetched at offset 0, never at the stale offset
 *     (the parent holds the filters in useState, so the prop identity
 *     changes exactly when the user changes a filter).
 * (b) P27/FE-M3 — switching the orgId prop mid-pagination never
 *     dispatches the new org at the previous offset.
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { PaymentList } from "../components/payment-list";
import type { Payment } from "@/shared/schemas";

const fetchedUrls: string[] = [];

vi.mock("@/lib/api-client", () => ({
  api: {
    get: vi.fn(async (url: string) => {
      fetchedUrls.push(url);
      return {
        results: [
          {
            id: `pay-${fetchedUrls.length}`,
            org: "org-123",
            payment_type: "RECEIVED",
            payment_number: "PAY-2026-001",
            payment_date: "2026-01-15",
            contact: "contact-1",
            contact_name: "ABC Pte Ltd",
            bank_account: "bank-1",
            bank_account_name: "Test Account",
            currency: "SGD",
            exchange_rate: "1.000000",
            amount: "5000.0000",
            base_amount: "5000.0000",
            fx_gain_loss: "0.0000",
            payment_method: "BANK_TRANSFER",
            payment_method_display: "Bank Transfer",
            payment_reference: null,
            journal_entry: null,
            is_reconciled: false,
            is_voided: false,
            notes: null,
            created_at: "2026-01-15T10:00:00Z",
            updated_at: "2026-01-15T10:00:00Z",
          } satisfies Payment,
        ],
        count: 51,
      };
    }),
  },
  endpoints: {
    banking: (orgId: string) => ({
      payments: `/api/v1/${orgId}/banking/payments/`,
      paymentDetail: (id: string) => `/api/v1/${orgId}/banking/payments/${id}/`,
    }),
  },
}));

function renderList(
  orgId = "org-123",
  filters?: { payment_type?: "RECEIVED" | "MADE" }
) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <PaymentList orgId={orgId} filters={filters} />
    </QueryClientProvider>
  );
}

describe("PaymentList — the pagination state machine (P27)", () => {
  beforeEach(() => {
    fetchedUrls.length = 0;
  });

  it("(a) changing the filters restarts the paging (P27/FE-M2)", async () => {
    const { rerender } = renderList();

    // Walk to page 2 of the unfiltered set.
    expect(await screen.findByText("Showing 1–20 of 51 rows")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: /next page/i }));
    expect(await screen.findByText("Showing 21–40 of 51 rows")).toBeInTheDocument();

    // The user narrows the filter (a NEW filters object identity).
    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });
    rerender(
      <QueryClientProvider client={queryClient}>
        <PaymentList orgId="org-123" filters={{ payment_type: "RECEIVED" }} />
      </QueryClientProvider>
    );

    // The filtered set is fetched at offset 0 — never at the stale
    // offset 20.
    expect(
      await screen.findByText("Showing 1–20 of 51 rows")
    ).toBeInTheDocument();
    const filteredUrls = fetchedUrls.filter((u) =>
      u.includes("payment_type=RECEIVED")
    );
    expect(filteredUrls.length).toBeGreaterThan(0);
    expect(
      filteredUrls.some((u) => u.includes("offset=20")),
      `the filtered set must never be fetched at a stale offset — got: ${filteredUrls.join(", ")}`
    ).toBe(false);
    expect(filteredUrls.some((u) => u.includes("offset=0"))).toBe(true);
  });

  it("(b) switching the organisation never dispatches the new org at the previous offset (P27/FE-M3)", async () => {
    const { rerender } = renderList();

    expect(await screen.findByText("Showing 1–20 of 51 rows")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: /next page/i }));
    expect(await screen.findByText("Showing 21–40 of 51 rows")).toBeInTheDocument();

    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });
    rerender(
      <QueryClientProvider client={queryClient}>
        <PaymentList orgId="org-456" />
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
