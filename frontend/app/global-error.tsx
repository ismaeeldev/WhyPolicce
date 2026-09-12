"use client";

import { ErrorContent } from "@/components/shared/ErrorContent";

/**
 * Catches errors thrown by the root layout itself (app/layout.tsx) — the
 * one case error.tsx cannot cover, since error.tsx renders inside the
 * layout it's meant to guard against. Must render its own <html>/<body>
 * (Next.js replaces the whole document in this case) — kept minimal
 * (no fonts/providers/Navbar/Footer, since those are exactly what may
 * have failed) but still the product's own ErrorContent, not a bare
 * Next.js default screen.
 */
export default function GlobalError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <html lang="en">
      <body className="min-h-full flex flex-col bg-bg text-text-primary">
        <main className="flex flex-1 flex-col">
          <ErrorContent error={error} reset={reset} />
        </main>
      </body>
    </html>
  );
}
