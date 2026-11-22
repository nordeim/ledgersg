import { DashboardClient } from "./dashboard-client";

/**
 * Dashboard Page
 *
 * Delegates to client component which uses auth context for org_id.
 * This ensures dynamic organization context instead of hardcoded values.
 *
 * NOTE: `npm run build:server` is the only production build (P10/M-12 —
 * the static-export mode was retired; it cannot support API-driven
 * detail routes).
 */
export default function DashboardPage() {
  return <DashboardClient />;
}
