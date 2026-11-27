"use client";

import * as React from "react";

import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { useInvoiceStore } from "@/stores/invoice-store";

/**
 * The in-app unsaved-work route guard (P19/FE-M3 — the P16/P17/P18
 * deferred register's route-guard item).
 *
 * The P17 beforeunload guard only covered tab-close/browser navigation:
 * a click on a sidebar Link (client-side navigation) silently discarded
 * a dirty invoice — the exact failure mode the guard existed to prevent,
 * one surface over. Next.js 16 ships no usePrompt/useBlocker, so the
 * guard is a document-level CAPTURE-phase click listener:
 *
 * - active only while the invoice store is dirty (mounted with the form);
 * - intercepts primary-button clicks (no ctrl/cmd/shift/alt — modified
 *   clicks open new tabs and never lose state) on same-app anchor hrefs
 *   (absolute URLs, hashes, mailto/tel/javascript pass through);
 * - preventDefault + stopPropagation in the capture phase means neither
 *   Next's Link handler nor the native default runs — the dialog decides;
 * - confirm clears the dirty flag FIRST (the beforeunload guard must not
 *   block the intentional full navigation) then window.location.assign;
 * - cancel simply closes — the form state was never touched.
 */
export function UnsavedRouteGuard() {
  const hasUnsavedChanges = useInvoiceStore((s) => s.hasUnsavedChanges);
  const setHasUnsavedChanges = useInvoiceStore((s) => s.setHasUnsavedChanges);
  const [pendingHref, setPendingHref] = React.useState<string | null>(null);

  React.useEffect(() => {
    if (!hasUnsavedChanges) {
      return;
    }

    const onClickCapture = (e: MouseEvent) => {
      if (e.defaultPrevented) return;
      // Primary-button plain clicks only — modified clicks open new
      // tabs/windows and never discard the current form.
      if (e.button !== 0 || e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) {
        return;
      }
      const target = e.target as HTMLElement | null;
      const anchor = target?.closest?.("a[href]") as HTMLAnchorElement | null;
      if (!anchor) return;
      const href = anchor.getAttribute("href");
      if (!href) return;
      if (
        href.startsWith("#") ||
        /^(mailto:|tel:|javascript:|data:|blob:|https?:)/i.test(href)
      ) {
        return;
      }
      // A same-app path href — the guard surface.
      e.preventDefault();
      e.stopPropagation();
      setPendingHref(href);
    };

    document.addEventListener("click", onClickCapture, true);
    return () => {
      document.removeEventListener("click", onClickCapture, true);
    };
  }, [hasUnsavedChanges]);

  const confirmLeave = () => {
    const href = pendingHref;
    setHasUnsavedChanges(false);
    setPendingHref(null);
    if (href) {
      // A full navigation (not a client-side push): the current form is
      // being discarded by explicit user decision.
      window.location.assign(href);
    }
  };

  const stay = () => setPendingHref(null);

  return (
    <Dialog
      open={pendingHref !== null}
      onOpenChange={(open) => {
        if (!open) stay();
      }}
    >
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle>Discard unsaved changes?</DialogTitle>
          <DialogDescription>
            You have unsaved changes on this form. Leaving the page will
            discard them.
          </DialogDescription>
        </DialogHeader>
        <DialogFooter>
          <Button type="button" variant="outline" className="rounded-sm" onClick={stay}>
            Stay on this page
          </Button>
          <Button
            type="button"
            className="rounded-sm bg-alert text-void hover:bg-alert/90"
            onClick={confirmLeave}
          >
            Discard and leave
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
