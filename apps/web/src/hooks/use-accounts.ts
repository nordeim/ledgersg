/**
 * Accounts Hooks - LedgerSG Frontend (P3/D-1)
 *
 * Lists the organisation's chart-of-accounts entries for the invoice
 * form's per-line posting-account select (the backend `add_line` contract
 * requires an `account_id` per line).
 *
 * `account_type` is the plain varchar on `coa.account` (e.g. "REVENUE") —
 * filtering happens server-side (`GET /api/v1/{org}/accounts/?account_type=…`).
 */

import { useQuery } from "@tanstack/react-query";
import { api, endpoints } from "@/lib/api-client";

export interface AccountOption {
  id: string;
  code: string;
  name: string;
  account_type: string;
  is_active: boolean;
  /** True for bank-eligible ledger accounts (the seeded 1100 series) —
   * the bank-account dialog's GL picker filters on it (P9/B-4). */
  is_bank: boolean;
}

export function useAccounts(
  orgId: string | null,
  filters?: {
    account_type?: string;
    is_active?: boolean;
    /** Bank-type accounts (the seeded 1100 series) — the bank-account
     * dialog's GL picker (P9/B-4). Server-side filter; children included. */
    is_bank?: boolean;
  }
) {
  const queryString = filters
    ? "?" +
      new URLSearchParams(
        Object.entries(filters).filter(([, v]) => v !== undefined) as [string, string][]
      ).toString()
    : "";

  return useQuery({
    queryKey: [orgId, "accounts", filters],
    queryFn: async () => {
      const response = await api.get<{
        results: AccountOption[];
        count: number;
      }>(endpoints.accounts(orgId as string).list + queryString);
      return response.results;
    },
    enabled: !!orgId,
  });
}

/** Revenue-side accounts for invoice lines (sales postings). */
export function useRevenueAccounts(orgId: string | null) {
  return useAccounts(orgId, { account_type: "REVENUE", is_active: true });
}
