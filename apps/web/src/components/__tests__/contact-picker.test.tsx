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
import { ContactPicker } from "../contact-picker";
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

    // P19/FE-M2: the options select on mousedown (the WAI-ARIA pattern —
    // it fires before the input's blur, so a pointer pick never races the
    // click-away close).
    fireEvent.mouseDown(await screen.findByRole("option", { name: /ABC Pte Ltd/i }));

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

describe("ContactPicker WAI-ARIA combobox (P19/FE-M2)", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(useContacts).mockReturnValue({
      data: CUSTOMERS,
      isLoading: false,
    } as unknown as ReturnType<typeof useContacts>);
  });

  it("the input controls the listbox (aria-controls) and announces expansion", async () => {
    const user = userEvent.setup();
    render(<ContactPicker orgId="org-1" type="customer" value="" onChange={vi.fn()} />);

    const input = screen.getByRole("combobox", { name: /search customer/i });
    expect(input.getAttribute("aria-expanded")).toBe("false");
    expect(input.getAttribute("aria-haspopup")).toBe("listbox");
    expect(input.getAttribute("aria-autocomplete")).toBe("list");

    await user.click(input);
    const listbox = await screen.findByRole("listbox", { name: /customer results/i });
    expect(input.getAttribute("aria-controls")).toBe(listbox.id);
  });

  it("ArrowDown + Enter selects the first option without a pointer", async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();
    render(
      <ContactPicker orgId="org-1" type="customer" value="" onChange={onChange} />
    );

    const input = screen.getByRole("combobox", { name: /search customer/i });
    input.focus();
    await user.keyboard("{ArrowDown}");

    // The active option is announced and flagged selected.
    const firstOption = screen.getByRole("option", { name: /ABC Pte Ltd/i });
    expect(input.getAttribute("aria-activedescendant")).toBe(firstOption.id);
    expect(firstOption.getAttribute("aria-selected")).toBe("true");

    await user.keyboard("{ArrowDown}");
    const secondOption = screen.getByRole("option", { name: /XYZ Trading/i });
    expect(input.getAttribute("aria-activedescendant")).toBe(secondOption.id);
    expect(firstOption.getAttribute("aria-selected")).toBe("false");

    await user.keyboard("{Enter}");
    expect(onChange).toHaveBeenCalledWith(CUSTOMERS[1].id);
    // The selection renders in the box, the listbox closes.
    expect(screen.getByText(/XYZ Trading/)).toBeInTheDocument();
    expect(screen.queryByRole("listbox")).not.toBeInTheDocument();
  });

  it("ArrowUp wraps to the last option", async () => {
    const user = userEvent.setup();
    render(<ContactPicker orgId="org-1" type="customer" value="" onChange={vi.fn()} />);

    const input = screen.getByRole("combobox", { name: /search customer/i });
    input.focus();
    await user.keyboard("{ArrowUp}");

    const lastOption = screen.getByRole("option", { name: /XYZ Trading/i });
    expect(input.getAttribute("aria-activedescendant")).toBe(lastOption.id);
  });

  it("Escape closes the listbox and keeps focus on the input", async () => {
    const user = userEvent.setup();
    render(<ContactPicker orgId="org-1" type="customer" value="" onChange={vi.fn()} />);

    const input = screen.getByRole("combobox", { name: /search customer/i });
    input.focus();
    await user.keyboard("{ArrowDown}");
    expect(screen.getByRole("listbox")).toBeInTheDocument();

    await user.keyboard("{Escape}");
    expect(screen.queryByRole("listbox")).not.toBeInTheDocument();
    expect(screen.getByRole("combobox", { name: /search customer/i })).toHaveFocus();
  });

  it("the empty-state row is not announced as an option", async () => {
    vi.mocked(useContacts).mockReturnValue({
      data: [],
      isLoading: false,
    } as unknown as ReturnType<typeof useContacts>);

    const user = userEvent.setup();
    render(<ContactPicker orgId="org-1" type="customer" value="" onChange={vi.fn()} />);

    await user.click(screen.getByRole("combobox", { name: /search customer/i }));
    expect(await screen.findByRole("listbox", { name: /customer results/i })).toBeInTheDocument();
    expect(screen.queryAllByRole("option")).toHaveLength(0);
  });
});
