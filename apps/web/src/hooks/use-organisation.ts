/**
 * Organisation Hooks - LedgerSG Frontend
 *
 * P6/C-5: the settings page contract — organisation detail, allowlisted
 * updates, and GST registration/deregistration.
 */

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api, endpoints } from "@/lib/api-client";
import { toast } from "@/hooks/use-toast";

/** The backend OrganisationSerializer contract. */
export interface OrganisationDetail {
  id: string;
  name: string;
  legal_name: string;
  uen: string;
  entity_type: string;
  gst_registered: boolean;
  gst_reg_number: string;
  gst_reg_date: string | null;
  peppol_participant_id: string;
  invoicenow_enabled: boolean;
  fy_start_month: number;
  base_currency: string;
  is_active: boolean;
  address_line_1: string;
  address_line_2: string;
  city: string;
  postal_code: string;
  country: string;
  contact_email: string;
  contact_phone: string;
  created_at: string;
  updated_at: string;
}

export type OrganisationUpdate = Partial<
  Pick<
    OrganisationDetail,
    | "name"
    | "legal_name"
    | "uen"
    | "entity_type"
    | "address_line_1"
    | "address_line_2"
    | "city"
    | "postal_code"
    | "country"
    | "contact_email"
    | "contact_phone"
    | "base_currency"
    | "peppol_participant_id"
    | "invoicenow_enabled"
  >
>;

export interface GstRegistrationInput {
  gst_reg_number: string;
  gst_reg_date: string;
}

export function useOrganisation(orgId: string | null | undefined) {
  return useQuery({
    queryKey: [orgId, "organisation"],
    queryFn: async () => {
      const response = await api.get<OrganisationDetail>(
        endpoints.organisations.detail(orgId as string)
      );
      return response;
    },
    enabled: !!orgId,
  });
}

export function useUpdateOrganisation(orgId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (updates: OrganisationUpdate) => {
      const response = await api.patch<OrganisationDetail>(
        endpoints.organisations.detail(orgId),
        updates
      );
      return response;
    },
    onSuccess: () => {
      toast({
        title: "Settings saved",
        description: "Organisation details have been updated.",
        variant: "success",
      });
      queryClient.invalidateQueries({ queryKey: [orgId, "organisation"] });
    },
    onError: (error: Error) => {
      toast({
        title: "Failed to save settings",
        description: error.message || "An error occurred while saving.",
        variant: "error",
      });
    },
  });
}

export function useGstRegistration(orgId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (data: GstRegistrationInput) => {
      const response = await api.post<OrganisationDetail>(
        endpoints.organisations.gst(orgId),
        data
      );
      return response;
    },
    onSuccess: () => {
      toast({
        title: "GST registration saved",
        description:
          "The organisation is now GST-registered and the GST control accounts are seeded.",
        variant: "success",
      });
      queryClient.invalidateQueries({ queryKey: [orgId, "organisation"] });
    },
    onError: (error: Error) => {
      toast({
        title: "Failed to register for GST",
        description: error.message || "An error occurred while registering.",
        variant: "error",
      });
    },
  });
}

export function useGstDeregistration(orgId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async () => {
      const response = await api.delete<OrganisationDetail>(
        endpoints.organisations.gst(orgId)
      );
      return response;
    },
    onSuccess: () => {
      toast({
        title: "GST deregistered",
        description: "The organisation is no longer GST-registered.",
        variant: "warning",
      });
      queryClient.invalidateQueries({ queryKey: [orgId, "organisation"] });
    },
    onError: (error: Error) => {
      toast({
        title: "Failed to deregister",
        description: error.message || "An error occurred while deregistering.",
        variant: "error",
      });
    },
  });
}
