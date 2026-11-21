import { beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import LoginPage from "../page";

// Mock auth provider (established pattern — see banking page tests)
vi.mock("@/providers/auth-provider", () => ({
  useAuth: () => ({
    login: vi.fn().mockResolvedValue(undefined),
    isAuthenticated: false,
    isLoading: false,
  }),
}));

// Mock next/navigation router
vi.mock("next/navigation", () => ({
  useRouter: () => ({
    push: vi.fn(),
    replace: vi.fn(),
    prefetch: vi.fn(),
  }),
}));

beforeEach(() => {
  vi.clearAllMocks();
});

/**
 * Accessibility semantics of the login page (B-2).
 *
 * The page is what unauthenticated users of every protected route land on
 * (via the auth-guard redirect), and it is the page the e2e axe scan covers.
 * Contract: exactly one <main> landmark and exactly one level-1 heading.
 */
describe("LoginPage accessibility semantics", () => {
  it("renders its content inside a main landmark", () => {
    render(<LoginPage />);

    expect(screen.getByRole("main")).toBeInTheDocument();
  });

  it("renders exactly one level-1 heading containing the brand", () => {
    render(<LoginPage />);

    const h1s = screen.getAllByRole("heading", { level: 1 });
    expect(h1s).toHaveLength(1);
    expect(h1s[0]).toHaveTextContent(/LEDGERSG/);
  });

  it("does not skip heading levels below the h1", () => {
    render(<LoginPage />);

    // The brand is the h1; the next heading level used must not be an h3
    // directly under it (level-2 or nothing).
    const headings = screen
      .getAllByRole("heading")
      .map((heading) => Number(heading.tagName.slice(1)));
    expect(headings).toEqual([1]);
  });
});
