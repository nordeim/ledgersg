/**
 * Tax Code Hooks - LedgerSG Frontend (P3/D-3)
 *
 * Provides the invoice form with the tax-code rate rows IN FORCE on the
 * document's date — the P2 backend contract
 * (`GET /api/v1/{org}/gst/tax-codes/?effective_on=YYYY-MM-DD`, one row per
 * code, org rows shadowing system rows). The client-side preview then uses
 * the server-resolved rate instead of the hardcoded 9% map, so backdated
 * documents (SR was 8% in 2023) and org-custom rates preview correctly.
 *
 * Fallback contract: when there is no org id or the API is unreachable
 * (backend-less default e2e runs), `data` stays undefined and callers fall
 * back to the static list — green by default.
 */

import { useQuery } from "@tanstack/react-query";
import { api, endpoints } from "@/lib/api-client";
import { TAX_CODES, type TaxCode } from "@/shared/schemas/invoice";

export interface ResolvedTaxCode {
  id: string;
  code: TaxCode;
  name: string;
  rate: string;
}

/** Static fallback mirroring the schema's TAX_CODES with today's rates. */
export const FALLBACK_TAX_CODES: ResolvedTaxCode[] = TAX_CODES.map((code) => ({
  id: code, // no server row behind it — id is the code itself
  code,
  name: code,
  rate:
    code === "SR" || code === "TX" || code === "BL" || code === "RS"
      ? "0.09"
      : "0",
}));

export function useTaxCodes(orgId: string | null, effectiveOn?: string) {
  return useQuery({
    queryKey: [orgId, "tax-codes", effectiveOn ?? "today"],
    queryFn: async () => {
      const base = endpoints.gst(orgId as string).taxCodes;
      const url = effectiveOn ? `${base}?effective_on=${effectiveOn}` : base;
      const response = await api.get<{
        results: Array<{
          id: string;
          code: string;
          name: string;
          rate: string;
        }>;
        count: number;
      }>(url);
      return response.results as ResolvedTaxCode[];
    },
    enabled: !!orgId,
    // Rate history is small and date-keyed; a stale list would show the
    // wrong rates for a changed document date.
    staleTime: 0,
  });
}
