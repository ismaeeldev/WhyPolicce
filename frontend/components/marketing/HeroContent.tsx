"use client";

import { motion } from "framer-motion";

import { SearchBar } from "@/components/search/SearchBar";

const EASE = [0.22, 1, 0.36, 1] as const;

const item = {
  hidden: { opacity: 0, y: 16 },
  show: { opacity: 1, y: 0 },
};

/**
 * Subhead + search bar, with a deliberate staggered entrance on mount —
 * AgentGuide/03_MasterPromptGuide.md Step 2's Design Quality Bar.
 *
 * The H1 headline is intentionally NOT in this client component — it's
 * rendered as plain static markup in app/page.tsx (a Server Component) so it
 * paints immediately with the rest of the static HTML. Lighthouse traced a
 * ~550ms Largest Contentful Paint delay to the headline being gated behind
 * Framer Motion's initial="hidden" state, i.e. invisible until JS hydrates —
 * a real LCP anti-pattern for a static, server-rendered heading. Only the
 * secondary elements (which aren't the LCP candidate) get the entrance motion.
 */
export function HeroContent() {
  return (
    <motion.div
      initial="hidden"
      animate="show"
      variants={{ show: { transition: { staggerChildren: 0.1 } } }}
      className="flex w-full flex-col items-center"
    >
      <motion.p
        variants={item}
        transition={{ duration: 0.5, ease: EASE }}
        className="mt-5 max-w-[520px] text-body-lg text-text-secondary"
      >
        Ask about police reports, case updates, curfews, and public safety
        data — the answer streams in live, no ads, no clutter, just what
        you asked.
      </motion.p>

      <motion.div
        variants={item}
        transition={{ duration: 0.5, ease: EASE }}
        className="mt-10 w-full"
      >
        <SearchBar />
      </motion.div>
    </motion.div>
  );
}
