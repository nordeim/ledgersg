import { beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import RegisterPage from "../page";
import LoginPage from "../../login/page";
import { ApiError } from "@/lib/api-client";

// P10/H-2: the registration page — the login page's "Create account" link
// was href="#" (dead) while POST /api/v1/auth/register/ existed with zero
// consumers. A brand-new self-serve user could not enter the product.

const registerMock = vi.fn().mockResolvedValue(undefined);

vi.mock("@/providers/auth-provider", () => ({
  useAuth: () => ({
    register: registerMock,
    login: vi.fn().mockResolvedValue(undefined),
    isAuthenticated: false,
    isLoading: false,
  }),
}));

const pushMock = vi.fn();

vi.mock("next/navigation", () => ({
  useRouter: () => ({
    push: pushMock,
    replace: vi.fn(),
    prefetch: vi.fn(),
  }),
}));

beforeEach(() => {
  vi.clearAllMocks();
  // The org-less fresh-registration state (the P10/H-2 routing case).
  registerMock.mockResolvedValue([]);
});

describe("RegisterPage rendering", () => {
  it("renders its content inside a main landmark with one level-1 heading", () => {
    render(<RegisterPage />);

    expect(screen.getByRole("main")).toBeInTheDocument();
    const h1s = screen.getAllByRole("heading", { level: 1 });
    expect(h1s).toHaveLength(1);
    expect(h1s[0]).toHaveTextContent(/LEDGERSG/);
  });

  it("renders the register fields with the backend's 12-char password floor", () => {
    render(<RegisterPage />);

    expect(screen.getByLabelText(/full name/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/email/i)).toBeInTheDocument();
    const password = screen.getByLabelText(/^password/i) as HTMLInputElement;
    expect(password.minLength).toBe(12);
    expect(screen.getByLabelText(/confirm password/i)).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: /create account/i })
    ).toBeInTheDocument();
  });

  it("links back to the login page", () => {
    render(<RegisterPage />);

    const back = screen.getByRole("link", { name: /sign in/i });
    expect(back).toHaveAttribute("href", "/login");
  });
});

describe("RegisterPage submit", () => {
  it("registers and routes the org-less user to organisation creation", async () => {
    const user = userEvent.setup();
    render(<RegisterPage />);

    await user.type(screen.getByLabelText(/full name/i), "Tan Ah Kow");
    await user.type(screen.getByLabelText(/email/i), "tan@example.sg");
    await user.type(screen.getByLabelText(/^password/i), "correct-horse-battery");
    await user.type(screen.getByLabelText(/confirm password/i), "correct-horse-battery");
    await user.click(screen.getByRole("button", { name: /create account/i }));

    await waitFor(() => {
      expect(registerMock).toHaveBeenCalledWith(
        "tan@example.sg",
        "correct-horse-battery",
        "Tan Ah Kow"
      );
    });
    // A fresh registration has no organisation — the P9 org-creation page
    // is the next step of the self-serve loop.
    await waitFor(() => {
      expect(pushMock).toHaveBeenCalledWith("/settings/organisations/new");
    });
  });

  it("blocks submit when the passwords do not match", async () => {
    const user = userEvent.setup();
    render(<RegisterPage />);

    await user.type(screen.getByLabelText(/full name/i), "Tan Ah Kow");
    await user.type(screen.getByLabelText(/email/i), "tan@example.sg");
    await user.type(screen.getByLabelText(/^password/i), "correct-horse-battery");
    await user.type(screen.getByLabelText(/confirm password/i), "different-password-x");
    await user.click(screen.getByRole("button", { name: /create account/i }));

    expect(registerMock).not.toHaveBeenCalled();
    expect(
      await screen.findByText(/passwords do not match/i)
    ).toBeInTheDocument();
  });

  it("surfaces the backend error envelope (e.g. email already registered)", async () => {
    registerMock.mockRejectedValueOnce(
      new ApiError(400, "Email already registered.")
    );
    const user = userEvent.setup();
    render(<RegisterPage />);

    await user.type(screen.getByLabelText(/full name/i), "Tan Ah Kow");
    await user.type(screen.getByLabelText(/email/i), "taken@example.sg");
    await user.type(screen.getByLabelText(/^password/i), "correct-horse-battery");
    await user.type(screen.getByLabelText(/confirm password/i), "correct-horse-battery");
    await user.click(screen.getByRole("button", { name: /create account/i }));

    expect(await screen.findByText(/email already registered/i)).toBeInTheDocument();
    expect(pushMock).not.toHaveBeenCalled();
  });
});

describe("LoginPage link truth (P10/H-2)", () => {
  it("links Create account to the register route", () => {
    render(<LoginPage />);

    const create = screen.getByRole("link", { name: /create account/i });
    expect(create).toHaveAttribute("href", "/register");
  });

  it("no longer renders the dead Forgot password link (no backend endpoint exists)", () => {
    render(<LoginPage />);

    expect(
      screen.queryByRole("link", { name: /forgot password/i })
    ).toBeNull();
  });
});
