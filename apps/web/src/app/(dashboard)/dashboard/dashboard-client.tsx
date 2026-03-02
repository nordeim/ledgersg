"use client";

import * as React from "react";
import { useQuery } from "@tanstack/react-query";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
  TrendingUp,
  TrendingDown,
  AlertTriangle,
  FileText,
  PieChart,
  Calendar,
  Loader2,
} from "lucide-react";
import Link from "next/link";
import { cn } from "@/lib/utils";
import { DashboardActions } from "./dashboard-actions";
import { GSTChartWrapper } from "./gst-chart-wrapper";
import { useAuth } from "@/providers/auth-provider";
import { api } from "@/lib/api-client";

interface DashboardData {
  gst_payable: string;
  gst_payable_display: string;
  outstanding_receivables: string;
  outstanding_payables: string;
  revenue_mtd: string;
  revenue_ytd: string;
  cash_on_hand: string;
  gst_threshold_status: "SAFE" | "WARNING" | "CRITICAL" | "EXCEEDED";
  gst_threshold_utilization: number;
  gst_threshold_amount: string;
  gst_threshold_limit: string;
  compliance_alerts: ComplianceAlert[];
  invoices_pending: number;
  invoices_overdue: number;
  invoices_peppol_pending: number;
  current_gst_period: GSTPeriod;
  last_updated: string;
}

interface ComplianceAlert {
  id: string;
  severity: "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";
  title: string;
  message: string;
  action_required: string;
  deadline?: string;
  dismissed: boolean;
}

interface GSTPeriod {
  start_date: string;
  end_date: string;
  filing_due_date: string;
  days_remaining: number;
}

