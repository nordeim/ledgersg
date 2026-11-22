/**
 * Invoice Submission Adapter (P3/D-1)
 *
 * Pure mapping from the invoice form state to the backend create
 * contracts — no React, fully unit-testable:
 *
 *   POST /api/v1/{org}/invoicing/contacts/
 *     { contact_type: "CUSTOMER", name, email, uen, address_line_1,
 *       is_customer: true }
 *
 *   POST /api/v1/{org}/invoicing/documents/
 *     { document_type: "SALES_INVOICE", contact_id, issue_date, due_date,
 *       reference, notes, lines: [{ account_id, description, quantity,
 *       unit_price, discount_pct, tax_code_id, is_bcrs_deposit }] }
 *
 * Contract notes (validated against apps/invoicing/serializers.py:164 and
 * document_service._add_lines):
 *   - the backend `core.document_sequence` owns document numbering — the
 *     form's local `invoice_number` is a display/reference value only and
 *     is intentionally NOT sent
 *   - computed client preview fields (line_subtotal/gst_amount/line_total,
 *     line id) are dropped; the server recalculates authoritatively
 *   - `discount_pct` is applied server-side since the P3/H-03 remediation
 */

import type { Invoice } from "@/shared/schemas/invoice";
import type { TaxCode } from "@/shared/schemas/invoice";

export interface ContactPayload {
  contact_type: "CUSTOMER";
  name: string;
  email?: string;
  uen?: string;
  address_line_1?: string;
  is_customer: boolean;
}

export interface DocumentLinePayload {
  account_id: string;
  description: string;
  quantity: string;
  unit_price: string;
  discount_pct: string;
  tax_code_id: string;
  is_bcrs_deposit: boolean;
}

export interface DocumentPayload {
  document_type: "SALES_INVOICE" | "SALES_QUOTE";
  contact_id: string;
  issue_date: string;
  due_date: string;
  reference?: string;
  notes?: string;
  lines: DocumentLinePayload[];
}

export function buildContactPayload(invoice: Invoice): ContactPayload {
  const customer = invoice.customer;
  return {
    contact_type: "CUSTOMER",
    name: customer.name,
    email: customer.email || undefined,
    uen: customer.uen || undefined,
    address_line_1: customer.address || undefined,
    is_customer: true,
  };
}

export function buildDocumentPayload(
  invoice: Invoice,
  contactId: string,
  taxCodeIdByCode: ReadonlyMap<TaxCode, string>,
  documentType: DocumentPayload["document_type"] = "SALES_INVOICE"
): DocumentPayload {
  return {
    document_type: documentType,
    contact_id: contactId,
    issue_date: invoice.issue_date,
    due_date: invoice.due_date,
    reference: invoice.reference || undefined,
    notes: invoice.notes || undefined,
    lines: invoice.lines.map((line) => ({
      account_id: line.account_id,
      description: line.description,
      quantity: line.quantity,
      unit_price: line.unit_price,
      discount_pct: line.discount_pct,
      tax_code_id: taxCodeIdByCode.get(line.tax_code) ?? "",
      is_bcrs_deposit: line.is_bcrs_deposit,
    })),
  };
}

/**
 * Pre-flight validation for the pieces the backend contract requires that
 * the form schema alone does not enforce (posting account per line,
 * server-resolved tax-code row per line, customer). Returns a list of
 * human-readable problems; empty list = ready to submit.
 *
 * P10/H-1: `requireCustomerName` is false when the form is picking an
 * EXISTING contact (the name lives on the picked row, not the form state);
 * the caller checks the picked id separately.
 */
export function validateSubmissionReadiness(
  invoice: Invoice,
  taxCodeIdByCode: ReadonlyMap<TaxCode, string>,
  options: { requireCustomerName?: boolean } = {}
): string[] {
  const { requireCustomerName = true } = options;
  const problems: string[] = [];

  if (requireCustomerName && !invoice.customer.name.trim()) {
    problems.push("Customer name is required.");
  }

  invoice.lines.forEach((line, i) => {
    const lineNumber = i + 1;
    if (!line.account_id) {
      problems.push(`Line ${lineNumber} has no posting account selected.`);
    }
    if (!taxCodeIdByCode.get(line.tax_code)) {
      problems.push(
        `Line ${lineNumber} tax code ${line.tax_code} could not be resolved to ` +
          `a rate row in force on ${invoice.issue_date}.`
      );
    }
  });

  return problems;
}
