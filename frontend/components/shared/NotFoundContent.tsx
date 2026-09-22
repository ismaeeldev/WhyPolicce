"use client";

import Link from "next/link";
import { CompassIcon } from "lucide-react";
import { motion } from "framer-motion";

const EASE = [0.22, 1, 0.36, 1] as const;

/**
 * Global on-brand 404 — AgentGuide/02_ApplicationFlow.md §7.
 * Client wrapper for entrance motion; metadata lives in not-found's parent
 * layout via the static export in not-found.tsx (Next.js limitation).
 *
 * Real bug found during a full-scope re-audit: this used to lean on the
 * OLD RAG-search product's own metaphor — "no results," a search icon,
 * and a "Start a search" button linking to /search, the retired product
 * (see the scope PDF's "What We Are No Longer Building On"). A visitor
 * hitting a bad/stale link (e.g. a deleted inquiry) got bounced further
 * from the forum, not back to it — /search is behind the same auth guard
 * as the rest of the old product, so a logged-out visitor would even get
 * detoured through a login prompt before landing on a dead product.
 * Rewritten for the real forum: the second recovery action now points at
 * starting a new inquiry, the actual thing a visitor here can DO, rather
 * than duplicating "Back to home."
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
        <CompassIcon className="h-10 w-10 text-text-muted mb-6" strokeWidth={1.5} />
        <h1 className="font-display text-h1 sm:text-display-lg leading-[1.1] mb-3">
          This page doesn&apos;t exist.
        </h1>
        <p className="max-w-sm text-body text-text-secondary mb-8">
          It may have been deleted or the link is wrong. Head back to the
          feed, or post what you&apos;re looking for as a new inquiry.
        </p>
        <div className="flex flex-wrap items-center justify-center gap-3">
          <Link
            href="/"
            className="rounded-sm bg-accent px-5 py-2.5 text-body-sm font-medium text-accent-foreground transition-all hover:bg-accent-hover active:scale-[0.98] focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2 outline-none"
          >
            Back to the feed
          </Link>
          <Link
            href="/inquiries/new"
            className="rounded-sm border border-border-strong px-5 py-2.5 text-body-sm font-medium text-text-primary transition-all hover:bg-bg-subtle active:scale-[0.98] focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2 outline-none"
          >
            Post an inquiry
          </Link>
        </div>
      </motion.div>
    </div>
  );
}
