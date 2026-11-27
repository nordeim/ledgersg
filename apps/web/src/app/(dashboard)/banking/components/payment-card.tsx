"use client";

import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { formatMoney } from "@/shared/format";
import type { Payment } from "@/shared/schemas";
import { ArrowDownLeft, ArrowUpRight, CheckCircle2, AlertCircle } from "lucide-react";

interface PaymentCardProps {
  payment: Payment;
  onClick?: (payment: Payment) => void;
  showActions?: boolean;
  /** P9/B-6: the void correction path (the P5 engine finally gets a UI). */
  onVoid?: (payment: Payment) => void;
}

export function PaymentCard({ payment, onClick, onVoid }: PaymentCardProps) {
  const isReceived = payment.payment_type === "RECEIVED";
  const amountPrefix = isReceived ? "+" : "-";
  const amountColor = isReceived ? "text-success" : "text-text-primary";
  const Icon = isReceived ? ArrowDownLeft : ArrowUpRight;

  // P21/FE-M4: the P19 transaction-row keyboard contract — a clickable
  // div is mouse-only (no role, no tab order, no keydown). Only applies
  // when a handler is wired (otherwise the card stays static).
  const interactive = Boolean(onClick);

  return (
    <Card
      className={interactive
        ? "border-border bg-surface hover:border-accent-primary/50 hover:bg-carbon cursor-pointer transition-colors rounded-sm focus-visible:outline-accent-primary"
        : "border-border bg-surface rounded-sm"}
      role={interactive ? "button" : undefined}
      tabIndex={interactive ? 0 : undefined}
      aria-label={
        interactive
          ? `Payment ${payment.payment_number} — ${formatMoney(payment.amount)} ${payment.currency}`
          : undefined
      }
      onClick={() => onClick?.(payment)}
      onKeyDown={(e) => {
        if (!interactive) return;
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          onClick?.(payment);
        }
      }}
      data-testid="payment-card"
    >
      <CardContent className="p-4">
        <div className="flex items-center justify-between">
          {/* Left: Payment Info */}
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 mb-1">
              <span className="font-medium text-text-primary truncate">
                {payment.payment_number}
              </span>
              {payment.is_reconciled && (
                <Badge variant="secondary" className="text-xs rounded-sm">
                  <CheckCircle2 className="h-3 w-3 mr-1" />
                  Reconciled
                </Badge>
              )}
              {payment.is_voided && (
                <Badge variant="destructive" className="text-xs rounded-sm">
                  <AlertCircle className="h-3 w-3 mr-1" />
                  Voided
                </Badge>
              )}
            </div>
            
            <div className="text-sm text-text-secondary truncate">
              {payment.contact_name || "Unknown Contact"}
            </div>
            
            <div className="flex items-center gap-2 mt-1 text-xs text-text-muted">
              <span>{payment.payment_date}</span>
              <span>•</span>
              <span>{payment.payment_method_display || payment.payment_method}</span>
            </div>
          </div>

          {/* Right: Amount + the correction path */}
          <div className="text-right ml-4 flex flex-col items-end gap-2">
            <div>
              <div className={`font-mono text-lg font-medium tabular-nums flex items-center justify-end gap-1 ${amountColor}`}>
                <Icon className="h-4 w-4" />
                <span>
                  {amountPrefix}
                  {payment.currency} {formatMoney(payment.amount)}
                </span>
              </div>
              {payment.fx_gain_loss && parseFloat(payment.fx_gain_loss) !== 0 && (
                <div className="text-xs text-text-muted">
                  FX: {parseFloat(payment.fx_gain_loss) > 0 ? "+" : ""}
                  {formatMoney(payment.fx_gain_loss)}
                </div>
              )}
            </div>
            {onVoid && !payment.is_voided && (
              <Button
                size="sm"
                variant="ghost"
                className="h-7 px-2 text-xs text-text-secondary hover:text-alert"
                onClick={(e) => {
                  e.stopPropagation();
                  onVoid(payment);
                }}
              >
                Void
              </Button>
            )}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
