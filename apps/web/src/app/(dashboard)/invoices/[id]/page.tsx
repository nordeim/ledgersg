import { InvoiceDetailClient } from "./invoice-detail-client";

/**
 * P6/D-1: route params are a Promise in this Next.js version — the page
 * must await them. The mock-era generateStaticParams (demo invoice IDs)
 * is gone: the page is client-driven against the real detail endpoint.
 */
export default async function InvoiceDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  return <InvoiceDetailClient id={id} />;
}
