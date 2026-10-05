"use client";

import { FeedEmptyStateNoOwnInquiries } from "@/components/feed/FeedEmptyState";
import { InquiryCard } from "@/components/feed/InquiryCard";
import { useMyInquiries } from "@/hooks/useInquiries";

/**
 * "My Inquiries" — a citizen's own posts, real gap the user reported:
 * there was no dedicated place to see just your own inquiries, only the
 * full nationwide feed. Reuses the main feed's own InquiryCard and
 * loading/error/empty-state conventions (app/page.tsx) rather than
 * inventing a second card design for the same content shape. Lives
 * under /account/* so it inherits proxy.ts's existing auth guard on
 * that whole prefix — no new route-protection entry needed.
 *
 * View/edit/delete happens on the existing thread page (click through,
 * same as the main feed) rather than inline on this list — the thread
 * page's InquiryEditDeleteControls is already built specifically for
 * that context (its delete redirects to "/", its edit toggles an
 * inline form on that same page); duplicating a second, list-context
 * version would fork behavior for no real benefit here.
 */
import Link from "next/link";
import { Plus, Sparkles } from "lucide-react";

export default function MyInquiriesPage() {
  const query = useMyInquiries();

  const allItems = query.data?.pages.flatMap((page) => page.items) ?? [];
  const total = query.data?.pages[0]?.total ?? 0;

  return (
    <div className="mx-auto w-full max-w-[1200px] px-5 sm:px-6 py-8 sm:py-12">
      <div className="mx-auto max-w-[760px]">
        <div className="mb-8 flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-border-default/60 pb-6">
          <div>
            <div className="inline-flex items-center gap-2 rounded-full border border-accent/20 bg-accent-subtle/50 px-3 py-0.5 text-caption font-medium text-accent-bright mb-2">
              <Sparkles className="h-3 w-3 text-accent" />
              <span>Personal Ledger</span>
            </div>
            <h1 className="font-display text-h1 text-text-primary tracking-tight">My Inquiries</h1>
            <p className="mt-1 text-body-sm text-text-secondary">
              Review, manage, and track community and legal responses to your posts.
            </p>
          </div>
          <Link
            href="/inquiries/new"
            className="inline-flex items-center justify-center gap-2 rounded-xl bg-accent px-4 py-2.5 text-body-sm font-semibold text-accent-foreground transition-all duration-200 hover:bg-accent-hover hover:shadow-md shrink-0 focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2 outline-none"
          >
            <Plus className="h-4 w-4" />
            <span>New Inquiry</span>
          </Link>
        </div>

        <div className="flex flex-col gap-4">
          {query.isError && (
            <div className="rounded-md border border-danger bg-danger-subtle p-5 text-center">
              <p className="text-body-sm text-text-primary mb-3">
                Your inquiries didn&apos;t load — that&apos;s on us, not you.
              </p>
              <button
                type="button"
                onClick={() => query.refetch()}
                className="rounded-sm px-4 py-2 text-body-sm font-medium text-text-primary hover:bg-bg-subtle transition-colors focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2 outline-none"
              >
                Try again
              </button>
            </div>
          )}

          {query.isLoading && (
            <div className="flex flex-col gap-4" role="status" aria-label="Loading your inquiries">
              {Array.from({ length: 3 }).map((_, i) => (
                <div key={i} className="rounded-md border border-border-default bg-bg-elevated p-4 sm:p-6 animate-pulse">
                  <div className="h-5 w-32 rounded-full bg-bg-subtle" />
                  <div className="mt-3 h-5 w-2/3 rounded bg-bg-subtle" />
                  <div className="mt-3 h-4 w-full rounded bg-bg-subtle" />
                </div>
              ))}
            </div>
          )}

          {!query.isError && !query.isLoading && allItems.length === 0 && (
            <FeedEmptyStateNoOwnInquiries />
          )}

          {!query.isLoading &&
            allItems.map((inquiry) => <InquiryCard key={inquiry.id} inquiry={inquiry} />)}

          {query.hasNextPage && (
            <div className="flex justify-center py-2">
              {query.isFetchingNextPage ? (
                <div
                  className="h-8 w-8 animate-spin rounded-full border-2 border-border-default border-t-accent"
                  role="status"
                  aria-label="Loading more"
                />
              ) : (
                <button
                  type="button"
                  onClick={() => query.fetchNextPage()}
                  className="rounded-sm border border-border-strong px-5 py-2.5 text-body-sm font-medium text-text-primary hover:bg-bg-subtle transition-colors focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2 outline-none"
                >
                  Load more
                </button>
              )}
            </div>
          )}

          {!query.hasNextPage && allItems.length > 0 && (
            <p className="py-2 text-center text-caption text-text-muted">
              {total} {total === 1 ? "inquiry" : "inquiries"} total
            </p>
          )}
        </div>
      </div>
    </div>
  );
}
