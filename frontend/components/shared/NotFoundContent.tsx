"use client";

import Link from "next/link";
import { SearchX } from "lucide-react";
import { motion } from "framer-motion";

const EASE = [0.22, 1, 0.36, 1] as const;

/**
 * Global on-brand 404 — AgentGuide/02_ApplicationFlow.md §7.
 * Client wrapper for entrance motion; metadata lives in not-found's parent
 * layout via the static export in not-found.tsx (Next.js limitation).
 *
 * UI polish pass: was a fairly generic "icon + message + button" template.
 * Leans into the product's own search metaphor instead — "no results" copy
 * and a faint ambient glow (the same decorative language already used on
 * the hero and auth shell) so a 404 still feels like part of WhyPolice,
 * not a stock error page bolted onto it.
 */
export function NotFoundContent() {
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
        <SearchX className="h-10 w-10 text-text-muted mb-6" strokeWidth={1.5} />
        <h1 className="font-display text-display-lg leading-[1.1] mb-3">
          No results for that page.
        </h1>
        <p className="max-w-sm text-body text-text-secondary mb-8">
          It doesn&apos;t exist, or may have moved. The trail runs cold here —
          try a fresh search instead.
        </p>
        <div className="flex items-center gap-3">
          <Link
            href="/"
            className="rounded-sm bg-accent px-5 py-2.5 text-body-sm font-medium text-accent-foreground transition-all hover:bg-accent-hover active:scale-[0.98] focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2 outline-none"
          >
            Back to home
          </Link>
          <Link
            href="/search"
            className="rounded-sm border border-border-strong px-5 py-2.5 text-body-sm font-medium text-text-primary transition-all hover:bg-bg-subtle active:scale-[0.98] focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2 outline-none"
          >
            Start a search
          </Link>
        </div>
      </motion.div>
    </div>
  );
}
