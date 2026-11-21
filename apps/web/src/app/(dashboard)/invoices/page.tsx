import { Metadata } from "next";
import { InvoicesClient } from "./invoices-client";

export const metadata: Metadata = {
  title: "Invoices — LedgerSG",
  description: "Manage your invoices and quotes",
};

export default function InvoicesPage() {
  return <InvoicesClient />;
}
