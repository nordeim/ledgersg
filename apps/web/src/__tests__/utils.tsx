/**
 * LEDGERSG TEST UTILITIES
 *
 * Custom render function with providers for component testing
 */

import * as React from "react";
import { render as rtlRender, RenderOptions } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

// Create a custom render function that includes providers
interface CustomRenderOptions extends Omit<RenderOptions, "wrapper"> {
  queryClient?: QueryClient;
}

function createTestQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
        staleTime: 0,
        gcTime: 0,
      },
    },
  });
}

function AllProviders({ children }: { children: React.ReactNode }) {
  const queryClient = createTestQueryClient();

  return (
    <QueryClientProvider client={queryClient}>
      {children}
    </QueryClientProvider>
  );
}

export function render(
  ui: React.ReactElement,
  options: CustomRenderOptions = {}
) {
  const { queryClient = createTestQueryClient(), ...renderOptions } = options;

  return {
    ...rtlRender(ui, {
      wrapper: AllProviders,
      ...renderOptions,
    }),
    queryClient,
  };
}

// Re-export everything from testing-library
export * from "@testing-library/react";
export { userEvent } from "@testing-library/user-event";

// Custom test ID helpers
export const testIds = {
  button: (name?: string) => name ? `button-${name}` : "button",
  input: (name: string) => `input-${name}`,
  form: (name?: string) => name ? `form-${name}` : "form",
  toast: "toast",
  skeleton: "skeleton",
  badge: (variant?: string) => variant ? `badge-${variant}` : "badge",
} as const;
