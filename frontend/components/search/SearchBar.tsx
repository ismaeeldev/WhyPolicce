"use client";

import { useUser } from "@auth0/nextjs-auth0";
import { motion, AnimatePresence } from "framer-motion";
import { ArrowUp, Sparkles } from "lucide-react";
import { useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";

import { trackEvent } from "@/lib/analytics";

const PENDING_QUERY_KEY = "wp_pending_query";

const PLACEHOLDER_EXAMPLES = [
  "Compare Roth IRA vs 401k for a freelancer",
  "Why does the sky turn orange at sunset?",
  "Summarize the latest Fed rate decision",
  "Explain quantum entanglement like I'm 12",
];

const EXAMPLE_CHIPS = [
  "Explain the James Webb deep field image",
  "Draft a polite deadline-extension email",
  "Why do cats knead blankets?",
  "What's the difference between weather and climate?",
];

type SearchBarProps = {
  autoFocus?: boolean;
  initialValue?: string;
  disabled?: boolean;
  /** If provided, called for a logged-in submit instead of the built-in stub
   * — the protected /search page wires this to useSearchStream. Landing page
   * (Step 2) omits it, keeping the original "nothing to submit to yet" behavior. */
  onSubmit?: (query: string) => void;
  /** Deep-search toggle — only rendered when a handler is provided, so the
   * public landing page (which has no tier concept) never shows it. */
  deepSearch?: boolean;
  onDeepSearchChange?: (value: boolean) => void;
};

/**
 * The centered search bar — AgentGuide/01_ThemeGuideline.md §4.3, the single
 * highest design-priority component in the product. Logged-out submit
 * preserves the query and redirects to /signup per ApplicationFlow §2.2;
 * logged-in submit calls the optional onSubmit prop, wired to real SSE
 * streaming on the protected /search page (Step 5).
 */
export function SearchBar({
  autoFocus = false,
  initialValue = "",
  disabled = false,
  onSubmit,
  deepSearch,
  onDeepSearchChange,
}: SearchBarProps) {
  const [value, setValue] = useState(initialValue);
  const [placeholderIndex, setPlaceholderIndex] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);
  const router = useRouter();
  const { user } = useUser();

  useEffect(() => {
    if (value) return;
    const interval = setInterval(() => {
      setPlaceholderIndex((i) => (i + 1) % PLACEHOLDER_EXAMPLES.length);
    }, 3200);
    return () => clearInterval(interval);
  }, [value]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const query = value.trim();
    if (!query || disabled) return;

    if (!user) {
      trackEvent("search_submitted_logged_out", { queryLength: query.length });
      sessionStorage.setItem(PENDING_QUERY_KEY, query);
      router.push("/signup");
      return;
    }

    if (onSubmit) {
      onSubmit(query);
      return;
    }

    // Logged-in on the public landing page — preserve query and route to
    // /search, same pattern as the logged-out → /signup handoff.
    trackEvent("search_submitted_logged_in_redirect", { queryLength: query.length });
    sessionStorage.setItem(PENDING_QUERY_KEY, query);
    router.push("/search");
  };

  const fillChip = (chip: string) => {
    setValue(chip);
    trackEvent("example_chip_clicked", { chip });
    inputRef.current?.focus();
  };

  return (
    <div className="w-full max-w-[760px] mx-auto">
      <form
        onSubmit={handleSubmit}
        className="relative flex items-center rounded-lg bg-bg-elevated border border-border-default shadow-card transition-colors focus-within:border-accent"
      >
        <div className="relative flex-1 h-14 sm:h-16">
          <input
            ref={inputRef}
            type="text"
            value={value}
            onChange={(e) => setValue(e.target.value)}
            autoFocus={autoFocus}
            disabled={disabled}
            aria-label="Search"
            className="absolute inset-0 w-full h-full bg-transparent pl-5 sm:pl-6 pr-14 text-body-lg text-text-primary outline-none placeholder:text-transparent disabled:opacity-60"
          />
          {!value && (
            <div className="absolute inset-0 flex items-center pl-5 sm:pl-6 pr-14 pointer-events-none overflow-hidden">
              <AnimatePresence mode="wait">
                <motion.span
                  key={placeholderIndex}
                  initial={{ opacity: 0, y: 6 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -6 }}
                  transition={{ duration: 0.35, ease: [0.22, 1, 0.36, 1] }}
                  className="text-body-lg text-text-muted truncate"
                >
                  {PLACEHOLDER_EXAMPLES[placeholderIndex]}
                </motion.span>
              </AnimatePresence>
            </div>
          )}
        </div>
        <button
          type="submit"
          disabled={!value.trim() || disabled}
          aria-label="Submit search"
          className="mr-2.5 flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-accent text-accent-foreground transition-all hover:bg-accent-hover active:scale-95 disabled:bg-bg-subtle disabled:text-text-muted focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2 outline-none"
        >
          <ArrowUp className="h-4 w-4" />
        </button>
      </form>

      <div className="mt-5 flex flex-wrap items-center justify-center gap-2">
        {onDeepSearchChange && (
          <button
            type="button"
            aria-pressed={deepSearch}
            disabled={disabled}
            onClick={() => onDeepSearchChange(!deepSearch)}
            className={`flex items-center gap-1.5 rounded-full border px-3.5 py-1.5 text-body-sm transition-colors focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2 outline-none disabled:opacity-60 ${
              deepSearch
                ? "border-accent bg-accent-subtle text-text-primary"
                : "border-border-default bg-bg-elevated text-text-secondary hover:border-border-strong"
            }`}
          >
            <Sparkles className="h-3.5 w-3.5" />
            Deep search
          </button>
        )}
        {EXAMPLE_CHIPS.map((chip) => (
          <button
            key={chip}
            type="button"
            onClick={() => fillChip(chip)}
            disabled={disabled}
            className="rounded-full border border-border-default bg-bg-elevated px-3.5 py-1.5 text-body-sm text-text-secondary transition-colors hover:border-border-strong hover:text-text-primary hover:bg-bg-subtle focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2 outline-none disabled:opacity-60"
          >
            {chip}
          </button>
        ))}
      </div>
    </div>
  );
}
