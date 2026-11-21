/**
 * Invoice Submission Adapter Tests (TDD — P3/D-1)
 *
 * The New Invoice form's onSubmit was a stub (console.log + mock UUID);
 * this adapter maps form state to the backend create contracts:
 *   POST /{org}/invoicing/contacts/      (contact_type CUSTOMER, name, uen…)
 *   POST /{org}/invoicing/documents/     (document_type, contact_id, lines…)
 *
 * Line mapping notes (validated against apps/invoicing/serializers.py:164
 * and document_service._add_lines): each line needs account_id,
 * description, quantity, unit_price, tax_code_id, is_bcrs_deposit and
 * discount_pct; computed preview fields and the form-local
 * invoice_number are dropped (the backend document_sequence owns
 * numbering).
 */

import { describe, it, expect } from "vitest";
import {
  buildContactPayload,
  buildDocumentPayload,
  validateSubmissionReadiness,
} from "../invoice-submit";
import { createEmptyInvoice, type Invoice, type TaxCode } from "@/shared/schemas/invoice";

function readyInvoice(): Invoice {
  const invoice = createEmptyInvoice();
  invoice.invoice_number = "INV-LOCAL-001";
  invoice.issue_date = "2024-06-15";
  invoice.due_date = "2024-07-15";
  invoice.reference = "PO-77";
  invoice.notes = "thank you";
  invoice.customer = {
    ...invoice.customer,
    name: "Acme Pte Ltd",
    email: "billing@acme.sg",
    uen: "201912345A",
  };
  invoice.lines = [
    {
      id: "line-1",
      description: "Consulting",
      quantity: "10",
      unit_price: "100.00",
      discount_pct: "10",
      tax_code: "SR",
      is_bcrs_deposit: false,
      account_id: "acc-4000",
      line_subtotal: "900.0000",
      gst_amount: "81.0000",
      line_total: "981.0000",
    },
  ];
  return invoice;
}

describe("buildContactPayload", () => {
  it("maps the form customer to the backend contact contract", () => {
    const invoice = readyInvoice();

    const payload = buildContactPayload(invoice);

    expect(payload).toEqual({
      contact_type: "CUSTOMER",
      name: "Acme Pte Ltd",
      email: "billing@acme.sg",
      uen: "201912345A",
      // blank form fields are omitted, not sent as empty strings
      address_line_1: undefined,
      is_customer: true,
    });
  });
});

describe("buildDocumentPayload", () => {
  it("maps the form to the backend document create contract", () => {
    const invoice = readyInvoice();
    const taxCodeIdByCode = new Map<TaxCode, string>([["SR", "sr-row-uuid"]]);

    const payload = buildDocumentPayload(invoice, "contact-uuid-1", taxCodeIdByCode);

    expect(payload).toEqual({
      document_type: "SALES_INVOICE",
      contact_id: "contact-uuid-1",
      issue_date: "2024-06-15",
      due_date: "2024-07-15",
      reference: "PO-77",
      notes: "thank you",
      lines: [
        {
          account_id: "acc-4000",
          description: "Consulting",
          quantity: "10",
          unit_price: "100.00",
          discount_pct: "10",
          tax_code_id: "sr-row-uuid",
          is_bcrs_deposit: false,
        },
      ],
    });
  });

  it("drops computed preview fields and the local invoice number", () => {
    const invoice = readyInvoice();
    const payload = buildDocumentPayload(invoice, "c1", new Map<TaxCode, string>([["SR", "sr"]]));

    expect(payload.lines[0]).not.toHaveProperty("line_subtotal");
    expect(payload.lines[0]).not.toHaveProperty("gst_amount");
    expect(payload.lines[0]).not.toHaveProperty("line_total");
    expect(payload.lines[0]).not.toHaveProperty("id");
    expect(payload).not.toHaveProperty("invoice_number");
  });
});

describe("validateSubmissionReadiness", () => {
  it("rejects a line without a posting account", () => {
    const invoice = readyInvoice();
    invoice.lines[0].account_id = "";

    const problems = validateSubmissionReadiness(invoice, new Map<TaxCode, string>([["SR", "sr"]]));

    expect(problems).toEqual([
      "Line 1 has no posting account selected.",
    ]);
  });

  it("rejects a line whose tax code has no server-resolved row", () => {
    const invoice = readyInvoice();

    const problems = validateSubmissionReadiness(invoice, new Map<TaxCode, string>());

    expect(problems).toEqual([
      "Line 1 tax code SR could not be resolved to a rate row in force on 2024-06-15.",
    ]);
  });

  it("rejects an empty customer name", () => {
    const invoice = readyInvoice();
    invoice.customer = { ...invoice.customer, name: "" };

    const problems = validateSubmissionReadiness(invoice, new Map<TaxCode, string>([["SR", "sr"]]));

    expect(problems).toEqual(["Customer name is required."]);
  });

  it("returns no problems for a ready invoice", () => {
    expect(validateSubmissionReadiness(readyInvoice(), new Map<TaxCode, string>([["SR", "sr"]]))).toEqual([]);
  });
});
