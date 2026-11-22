"use client";

import { useMemo, useState } from "react";
import { Loader2 } from "lucide-react";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useCreateBankAccount } from "@/hooks/use-banking";
import { useAccounts } from "@/hooks/use-accounts";
import { bankAccountInputSchema } from "@/shared/schemas/bank-account";

/**
 * P9/B-4: the bank-account creation dialog — the "Add Bank Account"/"Add
 * Account" buttons were dead (no onClick, no form anywhere) while the
 * backend + create hook were real. A new organisation could not add a
 * bank account through the UI, gating the whole payments surface.
 *
 * Validation mirrors the backend (BankAccountCreateSerializer) via the
 * shared zod schema; the GL account must be one of the org's bank-type
 * accounts (the seeded 1100 series qualify).
 */

interface Props {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  orgId: string;
}

export function BankAccountDialog({ open, onOpenChange, orgId }: Props) {
  const createAccount = useCreateBankAccount(orgId);
  const { data: accountsData, isLoading: accountsLoading } = useAccounts(orgId, {
    is_active: true,
  });

  const bankAccounts = useMemo(
    () => (accountsData ?? []).filter((a) => a.is_bank),
    [accountsData]
  );

  const [form, setForm] = useState({
    account_name: "",
    bank_name: "",
    account_number: "",
    currency: "SGD",
    gl_account: "",
    paynow_type: "",
    paynow_id: "",
    is_default: false,
  });
  const [errors, setErrors] = useState<Record<string, string>>({});

  const set = (key: keyof typeof form, value: string | boolean) => {
    setForm((prev) => ({ ...prev, [key]: value }));
    setErrors((prev) => {
      if (!prev[key]) return prev;
      const next = { ...prev };
      delete next[key];
      return next;
    });
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();

    const parsed = bankAccountInputSchema.safeParse({
      account_name: form.account_name,
      bank_name: form.bank_name,
      account_number: form.account_number,
      currency: form.currency,
      gl_account: form.gl_account,
      paynow_type: form.paynow_type ? form.paynow_type : null,
      paynow_id: form.paynow_type ? form.paynow_id : null,
      is_default: form.is_default,
    });

    if (!parsed.success) {
      const fieldErrors: Record<string, string> = {};
      for (const issue of parsed.error.issues) {
        const key = String(issue.path[0] ?? "form");
        if (!fieldErrors[key]) fieldErrors[key] = issue.message;
      }
      setErrors(fieldErrors);
      return;
    }

    createAccount.mutate(parsed.data, {
      onSuccess: () => {
        setForm({
          account_name: "",
          bank_name: "",
          account_number: "",
          currency: "SGD",
          gl_account: "",
          paynow_type: "",
          paynow_id: "",
          is_default: false,
        });
        onOpenChange(false);
      },
    });
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="border-border bg-carbon rounded-sm max-w-lg">
        <DialogHeader>
          <DialogTitle className="font-display text-xl text-text-primary">
            Add Bank Account
          </DialogTitle>
          <DialogDescription className="text-text-secondary">
            Bank accounts feed payments, imports, and reconciliation.
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit} className="space-y-4" noValidate>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div className="space-y-2">
              <label htmlFor="ba-name" className="text-sm text-text-secondary">
                Account name <span className="text-alert">*</span>
              </label>
              <Input
                id="ba-name"
                value={form.account_name}
                onChange={(e) => set("account_name", e.target.value)}
                placeholder="Operating Account"
                className="rounded-sm"
              />
              {errors.account_name && (
                <p className="text-sm text-alert">{errors.account_name}</p>
              )}
            </div>
            <div className="space-y-2">
              <label htmlFor="ba-bank" className="text-sm text-text-secondary">
                Bank name <span className="text-alert">*</span>
              </label>
              <Input
                id="ba-bank"
                value={form.bank_name}
                onChange={(e) => set("bank_name", e.target.value)}
                placeholder="DBS Bank"
                className="rounded-sm"
              />
              {errors.bank_name && (
                <p className="text-sm text-alert">{errors.bank_name}</p>
              )}
            </div>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div className="space-y-2">
              <label htmlFor="ba-number" className="text-sm text-text-secondary">
                Account number <span className="text-alert">*</span>
              </label>
              <Input
                id="ba-number"
                value={form.account_number}
                onChange={(e) => set("account_number", e.target.value)}
                placeholder="1234567890"
                className="rounded-sm"
              />
              {errors.account_number && (
                <p className="text-sm text-alert">{errors.account_number}</p>
              )}
            </div>
            <div className="space-y-2">
              <label htmlFor="ba-currency" className="text-sm text-text-secondary">
                Currency
              </label>
              <Input
                id="ba-currency"
                value={form.currency}
                onChange={(e) => set("currency", e.target.value.toUpperCase())}
                maxLength={3}
                className="rounded-sm"
              />
              {errors.currency && (
                <p className="text-sm text-alert">{errors.currency}</p>
              )}
            </div>
          </div>

          <div className="space-y-2">
            <label htmlFor="ba-gl" className="text-sm text-text-secondary">
              GL account <span className="text-alert">*</span>
            </label>
            <select
              id="ba-gl"
              value={form.gl_account}
              onChange={(e) => set("gl_account", e.target.value)}
              className="flex h-10 w-full items-center justify-between rounded-sm border border-border bg-surface px-3 py-2 text-sm text-text-primary focus:outline-none focus:ring-2 focus:ring-accent-primary/50 focus:border-accent-primary disabled:cursor-not-allowed disabled:opacity-50"
            >
              <option value="">
                {accountsLoading
                  ? "Loading accounts…"
                  : bankAccounts.length === 0
                    ? "No bank-type accounts"
                    : "Select the ledger account"}
              </option>
              {bankAccounts.map((account) => (
                <option key={account.id} value={account.id}>
                  {account.code} — {account.name}
                </option>
              ))}
            </select>
            <p className="text-xs text-text-muted">
              Bank-type accounts from your chart (the seeded 1100 series).
            </p>
            {errors.gl_account && (
              <p className="text-sm text-alert">{errors.gl_account}</p>
            )}
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div className="space-y-2">
              <label htmlFor="ba-paynow-type" className="text-sm text-text-secondary">
                PayNow type
              </label>
              <select
                id="ba-paynow-type"
                value={form.paynow_type || ""}
                onChange={(e) => set("paynow_type", e.target.value)}
                className="flex h-10 w-full items-center justify-between rounded-sm border border-border bg-surface px-3 py-2 text-sm text-text-primary focus:outline-none focus:ring-2 focus:ring-accent-primary/50 focus:border-accent-primary disabled:cursor-not-allowed disabled:opacity-50"
              >
                <option value="">None</option>
                <option value="UEN">UEN</option>
                <option value="MOBILE">Mobile</option>
                <option value="NRIC">NRIC</option>
              </select>
            </div>
            <div className="space-y-2">
              <label htmlFor="ba-paynow-id" className="text-sm text-text-secondary">
                PayNow ID
              </label>
              <Input
                id="ba-paynow-id"
                value={form.paynow_id}
                onChange={(e) => set("paynow_id", e.target.value)}
                placeholder={form.paynow_type === "MOBILE" ? "+65…" : "Required with a type"}
                className="rounded-sm"
                disabled={!form.paynow_type}
              />
              {errors.paynow_id && (
                <p className="text-sm text-alert">{errors.paynow_id}</p>
              )}
            </div>
          </div>

          <label
            htmlFor="ba-default"
            className="flex items-center gap-3 text-sm text-text-primary cursor-pointer"
          >
            <input
              id="ba-default"
              type="checkbox"
              checked={form.is_default}
              onChange={(e) => set("is_default", e.target.checked)}
              className="h-4 w-4 rounded-sm"
            />
            Make this the default account
          </label>

          <DialogFooter className="gap-2">
            <Button
              type="button"
              variant="outline"
              className="rounded-sm"
              onClick={() => onOpenChange(false)}
            >
              Cancel
            </Button>
            <Button
              type="submit"
              className="rounded-sm bg-accent-primary text-void hover:bg-accent-primary-dim"
              disabled={createAccount.isPending}
            >
              {createAccount.isPending && (
                <Loader2 className="h-4 w-4 mr-2 animate-spin" aria-hidden />
              )}
              {createAccount.isPending ? "Adding…" : "Add Account"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
