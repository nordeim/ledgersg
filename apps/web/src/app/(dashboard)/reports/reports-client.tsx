"use client";

import * as React from "react";
import {
  AlertTriangle,
  Loader2,
  Building2,
  ShieldAlert,
  CheckCircle2,
} from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { useAuth } from "@/providers/auth-provider";
import {
  useFinancialReport,
  useAgedReport,
  useGSTReturns,
  useGenerateGSTReturn,
  useFileGSTReturn,
  useReviewGSTReturn,
  useAmendGSTReturn,
  useCreateGSTReturnPeriods,
  useGSTDeadlines,
  useGSTReturn,
  type FinancialReportLine,
} from "@/hooks/use-reports";
import { ApiError } from "@/lib/api-client";

/**
 * Real reports page (P8/R-7 — replaced the static Generate-button shell).
 * Statements, the GST F5 lifecycle and aged AR/AP all read live data.
 */

function todayISO(): string {
  return new Date().toISOString().slice(0, 10);
}

function firstOfYearISO(): string {
  return `${new Date().getFullYear()}-01-01`;
}

function formatAmount(value: string | undefined): string {
  if (value === undefined) return "—";
  const n = Number(value);
  if (Number.isNaN(n)) return value;
  return n.toLocaleString("en-SG", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

function StatusBadge({ status }: { status: string }) {
  const variant =
    status === "FILED"
      ? "default"
      : status === "COMPUTED" || status === "REVIEWED"
        ? "secondary"
        : status === "AMENDED"
          ? "outline"
          : "destructive";
  return <Badge variant={variant}>{status}</Badge>;
}

function ReportRows({ lines, amountLabel }: { lines: FinancialReportLine[]; amountLabel: string }) {
  if (lines.length === 0) {
    return (
      <p className="py-6 text-center text-sm text-text-secondary">
        No activity in this period.
      </p>
    );
  }
  return (
    <table className="w-full text-sm">
      <thead>
        <tr className="border-b border-border text-left text-text-muted">
          <th scope="col" className="py-2 pr-4 font-medium">Code</th>
          <th scope="col" className="py-2 pr-4 font-medium">Account</th>
          <th scope="col" className="py-2 text-right font-medium">{amountLabel}</th>
        </tr>
      </thead>
      <tbody>
        {lines.map((line) => (
          <tr key={line.account_code} className="border-b border-border/50">
            <td className="py-2 pr-4 font-mono text-xs text-text-secondary">{line.account_code}</td>
            <td className="py-2 pr-4 text-text-primary">{line.account_name}</td>
            <td className="py-2 text-right font-mono text-text-primary">
              {formatAmount(line.amount)}
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

export function ReportsClient() {
  const { currentOrg, isLoading: authLoading, hasPermission } = useAuth();
  const orgId = currentOrg?.id ?? null;

  const [startDate, setStartDate] = React.useState(firstOfYearISO());
  const [endDate, setEndDate] = React.useState(todayISO());
  const [asAt, setAsAt] = React.useState(todayISO());

  const pl = useFinancialReport(orgId, "profit_loss", {
    start_date: startDate,
    end_date: endDate,
  });
  const bs = useFinancialReport(orgId, "balance_sheet", { as_at_date: asAt });
  const tb = useFinancialReport(orgId, "trial_balance", { as_at_date: asAt });
  const agedAr = useAgedReport(orgId, "receivables", asAt);
  const agedAp = useAgedReport(orgId, "payables", asAt);
  const gstYear = React.useMemo(() => new Date(asAt).getFullYear(), [asAt]);
  const gstReturns = useGSTReturns(orgId, gstYear);
  const generateReturn = useGenerateGSTReturn(orgId ?? "");
  const fileReturn = useFileGSTReturn(orgId ?? "");
  // P10/H-3: the full F5 lifecycle — review/amend actions, the deadlines
  // banner, and period creation from the UI (the hooks existed; only
  // compute/file were wired, and the computed boxes never rendered).
  const reviewReturn = useReviewGSTReturn(orgId ?? "");
  const amendReturn = useAmendGSTReturn(orgId ?? "");
  const createPeriods = useCreateGSTReturnPeriods(orgId ?? "");
  const gstDeadlines = useGSTDeadlines(orgId);
  const [amending, setAmending] = React.useState<string | null>(null);
  const [showCreatePeriods, setShowCreatePeriods] = React.useState(false);
  const [expandedBoxes, setExpandedBoxes] = React.useState<string | null>(null);

  if (authLoading) {
    return (
      <div className="flex items-center justify-center gap-2 py-24 text-text-secondary">
        <Loader2 className="h-5 w-5 animate-spin" />
        <span>Loading reports…</span>
      </div>
    );
  }

  // P7/F-12: an authenticated user with no organisation is not an error.
  if (!currentOrg) {
    return (
      <Card className="border-border bg-carbon">
        <CardContent className="flex flex-col items-center gap-3 py-16">
          <Building2 className="h-8 w-8 text-accent-secondary" />
          <p className="font-medium text-text-primary">No organisation selected</p>
          <p className="text-sm text-text-secondary">
            Select an organisation to view its reports.
          </p>
        </CardContent>
      </Card>
    );
  }
  // P11/L-1: Review/File/Amend are the GST-filer's acts — members saw the
  // buttons and got 403 error toasts (the backend gates can_file_gst).
  // Computed after the no-org guard: permission checks need the org context.
  const canFileGst = hasPermission("can_file_gst");

  const reportsPermissionError = [pl, bs, tb, agedAr, agedAp].some(
    (q) => q.error instanceof ApiError && (q.error as ApiError).status === 403
  );
  if (reportsPermissionError) {
    return (
      <Card className="border-border bg-carbon">
        <CardContent className="flex flex-col items-center gap-3 py-16">
          <ShieldAlert className="h-8 w-8 text-alert" />
          <p className="font-medium text-text-primary">Reports permission required</p>
          <p className="text-sm text-text-secondary">
            Your role does not include the reports permission. Ask a manager to
            grant <code>can_view_reports</code>.
          </p>
        </CardContent>
      </Card>
    );
  }

  const dateControls = (
    <div className="flex flex-wrap items-end gap-4">
      <div className="space-y-1">
        <label htmlFor="report-start" className="text-xs font-medium text-text-secondary">
          From
        </label>
        <Input
          id="report-start"
          type="date"
          value={startDate}
          onChange={(e) => setStartDate(e.target.value)}
          className="h-9 w-40 border-border bg-surface"
        />
      </div>
      <div className="space-y-1">
        <label htmlFor="report-end" className="text-xs font-medium text-text-secondary">
          To
        </label>
        <Input
          id="report-end"
          type="date"
          value={endDate}
          onChange={(e) => setEndDate(e.target.value)}
          className="h-9 w-40 border-border bg-surface"
        />
      </div>
      <div className="space-y-1">
        <label htmlFor="report-as-at" className="text-xs font-medium text-text-secondary">
          As at
        </label>
        <Input
          id="report-as-at"
          type="date"
          value={asAt}
          onChange={(e) => setAsAt(e.target.value)}
          className="h-9 w-40 border-border bg-surface"
        />
      </div>
    </div>
  );

  const plData = pl.data?.data;
  const bsData = bs.data?.data;
  const tbData = tb.data?.data;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="font-display text-2xl font-bold text-text-primary">Reports</h1>
          <p className="text-sm text-text-secondary mt-1">
            Statements, GST F5 returns and ageing — computed from your books
          </p>
        </div>
      </div>

      {dateControls}

      <Tabs defaultValue="trial-balance">
        <TabsList className="flex-wrap">
          <TabsTrigger value="trial-balance">Trial Balance</TabsTrigger>
          <TabsTrigger value="profit-loss">Profit &amp; Loss</TabsTrigger>
          <TabsTrigger value="balance-sheet">Balance Sheet</TabsTrigger>
          <TabsTrigger value="gst-f5">GST F5</TabsTrigger>
          <TabsTrigger value="aged">Aged AR / AP</TabsTrigger>
        </TabsList>

        <TabsContent value="trial-balance" className="mt-4">
          <Card className="border-border bg-carbon">
            <CardContent className="space-y-4 pt-6">
              <div className="flex items-center justify-between">
                <h2 className="font-display text-lg font-semibold text-text-primary">
                  Trial Balance
                </h2>
                {tbData?.totals && (
                  <Badge variant={tbData.totals.balanced ? "default" : "destructive"}>
                    {tbData.totals.balanced ? "Balanced" : "Out of balance"}
                  </Badge>
                )}
              </div>
              {tb.isLoading ? (
                <div className="flex items-center justify-center gap-2 py-16 text-text-secondary">
                  <Loader2 className="h-5 w-5 animate-spin" />
                  <span className="text-sm">Computing trial balance…</span>
                </div>
              ) : tb.isError ? (
                <p className="py-8 text-center text-sm text-alert">
                  Failed to compute trial balance.
                </p>
              ) : (tbData?.lines?.length ?? 0) === 0 ? (
                <p className="py-8 text-center text-sm text-text-secondary">
                  No journal activity as at this date.
                </p>
              ) : (
                <>
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b border-border text-left text-text-muted">
                        <th scope="col" className="py-2 pr-4 font-medium">Code</th>
                        <th scope="col" className="py-2 pr-4 font-medium">Account</th>
                        <th scope="col" className="py-2 text-right font-medium">Debits</th>
                        <th scope="col" className="py-2 text-right font-medium">Credits</th>
                      </tr>
                    </thead>
                    <tbody>
                      {tbData?.lines.map((line) => (
                        <tr key={line.account_id} className="border-b border-border/50">
                          <td className="py-2 pr-4 font-mono text-xs text-text-secondary">
                            {line.account_code}
                          </td>
                          <td className="py-2 pr-4 text-text-primary">{line.account_name}</td>
                          <td className="py-2 text-right font-mono text-text-primary">
                            {formatAmount(line.total_debits)}
                          </td>
                          <td className="py-2 text-right font-mono text-text-primary">
                            {formatAmount(line.total_credits)}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                    <tfoot>
                      <tr className="border-t-2 border-border font-medium">
                        <td colSpan={2} className="py-2 text-text-secondary">Totals</td>
                        <td className="py-2 text-right font-mono">
                          {formatAmount(tbData?.totals.total_debits)}
                        </td>
                        <td className="py-2 text-right font-mono">
                          {formatAmount(tbData?.totals.total_credits)}
                        </td>
                      </tr>
                    </tfoot>
                  </table>
                </>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="profit-loss" className="mt-4">
          <Card className="border-border bg-carbon">
            <CardContent className="space-y-4 pt-6">
              <h2 className="font-display text-lg font-semibold text-text-primary">
                Profit &amp; Loss
              </h2>
              {pl.isLoading ? (
                <div className="flex items-center justify-center gap-2 py-16 text-text-secondary">
                  <Loader2 className="h-5 w-5 animate-spin" />
                  <span className="text-sm">Computing profit &amp; loss…</span>
                </div>
              ) : pl.isError ? (
                <p className="py-8 text-center text-sm text-alert">
                  Failed to compute profit &amp; loss.
                </p>
              ) : (
                <div className="space-y-6">
                  <section className="space-y-2">
                    <h3 className="text-sm font-semibold uppercase tracking-wide text-text-secondary">
                      Revenue
                    </h3>
                    <ReportRows lines={plData?.sections.revenue ?? []} amountLabel="Amount" />
                    <p className="text-right font-mono text-sm text-text-secondary">
                      Total revenue: {formatAmount(plData?.revenue_total)}
                    </p>
                  </section>
                  <section className="space-y-2">
                    <h3 className="text-sm font-semibold uppercase tracking-wide text-text-secondary">
                      Expenses
                    </h3>
                    <ReportRows lines={plData?.sections.expenses ?? []} amountLabel="Amount" />
                    <p className="text-right font-mono text-sm text-text-secondary">
                      Total expenses: {formatAmount(plData?.expense_total)}
                    </p>
                  </section>
                  <div className="flex items-center justify-between border-t-2 border-border pt-4">
                    <span className="font-medium text-text-primary">Net profit</span>
                    <span className="font-mono text-lg font-semibold text-text-primary">
                      {formatAmount(plData?.net_profit)}
                    </span>
                  </div>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="balance-sheet" className="mt-4">
          <Card className="border-border bg-carbon">
            <CardContent className="space-y-4 pt-6">
              <div className="flex items-center justify-between">
                <h2 className="font-display text-lg font-semibold text-text-primary">
                  Balance Sheet
                </h2>
                {bsData && (
                  <Badge variant={bsData.balanced ? "default" : "destructive"}>
                    {bsData.balanced ? "Balanced" : "Out of balance"}
                  </Badge>
                )}
              </div>
              {bs.isLoading ? (
                <div className="flex items-center justify-center gap-2 py-16 text-text-secondary">
                  <Loader2 className="h-5 w-5 animate-spin" />
                  <span className="text-sm">Computing balance sheet…</span>
                </div>
              ) : bs.isError ? (
                <p className="py-8 text-center text-sm text-alert">
                  Failed to compute balance sheet.
                </p>
              ) : (
                <div className="space-y-6">
                  <section className="space-y-2">
                    <h3 className="text-sm font-semibold uppercase tracking-wide text-text-secondary">
                      Assets
                    </h3>
                    <ReportRows lines={bsData?.sections.assets ?? []} amountLabel="Amount" />
                    <p className="text-right font-mono text-sm text-text-secondary">
                      Total assets: {formatAmount(bsData?.assets_total)}
                    </p>
                  </section>
                  <section className="space-y-2">
                    <h3 className="text-sm font-semibold uppercase tracking-wide text-text-secondary">
                      Liabilities
                    </h3>
                    <ReportRows lines={bsData?.sections.liabilities ?? []} amountLabel="Amount" />
                    <p className="text-right font-mono text-sm text-text-secondary">
                      Total liabilities: {formatAmount(bsData?.liabilities_total)}
                    </p>
                  </section>
                  <section className="space-y-2">
                    <h3 className="text-sm font-semibold uppercase tracking-wide text-text-secondary">
                      Equity
                    </h3>
                    <ReportRows lines={bsData?.sections.equity ?? []} amountLabel="Amount" />
                    <p className="text-right font-mono text-sm text-text-secondary">
                      Retained earnings: {formatAmount(bsData?.retained_earnings)}
                    </p>
                    <p className="text-right font-mono text-sm text-text-secondary">
                      Total equity incl. retained:{" "}
                      {formatAmount(
                        bsData
                          ? (
                              Number(bsData.equity_total) + Number(bsData.retained_earnings)
                            ).toFixed(4)
                          : undefined
                      )}
                    </p>
                  </section>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="gst-f5" className="mt-4">
          <Card className="border-border bg-carbon">
            <CardContent className="space-y-4 pt-6">
              <div className="flex items-center justify-between">
                <h2 className="font-display text-lg font-semibold text-text-primary">
                  GST F5 Returns ({gstYear})
                </h2>
                <Button
                  variant="outline"
                  size="sm"
                  className="h-8 rounded-sm border-border"
                  onClick={() => setShowCreatePeriods(true)}
                >
                  Create return periods
                </Button>
              </div>

              {/* P10/H-3: the next filing deadline, from the real endpoint. */}
              {gstDeadlines.data?.results?.[0] && (
                <p className="text-sm text-text-secondary" data-testid="gst-deadline-banner">
                  Next filing due:{" "}
                  <span className="font-medium text-text-primary">
                    {gstDeadlines.data.results[0].filing_due_date}
                  </span>{" "}
                  ({gstDeadlines.data.results[0].days_until_due} days) — period{" "}
                  {gstDeadlines.data.results[0].period_start} →{" "}
                  {gstDeadlines.data.results[0].period_end}
                </p>
              )}

              {gstReturns.isLoading ? (
                <div className="flex items-center justify-center gap-2 py-16 text-text-secondary">
                  <Loader2 className="h-5 w-5 animate-spin" />
                  <span className="text-sm">Loading returns…</span>
                </div>
              ) : gstReturns.isError ? (
                <p className="py-8 text-center text-sm text-alert">
                  Failed to load GST returns.
                </p>
              ) : (gstReturns.data?.results.length ?? 0) === 0 ? (
                <div className="flex flex-col items-center gap-2 py-10">
                  <p className="text-sm text-text-secondary">
                    No GST return periods for {gstYear}.
                  </p>
                  <p className="text-xs text-text-muted">
                    Create periods with a filing frequency and start date, then
                    compute generates the F5 boxes from your documents.
                  </p>
                </div>
              ) : (
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-border text-left text-text-muted">
                      <th scope="col" className="py-2 pr-4 font-medium">Period</th>
                      <th scope="col" className="py-2 pr-4 font-medium">Due</th>
                      <th scope="col" className="py-2 pr-4 font-medium">Status</th>
                      <th scope="col" className="py-2 pr-4 text-right font-medium">Net GST</th>
                      <th scope="col" className="py-2 text-right font-medium">Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {gstReturns.data?.results.map((row) => (
                      <React.Fragment key={row.id}>
                        <tr className="border-b border-border/50">
                          <td className="py-2 pr-4 text-text-primary">
                            {row.period_start} → {row.period_end}
                          </td>
                          <td className="py-2 pr-4 text-text-secondary">{row.filing_due_date}</td>
                          <td className="py-2 pr-4">
                            <StatusBadge status={row.status} />
                          </td>
                          <td className="py-2 pr-4 text-right font-mono text-text-primary">
                            {formatAmount(row.net_gst)}
                          </td>
                          <td className="py-2 text-right">
                            <div className="inline-flex flex-wrap gap-2 justify-end">
                              <Button
                                variant="outline"
                                size="sm"
                                className="h-8 rounded-sm border-border"
                                aria-expanded={expandedBoxes === row.id}
                                onClick={() =>
                                  setExpandedBoxes(
                                    expandedBoxes === row.id ? null : row.id
                                  )
                                }
                              >
                                View boxes
                              </Button>
                              <Button
                                variant="outline"
                                size="sm"
                                className="h-8 rounded-sm border-border"
                                disabled={
                                  generateReturn.isPending || row.status === "FILED"
                                }
                                onClick={() => generateReturn.mutate(row.id)}
                              >
                                {generateReturn.isPending ? (
                                  <Loader2 className="h-3.5 w-3.5 animate-spin" />
                                ) : (
                                  <CheckCircle2 className="h-3.5 w-3.5" />
                                )}
                                Compute
                              </Button>
                              {canFileGst && row.status === "COMPUTED" && (
                                <Button
                                  variant="outline"
                                  size="sm"
                                  className="h-8 rounded-sm border-border"
                                  disabled={reviewReturn.isPending}
                                  onClick={() => reviewReturn.mutate(row.id)}
                                >
                                  Review
                                </Button>
                              )}
                              {canFileGst && (
                                <Button
                                  variant="outline"
                                  size="sm"
                                  className="h-8 rounded-sm border-border"
                                  disabled={fileReturn.isPending || row.status === "FILED"}
                                  onClick={() => fileReturn.mutate({ returnId: row.id })}
                                >
                                  File
                                </Button>
                              )}
                              {canFileGst && row.status === "FILED" && (
                                <Button
                                  variant="outline"
                                  size="sm"
                                  className="h-8 rounded-sm border-border"
                                  onClick={() => setAmending(row.id)}
                                >
                                  Amend
                                </Button>
                              )}
                            </div>
                          </td>
                        </tr>
                        {expandedBoxes === row.id && (
                          <tr className="border-b border-border/50">
                            <td colSpan={5} className="py-3">
                              <F5BoxesPanel orgId={orgId ?? ""} returnId={row.id} />
                            </td>
                          </tr>
                        )}
                      </React.Fragment>
                    ))}
                  </tbody>
                </table>
              )}

              {/* Create-periods dialog (P10/H-3 — the empty state's "created
                  from the API" text replaced by a real affordance). */}
              {showCreatePeriods && (
                <CreatePeriodsDialog
                  open={showCreatePeriods}
                  onOpenChange={setShowCreatePeriods}
                  isPending={createPeriods.isPending}
                  onSubmit={(payload) => {
                    createPeriods.mutate(payload, {
                      onSuccess: () => setShowCreatePeriods(false),
                    });
                  }}
                />
              )}

              {/* Amend-reason dialog (the backend requires a reason). */}
              {amending && (
                <AmendReasonDialog
                  open={!!amending}
                  onOpenChange={(open) => !open && setAmending(null)}
                  isPending={amendReturn.isPending}
                  onSubmit={(reason) => {
                    amendReturn.mutate(
                      { returnId: amending, reason },
                      { onSuccess: () => setAmending(null) }
                    );
                  }}
                />
              )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="aged" className="mt-4 space-y-4">
          {(
            [
              ["Receivables", agedAr],
              ["Payables", agedAp],
            ] as const
          ).map(([label, query]) => (
            <Card key={label} className="border-border bg-carbon">
              <CardContent className="space-y-4 pt-6">
                <div className="flex items-center justify-between">
                  <h2 className="font-display text-lg font-semibold text-text-primary">
                    Aged {label}
                  </h2>
                  <span className="font-mono text-sm text-text-secondary">
                    Total: {formatAmount(query.data?.totals.outstanding_total)}
                  </span>
                </div>
                {query.isLoading ? (
                  <div className="flex items-center justify-center gap-2 py-12 text-text-secondary">
                    <Loader2 className="h-5 w-5 animate-spin" />
                    <span className="text-sm">Computing aged {label.toLowerCase()}…</span>
                  </div>
                ) : query.isError ? (
                  <p className="py-8 text-center text-sm text-alert">
                    Failed to compute aged {label.toLowerCase()}.
                  </p>
                ) : (query.data?.results.length ?? 0) === 0 ? (
                  <p className="py-8 text-center text-sm text-text-secondary">
                    Nothing outstanding as at this date.
                  </p>
                ) : (
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b border-border text-left text-text-muted">
                        <th scope="col" className="py-2 pr-4 font-medium">Contact</th>
                        <th scope="col" className="py-2 pr-4 font-medium">Docs</th>
                        <th scope="col" className="py-2 pr-4 text-right font-medium">Current</th>
                        <th scope="col" className="py-2 pr-4 text-right font-medium">1–30</th>
                        <th scope="col" className="py-2 pr-4 text-right font-medium">31–60</th>
                        <th scope="col" className="py-2 pr-4 text-right font-medium">61–90</th>
                        <th scope="col" className="py-2 text-right font-medium">90+</th>
                      </tr>
                    </thead>
                    <tbody>
                      {query.data?.results.map((row) => (
                        <tr key={row.contact_id} className="border-b border-border/50">
                          <td className="py-2 pr-4 text-text-primary">{row.contact_name}</td>
                          <td className="py-2 pr-4 text-text-secondary">{row.document_count}</td>
                          <td className="py-2 pr-4 text-right font-mono">{formatAmount(row.current)}</td>
                          <td className="py-2 pr-4 text-right font-mono">{formatAmount(row.d1_30)}</td>
                          <td className="py-2 pr-4 text-right font-mono">{formatAmount(row.d31_60)}</td>
                          <td className="py-2 pr-4 text-right font-mono">{formatAmount(row.d61_90)}</td>
                          <td className="py-2 text-right font-mono text-alert">
                            {formatAmount(row.d90_plus)}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                )}
              </CardContent>
            </Card>
          ))}
        </TabsContent>
      </Tabs>
    </div>
  );
}

// ---------------------------------------------------------------------------
// P10/H-3 — the F5 lifecycle helpers
// ---------------------------------------------------------------------------

/** IRAS box labels (the schema's own convention, gst.return CHECKs). */
// P11/H-2: the keys are the DETAIL serializer's real keys
// (box1_std_rated_supplies…) — the old box1…box14 keys never matched the
// payload, so every box rendered "—" and the P10 "boxes visible before
// File" deliverable was non-functional.
const F5_BOX_LABELS: [string, string][] = [
  ["box1_std_rated_supplies", "Box 1 — Standard-rated supplies"],
  ["box2_zero_rated_supplies", "Box 2 — Zero-rated supplies"],
  ["box3_exempt_supplies", "Box 3 — Exempt supplies"],
  ["box4_total_supplies", "Box 4 — Total supplies (1+2+3)"],
  ["box5_total_taxable_purchases", "Box 5 — Total taxable purchases"],
  ["box6_output_tax", "Box 6 — Output tax due"],
  ["box7_input_tax_claimable", "Box 7 — Input tax claimed"],
  ["box8_net_gst", "Box 8 — Net GST (6−7)"],
  ["box13_total_revenue", "Box 13 — Total value of supplies"],
  ["box14_reverse_charge_supplies", "Box 14 — Reverse charge supplies"],
];

function F5BoxesPanel({ orgId, returnId }: { orgId: string; returnId: string }) {
  const detail = useGSTReturn(orgId, returnId);

  if (detail.isLoading) {
    return (
      <p className="text-sm text-text-secondary py-2">Loading the computed boxes…</p>
    );
  }
  if (detail.isError || !detail.data) {
    return (
      <p className="text-sm text-alert py-2">
        Failed to load the computed boxes.{" "}
        {detail.data === null && "Compute the return first."}
      </p>
    );
  }
  const boxes = detail.data.boxes ?? {};
  return (
    <div className="rounded-sm border border-border bg-surface/40 p-3" data-testid="f5-boxes-panel">
      <dl className="grid grid-cols-1 sm:grid-cols-2 gap-x-6 gap-y-1 text-sm">
        {F5_BOX_LABELS.map(([key, label]) => (
          <div key={key} className="flex items-center justify-between gap-2">
            <dt className="text-text-secondary">{label}</dt>
            <dd className="font-mono text-text-primary">
              {boxes[key] !== undefined ? boxes[key] : "—"}
            </dd>
          </div>
        ))}
      </dl>
      <p className="text-xs text-text-muted mt-2">
        Computed {detail.data.computed_at ?? "—"} · status {detail.data.status}
      </p>
    </div>
  );
}

function CreatePeriodsDialog({
  open,
  onOpenChange,
  isPending,
  onSubmit,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  isPending: boolean;
  onSubmit: (payload: {
    filing_frequency: "MONTHLY" | "QUARTERLY";
    start_date: string;
  }) => void;
}) {
  const [frequency, setFrequency] = React.useState<"MONTHLY" | "QUARTERLY">(
    "QUARTERLY"
  );
  const [startDate, setStartDate] = React.useState(todayISO());

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="border-border bg-carbon rounded-sm max-w-md">
        <DialogHeader>
          <DialogTitle className="font-display text-xl text-text-primary">
            Create return periods
          </DialogTitle>
          <DialogDescription>
            Draft F5 periods are created for the frequency from the start date;
            compute generates the boxes from your documents.
          </DialogDescription>
        </DialogHeader>
        <div className="space-y-3">
          <div className="space-y-2">
            <label
              htmlFor="gst-frequency"
              className="text-sm font-medium text-text-secondary"
            >
              Filing frequency
            </label>
            <select
              id="gst-frequency"
              value={frequency}
              onChange={(e) =>
                setFrequency(e.target.value as "MONTHLY" | "QUARTERLY")
              }
              className="h-10 w-full rounded-sm border border-border bg-surface px-3 text-sm text-text-primary"
            >
              <option value="QUARTERLY">Quarterly</option>
              <option value="MONTHLY">Monthly</option>
            </select>
          </div>
          <Input
            label="Period start"
            type="date"
            value={startDate}
            onChange={(e) => setStartDate(e.target.value)}
            disabled={isPending}
          />
        </div>
        <DialogFooter>
          <Button
            type="button"
            variant="outline"
            className="rounded-sm border-border"
            onClick={() => onOpenChange(false)}
            disabled={isPending}
          >
            Cancel
          </Button>
          <Button
            type="button"
            className="rounded-sm bg-accent-primary text-void hover:bg-accent-primary-dim"
            disabled={isPending || !startDate}
            onClick={() => onSubmit({ filing_frequency: frequency, start_date: startDate })}
          >
            {isPending ? (
              <Loader2 className="h-4 w-4 animate-spin" aria-hidden />
            ) : (
              "Create Periods"
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

function AmendReasonDialog({
  open,
  onOpenChange,
  isPending,
  onSubmit,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  isPending: boolean;
  onSubmit: (reason: string) => void;
}) {
  const [reason, setReason] = React.useState("");

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="border-border bg-carbon rounded-sm max-w-md">
        <DialogHeader>
          <DialogTitle className="font-display text-xl text-text-primary">
            Amend filed return
          </DialogTitle>
          <DialogDescription>
            The return is marked for amendment — a reason is required (max 500
            characters).
          </DialogDescription>
        </DialogHeader>
        <div className="space-y-2">
          <label
            htmlFor="amend-reason"
            className="text-sm font-medium text-text-secondary"
          >
            Reason
          </label>
          <textarea
            id="amend-reason"
            value={reason}
            onChange={(e) => setReason(e.target.value)}
            maxLength={500}
            rows={3}
            className="w-full rounded-sm border border-border bg-surface px-3 py-2 text-sm text-text-primary"
            placeholder="e.g. Box 1 included an exempt supply"
            disabled={isPending}
          />
        </div>
        <DialogFooter>
          <Button
            type="button"
            variant="outline"
            className="rounded-sm border-border"
            onClick={() => onOpenChange(false)}
            disabled={isPending}
          >
            Cancel
          </Button>
          <Button
            type="button"
            className="rounded-sm bg-accent-primary text-void hover:bg-accent-primary-dim"
            disabled={isPending || !reason.trim()}
            onClick={() => onSubmit(reason.trim())}
          >
            {isPending ? (
              <Loader2 className="h-4 w-4 animate-spin" aria-hidden />
            ) : (
              "Submit Amendment"
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
