import * as React from "react";
import { ChevronLeft, ChevronRight } from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

/**
 * TABLE PAGINATION (P24/FE-M2)
 *
 * The shared page control for the server-side `?limit=&offset=` list
 * contract: a "Showing x–y of z" summary (a polite live region — page
 * changes announce), real Previous/Next buttons with disabled states at
 * the boundaries, and an onPageChange(offset) callback driven by offset
 * math. The ledger is the first consumer; every table surface reuses it.
 */

export interface TablePaginationProps {
  /** The current page's offset (rows already skipped). */
  offset: number;
  /** The page size the caller requests. */
  limit: number;
  /** The TOTAL matching rows (the envelope's count — not the page size). */
  count: number;
  /** Fires with the new offset (clamped at 0 at the set's start). */
  onPageChange: (offset: number) => void;
  /** Disables both buttons while the page is in flight. */
  disabled?: boolean;
  className?: string;
}

export function TablePagination({
  offset,
  limit,
  count,
  onPageChange,
  disabled = false,
  className,
}: TablePaginationProps) {
  const start = count === 0 ? 0 : offset + 1;
  const end = Math.min(offset + limit, count);
  const onFirstPage = offset <= 0;
  const onLastPage = offset + limit >= count;

  return (
    <nav aria-label="Pagination" className={cn("flex items-center justify-between gap-4", className)}>
      <p aria-live="polite" className="text-sm text-text-secondary">
        Showing {start}–{end} of {count} rows
      </p>
      <div className="flex items-center gap-2">
        <Button
          variant="outline"
          size="sm"
          onClick={() => onPageChange(Math.max(0, offset - limit))}
          disabled={disabled || onFirstPage}
          aria-label="Go to previous page"
        >
          <ChevronLeft className="h-4 w-4" aria-hidden="true" />
          <span>Previous</span>
        </Button>
        <Button
          variant="outline"
          size="sm"
          onClick={() => onPageChange(offset + limit)}
          disabled={disabled || onLastPage}
          aria-label="Go to next page"
        >
          <span>Next</span>
          <ChevronRight className="h-4 w-4" aria-hidden="true" />
        </Button>
      </div>
    </nav>
  );
}
