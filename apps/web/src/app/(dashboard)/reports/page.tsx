import { Metadata } from "next";
import { ReportsClient } from "./reports-client";

export const metadata: Metadata = {
  title: "Reports — LedgerSG",
  description: "Financial statements, GST F5 returns and aged receivables/payables",
};

export default function ReportsPage() {
  return <ReportsClient />;
}
