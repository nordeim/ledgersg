/**
 * Ledger Hooks - LedgerSG Frontend
 *
 * P6/C-5: the flat line-level general-ledger contract
 * (GET /api/v1/{org_id}/journal-entries/ledger/).
 *
 * P24/FE-M2: the pagination contract — limit/offset ride the query
 * string AND the queryKey (the page identity): without the key a page
 * change would resolve the previous page from cache and the table
 * would silently show the wrong rows.
 */

import { useQuery } from "@tanstack/react-query";
import { api, endpoints } from "@/lib/api-client";

/** One row per journal line (the backend LedgerView contract). */
export interface LedgerLine {
  id: string;
  entry_id: string;
  entry_number: number;
  entry_date: string;
  source_type: string;
  reference: string;
  narration: string;
  line_number: number;
  account_id: string;
  account_code: string;
  account_name: string;
  description: string;
  debit: string;
  credit: string;
}

export interface LedgerResponse {
  results: LedgerLine[];
  count: number;
  /** P24/BE-M1: present only in the paginated mode (limit provided). */
  next?: string | null;
  previous?: string | null;
}

export interface LedgerFilters {
  date_from?: string;
  date_to?: string;
  account_id?: string;
  source_type?: string;
}

/** P24/FE-M2: the page request (limit/offset over the backend contract). */
export interface LedgerPage {
  limit: number;
  offset: number;
}

export function useLedger(
  orgId: string | null | undefined,
  filters?: LedgerFilters,
  page?: LedgerPage
) {
  const params = new URLSearchParams();
  if (filters) {
    for (const [key, value] of Object.entries(filters)) {
      if (value) params.set(key, value);
    }
  }
  if (page) {
    params.set("limit", String(page.limit));
    params.set("offset", String(page.offset));
  }
  const queryString = params.toString() ? `?${params.toString()}` : "";

  return useQuery({
    // The page identity MUST live in the key (P24/FE-L1) — pages are
    // distinct cache entries, never served from each other's cache.
    queryKey: [orgId, "ledger", filters ?? null, page ?? null],
    queryFn: async () => {
      const response = await api.get<LedgerResponse>(
        endpoints.journal(orgId as string).ledger + queryString
      );
      return response;
    },
    enabled: !!orgId,
    placeholderData: (previous) => previous,
  });
}
