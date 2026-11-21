/**
 * InvoiceLineRow Tests (TDD — P3/D-1 wiring, D-3 server-effective rates)
 *
 * Validates:
 * - the per-line Account select is populated from the org's accounts and
 *   is required for submission (backend `add_line` contract)
 * - the tax-code select renders the SERVER-RESOLVED rows (code + effective
 *   rate) when provided, falling back to the static list otherwise
 * - the preview uses the server rate in force, not the hardcoded 9% map
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import React from "react";
import { screen, waitFor, render } from "@/__tests__/utils";
import userEvent from "@testing-library/user-event";
import { useForm, FormProvider } from "react-hook-form";
import { InvoiceLineRow } from "../invoice-line-row";
import { createEmptyInvoice, type InvoiceInput } from "@/shared/schemas/invoice";
import type { ResolvedTaxCode } from "@/hooks/use-tax-codes";

function TestFormProvider({ children }: { children: React.ReactNode }) {
  const methods = useForm<InvoiceInput>({
    defaultValues: createEmptyInvoice(),
    mode: "onChange",
  });
  return <FormProvider {...methods}>{children}</FormProvider>;
}

const accounts = [
  { id: "acc-4000", code: "4000", name: "Sales Revenue" },
  { id: "acc-4100", code: "4100", name: "Service Revenue" },
];

const serverTaxCodes: ResolvedTaxCode[] = [
  { id: "sr-row", code: "SR", name: "Standard-Rated Supply", rate: "0.0800" },
  { id: "zr-row", code: "ZR", name: "Zero-Rated Supply", rate: "0.0000" },
];

function renderLineRow(props: Partial<Parameters<typeof InvoiceLineRow>[0]> = {}) {
  const onRemove = vi.fn();
  const utils = render(
    <TestFormProvider>
      <InvoiceLineRow
        index={0}
        isGSTRegistered={true}
        onRemove={onRemove}
        accounts={accounts}
        taxCodes={serverTaxCodes}
        {...props}
      />
    </TestFormProvider>
  );
  return { ...utils, onRemove };
}

describe("InvoiceLineRow", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders the per-line account select populated with the org accounts", async () => {
    renderLineRow();

    const accountSelect = screen.getByRole("combobox", { name: "Account" });
    expect(accountSelect).toBeInTheDocument();

    const user = userEvent.setup();
    await user.click(accountSelect);
    expect(await screen.findByText("4000 · Sales Revenue")).toBeInTheDocument();
    expect(screen.getByText("4100 · Service Revenue")).toBeInTheDocument();
  });

  it("renders server-resolved tax codes with their effective rates", async () => {
    renderLineRow();

    const taxSelect = screen.getByRole("combobox", { name: "Tax code" });
    const user = userEvent.setup();
    await user.click(taxSelect);

    // Radix renders the selected label in the trigger AND the option list
    const srOptions = await screen.findAllByText(/SR · 8%/);
    expect(srOptions.length).toBeGreaterThanOrEqual(1);
    expect(await screen.findAllByText(/ZR · 0%/)).toHaveLength(1);
  });

  it("falls back to the static tax-code list when no server rows are provided", async () => {
    renderLineRow({ taxCodes: undefined });

    const taxSelect = screen.getByRole("combobox", { name: "Tax code" });
    const user = userEvent.setup();
    await user.click(taxSelect);

    const srOptions = await screen.findAllByText("SR");
    expect(srOptions.length).toBeGreaterThanOrEqual(1);
  });

  it("previews GST at the server rate in force (8% for a 2023-dated SR line)", async () => {
    renderLineRow();

    const user = userEvent.setup();
    await user.type(screen.getByLabelText("Line description"), "Consulting");
    await user.clear(screen.getByLabelText("Quantity"));
    await user.type(screen.getByLabelText("Quantity"), "1");
    await user.clear(screen.getByLabelText("Unit price"));
    await user.type(screen.getByLabelText("Unit price"), "100");

    await waitFor(
      () => expect(screen.getByLabelText("Line total").textContent).toBe("108.00"),
      { timeout: 3000 }
    );
  });
});
