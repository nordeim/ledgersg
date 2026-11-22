/**
 * Invoice Hooks - LedgerSG Frontend
 * 
 * Provides hooks for invoice operations including:
 * - Listing and filtering invoices
 * - Creating and updating invoices
 * - Approving and voiding invoices
 * - Sending invoices via email
 * - Sending via InvoiceNow (Peppol)
 * - PDF generation
 * 
 * All hooks use TanStack Query for caching and state management.
 */

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api, endpoints } from "@/lib/api-client";
import { toast } from "@/hooks/use-toast";
import type { Invoice } from "@/shared/schemas/invoice";
import type { DocumentPayload } from "@/lib/invoice-submit";

/**
 * The REAL backend list contract (InvoiceDocumentListSerializer):
 * a lightweight row shape — NOT the full client-side Invoice schema
 * (P5: the hook previously typed the response as Invoice, a type lie).
 */
export interface InvoiceListItem {
  id: string;
  document_type: string;
  document_number: string;
  contact_id: string;
  contact_name: string;
  issue_date: string;
  due_date: string;
  status: string;
  status_display: string;
  total_incl: string;
  currency: string;
}

export interface InvoiceListResponse {
  results: InvoiceListItem[];
  count: number;
  next?: string;
  previous?: string;
}

/**
 * The REAL backend detail contract (InvoiceDocumentDetailSerializer,
 * P6/F-11): nested contact + lines + totals + the payment state
 * (amount_paid persisted, amount_due from the DB generated column).
 */
export interface InvoiceDetailLine {
  id: string;
  line_number: number;
  description: string;
  account_id: string;
  account_code: string;
  account_name: string;
  quantity: string;
  unit_price: string;
  discount_pct: string;
  discount_amount: string;
  line_amount: string;
  tax_code_id: string | null;
  tax_code_code: string | null;
  tax_rate: string;
  gst_amount: string;
  total_amount: string;
  is_bcrs_deposit: boolean;
}

export interface InvoiceDetail {
  id: string;
  document_type: string;
  document_number: string;
  contact: {
    id: string;
    name: string;
    contact_type: string;
    is_customer: boolean;
    is_supplier: boolean;
    email: string;
    phone: string;
    is_active: boolean;
    city: string;
    country: string;
  };
  issue_date: string;
  due_date: string;
  reference: string;
  notes: string;
  status: string;
  lines: InvoiceDetailLine[];
  total_excl: string;
  gst_total: string;
  total_incl: string;
  currency: string;
  amount_paid: string;
  amount_due: string;
  journal_entry_id: string | null;
  peppol_status: string;
  approved_at: string | null;
  voided_at: string | null;
  status_history: unknown[];
  created_at: string;
  updated_at: string;
}

// List invoices with optional filters (orgId nullable: the query stays
// disabled until the org context resolves)
export function useInvoices(
  orgId: string | null | undefined,
  filters?: {
    status?: string;
    document_type?: string;
    search?: string;
    date_from?: string;
    date_to?: string;
  }
) {
  const queryString = filters
    ? "?" + new URLSearchParams(Object.entries(filters).filter(([, v]) => v)).toString()
    : "";

  return useQuery({
    queryKey: [orgId, "invoices", filters],
    queryFn: async () => {
      const response = await api.get<InvoiceListResponse>(
        endpoints.invoices(orgId as string).list + queryString
      );
      return response;
    },
    enabled: !!orgId,
  });
}

// Get single invoice detail
export function useInvoice(orgId: string, invoiceId: string) {
  return useQuery({
    queryKey: [orgId, "invoices", invoiceId],
    queryFn: async () => {
      const response = await api.get<InvoiceDetail>(
        endpoints.invoices(orgId).detail(invoiceId)
      );
      return response;
    },
    enabled: !!orgId && !!invoiceId,
  });
}

// Create invoice
// The mutationFn takes the backend create contract (mapped from the form
// by lib/invoice-submit.ts — P3/D-1).
export function useCreateInvoice(orgId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (data: DocumentPayload) => {
      const response = await api.post<Invoice>(
        endpoints.invoices(orgId).list,
        data
      );
      return response;
    },
    onSuccess: () => {
      toast({
        title: "Invoice created",
        description: "Your invoice has been created successfully.",
        variant: "success",
      });
      // Invalidate invoices list
      queryClient.invalidateQueries({ queryKey: [orgId, "invoices"] });
      // Invalidate dashboard metrics
      queryClient.invalidateQueries({ queryKey: [orgId, "dashboard"] });
    },
    onError: (error: Error) => {
      toast({
        title: "Failed to create invoice",
        description: error.message || "An error occurred while creating the invoice.",
        variant: "error",
      });
    },
  });
}

// Update-invoice hook removed (P7/F-13): it was dead code wired to the
// orphaned mock-era edit route; the backend update contract only accepts
// due_date/reference/notes (no line editing). The real edit flow is
// registered deferred debt — do not re-add a hook that pretends to edit.

