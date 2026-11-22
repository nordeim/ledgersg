/**
 * P9/B-3 + K-5: the contact picker — searchable, typed (customer/supplier),
 * wired to the REAL list-endpoint contract.
 *
 * The payment forms previously bound contact_id to a raw text input
 * (UUID-validated) — a user could not select a customer at all. The
 * useContacts filter keys are the backend's actual params
 * (is_customer / is_supplier / is_active / search); the old `contact_type`
 * key was silently ignored.
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import { useState } from "react";
import userEvent from "@testing-library/user-event";
import { ContactPicker } from "../components/contact-picker";
import { useContacts } from "@/hooks/use-contacts";

vi.mock("@/hooks/use-contacts", () => ({
  useContacts: vi.fn(),
}));

const CUSTOMERS = [
  {
    id: "c-11111111-1111-4111-8111-111111111111",
    name: "ABC Pte Ltd",
    email: "billing@abc.example",
    contact_type: "CUSTOMER",
    is_active: true,
  },
  {
    id: "c-22222222-2222-4222-8222-222222222222",
    name: "XYZ Trading",
    email: "ap@xyz.example",
    contact_type: "BOTH",
    is_active: true,
  },
];

describe("ContactPicker (P9/B-3)", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(useContacts).mockReturnValue({
      data: CUSTOMERS,
      isLoading: false,
    } as unknown as ReturnType<typeof useContacts>);
  });

  it("searches customers with the backend's filter keys", async () => {
    const user = userEvent.setup();
    render(
      <ContactPicker orgId="org-1" type="customer" value="" onChange={vi.fn()} />
    );

    const input = screen.getByRole("combobox", { name: /search customer/i });
    await user.type(input, "ABC");

    await waitFor(() => {
      expect(useContacts).toHaveBeenCalledWith(
        "org-1",
        expect.objectContaining({
          search: "ABC",
          is_customer: true,
          is_active: true,
        })
      );
    });
  });

  it("searches suppliers with is_supplier", async () => {
    const user = userEvent.setup();
    render(
      <ContactPicker orgId="org-1" type="supplier" value="" onChange={vi.fn()} />
    );

    await user.type(screen.getByRole("combobox", { name: /search supplier/i }), "S");

    await waitFor(() => {
      expect(useContacts).toHaveBeenCalledWith(
        "org-1",
        expect.objectContaining({ is_supplier: true })
      );
    });
  });

  it("selects a contact and reports its id", async () => {
    const onChange = vi.fn();
    render(
      <ContactPicker orgId="org-1" type="customer" value="" onChange={onChange} />
    );

    // focus opens the dropdown
    screen.getByRole("combobox", { name: /search customer/i }).focus();

    expect(
      await screen.findByRole("option", { name: /ABC Pte Ltd/i })
    ).toBeInTheDocument();

    fireEvent.click(await screen.findByRole("option", { name: /ABC Pte Ltd/i }));

    await waitFor(() => {
      expect(onChange).toHaveBeenCalledWith(CUSTOMERS[0].id);
    });
    // The selection is displayed, not the UUID.
    expect(screen.getByText(/ABC Pte Ltd/)).toBeInTheDocument();
  });

  it("clears back to search mode", async () => {
    // A controlled harness — the real parents store the value in form
    // state, so clearing propagates through onChange like production.
    function Harness() {
      const [value, setValue] = useState(CUSTOMERS[0].id);
      return (
        <ContactPicker orgId="org-1" type="customer" value={value} onChange={setValue} />
      );
    }
    render(<Harness />);

    // The prefilled value displays its contact (the deep-link contract).
    expect(screen.getByText(/ABC Pte Ltd/)).toBeInTheDocument();

    fireEvent.click(screen.getByLabelText(/clear customer/i));

    expect(
      screen.getByRole("combobox", { name: /search customer/i })
    ).toBeInTheDocument();
  });
});
