"use client";

import { BrainCircuit, Check, Copy, Landmark, Lock, RotateCcw } from "lucide-react";
import { useEffect, useRef, useState } from "react";

import { ThinkingIndicator } from "@/components/search/ThinkingIndicator";
import { useUpgradeModalStore } from "@/stores/useUpgradeModalStore";

import type { StreamStatus } from "@/hooks/useSearchStream";
import type { SearchSource } from "@/lib/sse";

// A source's own dataset id (e.g. "chicago_crimes", "nyc_nypd_arrest") is
// internal/technical — a real client-facing gap this citation feature
// exists to close would just move the "hard to parse" problem into the
// citation line itself if shown verbatim. Turns it into the kind of
// plain-language label a user actually reads, e.g. "Chicago Police Dept.
// crime data" — falls back to a generic-but-still-honest label for any
// source not in this map rather than ever hiding a real citation.
function formatSourceLabel(source: SearchSource): string {
  const isCalls = /_calls$/.test(source.source) || /calls_for_service|_cfs/.test(source.source);
  const kind = isCalls ? "calls-for-service data" : "crime data";
  return `${source.city} ${kind}`;
}

// Real bug found and fixed during this feature's own follow-up testing:
// two technically distinct backend sources for the same city (e.g. NYC's
// separate nyc_nypd_arrest and nyc_nypd_complaint datasets) both format to
// the identical label "New York City crime data" — the backend's own
// _build_citations() correctly keeps them as separate citation entries
// (real, distinct datasets, right for data integrity), but rendering both
// literally produced "New York City crime data, New York City crime
// data," a genuinely confusing duplicate a user would read as a mistake.
// De-duplicated at the DISPLAY layer, after formatting, not by changing
// what the backend tracks — Set() on the formatted strings preserves
// first-seen order, matching the citation list's own retrieval order.
function formatSourceLabels(sources: SearchSource[]): string {
  return Array.from(new Set(sources.map(formatSourceLabel))).join(", ");
}

/**
 * Streaming answer display — AgentGuide/01_ThemeGuideline.md §4.3, §7.3
 * point 4, and §7.4 (anti-fluctuation: this is the single most
 * animation-risk-prone screen in the app). The text grows as one block
 * (typewriter-style reveal per §7.3.4) rather than animating individual
 * per-chunk spans with array-index keys — avoids the exact "unstable keys"
 * jank §7.4 warns about, since a single accumulating text node has nothing
 * to re-key on each token.
 */
