"use client";

import { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { AlertTriangle, CreditCard, RefreshCw } from "lucide-react";
import { usePayments } from "@/hooks/use-banking";
import { PaymentCard } from "./payment-card";
import type { Payment } from "@/shared/schemas";

interface PaymentListProps {
  orgId: string;
  filters?: {
    payment_type?: "RECEIVED" | "MADE";
    is_reconciled?: boolean | null;
    date_from?: string;
    date_to?: string;
  };
  onPaymentClick?: (payment: Payment) => void;
}

export function PaymentList({ orgId, filters = {}, onPaymentClick }: PaymentListProps) {
  const { data, isLoading, error, refetch } = usePayments(orgId, filters);
  const [selectedPaymentId, setSelectedPaymentId] = useState<string | null>(null);

  if (isLoading) {
    return (
      <div className="space-y-3" data-testid="payments-loading">
        {[1, 2, 3].map((i) => (
          <Card key={i} className="border-border bg-surface rounded-sm">
            <CardContent className="p-4">
              <div className="flex items-center justify-between">
                <div className="space-y-2 flex-1">
                  <Skeleton className="h-5 w-32" />
                  <Skeleton className="h-4 w-48" />
                </div>
                <Skeleton className="h-8 w-24" />
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
    );
  }

  if (error) {
    return (
      <Alert variant="destructive" className="rounded-sm" data-testid="payments-error">
        <AlertTriangle className="h-4 w-4" />
        <AlertTitle>Error loading payments</AlertTitle>
        <AlertDescription className="flex flex-col gap-2">
          <p>Failed to load payments. Please try again.</p>
          <Button 
            variant="outline" 
            size="sm" 
            onClick={() => refetch()}
            className="w-fit"
          >
            <RefreshCw className="h-4 w-4 mr-2" />
            Retry
          </Button>
        </AlertDescription>
      </Alert>
    );
  }

  if (!data || data.count === 0) {
    return (
      <Card className="border-border bg-carbon rounded-sm" data-testid="payments-empty">
        <CardContent className="py-12">
          <div className="text-center">
            <CreditCard className="h-12 w-12 text-text-muted mx-auto mb-4" />
            <h3 className="text-lg font-semibold text-text-primary mb-2">
              No payments found
            </h3>
            <p className="text-text-secondary mb-4">
              {filters.payment_type === "RECEIVED" 
                ? "No received payments match your filters."
                : filters.payment_type === "MADE"
                ? "No made payments match your filters."
                : "No payments found. Create your first payment to get started."}
            </p>
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-3" data-testid="payments-list">
      <div className="flex items-center justify-between text-sm text-text-muted mb-2">
        <span>
          Showing {data.results.length} of {data.count} payments
        </span>
        {data.next && (
          <Button variant="link" size="sm" className="h-auto p-0">
            Load more
          </Button>
        )}
      </div>
      
      {data.results.map((payment) => (
        <PaymentCard
          key={payment.id}
          payment={payment}
          onClick={(p) => {
            setSelectedPaymentId(p.id);
            onPaymentClick?.(p);
          }}
          showActions={true}
        />
      ))}
    </div>
  );
}
