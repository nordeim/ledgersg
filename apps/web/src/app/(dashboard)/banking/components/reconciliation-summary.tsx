"use client";

import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { useBankTransactions } from "@/hooks/use-banking";
import { CheckCircle2, AlertCircle, List, Percent } from "lucide-react";

interface ReconciliationSummaryProps {
  orgId: string;
  bankAccountId?: string;
}

export function ReconciliationSummary({ orgId, bankAccountId }: ReconciliationSummaryProps) {
  const { data, isLoading } = useBankTransactions(orgId, {
    bank_account_id: bankAccountId,
  });

  if (isLoading) {
    return (
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4" data-testid="summary-loading">
        {[1, 2, 3, 4].map((i) => (
          <Card key={i} className="border-border bg-carbon rounded-sm">
            <CardContent className="p-4">
              <Skeleton className="h-4 w-24 mb-2" />
              <Skeleton className="h-8 w-16" />
            </CardContent>
          </Card>
        ))}
      </div>
    );
  }

  const transactions = data?.results || [];
  const total = transactions.length;
  const reconciled = transactions.filter((t) => t.is_reconciled).length;
  const unreconciled = total - reconciled;
  const rate = total > 0 ? Math.round((reconciled / total) * 100) : 0;

  const stats = [
    {
      label: "Total Transactions",
      value: total,
      icon: List,
      color: "text-text-primary",
    },
    {
      label: "Reconciled",
      value: reconciled,
      icon: CheckCircle2,
      color: "text-success",
    },
    {
      label: "Unreconciled",
      value: unreconciled,
      icon: AlertCircle,
      color: "text-warning",
    },
    {
      label: "Reconciliation Rate",
      value: `${rate}%`,
      icon: Percent,
      color: rate >= 80 ? "text-success" : rate >= 50 ? "text-text-primary" : "text-warning",
    },
  ];

  return (
    <div className="grid grid-cols-2 md:grid-cols-4 gap-4" data-testid="reconciliation-summary">
      {stats.map((stat) => (
        <Card key={stat.label} className="border-border bg-carbon rounded-sm">
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-text-muted">{stat.label}</p>
                <p className={`text-2xl font-bold ${stat.color}`}>{stat.value}</p>
              </div>
              <stat.icon className={`h-8 w-8 ${stat.color} opacity-50`} />
            </div>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}
