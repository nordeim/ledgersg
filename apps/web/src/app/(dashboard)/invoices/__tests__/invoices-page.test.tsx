/**
 * P5/C-5 (part 1) — real invoices list page.
 *
 * RED suite (against the mock page): the page must render REAL rows from
 * useInvoices (backend {results, count} contract), show loading / error /
 * empty states, and never render fabricated data.
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { act, fireEvent, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
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
      expect.objectContaining({ type: "SALES_INVOICE" }),
      undefined,
      expect.objectContaining({ limit: 20, offset: 0 })
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

  // ------------------------------------------------------------------
  // P26: the frontend pagination wiring — the shared TablePagination on
  // the invoices surface + the server-side search migration.
  // ------------------------------------------------------------------

  it("renders the shared TablePagination with the truthful summary (P26)", async () => {
    vi.mocked(invoiceHooks.useInvoices).mockReturnValue({
      data: {
        results: [mockInvoice(), mockInvoice({ id: "doc-2", document_number: "INV-000043" })],
        count: 25,
      },
      isLoading: false,
      isError: false,
      error: null,
      isFetching: false,
    } as unknown as ReturnType<typeof invoiceHooks.useInvoices>);

    renderPage();

    // The nav landmark + the truthful page-math summary: the "of 25"
    // TOTAL (the pre-P26 page showed only the fetched rows' count).
    const pagination = screen.getByRole("navigation", { name: "Pagination" });
    expect(pagination).toBeInTheDocument();
    expect(screen.getByText("Showing 1–20 of 25 rows")).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Previous page" })
    ).toBeDisabled();
    expect(screen.getByRole("button", { name: "Next page" })).toBeEnabled();
  });

  it("drives the search server-side through the hook's search filter (P26)", async () => {
    vi.useFakeTimers();
    try {
      vi.mocked(invoiceHooks.useInvoices).mockReturnValue({
        data: { results: [], count: 0 },
        isLoading: false,
        isError: false,
        error: null,
        isFetching: false,
      } as unknown as ReturnType<typeof invoiceHooks.useInvoices>);

      renderPage();

      const searchBox = screen.getByLabelText(
        "Search invoices by number or customer"
      );
      fireEvent.change(searchBox, { target: { value: "INV-000042" } });

      // Before the 300ms debounce elapses the search has NOT been sent.
      expect(invoiceHooks.useInvoices).not.toHaveBeenCalledWith(
        expect.anything(),
        expect.objectContaining({ search: "INV-000042" }),
        expect.anything(),
        expect.anything()
      );

      await act(async () => {
        vi.advanceTimersByTime(350);
      });

      // The search rides the hook's filters — the SERVER filters the
      // set (the client-side filter only ever saw the fetched page).
      expect(invoiceHooks.useInvoices).toHaveBeenCalledWith(
        expect.anything(),
        expect.objectContaining({ type: "SALES_INVOICE", search: "INV-000042" }),
        undefined,
        expect.objectContaining({ limit: 20, offset: 0 })
      );
    } finally {
      vi.useRealTimers();
    }
  });

  it("keeps the pagination controls on a page beyond the end (P26, the P25 pattern)", async () => {
    // The mock shrinks the set once the reader walks past offset 40
    // (the realistic sequence: rows deleted server-side between
    // fetches) — count 40, an empty page at offset 40.
    vi.mocked(invoiceHooks.useInvoices).mockImplementation(
      ((
        _orgId: unknown,
        _filters: unknown,
        _options: unknown,
        page: { offset: number } | undefined
      ) => ({
        data:
          (page?.offset ?? 0) >= 40
            ? { results: [], count: 40 }
            : { results: [mockInvoice()], count: 60 },
        isLoading: false,
        isError: false,
        error: null,
        isFetching: false,
      })) as unknown as typeof invoiceHooks.useInvoices
    );

    renderPage();

    const user = userEvent.setup();
    await user.click(screen.getByRole("button", { name: /next page/i }));
    await user.click(screen.getByRole("button", { name: /next page/i }));

    // count > 0 with an empty page: the controls stay (the way back),
    // never the false "No invoices yet".
    expect(
      await screen.findByText("Showing 0–0 of 40 rows")
    ).toBeInTheDocument();
    expect(screen.queryByText(/no invoices yet/i)).not.toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: /previous page/i })
    ).not.toBeDisabled();
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
