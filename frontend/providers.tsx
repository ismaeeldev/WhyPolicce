"use client";

import { Auth0Provider } from "@auth0/nextjs-auth0";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ReactQueryDevtools } from "@tanstack/react-query-devtools";
import { MotionConfig } from "framer-motion";
import { ThemeProvider } from "next-themes";
import { useState } from "react";

import { RouteProgressBar } from "@/components/layout/RouteProgressBar";
import { OfflineBanner } from "@/components/shared/OfflineBanner";
import { ToastViewport } from "@/components/shared/Toast";
import { UpgradeModal } from "@/components/shared/UpgradeModal";

/**
 * App-wide providers — AgentGuide/01_ThemeGuideline.md §8 (dark mode) and §10
 * (state management), plus Auth0Provider (Step 3) so `useUser()` works in
 * client components like the Navbar. One QueryClient per browser session
 * (useState so it survives re-renders but isn't shared across users on the server).
 */
export function Providers({ children }: { children: React.ReactNode }) {
  const [queryClient] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            staleTime: 30_000,
            refetchOnWindowFocus: true,
          },
        },
      }),
  );

  return (
    <Auth0Provider>
      <QueryClientProvider client={queryClient}>
        <ThemeProvider attribute="class" defaultTheme="system" enableSystem>
          {/* "user" — every Framer Motion animation in the app (cards, toasts,
              modals, marketing entrances) auto-respects the OS-level
              prefers-reduced-motion setting from here, without needing to
              thread a check through each individual component. GSAP
              (ScrollReveal) and the CSS-keyframe skeleton/hero-drift
              animations already handle it themselves (see globals.css). */}
          <MotionConfig reducedMotion="user">
            <OfflineBanner />
            <RouteProgressBar />
            {children}
            <UpgradeModal />
            <ToastViewport />
          </MotionConfig>
        </ThemeProvider>
        <ReactQueryDevtools initialIsOpen={false} />
      </QueryClientProvider>
    </Auth0Provider>
  );
}
