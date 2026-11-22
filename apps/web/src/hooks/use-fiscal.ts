"use client";

/**
 * Fiscal year & period hooks (P10/M-8).
 *
 * The endpoints existed backend-side (list years/periods, close year,
 * close period — plus the new open period) with ZERO frontend consumers;
 * the invoice-approval error "Please open the fiscal period or change the
 * invoice date" pointed at an action no surface could perform.
 */

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api, endpoints } from "@/lib/api-client";
import { toast } from "@/hooks/use-toast";

/** FiscalYearSerializer (GET /fiscal-years/ wraps the list in `data`). */
export interface FiscalYearRow {
  id: string;
  label: string;
  start_date: string;
  end_date: string;
  is_closed: boolean;
  closed_at: string | null;
  created_at: string;
}

/** The periods list view's row shape (FiscalPeriodListView). */
export interface FiscalPeriodRow {
  id: string;
  name: string;
  start_date: string;
  end_date: string;
  status: "OPEN" | "CLOSED";
  fiscal_year_id: string;
}

interface FiscalYearsResponse {
  data: FiscalYearRow[];
  count: number;
}

interface FiscalPeriodsResponse {
  results: FiscalPeriodRow[];
  count: number;
}

export function useFiscalYears(orgId: string | null) {
  return useQuery({
    queryKey: [orgId, "fiscal-years"],
    queryFn: async () => {
      return api.get<FiscalYearsResponse>(endpoints.fiscal(orgId!).years);
    },
    enabled: !!orgId,
  });
}

export function useFiscalPeriods(orgId: string | null) {
  return useQuery({
    queryKey: [orgId, "fiscal-periods"],
    queryFn: async () => {
      return api.get<FiscalPeriodsResponse>(endpoints.fiscal(orgId!).periods);
    },
    enabled: !!orgId,
  });
}

function useFiscalMutation<TArg>(
  orgId: string,
  mutationFn: (arg: TArg) => Promise<unknown>,
  successTitle: string,
  errorTitle: string
) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn,
    onSuccess: () => {
      toast({ title: successTitle, variant: "success" });
      queryClient.invalidateQueries({ queryKey: [orgId, "fiscal-periods"] });
      queryClient.invalidateQueries({ queryKey: [orgId, "fiscal-years"] });
    },
    onError: (error: Error) => {
      toast({
        title: errorTitle,
        description: error.message || "Please try again.",
        variant: "error",
      });
    },
  });
}

/** P10/M-8: open a closed period (manager-gated server-side). */
export function useOpenFiscalPeriod(orgId: string) {
  return useFiscalMutation<string>(
    orgId,
    (periodId) => api.post(endpoints.fiscal(orgId).openPeriod(periodId)),
    "Fiscal period opened",
    "Failed to open fiscal period"
  );
}

export function useCloseFiscalPeriod(orgId: string) {
  return useFiscalMutation<string>(
    orgId,
    (periodId) => api.post(endpoints.fiscal(orgId).closePeriod(periodId)),
    "Fiscal period closed",
    "Failed to close fiscal period"
  );
}

/** Close a year — the backend 400s (naming the open periods) until every
 * period under it is closed; the toast surfaces that message. */
export function useCloseFiscalYear(orgId: string) {
  return useFiscalMutation<string>(
    orgId,
    (yearId) => api.post(endpoints.fiscal(orgId).closeYear(yearId)),
    "Fiscal year closed",
    "Failed to close fiscal year"
  );
}
