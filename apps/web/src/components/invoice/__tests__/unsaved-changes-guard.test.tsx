/**
 * Unsaved-changes guard (P17/FE-M4).
 *
 * The store's hasUnsavedChanges was WRITTEN (invoice-form.tsx) but never
 * READ: no beforeunload listener, no navigation guard — a user typing a
 * long invoice who closes the tab lost everything silently. The guard is
 * a hook the form owns (src/hooks/use-unsaved-changes-guard.ts), driven
 * by the store the form already writes.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import React from "react";
import { render, screen, act } from "@/__tests__/utils";
import userEvent from "@testing-library/user-event";
import { useInvoiceStore } from "@/stores/invoice-store";
import { useUnsavedChangesGuard } from "@/hooks/use-unsaved-changes-guard";

function Probe() {
  useUnsavedChangesGuard();
  return (
    <div>
      <button
        type="button"
        onClick={() => useInvoiceStore.getState().setHasUnsavedChanges(true)}
      >
        mark dirty
      </button>
      <button
        type="button"
        onClick={() => useInvoiceStore.getState().setHasUnsavedChanges(false)}
      >
        mark clean
      </button>
    </div>
  );
}

function dispatchBeforeUnload() {
  const ev = new Event("beforeunload", { cancelable: true });
  // lib.dom types returnValue as boolean (legacy); the runtime contract
  // is "any truthy value requests the dialog" — assign via a record cast.
  (ev as unknown as Record<string, unknown>).returnValue = undefined;
  window.dispatchEvent(ev);
  // jsdom's dispatchEvent return semantics differ from browsers — the
  // contract under test is the returnValue the handler sets (the
  // browser shows the dialog iff it is truthy).
  return { ev: ev as unknown as { returnValue: unknown } };
}

describe("unsaved-changes guard (P17/FE-M4)", () => {
  beforeEach(() => {
    useInvoiceStore.getState().setHasUnsavedChanges(false);
  });

  afterEach(() => {
    useInvoiceStore.getState().setHasUnsavedChanges(false);
  });

  it("warns on beforeunload ONLY while dirty", async () => {
    const { unmount } = render(<Probe />);

    // Clean: no warning requested.
    let { ev } = dispatchBeforeUnload();
    expect(ev.returnValue ?? "").not.toBeTruthy();

    // Dirty: the handler requests the confirmation dialog.
    await userEvent.click(screen.getByRole("button", { name: "mark dirty" }));
    ({ ev } = dispatchBeforeUnload());
    expect(String(ev.returnValue)).toBeTruthy();

    // Clean again: the warning clears.
    await userEvent.click(screen.getByRole("button", { name: "mark clean" }));
    ({ ev } = dispatchBeforeUnload());
    expect(ev.returnValue ?? "").not.toBeTruthy();
    unmount();
  });

  it("removes the listener on unmount (no cross-page leakage)", () => {
    const addSpy = vi.spyOn(window, "addEventListener");
    const removeSpy = vi.spyOn(window, "removeEventListener");
    const { unmount } = render(<Probe />);
    expect(
      addSpy.mock.calls.some(([type]) => type === "beforeunload")
    ).toBe(true);
    unmount();
    expect(
      removeSpy.mock.calls.some(([type]) => type === "beforeunload")
    ).toBe(true);
  });

  it("the guard stays consistent across re-renders", () => {
    const { rerender } = render(<Probe />);
    act(() => {
      useInvoiceStore.getState().setHasUnsavedChanges(true);
    });
    rerender(<Probe />);
    const { ev } = dispatchBeforeUnload();
    expect(String(ev.returnValue)).toBeTruthy();
  });
});
