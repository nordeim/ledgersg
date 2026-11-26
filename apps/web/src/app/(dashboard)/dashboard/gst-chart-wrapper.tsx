"use client";

import { useSyncExternalStore } from "react";
import { GSTF5Chart } from "@/components/dashboard/gst-f5-chart";

// P17/FE-M2: the mounted flag via useSyncExternalStore — the
// setMounted(true)-in-an-effect pattern is a cascading-render
// (react-hooks/set-state-in-effect); this is the sanctioned
// "is hydrated" probe (server snapshot false, client true).
const emptySubscribe = () => () => {};
const useIsHydrated = () =>
  useSyncExternalStore(
    emptySubscribe,
    () => true,
    () => false
  );

interface GSTChartWrapperProps {
  gstPayable: string;
}

export function GSTChartWrapper({ gstPayable }: GSTChartWrapperProps) {
  const mounted = useIsHydrated();

  if (!mounted) {
    return (
      <div className="h-[200px] bg-surface/50 rounded-sm flex items-center justify-center">
        <span className="text-text-muted text-sm">Loading chart...</span>
      </div>
    );
  }

  return <GSTF5Chart gstPayable={gstPayable} />;
}
