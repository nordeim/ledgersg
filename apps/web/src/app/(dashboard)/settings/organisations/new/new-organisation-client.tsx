"use client";

import { useState } from "react";

import { uenSchema } from "@/shared/schemas/uen";
import { ArrowLeft, Building, Loader2 } from "lucide-react";
import Link from "next/link";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  useCreateOrganisation,
  type OrganisationCreateInput,
} from "@/hooks/use-organisation";

/**
 * P9/O-1: the organisation-creation form — the route the dashboard's
 * "Create Organisation" CTA has pointed at all along. Registration creates
 * a user with no organisation; this page is where the product becomes
 * usable for a self-serve user (backend: OrganisationListCreateView, which
 * also seeds the chart of accounts, first fiscal year, roles, and tax
 * codes).
 */

const ENTITY_TYPES = [
  { value: "PRIVATE_LIMITED", label: "Private Limited (Pte Ltd)" },
  { value: "SOLE_PROPRIETORSHIP", label: "Sole Proprietorship" },
  { value: "PARTNERSHIP", label: "Partnership" },
  { value: "LIMITED_LIABILITY_PARTNERSHIP", label: "Limited Liability Partnership (LLP)" },
  { value: "PUBLIC_LIMITED", label: "Public Limited" },
  { value: "NON_PROFIT", label: "Non-Profit" },
  { value: "OTHER", label: "Other" },
] as const;

interface FormState {
  name: string;
  legal_name: string;
  uen: string;
  entity_type: string;
  gst_registered: boolean;
  gst_reg_number: string;
}

const INITIAL: FormState = {
  name: "",
  legal_name: "",
  uen: "",
  entity_type: "PRIVATE_LIMITED",
  gst_registered: false,
  gst_reg_number: "",
};

