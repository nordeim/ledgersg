import type { Metadata } from "next";
import { SettingsClient } from "./settings-client";

export const metadata: Metadata = {
  title: "Settings — LedgerSG",
  description: "Manage your account and organization settings",
};

export default function SettingsPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="font-display text-2xl font-bold text-text-primary">
          Settings
        </h1>
        <p className="text-sm text-text-secondary mt-1">
          Manage your account and organization
        </p>
      </div>
      <SettingsClient />
    </div>
  );
}
