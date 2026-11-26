"use client";

import { useEffect } from "react";

import { useInvoiceStore } from "@/stores/invoice-store";

/**
 * Unsaved-changes guard (P17/FE-M4).
 *
 * The store's hasUnsavedChanges was written (invoice-form.tsx) but never
 * read — closing the tab mid-edit silently discarded the work. This hook
 * owns the read side: while the form is mounted, a beforeunload listener
 * requests the browser's leave-confirmation when (and only when) the
 * store is dirty. Unmounting removes the listener so no other page
 * inherits the warning.
 *
 * In-app route navigation stays intentionally unguarded for now: the
 * shell nav is a known exit surface, and intercepting Next's client
 * navigation requires a router-level guard (the `Link`-wrapper or
 * `usePrompt` pattern). Registered in the P17 deferred list.
 */
export function useUnsavedChangesGuard(): void {
  useEffect(() => {
    const handler = (event: BeforeUnloadEvent) => {
      if (!useInvoiceStore.getState().hasUnsavedChanges) {
        // Clean: explicitly leave the default (no dialog).
        delete event.returnValue;
        return;
      }
      // The modern contract: preventDefault + any truthy returnValue
      // (Chrome requires returnValue; Safari requires preventDefault).
      event.preventDefault();
      event.returnValue =
        "You have unsaved changes. Leaving this page will discard them.";
    };

    window.addEventListener("beforeunload", handler);
    return () => {
      window.removeEventListener("beforeunload", handler);
    };
  }, []);
}
