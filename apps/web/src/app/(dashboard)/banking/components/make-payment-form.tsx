"use client";

import { useState } from "react";
import { Card, CardContent, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { AlertCircle, X } from "lucide-react";
import { MoneyInput } from "@/components/ui/money-input";
import { useMakePayment, useBankAccounts } from "@/hooks/use-banking";
import { paymentMakeInputSchema } from "@/shared/schemas";
import type { PaymentMakeInput } from "@/shared/schemas";
import { ContactPicker } from "@/components/contact-picker";
import { AllocationSection } from "./allocation-section";
import type { PaymentAllocationEntry } from "@/shared/schemas/payment";
import { z } from "zod";

/**
 * P9/B-5: the Make Payment form — the banking page's "Make Payment" button
 * set `showMakeForm` state that nothing read (no form existed), while
 * useMakePayment + POST /payments/make/ were real and unconsumed. Payables
 * could never be recorded, so aged payables could never be populated by UI
 * action. Mirrors the receive form with supplier-side contact search.
 */

interface MakePaymentFormProps {
  orgId: string;
  onSuccess?: () => void;
  onCancel?: () => void;
}

const PAYMENT_METHODS = [
  { value: "BANK_TRANSFER", label: "Bank Transfer" },
  { value: "CHEQUE", label: "Cheque" },
  { value: "CASH", label: "Cash" },
  { value: "PAYNOW", label: "PayNow" },
  { value: "CREDIT_CARD", label: "Credit Card" },
  { value: "GIRO", label: "GIRO" },
  { value: "OTHER", label: "Other" },
] as const;

export function MakePaymentForm({ orgId, onSuccess, onCancel }: MakePaymentFormProps) {
  const { data: accountsData, isLoading: isLoadingAccounts } = useBankAccounts(orgId, { is_active: true });
  const makePayment = useMakePayment(orgId);

  const [formData, setFormData] = useState<Partial<PaymentMakeInput>>({
    contact_id: "",
    bank_account_id: "",
    payment_date: new Date().toISOString().split("T")[0],
    amount: "",
    currency: "SGD",
    exchange_rate: "1.000000",
    payment_method: "BANK_TRANSFER",
    payment_reference: "",
    notes: "",
  });
  const [allocations, setAllocations] = useState<PaymentAllocationEntry[]>([]);

  const [errors, setErrors] = useState<Record<string, string>>({});
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleChange = (field: keyof PaymentMakeInput, value: string) => {
    setFormData((prev) => ({ ...prev, [field]: value }));
    if (errors[field]) {
      setErrors((prev) => {
        const newErrors = { ...prev };
        delete newErrors[field];
        return newErrors;
      });
    }
  };

  const validateForm = (): boolean => {
    try {
      paymentMakeInputSchema.parse(formData);
      setErrors({});
      return true;
    } catch (error) {
      if (error instanceof z.ZodError) {
        const newErrors: Record<string, string> = {};
        error.issues.forEach((issue) => {
          if (issue.path && issue.path.length > 0) {
            const field = String(issue.path[0]);
            newErrors[field] = issue.message;
          }
        });
        setErrors(newErrors);
      }
      return false;
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!validateForm()) return;

    setIsSubmitting(true);
    try {
      await makePayment.mutateAsync({
        ...(formData as PaymentMakeInput),
        // P9/B-3b: settle the supplier's open bills (PAY- documents
        // populate aged payables).
        ...(allocations.length > 0 ? { allocations } : {}),
      });
      onSuccess?.();
    } catch {
      setIsSubmitting(false);
    }
  };

  const bankAccounts = accountsData?.results || [];

  return (
    <Card className="border-border bg-carbon rounded-sm w-full max-w-2xl">
      <form onSubmit={handleSubmit}>
        <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle className="font-display text-lg text-text-primary">
            Make Payment
          </CardTitle>
          <Button
            type="button"
            variant="ghost"
            size="icon"
            onClick={onCancel}
            className="h-8 w-8"
          >
            <X className="h-4 w-4" />
          </Button>
        </CardHeader>

        <CardContent className="space-y-4">
          {makePayment.isError && (
            <Alert variant="destructive" className="rounded-sm">
              <AlertCircle className="h-4 w-4" />
              <AlertDescription>
                Failed to make payment. Please check your input and try again.
              </AlertDescription>
            </Alert>
          )}

          <div className="grid grid-cols-2 gap-4">
            {/* Supplier */}
            <div className="space-y-2">
              <label className="text-sm text-text-secondary">
                Supplier <span className="text-alert">*</span>
              </label>
              <ContactPicker
                orgId={orgId}
                type="supplier"
                value={formData.contact_id || ""}
                onChange={(id) => handleChange("contact_id", id)}
                disabled={isSubmitting}
                invalid={!!errors.contact_id}
              />
              {errors.contact_id && (
                <p className="text-sm text-alert">{errors.contact_id}</p>
              )}
            </div>

            {/* Bank Account */}
            <div className="space-y-2">
              <label className="text-sm text-text-secondary">
                Bank Account <span className="text-alert">*</span>
              </label>
              <Select
                value={formData.bank_account_id}
                onValueChange={(value) => handleChange("bank_account_id", value)}
                disabled={isLoadingAccounts || isSubmitting}
              >
                <SelectTrigger className="rounded-sm" aria-label="Bank account">
                  <SelectValue placeholder="Select account" />
                </SelectTrigger>
                <SelectContent>
                  {bankAccounts.map((account) => (
                    <SelectItem key={account.id} value={account.id}>
                      {account.account_name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              {errors.bank_account_id && (
                <p className="text-sm text-alert">{errors.bank_account_id}</p>
              )}
            </div>

            {/* Amount */}
            <div className="space-y-2">
              <label className="text-sm text-text-secondary">
                Amount <span className="text-alert">*</span>
              </label>
              <MoneyInput
                value={formData.amount || ""}
                onChange={(value) => handleChange("amount", value)}
                ariaLabel="Payment amount"
                disabled={isSubmitting}
              />
              {errors.amount && (
                <p className="text-sm text-alert">{errors.amount}</p>
              )}
            </div>

            {/* Payment Date */}
            <div className="space-y-2">
              <label className="text-sm text-text-secondary">
                Payment Date <span className="text-alert">*</span>
              </label>
              <Input
                type="date"
                value={formData.payment_date || ""}
                onChange={(e) => handleChange("payment_date", e.target.value)}
                className="rounded-sm"
                disabled={isSubmitting}
              />
              {errors.payment_date && (
                <p className="text-sm text-alert">{errors.payment_date}</p>
              )}
            </div>

            {/* Payment Method */}
            <div className="space-y-2">
              <label className="text-sm text-text-secondary">
                Payment Method <span className="text-alert">*</span>
              </label>
              <Select
                value={formData.payment_method}
                onValueChange={(value) => handleChange("payment_method", value)}
                disabled={isSubmitting}
              >
                <SelectTrigger className="rounded-sm">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {PAYMENT_METHODS.map((method) => (
                    <SelectItem key={method.value} value={method.value}>
                      {method.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              {errors.payment_method && (
                <p className="text-sm text-alert">{errors.payment_method}</p>
              )}
            </div>

            {/* Reference */}
            <div className="space-y-2">
              <label className="text-sm text-text-secondary">Reference</label>
              <Input
                placeholder="e.g., BILL-000012"
                value={formData.payment_reference || ""}
                onChange={(e) => handleChange("payment_reference", e.target.value)}
                className="rounded-sm"
                disabled={isSubmitting}
              />
            </div>
          </div>

          {/* Notes */}
          <div className="space-y-2">
            <label className="text-sm text-text-secondary">Notes</label>
            <Input
              placeholder="Additional notes..."
              value={formData.notes || ""}
              onChange={(e) => handleChange("notes", e.target.value)}
              className="rounded-sm"
              disabled={isSubmitting}
            />
          </div>

          {/* P9/B-3b: settle the supplier's open bills with this payment */}
          <AllocationSection
            orgId={orgId}
            contactId={formData.contact_id || ""}
            documentType="PURCHASE_INVOICE"
            allocations={allocations}
            onChange={setAllocations}
            disabled={isSubmitting}
          />
        </CardContent>

        <CardFooter className="flex justify-end gap-2">
          <Button
            type="button"
            variant="outline"
            onClick={onCancel}
            disabled={isSubmitting}
            className="rounded-sm"
          >
            Cancel
          </Button>
          <Button
            type="submit"
            disabled={isSubmitting || isLoadingAccounts}
            className="rounded-sm bg-accent-primary text-void hover:bg-accent-primary-dim"
          >
            {isSubmitting ? "Recording…" : "Make Payment"}
          </Button>
        </CardFooter>
      </form>
    </Card>
  );
}
