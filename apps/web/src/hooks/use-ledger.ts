/**
 * Ledger Hooks - LedgerSG Frontend
 *
 * P6/C-5: the flat line-level general-ledger contract
 * (GET /api/v1/{org_id}/journal-entries/ledger/).
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
}

export interface LedgerFilters {
  date_from?: string;
  date_to?: string;
  account_id?: string;
  source_type?: string;
}

export function useLedger(
  orgId: string | null | undefined,
  filters?: LedgerFilters
) {
  const queryString = filters
    ? "?" +
      new URLSearchParams(
        Object.entries(filters).filter(([, v]) => v)
      ).toString()
    : "";

  return useQuery({
    queryKey: [orgId, "ledger", filters],
    queryFn: async () => {
      const response = await api.get<LedgerResponse>(
        endpoints.journal(orgId as string).ledger + queryString
      );
      return response;
    },
    enabled: !!orgId,
  });
}
