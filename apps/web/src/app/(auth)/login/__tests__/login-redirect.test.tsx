/**
 * P16/FE-M1 — the ?redirect= parameter must not be an open redirect.
 *
 * The pre-P16 handler pushed params.get("redirect") verbatim —
 * /login?redirect=https://phish.example (or //phish.example) sent the
 * user off-site immediately after authentication (CWE-601).
 */
import { beforeEach, describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import LoginPage from "../page";

const push = vi.fn();
const loginMock = vi.fn().mockResolvedValue(undefined);

vi.mock("@/providers/auth-provider", () => ({
  useAuth: () => ({
    login: (...args: unknown[]) => loginMock(...args),
    isAuthenticated: false,
    isLoading: false,
  }),
}));

vi.mock("next/navigation", () => ({
  useRouter: () => ({
    push,
    replace: vi.fn(),
    prefetch: vi.fn(),
  }),
}));

function setRedirectParam(value: string | null) {
  // jsdom honours history.replaceState — location.search then reflects
  // the URL the page reads.
  const url = value === null ? "/login/" : `/login/?redirect=${encodeURIComponent(value)}`;
  window.history.replaceState(null, "", url);
}

beforeEach(() => {
  vi.clearAllMocks();
});

async function submitForm() {
  render(<LoginPage />);
  fireEvent.change(screen.getByLabelText(/email/i), {
    target: { value: "demo@ledgersg.sg" },
  });
  fireEvent.change(screen.getByLabelText(/password/i), {
    target: { value: "demo1234pass" },
  });
  fireEvent.submit(screen.getByRole("button", { name: /sign in/i }).closest("form")!);
  await waitFor(() => expect(loginMock).toHaveBeenCalled());
}

describe("login redirect guard (P16/FE-M1)", () => {
  it("pushes a same-app path", async () => {
    setRedirectParam("/invoices");
    await submitForm();
    await waitFor(() => expect(push).toHaveBeenCalledWith("/invoices"));
  });

  it("falls back to /dashboard for an absolute https URL", async () => {
    setRedirectParam("https://phish.example/steal");
    await submitForm();
    await waitFor(() => expect(push).toHaveBeenCalledWith("/dashboard"));
    expect(push).not.toHaveBeenCalledWith("https://phish.example/steal");
  });

  it("falls back to /dashboard for a protocol-relative //host URL", async () => {
    setRedirectParam("//phish.example");
    await submitForm();
    await waitFor(() => expect(push).toHaveBeenCalledWith("/dashboard"));
    expect(push).not.toHaveBeenCalledWith("//phish.example");
  });

  it("falls back to /dashboard when no redirect param exists", async () => {
    setRedirectParam(null);
    await submitForm();
    await waitFor(() => expect(push).toHaveBeenCalledWith("/dashboard"));
  });
});
