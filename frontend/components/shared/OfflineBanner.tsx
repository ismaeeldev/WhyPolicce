"use client";

import { AnimatePresence, motion } from "framer-motion";
import { WifiOff } from "lucide-react";

import { useOnlineStatus } from "@/hooks/useOnlineStatus";

/**
 * Global "you're offline" indicator — AgentGuide/03_MasterPromptGuide.md
 * Step 8's Bug Sweep explicitly calls for testing this scenario ("Simulate
 * an offline network mid-navigation... does the app communicate the
 * failure?"); this is what actually communicates it, rather than leaving
 * every in-flight request to fail with a generic, uncontextualized error.
 *
 * Fixed overlay (not layout-shifting) so it never causes CLS — sits at the
 * same system-notification tier as the Toast viewport (§3.2's z-[70]),
 * positioned at the top so it never visually collides with Toast's
 * bottom placement. Uses the same calm warning-subtle treatment as
 * AnswerPanel's rate-limited state (§4.3) — connectivity loss is
 * informational, not alarming, so this deliberately avoids the danger tokens.
 */
export function OfflineBanner() {
  const isOnline = useOnlineStatus();

  return (
    <AnimatePresence>
      {!isOnline && (
        <motion.div
          initial={{ y: -48, opacity: 0 }}
          animate={{ y: 0, opacity: 1 }}
          exit={{ y: -48, opacity: 0 }}
          transition={{ duration: 0.25, ease: [0.22, 1, 0.36, 1] }}
          role="status"
          aria-live="polite"
          className="fixed inset-x-0 top-0 z-[70] flex items-center justify-center gap-2 border-b border-warning bg-warning-subtle px-4 py-2 text-body-sm text-text-primary"
        >
          <WifiOff className="h-3.5 w-3.5 shrink-0" />
          You&apos;re offline — reconnect to keep searching.
        </motion.div>
      )}
    </AnimatePresence>
  );
}
