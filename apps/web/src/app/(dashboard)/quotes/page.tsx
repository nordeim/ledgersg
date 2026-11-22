import { Metadata } from "next";
import { QuotesClient } from "./quotes-client";

export const metadata: Metadata = {
  title: "Quotes — LedgerSG",
  description: "Create and manage customer quotations",
};

export default function QuotesPage() {
  return <QuotesClient />;
}
