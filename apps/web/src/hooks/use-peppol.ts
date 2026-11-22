"use client";

/**
 * Peppol / InvoiceNow hooks (P10/M-10).
 *
 * GET/PATCH /peppol/settings/ is backend-real (member-readable GET;
 * manager-gated typed PATCH — PeppolSettingsSerializer) with zero
 * frontend consumers: the "Send via InvoiceNow" 400 ("Configure an
 * access point (Peppol settings)…") pointed at a surface that did not
 * exist.
 */

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api, endpoints } from "@/lib/api-client";
import { toast } from "@/hooks/use-toast";

/** PeppolSettingsView's GET payload. */
export interface PeppolSettings {
  enabled: boolean;
  participant_id: string;
  is_configured: boolean;
  access_point_provider: string | null;
  auto_transmit: boolean;
  retry_attempts: number;
  status: "configured" | "not_configured";
}

/** The typed PATCH payload (PeppolSettingsSerializer). */
export interface PeppolSettingsUpdate {
  enabled?: boolean;
  participant_id?: string;
  auto_transmit?: boolean;
  access_point_provider?: string;
  retry_attempts?: number;
}

export function usePeppolSettings(orgId: string | null) {
  return useQuery({
    queryKey: [orgId, "peppol-settings"],
    queryFn: async () => {
      return api.get<PeppolSettings>(endpoints.peppol(orgId!).settings);
    },
    enabled: !!orgId,
  });
}

export function useUpdatePeppolSettings(orgId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (data: PeppolSettingsUpdate) => {
      const response = await api.patch<PeppolSettings>(
        endpoints.peppol(orgId).settings,
        data
      );
      return response;
    },
    onSuccess: () => {
      toast({
        title: "InvoiceNow settings saved",
        variant: "success",
      });
      queryClient.invalidateQueries({ queryKey: [orgId, "peppol-settings"] });
      // enabled/participant_id live on the organisation — keep the org
      // query honest too.
      queryClient.invalidateQueries({ queryKey: [orgId, "organisation"] });
    },
    onError: (error: Error) => {
      toast({
        title: "Failed to save InvoiceNow settings",
        description: error.message || "An error occurred while saving.",
        variant: "error",
      });
    },
  });
}
