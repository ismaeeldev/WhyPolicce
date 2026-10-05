"use client";

import { useState } from "react";

import { FeedEmptyStateNoInquiries, FeedEmptyStateNoResults } from "@/components/feed/FeedEmptyState";
import { FeedFilterBar } from "@/components/feed/FeedFilterBar";
import { InquiryCard } from "@/components/feed/InquiryCard";
import { HomeSidebar } from "@/components/home/HomeSidebar";
import { useDebouncedValue } from "@/hooks/useDebouncedValue";
import { useInquiries, type InquiriesFilters } from "@/hooks/useInquiries";
import { ApiError } from "@/lib/api-client";

const DEFAULT_FILTERS: InquiriesFilters = { region: "", status: "", sort: "newest", q: "" };

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

  const handleSelectPrecinct = (precinct: string) => {
    setSearchInput(precinct);
  };

  const allItems = query.data?.pages.flatMap((page) => page.items) ?? [];
  const total = query.data?.pages[0]?.total ?? 0;
  const hasAnyFilterOrSearch =
    !!filters.region || !!filters.status || filters.sort !== "newest" || !!debouncedSearch;

  return (
    <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
      {/* Main Feed Column (Left / Center) */}
      <div className="lg:col-span-8 flex flex-col min-w-0">
        <div className="flex items-center justify-between gap-3 mb-4">
          <div>
            <h2 className="font-display text-xl sm:text-2xl font-semibold text-text-primary tracking-tight">
              Recent Community Inquiries
            </h2>
            <p className="text-caption text-text-muted mt-0.5">
              Live public incident reports, community evidence traces, and official statements.
            </p>
          </div>
          {hasAnyFilterOrSearch && (
            <button
              type="button"
              onClick={handleClearAll}
              className="text-[11px] font-mono text-accent hover:underline px-2 py-1 rounded bg-accent/10 border border-accent/20 transition-colors"
            >
              Reset Filters
            </button>
          )}
        </div>

        <FeedFilterBar
          searchInput={searchInput}
          onSearchInputChange={setSearchInput}
          filters={filters}
          onFiltersChange={handleFiltersChange}
          onClearAll={handleClearAll}
        />

        {!query.isError && hasAnyFilterOrSearch && (query.isLoading || allItems.length > 0) && (
          <p className="mt-4 mb-1 font-mono text-caption tabular-nums text-text-muted">
            {query.isLoading ? "Searching…" : `${total} result${total === 1 ? "" : "s"} for your filters`}
          </p>
        )}

        <div className="mt-4 flex flex-col gap-4">
          {query.isError && (
            <div className="rounded-xl border border-danger/60 bg-danger-subtle p-6 text-center shadow-card">
              {query.error instanceof ApiError && query.error.code === "attorney_not_verified" ? (
                <p className="text-body-sm text-text-primary">{query.error.message}</p>
              ) : (
                <>
                  <p className="text-body-sm text-text-primary mb-3">
                    The feed didn&apos;t load — that&apos;s on us, not you.
                  </p>
                  <button
                    type="button"
                    onClick={() => query.refetch()}
                    className="rounded-lg border border-accent/40 bg-accent/10 px-4 py-2 text-body-sm font-medium text-accent hover:bg-accent hover:text-accent-foreground transition-colors outline-none"
                  >
                    Try again
                  </button>
                </>
              )}
            </div>
          )}

          {query.isLoading && (
            <div className="flex flex-col gap-4" role="status" aria-label="Loading inquiries">
              {Array.from({ length: 3 }).map((_, i) => (
                <div key={i} className="rounded-xl border border-border-default/80 bg-bg-elevated p-6 shadow-card animate-pulse">
                  <div className="flex items-center justify-between gap-3 mb-3">
                    <div className="flex items-center gap-2">
                      <div className="h-5 w-24 rounded bg-bg-subtle" />
                      <div className="h-4 w-28 rounded bg-bg-subtle/80" />
                    </div>
                    <div className="h-4 w-8 rounded bg-bg-subtle" />
                  </div>
                  <div className="mt-2 h-6 w-3/4 rounded bg-bg-subtle" />
                  <div className="mt-2 h-4 w-1/3 rounded bg-bg-subtle/60" />
                  <div className="mt-3 space-y-1.5">
                    <div className="h-4 w-full rounded bg-bg-subtle/50" />
                    <div className="h-4 w-4/5 rounded bg-bg-subtle/50" />
                  </div>
                  <div className="mt-4 pt-3 border-t border-border-default/50 flex justify-between">
                    <div className="h-4 w-32 rounded bg-bg-subtle" />
                    <div className="h-7 w-20 rounded bg-bg-subtle" />
                  </div>
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
            allItems.map((inquiry, index) => (
              <InquiryCard
                key={inquiry.id}
                inquiry={inquiry}
                isLatest={index === 0 && !hasAnyFilterOrSearch}
              />
            ))}

          {query.hasNextPage && (
            <div className="flex justify-center py-4">
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
                  className="rounded-lg border border-border-strong bg-bg-elevated px-6 py-2.5 text-body-sm font-medium text-text-primary hover:bg-bg-subtle hover:border-accent/40 transition-colors focus-visible:ring-2 focus-visible:ring-accent outline-none shadow-sm"
                >
                  Load more inquiries
                </button>
              )}
            </div>
          )}

          {!query.hasNextPage && allItems.length > 0 && (
            <p className="py-4 text-center text-caption font-mono text-text-muted">
              ✓ All {total} {total === 1 ? "inquiry" : "inquiries"} loaded
            </p>
          )}
        </div>
      </div>

      {/* Right Column: Sticky Sidebar Widgets (sticks cleanly under navbar) */}
      <div className="lg:col-span-4 sticky top-24 self-start space-y-6">
        <HomeSidebar onSelectPrecinct={handleSelectPrecinct} />
      </div>
    </div>
  );
}
