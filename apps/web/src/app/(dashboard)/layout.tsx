"use client";

import { useEffect, useSyncExternalStore } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/providers/auth-provider";
import { Shell } from "@/components/layout/shell";

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const { isAuthenticated, isLoading } = useAuth();
  const router = useRouter();
  // P17/FE-M2: the hydration probe via useSyncExternalStore (server
  // snapshot false, client true) — the setMounted-in-an-effect pattern
  // was a cascading render flagged by react-hooks/set-state-in-effect.
  const mounted = useSyncExternalStore(
    () => () => {},
    () => true,
    () => false
  );

  useEffect(() => {
    // Only redirect after initial loading is complete
    if (mounted && !isLoading && !isAuthenticated) {
      const currentPath = window.location.pathname;
      const returnUrl = currentPath !== '/' ? `?redirect=${encodeURIComponent(currentPath)}` : '';
      router.push(`/login${returnUrl}`);
    }
  }, [mounted, isLoading, isAuthenticated, router]);

  // Show loading state during auth check
  if (!mounted || isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-void">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-accent-primary"></div>
      </div>
    );
  }

  // Don't render children if not authenticated
  if (!isAuthenticated) {
    return null;
  }

  return <Shell>{children}</Shell>;
}
