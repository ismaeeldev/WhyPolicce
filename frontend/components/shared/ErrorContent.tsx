"use client";

import { useEffect } from "react";
import Link from "next/link";
import { TriangleAlert } from "lucide-react";
import { motion } from "framer-motion";

const EASE = [0.22, 1, 0.36, 1] as const;

/**
 * Global on-brand error boundary — closes the gap-audit finding that no
 * error.tsx existed anywhere in the app, so any thrown render/data error
 * fell through to Next.js's default unstyled error screen instead of
 * WhyPolice's own UI. Mirrors NotFoundContent's structure/motion/tokens
 * exactly (same ambient-glow language, same button pair) so an error page
 * still feels like part of the product, not a generic template.
 */
export function ErrorContent({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    // Next.js requires client error boundaries to log the error themselves
    // (it isn't reported anywhere else). Kept to console — no analytics/
    // error-tracking service is wired into this project.
    console.error(error);
  }, [error]);

  return (
    <div className="relative flex flex-1 items-center justify-center overflow-hidden px-6 py-24">
      <div
        aria-hidden="true"
        className="animate-wp-drift pointer-events-none absolute h-[380px] w-[380px] rounded-full bg-accent-subtle opacity-30 blur-[100px]"
      />
      <motion.div
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.35, ease: EASE }}
        className="relative flex flex-col items-center text-center"
      >
        <TriangleAlert className="h-10 w-10 text-text-muted mb-6" strokeWidth={1.5} />
        <h1 className="font-display text-display-lg leading-[1.1] mb-3">
          Something went wrong.
        </h1>
        <p className="max-w-sm text-body text-text-secondary mb-8">
          That search hit a snag on our end. Try again, or head back home —
          nothing you had in progress was lost.
        </p>
        <div className="flex items-center gap-3">
          <button
            type="button"
            onClick={reset}
            className="rounded-sm bg-accent px-5 py-2.5 text-body-sm font-medium text-accent-foreground transition-all hover:bg-accent-hover active:scale-[0.98] focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2 outline-none"
          >
            Try again
          </button>
          <Link
            href="/"
            className="rounded-sm border border-border-strong px-5 py-2.5 text-body-sm font-medium text-text-primary transition-all hover:bg-bg-subtle active:scale-[0.98] focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2 outline-none"
          >
            Back to home
          </Link>
        </div>
      </motion.div>
    </div>
  );
}
