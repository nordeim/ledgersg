/**
 * P20 a11y sweep (Mode B, RED first) — the two Highs + the small batch the
 * frontend audit found on the surfaces P19 did not touch.
 *
 * FE-P20-H1: the invoice form's Notes/Terms textareas have no accessible
 *   name (labels without htmlFor, textareas without id/aria-label —
 *   register() does not generate ids). WCAG 1.3.1/4.1.2 Level A on the
 *   primary money-entry form.
 * FE-P20-M4: gst-f5-chart's "accessible data table" has an invalid ARIA
 *   owned structure (role="table" > role="rowheader" containing
 *   role="columnheader" children — ARIA requires table > row >
 *   columnheader). Browsers prune the invalid tree, defeating the
 *   toggle's purpose (the P19 FE-L1 class left behind).
 * FE-P20-L2: every dashboard page renders two h1s (the sidebar brand
 *   shell h1 + the page h1) — the brand must not be a heading.
 * FE-P20-L3: the primary loading states are silent to screen readers
 *   (no role="status"/aria-live on the dashboard + invoices loading
 *   blocks).
 * FE-P20-M7: invoice detail dates render through a UTC date-only parse +
 *   local-timezone toLocaleDateString — one day early for timezones
 *   behind UTC (a money-document date comprehension issue).
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import React from "react";
import { render, screen } from "@/__tests__/utils";
import userEvent from "@testing-library/user-event";
import { InvoiceForm } from "@/components/invoice/invoice-form";
import { GSTF5Chart } from "@/components/dashboard/gst-f5-chart";
import { formatDateOnly } from "@/shared/format";

vi.mock("@/hooks/use-contacts", () => ({
  useCreateContact: () => ({ mutateAsync: vi.fn() }),
  useContacts: () => ({
    data: [
      {
        id: "7c9e6679-7425-40de-944b-e07fc1f90ae7",
        name: "Marina Consulting Group Pte Ltd",
        email: "billing@marina.example.sg",
        is_customer: true,
        is_supplier: false,
        is_active: true,
      },
    ],
    isLoading: false,
    isError: false,
  }),
}));

vi.mock("@/hooks/use-invoices", () => ({
  useCreateInvoice: () => ({ mutateAsync: vi.fn() }),
}));

vi.mock("@/hooks/use-tax-codes", () => ({
  useTaxCodes: () => ({
    data: [{ id: "sr-row", code: "SR", name: "Standard-Rated Supply", rate: "0.0900" }],
    isLoading: false,
    isError: false,
  }),
  FALLBACK_TAX_CODES: [{ id: "SR", code: "SR", name: "SR", rate: "0.09" }],
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

describe("InvoiceForm a11y (P20/FE-H1)", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("the Notes textarea has an accessible name", () => {
    render(<InvoiceForm onSuccess={vi.fn()} />);
    // getByRole with name throws when the textbox is unnamed — the RED.
    expect(() =>
      screen.getByRole("textbox", { name: /^notes$/i })
    ).not.toThrow();
  });

  it("the Terms & Conditions textarea has an accessible name", () => {
    render(<InvoiceForm onSuccess={vi.fn()} />);
    expect(() =>
      screen.getByRole("textbox", { name: /terms & conditions/i })
    ).not.toThrow();
  });

  it("the label elements are programmatically associated (htmlFor/id)", () => {
    const { container } = render(
      <InvoiceForm onSuccess={vi.fn()} />
    );
    const labels = Array.from(container.querySelectorAll("label"));
    const notesLabel = labels.find((l) => l.textContent === "Notes");
    const termsLabel = labels.find((l) => l.textContent === "Terms & Conditions");
    expect(notesLabel).toBeTruthy();
    expect(termsLabel).toBeTruthy();
    // The association, not just the visible text.
    expect(notesLabel!.getAttribute("for")).toBeTruthy();
    expect(termsLabel!.getAttribute("for")).toBeTruthy();
    expect(
      document.getElementById(notesLabel!.getAttribute("for")!)
    ).toBeTruthy();
    expect(
      document.getElementById(termsLabel!.getAttribute("for")!)
    ).toBeTruthy();
  });
});

describe("GstF5Chart ARIA table structure (P20/FE-M4)", () => {
  it("the data table view has a valid owned structure (row > columnheader)", async () => {
    const user = userEvent.setup();
    render(<GSTF5Chart gstPayable="90.0000" />);
    // The chart is the default view — switch to the table (a no-op if
    // the table is already the default).
    if (!screen.queryByRole("table", { name: "GST F5 Return Breakdown" })) {
      await user.click(screen.getByRole("button", { name: /show data table/i }));
    }
    const tableEl = screen.getByRole("table", { name: "GST F5 Return Breakdown" });
    // The header cells live inside a real row (the invalid
    // rowheader-as-container is pruned by browsers and fails this query).
    expect(
      tableEl.querySelector('[role="row"] > [role="columnheader"]')
    ).toBeTruthy();
  });
});

describe("date formatting (P20/FE-M7)", () => {
  it("a date-only string renders as its own lexical date regardless of the runner timezone", () => {
    // 2024-01-31 parsed as UTC midnight: in a runner behind UTC (e.g.
    // America/New_York) the old formatter rendered "31 Jan" as "30 Jan".
    // The fixed formatter must emit the string's own date in every zone.
    const out = formatDateOnly("2024-01-31");
    expect(out).toMatch(/31/);
    expect(out).toMatch(/jan/i);
    expect(out).toMatch(/2024/);
  });

  it("garbage input falls back to the raw string (the existing contract)", () => {
    expect(formatDateOnly("not a date")).toBe("not a date");
  });
});
