"use client";

import { useUser } from "@auth0/nextjs-auth0";
import { ArrowUp, Search, Sparkles } from "lucide-react";
import { useRouter } from "next/navigation";
import { useRef, useState } from "react";

import { trackEvent } from "@/lib/analytics";
import { useSupportedStates } from "@/hooks/useSupportedStates";

const PENDING_QUERY_KEY = "wp_pending_query";

// Revision 3 (plan.md Step 3): examples are now grouped by public-safety
// category, mirroring why.com's real category-pill pattern (Sport /
// Technology / Politics) adapted to WhyPolice's actual domain — Incidents,
// Curfews & Alerts, Case Updates. Each category drives both the rotating
// placeholder AND the visible example chips, so picking a category
// actually changes what's shown, not just a cosmetic label.
export const SEARCH_CATEGORIES = [
  {
    id: "incidents",
    label: "Incidents",
    examples: [
      "Why did the NYPD close the case on Wall Street?",
      "Summarize the latest incident report for downtown Seattle",
      "Has there been a case update for the Main Street robbery?",
      "What happened in the case filed against a local business?",
    ],
  },
  {
    id: "curfews",
    label: "Curfews & Alerts",
    examples: [
      "What is the curfew in Austin tonight?",
      "What's the curfew policy in Chicago this weekend?",
      "Is there an active public safety alert in my area?",
      "Any severe weather or emergency alerts issued today?",
    ],
  },
  {
    id: "cases",
    label: "Case Updates",
    examples: [
      "Give me a summary of last week's precinct incident log",
      "What's the status of the case filed against a local business?",
      "Any recent arrests reported in my precinct?",
      "Was there a felony assault reported nearby?",
    ],
  },
] as const;

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
  /** State Selector, Step 6 — real client-requested feature (their own
   * pasted SearchBar draft already used this exact prop naming). Same
   * "only rendered when a handler is provided" pattern as deep-search
   * above — the public landing page doesn't need it, only the protected
   * /search page wires it. `selectedState` is a real 2-letter USPS code
   * or null/undefined (no state selected — the general, unscoped search
   * behavior from before this feature existed). */
  selectedState?: string | null;
  onStateChange?: (value: string | null) => void;
  /** Landing-page-only: shows the why.com-style category pill row above
   * the search bar, and swaps the rotating placeholder + example chips to
   * match whichever category is selected. Omitted on the protected
   * /search page (Step 5), which reuses this same component but has no
   * concept of marketing categories — just a plain search bar there. */
  showCategories?: boolean;
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
  selectedState,
  onStateChange,
  showCategories = false,
}: SearchBarProps) {
  const { data: supportedStates } = useSupportedStates();
  const [value, setValue] = useState(initialValue);
  const [categoryIndex, setCategoryIndex] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);
  const router = useRouter();
  const { user } = useUser();

  const activeChips = showCategories
    ? SEARCH_CATEGORIES[categoryIndex].examples
    : SEARCH_CATEGORIES[0].examples;

  const selectCategory = (index: number) => {
    setCategoryIndex(index);
    trackEvent("search_category_selected", { category: SEARCH_CATEGORIES[index].id });
  };

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
    <div className="wp-search w-full min-w-0 max-w-[760px] mx-auto">
      {/* Revision 3 (plan.md Step 3): category pills, matching why.com's
          real Sport/Technology/Politics row above its search reveal —
          adapted to public-safety topics. Landing-page-only (showCategories
          prop); the protected /search page renders this same component
          without them, since a logged-in user is past the marketing
          moment these serve. Selecting a category changes both the
          rotating placeholder and the visible example chips below. */}
      {showCategories && (
        <div className="mb-5 flex flex-wrap items-center justify-center gap-2">
          {SEARCH_CATEGORIES.map((category, i) => (
            <button
              key={category.id}
              type="button"
              aria-pressed={categoryIndex === i}
              onClick={() => selectCategory(i)}
              className={`wp-category rounded-full border px-3.5 py-2 text-caption font-medium transition-colors focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2 outline-none ${
                categoryIndex === i
                  // Real contrast bug found and fixed during a UI audit
                  // (plan.md "UI audit"): accent (#B0521F) text on
                  // accent-subtle measures ~4.08:1 at caption size,
                  // failing AA's 4.5:1 — the exact failure mode §1.4
                  // already documents and fixes for the Pro/tier badge
                  // pattern (§4.6: "text-primary for the label, accent
                  // reserved for icons only"). This was the one place in
                  // the codebase that had regressed to the banned
                  // pairing. Border can stay accent — borders/UI
                  // components only need the 3:1 threshold, which accent
                  // clears comfortably.
                  ? "border-accent text-text-primary bg-accent-subtle"
                  : "border-border-strong text-text-muted hover:text-text-secondary hover:border-text-muted"
              }`}
            >
              {category.label}
            </button>
          ))}
        </div>
      )}

      {/* Pill-shaped input matching why.com's real, live-measured search bar
          (verified via getComputedStyle, not guessed): ~580px max-width,
          ~64px tall, fully rounded, semi-transparent dark fill, ~20px
          input font-size, literal "Ask anything…" placeholder. The
          rotating-question job now belongs to TypedHeadline (Step 7) —
          why.com's own placeholder is static, not rotating, once the
          search bar itself is revealed.

          Step 8 fix: the 580px cap is why.com-matching specifically for
          the marketing landing moment (showCategories) — hardcoding it
          unconditionally had regressed the protected /search page's bar
          to be visibly narrower than its own AnswerPanel below it (that
          panel is still the page's original 760px), a real layout
          mismatch this component's two consumers didn't share before.
          Only the landing usage gets the narrower why.com-matched width;
          /search keeps filling its own container. */}
      <form
        onSubmit={handleSubmit}
        className={`wp-search-form relative mx-auto flex min-w-0 items-center rounded-full border border-border-default shadow-card transition-colors focus-within:border-accent ${
          showCategories ? "max-w-[640px]" : "w-full"
        }`}
        style={{ backgroundColor: "rgba(17, 17, 16, 0.86)" }}
      >
        <Search
          aria-hidden="true"
          className="pointer-events-none absolute left-5 h-4 w-4 text-search-pill-foreground/60"
        />
        <input
          ref={inputRef}
          type="text"
          value={value}
          onChange={(e) => setValue(e.target.value)}
          autoFocus={autoFocus}
          disabled={disabled}
          aria-label="Search"
          placeholder="Ask anything…"
          className="h-16 min-w-0 w-full flex-1 bg-transparent pl-11 pr-3 text-body sm:text-search-pill text-search-pill-foreground outline-none placeholder:text-search-pill-foreground/60 disabled:opacity-60"
        />
        <button
          type="submit"
          disabled={!value.trim() || disabled}
          aria-label="Submit search"
          className="mr-2 flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-accent text-accent-foreground transition-all hover:opacity-90 active:scale-95 disabled:bg-bg-subtle disabled:text-text-muted disabled:opacity-100 focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2 outline-none"
        >
          <ArrowUp className="h-4 w-4" />
        </button>
      </form>

      <div className="wp-search-suggestions mt-5 flex flex-wrap items-center justify-center gap-2">
        {/* State Selector, Step 6 — real client-requested feature. Real
            options fetched live from GET /api/search/states (Step 3),
            not the client's own draft's 5-state hardcoded placeholder
            (NY/CA/TX/FL/IL) — this list can only ever show states
            WhyPolice actually has real integrated data for, and stays
            correct automatically as future city-expansion phases land. */}
        {onStateChange && (
          <select
            value={selectedState ?? ""}
            onChange={(e) => onStateChange(e.target.value || null)}
            disabled={disabled}
            aria-label="Select U.S. State"
            className="min-h-10 rounded-full border border-border-default bg-bg-elevated px-3.5 py-2 text-body-sm text-text-secondary transition-colors hover:border-border-strong focus-visible:ring-2 focus-visible:ring-accent outline-none disabled:opacity-60 cursor-pointer"
          >
            <option value="">All states</option>
            {supportedStates?.map((s) => (
              <option key={s.code} value={s.code}>
                {s.name} ({s.code})
              </option>
            ))}
          </select>
        )}
        {onDeepSearchChange && (
          <button
            type="button"
            aria-pressed={deepSearch}
            disabled={disabled}
            onClick={() => onDeepSearchChange(!deepSearch)}
            className={`flex items-center gap-1.5 min-h-10 rounded-full border px-3.5 py-2 text-body-sm transition-colors focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2 outline-none disabled:opacity-60 ${
              deepSearch
                ? "border-accent bg-accent-subtle text-text-primary"
                : "border-border-default bg-bg-elevated text-text-secondary hover:border-border-strong"
            }`}
          >
            <Sparkles className="h-3.5 w-3.5" />
            Deep search
          </button>
        )}
        {activeChips.map((chip) => (
          <button
            key={chip}
            type="button"
            onClick={() => fillChip(chip)}
            disabled={disabled}
            className="min-h-10 rounded-full border border-border-default bg-bg-elevated px-3.5 py-2 text-body-sm text-text-secondary transition-colors hover:border-border-strong hover:text-text-primary hover:bg-bg-subtle focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2 outline-none disabled:opacity-60"
          >
            {chip}
          </button>
        ))}
      </div>
    </div>
  );
}
