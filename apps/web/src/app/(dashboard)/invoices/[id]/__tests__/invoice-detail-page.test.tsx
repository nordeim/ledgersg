/**
 * P6/C-5 — real invoice detail page.
 *
 * RED suite (against the mock page): the page must render the REAL
 * document from useInvoice (backend detail serializer contract, incl. the
 * P6/F-11 amount_paid/amount_due fields), show loading / error states,
 * expose the real mutations, and never render fabricated data.
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor, cleanup } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { InvoiceDetailClient } from "../invoice-detail-client";
import * as invoiceHooks from "@/hooks/use-invoices";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn() }),
}));

vi.mock("@/providers/auth-provider", () => ({
  useAuth: () => ({
    currentOrg: { id: "org-123", name: "Test Org" },
    isLoading: false,
  }),
}));

vi.mock("@/hooks/use-invoices");

const mockMutation = () => ({
  mutate: vi.fn(),
  mutateAsync: vi.fn(),
  isPending: false,
  isError: false,
  error: null,
});

const mockDetail = (overrides: Record<string, unknown> = {}) => ({
  id: "doc-1",
  document_type: "SALES_INVOICE",
  document_number: "INV-000042",
  contact: {
    id: "contact-1",
    name: "Marina Consulting Group Pte Ltd",
    contact_type: "CUSTOMER",
    email: "accounts@marina.example",
    phone: "+65 6123 4567",
    city: "Singapore",
    country: "SG",
  },
  issue_date: "2026-11-01",
  due_date: "2026-12-01",
  reference: "PO-2026-001",
  notes: "Payment due within 30 days.",
  status: "APPROVED",
  lines: [
    {
      id: "line-1",
      line_number: 1,
      description: "Consulting services retainer",
      account_id: "acc-1",
      account_code: "4100",
      account_name: "Consulting Revenue",
      quantity: "5.0000",
      unit_price: "250.0000",
      discount_pct: "0.0000",
      discount_amount: "0.0000",
      line_amount: "1250.0000",
      tax_code_id: "tax-1",
      tax_code_code: "SR",
      tax_rate: "9.0000",
      gst_amount: "112.5000",
      total_amount: "1362.5000",
      is_bcrs_deposit: false,
    },
    {
      id: "line-2",
      line_number: 2,
      description: "Software implementation",
      account_id: "acc-1",
      account_code: "4100",
      account_name: "Consulting Revenue",
      quantity: "2.0000",
      unit_price: "425.0000",
      discount_pct: "0.0000",
      discount_amount: "0.0000",
      line_amount: "850.0000",
      tax_code_id: "tax-1",
      tax_code_code: "SR",
      tax_rate: "9.0000",
      gst_amount: "76.5000",
      total_amount: "926.5000",
      is_bcrs_deposit: false,
    },
  ],
  total_excl: "2100.0000",
  gst_total: "189.0000",
  total_incl: "2289.0000",
  currency: "SGD",
  amount_paid: "400.0000",
  amount_due: "1889.0000",
  journal_entry_id: "je-1",
  peppol_status: "NOT_SENT",
  approved_at: "2026-11-02T10:00:00Z",
  voided_at: null,
  status_history: [],
  created_at: "2026-11-01T09:00:00Z",
  updated_at: "2026-11-02T10:00:00Z",
  ...overrides,
});

function renderPage(id = "doc-1") {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <InvoiceDetailClient id={id} />
    </QueryClientProvider>
  );
}

describe("InvoiceDetailClient (real data)", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(invoiceHooks.useApproveInvoice).mockReturnValue(
      mockMutation() as unknown as ReturnType<typeof invoiceHooks.useApproveInvoice>
    );
    vi.mocked(invoiceHooks.useVoidInvoice).mockReturnValue(
      mockMutation() as unknown as ReturnType<typeof invoiceHooks.useVoidInvoice>
    );
    vi.mocked(invoiceHooks.useSendInvoice).mockReturnValue(
      mockMutation() as unknown as ReturnType<typeof invoiceHooks.useSendInvoice>
    );
    vi.mocked(invoiceHooks.useInvoicePDF).mockReturnValue(
      mockMutation() as unknown as ReturnType<typeof invoiceHooks.useInvoicePDF>
    );
    vi.mocked(invoiceHooks.useSendInvoiceNow).mockReturnValue(
      mockMutation() as unknown as ReturnType<typeof invoiceHooks.useSendInvoiceNow>
    );
    vi.mocked(invoiceHooks.useInvoiceNowStatus).mockReturnValue({
      data: undefined,
      isLoading: false,
      isError: false,
      error: null,
    } as unknown as ReturnType<typeof invoiceHooks.useInvoiceNowStatus>);
  });

  it("renders the real document number, contact and status from useInvoice", async () => {
    vi.mocked(invoiceHooks.useInvoice).mockReturnValue({
      data: mockDetail(),
      isLoading: false,
      isError: false,
      error: null,
    } as unknown as ReturnType<typeof invoiceHooks.useInvoice>);

    renderPage();

    expect((await screen.findAllByText("INV-000042")).length).toBeGreaterThan(0);
    expect(
      await screen.findByText("Marina Consulting Group Pte Ltd")
    ).toBeInTheDocument();
    // the mock fixture data must be gone
    expect(screen.queryByText("Acme Corporation Pte Ltd")).not.toBeInTheDocument();
    expect(screen.queryByText("Ledger SG Pte Ltd")).not.toBeInTheDocument();
  });

  it("renders the real lines from the detail serializer", async () => {
    vi.mocked(invoiceHooks.useInvoice).mockReturnValue({
      data: mockDetail(),
      isLoading: false,
      isError: false,
      error: null,
    } as unknown as ReturnType<typeof invoiceHooks.useInvoice>);

    renderPage();

    expect(
      await screen.findByText("Consulting services retainer")
    ).toBeInTheDocument();
    expect(screen.getByText("Software implementation")).toBeInTheDocument();
    // line amounts (quantity x unit price)
    expect(screen.getAllByText("1,250.00").length).toBeGreaterThan(0);
    expect(screen.getAllByText("850.00").length).toBeGreaterThan(0);
  });

  it("renders the totals incl. GST", async () => {
    vi.mocked(invoiceHooks.useInvoice).mockReturnValue({
      data: mockDetail(),
      isLoading: false,
      isError: false,
      error: null,
    } as unknown as ReturnType<typeof invoiceHooks.useInvoice>);

    renderPage();

    expect((await screen.findAllByText("INV-000042")).length).toBeGreaterThan(0);
    expect(screen.getAllByText("2,100.00").length).toBeGreaterThan(0);
    expect(screen.getAllByText("189.00").length).toBeGreaterThan(0);
    expect(screen.getAllByText("2,289.00").length).toBeGreaterThan(0);
  });

  it("renders the payment state (P6/F-11 amount_paid / amount_due)", async () => {
    vi.mocked(invoiceHooks.useInvoice).mockReturnValue({
      data: mockDetail(),
      isLoading: false,
      isError: false,
      error: null,
    } as unknown as ReturnType<typeof invoiceHooks.useInvoice>);

    renderPage();

    expect((await screen.findAllByText("INV-000042")).length).toBeGreaterThan(0);
    expect(screen.getByText(/amount paid/i)).toBeInTheDocument();
    expect(screen.getByText(/amount due/i)).toBeInTheDocument();
    expect(screen.getAllByText("400.00").length).toBeGreaterThan(0);
    expect(screen.getAllByText("1,889.00").length).toBeGreaterThan(0);
  });

  it("shows the loading state while the detail is fetching", () => {
    vi.mocked(invoiceHooks.useInvoice).mockReturnValue({
      data: undefined,
      isLoading: true,
      isError: false,
      error: null,
    } as unknown as ReturnType<typeof invoiceHooks.useInvoice>);

    renderPage();

    expect(screen.getByText(/loading/i)).toBeInTheDocument();
  });

  it("shows the error state when the detail fails to load", async () => {
    vi.mocked(invoiceHooks.useInvoice).mockReturnValue({
      data: undefined,
      isLoading: false,
      isError: true,
      error: new Error("Network error"),
    } as unknown as ReturnType<typeof invoiceHooks.useInvoice>);

    renderPage();

    expect(
      await screen.findByText(/failed to load invoice/i)
    ).toBeInTheDocument();
  });

  it("exposes the approve action for a DRAFT document", async () => {
    vi.mocked(invoiceHooks.useInvoice).mockReturnValue({
      data: mockDetail({ status: "DRAFT", approved_at: null }),
      isLoading: false,
      isError: false,
      error: null,
    } as unknown as ReturnType<typeof invoiceHooks.useInvoice>);

    const approve = mockMutation();
    vi.mocked(invoiceHooks.useApproveInvoice).mockReturnValue(
      approve as unknown as ReturnType<typeof invoiceHooks.useApproveInvoice>
    );

    renderPage();

    const button = await screen.findByRole("button", { name: /approve/i });
    await userEvent.click(button);

    await waitFor(() => expect(approve.mutate).toHaveBeenCalled());
  });
});

describe("InvoiceDetailClient — void flow (P7/F-1, F-8)", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(invoiceHooks.useApproveInvoice).mockReturnValue(
      mockMutation() as unknown as ReturnType<typeof invoiceHooks.useApproveInvoice>
    );
    vi.mocked(invoiceHooks.useSendInvoice).mockReturnValue(
      mockMutation() as unknown as ReturnType<typeof invoiceHooks.useSendInvoice>
    );
  });

  async function renderApproved() {
    vi.mocked(invoiceHooks.useInvoice).mockReturnValue({
      data: mockDetail({ status: "APPROVED" }),
      isLoading: false,
      isError: false,
      error: null,
    } as unknown as ReturnType<typeof invoiceHooks.useInvoice>);
    const voidMutation = mockMutation();
    vi.mocked(invoiceHooks.useVoidInvoice).mockReturnValue(
      voidMutation as unknown as ReturnType<typeof invoiceHooks.useVoidInvoice>
    );
    renderPage();
    await screen.findAllByText("INV-000042");
    return voidMutation;
  }

  it("opens a reason dialog when Void is clicked (never a bare mutate)", async () => {
    const voidMutation = await renderApproved();

    await userEvent.click(screen.getByRole("button", { name: /void/i }));

    // The dialog is open with a labelled reason field; the mutation has NOT
    // fired yet (the pre-P7 page called mutate("") immediately — always a
    // 400 because the backend requires a non-empty reason).
    expect(await screen.findByLabelText(/reason for voiding/i)).toBeInTheDocument();
    expect(voidMutation.mutate).not.toHaveBeenCalled();
  });

  it("renders the Void action only for statuses the engine accepts (P8/G-3)", async () => {
    // PAID and VOID: no Void button (a paid invoice needs a credit note;
    // the pre-P8 gate rendered a button that always 400'd).
    for (const notVoidable of ["PAID", "VOID"]) {
      cleanup();
      vi.mocked(invoiceHooks.useInvoice).mockReturnValue({
        data: mockDetail({ status: notVoidable }),
        isLoading: false,
        isError: false,
        error: null,
      } as unknown as ReturnType<typeof invoiceHooks.useInvoice>);
      renderPage();
      await screen.findAllByText("INV-000042");
      expect(
        screen.queryByRole("button", { name: /^void$/i })
      ).not.toBeInTheDocument();
    }

    // DRAFT (and the other accepted sources): the button is available.
    for (const voidable of ["DRAFT", "OVERDUE"]) {
      cleanup();
      vi.mocked(invoiceHooks.useInvoice).mockReturnValue({
        data: mockDetail({ status: voidable }),
        isLoading: false,
        isError: false,
        error: null,
      } as unknown as ReturnType<typeof invoiceHooks.useInvoice>);
      renderPage();
      await screen.findAllByText("INV-000042");
      expect(
        screen.getByRole("button", { name: /^void$/i })
      ).toBeInTheDocument();
    }
  });

  it("blocks submission of an empty reason (client-side, native + message)", async () => {
    const voidMutation = await renderApproved();

    await userEvent.click(screen.getByRole("button", { name: /void/i }));
    const confirm = await screen.findByRole("button", { name: /void invoice/i });
    await userEvent.click(confirm);

    // No API call without a reason.
    expect(voidMutation.mutate).not.toHaveBeenCalled();
  });

  it("submits the typed reason to the void mutation", async () => {
    const voidMutation = await renderApproved();

    await userEvent.click(screen.getByRole("button", { name: /void/i }));
    const reason = await screen.findByLabelText(/reason for voiding/i);
    await userEvent.type(reason, "Wrong amount billed");
    await userEvent.click(screen.getByRole("button", { name: /void invoice/i }));

    await waitFor(() =>
      expect(voidMutation.mutate).toHaveBeenCalledWith(
        "Wrong amount billed",
        expect.anything()
      )
    );
    expect(voidMutation.mutate.mock.calls[0][0]).toBe("Wrong amount billed");
  });

  it("can cancel the void dialog without any API call", async () => {
    const voidMutation = await renderApproved();

    await userEvent.click(screen.getByRole("button", { name: /void/i }));
    await userEvent.type(await screen.findByLabelText(/reason for voiding/i), "oops");
    await userEvent.click(screen.getByRole("button", { name: /cancel/i }));

    expect(voidMutation.mutate).not.toHaveBeenCalled();
    expect(screen.queryByLabelText(/reason for voiding/i)).not.toBeInTheDocument();
  });
});

describe("InvoiceDetailClient — PDF + InvoiceNow actions (P7/F-13)", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(invoiceHooks.useApproveInvoice).mockReturnValue(
      mockMutation() as unknown as ReturnType<typeof invoiceHooks.useApproveInvoice>
    );
    vi.mocked(invoiceHooks.useVoidInvoice).mockReturnValue(
      mockMutation() as unknown as ReturnType<typeof invoiceHooks.useVoidInvoice>
    );
    vi.mocked(invoiceHooks.useSendInvoice).mockReturnValue(
      mockMutation() as unknown as ReturnType<typeof invoiceHooks.useSendInvoice>
    );
    vi.mocked(invoiceHooks.useInvoiceNowStatus).mockReturnValue({
      data: undefined,
      isLoading: false,
      isError: false,
      error: null,
    } as unknown as ReturnType<typeof invoiceHooks.useInvoiceNowStatus>);
  });

  it("exposes a PDF download that goes through the api-client blob path", async () => {
    vi.mocked(invoiceHooks.useInvoice).mockReturnValue({
      data: mockDetail({ status: "APPROVED" }),
      isLoading: false,
      isError: false,
      error: null,
    } as unknown as ReturnType<typeof invoiceHooks.useInvoice>);
    const pdf = mockMutation();
    vi.mocked(invoiceHooks.useInvoicePDF).mockReturnValue(
      pdf as unknown as ReturnType<typeof invoiceHooks.useInvoicePDF>
    );

    renderPage();
    const button = await screen.findByRole("button", { name: /^pdf$/i });
    await userEvent.click(button);

    expect(pdf.mutate).toHaveBeenCalled();
  });

  it("shows the InvoiceNow send action only for APPROVED documents (P8/G-8)", async () => {
    // DRAFT and every non-APPROVED status: no InvoiceNow button — the
    // backend refuses anything but APPROVED, so the old !isDraft &&
    // !isVoid gate rendered buttons that always 400'd.
    for (const notEligible of ["DRAFT", "SENT", "PARTIALLY_PAID", "PAID", "OVERDUE"]) {
      cleanup();
      vi.mocked(invoiceHooks.useInvoice).mockReturnValue({
        data: mockDetail({ status: notEligible }),
        isLoading: false,
        isError: false,
        error: null,
      } as unknown as ReturnType<typeof invoiceHooks.useInvoice>);
      const sendNow = mockMutation();
      vi.mocked(invoiceHooks.useSendInvoiceNow).mockReturnValue(
        sendNow as unknown as ReturnType<typeof invoiceHooks.useSendInvoiceNow>
      );

      renderPage();
      await screen.findAllByText("INV-000042");
      expect(
        screen.queryByRole("button", { name: /send via invoicenow/i })
      ).not.toBeInTheDocument();
    }

    // APPROVED: the button fires the real transmission mutation
    const sendNow = mockMutation();
    vi.mocked(invoiceHooks.useSendInvoiceNow).mockReturnValue(
      sendNow as unknown as ReturnType<typeof invoiceHooks.useSendInvoiceNow>
    );
    vi.mocked(invoiceHooks.useInvoice).mockReturnValue({
      data: mockDetail({ status: "APPROVED" }),
      isLoading: false,
      isError: false,
      error: null,
    } as unknown as ReturnType<typeof invoiceHooks.useInvoice>);

    renderPage();
    const button = await screen.findByRole("button", { name: /send via invoicenow/i });
    await userEvent.click(button);
    expect(sendNow.mutate).toHaveBeenCalled();
  });

  it("surfaces a non-NOT_SENT InvoiceNow transmission status badge", async () => {
    vi.mocked(invoiceHooks.useInvoice).mockReturnValue({
      data: mockDetail({ status: "APPROVED" }),
      isLoading: false,
      isError: false,
      error: null,
    } as unknown as ReturnType<typeof invoiceHooks.useInvoice>);
    vi.mocked(invoiceHooks.useInvoiceNowStatus).mockReturnValue({
      data: { status: "DELIVERED", logs: [] },
      isLoading: false,
      isError: false,
      error: null,
    } as unknown as ReturnType<typeof invoiceHooks.useInvoiceNowStatus>);

    renderPage();
    expect(await screen.findByText(/invoicenow: delivered/i)).toBeInTheDocument();
  });
});
