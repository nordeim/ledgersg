import { useQuery } from "@tanstack/react-query";
import { api, endpoints } from "@/lib/api-client";
import type { DashboardMetrics } from "@/shared/schemas/dashboard";

// Dashboard metrics
export function useDashboardMetrics(orgId: string) {
  return useQuery({
    queryKey: [orgId, "dashboard", "metrics"],
    queryFn: async () => {
      const response = await api.get<DashboardMetrics>(
        endpoints.dashboard(orgId).metrics
      );
      return response;
    },
    enabled: !!orgId,
    // Refresh every 5 minutes
    refetchInterval: 5 * 60 * 1000,
    // Stale after 1 minute
    staleTime: 60 * 1000,
  });
}

// Compliance alerts
export function useComplianceAlerts(orgId: string) {
  return useQuery({
    queryKey: [orgId, "dashboard", "alerts"],
    queryFn: async () => {
      const response = await api.get<{
        results: Array<{
          id: string;
          severity: "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";
          title: string;
          message: string;
          action_required: string;
          deadline?: string;
          dismissed: boolean;
        }>;
      }>(endpoints.dashboard(orgId).alerts);
      return response.results;
    },
    enabled: !!orgId,
    refetchInterval: 60 * 1000, // Refresh every minute
  });
}