export function DashboardClient() {
  const { currentOrg, isLoading: authLoading } = useAuth();

  const orgId = currentOrg?.id;

  const { data, isLoading, error } = useQuery<DashboardData>({
    queryKey: ["dashboard", orgId],
    queryFn: () => api.get<DashboardData>(`/api/v1/${orgId}/dashboard/`),
    enabled: !!orgId, // Only fetch when org is available
    staleTime: 60 * 1000, // 1 minute
  });

  if (authLoading) {
    return (
      <div className="flex items-center justify-center h-[60vh]">
        <Loader2 className="h-8 w-8 animate-spin text-accent-primary" />
      </div>
    );
  }

  if (!orgId) {
    return (
      <div className="flex items-center justify-center h-[60vh]">
        <div className="text-center">
          <AlertTriangle className="h-12 w-12 text-warning mx-auto mb-4" />
          <h2 className="text-xl font-semibold text-text-primary mb-2">
            No Organisation Selected
          </h2>
          <p className="text-text-secondary">
            Please select an organisation to view the dashboard
          </p>
        </div>
      </div>
    );
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-[60vh]">
        <Loader2 className="h-8 w-8 animate-spin text-accent-primary" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center h-[60vh]">
        <div className="text-center">
          <AlertTriangle className="h-12 w-12 text-alert mx-auto mb-4" />
          <h2 className="text-xl font-semibold text-text-primary mb-2">
            Failed to load dashboard
          </h2>
          <p className="text-text-secondary">Please try refreshing the page</p>
        </div>
      </div>
    );
  }

  if (!data) {
    return null;
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="font-display text-2xl font-bold text-text-primary">
            Command Center
          </h1>
          <p className="text-sm text-text-secondary mt-1">
            Real-time compliance and financial overview
          </p>
        </div>
        <DashboardActions />
      </div>

      {/* Compliance Alerts */}
      {data.compliance_alerts.length > 0 && (
        <div className="space-y-2">
          {data.compliance_alerts.map((alert) => (
            <div
              key={alert.id}
              className={cn(
                "flex items-center gap-3 p-3 rounded-sm border",
                alert.severity === "CRITICAL" && "bg-alert/10 border-alert",
                alert.severity === "HIGH" && "bg-warning/10 border-warning",
                alert.severity === "MEDIUM" && "bg-accent-secondary/10 border-accent-secondary",
                alert.severity === "LOW" && "bg-surface border-border"
              )}
            >
              <AlertTriangle
                className={cn(
                  "h-5 w-5 flex-shrink-0",
                  alert.severity === "CRITICAL" && "text-alert",
                  alert.severity === "HIGH" && "text-warning",
                  alert.severity === "MEDIUM" && "text-accent-secondary",
                  alert.severity === "LOW" && "text-text-muted"
                )}
              />
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium text-text-primary">
                  {alert.title}
                </p>
                <p className="text-xs text-text-secondary">{alert.message}</p>
              </div>
              <Link
                href="#"
                className="px-3 py-1.5 text-xs font-medium rounded-sm border border-border bg-surface text-text-secondary hover:text-text-primary hover:bg-carbon transition-colors"
              >
                {alert.action_required}
              </Link>
            </div>
          ))}
        </div>
      )}

      {/* Metrics Grid */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        {/* GST Payable - Dominant Card */}
        <Card className="border-border bg-carbon rounded-sm md:col-span-2 lg:col-span-2">
          <CardHeader className="pb-3">
            <div className="flex items-center justify-between">
              <div>
                <CardTitle className="font-display text-lg text-text-primary">
                  GST Payable
                </CardTitle>
                <CardDescription>Current period liability (Box 8)</CardDescription>
              </div>
              <Badge
                variant="outline"
                className="border-accent-primary text-accent-primary rounded-sm"
              >
                Box 8
              </Badge>
            </div>
          </CardHeader>
          <CardContent>
            <div className="flex items-baseline gap-2">
              <span className="text-5xl font-mono font-bold text-accent-primary tabular-nums slashed-zero">
                S$ {data.gst_payable_display}
              </span>
              <span className="text-sm text-text-secondary">SGD</span>
            </div>
            <div className="mt-4 flex items-center gap-2 text-sm">
              <TrendingUp className="h-4 w-4 text-accent-primary" />
              <span className="text-accent-primary">+8.2%</span>
              <span className="text-text-muted">vs last period</span>
            </div>

            {/* GST F5 Breakdown Chart */}
            <div className="mt-6 pt-6 border-t border-border">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-sm font-medium text-text-primary">
                  GST F5 Breakdown
                </h3>
                <Link
                  href="#"
                  className="inline-flex items-center gap-1 px-3 py-1.5 text-xs font-medium rounded-sm border border-border bg-surface text-text-secondary hover:text-text-primary hover:bg-carbon transition-colors"
                >
                  <FileText className="h-3 w-3" />
                  File F5
                </Link>
              </div>
              <GSTChartWrapper gstPayable={data.gst_payable_display} />
            </div>
          </CardContent>
        </Card>

        {/* Outstanding Receivables */}
        <Card className="border-border bg-carbon rounded-sm">
          <CardHeader className="pb-3">
            <CardTitle className="font-display text-sm text-text-secondary">
              Outstanding Receivables
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-mono font-bold text-text-primary tabular-nums slashed-zero">
              S$ {data.outstanding_receivables}
            </div>
            <div className="mt-2 flex items-center gap-2 text-sm">
              <FileText className="h-4 w-4 text-accent-secondary" />
              <span className="text-text-secondary">
                {data.invoices_pending} pending
              </span>
            </div>
            {data.invoices_overdue > 0 && (
              <div className="mt-2 text-xs text-alert">
                {data.invoices_overdue} invoices overdue
              </div>
            )}
          </CardContent>
        </Card>

        {/* Cash on Hand */}
        <Card className="border-border bg-carbon rounded-sm">
          <CardHeader className="pb-3">
            <CardTitle className="font-display text-sm text-text-secondary">
              Cash on Hand
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-mono font-bold text-text-primary tabular-nums slashed-zero">
              S$ {data.cash_on_hand}
            </div>
            <div className="mt-2 flex items-center gap-2 text-sm">
              <TrendingDown className="h-4 w-4 text-warning" />
              <span className="text-warning">-2.4%</span>
              <span className="text-text-muted">vs last month</span>
            </div>
          </CardContent>
        </Card>

        {/* Revenue MTD */}
        <Card className="border-border bg-carbon rounded-sm">
          <CardHeader className="pb-3">
            <CardTitle className="font-display text-sm text-text-secondary">
              Revenue (MTD)
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-mono font-bold text-text-primary tabular-nums slashed-zero">
              S$ {data.revenue_mtd}
            </div>
            <div className="mt-2 flex items-center gap-2 text-sm">
              <TrendingUp className="h-4 w-4 text-accent-primary" />
              <span className="text-accent-primary">+12.5%</span>
              <span className="text-text-muted">vs last month</span>
            </div>
          </CardContent>
        </Card>

        {/* GST Threshold */}
        <Card className="border-border bg-carbon rounded-sm">
          <CardHeader className="pb-3">
            <CardTitle className="font-display text-sm text-text-secondary">
              GST Threshold
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex items-center justify-between">
              <span className="text-2xl font-mono font-bold text-text-primary">
                {data.gst_threshold_utilization}%
              </span>
              <Badge
                variant={
                  data.gst_threshold_status === "CRITICAL"
                    ? "destructive"
                    : data.gst_threshold_status === "WARNING"
                    ? "secondary"
                    : "outline"
                }
                className="rounded-sm"
              >
                {data.gst_threshold_status}
              </Badge>
            </div>
            <div className="mt-3">
              <div className="w-full bg-surface h-2 rounded-sm overflow-hidden">
                <div
                  className={cn(
                    "h-full transition-all duration-500",
                    data.gst_threshold_status === "CRITICAL"
                      ? "bg-alert"
                      : data.gst_threshold_status === "WARNING"
                      ? "bg-warning"
                      : "bg-accent-primary"
                  )}
                  style={{ width: `${Math.min(data.gst_threshold_utilization, 100)}%` }}
                />
              </div>
              <p className="text-xs text-text-muted mt-2">
                S$ {data.gst_threshold_amount} / S$ {data.gst_threshold_limit}
              </p>
            </div>
          </CardContent>
        </Card>

        {/* Revenue YTD */}
        <Card className="border-border bg-carbon rounded-sm">
          <CardHeader className="pb-3">
            <CardTitle className="font-display text-sm text-text-secondary">
              Revenue (YTD)
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-mono font-bold text-text-primary tabular-nums slashed-zero">
              S$ {data.revenue_ytd}
            </div>
            <div className="mt-2 flex items-center gap-2 text-sm">
              <PieChart className="h-4 w-4 text-accent-secondary" />
              <span className="text-text-secondary">On track for target</span>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* GST Period & Recent Activity */}
      <div className="grid gap-4 lg:grid-cols-2">
        {/* GST Filing Period */}
        <Card className="border-border bg-carbon rounded-sm">
          <CardHeader className="pb-3">
            <CardTitle className="font-display text-sm text-text-secondary flex items-center gap-2">
              <Calendar className="w-4 h-4" />
              Current GST Period
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-3 gap-4">
              <div>
                <p className="text-xs text-text-muted">Period Start</p>
                <p className="font-mono text-sm text-text-primary">
                  {data.current_gst_period.start_date}
                </p>
              </div>
              <div>
                <p className="text-xs text-text-muted">Period End</p>
                <p className="font-mono text-sm text-text-primary">
                  {data.current_gst_period.end_date}
                </p>
              </div>
              <div>
                <p className="text-xs text-text-muted">Filing Due</p>
                <p
                  className={cn(
                    "font-mono text-sm",
                    data.current_gst_period.days_remaining <= 7
                      ? "text-alert"
                      : "text-text-primary"
                  )}
                >
                  {data.current_gst_period.filing_due_date}
                  <span className="text-xs text-text-muted ml-2">
                    ({data.current_gst_period.days_remaining} days)
                  </span>
                </p>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Quick Stats */}
        <Card className="border-border bg-carbon rounded-sm">
          <CardHeader className="pb-3">
            <CardTitle className="font-display text-sm text-text-secondary">
              Quick Stats
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-3 gap-4">
              <div>
                <p className="text-xs text-text-muted">Pending</p>
                <p className="font-mono text-lg text-text-primary">
                  {data.invoices_pending}
                </p>
              </div>
              <div>
                <p className="text-xs text-text-muted">Overdue</p>
                <p className="font-mono text-lg text-alert">
                  {data.invoices_overdue}
                </p>
              </div>
              <div>
                <p className="text-xs text-text-muted">Peppol Pending</p>
                <p className="font-mono text-lg text-accent-secondary">
                  {data.invoices_peppol_pending}
                </p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Last Updated Footer */}
      <div className="text-right text-xs text-text-muted">
        Last updated: {new Date(data.last_updated).toLocaleString()}
      </div>
    </div>
  );
}
