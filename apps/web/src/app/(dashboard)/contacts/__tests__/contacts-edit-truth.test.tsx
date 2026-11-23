import { beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import ContactsClient from "../contacts-client";
import { useContact, useContacts } from "@/hooks/use-contacts";

/**
 * P11/H-1 + M-3 — the contacts edit surface tells the truth.
 *
 * H-1: the edit dialog prefilled from the LIST row, whose serializer never
 * carried uen/peppol_id/address_line_1/postal_code/gst_reg_number — those
 * inputs prefilled blank, and Save PATCHed all eight fields unconditionally,
 * so fixing an email ERASED the stored UEN, Peppol ID and address with a
 * success toast. The dialog must prefill from the DETAIL payload.
 *
 * M-3: the search "debounce" was a useMemo whose cleanup return is never
 * invoked — one request per keystroke, stale intermediate values, timers
 * surviving unmount. A real debounce must settle to the LAST value only.
 */

// The REAL list-serializer shape (post P11: id/name/contact_type/is_customer/
// is_supplier/email/phone/is_active/city/country/uen/peppol_id — never
// address_line_1/postal_code/gst_reg_number).
const listRow = {
  id: "7c9e6679-7425-40de-944b-e07fc1f90ae7",
  org_id: "org-1",
  contact_type: "CUSTOMER" as const,
  name: "Marina Consulting Group Pte Ltd",
  is_customer: true,
  is_supplier: false,
  email: "billing@marina.example.sg",
  phone: "+65 6123 4567",
  is_active: true,
  city: "Singapore",
  country: "SG",
  uen: "201912345A",
  peppol_id: "0209-201912345A-1234",
};

// The REAL detail-serializer shape (ContactDetailSerializer — the full
// field set the edit dialog needs).
const contactDetail = {
  ...listRow,
  company_name: "Marina Consulting Group",
  legal_name: "Marina Consulting Group Pte Ltd",
  gst_reg_number: "M90345678X",
  is_gst_registered: true,
  address_line_1: "12 Marina Boulevard #05-01",
  address_line_2: "Marina Bay Financial Centre",
  state_province: "",
  postal_code: "018982",
  default_currency: "SGD",
  payment_terms_days: 30,
  credit_limit: null,
  peppol_scheme_id: "0209",
  notes: "",
  created_at: "2026-11-01T00:00:00Z",
  updated_at: "2026-11-01T00:00:00Z",
};

const updateMock = vi.fn().mockResolvedValue({});
const deactivateMock = vi.fn().mockResolvedValue({});

vi.mock("@/hooks/use-contacts", () => ({
  useContacts: vi.fn(() => ({
    data: [listRow],
    isLoading: false,
    isError: false,
  })),
  useContact: vi.fn(() => ({
    data: contactDetail,
    isLoading: false,
  })),
  useUpdateContact: () => ({
    mutateAsync: updateMock,
    isPending: false,
  }),
  useDeactivateContact: () => ({
    mutateAsync: deactivateMock,
    isPending: false,
  }),
}));

vi.mock("@/providers/auth-provider", () => ({
  useAuth: () => ({
    currentOrg: { id: "org-1", name: "Test Org" },
    isAuthenticated: true,
    isLoading: false,
  }),
}));

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn() }),
  useSearchParams: () => ({ get: vi.fn(() => null) }),
}));

beforeEach(() => {
  vi.clearAllMocks();
  updateMock.mockResolvedValue({});
  deactivateMock.mockResolvedValue({});
});

describe("P11/H-1 — the edit dialog prefills from the detail payload", () => {
  it("prefills UEN, Peppol ID, address and GST reg no from the DETAIL endpoint", async () => {
    const user = userEvent.setup();
    render(<ContactsClient />);

    await user.click(
      screen.getByRole("button", { name: new RegExp(`edit ${listRow.name}`, "i") })
    );

    // The fields the LIST payload never carried must come from the detail
    // payload — not prefill blank.
    expect(await screen.findByLabelText(/address line 1/i)).toHaveValue(
      contactDetail.address_line_1
    );
    expect(screen.getByLabelText(/postal code/i)).toHaveValue(
      contactDetail.postal_code
    );
    expect(screen.getByLabelText(/gst registration no/i)).toHaveValue(
      contactDetail.gst_reg_number
    );
    expect(screen.getByLabelText(/uen/i)).toHaveValue(listRow.uen);
    expect(screen.getByLabelText(/peppol id/i)).toHaveValue(listRow.peppol_id);
    // The detail hook was actually used (not the list row).
    expect(useContact).toHaveBeenCalledWith("org-1", listRow.id);
  });

  it("saving a single-field fix PATCHes the truthfully-prefilled field set (no blank overwrite)", async () => {
    const user = userEvent.setup();
    render(<ContactsClient />);

    await user.click(
      screen.getByRole("button", { name: new RegExp(`edit ${listRow.name}`, "i") })
    );

    const peppolInput = await screen.findByLabelText(/peppol id/i);
    await user.clear(peppolInput);
    await user.type(peppolInput, "0209-201912345A-9999");

    await user.click(screen.getByRole("button", { name: /save changes/i }));

    await waitFor(() => expect(updateMock).toHaveBeenCalledTimes(1));
    const sent = updateMock.mock.calls[0][0];
    expect(sent).toMatchObject({
      peppol_id: "0209-201912345A-9999",
      // The untouched fields ride along with their TRUE values — blank
      // prefill would have erased them server-side.
      uen: "201912345A",
      address_line_1: "12 Marina Boulevard #05-01",
      postal_code: "018982",
      gst_reg_number: "M90345678X",
    });
  });
});

describe("P11/M-3 — the search debounce settles to the last value", () => {
  it("typing a burst fires ONE search with the final value — no intermediates", async () => {
    const user = userEvent.setup();
    render(<ContactsClient />);

    const search = screen.getByRole("textbox", { name: /search contacts/i });
    await user.type(search, "acme");

    // The debounce settles on the LAST value.
    await waitFor(() => {
      expect(useContacts).toHaveBeenLastCalledWith(
        "org-1",
        expect.objectContaining({ search: "acme" })
      );
    });

    // No intermediate value ever landed — the broken useMemo debounce fired
    // one stale timer per keystroke ("a", "ac", "acm" all landed).
    const searchedValues = vi
      .mocked(useContacts)
      .mock.calls.map(([, filters]) => (filters as { search?: string }).search)
      .filter(Boolean);
    expect(searchedValues).toEqual(["acme"]);
  });

  it("rapid retyping cancels the stale timer (final value wins)", async () => {
    const user = userEvent.setup();
    render(<ContactsClient />);

    const search = screen.getByRole("textbox", { name: /search contacts/i });
    await user.type(search, "acme");
    await user.clear(search);
    await user.type(search, "bayan");

    await waitFor(() => {
      expect(useContacts).toHaveBeenLastCalledWith(
        "org-1",
        expect.objectContaining({ search: "bayan" })
      );
    });

    const searchedValues = vi
      .mocked(useContacts)
      .mock.calls.map(([, filters]) => (filters as { search?: string }).search)
      .filter(Boolean);
    // The clear cancelled the stale "acme" burst mid-debounce (typed and
    // cleared inside the 300ms window) — only the retyped value lands.
    // With the broken useMemo debounce the stale "acme"/"acm" timers all
    // fired after the retype began.
    expect(searchedValues).toEqual(["bayan"]);
  });
});
