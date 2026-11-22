"use client";

import * as React from "react";
import { useState } from "react";
import Link from "next/link";
import {
  ArrowLeft,
  Printer,
  Send,
  CheckCircle,
  Ban,
  Clock,
  AlertTriangle,
  Loader2,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Textarea } from "@/components/ui/textarea";
import { useAuth } from "@/providers/auth-provider";
import {
  useInvoice,
  useApproveInvoice,
  useVoidInvoice,
  useSendInvoice,
  useInvoicePDF,
  useSendInvoiceNow,
  useInvoiceNowStatus,
} from "@/hooks/use-invoices";

/**
 * Real invoice detail (P6/C-5 — replaced the mockInvoice fixture).
 * Data comes from the backend detail endpoint
 * (InvoiceDocumentDetailSerializer incl. the P6/F-11 payment state).
 */

function getStatusBadgeClass(status: string) {
  switch (status) {
    case "PAID":
      return "bg-success text-white";
    case "SENT":
    case "APPROVED":
      return "bg-accent-secondary text-void";
    case "PARTIALLY_PAID":
      return "bg-accent-secondary/70 text-void";
    case "DRAFT":
      return "bg-surface text-text-secondary border border-border";
    case "OVERDUE":
      return "bg-alert text-white";
    case "VOID":
      return "bg-surface text-text-muted line-through";
    default:
      return "bg-surface text-text-secondary";
  }
}

function formatStatus(status: string) {
  return status
    .split("_")
    .map((word) => word.charAt(0) + word.slice(1).toLowerCase())
    .join(" ");
}

