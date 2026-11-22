import { InvoiceDetailClient } from "@/app/(dashboard)/invoices/[id]/invoice-detail-client";

/**
 * Quote detail (P8/Q-4) — the shared document detail client in quote
 * mode: QUOTATION framing, no payment state / approval / InvoiceNow, a
 * Convert-to-invoice action on DRAFT/SENT quotes.
 */
export default async function QuoteDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  return <InvoiceDetailClient id={id} variant="quote" />;
}
