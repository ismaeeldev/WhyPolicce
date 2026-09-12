"use client";

import { motion } from "framer-motion";
import { Landmark, Sparkles } from "lucide-react";
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
        <div className="flex flex-col items-start justify-between gap-3 pr-8 sm:flex-row">
          <p className="text-body text-text-primary leading-snug line-clamp-2 [overflow-wrap:anywhere]">
            {session.title || "Untitled search"}
          </p>
          {session.isDeepSearch && (
            // Real token-drift fix from a UI audit (plan.md "UI audit"):
            // this was the one badge in the codebase using a bespoke
            // 11px/leading-4 pairing instead of the established
            // text-caption token every other badge (Pro/tier badges,
            // pricing's "Most popular", AnswerPanel's source/memory
            // lines) already uses for this exact visual role.
            <span className="flex shrink-0 items-center gap-1 rounded-full bg-accent-subtle px-2.5 py-0.5 text-text-primary text-caption font-medium">
              <Sparkles className="h-3 w-3 text-accent-bright" />
              Deep search
            </span>
          )}
        </div>
        <div className="mt-2 flex items-center gap-2 text-body-sm text-text-muted">
          <span>{formatRelativeTime(session.createdAt)}</span>
          {/* Real gap found via UI review (plan.md "Product/quality
              work"): the source-citations feature already surfaces real
              public-record attribution on the live answer view and
              session-detail replay, but a user scanning their history had
              no way to tell "this one found real records" from "this one
              didn't" without opening each session. Same "absence must be
              invisible" rule as everywhere else this feature appears —
              no icon at all when a session has no sources, never a
              visible "no sources" state. Reuses AnswerPanel's own
              Landmark icon for the same concept rather than a new one. */}
          {session.hasSources && (
            <span className="flex items-center gap-1" title="Sourced from real public records">
              <Landmark className="h-3 w-3 shrink-0" />
            </span>
          )}
        </div>
      </Link>
    </motion.div>
  );
}
