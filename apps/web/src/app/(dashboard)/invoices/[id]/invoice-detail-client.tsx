"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import Link from "next/link";
import {
  ArrowLeft,
  Edit,
  Printer,
  Send,
  CheckCircle,
  Ban,
  Trash2,
  Clock,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

// Mock invoice data
const mockInvoice = {
  id: "INV-2024-0001",
  status: "pending",
  issueDate: "2024-01-15",
  dueDate: "2024-02-15",
  client: {
    name: "Acme Corporation Pte Ltd",
    email: "accounts@acme.sg",
    address: "123 Business Park Road\nSingapore 609921",
  },
  company: {
    name: "Ledger SG Pte Ltd",
    uen: "202412345K",
    address: "456 Finance Street\nSingapore 049123",
    email: "hello@ledgersg.com",
  },
  items: [
    { description: "Consulting Services - January 2024", quantity: 40, rate: 150, amount: 6000 },
    { description: "Software Development", quantity: 20, rate: 200, amount: 4000 },
  ],
  subtotal: 10000,
  gstRate: 9,
  gstAmount: 900,
  total: 10900,
  notes: "Payment due within 30 days. Please include invoice number in payment reference.",
};

const statusConfig: Record<string, { label: string; className: string }> = {
  draft: { label: "Draft", className: "bg-accent-secondary text-void" },
  pending: { label: "Pending", className: "bg-amber-500 text-void" },
  paid: { label: "Paid", className: "bg-success text-white" },
  overdue: { label: "Overdue", className: "bg-alert text-white" },
  void: { label: "Void", className: "border-border text-text-secondary" },
};

interface InvoiceDetailClientProps {
  id: string;
}

export function InvoiceDetailClient({ id }: InvoiceDetailClientProps) {
  const router = useRouter();
  const [invoice, setInvoice] = useState(mockInvoice);

  const handleApprove = () => {
    setInvoice((prev) => ({ ...prev, status: "pending" }));
  };

  const handleVoid = () => {
    setInvoice((prev) => ({ ...prev, status: "void" }));
  };

  const handleDelete = () => {
    router.push("/invoices");
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
              {invoice.id}
            </h1>
            <div className="flex items-center gap-2 mt-1">
              <Badge
                variant="outline"
                className={statusConfig[invoice.status]?.className || ""}
              >
                {statusConfig[invoice.status]?.label || invoice.status}
              </Badge>
              <span className="text-sm text-text-secondary flex items-center gap-1">
                <Clock className="h-3 w-3" />
                Due {invoice.dueDate}
              </span>
            </div>
          </div>
        </div>

        <div className="flex items-center gap-2">
          {invoice.status === "draft" && (
            <Button
              onClick={handleApprove}
              className="gap-2 bg-success hover:bg-success/90"
            >
              <CheckCircle className="h-4 w-4" />
              Approve
            </Button>
          )}
          
          <Button variant="outline" className="gap-2">
            <Printer className="h-4 w-4" />
            Print
          </Button>
          
          <Button variant="outline" className="gap-2">
            <Send className="h-4 w-4" />
            Send
          </Button>

          <Button variant="outline" size="icon" onClick={() => router.push(`/invoices/${id}/edit`)}>
            <Edit className="h-4 w-4" />
          </Button>
          
          {invoice.status !== "void" && (
            <Button variant="outline" size="icon" onClick={handleVoid} className="text-alert hover:text-alert hover:bg-alert/10">
              <Ban className="h-4 w-4" />
            </Button>
          )}
          
          <Button variant="outline" size="icon" onClick={handleDelete} className="text-alert hover:text-alert hover:bg-alert/10">
            <Trash2 className="h-4 w-4" />
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
                {invoice.company.name}
              </h2>
              <p className="text-sm text-text-secondary whitespace-pre-line">
                {invoice.company.address}
              </p>
              <p className="text-sm text-text-secondary mt-2">
                UEN: {invoice.company.uen}
              </p>
              <p className="text-sm text-text-secondary">
                {invoice.company.email}
              </p>
            </div>
            <div className="text-left md:text-right">
              <h3 className="font-display text-xl font-bold text-text-primary mb-2">
                INVOICE
              </h3>
              <p className="text-sm text-text-secondary">
                <span className="font-medium">Invoice #:</span> {invoice.id}
              </p>
              <p className="text-sm text-text-secondary">
                <span className="font-medium">Issue Date:</span> {invoice.issueDate}
              </p>
              <p className="text-sm text-text-secondary">
                <span className="font-medium">Due Date:</span> {invoice.dueDate}
              </p>
            </div>
          </div>

          {/* Bill To */}
          <div className="mb-12">
            <p className="text-sm font-medium text-text-muted uppercase tracking-wide mb-2">
              Bill To
            </p>
            <h4 className="font-display text-lg font-semibold text-text-primary mb-1">
              {invoice.client.name}
            </h4>
            <p className="text-sm text-text-secondary whitespace-pre-line">
              {invoice.client.address}
            </p>
            <p className="text-sm text-text-secondary mt-1">
              {invoice.client.email}
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
                {invoice.items.map((item, index) => (
                  <tr key={index} className="border-b border-border/50">
                    <td className="py-4 px-4 text-text-primary">
                      {item.description}
                    </td>
                    <td className="py-4 px-4 text-right text-text-secondary">
                      {item.quantity}
                    </td>
                    <td className="py-4 px-4 text-right text-text-secondary">
                      ${item.rate.toLocaleString()}
                    </td>
                    <td className="py-4 px-4 text-right font-medium text-text-primary">
                      ${item.amount.toLocaleString()}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Totals */}
          <div className="flex justify-end mb-8">
            <div className="w-full md:w-64 space-y-2">
              <div className="flex justify-between text-sm">
                <span className="text-text-secondary">Subtotal</span>
                <span className="text-text-primary">${invoice.subtotal.toLocaleString()}</span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-text-secondary">GST ({invoice.gstRate}%)</span>
                <span className="text-text-primary">${invoice.gstAmount.toLocaleString()}</span>
              </div>
              <div className="my-2 border-t border-border" />
              <div className="flex justify-between font-display text-lg font-bold">
                <span className="text-text-primary">Total</span>
                <span className="text-accent-primary">${invoice.total.toLocaleString()}</span>
              </div>
            </div>
          </div>

          {/* Notes */}
          {invoice.notes && (
            <div className="bg-surface p-4 border border-border">
              <p className="text-sm font-medium text-text-secondary mb-1">Notes</p>
              <p className="text-sm text-text-secondary">{invoice.notes}</p>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
