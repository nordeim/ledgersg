"use client";

import { useMemo } from "react";
import { CalendarRange, Loader2, Lock, Unlock } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { useAuth } from "@/providers/auth-provider";
import {
  useFiscalYears,
  useFiscalPeriods,
  useOpenFiscalPeriod,
  useCloseFiscalPeriod,
  useCloseFiscalYear,
  type FiscalPeriodRow,
} from "@/hooks/use-fiscal";

/**
 * P10/M-8: the Settings "Fiscal year & periods" card — the first consumer
 * of the fiscal endpoints. Period open/close is a deliberate control act
 * a manager performs; the invoice-approval error ("Please open the fiscal
 * period or change the invoice date") becomes actionable.
 */

export function FiscalCard({ orgId }: { orgId: string }) {
  const { hasPermission } = useAuth();
  const canManage = hasPermission("can_manage_org");

  const { data: yearsData, isLoading } = useFiscalYears(orgId);
  const { data: periodsData } = useFiscalPeriods(orgId);
  const openPeriod = useOpenFiscalPeriod(orgId);
  const closePeriod = useCloseFiscalPeriod(orgId);
  const closeYear = useCloseFiscalYear(orgId);

  const periodsByYear = useMemo(() => {
    const map = new Map<string, FiscalPeriodRow[]>();
    for (const period of periodsData?.results ?? []) {
      const list = map.get(period.fiscal_year_id) ?? [];
      list.push(period);
      map.set(period.fiscal_year_id, list);
    }
    return map;
  }, [periodsData]);

  if (isLoading) {
    return (
      <Card className="border-border bg-carbon rounded-sm">
        <CardContent className="py-10">
          <div
            data-testid="fiscal-card-loading"
            className="flex items-center justify-center gap-2 text-sm text-text-secondary"
          >
            <Loader2 className="h-4 w-4 animate-spin" aria-hidden />
            Loading fiscal years…
          </div>
        </CardContent>
      </Card>
    );
  }

  const years = yearsData?.data ?? [];

  return (
    <Card className="border-border bg-carbon rounded-sm">
      <CardHeader>
        <div className="flex items-center gap-2">
          <CalendarRange className="h-5 w-5 text-accent-primary" aria-hidden />
          <CardTitle className="font-display text-lg text-text-primary">
            Fiscal Year &amp; Periods
          </CardTitle>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        <p className="text-sm text-text-secondary">
          Invoices can only be posted to open periods. A back-dated invoice
          outside the open periods needs its period opened here first.
        </p>

        {years.length === 0 ? (
          <p className="text-sm text-text-muted">
            No fiscal years yet — the first one is created with your
            organisation.
          </p>
        ) : (
          <div className="space-y-4">
            {years.map((year) => {
              const periods = periodsByYear.get(year.id) ?? [];
              return (
                <div
                  key={year.id}
                  className="rounded-sm border border-border bg-surface p-3 space-y-2"
                >
                  <div className="flex items-center justify-between gap-2 flex-wrap">
                    <div className="flex items-center gap-2">
                      <span className="font-medium text-text-primary">
                        {year.label}
                      </span>
                      <span className="text-xs text-text-muted">
                        {year.start_date} → {year.end_date}
                      </span>
                    </div>
                    {year.is_closed ? (
                      <Badge variant="outline" className="rounded-sm text-xs text-text-muted">
                        Closed
                      </Badge>
                    ) : (
                      canManage && (
                        <Button
                          type="button"
                          variant="outline"
                          size="sm"
                          className="rounded-sm border-border h-8 text-alert hover:text-alert"
                          aria-label={`Close year ${year.label}`}
                          disabled={closeYear.isPending}
                          onClick={() => closeYear.mutate(year.id)}
                        >
                          Close year
                        </Button>
                      )
                    )}
                  </div>

                  {periods.length === 0 ? (
                    <p className="text-xs text-text-muted">No periods.</p>
                  ) : (
                    <div className="space-y-1">
                      {periods.map((period) => {
                        const isOpen = period.status === "OPEN";
                        return (
                          <div
                            key={period.id}
                            data-testid={`fiscal-period-${period.id}`}
                            className="flex items-center justify-between gap-2 rounded-sm px-2 py-1.5 bg-carbon"
                          >
                            <div className="flex items-center gap-2 min-w-0">
                              <span className="text-sm text-text-primary truncate">
                                {period.name}
                              </span>
                              <span className="text-xs text-text-muted hidden sm:inline">
                                {period.start_date} → {period.end_date}
                              </span>
                            </div>
                            <div className="flex items-center gap-2 shrink-0">
                              <Badge
                                variant="outline"
                                className={`rounded-sm text-xs ${
                                  isOpen ? "text-success" : "text-text-muted"
                                }`}
                              >
                                {isOpen ? "Open" : "Closed"}
                              </Badge>
                              {canManage && (
                                <Button
                                  type="button"
                                  variant="outline"
                                  size="sm"
                                  className="rounded-sm border-border h-7 text-xs"
                                  aria-label={`${isOpen ? "Close" : "Open"} ${period.name}`}
                                  disabled={
                                    isOpen
                                      ? closePeriod.isPending
                                      : openPeriod.isPending
                                  }
                                  onClick={() =>
                                    isOpen
                                      ? closePeriod.mutate(period.id)
                                      : openPeriod.mutate(period.id)
                                  }
                                >
                                  {isOpen ? (
                                    <Lock className="h-3 w-3 mr-1" aria-hidden />
                                  ) : (
                                    <Unlock className="h-3 w-3 mr-1" aria-hidden />
                                  )}
                                  {isOpen ? "Close" : "Open"}
                                </Button>
                              )}
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
