import { EditInvoiceClient } from "./edit-invoice-client";

// Generate static params for demo invoices
export function generateStaticParams() {
  return [
    { id: "INV-2024-0001" },
    { id: "INV-2024-0002" },
    { id: "INV-2024-0003" },
  ];
}

export default function EditInvoicePage({ params }: { params: { id: string } }) {
  return <EditInvoiceClient id={params.id} />;
}
