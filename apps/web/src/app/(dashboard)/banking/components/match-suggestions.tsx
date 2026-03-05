"use client";

import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Loader2, AlertCircle } from "lucide-react";
import { formatMoney } from "@/shared/format";

interface PaymentMatch {
  payment_id: string;
  payment_number: string;
  amount: string;
  contact_name: string;
  match_score: number;
}

interface MatchSuggestionsProps {
  suggestions: PaymentMatch[];
  transactionAmount: string;
  onSelect: (paymentId: string) => void;
  isLoading?: boolean;
}

export function MatchSuggestions({
  suggestions,
  transactionAmount,
  onSelect,
  isLoading = false,
}: MatchSuggestionsProps) {
  const getScoreColor = (score: number) => {
    if (score >= 80) return "bg-success text-void";
    if (score >= 50) return "bg-warning text-void";
    return "bg-text-muted text-void";
  };

  const isExactMatch = (amount: string) => {
    return parseFloat(amount) === parseFloat(transactionAmount);
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-8" data-testid="suggestions-loading">
        <Loader2 className="h-6 w-6 animate-spin text-accent-primary" />
      </div>
    );
  }

  if (suggestions.length === 0) {
    return (
      <div className="text-center py-8 text-text-muted">
        <AlertCircle className="h-8 w-8 mx-auto mb-2" />
        <p>No matching payments found</p>
      </div>
    );
  }

  return (
    <div className="space-y-2" data-testid="match-suggestions">
      {suggestions.map((match) => (
        <button
          key={match.payment_id}
          onClick={() => onSelect(match.payment_id)}
          className="w-full p-4 rounded-sm border border-border bg-surface hover:border-accent-primary/50 hover:bg-carbon transition-colors text-left"
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
                {isExactMatch(match.amount) && (
                  <Badge variant="outline" className="text-xs">
                    Exact Match
                  </Badge>
                )}
              </div>
              <p className="text-sm text-text-secondary">{match.contact_name}</p>
            </div>
            <div className="text-right">
              <p
                className={`font-mono ${
                  isExactMatch(match.amount)
                    ? "text-success font-medium"
                    : "text-text-primary"
                }`}
              >
                S$ {formatMoney(match.amount)}
              </p>
            </div>
          </div>
        </button>
      ))}
    </div>
  );
}
