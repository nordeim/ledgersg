/**
 * P10/M-9: change password. The backend endpoint is real (POST
 * /api/v1/auth/change-password/ — expires every refresh token + the
 * session cookies) with zero UI, while the Settings profile card claimed
 * "Profile editing is handled by your account settings" — no such
 * surface existed anywhere. The lie dies; the card speaks the backend's
 * 12-char floor (AUTH_PASSWORD_VALIDATORS min_length: 12).
 */

import { beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ChangePasswordCard } from "../components/change-password-card";
import { ApiError } from "@/lib/api-client";

const { __mocks } = vi.hoisted(() => ({
  __mocks: {
    post: vi.fn(),
    logout: vi.fn().mockResolvedValue(undefined),
  },
}));

vi.mock("@/lib/api-client", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/api-client")>();
  return {
    ...actual,
    api: { ...actual.api, post: __mocks.post },
  };
});

vi.mock("@/providers/auth-provider", () => ({
  useAuth: () => ({
    logout: __mocks.logout,
    user: { id: "u1", email: "demo@ledgersg.sg", full_name: "Demo User" },
    currentOrg: { id: "org-1", name: "Test Org" },
    isLoading: false,
  }),
}));

function renderCard() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <ChangePasswordCard />
    </QueryClientProvider>
  );
}

const CURRENT = "correct-horse-battery-1";
const NEW = "staple-battery-9-new";

async function fillAndSubmit(user: ReturnType<typeof userEvent.setup>) {
  await user.type(screen.getByLabelText(/^current password/i), CURRENT);
  await user.type(screen.getByLabelText(/^new password/i), NEW);
  await user.type(screen.getByLabelText(/^confirm new password/i), NEW);
  await user.click(screen.getByRole("button", { name: /change password/i }));
}

describe("ChangePasswordCard (P10/M-9)", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    __mocks.post.mockResolvedValue({ message: "Password changed successfully" });
  });

  it("renders the three fields with the backend's 12-char floor", () => {
    renderCard();

    expect(screen.getByLabelText(/^current password/i)).toBeInTheDocument();
    const newPassword = screen.getByLabelText(/^new password/i) as HTMLInputElement;
    expect(newPassword.minLength).toBe(12);
    expect(screen.getByLabelText(/^confirm new password/i)).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: /change password/i })
    ).toBeInTheDocument();
  });

  it("refuses a short new password client-side", async () => {
    const user = userEvent.setup();
    renderCard();

    await user.type(screen.getByLabelText(/^current password/i), CURRENT);
    await user.type(screen.getByLabelText(/^new password/i), "short");
    await user.type(screen.getByLabelText(/^confirm new password/i), "short");
    await user.click(screen.getByRole("button", { name: /change password/i }));

    expect(__mocks.post).not.toHaveBeenCalled();
    expect(screen.getByText(/at least 12 characters/i)).toBeInTheDocument();
  });

  it("refuses a mismatched confirmation client-side", async () => {
    const user = userEvent.setup();
    renderCard();

    await user.type(screen.getByLabelText(/^current password/i), CURRENT);
    await user.type(screen.getByLabelText(/^new password/i), NEW);
    await user.type(screen.getByLabelText(/^confirm new password/i), "different-pass-123");
    await user.click(screen.getByRole("button", { name: /change password/i }));

    expect(__mocks.post).not.toHaveBeenCalled();
    expect(screen.getByText(/passwords do not match/i)).toBeInTheDocument();
  });

  it("submits the wire contract and clears the dead session", async () => {
    const user = userEvent.setup();
    renderCard();

    await fillAndSubmit(user);

    await waitFor(() => {
      expect(__mocks.post).toHaveBeenCalledWith(
        "/api/v1/auth/change-password/",
        { old_password: CURRENT, new_password: NEW }
      );
    });
    // The backend revoked every refresh token — the client clears state
    // and lands on /login (via the provider's logout seam).
    await waitFor(() => expect(__mocks.logout).toHaveBeenCalledTimes(1));
  });

  it("surfaces the backend's wrong-current-password error", async () => {
    const user = userEvent.setup();
    __mocks.post.mockRejectedValue(
      new ApiError(400, "Current password is incorrect.")
    );
    renderCard();

    await fillAndSubmit(user);

    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent(/current password is incorrect/i);
    expect(__mocks.logout).not.toHaveBeenCalled();
  });
});
