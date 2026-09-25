import { QueryClient } from "@tanstack/react-query";
import { cache } from "react";

/**
 * Server-only QueryClient factory — TanStack Query's own documented
 * Next.js App Router pattern (react's `cache()` scopes one instance per
 * request, never shared across requests/users, unlike a module-level
 * singleton which would leak one user's prefetched data into another's
 * response on a shared server). Used to prefetch data in a Server
 * Component, then hand it to the client tree via HydrationBoundary —
 * see app/page.tsx for the first real use of this.
 */
export const getQueryClient = cache(
  () =>
    new QueryClient({
      defaultOptions: {
        queries: {
          staleTime: 30_000,
        },
      },
    }),
);
