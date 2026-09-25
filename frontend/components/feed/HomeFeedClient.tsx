"use client";

import { useState } from "react";

import { FeedEmptyStateNoInquiries, FeedEmptyStateNoResults } from "@/components/feed/FeedEmptyState";
import { FeedFilterBar } from "@/components/feed/FeedFilterBar";
import { InquiryCard } from "@/components/feed/InquiryCard";
import { useDebouncedValue } from "@/hooks/useDebouncedValue";
import { useInquiries, type InquiriesFilters } from "@/hooks/useInquiries";

const DEFAULT_FILTERS: InquiriesFilters = { region: "", status: "", sort: "newest", q: "" };

/**
 * Home feed's interactive client half — split out of app/page.tsx so the
 * server half can prefetch the default-filter first page and hand it
 * over already-hydrated (see app/page.tsx's own comment for why). This
 * component's own behavior is unchanged from before the split: same
 * filters/search/pagination state, same "Load more" pattern. The
 * server-prefetched data lands in useInquiries' cache under the exact
 * DEFAULT_FILTERS key, so the very first render here reads it from cache
 * (already hydrated, no fetch) rather than issuing a duplicate request —
 * every filter/search change past that point behaves exactly as before.
 */
export function HomeFeedClient() {
  const [searchInput, setSearchInput] = useState("");
  const [filters, setFilters] = useState<InquiriesFilters>(DEFAULT_FILTERS);
  const debouncedSearch = useDebouncedValue(searchInput, 300);

  const query = useInquiries({ ...filters, q: debouncedSearch });

  const handleFiltersChange = (next: Partial<InquiriesFilters>) => {
    setFilters((prev) => ({ ...prev, ...next }));
  };

  const handleClearAll = () => {
    setSearchInput("");
    setFilters(DEFAULT_FILTERS);
  };

  const allItems = query.data?.pages.flatMap((page) => page.items) ?? [];
  const total = query.data?.pages[0]?.total ?? 0;
  const hasAnyFilterOrSearch =
    !!filters.region || !!filters.status || filters.sort !== "newest" || !!debouncedSearch;

  return (
    <>
      <FeedFilterBar
        searchInput={searchInput}
        onSearchInputChange={setSearchInput}
        filters={filters}
        onFiltersChange={handleFiltersChange}
        onClearAll={handleClearAll}
      />

      <div className="mt-6 flex flex-col gap-4">
        {query.isError && (
          <div className="rounded-md border border-danger bg-danger-subtle p-5 text-center">
            <p className="text-body-sm text-text-primary mb-3">
              The feed didn&apos;t load — that&apos;s on us, not you.
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

        {/* Real bug found via live testing, not caught by code review:
            query.isLoading is TanStack Query's "very first load of this
            queryKey" flag — when the debounced search term changes, the
            filters object (and therefore the query key) changes too, so
            this becomes a brand-new query with its own fresh isLoading
            cycle. During that window, allItems is correctly empty (no
            data yet) but isLoading genuinely IS true, which is exactly
            right — the bug was that nothing was ever rendered for that
            state: the empty-state block only handled "done loading,
            zero results," and cards can only render once data exists,
            leaving a real, silent blank gap between clearing the old
            list and the new one arriving. Fixed with an explicit
            isLoading skeleton row so a mid-search fetch is never a
            blank area. */}
        {query.isLoading && (
          <div className="flex flex-col gap-4" role="status" aria-label="Loading inquiries">
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
          hasAnyFilterOrSearch ? (
            <FeedEmptyStateNoResults onClearFilters={handleClearAll} />
          ) : (
            <FeedEmptyStateNoInquiries />
          )
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
    </>
  );
}
