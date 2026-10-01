"use client";

import { useInquiryStats } from "@/hooks/useInquiries";

/**
 * Home page stats strip — Scope Revision 3 follow-up. Real gap found
 * during a fresh deep audit: the client's own ask was "the homepage
 * should look like a home page," but the page as shipped was still just
 * a title followed immediately by a bare feed list, with nothing
 * establishing scale or trust before the raw records — the one thing
 * that reads as distinctly "home page" rather than "listing page."
 *
 * Real numbers from GET /api/v1/inquiries/stats, never placeholders —
 * server-prefetched in app/page.tsx the same way the feed itself is, so
 * this renders with real data on first paint, not a loading flash.
 * isLoading only ever shows for a client-side re-render (e.g. after a
 * cache invalidation), never the initial server-rendered load.
 *
 * Deliberately only 2 stats, not 3: a "Verified Attorneys" count was
 * cut after a fresh review — the backend's own number is real and
 * honest, but this early, a small raw count (e.g. single digits) would
 * undersell a platform explicitly pitching itself as a "high-trust"
 * attorney network, working against the client's own stated goal
 * rather than for it. Records/states are both large, genuinely
 * impressive numbers from day one — this strip only shows what's
 * actually flattering, rather than filling a third slot with a weak
 * one just to make a row of three.
 */
export function StatsStrip() {
  const { data, isLoading } = useInquiryStats();

  const items: { label: string; value: string }[] = [
    { label: "Records tracked", value: isLoading || !data ? "—" : data.totalRecords.toLocaleString() },
    { label: "States covered", value: isLoading || !data ? "—" : data.totalStates.toLocaleString() },
  ];

  // Real, honest affordance, not a fake-looking one: clicking either
  // stat scrolls straight to the feed below — the actual records these
  // numbers describe. Simpler and more truthful than routing to a
  // filtered view this strip doesn't actually control.
  const scrollToFeed = () => {
    document.querySelector('[data-testid="inquiry-card"]')?.scrollIntoView({ behavior: "smooth", block: "start" });
  };

  return (
    <div className="mt-8 grid grid-cols-2 divide-x divide-border-default rounded-lg border border-border-default bg-bg-elevated shadow-card">
      {items.map((item) => (
        <button
          key={item.label}
          type="button"
          onClick={scrollToFeed}
          className="flex flex-col items-center gap-1 px-3 py-4 text-center transition-colors hover:bg-bg-subtle focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-inset outline-none sm:px-4"
        >
          <span className="font-display text-h2 tabular-nums text-text-primary">{item.value}</span>
          <span className="font-mono text-caption uppercase tracking-[0.08em] text-text-muted">
            {item.label}
          </span>
        </button>
      ))}
    </div>
  );
}
