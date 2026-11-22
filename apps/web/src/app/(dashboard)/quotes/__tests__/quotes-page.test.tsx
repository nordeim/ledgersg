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

    expect(invoiceHooks.useInvoices).toHaveBeenCalledWith(
      "org-1",
      { type: "SALES_QUOTE" }
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
            status: "APPROVED", // converted
            total_incl: "500.0000",
          },
        ],
        count: 2,
      },
      isLoading: false,
      isError: false,
    } as any);

    renderPage();

    expect(await screen.findByText("QT-00001")).toBeInTheDocument();
    expect(screen.getByText("Acme Pte Ltd")).toBeInTheDocument();
    // Converted quotes show the truthful state, not a Convert action
    expect(screen.getByText("CONVERTED")).toBeInTheDocument();
    const convertButtons = screen.getAllByRole("button", { name: /convert/i });
    expect(convertButtons).toHaveLength(1); // only the DRAFT row
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
