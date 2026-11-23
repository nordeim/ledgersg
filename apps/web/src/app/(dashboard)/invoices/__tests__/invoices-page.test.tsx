/**
 * P5/C-5 (part 1) — real invoices list page.
 *
 * RED suite (against the mock page): the page must render REAL rows from
 * useInvoices (backend {results, count} contract), show loading / error /
 * empty states, and never render fabricated data.
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { InvoicesClient } from "../invoices-client";
import * as invoiceHooks from "@/hooks/use-invoices";

vi.mock("@/providers/auth-provider", () => ({
  useAuth: () => ({
    currentOrg: { id: "org-123", name: "Test Org" },
    isLoading: false,
  }),
}));

vi.mock("@/hooks/use-invoices");

const mockInvoice = (overrides: Record<string, unknown> = {}) => ({
  id: "doc-1",
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
  ...overrides,
});

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

describe("InvoicesClient (real data)", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders real rows from useInvoices", async () => {
    vi.mocked(invoiceHooks.useInvoices).mockReturnValue({
      data: {
        results: [
          mockInvoice(),
          mockInvoice({
            id: "doc-2",
            document_number: "INV-000043",
            contact_name: "XYZ Corporation",
            status: "PAID",
            status_display: "Paid",
            total_incl: "12300.0000",
          }),
        ],
        count: 2,
      },
      isLoading: false,
      isError: false,
      error: null,
    } as unknown as ReturnType<typeof invoiceHooks.useInvoices>);

    renderPage();

    expect(await screen.findByText("INV-000042")).toBeInTheDocument();
    expect(screen.getByText("ABC Pte Ltd")).toBeInTheDocument();
    expect(screen.getByText("XYZ Corporation")).toBeInTheDocument();
    // mock data must be gone — these strings only existed in the old fixture
    expect(screen.queryByText("Singapore Tech Solutions")).not.toBeInTheDocument();
    // P9/C-2: the page must ask for invoices only — without the type filter
    // the backend lists EVERY document (quotes and bills as invoices).
    expect(invoiceHooks.useInvoices).toHaveBeenCalledWith(
      expect.anything(),
      expect.objectContaining({ type: "SALES_INVOICE" })
    );
  });

  it("labels a non-invoice document type instead of implying an invoice", async () => {
    // Defensive truth: if any other document type ever reaches this list,
    // it is labelled — not silently rendered as an invoice.
    vi.mocked(invoiceHooks.useInvoices).mockReturnValue({
      data: {
        results: [
          mockInvoice({
            document_type: "SALES_CREDIT_NOTE",
            document_number: "CN-000007",
          }),
        ],
        count: 1,
      },
      isLoading: false,
      isError: false,
      error: null,
    } as unknown as ReturnType<typeof invoiceHooks.useInvoices>);

    renderPage();

    expect(await screen.findByText("CN-000007")).toBeInTheDocument();
    expect(screen.getByText("sales credit note")).toBeInTheDocument();
  });

  it("shows the empty state when the org has no invoices", async () => {
    vi.mocked(invoiceHooks.useInvoices).mockReturnValue({
      data: { results: [], count: 0 },
      isLoading: false,
      isError: false,
      error: null,
    } as unknown as ReturnType<typeof invoiceHooks.useInvoices>);

    renderPage();

    expect(
      await screen.findByText(/no invoices yet/i)
    ).toBeInTheDocument();
  });

  it("shows the error state when the list fails to load", async () => {
    vi.mocked(invoiceHooks.useInvoices).mockReturnValue({
      data: undefined,
      isLoading: false,
      isError: true,
      error: new Error("Network failed"),
    } as unknown as ReturnType<typeof invoiceHooks.useInvoices>);

    renderPage();

    expect(
      await screen.findByText(/failed to load invoices/i)
    ).toBeInTheDocument();
  });

  it("shows a loading state while fetching", () => {
    vi.mocked(invoiceHooks.useInvoices).mockReturnValue({
      data: undefined,
      isLoading: true,
      isError: false,
      error: null,
    } as unknown as ReturnType<typeof invoiceHooks.useInvoices>);

    renderPage();

    expect(screen.getByText(/loading invoices/i)).toBeInTheDocument();
  });
});
