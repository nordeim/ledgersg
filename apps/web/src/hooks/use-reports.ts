/**
 * Reports Hooks - LedgerSG Frontend
 *
 * P8/R-7: the real report contracts — financial statements
 * (GET /reports/financial/), aged receivables/payables (GET
 * /reports/aged/) and the GST F5 return lifecycle (POST generate/file on
 * /gst/returns/). The pre-P8 page was a static shell and its only GST
 * hook pointed at an endpoint that never existed (/gst/f5-compute/ —
 * deleted with this change).
 */

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, endpoints } from "@/lib/api-client";
import { toast } from "@/hooks/use-toast";

// ---------------------------------------------------------------------------
// Financial statements
// ---------------------------------------------------------------------------

export interface FinancialReportLine {
  account_code: string;
  account_name: string;
  amount: string;
}

export interface ProfitLossData {
  sections: { revenue: FinancialReportLine[]; expenses: FinancialReportLine[] };
  revenue_total: string;
  expense_total: string;
  net_profit: string;
}

export interface BalanceSheetData {
  sections: {
    assets: FinancialReportLine[];
    liabilities: FinancialReportLine[];
    equity: FinancialReportLine[];
  };
  assets_total: string;
  liabilities_total: string;
  equity_total: string;
  retained_earnings: string;
  balanced: boolean;
}

export interface TrialBalanceLine {
  account_id: string;
  account_code: string;
  account_name: string;
  account_type: string;
  total_debits: string;
  total_credits: string;
  balance: string;
}

export interface TrialBalanceData {
  lines: TrialBalanceLine[];
  totals: {
    total_debits: string;
    total_credits: string;
    balanced: boolean;
  };
}

export type FinancialReportType = "profit_loss" | "balance_sheet" | "trial_balance";

export interface FinancialReportParams {
  start_date?: string;
  end_date?: string;
  as_at_date?: string;
}

export function useFinancialReport(
  orgId: string | null | undefined,
  reportType: FinancialReportType,
  params: FinancialReportParams = {}
) {
  const search = new URLSearchParams({ report_type: reportType });
  for (const [key, value] of Object.entries(params)) {
    if (value) search.set(key, value);
  }
  return useQuery({
    queryKey: [orgId, "reports", "financial", reportType, params],
    queryFn: async () => {
      const response = await api.get<{
        report_type: string;
        period_start?: string | null;
        period_end?: string | null;
        as_at_date?: string | null;
        currency: string;
        data: ProfitLossData & BalanceSheetData & TrialBalanceData;
      }>(`${endpoints.reports(orgId as string).financial}?${search.toString()}`);
      return response;
    },
    enabled: !!orgId,
  });
}

// ---------------------------------------------------------------------------
// Aged receivables / payables
// ---------------------------------------------------------------------------

export interface AgedRow {
  contact_id: string;
  contact_name: string;
  document_count: number;
  outstanding_total: string;
  current: string;
  d1_30: string;
  d31_60: string;
  d61_90: string;
  d90_plus: string;
}

export interface AgedReportData {
  type: string;
  as_at: string;
  results: AgedRow[];
  totals: Omit<AgedRow, "contact_id" | "contact_name">;
}

export function useAgedReport(
  orgId: string | null | undefined,
  type: "receivables" | "payables",
  asAt?: string
) {
  const search = new URLSearchParams({ type });
  if (asAt) search.set("as_at", asAt);
  return useQuery({
    queryKey: [orgId, "reports", "aged", type, asAt],
    queryFn: async () =>
      api.get<AgedReportData>(
        `${endpoints.reports(orgId as string).aged}?${search.toString()}`
      ),
    enabled: !!orgId,
  });
}

// ---------------------------------------------------------------------------
// GST returns (F5)
// ---------------------------------------------------------------------------

export interface GSTReturnRow {
  id: string;
  return_type: string;
  period_start: string;
  period_end: string;
  filing_due_date: string;
  status: string;
  days_until_due: number;
  net_gst: string;
}

export function useGSTReturns(orgId: string | null | undefined, year?: number) {
  const search = year ? `?year=${year}` : "";
  return useQuery({
    queryKey: [orgId, "gst", "returns", year],
    queryFn: async () =>
      api.get<{ results: GSTReturnRow[]; count: number }>(
        `${endpoints.gst(orgId as string).returns}${search}`
      ),
    enabled: !!orgId,
  });
}

export interface GSTReturnDetail {
  id: string;
  return_type: string;
  period_start: string;
  period_end: string;
  filing_due_date: string;
  status: string;
  notes: string;
  boxes: Record<string, string>;
  computed_at: string | null;
  filed_at: string | null;
}

export function useGSTReturn(orgId: string | null | undefined, returnId: string | null) {
  return useQuery({
    queryKey: [orgId, "gst", "return", returnId],
    queryFn: async () =>
      api.get<GSTReturnDetail>(
        endpoints.gst(orgId as string).returnDetail(returnId as string)
      ),
    enabled: !!orgId && !!returnId,
  });
}

/** POST /gst/returns/ — create DRAFT period shells (filing_frequency + periods). */
export function useCreateGSTReturnPeriods(orgId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (payload: {
      filing_frequency: "MONTHLY" | "QUARTERLY";
      start_date: string;
      periods?: number;
    }) => api.post(endpoints.gst(orgId).returns, payload),
    onSuccess: () => {
      toast({
        title: "Return periods created",
        description: "Draft GST return periods are ready to compute.",
        variant: "success",
      });
      queryClient.invalidateQueries({ queryKey: [orgId, "gst", "returns"] });
    },
    onError: (error: Error) => {
      toast({
        title: "Failed to create return periods",
        description: error.message,
        variant: "error",
      });
    },
  });
}

/** POST /gst/returns/{id}/?force=true — (re)compute the F5 boxes. */
export function useGenerateGSTReturn(orgId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (returnId: string) =>
      api.post(`${endpoints.gst(orgId).returnDetail(returnId)}?force=true`, {}),
    onSuccess: () => {
      toast({
        title: "GST return computed",
        description: "The F5 boxes have been recalculated from your documents.",
        variant: "success",
      });
      queryClient.invalidateQueries({ queryKey: [orgId, "gst"] });
    },
    onError: (error: Error) => {
      toast({
        title: "Computation failed",
        description: error.message,
        variant: "error",
      });
    },
  });
}

/** POST /gst/returns/{id}/file/ — file with the IRAS. */
export function useFileGSTReturn(orgId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (payload: {
      returnId: string;
      filing_reference?: string;
    }) => {
      const { returnId, ...body } = payload;
      return api.post(endpoints.gst(orgId).returnFile(returnId), body);
    },
    onSuccess: () => {
      toast({
        title: "GST return filed",
        description: "Your F5 return has been marked as filed.",
        variant: "success",
      });
      queryClient.invalidateQueries({ queryKey: [orgId, "gst"] });
    },
    onError: (error: Error) => {
      toast({
        title: "Filing failed",
        description: error.message,
        variant: "error",
      });
    },
  });
}
