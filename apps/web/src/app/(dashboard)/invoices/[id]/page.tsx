import { InvoiceDetailClient } from "./invoice-detail-client";

// Generate static params for demo invoices
export function generateStaticParams() {
  return [
    { id: "INV-2024-0001" },
    { id: "INV-2024-0002" },
    { id: "INV-2024-0003" },
  ];
}

export default function InvoiceDetailPage({ params }: { params: { id: string } }) {
  return <InvoiceDetailClient id={params.id} />;
}
