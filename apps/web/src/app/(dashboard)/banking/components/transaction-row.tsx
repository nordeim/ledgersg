"use client";

import { useState } from "react";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { CheckCircle2, AlertCircle, ChevronDown, ChevronUp, ArrowDownLeft, ArrowUpRight } from "lucide-react";
import { formatMoney } from "@/shared/format";
import type { BankTransaction } from "@/shared/schemas";

interface TransactionRowProps {
  transaction: BankTransaction;
  onToggle?: () => void;
  onReconcile?: (transaction: BankTransaction) => void;
}

export function TransactionRow({ transaction, onToggle, onReconcile }: TransactionRowProps) {
  const [isExpanded, setIsExpanded] = useState(false);

  const isCredit = parseFloat(transaction.amount) >= 0;
  const amountPrefix = isCredit ? "+" : "";
  const amountColor = isCredit ? "text-success" : "text-alert";
  const AmountIcon = isCredit ? ArrowDownLeft : ArrowUpRight;

  const handleToggle = () => {
    setIsExpanded(!isExpanded);
    onToggle?.();
  };

  const getSourceLabel = (source: string) => {
    switch (source) {
      case "CSV":
        return "CSV";
      case "OFX":
        return "OFX";
      case "MT940":
        return "MT940";
      case "API":
        return "API";
      default:
        return source;
    }
  };

  return (
    <Card
      className={`border-border rounded-sm overflow-hidden transition-all ${
        transaction.is_reconciled ? "opacity-75" : ""
      }`}
      data-testid="transaction-row"
    >
      <div
        className="p-4 cursor-pointer hover:bg-surface transition-colors"
        onClick={handleToggle}
      >
        <div className="flex items-center justify-between">
          {/* Left: Transaction Info */}
          <div className="flex-1 min-w-0 pr-4">
            {/* Date Row */}
            <div className="flex items-center gap-2 mb-1">
              <span className="text-sm text-text-muted font-mono">
                {transaction.transaction_date}
              </span>
              
              {/* Import Source Badge */}
              <Badge variant="outline" className="text-xs rounded-sm">
                {getSourceLabel(transaction.import_source)}
              </Badge>
            </div>
            
            {/* Description */}
            <div className="text-text-primary truncate font-medium">
              {transaction.description}
            </div>
            
            {/* Reference if available */}
            {transaction.reference && (
              <div className="text-xs text-text-muted mt-0.5">
                Ref: {transaction.reference}
              </div>
            )}
          </div>

          {/* Right: Amount and Status */}
          <div className="text-right flex items-center gap-4">
            {/* Amount */}
            <div className={`font-mono text-lg font-medium tabular-nums flex items-center gap-1 ${amountColor}`}>
              <AmountIcon className="h-4 w-4" />
              <span data-testid="transaction-amount" className={amountColor}>
                {amountPrefix}
                S$ {formatMoney(transaction.amount)}
              </span>
            </div>

            {/* Status Badge */}
            <div className="min-w-[100px]">
              {transaction.is_reconciled ? (
                <Badge variant="secondary" className="text-xs rounded-sm gap-1">
                  <CheckCircle2 className="h-3 w-3" data-testid="check-icon" />
                  Reconciled
                </Badge>
              ) : (
                <Badge variant="outline" className="text-xs rounded-sm gap-1 text-warning border-warning">
                  <AlertCircle className="h-3 w-3" />
                  Unreconciled
                </Badge>
              )}
            </div>

            {/* Expand Icon */}
            <div className="text-text-muted">
              {isExpanded ? <ChevronUp className="h-5 w-5" /> : <ChevronDown className="h-5 w-5" />}
            </div>
          </div>
        </div>
      </div>

      {/* Expanded Details */}
      {isExpanded && (
        <CardContent className="border-t border-border bg-carbon p-4">
          <div className="space-y-3">
            <div className="text-sm font-semibold text-text-primary">
              Transaction Details
            </div>
            
            {/* Details Grid */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
              <div>
                <span className="text-text-muted block">Bank Account</span>
                <span className="text-text-primary">{transaction.bank_account_name}</span>
              </div>
              
              <div>
                <span className="text-text-muted block">Value Date</span>
                <span className="text-text-primary">{transaction.value_date || transaction.transaction_date}</span>
              </div>
              
              {transaction.running_balance && (
                <div>
                  <span className="text-text-muted block">Balance:</span>
                  <span className="text-text-primary font-mono">
                    S$ {formatMoney(transaction.running_balance)}
                  </span>
                </div>
              )}
              
              {transaction.external_id && (
                <div>
                  <span className="text-text-muted block">External ID</span>
                  <span className="text-text-primary">{transaction.external_id}</span>
                </div>
              )}
            </div>

            {/* Matched Payment Info */}
            {transaction.is_reconciled && transaction.matched_payment && (
              <div className="pt-3 border-t border-border">
                <span className="text-text-muted text-sm">Matched Payment:</span>
                <span className="text-text-primary text-sm ml-2 font-mono">
                  {transaction.matched_payment}
                </span>
                {transaction.reconciled_at && (
                  <span className="text-text-muted text-xs block mt-1">
                    Reconciled: {new Date(transaction.reconciled_at).toLocaleString()}
                  </span>
                )}
              </div>
            )}

            {/* Action Button */}
            {!transaction.is_reconciled && onReconcile && (
              <div className="pt-3 border-t border-border flex justify-end">
                <Button
                  size="sm"
                  onClick={(e) => {
                    e.stopPropagation();
                    onReconcile(transaction);
                  }}
                  className="rounded-sm bg-accent-primary text-void hover:bg-accent-primary-dim"
                >
                  Reconcile
                </Button>
              </div>
            )}
          </div>
        </CardContent>
      )}
    </Card>
  );
}
