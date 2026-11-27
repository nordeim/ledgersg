import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api, endpoints } from "@/lib/api-client";

// Types matching backend schema
export interface Contact {
  id: string;
  org_id: string;
  contact_type: "CUSTOMER" | "SUPPLIER" | "BOTH";
  name: string;
  legal_name?: string;
  email?: string;
  phone?: string;
  address_line_1?: string;
  address_line_2?: string;
  postal_code?: string;
  country: string;
  uen?: string;
  gst_reg_number?: string;
  peppol_id?: string;
  is_peppol_enabled: boolean;
  payment_terms_days: number;
  currency: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

interface ContactInput {
  contact_type: "CUSTOMER" | "SUPPLIER" | "BOTH";
  name: string;
  legal_name?: string;
  email?: string;
  phone?: string;
  address_line_1?: string;
  address_line_2?: string;
  postal_code?: string;
  country?: string;
  uen?: string;
  gst_reg_number?: string;
  peppol_id?: string;
  is_peppol_enabled?: boolean;
  payment_terms_days?: number;
  currency?: string;
}

/** The list envelope (P26: the hook returns the FULL envelope — the
 * pre-P26 hook unwrapped `results` and threw the count away, so no
 * consumer could render a truthful total or paginate). */
export interface ContactListResponse {
  results: Contact[];
  count: number;
  next?: string | null;
  previous?: string | null;
}

/** P26: the page request (limit/offset over the P24 backend contract). */
export interface ContactPage {
  limit: number;
  offset: number;
}

// List contacts with optional filters.
// P9/K-5: the filter keys are the backend's actual query params
// (invoicing ContactListView reads is_customer / is_supplier / is_active /
// search). The old `contact_type` key was silently ignored.
// P26: the optional `page` paginates server-side (the picker keeps the
// unpaginated shape — its search-bounded fetch needs no page).
export function useContacts(
  orgId: string,
  filters?: {
    is_customer?: boolean;
    is_supplier?: boolean;
    is_active?: boolean;
    search?: string;
  },
  page?: ContactPage
) {
  const params = new URLSearchParams(
    Object.entries(filters ?? {})
      .filter(([, v]) => v !== undefined)
      .map(([k, v]) => [k, String(v)]) as [string, string][]
  );
  if (page) {
    params.set("limit", String(page.limit));
    params.set("offset", String(page.offset));
  }
  const queryString = params.toString() ? `?${params.toString()}` : "";

  return useQuery({
    // P26: the page identity MUST live in the key (the P24/FE-L1
    // cache-paging trap) — pages are distinct cache entries.
    queryKey: [orgId, "contacts", filters ?? null, page ?? null],
    queryFn: async () => {
      const response = await api.get<ContactListResponse>(
        endpoints.contacts(orgId).list + queryString
      );
      return response;
    },
    enabled: !!orgId,
  });
}

// Get single contact detail
export function useContact(orgId: string, contactId: string) {
  return useQuery({
    queryKey: [orgId, "contacts", contactId],
    queryFn: async () => {
      const response = await api.get<Contact>(
        endpoints.contacts(orgId).detail(contactId)
      );
      return response;
    },
    enabled: !!orgId && !!contactId,
  });
}

// Create contact
export function useCreateContact(orgId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (data: ContactInput) => {
      const response = await api.post<Contact>(
        endpoints.contacts(orgId).list,
        data
      );
      return response;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [orgId, "contacts"] });
    },
  });
}

// Update contact
export function useUpdateContact(orgId: string, contactId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (data: Partial<ContactInput>) => {
      const response = await api.patch<Contact>(
        endpoints.contacts(orgId).detail(contactId),
        data
      );
      return response;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [orgId, "contacts", contactId] });
      queryClient.invalidateQueries({ queryKey: [orgId, "contacts"] });
    },
  });
}

// Deactivate contact
export function useDeactivateContact(orgId: string, contactId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async () => {
      const response = await api.delete<Contact>(
        endpoints.contacts(orgId).detail(contactId)
      );
      return response;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [orgId, "contacts"] });
    },
  });
}
