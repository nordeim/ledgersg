import { beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import ContactsClient from "../contacts-client";
import { useContacts } from "@/hooks/use-contacts";

// P10/M-5: contacts management — the backend has full CRUD and the hooks
// were complete but ZERO UI existed: a wrong Peppol ID or email (required
// for InvoiceNow sends) could never be corrected in-app.

// P11: the fixture rebuilt from the REAL serializer shapes — the list row
// (ContactListSerializer: uen/peppol_id joined in P11/H-1) and the detail
// payload the edit dialog now prefills from.
const contactFixture = {
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

const contactDetailFixture = {
  ...contactFixture,
  company_name: "Marina Consulting Group",
  legal_name: "Marina Consulting Group Pte Ltd",
  gst_reg_number: "M90345678X",
  is_gst_registered: true,
  address_line_1: "12 Marina Boulevard #05-01",
  address_line_2: "",
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
  // P26: the hook returns the full envelope — the factory mock follows.
  useContacts: vi.fn(() => ({
    data: { results: [contactFixture], count: 1 },
    isLoading: false,
    isError: false,
  })),
  useContact: vi.fn(() => ({
    data: contactDetailFixture,
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
    // P11/L-1: the row actions gate on can_manage_org — the manager view.
    hasPermission: (permission: string) => permission === "can_manage_org",
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

describe("ContactsClient — list", () => {
  it("renders the contact rows with name, email, UEN and type badges", () => {
    render(<ContactsClient />);

    expect(screen.getByText("Marina Consulting Group Pte Ltd")).toBeInTheDocument();
    expect(screen.getByText("billing@marina.example.sg")).toBeInTheDocument();
    expect(screen.getByText(/UEN 201912345A/)).toBeInTheDocument();
    expect(screen.getByText(/^Customer$/)).toBeInTheDocument();
  });

  it("searches with the backend's real filter keys (is_customer/is_supplier/search)", async () => {
    const user = userEvent.setup();
    render(<ContactsClient />);

    const search = screen.getByRole("textbox", { name: /search contacts/i });
    await user.type(search, "Marina");
    await user.click(screen.getByRole("button", { name: /customers only/i }));

    await waitFor(() => {
      expect(useContacts).toHaveBeenLastCalledWith(
        "org-1",
        expect.objectContaining({
          search: "Marina",
          is_customer: true,
        }),
        expect.objectContaining({ limit: 20, offset: 0 })
      );
    });
  });

  it("shows the empty state when there are no contacts", () => {
    vi.mocked(useContacts).mockReturnValueOnce({
      data: { results: [], count: 0 },
      isLoading: false,
      isError: false,
    } as never);
    render(<ContactsClient />);

    expect(screen.getByText(/no contacts yet/i)).toBeInTheDocument();
  });
});

describe("ContactsClient — edit", () => {
  it("opens the edit dialog prefilled and PATCHes the allowlisted fields", async () => {
    const user = userEvent.setup();
    render(<ContactsClient />);

    await user.click(
      screen.getByRole("button", { name: new RegExp(`edit ${contactFixture.name}`, "i") })
    );

    const nameInput = await screen.findByLabelText(/name/i);
    expect(nameInput).toHaveValue(contactFixture.name);

    const peppolInput = screen.getByLabelText(/peppol id/i);
    expect(peppolInput).toHaveValue(contactFixture.peppol_id);
    await user.clear(peppolInput);
    await user.type(peppolInput, "0209-201912345A-9999");

    await user.click(screen.getByRole("button", { name: /save changes/i }));

    await waitFor(() => expect(updateMock).toHaveBeenCalledTimes(1));
    expect(updateMock).toHaveBeenCalledWith(
      expect.objectContaining({ peppol_id: "0209-201912345A-9999" })
    );
  });
});

describe("ContactsClient — pagination (P26)", () => {
  it("consumes the list envelope and renders the shared TablePagination", () => {
    // The hook now returns {results, count} (the pre-P26 hook unwrapped
    // results and threw the count away) — the page renders the shared
    // control with the truthful total.
    vi.mocked(useContacts).mockReturnValueOnce({
      data: {
        results: [contactFixture],
        count: 25,
      },
      isLoading: false,
      isError: false,
    } as unknown as ReturnType<typeof useContacts>);

    render(<ContactsClient />);

    expect(screen.getByText(contactFixture.name)).toBeInTheDocument();
    const pagination = screen.getByRole("navigation", { name: "Pagination" });
    expect(pagination).toBeInTheDocument();
    expect(screen.getByText("Showing 1–20 of 25 rows")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Previous page" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Next page" })).toBeEnabled();
  });

  it("keeps the truthful empty state when the count is zero", () => {
    vi.mocked(useContacts).mockReturnValueOnce({
      data: { results: [], count: 0 },
      isLoading: false,
      isError: false,
    } as unknown as ReturnType<typeof useContacts>);

    render(<ContactsClient />);

    expect(screen.getByText(/no contacts yet/i)).toBeInTheDocument();
    expect(
      screen.queryByRole("navigation", { name: "Pagination" })
    ).not.toBeInTheDocument();
  });
});

describe("ContactsClient — deactivate", () => {
  it("deactivates only after an explicit confirmation", async () => {
    const user = userEvent.setup();
    render(<ContactsClient />);

    await user.click(
      screen.getByRole("button", { name: new RegExp(`deactivate ${contactFixture.name}`, "i") })
    );

    // The confirm dialog gates the destructive action.
    expect(deactivateMock).not.toHaveBeenCalled();
    expect(screen.getByText(/deactivate this contact/i)).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: /^deactivate$/i }));

    await waitFor(() => expect(deactivateMock).toHaveBeenCalledTimes(1));
  });
});
