/**
 * P8/Q-4: the quotes pages are real — the list reads SALES_QUOTE documents
 * (via the ?type= filter key the backend reads), conversion fires the
 * convert mutation, and the shared detail client in quote mode gates the
 * invoice-only surfaces.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, cleanup } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { QuotesClient } from "../quotes-client";
import * as invoiceHooks from "@/hooks/use-invoices";
import * as authModule from "@/providers/auth-provider";

vi.mock("@/providers/auth-provider", () => ({
  useAuth: vi.fn(),
}));

vi.mock("@/hooks/use-invoices", () => ({
  useInvoices: vi.fn(),
  useConvertQuote: vi.fn(),
}));

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn() }),
}));

/* eslint-disable @typescript-eslint/no-explicit-any -- test mocks */
function renderPage() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  render(
    <QueryClientProvider client={queryClient}>
      <QuotesClient />
    </QueryClientProvider>
  );
}

const ORG = { id: "org-1", name: "Quotes Org", gst_registered: true };

describe("QuotesClient (P8/Q-4)", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(authModule.useAuth).mockReturnValue({
      currentOrg: ORG,
      isLoading: false,
    } as unknown as ReturnType<typeof authModule.useAuth>);
    vi.mocked(invoiceHooks.useConvertQuote).mockReturnValue({
      mutate: vi.fn(),
      isPending: false,
    } as any);
  });

  afterEach(() => cleanup());

  it("requests SALES_QUOTE documents with the type filter key the backend reads", () => {
    vi.mocked(invoiceHooks.useInvoices).mockReturnValue({
      data: { results: [], count: 0 },
      isLoading: false,
      isError: false,
    } as any);

    renderPage();

    // P26: the page param rides with the type filter (limit 20, offset 0).
    expect(invoiceHooks.useInvoices).toHaveBeenCalledWith(
      "org-1",
      { type: "SALES_QUOTE" },
      undefined,
      expect.objectContaining({ limit: 20, offset: 0 })
    );
  });

  it("renders quote rows with a Convert action on DRAFT/SENT only", async () => {
    vi.mocked(invoiceHooks.useInvoices).mockReturnValue({
      data: {
        results: [
          {
            id: "q1",
            document_number: "QT-00001",
            contact_name: "Acme Pte Ltd",
            issue_date: "2024-03-01",
            due_date: "2024-04-01",
            status: "DRAFT",
            total_incl: "1090.0000",
          },
          {
            id: "q2",
            document_number: "QT-00002",
            contact_name: "Beta Ltd",
            issue_date: "2024-03-02",
            due_date: "2024-04-02",
            status: "APPROVED",
            // P9/C-6: CONVERTED means the link exists — an approved quote
            // WITHOUT a linked invoice is just APPROVED (the badge gates on
            // related_document_id now, not the status).
            related_document_id: "inv-from-q2",
            total_incl: "500.0000",
          },
          {
            id: "q3",
            document_number: "QT-00003",
            contact_name: "Gamma Pte Ltd",
            issue_date: "2024-03-03",
            due_date: "2024-04-03",
            status: "APPROVED",
            related_document_id: null,
            total_incl: "300.0000",
          },
        ],
        count: 3,
      },
      isLoading: false,
      isError: false,
    } as any);

    renderPage();

    expect(await screen.findByText("QT-00001")).toBeInTheDocument();
    expect(screen.getByText("Acme Pte Ltd")).toBeInTheDocument();
    // Converted quotes show the truthful state, not a Convert action
    expect(screen.getByText("CONVERTED")).toBeInTheDocument();
    // An approved-but-unconverted quote shows APPROVED (not CONVERTED)
    expect(screen.getByText("APPROVED")).toBeInTheDocument();
    const convertButtons = screen.getAllByRole("button", { name: /convert/i });
    // only the DRAFT row — the engine converts DRAFT/SENT quotes; an
    // APPROVED quote without a link shows APPROVED but cannot convert
    expect(convertButtons).toHaveLength(1);
  });

  it("fires the convert mutation when Convert is clicked", async () => {
    const mutate = vi.fn();
    vi.mocked(invoiceHooks.useConvertQuote).mockReturnValue({
      mutate,
      isPending: false,
    } as any);
    vi.mocked(invoiceHooks.useInvoices).mockReturnValue({
      data: {
        results: [
          {
            id: "q1",
            document_number: "QT-00001",
            contact_name: "Acme",
            issue_date: "2024-03-01",
            due_date: "2024-04-01",
            status: "SENT",
            total_incl: "109.0000",
          },
        ],
        count: 1,
      },
      isLoading: false,
      isError: false,
    } as any);

    renderPage();
    await userEvent.click(
      await screen.findByRole("button", { name: /convert/i })
    );
    expect(mutate).toHaveBeenCalledWith("q1");
  });

  // P26: the frontend pagination wiring — the quotes surface rides the
  // same useInvoices page param and renders the shared control.
  it("renders the shared TablePagination with the truthful total (P26)", () => {
    vi.mocked(invoiceHooks.useInvoices).mockReturnValue({
      data: {
        results: [
          {
            id: "q1",
            document_number: "QT-00001",
            contact_name: "Acme",
            issue_date: "2024-03-01",
            due_date: "2024-04-01",
            status: "SENT",
            total_incl: "109.0000",
          },
        ],
        count: 25,
      },
      isLoading: false,
      isError: false,
      isFetching: false,
    } as any);

    renderPage();

    const pagination = screen.getByRole("navigation", { name: "Pagination" });
    expect(pagination).toBeInTheDocument();
    expect(screen.getByText("Showing 1–20 of 25 rows")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Next page" })).toBeEnabled();
  });

  it("shows the no-org state, never a fake failure", () => {
    vi.mocked(authModule.useAuth).mockReturnValue({
      currentOrg: null,
      isLoading: false,
    } as unknown as ReturnType<typeof authModule.useAuth>);
    vi.mocked(invoiceHooks.useInvoices).mockReturnValue({
      data: undefined,
      isLoading: false,
      isError: false,
    } as any);

    renderPage();
    expect(screen.getByText(/no organisation selected/i)).toBeInTheDocument();
    expect(screen.queryByText(/failed to load/i)).not.toBeInTheDocument();
  });
});
