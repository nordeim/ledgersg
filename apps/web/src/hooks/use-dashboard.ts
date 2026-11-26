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
