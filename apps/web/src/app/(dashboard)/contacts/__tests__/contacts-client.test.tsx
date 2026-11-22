import { beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import ContactsClient from "../contacts-client";
import { useContacts } from "@/hooks/use-contacts";

// P10/M-5: contacts management — the backend has full CRUD and the hooks
// were complete but ZERO UI existed: a wrong Peppol ID or email (required
// for InvoiceNow sends) could never be corrected in-app.

const contactFixture = {
  id: "7c9e6679-7425-40de-944b-e07fc1f90ae7",
  org_id: "org-1",
  contact_type: "CUSTOMER" as const,
  name: "Marina Consulting Group Pte Ltd",
  email: "billing@marina.example.sg",
  phone: "+65 6123 4567",
  uen: "201912345A",
  gst_reg_number: "M90345678X",
  peppol_id: "0209-201912345A-1234",
  is_peppol_enabled: true,
  payment_terms_days: 30,
  currency: "SGD",
  is_active: true,
  country: "SG",
  created_at: "2026-11-01T00:00:00Z",
  updated_at: "2026-11-01T00:00:00Z",
};

const updateMock = vi.fn().mockResolvedValue({});
const deactivateMock = vi.fn().mockResolvedValue({});

vi.mock("@/hooks/use-contacts", () => ({
  useContacts: vi.fn(() => ({
    data: [contactFixture],
    isLoading: false,
    isError: false,
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
        })
      );
    });
  });

  it("shows the empty state when there are no contacts", () => {
    vi.mocked(useContacts).mockReturnValueOnce({
      data: [],
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
