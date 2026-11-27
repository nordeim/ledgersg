"use client";

import { useState } from "react";
import { Loader2, Send } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { useAuth } from "@/providers/auth-provider";
import {
  usePeppolSettings,
  useUpdatePeppolSettings,
  type PeppolSettings,
} from "@/hooks/use-peppol";

/**
 * P10/M-10: the InvoiceNow / Peppol settings card — the GET/PATCH
 * endpoint's first consumer. "Send via InvoiceNow" 400s with "Configure
 * an access point (Peppol settings)…" — that named surface now exists.
 * PATCH is manager-gated server-side; non-managers see a read-only view.
 */

export function InvoiceNowSettingsCard({ orgId }: { orgId: string }) {
  const { data: settings, isLoading } = usePeppolSettings(orgId);

  if (isLoading) {
    return (
      <Card className="border-border bg-carbon rounded-sm">
        <CardContent className="py-10">
          <div
            data-testid="invoicenow-card-loading"
            className="flex items-center justify-center gap-2 text-sm text-text-secondary"
          >
            <Loader2 className="h-4 w-4 animate-spin" aria-hidden />
            Loading InvoiceNow settings…
          </div>
        </CardContent>
      </Card>
    );
  }

  if (!settings) {
    return (
      <Card className="border-border bg-carbon rounded-sm">
        <CardContent className="py-6 text-sm text-text-secondary">
          InvoiceNow settings could not be loaded. Please refresh the page.
        </CardContent>
      </Card>
    );
  }

  // The inner form mounts once per payload (keyed) — its useState
  // initialiser prefills from GET, no effect-state round trip.
  return (
    <InvoiceNowForm
      key={`${settings.participant_id}|${settings.retry_attempts}|${settings.status}`}
      orgId={orgId}
      settings={settings}
    />
  );
}

function InvoiceNowForm({
  orgId,
  settings,
}: {
  orgId: string;
  settings: PeppolSettings;
}) {
  const { hasPermission } = useAuth();
  const canManage = hasPermission("can_manage_org");
  const update = useUpdatePeppolSettings(orgId);

  const [form, setForm] = useState({
    enabled: settings.enabled,
    participant_id: settings.participant_id ?? "",
    access_point_provider: settings.access_point_provider ?? "",
    auto_transmit: settings.auto_transmit,
    retry_attempts: String(settings.retry_attempts),
  });

  const retryValue = Number.parseInt(form.retry_attempts, 10);
  const retryInvalid =
    Number.isNaN(retryValue) || retryValue < 0 || retryValue > 10;

  const handleSave = () => {
    if (retryInvalid) return;
    update.mutate({
      enabled: form.enabled,
      participant_id: form.participant_id,
      access_point_provider: form.access_point_provider,
      auto_transmit: form.auto_transmit,
      retry_attempts: retryValue,
    });
  };

  return (
    <Card className="border-border bg-carbon rounded-sm">
      <CardHeader>
        <div className="flex items-center gap-2">
          <Send className="h-5 w-5 text-accent-primary" aria-hidden />
          <CardTitle className="font-display text-lg text-text-primary">
            InvoiceNow / Peppol
          </CardTitle>
          {settings.is_configured ? (
            <Badge className="bg-success text-void rounded-sm">Configured</Badge>
          ) : (
            <Badge variant="outline" className="rounded-sm text-text-muted">
              Not configured
            </Badge>
          )}
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        <p className="text-sm text-text-secondary">
          InvoiceNow sends invoices over the Peppol network. Enable it,
          set your participant ID, and configure the access point the
          transmissions run through.
        </p>

        <div className="space-y-3">
          <label
            htmlFor="peppol-enabled"
            className="flex items-center gap-3 text-sm text-text-primary cursor-pointer"
          >
            <input
              id="peppol-enabled"
              type="checkbox"
              checked={form.enabled}
              onChange={(e) =>
                setForm((f) => ({ ...f, enabled: e.target.checked }))
              }
              disabled={!canManage || update.isPending}
              className="h-4 w-4 rounded-sm"
            />
            Enable InvoiceNow
          </label>

          <div className="grid gap-4 md:grid-cols-2">
            <Input
              label="Peppol participant ID"
              placeholder="0209-201912345A-1234"
              value={form.participant_id}
              onChange={(e) =>
                setForm((f) => ({ ...f, participant_id: e.target.value }))
              }
              disabled={!canManage || update.isPending}
            />
            <Input
              label="Access point provider"
              placeholder="Storecove"
              value={form.access_point_provider}
              onChange={(e) =>
                setForm((f) => ({ ...f, access_point_provider: e.target.value }))
              }
              disabled={!canManage || update.isPending}
            />
            <Input
              label="Retry attempts"
              type="number"
              min={0}
              max={10}
              value={form.retry_attempts}
              onChange={(e) =>
                setForm((f) => ({ ...f, retry_attempts: e.target.value }))
              }
              disabled={!canManage || update.isPending}
            />
          </div>

          <label
            htmlFor="peppol-auto-transmit"
            className="flex items-center gap-3 text-sm text-text-primary cursor-pointer"
          >
            <input
              id="peppol-auto-transmit"
              type="checkbox"
              checked={form.auto_transmit}
              onChange={(e) =>
                setForm((f) => ({ ...f, auto_transmit: e.target.checked }))
              }
              disabled={!canManage || update.isPending}
              className="h-4 w-4 rounded-sm"
            />
            Auto-transmit approved invoices
          </label>
        </div>

        {retryInvalid && (
          <p className="text-sm text-alert" role="alert">
            Retry attempts must be a whole number between 0 and 10.
          </p>
        )}

        {canManage && (
          <Button
            type="button"
            onClick={handleSave}
            disabled={update.isPending || retryInvalid}
            className="rounded-sm bg-accent-primary text-void hover:bg-accent-primary-dim"
          >
            {update.isPending && (
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
            )}
            Save InvoiceNow settings
          </Button>
        )}
      </CardContent>
    </Card>
  );
}
