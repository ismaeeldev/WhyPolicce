"use client";

import { BrainCircuit, Check, Copy, Lock, RotateCcw } from "lucide-react";
import { useEffect, useRef, useState } from "react";

import { useUpgradeModalStore } from "@/stores/useUpgradeModalStore";

import type { StreamStatus } from "@/hooks/useSearchStream";

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
      {isWaiting && !text && (
        <div className="flex items-center gap-2">
          <span className="relative flex h-2 w-2">
            <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-accent opacity-40" />
            <span className="relative inline-flex h-2 w-2 rounded-full bg-accent" />
          </span>
          <p className="text-body-sm text-text-secondary">Thinking…</p>
        </div>
      )}

      {(text || isStreaming) && (
        <p className="text-body text-text-primary leading-relaxed whitespace-pre-wrap">
          {text}
          {isStreaming && (
            <span className="inline-block w-[2px] h-[1em] align-middle ml-0.5 bg-accent animate-pulse" />
          )}
        </p>
      )}

      {showActions && memorySnippets.length > 0 && (
        <p className="mt-4 flex items-center gap-1.5 text-caption text-text-muted">
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
