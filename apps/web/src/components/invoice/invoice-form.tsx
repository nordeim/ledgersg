"use client";

import * as React from "react";
import { useForm, FormProvider, useFieldArray } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import {
  invoiceSchema,
  type Invoice,
  type InvoiceInput,
  type TaxCode,
  createEmptyInvoice,
  createEmptyLine,
} from "@/shared/schemas/invoice";
import { InvoiceLineRow, type LineAccountOption } from "./invoice-line-row";
import { TaxBreakdownCard } from "./tax-breakdown-card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Plus, Search, AlertCircle } from "lucide-react";
import { cn } from "@/lib/utils";
import { calculateFromLines } from "@/lib/gst-engine";
import {
  buildContactPayload,
  buildDocumentPayload,
  validateSubmissionReadiness,
} from "@/lib/invoice-submit";
import { useInvoiceStore } from "@/stores/invoice-store";
import { useAuth } from "@/providers/auth-provider";
import { useTaxCodes } from "@/hooks/use-tax-codes";
import { useRevenueAccounts } from "@/hooks/use-accounts";
import { useCreateContact } from "@/hooks/use-contacts";
import { useCreateInvoice } from "@/hooks/use-invoices";
import { ContactPicker } from "@/components/contact-picker";

interface InvoiceFormProps {
  initialData?: Partial<InvoiceInput>;
  isGSTRegistered?: boolean;
  documentType?: "SALES_INVOICE" | "SALES_QUOTE";
  onSuccess?: (invoiceId: string) => void;
}

