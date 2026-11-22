import type { Metadata } from "next";
import ContactsClient from "./contacts-client";

export const metadata: Metadata = {
  title: "Contacts — LedgerSG",
  description: "Manage your customers and suppliers",
};

export default function ContactsPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="font-display text-2xl font-bold text-text-primary">
          Contacts
        </h1>
        <p className="text-sm text-text-secondary mt-1">
          Manage your customers and suppliers — names, UENs and Peppol IDs
        </p>
      </div>
      <ContactsClient />
    </div>
  );
}
