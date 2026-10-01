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
 */
export function StatsStrip() {
  const { data, isLoading } = useInquiryStats();

  const items: { label: string; value: string }[] = [
    { label: "Records tracked", value: isLoading || !data ? "—" : data.totalRecords.toLocaleString() },
    { label: "States covered", value: isLoading || !data ? "—" : data.totalStates.toLocaleString() },
    { label: "Verified attorneys", value: isLoading || !data ? "—" : data.verifiedAttorneys.toLocaleString() },
  ];

  return (
    <div className="mt-8 grid grid-cols-3 divide-x divide-border-default rounded-lg border border-border-default bg-bg-elevated shadow-card">
      {items.map((item) => (
        <div key={item.label} className="flex flex-col items-center gap-1 px-3 py-4 text-center sm:px-4">
          <span className="font-display text-h2 tabular-nums text-text-primary">{item.value}</span>
          <span className="font-mono text-caption uppercase tracking-[0.08em] text-text-muted">
            {item.label}
          </span>
        </div>
      ))}
    </div>
  );
}
