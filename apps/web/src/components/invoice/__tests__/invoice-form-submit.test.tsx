/**
 * Invoice Form Submit Tests (TDD — P3/D-1)
 *
 * The form's onSubmit was a stub (console.log + setTimeout + mock UUID).
 * These tests pin the real contract:
 *   submit -> create contact -> create document -> onSuccess(created.id)
 * including the error banner path. Mutations are mocked at the hook
 * modules (the adapter itself is covered by invoice-submit.test.ts).
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import React from "react";
import { screen, waitFor, render, fireEvent } from "@/__tests__/utils";
import userEvent from "@testing-library/user-event";
import { InvoiceForm } from "../invoice-form";
import { createEmptyInvoice, type InvoiceInput } from "@/shared/schemas/invoice";

const createContactMock = vi.fn();
const createInvoiceMock = vi.fn();

vi.mock("@/hooks/use-contacts", () => ({
  useCreateContact: () => ({
    mutateAsync: createContactMock,
  }),
}));

vi.mock("@/hooks/use-invoices", () => ({
  useCreateInvoice: () => ({
    mutateAsync: createInvoiceMock,
  }),
}));

vi.mock("@/hooks/use-tax-codes", () => ({
  useTaxCodes: () => ({
    data: [
      { id: "sr-row", code: "SR", name: "Standard-Rated Supply", rate: "0.0900" },
    ],
    isLoading: false,
    isError: false,
  }),
  FALLBACK_TAX_CODES: [
    { id: "SR", code: "SR", name: "SR", rate: "0.09" },
  ],
}));

vi.mock("@/hooks/use-accounts", () => ({
  useAccounts: () => ({
    data: [
      { id: "acc-4000", code: "4000", name: "Sales Revenue", account_type: "REVENUE" },
    ],
    isLoading: false,
    isError: false,
  }),
  useRevenueAccounts: () => ({
    data: [
      { id: "acc-4000", code: "4000", name: "Sales Revenue", account_type: "REVENUE" },
    ],
    isLoading: false,
    isError: false,
  }),
}));

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn() }),
}));

vi.mock("@/providers/auth-provider", () => ({
  useAuth: () => ({
    currentOrg: { id: "org-1", name: "Test Org" },
    isAuthenticated: true,
    isLoading: false,
  }),
}));

async function fillValidForm(user: ReturnType<typeof userEvent.setup>) {
  await user.type(screen.getByLabelText("Customer Name"), "Acme Pte Ltd");
  await user.type(screen.getByLabelText("Line description"), "Consulting");
  await user.clear(screen.getByLabelText("Quantity"));
  await user.type(screen.getByLabelText("Quantity"), "2");
  await user.clear(screen.getByLabelText("Unit price"));
  await user.type(screen.getByLabelText("Unit price"), "100");

  // select the posting account (Radix select) via keyboard — ArrowDown
  // highlights the first option, Enter selects it (userEvent pointer
  // interactions are refused on jsdom's animated select portal)
  const accountSelect = screen.getByRole("combobox", { name: "Account" });
  await user.click(accountSelect);
  await user.keyboard("{ArrowDown}{Enter}");
}

describe("InvoiceForm submit", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("creates the contact then the document and calls onSuccess with the created id", async () => {
    const onSuccess = vi.fn();
    renderForm({ onSuccess });

    const user = userEvent.setup();
    await fillValidForm(user);

    createContactMock.mockResolvedValueOnce({ id: "contact-uuid-9" });
    createInvoiceMock.mockResolvedValueOnce({ id: "doc-uuid-9", status: "DRAFT" });

    await user.click(screen.getByRole("button", { name: /send invoice/i }));

    await waitFor(() => expect(onSuccess).toHaveBeenCalledWith("doc-uuid-9"));

    expect(createContactMock).toHaveBeenCalledTimes(1);
    expect(createContactMock).toHaveBeenCalledWith(
      expect.objectContaining({
        contact_type: "CUSTOMER",
        name: "Acme Pte Ltd",
        is_customer: true,
      })
    );

    expect(createInvoiceMock).toHaveBeenCalledTimes(1);
    const docPayload = createInvoiceMock.mock.calls[0][0];
    expect(docPayload).toMatchObject({
      document_type: "SALES_INVOICE",
      contact_id: "contact-uuid-9",
    });
    expect(docPayload.lines[0]).toMatchObject({
      account_id: "acc-4000",
      description: "Consulting",
      quantity: "2",
      // MoneyInput normalises to the 4dp internal precision
      unit_price: "100.0000",
      tax_code_id: "sr-row",
    });
    // computed preview fields are server-recalculated, never sent
    expect(docPayload.lines[0]).not.toHaveProperty("line_subtotal");
    expect(docPayload).not.toHaveProperty("invoice_number");
  });

  it("shows the error banner when the document create fails", async () => {
    const onSuccess = vi.fn();
    renderForm({ onSuccess });

    const user = userEvent.setup();
    await fillValidForm(user);

    createContactMock.mockResolvedValueOnce({ id: "contact-uuid-9" });
    createInvoiceMock.mockRejectedValueOnce(
      new Error("No open fiscal period found for date 2024-06-15.")
    );

    await user.click(screen.getByRole("button", { name: /send invoice/i }));

    await waitFor(() =>
      expect(screen.getByRole("alert")).toHaveTextContent(/fiscal period/i)
    );
    expect(onSuccess).not.toHaveBeenCalled();
  });

  it("does not submit when a line has no posting account", async () => {
    const onSuccess = vi.fn();
    renderForm({ onSuccess });

    const user = userEvent.setup();
    // fill everything EXCEPT the account selection
    await user.type(screen.getByLabelText("Customer Name"), "Acme Pte Ltd");
    await user.type(screen.getByLabelText("Line description"), "Consulting");
    await user.clear(screen.getByLabelText("Quantity"));
    await user.type(screen.getByLabelText("Quantity"), "2");
    await user.clear(screen.getByLabelText("Unit price"));
    await user.type(screen.getByLabelText("Unit price"), "100");

    await user.click(screen.getByRole("button", { name: /send invoice/i }));

    await waitFor(() =>
      expect(screen.getByRole("alert")).toHaveTextContent(/no posting account/i)
    );
    expect(createContactMock).not.toHaveBeenCalled();
    expect(createInvoiceMock).not.toHaveBeenCalled();
    expect(onSuccess).not.toHaveBeenCalled();
  });
});

function renderForm(props: { onSuccess?: (id: string) => void } = {}) {
  const initialData = createEmptyInvoice() as InvoiceInput;
  return render(<InvoiceForm initialData={initialData} onSuccess={props.onSuccess} />);
}
