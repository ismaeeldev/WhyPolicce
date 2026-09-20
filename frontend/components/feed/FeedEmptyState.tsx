import { FileSearch, MessageCirclePlus } from "lucide-react";
import Link from "next/link";

/**
 * Feed empty states — forum rebuild, Milestone 2 Step M2.2
 * (WhyPoliceForum_MasterGuide.md). Two genuinely different cases, written
 * separately per Standing UI Discipline rule 8: an empty feed overall
 * (invites the first post) vs. filters/search matching nothing (invites
 * clearing filters) — never one generic "nothing here" string for both.
 */
export function FeedEmptyStateNoInquiries() {
  return (
    <div className="flex flex-col items-center gap-3 rounded-md border border-dashed border-border-strong bg-bg-elevated py-16 text-center px-6">
      <MessageCirclePlus className="h-8 w-8 text-text-muted" strokeWidth={1.5} />
      <p className="text-body font-medium text-text-primary">Be the first to post here</p>
      <p className="max-w-sm text-body-sm text-text-secondary">
        No inquiries have been shared yet. Start the conversation with the first one.
      </p>
      <Link
        href="/inquiries/new"
        className="mt-2 rounded-sm bg-accent px-4 py-2 text-body-sm font-medium text-accent-foreground hover:bg-accent-hover transition-colors focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2 outline-none"
      >
        Post the first inquiry
      </Link>
    </div>
  );
}

export function FeedEmptyStateNoResults({ onClearFilters }: { onClearFilters: () => void }) {
  return (
    <div className="flex flex-col items-center gap-3 rounded-md border border-dashed border-border-strong bg-bg-elevated py-16 text-center px-6">
      <FileSearch className="h-8 w-8 text-text-muted" strokeWidth={1.5} />
      <p className="text-body font-medium text-text-primary">No matches for these filters</p>
      <p className="max-w-sm text-body-sm text-text-secondary">
        Try a different search term or clear your filters to see everything.
      </p>
      <button
        type="button"
        onClick={onClearFilters}
        className="mt-2 rounded-sm border border-border-strong px-4 py-2 text-body-sm font-medium text-text-primary hover:bg-bg-subtle transition-colors focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2 outline-none"
      >
        Clear filters
      </button>
    </div>
  );
}
