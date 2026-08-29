"use client";

import { motion } from "framer-motion";
import { Sparkles } from "lucide-react";
import Link from "next/link";

import { formatRelativeTime } from "@/lib/format";

import type { HistorySession } from "@/hooks/useSearchHistory";

const CARD_VARIANTS = {
  hidden: { opacity: 0, y: 16 },
  visible: { opacity: 1, y: 0 },
};

/**
 * History session card — AgentGuide/01_ThemeGuideline.md §4.4 (hover lift
 * 2px + shadow deepen, 150ms) and §4.6 (deep-search badge reuses the same
 * pill language as the Pro tier badge). Entrance stagger is driven by the
 * parent list's `custom` index (§7.2: 60–100ms stagger).
 */
export function SessionCard({ session, index }: { session: HistorySession; index: number }) {
  return (
    <motion.div
      variants={CARD_VARIANTS}
      initial="hidden"
      animate="visible"
      transition={{ duration: 0.3, delay: Math.min(index * 0.06, 0.36), ease: [0.22, 1, 0.36, 1] }}
      whileHover={{ y: -2 }}
      className="group"
    >
      <Link
        href={`/search/${session.id}`}
        className="block rounded-md border border-border-default bg-bg-elevated p-4 sm:p-6 shadow-none transition-shadow duration-150 group-hover:shadow-card focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2 outline-none"
      >
        <div className="flex items-start justify-between gap-3">
          <p className="text-body text-text-primary leading-snug line-clamp-2">
            {session.title || "Untitled search"}
          </p>
          {session.isDeepSearch && (
            <span className="flex shrink-0 items-center gap-1 rounded-full bg-accent-subtle px-2.5 py-0.5 text-text-primary text-[11px] leading-4 font-medium">
              <Sparkles className="h-3 w-3 text-accent-bright" />
              Deep search
            </span>
          )}
        </div>
        <p className="mt-2 text-body-sm text-text-muted">{formatRelativeTime(session.createdAt)}</p>
      </Link>
    </motion.div>
  );
}
