/**
 * P7/F-16: ledger-table accessibility — column headers expose their sort
 * state (aria-sort) and scope to screen readers.
 */

import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { LedgerTable } from "../ledger-table";

vi.mock("@/providers/auth-provider", () => ({
  useAuth: () => ({ currentOrg: { id: "org-1", name: "Org" }, isLoading: false }),
}));

const line = {
  id: "l1",
  entry_id: "e1",
  entry_number: 1,
  entry_date: "2026-01-15",
  source_type: "SALES_INVOICE",
  reference: "INV-000001",
  narration: "Invoice INV-000001",
  line_number: 1,
  account_id: "a",
  account_code: "1200",
  account_name: "Accounts Receivable",
  description: "d",
  debit: "100.0000",
  credit: "0.0000",
};

describe("ledger-table a11y (P7/F-16)", () => {
  it("exposes scope=col and aria-sort on every column header", () => {
    render(<LedgerTable data={[line]} />);

    const headers = screen.getAllByRole("columnheader");
    expect(headers.length).toBeGreaterThan(0);
    for (const header of headers) {
      expect(header).toHaveAttribute("scope", "col");
      expect(header).toHaveAttribute("aria-sort");
    }
  });
});
