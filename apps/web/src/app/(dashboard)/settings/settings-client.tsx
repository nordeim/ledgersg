"use client";

import * as React from "react";
import { useState } from "react";
import { AlertTriangle, Building, Loader2, User } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { useAuth } from "@/providers/auth-provider";
import { optionalUenSchema } from "@/shared/schemas/uen";
import { FiscalCard } from "./components/fiscal-card";
import { ChangePasswordCard } from "./components/change-password-card";
import { InvoiceNowSettingsCard } from "./components/invoicenow-settings-card";
import {
  useOrganisation,
  useUpdateOrganisation,
  useGstRegistration,
  useGstDeregistration,
  type OrganisationUpdate,
} from "@/hooks/use-organisation";

/**
 * Real organisation settings (P6/C-5 — replaced the hardcoded
 * defaultValue cards). Controlled inputs over the real organisation;
 * saves through the PATCH allowlist; GST registration state is driven by
 * the dedicated endpoints (which also seed the GST control accounts).
 */

export function SettingsClient() {
  const { currentOrg, user, isLoading: authLoading } = useAuth();
  const orgId = currentOrg?.id ?? null;

  const { data: org, isLoading, isError } = useOrganisation(orgId);
  const updateOrganisation = useUpdateOrganisation(orgId as string);
  const registerGst = useGstRegistration(orgId as string);
  const deregisterGst = useGstDeregistration(orgId as string);

  const [form, setForm] = useState<OrganisationUpdate>({});
  // P19/FE-L8: the org UEN edit's client-side validation error (declared
  // with the other hooks — the first cut landed below an early return and
  // tripped rules-of-hooks).
  const [uenError, setUenError] = useState<string | null>(null);
  const [gstNumber, setGstNumber] = useState("");
  const [gstDate, setGstDate] = useState("");

  // P8/S-2: local edits survive background refetches — the reset fires
  // only when the user's own save lands (onSuccess below). The old
  // updated_at-keyed effect wiped in-flight edits whenever GST
  // register/deregister invalidated the org query.
  const handleSaveSuccess = () => {
    setForm({});
  };

  React.useEffect(() => {
    setGstNumber(org?.gst_reg_number ?? "");
    setGstDate(org?.gst_reg_date ?? "");
  }, [org?.gst_reg_number, org?.gst_reg_date]);

  // P7/F-12: an authenticated user with no organisation is not a load
  // failure — a disabled query reports isLoading=false and the old
  // `isError || !org` branch rendered "Failed to load settings" for a
  // legitimately org-less user.
  if (authLoading) {
    return (
      <div role="status" aria-live="polite" className="flex items-center justify-center gap-2 py-24 text-text-secondary">
        <Loader2 className="h-5 w-5 animate-spin" aria-hidden />
        <span>Loading settings…</span>
      </div>
    );
  }

  if (!currentOrg) {
    return (
      <Card className="border-border bg-carbon">
        <CardContent className="flex flex-col items-center gap-3 py-16">
          <Building className="h-8 w-8 text-accent-secondary" />
          <p className="font-medium text-text-primary">No organisation selected</p>
          <p className="text-sm text-text-secondary">
            Create or select an organisation to manage its settings.
          </p>
        </CardContent>
      </Card>
    );
  }

  if (isLoading) {
    return (
      <div role="status" aria-live="polite" className="flex items-center justify-center gap-2 py-24 text-text-secondary">
        <Loader2 className="h-5 w-5 animate-spin" aria-hidden />
        <span>Loading settings…</span>
      </div>
    );
  }

  if (isError || !org) {
    return (
      <Card className="border-border bg-carbon">
        <CardContent className="flex flex-col items-center gap-3 py-16">
          <AlertTriangle className="h-8 w-8 text-alert" />
          <p className="font-medium text-text-primary">
            Failed to load settings
          </p>
          <p className="text-sm text-text-secondary">
            The organisation details could not be loaded from the server.
          </p>
        </CardContent>
      </Card>
    );
  }

  const value = (key: keyof OrganisationUpdate): string =>
    (form[key] ?? (org as unknown as Record<string, unknown>)[key] ?? "") as string;

  const setValue = (key: keyof OrganisationUpdate, v: string) =>
    setForm((prev) => ({ ...prev, [key]: v }));

  const handleSave = () => {
    if (Object.keys(form).length === 0) return;
    // P19/FE-L8: the org UEN edit validates with the shared ACRA schema
    // (the create path validates via uenSchema.safeParse).
    if (!optionalUenSchema.safeParse(value("uen")).success) {
      setUenError("UEN format is invalid.");
      return;
    }
    setUenError(null);
    updateOrganisation.mutate(form, { onSuccess: handleSaveSuccess });
  };

  const handleRegister = () => {
    if (!gstNumber || !gstDate) return;
    registerGst.mutate({ gst_reg_number: gstNumber, gst_reg_date: gstDate });
  };

  return (
    <div className="space-y-6">
      {/* Organisation Settings */}
      <Card className="border-border bg-carbon rounded-sm">
        <CardHeader>
          <div className="flex items-center gap-2">
            <Building className="h-5 w-5 text-accent-primary" />
            <CardTitle className="font-display text-lg text-text-primary">
              Organisation
            </CardTitle>
          </div>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid gap-4 md:grid-cols-2">
            <Input
              label="Company Name"
              value={value("name")}
              onChange={(e) => setValue("name", e.target.value)}
            />
            <Input
              label="Legal Name"
              value={value("legal_name")}
              onChange={(e) => setValue("legal_name", e.target.value)}
            />
            <Input
              label="UEN"
              value={value("uen")}
              onChange={(e) => setValue("uen", e.target.value)}
              error={uenError ?? undefined}
            />
            {/* P11/M-5: the DB column is CHAR(3) — free text sent 4+
            chars into a DataError 500; the backend now 400s, and the input
            tells the truth up front. */}
            <Input
              label="Base Currency"
              maxLength={3}
              value={value("base_currency")}
              onChange={(e) => setValue("base_currency", e.target.value.toUpperCase())}
            />
            <Input
              label="Address Line 1"
              value={value("address_line_1")}
              onChange={(e) => setValue("address_line_1", e.target.value)}
            />
            <Input
              label="Address Line 2"
              value={value("address_line_2")}
              onChange={(e) => setValue("address_line_2", e.target.value)}
            />
            <Input
              label="City"
              value={value("city")}
              onChange={(e) => setValue("city", e.target.value)}
            />
            <Input
              label="Postal Code"
              value={value("postal_code")}
              onChange={(e) => setValue("postal_code", e.target.value)}
            />
            <Input
              label="Contact Email"
              value={value("contact_email")}
              onChange={(e) => setValue("contact_email", e.target.value)}
            />
            <Input
              label="Contact Phone"
              value={value("contact_phone")}
              onChange={(e) => setValue("contact_phone", e.target.value)}
            />
          </div>
          <Button
            onClick={handleSave}
            disabled={
              updateOrganisation.isPending || Object.keys(form).length === 0
            }
            className="rounded-sm bg-accent-primary text-void hover:bg-accent-primary-dim"
          >
            {updateOrganisation.isPending && (
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
            )}
            Save Changes
          </Button>
        </CardContent>
      </Card>

      {/* GST Registration */}
      <Card className="border-border bg-carbon rounded-sm">
        <CardHeader>
          <div className="flex items-center gap-2">
            <Building className="h-5 w-5 text-accent-primary" />
            <CardTitle className="font-display text-lg text-text-primary">
              GST Registration
            </CardTitle>
            {org.gst_registered ? (
              <Badge className="bg-success text-void">Registered</Badge>
            ) : (
              <Badge className="bg-surface text-text-secondary border border-border">
                Not Registered
              </Badge>
            )}
          </div>
        </CardHeader>
        <CardContent className="space-y-4">
          {org.gst_registered ? (
            <>
              <div className="grid gap-4 md:grid-cols-2">
                <Input
                  label="GST Registration No"
                  value={gstNumber}
                  onChange={(e) => setGstNumber(e.target.value)}
                  disabled
                />
                <Input
                  label="Registration Date"
                  value={gstDate}
                  onChange={(e) => setGstDate(e.target.value)}
                  disabled
                />
              </div>
              <Button
                variant="outline"
                onClick={() => deregisterGst.mutate()}
                disabled={deregisterGst.isPending}
                className="rounded-sm border-border text-alert hover:text-alert hover:bg-alert/10"
              >
                {deregisterGst.isPending && (
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                )}
                Deregister from GST
              </Button>
            </>
          ) : (
            <>
              <p className="text-sm text-text-secondary">
                Register the organisation for GST. This seeds the GST input
                and output control accounts in your chart of accounts.
              </p>
              <div className="grid gap-4 md:grid-cols-2">
                <Input
                  label="GST Registration No"
                  placeholder="M90345678"
                  value={gstNumber}
                  onChange={(e) => setGstNumber(e.target.value)}
                />
                <Input
                  label="Registration Date"
                  type="date"
                  value={gstDate}
                  onChange={(e) => setGstDate(e.target.value)}
                />
              </div>
              <Button
                onClick={handleRegister}
                disabled={
                  registerGst.isPending || !gstNumber || !gstDate
                }
                className="rounded-sm bg-accent-primary text-void hover:bg-accent-primary-dim"
              >
                {registerGst.isPending && (
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                )}
                Register for GST
              </Button>
            </>
          )}
        </CardContent>
      </Card>

      {/* P10/M-10: InvoiceNow / Peppol — the surface the invoice
          detail's "Configure an access point (Peppol settings)" 400
          names (its first consumer). */}
      <InvoiceNowSettingsCard orgId={currentOrg.id} />

      {/* P10/M-8: fiscal years & periods — the control surface the
          invoice-approval error points at. */}
      <FiscalCard orgId={currentOrg.id} />

      {/* User Profile (read-only view of the signed-in user) */}
      <Card className="border-border bg-carbon rounded-sm">
        <CardHeader>
          <div className="flex items-center gap-2">
            <User className="h-5 w-5 text-accent-primary" />
            <CardTitle className="font-display text-lg text-text-primary">
              User Profile
            </CardTitle>
          </div>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid gap-4 md:grid-cols-2">
            <Input label="Full Name" value={user?.full_name ?? ""} disabled />
            <Input label="Email" value={user?.email ?? ""} disabled />
          </div>
          {/* P10/M-9: the "Profile editing is handled by your account
              settings" line was a lie — no such surface existed. The
              real change-password affordance is the card below. */}
        </CardContent>
      </Card>

      {/* P10/M-9: change password — the backend endpoint is real (revokes
          every session); this is its first consumer. */}
      <ChangePasswordCard />
    </div>
  );
}