// Approve invoice (DRAFT -> APPROVED)
export function useApproveInvoice(orgId: string, invoiceId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async () => {
      const response = await api.post<Invoice>(
        endpoints.invoices(orgId).approve(invoiceId),
        {}
      );
      return response;
    },
    onSuccess: () => {
      toast({
        title: "Invoice approved",
        description: "The invoice has been approved and journal entries have been created.",
        variant: "success",
      });
      queryClient.invalidateQueries({ queryKey: [orgId, "invoices", invoiceId] });
      queryClient.invalidateQueries({ queryKey: [orgId, "invoices"] });
      queryClient.invalidateQueries({ queryKey: [orgId, "dashboard"] });
      queryClient.invalidateQueries({ queryKey: [orgId, "ledger"] });
    },
    onError: (error: Error) => {
      toast({
        title: "Failed to approve invoice",
        description: error.message || "An error occurred while approving the invoice.",
        variant: "error",
      });
    },
  });
}

// Void invoice
export function useVoidInvoice(orgId: string, invoiceId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (reason: string) => {
      const response = await api.post<Invoice>(
        endpoints.invoices(orgId).void(invoiceId),
        { reason }
      );
      return response;
    },
    onSuccess: () => {
      toast({
        title: "Invoice voided",
        description: "The invoice has been voided and reversal entries have been created.",
        variant: "warning",
      });
      queryClient.invalidateQueries({ queryKey: [orgId, "invoices", invoiceId] });
      queryClient.invalidateQueries({ queryKey: [orgId, "invoices"] });
      queryClient.invalidateQueries({ queryKey: [orgId, "dashboard"] });
      // P7/F-8: voiding posts the reversal journal entry — the ledger page
      // must refresh too (approve already invalidated it; void did not).
      queryClient.invalidateQueries({ queryKey: [orgId, "ledger"] });
    },
    onError: (error: Error) => {
      toast({
        title: "Failed to void invoice",
        description: error.message || "An error occurred while voiding the invoice.",
        variant: "error",
      });
    },
  });
}

// Send invoice via email
export function useSendInvoice(orgId: string, invoiceId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (emailData: {
      /** Recipient addresses — a LIST (P7/F-6): the backend passes them
       * straight to the email task; a bare string crashes it silently. */
      to: string[];
      cc?: string[];
      message?: string;
    }) => {
      const response = await api.post<Invoice>(
        endpoints.invoices(orgId).send(invoiceId),
        emailData
      );
      return response;
    },
    onSuccess: () => {
      toast({
        title: "Invoice sent",
        description: "The invoice has been sent via email.",
        variant: "success",
      });
      queryClient.invalidateQueries({ queryKey: [orgId, "invoices", invoiceId] });
    },
    onError: (error: Error) => {
      toast({
        title: "Failed to send invoice",
        description: error.message || "An error occurred while sending the invoice.",
        variant: "error",
      });
    },
  });
}

// Send via InvoiceNow (Peppol)
export function useSendInvoiceNow(orgId: string, invoiceId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async () => {
      const response = await api.post<{
        status: string;
        message_id: string;
        transmission_log_id: string;
      }>(endpoints.invoices(orgId).sendInvoiceNow(invoiceId), {});
      return response;
    },
    onSuccess: () => {
      toast({
        title: "InvoiceNow transmission queued",
        description: "The invoice has been queued for InvoiceNow transmission. Check status for updates.",
        variant: "info",
      });
      queryClient.invalidateQueries({ queryKey: [orgId, "invoices", invoiceId] });
      queryClient.invalidateQueries({ queryKey: [orgId, "peppol"] });
    },
    onError: (error: Error) => {
      toast({
        title: "InvoiceNow transmission failed",
        description: error.message || "An error occurred while queuing the InvoiceNow transmission.",
        variant: "error",
      });
    },
  });
}

// InvoiceNow status response type
interface InvoiceNowStatusResponse {
  status: string;
  message_id?: string;
  transmitted_at?: string;
  delivered_at?: string;
  logs: Array<{
    id: string;
    status: string;
    timestamp: string;
    error_message?: string;
  }>;
}

// Get InvoiceNow status
export function useInvoiceNowStatus(orgId: string, invoiceId: string) {
  return useQuery<InvoiceNowStatusResponse>({
    queryKey: [orgId, "invoices", invoiceId, "invoicenow-status"],
    queryFn: async () => {
      const response = await api.get<InvoiceNowStatusResponse>(
        endpoints.invoices(orgId).invoiceNowStatus(invoiceId)
      );
      return response;
    },
    enabled: !!orgId && !!invoiceId,
    refetchInterval: (query) => {
      const data = query.state.data;
      // Poll every 5 seconds if pending
      if (data?.status === "PENDING" || data?.status === "TRANSMITTING") {
        return 5000;
      }
      return false;
    },
  });
}

// Download PDF
export function useInvoicePDF(orgId: string, invoiceId: string) {
  return useMutation({
    mutationFn: async () => {
      // Authorized through the api-client (in-memory token + 401 refresh)
      // — never localStorage: the zero-JWT-exposure mandate forbids
      // client-side token storage, and the token never lived there anyway
      // (P3/D-2 fixed the old `localStorage.getItem("accessToken")` path
      // that sent `Bearer null` on every download).
      const blob = await api.blob(endpoints.invoices(orgId).pdf(invoiceId));

      const downloadUrl = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = downloadUrl;
      a.download = `invoice-${invoiceId}.pdf`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      window.URL.revokeObjectURL(downloadUrl);
    },
  });
}