export function AnswerPanel({
  text,
  status,
  errorMessage,
  retryAfterSeconds,
  tier,
  onRetry,
  retryLabel = "Regenerate",
  memorySnippets = [],
  sources = [],
}: {
  text: string;
  status: StreamStatus;
  errorMessage: string | null;
  retryAfterSeconds: number | null;
  tier: "free" | "pro" | undefined;
  onRetry: () => void;
  /** "Regenerate" re-runs the same prompt in place (live search screen);
   * session-detail replay passes "Continue this search" since onRetry there
   * navigates to /search instead of regenerating in place. */
  retryLabel?: string;
  /** ApplicationFlow §3.3 state 5 — "Memory referenced: [note titles]" line.
   * Absence must be invisible (empty array = nothing rendered), never a
   * visible "no memory used" state, per §7's edge-states checklist. */
  memorySnippets?: string[];
  /** Real source citations — see search_service.py's _build_citations and
   * this project's plan.md "Beyond Phase 31" UI-quality note: this answers
   * a genuine, previously-missing client-facing gap (every answer is
   * backed by real, retrieved public records, but the UI never visibly
   * said so, only the answer's own free-text prose did). Same
   * "absence must be invisible" rule as memorySnippets — an off-topic
   * question with no retrieved records renders no citation line at all,
   * never a "no sources found" state. */
  sources?: SearchSource[];
}) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [userScrolledUp, setUserScrolledUp] = useState(false);
  const [copied, setCopied] = useState(false);
  const openUpgradeModal = useUpgradeModalStore((s) => s.open);

  // Reset the "user scrolled up" flag when a new submission starts — React's
  // own recommended "adjust state during render" pattern (not an effect) for
  // resetting state in response to a prop change, avoids an extra render pass.
  const [prevStatus, setPrevStatus] = useState(status);
  if (status !== prevStatus) {
    setPrevStatus(status);
    if (status === "submitting") setUserScrolledUp(false);
  }

  // Auto-scroll while streaming — reserved container height + transform-only
  // scroll (not layout-affecting), guarded so it never fights a manual scroll.
  useEffect(() => {
    if (status !== "streaming" || userScrolledUp) return;
    containerRef.current?.scrollTo({ top: containerRef.current.scrollHeight });
  }, [text, status, userScrolledUp]);

  const handleScroll = () => {
    const el = containerRef.current;
    if (!el) return;
    const distanceFromBottom = el.scrollHeight - el.scrollTop - el.clientHeight;
    setUserScrolledUp(distanceFromBottom > 48);
  };

  const handleCopy = async () => {
    await navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  };

  if (status === "idle") return null;

  if (status === "error") {
    return (
      <div className="mt-6 rounded-md border border-danger bg-danger-subtle p-5 text-center">
        <p className="text-body-sm text-text-primary mb-3">
          Search interrupted — {errorMessage ?? "that answer didn't arrive."}
        </p>
        <button
          type="button"
          onClick={onRetry}
          className="rounded-sm px-3.5 py-1.5 text-body-sm text-text-secondary hover:bg-bg-subtle transition-colors focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2 outline-none"
        >
          Try again
        </button>
      </div>
    );
  }

  if (status === "rate_limited") {
    return (
      <div className="mt-6 rounded-md border border-warning bg-warning-subtle p-5 text-center">
        <p className="text-body-sm text-text-primary">
          {errorMessage ?? "You're searching faster than we can keep up."}
          {retryAfterSeconds != null && ` Try again in ${retryAfterSeconds}s.`}
        </p>
      </div>
    );
  }

  if (status === "upgrade_required") {
    // The global upgrade modal (Step 1's store, Step 5's real consumer) is
    // the actual UI for this state — nothing else to render inline here.
    return null;
  }

  const isWaiting = status === "submitting";
  const isStreaming = status === "streaming";
  const showActions = status === "complete";

  return (
    <div
      ref={containerRef}
      onScroll={handleScroll}
      aria-live="polite"
      aria-busy={isWaiting || isStreaming}
      className="mt-6 min-h-[120px] max-h-[50vh] overflow-y-auto rounded-md border border-border-default bg-bg-elevated p-5 sm:p-6"
    >
      {isWaiting && !text && <ThinkingIndicator />}

      {(text || isStreaming) && (
        <p className="text-body text-text-primary leading-relaxed whitespace-pre-wrap">
          {text}
          {isStreaming && (
            <span className="inline-block w-[2px] h-[1em] align-middle ml-0.5 bg-accent animate-pulse" />
          )}
        </p>
      )}

      {showActions && sources.length > 0 && (
        <p className="mt-4 flex items-center gap-1.5 text-caption text-text-muted">
          <Landmark className="h-3 w-3 shrink-0" />
          Sourced from real public records: {formatSourceLabels(sources)}
        </p>
      )}

      {showActions && memorySnippets.length > 0 && (
        <p className="mt-1.5 flex items-center gap-1.5 text-caption text-text-muted">
          <BrainCircuit className="h-3 w-3 shrink-0" />
          Memory referenced: {memorySnippets.join(", ")}
        </p>
      )}

      {showActions && (
        <div className="mt-5 flex items-center gap-2 border-t border-border-default pt-4">
          <button
            type="button"
            onClick={handleCopy}
            className="flex items-center gap-1.5 rounded-sm px-2.5 py-1.5 text-body-sm text-text-secondary hover:bg-bg-subtle hover:text-text-primary transition-colors focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2 outline-none"
          >
            {copied ? <Check className="h-3.5 w-3.5" /> : <Copy className="h-3.5 w-3.5" />}
            {copied ? "Copied" : "Copy"}
          </button>
          <button
            type="button"
            onClick={onRetry}
            className="flex items-center gap-1.5 rounded-sm px-2.5 py-1.5 text-body-sm text-text-secondary hover:bg-bg-subtle hover:text-text-primary transition-colors focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2 outline-none"
          >
            <RotateCcw className="h-3.5 w-3.5" />
            {retryLabel}
          </button>
          <button
            type="button"
            onClick={() => openUpgradeModal("advanced_export")}
            className="flex items-center gap-1.5 rounded-sm px-2.5 py-1.5 text-body-sm text-text-muted hover:bg-bg-subtle transition-colors focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2 outline-none ml-auto"
          >
            {tier !== "pro" && <Lock className="h-3.5 w-3.5" />}
            Advanced export
          </button>
        </div>
      )}
    </div>
  );
}