export function NewOrganisationClient() {
  const [form, setForm] = useState<FormState>(INITIAL);
  const [errors, setErrors] = useState<Record<string, string>>({});
  const createOrganisation = useCreateOrganisation();

  const set = <K extends keyof FormState>(key: K, value: FormState[K]) => {
    setForm((prev) => ({ ...prev, [key]: value }));
    setErrors((prev) => {
      if (!prev[key]) return prev;
      const next = { ...prev };
      delete next[key];
      return next;
    });
  };

  const validate = (): boolean => {
    const next: Record<string, string> = {};
    if (!form.name.trim()) next.name = "The organisation name is required.";
    // P17/FE-L6 + P18/FE-M4: client-side ACRA validation THROUGH the
    // shared schema (one source — the message lives in uen.ts, not
    // duplicated here; the schema normalizes trim/uppercase exactly
    // like the backend's normalize-then-validate). Empty stays valid
    // (UEN is optional at creation, as the backend's validate() allows).
    const uenResult = form.uen.trim()
      ? uenSchema.safeParse(form.uen)
      : { success: true as const };
    if (!uenResult.success) {
      next.uen = uenResult.error.issues[0]?.message ?? "The UEN is not a valid ACRA format.";
    }
    if (form.gst_registered && !form.gst_reg_number.trim()) {
      next.gst_reg_number = "A GST registration number is required when GST-registered is on.";
    }
    setErrors(next);
    return Object.keys(next).length === 0;
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!validate()) return;

    const payload: OrganisationCreateInput = {
      name: form.name.trim(),
      legal_name: form.legal_name.trim() || form.name.trim(),
      uen: form.uen.trim(),
      entity_type: form.entity_type,
      gst_registered: form.gst_registered,
      gst_reg_number: form.gst_registered ? form.gst_reg_number.trim() : "",
      base_currency: "SGD",
      fy_start_month: 1,
    };
    createOrganisation.mutate(payload);
  };

  return (
    <div className="max-w-2xl mx-auto space-y-6">
      <div className="flex items-center gap-3">
        <Link
          href="/dashboard"
          className="inline-flex items-center gap-2 text-sm text-text-secondary hover:text-text-primary transition-colors"
        >
          <ArrowLeft className="h-4 w-4" aria-hidden />
          Back to dashboard
        </Link>
      </div>

      <Card className="border-border bg-carbon rounded-sm">
        <CardHeader>
          <CardTitle className="font-display text-2xl text-text-primary flex items-center gap-3">
            <Building className="h-6 w-6 text-accent-primary" aria-hidden />
            Create Organisation
          </CardTitle>
          <p className="text-sm text-text-secondary">
            Your chart of accounts, first fiscal year, and tax codes are set up
            automatically.
          </p>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-5" noValidate>
            <div className="space-y-2">
              <label htmlFor="org-name" className="text-sm text-text-secondary">
                Organisation name <span className="text-alert">*</span>
              </label>
              <Input
                id="org-name"
                value={form.name}
                onChange={(e) => set("name", e.target.value)}
                placeholder="Mama Shop Pte Ltd"
                className="rounded-sm"
                aria-required="true"
              />
              {errors.name && <p className="text-sm text-alert">{errors.name}</p>}
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div className="space-y-2">
                <label htmlFor="org-legal-name" className="text-sm text-text-secondary">
                  Legal name
                </label>
                <Input
                  id="org-legal-name"
                  value={form.legal_name}
                  onChange={(e) => set("legal_name", e.target.value)}
                  placeholder="Defaults to the organisation name"
                  className="rounded-sm"
                />
              </div>
              <div className="space-y-2">
                <label htmlFor="org-uen" className="text-sm text-text-secondary">
                  UEN
                </label>
                <Input
                  id="org-uen"
                  value={form.uen}
                  onChange={(e) => set("uen", e.target.value)}
                  placeholder="53312345A"
                  aria-invalid={Boolean(errors.uen)}
                  className="rounded-sm"
                />
                {errors.uen && (
                  <p className="text-sm text-alert" role="alert">
                    {errors.uen}
                  </p>
                )}
              </div>
            </div>

            <div className="space-y-2">
              <label htmlFor="org-entity-type" className="text-sm text-text-secondary">
                Entity type
              </label>
              <Select
                value={form.entity_type}
                onValueChange={(value) => set("entity_type", value)}
              >
                <SelectTrigger id="org-entity-type" className="rounded-sm">
                  <SelectValue placeholder="Select an entity type" />
                </SelectTrigger>
                <SelectContent>
                  {ENTITY_TYPES.map((type) => (
                    <SelectItem key={type.value} value={type.value}>
                      {type.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="border-t border-border pt-5 space-y-4">
              <label
                htmlFor="org-gst"
                className="flex items-center gap-3 text-sm text-text-primary cursor-pointer"
              >
                <input
                  id="org-gst"
                  type="checkbox"
                  checked={form.gst_registered}
                  onChange={(e) => set("gst_registered", e.target.checked)}
                  className="h-4 w-4 rounded-sm accent-primary"
                />
                <span className="label-text">
                  GST-registered
                  <span className="block text-xs text-text-secondary">
                    Turns on GST control accounts and F5 filing.
                  </span>
                </span>
              </label>

              {form.gst_registered && (
                <div className="space-y-2">
                  <label htmlFor="org-gst-number" className="text-sm text-text-secondary">
                    GST registration number <span className="text-alert">*</span>
                  </label>
                  <Input
                    id="org-gst-number"
                    value={form.gst_reg_number}
                    onChange={(e) => set("gst_reg_number", e.target.value)}
                    placeholder="M12345678"
                    className="rounded-sm"
                    aria-required="true"
                  />
                  {errors.gst_reg_number && (
                    <p className="text-sm text-alert">{errors.gst_reg_number}</p>
                  )}
                </div>
              )}
            </div>

            <div className="flex items-center justify-end gap-3 pt-2 border-t border-border">
              <Button
                type="submit"
                className="rounded-sm bg-accent-primary text-void hover:bg-accent-primary-dim font-medium"
                disabled={createOrganisation.isPending}
              >
                {createOrganisation.isPending ? (
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" aria-hidden />
                ) : (
                  <Building className="h-4 w-4 mr-2" aria-hidden />
                )}
                {createOrganisation.isPending ? "Creating…" : "Create Organisation"}
              </Button>
            </div>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
