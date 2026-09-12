"use client";

import { motion } from "framer-motion";
import { useEffect, useState } from "react";

import { SearchBar } from "@/components/search/SearchBar";

const EASE = [0.22, 1, 0.36, 1] as const;

const item = {
  hidden: { opacity: 0, y: 16 },
  show: { opacity: 1, y: 0 },
};

// Same key the protected /search page reads (app/(protected)/search/page.tsx)
// — picking a state here before signing up/logging in "just works" once the
// user lands on the real search page, with no separate handoff plumbing
// needed (the pending-query handoff already only carries the prompt text).
const SELECTED_STATE_KEY = "wp_selected_state";

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
  // Same hydration-safety pattern as SearchPage's own selectedState (see
  // its docstring): the <select>'s selected <option> is render-affecting,
  // so it must render the SSR-safe default (null) on first paint always,
  // then correct itself in an effect right after hydration — not read
  // localStorage inside a useState lazy initializer, which would make the
  // client's first paint disagree with the server's and trip a real React
  // hydration-mismatch error (the exact bug already found and fixed once
  // on the /search page for this identical case).
  const [selectedState, setSelectedStateRaw] = useState<string | null>(null);
  useEffect(() => {
    const stored = localStorage.getItem(SELECTED_STATE_KEY);
    // eslint-disable-next-line react-hooks/set-state-in-effect
    if (stored) setSelectedStateRaw(stored);
  }, []);
  const setSelectedState = (value: string | null) => {
    setSelectedStateRaw(value);
    try {
      if (value) {
        localStorage.setItem(SELECTED_STATE_KEY, value);
      } else {
        localStorage.removeItem(SELECTED_STATE_KEY);
      }
    } catch {
      // Storage unavailable (private browsing, quota) — selection still
      // works for this visit, it just won't carry through to signup/login.
    }
  };

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
        className="mt-6 max-w-[520px] text-body text-text-secondary sm:text-body-lg"
      >
        Ask about police reports, case updates, curfews, and public safety
        data — the answer streams in live, no ads, no clutter, just what
        you asked.
      </motion.p>

      <motion.div
        variants={item}
        transition={{ duration: 0.5, ease: EASE }}
        className="mt-8 w-full sm:mt-10"
      >
        {/* Revision 3 (plan.md Step 3): showCategories is landing-page-only
            — this is the only place SearchBar renders the why.com-style
            category pill row. The protected /search page's own SearchBar
            usage is deliberately left without this prop. */}
        <SearchBar showCategories selectedState={selectedState} onStateChange={setSelectedState} />
      </motion.div>
    </motion.div>
  );
}