function formatAmount(value: string) {
  const n = Number(value);
  if (Number.isNaN(n)) return value;
  return n.toLocaleString("en-SG", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
}

function formatDate(value: string) {
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return value;
  return d.toLocaleDateString("en-SG", {
    day: "numeric",
    month: "short",
    year: "numeric",
  });
}

interface InvoiceDetailClientProps {
  id: string;
}

export function InvoiceDetailClient({ id }: InvoiceDetailClientProps) {
  const { currentOrg, isLoading: authLoading } = useAuth();
  const orgId = currentOrg?.id ?? null;

  const { data: invoice, isLoading, isError } = useInvoice(orgId as string, id);
  const approveInvoice = useApproveInvoice(orgId as string, id);
  const voidInvoice = useVoidInvoice(orgId as string, id);
  const sendInvoice = useSendInvoice(orgId as string, id);
  // P7/F-13: previously dead hooks — the backends are real (P3/D-2 PDF
  // auth path; P5/C-2 InvoiceNow transmission), so the detail page now
  // actually exposes them.
  const downloadPdf = useInvoicePDF(orgId as string, id);
  const sendInvoiceNow = useSendInvoiceNow(orgId as string, id);
  const { data: invoiceNowStatus } = useInvoiceNowStatus(orgId as string, id);
  const [sending, setSending] = useState(false);

  // P7/F-1: the void flow needs a REASON (the backend rejects an empty
  // one — the pre-P7 page sent reason: "" and every void 400'd).
  const [voidDialogOpen, setVoidDialogOpen] = useState(false);
  const [voidReason, setVoidReason] = useState("");
  const [voidReasonTouched, setVoidReasonTouched] = useState(false);

  // P7/F-12: an authenticated user with no organisation is not an error —
  // disabled queries report isLoading=false, so guard explicitly before
  // the query states (mirrors the P5 invoices list client).
  if (authLoading) {
    return (
      <div className="flex items-center justify-center gap-2 py-24 text-text-secondary">
        <Loader2 className="h-5 w-5 animate-spin" />
        <span>Loading…</span>
      </div>
    );
  }

  if (!currentOrg) {
    return (
      <div className="space-y-4">
        <div className="flex items-center gap-4">
          <Link
            href="/invoices"
            className="inline-flex h-10 w-10 items-center justify-center border border-border text-text-secondary hover:bg-surface"
          >
            <ArrowLeft className="h-4 w-4" />
          </Link>
        </div>
        <Card className="border-border bg-carbon">
          <CardContent className="flex flex-col items-center gap-3 py-16">
            <AlertTriangle className="h-8 w-8 text-accent-secondary" />
            <p className="font-medium text-text-primary">No organisation selected</p>
            <p className="text-sm text-text-secondary">
              Select an organisation to view its invoices.
            </p>
          </CardContent>
        </Card>
      </div>
    );
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center gap-2 py-24 text-text-secondary">
        <Loader2 className="h-5 w-5 animate-spin" />
        <span>Loading invoice…</span>
      </div>
    );
  }

  if (isError || !invoice) {
    return (
      <div className="space-y-4">
        <div className="flex items-center gap-4">
          <Link
            href="/invoices"
            className="inline-flex h-10 w-10 items-center justify-center border border-border text-text-secondary hover:bg-surface"
          >
            <ArrowLeft className="h-4 w-4" />
          </Link>
        </div>
        <Card className="border-border bg-carbon">
          <CardContent className="flex flex-col items-center gap-3 py-16">
            <AlertTriangle className="h-8 w-8 text-alert" />
            <p className="font-medium text-text-primary">
              Failed to load invoice
            </p>
            <p className="text-sm text-text-secondary">
              The invoice could not be loaded. It may have been deleted, or
              the connection to the server failed.
            </p>
            <div className="flex gap-2">
              <Button variant="outline" onClick={() => window.location.reload()}>
                Retry
              </Button>
              <Link href="/invoices">
                <Button variant="outline">Back to invoices</Button>
              </Link>
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  const isDraft = invoice.status === "DRAFT";
  const isVoid = invoice.status === "VOID";
  // InvoiceNow needs an approved (ledger-posted) document (P5/C-2: the
  // transmission posts against the real document).
  const canSendInvoiceNow = !isDraft && !isVoid;
  const canSend =
    !isDraft &&
    !isVoid &&
    invoice.contact.email &&
    !sendInvoice.isPending &&
    !sending;
  // The payment state is truthful for every non-void document — an
  // unpaid invoice owes its full total (P6/F-11: always surface it).
  const showPaymentState = !isVoid;
  const isPaid = invoice.status === "PAID";

  const handleSend = async () => {
    if (!invoice.contact.email) return;
    setSending(true);
    try {
      // P7/F-6: the backend expects a LIST of recipient addresses — a bare
      // string passes the truthiness check but crashes the email task
      // (silent failure while the UI toasts success).
      await sendInvoice.mutateAsync({
        to: [invoice.contact.email],
        message: invoice.notes || undefined,
      });
    } catch {
      // onError already surfaces the toast (P7/F-18: no unhandled
      // rejection — mutateAsync rethrows).
    } finally {
      setSending(false);
    }
  };

  const openVoidDialog = () => {
    setVoidReason("");
    setVoidReasonTouched(false);
    setVoidDialogOpen(true);
  };

  const confirmVoid = () => {
    setVoidReasonTouched(true);
    const reason = voidReason.trim();
    if (!reason) return; // client-side gate; the backend enforces it too
    voidInvoice.mutate(reason, {
      onSuccess: () => setVoidDialogOpen(false),
    });
  };

  return (
    <div className="space-y-6">
      {/* Header Actions */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div className="flex items-center gap-4">
          <Link
            href="/invoices"
            className="inline-flex h-10 w-10 items-center justify-center border border-border text-text-secondary hover:bg-surface"
          >
            <ArrowLeft className="h-4 w-4" />
          </Link>
          <div>
            <h1 className="font-display text-2xl font-bold text-text-primary">
              {invoice.document_number}
            </h1>
            <div className="flex items-center gap-2 mt-1">
              <Badge
                variant="outline"
                className={getStatusBadgeClass(invoice.status)}
              >
                {formatStatus(invoice.status)}
              </Badge>
              {invoiceNowStatus?.status && invoiceNowStatus.status !== "NOT_SENT" && (
                <Badge variant="outline" className="bg-surface text-text-secondary">
                  InvoiceNow: {formatStatus(invoiceNowStatus.status)}
                </Badge>
              )}
              <span className="text-sm text-text-secondary flex items-center gap-1">
                <Clock className="h-3 w-3" />
                Due {formatDate(invoice.due_date)}
              </span>
            </div>
          </div>
        </div>

        <div className="flex items-center gap-2">
          {isDraft && (
            <Button
              onClick={() => approveInvoice.mutate()}
              disabled={approveInvoice.isPending}
              className="gap-2 bg-success hover:bg-success/90"
            >
              {approveInvoice.isPending ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <CheckCircle className="h-4 w-4" />
              )}
              Approve
            </Button>
          )}

          {!isVoid && (
            <Button
              variant="outline"
              onClick={openVoidDialog}
              disabled={voidInvoice.isPending}
              className="gap-2 text-alert hover:text-alert hover:bg-alert/10"
            >
              {voidInvoice.isPending ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Ban className="h-4 w-4" />
              )}
              Void
            </Button>
          )}

          <Button
            variant="outline"
            className="gap-2"
            onClick={handleSend}
            disabled={!canSend}
          >
            {sending || sendInvoice.isPending ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Send className="h-4 w-4" />
            )}
            Send
          </Button>

          {canSendInvoiceNow && (
            <Button
              variant="outline"
              className="gap-2"
              onClick={() => sendInvoiceNow.mutate()}
              disabled={sendInvoiceNow.isPending}
            >
              {sendInvoiceNow.isPending ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Send className="h-4 w-4" />
              )}
              Send via InvoiceNow
            </Button>
          )}

          <Button
            variant="outline"
            className="gap-2"
            onClick={() => downloadPdf.mutate()}
            disabled={downloadPdf.isPending}
          >
            {downloadPdf.isPending ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Printer className="h-4 w-4" />
            )}
            PDF
          </Button>

          <Button
            variant="outline"
            className="gap-2"
            onClick={() => window.print()}
          >
            <Printer className="h-4 w-4" />
            Print
          </Button>
        </div>
      </div>

      {/* Invoice Preview */}
      <Card className="border-border bg-carbon">
        <CardContent className="p-8 md:p-12">
          {/* Invoice Header */}
          <div className="flex flex-col md:flex-row justify-between gap-8 mb-12">
            <div>
              <h2 className="font-display text-2xl font-bold text-text-primary mb-2">
                {currentOrg?.name ?? "Your Company"}
              </h2>
              {currentOrg?.uen && (
                <p className="text-sm text-text-secondary mt-2">
                  UEN: {currentOrg.uen}
                </p>
              )}
              {currentOrg?.gst_registered && currentOrg.gst_reg_number && (
                <p className="text-sm text-text-secondary">
                  GST Reg No: {currentOrg.gst_reg_number}
                </p>
              )}
            </div>
            <div className="text-left md:text-right">
              <h3 className="font-display text-xl font-bold text-text-primary mb-2">
                {invoice.document_type === "SALES_CREDIT_NOTE"
                  ? "CREDIT NOTE"
                  : "INVOICE"}
              </h3>
              <p className="text-sm text-text-secondary">
                <span className="font-medium">Invoice #:</span>{" "}
                {invoice.document_number}
              </p>
              <p className="text-sm text-text-secondary">
                <span className="font-medium">Issue Date:</span>{" "}
                {formatDate(invoice.issue_date)}
              </p>
              <p className="text-sm text-text-secondary">
                <span className="font-medium">Due Date:</span>{" "}
                {formatDate(invoice.due_date)}
              </p>
              {invoice.reference && (
                <p className="text-sm text-text-secondary">
                  <span className="font-medium">Reference:</span>{" "}
                  {invoice.reference}
                </p>
              )}
            </div>
          </div>

          {/* Bill To */}
          <div className="mb-12">
            <p className="text-sm font-medium text-text-muted uppercase tracking-wide mb-2">
              Bill To
            </p>
            <h4 className="font-display text-lg font-semibold text-text-primary mb-1">
              {invoice.contact.name}
            </h4>
            {invoice.contact.city && (
              <p className="text-sm text-text-secondary">
                {invoice.contact.city}
                {invoice.contact.country ? `, ${invoice.contact.country}` : ""}
              </p>
            )}
            <p className="text-sm text-text-secondary mt-1">
              {invoice.contact.email}
            </p>
          </div>

          {/* Items Table */}
          <div className="overflow-x-auto mb-8">
            <table className="w-full">
              <thead>
                <tr className="border-b border-border">
                  <th className="text-left py-3 px-4 text-sm font-medium text-text-secondary">
                    Description
                  </th>
                  <th className="text-right py-3 px-4 text-sm font-medium text-text-secondary">
                    Qty
                  </th>
                  <th className="text-right py-3 px-4 text-sm font-medium text-text-secondary">
                    Rate
                  </th>
                  <th className="text-right py-3 px-4 text-sm font-medium text-text-secondary">
                    Amount
                  </th>
                </tr>
              </thead>
              <tbody>
                {invoice.lines.map((line) => (
                  <tr key={line.id} className="border-b border-border/50">
                    <td className="py-4 px-4 text-text-primary">
                      {line.description}
                    </td>
                    <td className="py-4 px-4 text-right text-text-secondary">
                      {Number(line.quantity).toLocaleString("en-SG")}
                    </td>
                    <td className="py-4 px-4 text-right text-text-secondary">
                      {formatAmount(line.unit_price)}
                    </td>
                    <td className="py-4 px-4 text-right font-medium text-text-primary">
                      {formatAmount(line.line_amount)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Totals */}
          <div className="flex justify-end mb-8">
            <div className="w-full md:w-72 space-y-2">
              <div className="flex justify-between text-sm">
                <span className="text-text-secondary">Subtotal</span>
                <span className="text-text-primary">
                  {formatAmount(invoice.total_excl)}
                </span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-text-secondary">GST</span>
                <span className="text-text-primary">
                  {formatAmount(invoice.gst_total)}
                </span>
              </div>
              <div className="my-2 border-t border-border" />
              <div className="flex justify-between font-display text-lg font-bold">
                <span className="text-text-primary">Total</span>
                <span className="text-accent-primary">
                  {formatAmount(invoice.total_incl)}
                </span>
              </div>
              {showPaymentState && (
                <>
                  <div className="flex justify-between text-sm">
                    <span className="text-text-secondary">Amount Paid</span>
                    <span className={isPaid ? "text-success" : "text-text-primary"}>
                      {formatAmount(invoice.amount_paid)}
                    </span>
                  </div>
                  <div className="flex justify-between text-sm font-medium">
                    <span className="text-text-secondary">Amount Due</span>
                    <span className={isPaid ? "text-success" : "text-alert"}>
                      {formatAmount(invoice.amount_due)}
                    </span>
                  </div>
                </>
              )}
            </div>
          </div>

          {/* Notes */}
          {invoice.notes && (
            <div className="bg-surface p-4 border border-border">
              <p className="text-sm font-medium text-text-secondary mb-1">
                Notes
              </p>
              <p className="text-sm text-text-secondary">{invoice.notes}</p>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Void reason dialog (P7/F-1) — the backend requires a non-empty
          reason; the pre-P7 page sent an empty one and every void 400'd. */}
      <Dialog open={voidDialogOpen} onOpenChange={setVoidDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Void invoice {invoice.document_number}?</DialogTitle>
            <DialogDescription>
              Voiding posts a reversing journal entry and releases any
              payment allocations. This cannot be undone.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-2">
            <label
              htmlFor="void-reason"
              className="text-sm font-medium text-text-primary"
            >
              Reason for voiding
            </label>
            <Textarea
              id="void-reason"
              value={voidReason}
              onChange={(e) => setVoidReason(e.target.value)}
              placeholder="e.g. Wrong amount billed"
              required
              aria-required="true"
              aria-invalid={voidReasonTouched && !voidReason.trim()}
              aria-describedby={
                voidReasonTouched && !voidReason.trim()
                  ? "void-reason-error"
                  : undefined
              }
            />
            {voidReasonTouched && !voidReason.trim() && (
              <p id="void-reason-error" className="text-sm text-alert" role="alert">
                A reason is required to void this invoice.
              </p>
            )}
          </div>
          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => setVoidDialogOpen(false)}
              disabled={voidInvoice.isPending}
            >
              Cancel
            </Button>
            <Button
              variant="outline"
              onClick={confirmVoid}
              disabled={voidInvoice.isPending || !voidReason.trim()}
              className="gap-2 text-alert hover:text-alert hover:bg-alert/10"
            >
              {voidInvoice.isPending && (
                <Loader2 className="h-4 w-4 animate-spin" />
              )}
              Void invoice
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
