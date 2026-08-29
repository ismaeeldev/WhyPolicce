"use client";

import Link from "next/link";
import { SearchX } from "lucide-react";
import { motion } from "framer-motion";

const EASE = [0.22, 1, 0.36, 1] as const;

/**
 * Global on-brand 404 — AgentGuide/02_ApplicationFlow.md §7.
 * Client wrapper for entrance motion; metadata lives in not-found's parent
 * layout via the static export in not-found.tsx (Next.js limitation).
 */
export function NotFoundContent() {
  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.35, ease: EASE }}
      className="flex flex-1 flex-col items-center justify-center px-6 py-24 text-center"
    >
      <SearchX className="h-10 w-10 text-text-muted mb-6" strokeWidth={1.5} />
      <h1 className="font-display text-display-lg leading-[1.1] mb-3">
        We couldn&apos;t find that.
      </h1>
      <p className="max-w-sm text-body text-text-secondary mb-8">
        The page you&apos;re looking for doesn&apos;t exist, or may have moved.
      </p>
      <Link
        href="/"
        className="rounded-sm bg-accent px-5 py-2.5 text-body-sm font-medium text-accent-foreground hover:bg-accent-hover transition-colors focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2 outline-none"
      >
        Back to home
      </Link>
    </motion.div>
  );
}
