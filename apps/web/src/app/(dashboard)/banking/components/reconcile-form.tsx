"use client";

import { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Loader2, X, CheckCircle2, AlertCircle } from "lucide-react";
import { useSuggestMatches, useReconcileTransaction } from "@/hooks/use-banking";
import { formatMoney } from "@/shared/format";
import type { BankTransaction } from "@/shared/schemas";

interface ReconcileFormProps {
  transaction: BankTransaction;
  orgId: string;
  onClose: () => void;
}

interface PaymentMatch {
  payment_id: string;
  payment_number: string;
  amount: string;
  contact_name: string;
  match_score: number;
}

export function ReconcileForm({ transaction, orgId, onClose }: ReconcileFormProps) {
  const { data: matches, isLoading: isLoadingMatches } = useSuggestMatches(
    orgId,
    transaction.id
  );
  const reconcileMutation = useReconcileTransaction(orgId, transaction.id);
  
  const [selectedPaymentId, setSelectedPaymentId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleReconcile = async () => {
    if (!selectedPaymentId) {
      setError("Please select a payment to reconcile");
      return;
    }

    setError(null);

    try {
      await reconcileMutation.mutateAsync({ payment_id: selectedPaymentId });
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Reconciliation failed");
    }
  };

  const getScoreColor = (score: number) => {
    if (score >= 80) return "bg-success text-void";
    if (score >= 50) return "bg-warning text-void";
    return "bg-text-muted text-void";
  };

  return (
    <Card className="border-border bg-carbon rounded-sm w-full max-w-2xl">
      <CardHeader className="flex flex-row items-center justify-between">
        <CardTitle className="font-display text-lg text-text-primary">
          Reconcile Transaction
        </CardTitle>
        <Button variant="ghost" size="icon" onClick={onClose}>
          <X className="h-4 w-4" />
        </Button>
      </CardHeader>
      <CardContent className="space-y-6">
        {/* Error Alert */}
        {error && (
          <Alert variant="destructive">
            <AlertCircle className="h-4 w-4" />
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        )}

        {/* Transaction Details */}
        <div className="p-4 bg-surface rounded-sm border border-border">
          <h4 className="text-sm font-semibold text-text-primary mb-2">
            Transaction Details
          </h4>
          <div className="grid grid-cols-2 gap-4 text-sm">
            <div>
              <span className="text-text-muted">Description:</span>
              <p className="text-text-primary">{transaction.description}</p>
            </div>
            <div>
              <span className="text-text-muted">Reference:</span>
              <p className="text-text-primary">{transaction.reference || "-"}</p>
            </div>
            <div>
              <span className="text-text-muted">Amount:</span>
              <p className="text-text-primary font-mono">
                S$ {formatMoney(transaction.amount)}
              </p>
            </div>
            <div>
              <span className="text-text-muted">Date:</span>
              <p className="text-text-primary">{transaction.transaction_date}</p>
            </div>
          </div>
        </div>

        {/* Match Suggestions */}
        <div>
          <h4 className="text-sm font-semibold text-text-primary mb-3">
            Suggested Matches
          </h4>
          
          {isLoadingMatches ? (
            <div className="flex items-center justify-center py-8">
              <Loader2 className="h-6 w-6 animate-spin text-accent-primary" />
            </div>
          ) : matches && matches.length > 0 ? (
            <div className="space-y-2">
              {matches.map((match: PaymentMatch) => (
                <button
                  key={match.payment_id}
                  onClick={() => setSelectedPaymentId(match.payment_id)}
                  className={`w-full p-4 rounded-sm border text-left transition-colors ${
                    selectedPaymentId === match.payment_id
                      ? "border-accent-primary bg-accent-primary/10"
                      : "border-border hover:border-accent-primary/50"
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-1">
                        <span className="font-medium text-text-primary">
                          {match.payment_number}
                        </span>
                        <Badge className={getScoreColor(match.match_score)}>
                          {match.match_score}%
                        </Badge>
                      </div>
                      <p className="text-sm text-text-secondary">
                        {match.contact_name}
                      </p>
                    </div>
                    <div className="text-right">
                      <p className="font-mono text-text-primary">
                        S$ {formatMoney(match.amount)}
                      </p>
                    </div>
                  </div>
                </button>
              ))}
            </div>
          ) : (
            <div className="text-center py-8 text-text-muted">
              <AlertCircle className="h-8 w-8 mx-auto mb-2" />
              <p>No matching payments found</p>
            </div>
          )}
        </div>

        {/* Action Buttons */}
        <div className="flex justify-end gap-2 pt-4 border-t border-border">
          <Button variant="outline" onClick={onClose}>
            Cancel
          </Button>
          <Button
            onClick={handleReconcile}
            disabled={reconcileMutation.isLoading || !selectedPaymentId}
            className="bg-accent-primary text-void hover:bg-accent-primary-dim"
          >
            {reconcileMutation.isLoading ? (
              <>
                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                Reconciling...
              </>
            ) : (
              <>
                <CheckCircle2 className="h-4 w-4 mr-2" />
                Reconcile
              </>
            )}
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}
