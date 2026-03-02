import { DashboardClient } from "./dashboard-client";

/**
 * Dashboard Page
 *
 * Delegates to client component which uses auth context for org_id.
 * This ensures dynamic organization context instead of hardcoded values.
 * 
 * NOTE: For production use with backend API, use `npm run build:server`
 * instead of `npm run build` (which is for static export).
 */
export default function DashboardPage() {
  return <DashboardClient />;
}
