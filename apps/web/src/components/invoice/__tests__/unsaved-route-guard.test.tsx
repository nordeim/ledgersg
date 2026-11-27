/**
 * P19/FE-M3 — the in-app unsaved-work route guard.
 *
 * The P17 beforeunload guard only covered tab-close; an in-app click on
 * the sidebar (a Next Link) silently discarded a dirty invoice. The
 * guard intercepts same-app anchor clicks (capture phase, primary
 * button, no modifiers) while the store is dirty, asks for
 * confirmation, and only then navigates.
 */

import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, it, expect, vi, beforeAll, beforeEach } from "vitest";
import { UnsavedRouteGuard } from "../../unsaved-route-guard";
import { useInvoiceStore } from "@/stores/invoice-store";

const assignMock = vi.fn();

// jsdom's window.location properties are non-configurable — replace the
// whole location object for the mock (restored by vitest's jsdom reset).
beforeAll(() => {
  Object.defineProperty(window, "location", {
    value: { ...window.location, assign: assignMock },
    writable: true,
  });
});

beforeEach(() => {
  assignMock.mockClear();
  useInvoiceStore.setState({ hasUnsavedChanges: false });
});

function Harness() {
  return (
    <div>
      <a href="/dashboard">Dashboard</a>
      <a href="https://external.example">External</a>
      <UnsavedRouteGuard />
    </div>
  );
}

describe("UnsavedRouteGuard (P19/FE-M3)", () => {
  it("a clean store lets in-app links navigate untouched", async () => {
    const user = userEvent.setup();
    render(<Harness />);

    await user.click(screen.getByRole("link", { name: "Dashboard" }));
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    expect(assignMock).not.toHaveBeenCalled();
  });

  it("a dirty store intercepts the in-app link and asks", async () => {
    const user = userEvent.setup();
    useInvoiceStore.setState({ hasUnsavedChanges: true });
    render(<Harness />);

    await user.click(screen.getByRole("link", { name: "Dashboard" }));

    expect(screen.getByRole("dialog")).toBeInTheDocument();
    expect(assignMock).not.toHaveBeenCalled();
  });

  it("cancel keeps the user on the page with the dirty state intact", async () => {
    const user = userEvent.setup();
    useInvoiceStore.setState({ hasUnsavedChanges: true });
    render(<Harness />);

    await user.click(screen.getByRole("link", { name: "Dashboard" }));
    await user.click(screen.getByRole("button", { name: /stay/i }));

    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    expect(assignMock).not.toHaveBeenCalled();
    expect(useInvoiceStore.getState().hasUnsavedChanges).toBe(true);
  });

  it("confirm clears the dirty flag and navigates", async () => {
    const user = userEvent.setup();
    useInvoiceStore.setState({ hasUnsavedChanges: true });
    render(<Harness />);

    await user.click(screen.getByRole("link", { name: "Dashboard" }));
    await user.click(screen.getByRole("button", { name: /discard and leave/i }));

    expect(useInvoiceStore.getState().hasUnsavedChanges).toBe(false);
    expect(assignMock).toHaveBeenCalledWith("/dashboard");
  });

  it("external links are never intercepted", async () => {
    const user = userEvent.setup();
    useInvoiceStore.setState({ hasUnsavedChanges: true });
    render(<Harness />);

    // The external link's default navigation is not prevented by the
    // guard (jsdom does not navigate for external URLs; the assertion is
    // that no dialog appears).
    await user.click(screen.getByRole("link", { name: "External" }));
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });
});
