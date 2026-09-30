"use client";

import { motion } from "framer-motion";
import { Moon, Sun } from "lucide-react";
import { useTheme } from "next-themes";
import { useSyncExternalStore } from "react";

/**
 * Dark mode toggle — AgentGuide/01_ThemeGuideline.md §8.
 * Respects system preference by default (next-themes), persists explicit
 * choice in localStorage. Sun/moon cross-fade with ~200ms rotation.
 */
export function ThemeToggle() {
  const { resolvedTheme, setTheme } = useTheme();
  const mounted = useSyncExternalStore(
    () => () => {},
    () => true,
    () => false,
  );

  if (!mounted) {
    return (
      <button
        type="button"
        aria-label="Toggle theme"
        className="flex h-9 w-9 items-center justify-center rounded-lg border border-border-default text-text-secondary"
        disabled
      />
    );
  }

  const isDark = resolvedTheme === "dark";

  return (
    <button
      type="button"
      onClick={() => setTheme(isDark ? "light" : "dark")}
      aria-label={isDark ? "Switch to light mode" : "Switch to dark mode"}
      // Real visual gap found during a fresh audit: this used to be a
      // borderless icon floating between the accent "New Inquiry" button
      // and the avatar/Log-in controls, with nothing tying it visually to
      // either — it read as a stray icon, not a deliberate control. A
      // bordered chip (matching FilterDropdown's own rounded-lg/border
      // treatment) gives it the same "this is a real control" weight as
      // every other interactive chip on the page.
      className="relative flex h-9 w-9 items-center justify-center rounded-lg border border-border-default text-text-secondary transition-colors hover:border-border-strong hover:bg-bg-subtle hover:text-text-primary focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2 outline-none"
    >
      <motion.span
        key={isDark ? "moon" : "sun"}
        initial={{ opacity: 0, rotate: -45, scale: 0.8 }}
        animate={{ opacity: 1, rotate: 0, scale: 1 }}
        transition={{ duration: 0.2, ease: "easeOut" }}
        className="flex items-center justify-center"
      >
        {isDark ? <Moon className="h-4 w-4" /> : <Sun className="h-4 w-4" />}
      </motion.span>
    </button>
  );
}