export function InvoiceForm({
  initialData,
  isGSTRegistered = true,
  documentType = "SALES_INVOICE",
  onSuccess,
}: InvoiceFormProps) {
  const { setHasUnsavedChanges } = useInvoiceStore();
  const [isSubmitting, setIsSubmitting] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);

  // P10/H-1: the customer card has two modes. "select" (the default)
  // picks an EXISTING contact through the searchable picker — no contact
  // row is created on submit (the old flow unconditionally created one,
  // duplicating UEN-less customers on every invoice and failing on repeat
  // UENs). "new" is the explicit new-customer act that still creates.
  const [contactMode, setContactMode] = React.useState<"select" | "new">(
    "select"
  );
  const [pickedContactId, setPickedContactId] = React.useState<string | null>(
    null
  );

  const { currentOrg } = useAuth();
  const orgId = currentOrg?.id ?? null;

  const defaultValues = React.useMemo(() => {
    const empty = createEmptyInvoice();
    return {
      ...empty,
      ...initialData,
    } as InvoiceInput;
  }, [initialData]);

  const methods = useForm<InvoiceInput>({
    resolver: zodResolver(invoiceSchema),
    defaultValues,
    mode: "onChange",
  });

  const {
    control,
    handleSubmit,
    watch,
    formState: { isDirty },
  } = methods;

  // Server-resolved tax codes in force on the document's own date (P3/D-3)
  const issueDate = watch("issue_date");
  const { data: taxCodes } = useTaxCodes(orgId, issueDate);
  const { data: revenueAccounts } = useRevenueAccounts(orgId);

  const createContact = useCreateContact(orgId ?? "");
  const createInvoice = useCreateInvoice(orgId ?? "");

  const { fields, append, remove } = useFieldArray({
    control,
    name: "lines",
  });

  // Watch lines for real-time calculations
  const lines = watch("lines") || [];

  // Rate overrides from the server-resolved rows (per tax code) drive the
  // preview at the rate in force on the document date (P3/D-3).
  const rateOverrides = React.useMemo<Partial<Record<TaxCode, string>> | undefined>(() => {
    if (!taxCodes || taxCodes.length === 0) return undefined;
    const map: Partial<Record<TaxCode, string>> = {};
    for (const tc of taxCodes) {
      map[tc.code] = tc.rate;
    }
    return map;
  }, [taxCodes]);

  // Calculate totals
  const { totals } = React.useMemo(() => {
    return calculateFromLines(lines as Invoice["lines"], rateOverrides);
  }, [lines, rateOverrides]);

  // Update form totals
  const setTotals = React.useCallback(
    (t: typeof totals) => {
      methods.setValue("subtotal", t.subtotal);
      methods.setValue("gst_amount", t.gst_amount);
      methods.setValue("total_amount", t.total_amount);
    },
    [methods]
  );
  React.useEffect(() => {
    setTotals(totals);
  }, [totals, setTotals]);

  // Track unsaved changes
  React.useEffect(() => {
    setHasUnsavedChanges(isDirty);
  }, [isDirty, setHasUnsavedChanges]);

  // Add new line
  const handleAddLine = () => {
    append(createEmptyLine() as InvoiceInput["lines"][number]);
  };

  // Remove line
  const handleRemoveLine = (index: number) => {
    if (fields.length > 1) {
      remove(index);
    }
  };

  // Form submission (P3/D-1 + P10/H-1): a picked existing contact submits
  // with its contact_id (no contact row is created); the explicit
  // new-customer mode creates the contact first. In both paths the server
  // recalculates every amount authoritatively.
  const onSubmit = async (data: InvoiceInput) => {
    setIsSubmitting(true);
    setError(null);

    try {
      const taxCodeIdByCode = new Map(
        (taxCodes ?? []).map((tc) => [tc.code, tc.id] as const)
      );

      const problems = validateSubmissionReadiness(
        data as Invoice,
        taxCodeIdByCode,
        { requireCustomerName: contactMode === "new" }
      );
      if (problems.length > 0) {
        setError(problems[0]);
        return;
      }

      let contactId: string;
      if (contactMode === "select") {
        if (!pickedContactId) {
          setError(
            "Select a customer (or switch to New customer to create one)."
          );
          return;
        }
        contactId = pickedContactId;
      } else {
        const contact = await createContact.mutateAsync(
          buildContactPayload(data as Invoice)
        );
        contactId = contact.id;
      }

      const document = await createInvoice.mutateAsync(
        buildDocumentPayload(
          data as Invoice,
          contactId,
          taxCodeIdByCode,
          documentType
        )
      );

      if (!document.id) {
        setError("The server response did not include the created document id.");
        return;
      }
      onSuccess?.(document.id);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Failed to save invoice"
      );
    } finally {
      setIsSubmitting(false);
    }
  };

  const onSaveDraft = () => {
    // The create endpoint always creates a DRAFT document — "save draft"
    // runs the same validated submission path.
    handleSubmit(onSubmit, onInvalidSubmit)();
  };

  // P10/H-1: in select mode the customer card renders no name input, so
  // zod's customer.name requirement fails invisibly — surface the real
  // guidance (pick a customer or switch to new-customer mode) instead.
  const onInvalidSubmit = (errors: Record<string, { message?: string }>) => {
    if (contactMode === "select" && !pickedContactId) {
      setError("Select a customer (or switch to New customer to create one).");
      return;
    }
    // A picked customer satisfies the schema; any other validation miss
    // surfaces its message instead of failing silently.
    const first = Object.values(errors)[0];
    if (first?.message) {
      setError(first.message);
    }
  };

  const accountOptions: LineAccountOption[] = React.useMemo(
    () =>
      (revenueAccounts ?? []).map((acc) => ({
        id: acc.id,
        code: acc.code,
        name: acc.name,
      })),
    [revenueAccounts]
  );

  return (
    <FormProvider {...methods}>
      <form
        onSubmit={handleSubmit(onSubmit, onInvalidSubmit)}
        className="space-y-6"
      >
        {error && (
          <div
            className="bg-alert/10 border border-alert rounded-sm p-4 flex items-start gap-3"
            role="alert"
          >
            <AlertCircle className="h-5 w-5 text-alert flex-shrink-0 mt-0.5" />
            <p className="text-sm text-alert">{error}</p>
          </div>
        )}

        <div className="grid gap-6 lg:grid-cols-3">
          {/* Main Form */}
          <div className="lg:col-span-2 space-y-6">
            {/* Invoice Details */}
            <Card className="border-border bg-carbon rounded-sm">
              <CardHeader>
                <CardTitle className="font-display text-lg text-text-primary">
                  Invoice Details
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid gap-4 md:grid-cols-2">
                  <Input
                    label="Invoice Number"
                    {...methods.register("invoice_number")}
                    error={methods.formState.errors.invoice_number?.message}
                  />
                  <Input
                    label="Reference"
                    {...methods.register("reference")}
                    placeholder="Optional reference"
                  />
                </div>
                <div className="grid gap-4 md:grid-cols-2">
                  <Input
                    label="Issue Date"
                    type="date"
                    {...methods.register("issue_date")}
                    error={methods.formState.errors.issue_date?.message}
                  />
                  <Input
                    label="Due Date"
                    type="date"
                    {...methods.register("due_date")}
                    error={methods.formState.errors.due_date?.message}
                  />
                </div>
              </CardContent>
            </Card>

            {/* Customer Details — P10/H-1: pick an existing customer (the
                default; no contact row is created on submit) or explicitly
                create a new one. The old card created a contact on EVERY
                submission — duplicating UEN-less customers and failing on
                repeat UENs. */}
            <Card className="border-border bg-carbon rounded-sm">
              <CardHeader className="flex flex-row items-center justify-between space-y-0">
                <CardTitle className="font-display text-lg text-text-primary">
                  Customer
                </CardTitle>
                {contactMode === "select" ? (
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    className="rounded-sm border-border"
                    onClick={() => {
                      setContactMode("new");
                      setPickedContactId(null);
                    }}
                  >
                    <Plus className="h-3.5 w-3.5" aria-hidden />
                    New customer
                  </Button>
                ) : (
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    className="rounded-sm border-border"
                    onClick={() => {
                      setContactMode("select");
                      setPickedContactId(null);
                    }}
                  >
                    <Search className="h-3.5 w-3.5" aria-hidden />
                    Search existing customers
                  </Button>
                )}
              </CardHeader>
              <CardContent className="space-y-4">
                {contactMode === "select" ? (
                  <div className="space-y-2">
                    <span
                      id="customer-picker-label"
                      className="text-sm font-medium text-text-secondary"
                    >
                      Customer
                    </span>
                    <ContactPicker
                      orgId={orgId ?? ""}
                      type="customer"
                      value={pickedContactId ?? ""}
                      onChange={setPickedContactId}
                      onSelect={(contact) => {
                        // Mirror the picked row into the form state so the
                        // zod schema (customer.name required) is satisfied;
                        // the submit path uses pickedContactId itself.
                        methods.setValue("customer.id", contact.id, {
                          shouldValidate: false,
                        });
                        methods.setValue("customer.name", contact.name, {
                          shouldValidate: false,
                        });
                      }}
                      disabled={isSubmitting}
                    />
                    <p className="text-xs text-text-muted">
                      Pick an existing customer — invoicing them again reuses
                      the same contact record.
                    </p>
                  </div>
                ) : (
                  <>
                    <div className="grid gap-4 md:grid-cols-2">
                      <Input
                        label="Customer Name"
                        {...methods.register("customer.name")}
                        error={methods.formState.errors.customer?.name?.message}
                      />
                      <Input
                        label="Email"
                        type="email"
                        {...methods.register("customer.email")}
                        error={methods.formState.errors.customer?.email?.message}
                      />
                    </div>
                    <div className="grid gap-4 md:grid-cols-2">
                      <Input
                        label="UEN (Optional)"
                        {...methods.register("customer.uen")}
                        placeholder="201912345A"
                        error={methods.formState.errors.customer?.uen?.message}
                      />
                      <Input
                        label="GST Registration No (Optional)"
                        {...methods.register("customer.gst_registration_no")}
                        placeholder="M90345678"
                      />
                    </div>
                  </>
                )}
              </CardContent>
            </Card>

            {/* Line Items */}
            <Card className="border-border bg-carbon rounded-sm">
              <CardHeader className="flex flex-row items-center justify-between">
                <CardTitle className="font-display text-lg text-text-primary">
                  Line Items
                </CardTitle>
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={handleAddLine}
                  className="rounded-sm border-border text-text-secondary"
                >
                  <Plus className="h-4 w-4 mr-2" />
                  Add Line
                </Button>
              </CardHeader>
              <CardContent>
                {/* Header Row */}
                <div
                  className="grid grid-cols-12 gap-2 pb-2 border-b border-border text-xs font-medium text-text-secondary"
                  role="rowheader"
                >
                  <div className="col-span-1"></div>
                  <div className="col-span-3">Description</div>
                  <div className="col-span-1 text-right">Qty</div>
                  <div className="col-span-2 text-right">Price</div>
                  <div className="col-span-1 text-right">Disc%</div>
                  <div className="col-span-1">Account</div>
                  <div className="col-span-1">Tax</div>
                  <div className="col-span-1 text-right">Total</div>
                  <div className="col-span-1"></div>
                </div>

                {/* Line Items */}
                <div role="rowgroup">
                  {fields.map((field, index) => (
                    <InvoiceLineRow
                      key={field.id}
                      index={index}
                      isGSTRegistered={isGSTRegistered}
                      onRemove={() => handleRemoveLine(index)}
                      accounts={accountOptions}
                      taxCodes={taxCodes}
                    />
                  ))}
                </div>

                {methods.formState.errors.lines && (
                  <p className="text-sm text-alert mt-2" role="alert">
                    {methods.formState.errors.lines.message}
                  </p>
                )}
              </CardContent>
            </Card>

            {/* Notes */}
            <Card className="border-border bg-carbon rounded-sm">
              <CardHeader>
                <CardTitle className="font-display text-lg text-text-primary">
                  Notes & Terms
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div>
                  <label className="text-sm font-medium text-text-secondary mb-1.5 block">
                    Notes
                  </label>
                  <textarea
                    {...methods.register("notes")}
                    rows={3}
                    className={cn(
                      "flex w-full rounded-sm border bg-surface px-3 py-2 text-sm",
                      "text-text-primary placeholder:text-text-muted",
                      "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent-primary/50 focus-visible:border-accent-primary",
                      "disabled:opacity-50 disabled:cursor-not-allowed",
                      "transition-colors resize-none",
                      "border-border"
                    )}
                    placeholder="Additional notes for the customer..."
                  />
                </div>
                <div>
                  <label className="text-sm font-medium text-text-secondary mb-1.5 block">
                    Terms & Conditions
                  </label>
                  <textarea
                    {...methods.register("terms")}
                    rows={2}
                    className={cn(
                      "flex w-full rounded-sm border bg-surface px-3 py-2 text-sm",
                      "text-text-primary placeholder:text-text-muted",
                      "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent-primary/50 focus-visible:border-accent-primary",
                      "disabled:opacity-50 disabled:cursor-not-allowed",
                      "transition-colors resize-none",
                      "border-border"
                    )}
                    placeholder="Payment terms and conditions..."
                  />
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Sidebar - Tax Breakdown */}
          <div className="lg:col-span-1">
            <TaxBreakdownCard
              isGSTRegistered={isGSTRegistered}
              totals={totals}
              onSubmit={handleSubmit(onSubmit, onInvalidSubmit)}
              onSaveDraft={onSaveDraft}
              isSubmitting={isSubmitting}
            />
          </div>
        </div>
      </form>
    </FormProvider>
  );
}
