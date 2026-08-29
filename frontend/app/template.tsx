"use client";

import { motion, useReducedMotion } from "framer-motion";

/**
 * Route content transition — AgentGuide/01_ThemeGuideline.md §9.
 * Subtle 8–12px vertical slide + fade on the content area only; the
 * persistent chrome (Navbar, Footer) stays put via layout.tsx.
 */
export default function Template({ children }: { children: React.ReactNode }) {
  const reduceMotion = useReducedMotion();

  return (
    <motion.div
      initial={reduceMotion ? false : { opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.22, ease: [0.22, 1, 0.36, 1] }}
      className="flex flex-1 flex-col"
    >
      {children}
    </motion.div>
  );
}
