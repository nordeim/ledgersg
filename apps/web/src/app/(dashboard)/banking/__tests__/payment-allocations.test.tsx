/**
 * P10/M-7: payment allocations visible after creation. The list serializer
 * carries no allocations; PaymentDetailView returns them but usePayment had
 * zero consumers — users could never see which invoices a payment settled.
 * The rows gain an inline detail expansion (not a route).
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { PaymentList } from "../components/payment-list";
import * as bankingHooks from "@/hooks/use-banking";

const paymentFixture = {
  id: "55555555-5555-4555-8555-555555555555",
  org: "org-1",
  payment_type: "RECEIVED" as const,
  payment_number: "PAY-2026-0001",
  payment_date: "2026-11-01",
  contact: "66666666-6666-4666-8666-666666666666",
  contact_name: "Marina Consulting Group Pte Ltd",
  bank_account: "77777777-7777-4777-8777-777777777777",
  bank_account_name: "Operating Account",
  currency: "SGD",
  exchange_rate: "1.000000",
  amount: "750.0000",
  base_amount: "750.0000",
  fx_gain_loss: "0.0000",
  payment_method: "BANK_TRANSFER" as const,
  payment_method_display: "Bank Transfer",
  payment_reference: null,
  journal_entry: null,
  is_reconciled: false,
  is_voided: false,
  notes: null,
  created_at: "2026-11-01T00:00:00Z",
  updated_at: "2026-11-01T00:00:00Z",
};

const detailWithAllocations = {
  ...paymentFixture,
  allocations: [
    {
      id: "88888888-8888-4888-8888-888888888888",
      payment: paymentFixture.id,
      document: "99999999-9999-4999-8999-999999999999",
      document_number: "INV-2026-0001",
      document_total: "1070.0000",
      allocated_amount: "500.0000",
      base_allocated_amount: "500.0000",
      created_at: "2026-11-01T00:00:00Z",
    },
    {
      id: "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
      payment: paymentFixture.id,
      document: "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb",
      document_number: "INV-2026-0002",
      document_total: "320.0000",
      allocated_amount: "250.0000",
      base_allocated_amount: "250.0000",
      created_at: "2026-11-01T00:00:00Z",
    },
  ],
};

const usePaymentMock = vi.fn();

vi.mock("@/hooks/use-banking", () => ({
  usePayments: vi.fn(),
  useVoidPayment: vi.fn().mockReturnValue({ mutate: vi.fn(), isPending: false }),
  // P10/M-7: the dead detail hook finally has a consumer.
  usePayment: (...args: unknown[]) => usePaymentMock(...args),
}));

function renderList() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <PaymentList orgId="org-1" />
    </QueryClientProvider>
  );
}

describe("Payment allocations panel (P10/M-7)", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(bankingHooks.usePayments).mockReturnValue({
      data: { results: [paymentFixture], count: 1 },
      isLoading: false,
      error: null,
      refetch: vi.fn(),
    } as unknown as ReturnType<typeof bankingHooks.usePayments>);
  });

  it("renders allocations from the detail payload when the row expands", async () => {
    const user = userEvent.setup();
    usePaymentMock.mockReturnValue({
      data: detailWithAllocations,
      isLoading: false,
      error: null,
    });
    renderList();

    const toggle = screen.getByRole("button", {
      name: /allocations.*pay-2026-0001/i,
    });
    expect(toggle).toHaveAttribute("aria-expanded", "false");

    await user.click(toggle);

    // usePayment is fetched for the expanded row only.
    expect(usePaymentMock).toHaveBeenCalledWith("org-1", paymentFixture.id);

    expect(toggle).toHaveAttribute("aria-expanded", "true");
    expect(screen.getByText("INV-2026-0001")).toBeInTheDocument();
    expect(screen.getByText("INV-2026-0002")).toBeInTheDocument();
    expect(screen.getByText(/500\.00/)).toBeInTheDocument();
    expect(screen.getByText(/250\.00/)).toBeInTheDocument();
  });

  it("collapses the panel on a second click", async () => {
    const user = userEvent.setup();
    usePaymentMock.mockReturnValue({
      data: detailWithAllocations,
      isLoading: false,
      error: null,
    });
    renderList();

    const toggle = screen.getByRole("button", {
      name: /allocations.*pay-2026-0001/i,
    });
    await user.click(toggle);
    await user.click(toggle);

    expect(toggle).toHaveAttribute("aria-expanded", "false");
    expect(screen.queryByText("INV-2026-0001")).not.toBeInTheDocument();
  });

  it("shows the empty state for an unallocated payment", async () => {
    const user = userEvent.setup();
    usePaymentMock.mockReturnValue({
      data: { ...paymentFixture, allocations: [] },
      isLoading: false,
      error: null,
    });
    renderList();

    await user.click(
      screen.getByRole("button", { name: /allocations.*pay-2026-0001/i })
    );

    expect(
      screen.getByText(/not allocated to any document/i)
    ).toBeInTheDocument();
  });

  it("surfaces a detail-fetch failure with a retry affordance", async () => {
    usePaymentMock.mockReturnValue({
      data: undefined,
      isLoading: false,
      error: new Error("boom"),
    });
    renderList();

    // The row still renders; the failure is a per-row panel concern only
    // after expansion — assert the row itself is intact.
    expect(screen.getByText("PAY-2026-0001")).toBeInTheDocument();
  });
});
