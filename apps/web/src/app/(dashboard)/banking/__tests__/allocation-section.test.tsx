/**
 * P9/B-3b: the allocation section — open documents for the chosen contact,
 * clamped allocation inputs, the backend's inline payload shape.
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { useState } from "react";
import userEvent from "@testing-library/user-event";
import { AllocationSection } from "../components/allocation-section";
import { useInvoices } from "@/hooks/use-invoices";

vi.mock("@/hooks/use-invoices", () => ({
  useInvoices: vi.fn(),
}));

const OPEN_INVOICES = {
  results: [
    {
      id: "d-55555555-5555-4555-8555-555555555555",
      document_type: "SALES_INVOICE",
      document_number: "INV-000041",
      contact_id: "c-1",
      contact_name: "ABC Pte Ltd",
      issue_date: "2026-01-15",
      due_date: "2026-02-14",
      status: "APPROVED",
      status_display: "Approved",
      total_incl: "5400.0000",
      currency: "SGD",
      amount_paid: "400.0000",
      amount_due: "5000.0000",
    },
    {
      id: "d-66666666-6666-4666-8666-666666666666",
      document_type: "SALES_INVOICE",
      document_number: "INV-000042",
      contact_id: "c-1",
      contact_name: "ABC Pte Ltd",
      issue_date: "2026-02-01",
      due_date: "2026-03-03",
      status: "PARTIALLY_PAID",
      status_display: "Partially Paid",
      total_incl: "1090.0000",
      currency: "SGD",
      amount_paid: "90.0000",
      amount_due: "1000.0000",
    },
    // settled + draft rows must NOT be offered
    {
      id: "d-77777777-7777-4777-8777-777777777777",
      document_type: "SALES_INVOICE",
      document_number: "INV-000043",
      contact_id: "c-1",
      contact_name: "ABC Pte Ltd",
      issue_date: "2026-02-10",
      due_date: "2026-03-10",
      status: "PAID",
      status_display: "Paid",
      total_incl: "100.0000",
      currency: "SGD",
      amount_paid: "100.0000",
      amount_due: "0.0000",
    },
    {
      id: "d-88888888-8888-4888-8888-888888888888",
      document_type: "SALES_INVOICE",
      document_number: "INV-000044",
      contact_id: "c-1",
      contact_name: "ABC Pte Ltd",
      issue_date: "2026-02-11",
      due_date: "2026-03-11",
      status: "DRAFT",
      status_display: "Draft",
      total_incl: "100.0000",
      currency: "SGD",
      amount_paid: "0.0000",
      amount_due: "100.0000",
    },
  ],
  count: 4,
};

describe("AllocationSection (P9/B-3b)", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(useInvoices).mockReturnValue({
      data: OPEN_INVOICES,
      isLoading: false,
    } as unknown as ReturnType<typeof useInvoices>);
  });

  it("offers only outstanding documents (settled and draft excluded)", () => {
    const onChange = vi.fn();
    render(
      <AllocationSection
        orgId="org-1"
        contactId="c-1"
        documentType="SALES_INVOICE"
        allocations={[]}
        onChange={onChange}
      />
    );

    expect(screen.getByText("INV-000041")).toBeInTheDocument();
    expect(screen.getByText("INV-000042")).toBeInTheDocument();
    expect(screen.queryByText("INV-000043")).not.toBeInTheDocument();
    expect(screen.queryByText("INV-000044")).not.toBeInTheDocument();
  });

  it("queries the contact's documents through the list endpoint — gated on the contact (P10/L-3)", () => {
    render(
      <AllocationSection
        orgId="org-1"
        contactId="c-1"
        documentType="SALES_INVOICE"
        allocations={[]}
        onChange={vi.fn()}
      />
    );

    expect(useInvoices).toHaveBeenCalledWith(
      "org-1",
      {
        type: "SALES_INVOICE",
        contact_id: "c-1",
      },
      // P10/L-3: no org-wide fetch pre-pick — the query is held off
      // until a contact exists.
      { enabled: true }
    );
  });

  it("holds the query off entirely when no contact is picked (P10/L-3)", () => {
    render(
      <AllocationSection
        orgId="org-1"
        contactId=""
        documentType="SALES_INVOICE"
        allocations={[]}
        onChange={vi.fn()}
      />
    );

    expect(useInvoices).toHaveBeenCalledWith(
      "org-1",
      { type: "SALES_INVOICE", contact_id: "" },
      { enabled: false }
    );
  });

  it("builds the allocations payload and clamps to the outstanding balance", async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();

    // A controlled harness — the real forms store allocations in state,
    // so each keystroke feeds back like production.
    function Harness() {
      const [allocations, setAllocations] = useState<
        { document_id: string; allocated_amount: string }[]
      >([]);
      return (
        <AllocationSection
          orgId="org-1"
          contactId="c-1"
          documentType="SALES_INVOICE"
          allocations={allocations}
          onChange={(next) => {
            onChange(next);
            setAllocations(next);
          }}
        />
      );
    }
    render(<Harness />);

    // over-allocate: 99999 against a 5000 balance → clamped to 5000
    await user.type(screen.getByLabelText(/allocation for INV-000041/i), "99999");

    expect(onChange).toHaveBeenLastCalledWith([
      { document_id: "d-55555555-5555-4555-8555-555555555555", allocated_amount: "5000.00" },
    ]);
  });

  it("clears an allocation when the input empties", async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();
    render(
      <AllocationSection
        orgId="org-1"
        contactId="c-1"
        documentType="SALES_INVOICE"
        allocations={[
          { document_id: "d-55555555-5555-4555-8555-555555555555", allocated_amount: "100.00" },
        ]}
        onChange={onChange}
      />
    );

    const input = screen.getByLabelText(
      /allocation for INV-000041/i
    ) as HTMLInputElement;
    await user.clear(input);

    expect(onChange).toHaveBeenLastCalledWith([]);
  });

  it("renders nothing without a contact", () => {
    const { container } = render(
      <AllocationSection
        orgId="org-1"
        contactId=""
        documentType="SALES_INVOICE"
        allocations={[]}
        onChange={vi.fn()}
      />
    );
    expect(container).toBeEmptyDOMElement();
  });
});
