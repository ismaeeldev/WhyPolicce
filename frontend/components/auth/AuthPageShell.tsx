"use client";

import { motion } from "framer-motion";

const EASE = [0.22, 1, 0.36, 1] as const;

/**
 * Shared shell for /login and /signup — AgentGuide's UI modernization pass.
 * Both pages were previously a static, centered card with no motion and a
 * lot of empty space — the same "very small UI" gap the Memory/History
 * empty states never had. Adds a staggered entrance and a subtle ambient
 * glow behind the card, reusing the same slow-drift decorative language
 * already established for the homepage hero (globals.css's `wp-drift`
 * keyframe) rather than inventing a new visual motif.
 */
export function AuthPageShell({
  children,
  maxWidthClassName = "max-w-[400px]",
}: {
  children: React.ReactNode;
  maxWidthClassName?: string;
}) {
  return (
    <div className="relative flex flex-1 items-center justify-center overflow-hidden px-6 py-20">
      <div
        aria-hidden="true"
        className="animate-wp-drift pointer-events-none absolute h-[420px] w-[420px] rounded-full bg-accent-subtle opacity-40 blur-[90px]"
      />
      <motion.div
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4, ease: EASE }}
        className={`relative w-full text-center ${maxWidthClassName}`}
      >
        {children}
      </motion.div>
    </div>
  );
}
