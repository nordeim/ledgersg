/**
 * P24/FE-M2 (the shared pagination control) — RED suite.
 *
 * The ledger pages through the backend's new `?limit=&offset=` contract;
 * this is the shared accessible control every table surface will reuse.
 * Contract: a "Showing x–y of z" summary (aria-live polite), real
 * Previous/Next buttons with disabled states at the boundaries, and
 * onPageChange(offset) callbacks with offset math.
 */

import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@/__tests__/utils";
import { TablePagination } from "../table-pagination";

function setup(props: Partial<Parameters<typeof TablePagination>[0]> = {}) {
  const onPageChange = vi.fn();
  render(
    <TablePagination
      offset={0}
      limit={50}
      count={51}
      onPageChange={onPageChange}
      {...props}
    />
  );
  return { onPageChange };
}

describe("TablePagination", () => {
  describe("The summary math", () => {
    it("renders the first-page summary 'Showing 1–50 of 51'", () => {
      setup({ offset: 0, limit: 50, count: 51 });
      expect(
        screen.getByText("Showing 1–50 of 51 rows")
      ).toBeInTheDocument();
    });

    it("renders the partial last-page summary 'Showing 51–51 of 51'", () => {
      setup({ offset: 50, limit: 50, count: 51 });
      expect(
        screen.getByText("Showing 51–51 of 51 rows")
      ).toBeInTheDocument();
    });

    it("renders the empty-set summary without a range error", () => {
      setup({ offset: 0, limit: 50, count: 0 });
      expect(
        screen.getByText("Showing 0–0 of 0 rows")
      ).toBeInTheDocument();
    });

    // P25/FE-L2: a page beyond the end (the set shrank server-side
    // between fetches) must not render a nonsensical "41–40" range —
    // the truthful summary is 0–0 with the controls as the way back.
    it("renders the beyond-end page summary 'Showing 0–0 of N' (never 41–40)", () => {
      setup({ offset: 40, limit: 20, count: 40 });
      expect(
        screen.getByText("Showing 0–0 of 40 rows")
      ).toBeInTheDocument();
      expect(
        screen.getByRole("button", { name: /previous page/i })
      ).not.toBeDisabled();
    });

    it("the summary is a polite live region (page changes announce)", () => {
      setup({ offset: 0, limit: 50, count: 51 });
      const summary = screen.getByText("Showing 1–50 of 51 rows");
      expect(summary).toHaveAttribute("aria-live", "polite");
    });
  });

  describe("The boundary disabled states", () => {
    it("disables Previous on the first page (offset 0)", () => {
      setup({ offset: 0, limit: 50, count: 51 });
      expect(
        screen.getByRole("button", { name: /previous page/i })
      ).toBeDisabled();
    });

    it("enables Previous past the first page", () => {
      setup({ offset: 50, limit: 50, count: 51 });
      expect(
        screen.getByRole("button", { name: /previous page/i })
      ).not.toBeDisabled();
    });

    it("disables Next when the page covers the end", () => {
      setup({ offset: 50, limit: 50, count: 51 });
      expect(
        screen.getByRole("button", { name: /next page/i })
      ).toBeDisabled();
    });

    it("enables Next while more rows exist", () => {
      setup({ offset: 0, limit: 50, count: 51 });
      expect(
        screen.getByRole("button", { name: /next page/i })
      ).not.toBeDisabled();
    });

    it("disables both buttons for an empty set", () => {
      setup({ offset: 0, limit: 50, count: 0 });
      expect(
        screen.getByRole("button", { name: /previous page/i })
      ).toBeDisabled();
      expect(screen.getByRole("button", { name: /next page/i })).toBeDisabled();
    });
  });

  describe("The page-change callbacks (offset math)", () => {
    it("Next fires onPageChange with offset + limit", () => {
      const { onPageChange } = setup({ offset: 0, limit: 50, count: 51 });
      fireEvent.click(screen.getByRole("button", { name: /next page/i }));
      expect(onPageChange).toHaveBeenCalledWith(50);
    });

    it("Previous fires onPageChange clamped at 0", () => {
      const { onPageChange } = setup({ offset: 50, limit: 50, count: 51 });
      fireEvent.click(screen.getByRole("button", { name: /previous page/i }));
      expect(onPageChange).toHaveBeenCalledWith(0);
    });

    it("Previous fires onPageChange with offset − limit mid-set", () => {
      const { onPageChange } = setup({ offset: 100, limit: 50, count: 200 });
      fireEvent.click(screen.getByRole("button", { name: /previous page/i }));
      expect(onPageChange).toHaveBeenCalledWith(50);
    });
  });

  describe("Accessibility", () => {
    it("exposes the pagination landmark", () => {
      setup({ offset: 0, limit: 50, count: 51 });
      expect(
        screen.getByRole("navigation", { name: "Pagination" })
      ).toBeInTheDocument();
    });

    // P25/FE-L1: WCAG 2.5.3 Label in Name — the accessible name must
    // CONTAIN the visible text ("Previous"/"Next"), or speech-input users
    // saying "click Previous" get no match. The exact-string query pins
    // the whole accessible name (a "Go to previous page" label fails it).
    it("the accessible names contain the visible text (WCAG 2.5.3 Label in Name)", () => {
      setup({ offset: 0, limit: 50, count: 51 });
      expect(
        screen.getByRole("button", { name: "Previous page" })
      ).toBeInTheDocument();
      expect(
        screen.getByRole("button", { name: "Next page" })
      ).toBeInTheDocument();
    });
  });
});
