"use client";

import { Search, X } from "lucide-react";
import { useState } from "react";

import { FilterDropdown } from "@/components/feed/FilterDropdown";
import { Sheet, SheetClose, SheetContent, SheetHeader, SheetTitle } from "@/components/ui/sheet";
import { US_STATES } from "@/lib/us-states";
import type { InquiriesFilters } from "@/hooks/useInquiries";

const STATUS_OPTIONS = [
  { value: "", label: "All statuses" },
  { value: "community_trace", label: "Community Trace" },
  { value: "awaiting_police_statement", label: "Awaiting Police Statement" },
];

const SORT_OPTIONS = [
  { value: "newest", label: "Newest" },
  { value: "most_followed", label: "Most Followed" },
];

const REGION_OPTIONS = [
  { value: "", label: "All states" },
  ...US_STATES.map((s) => ({ value: s.code, label: s.name })),
];

/**
 * Feed search/filter bar — forum rebuild, Milestone 2 Step M2.2
 * (WhyPoliceForum_MasterGuide.md). Text input placeholder matches the
 * client's own reference mockup verbatim. At 375px the three dropdowns
 * collapse into a single "Filters" sheet rather than overflowing
 * horizontally (tested explicitly, not just "shrinks and hope").
 */
export function FeedFilterBar({
  searchInput,
  onSearchInputChange,
  filters,
  onFiltersChange,
  onClearAll,
}: {
  searchInput: string;
  onSearchInputChange: (value: string) => void;
  filters: InquiriesFilters;
  onFiltersChange: (next: Partial<InquiriesFilters>) => void;
  onClearAll: () => void;
}) {
  const [mobileFiltersOpen, setMobileFiltersOpen] = useState(false);

  const hasActiveFilters =
    !!filters.region || !!filters.status || filters.sort !== "newest" || !!searchInput;

  return (
    <div className="flex flex-col gap-3">
      <div className="flex items-center gap-2">
        <div className="relative flex-1 min-w-0">
          <Search
            aria-hidden="true"
            className="pointer-events-none absolute left-4 top-1/2 -translate-y-1/2 h-4 w-4 text-text-muted"
          />
          <input
            type="text"
            value={searchInput}
            onChange={(e) => onSearchInputChange(e.target.value)}
            aria-label="Search inquiries"
            placeholder="Search state, city, precinct, or incident keyword..."
            className="h-12 w-full min-w-0 rounded-lg border border-border-default bg-bg-elevated pl-11 pr-4 text-body text-text-primary shadow-card outline-none transition-colors focus:border-accent placeholder:text-text-muted"
          />
        </div>

        {/* Desktop: three inline dropdowns. Mobile: single "Filters" sheet trigger. */}
        <div className="hidden md:flex items-center gap-2">
          <FilterDropdown
            label="Region"
            value={filters.region}
            options={REGION_OPTIONS}
            onChange={(region) => onFiltersChange({ region })}
          />
          <FilterDropdown
            label="Status"
            value={filters.status}
            options={STATUS_OPTIONS}
            onChange={(status) => onFiltersChange({ status })}
          />
          <FilterDropdown
            label="Sort"
            value={filters.sort}
            options={SORT_OPTIONS}
            onChange={(sort) => onFiltersChange({ sort: sort as InquiriesFilters["sort"] })}
          />
        </div>

        <button
          type="button"
          onClick={() => setMobileFiltersOpen(true)}
          className="md:hidden flex h-12 items-center gap-1.5 rounded-lg border border-border-default bg-bg-elevated px-4 text-body-sm text-text-secondary shrink-0 focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2 outline-none"
        >
          Filters
          {hasActiveFilters && <span className="h-1.5 w-1.5 rounded-full bg-accent" />}
        </button>
      </div>

      {hasActiveFilters && (
        <div className="flex flex-wrap items-center gap-2">
          {searchInput && (
            <FilterChip label={`"${searchInput}"`} onClear={() => onSearchInputChange("")} />
          )}
          {filters.region && (
            <FilterChip
              label={REGION_OPTIONS.find((o) => o.value === filters.region)?.label ?? filters.region}
              onClear={() => onFiltersChange({ region: "" })}
            />
          )}
          {filters.status && (
            <FilterChip
              label={STATUS_OPTIONS.find((o) => o.value === filters.status)?.label ?? filters.status}
              onClear={() => onFiltersChange({ status: "" })}
            />
          )}
          {filters.sort !== "newest" && (
            <FilterChip label="Most Followed" onClear={() => onFiltersChange({ sort: "newest" })} />
          )}
          <button
            type="button"
            onClick={onClearAll}
            className="text-caption text-text-muted hover:text-text-primary transition-colors rounded-sm focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2 outline-none"
          >
            Clear all
          </button>
        </div>
      )}

      <Sheet open={mobileFiltersOpen} onOpenChange={setMobileFiltersOpen}>
        <SheetContent side="top" className="bg-bg border-border-default">
          <SheetHeader>
            <SheetTitle className="font-display text-lg">Filters</SheetTitle>
          </SheetHeader>
          <div className="flex flex-col gap-4 px-4 pb-4">
            <MobileFilterSelect
              label="Region"
              value={filters.region}
              options={REGION_OPTIONS}
              onChange={(region) => onFiltersChange({ region })}
            />
            <MobileFilterSelect
              label="Status"
              value={filters.status}
              options={STATUS_OPTIONS}
              onChange={(status) => onFiltersChange({ status })}
            />
            <MobileFilterSelect
              label="Sort"
              value={filters.sort}
              options={SORT_OPTIONS}
              onChange={(sort) => onFiltersChange({ sort: sort as InquiriesFilters["sort"] })}
            />
            <SheetClose
              render={
                <button
                  type="button"
                  className="mt-2 rounded-sm bg-accent px-4 py-2.5 text-body-sm font-medium text-accent-foreground hover:bg-accent-hover transition-colors focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2 outline-none"
                />
              }
            >
              Apply
            </SheetClose>
          </div>
        </SheetContent>
      </Sheet>
    </div>
  );
}

function FilterChip({ label, onClear }: { label: string; onClear: () => void }) {
  return (
    <span className="inline-flex items-center gap-1 rounded-full bg-accent-subtle px-2.5 py-1 text-caption text-text-primary">
      {label}
      <button
        type="button"
        onClick={onClear}
        aria-label={`Remove ${label} filter`}
        className="rounded-full hover:bg-accent/20 focus-visible:ring-2 focus-visible:ring-accent outline-none"
      >
        <X className="h-3 w-3" />
      </button>
    </span>
  );
}

function MobileFilterSelect({
  label,
  value,
  options,
  onChange,
}: {
  label: string;
  value: string;
  options: { value: string; label: string }[];
  onChange: (value: string) => void;
}) {
  return (
    <label className="flex flex-col gap-1.5">
      <span className="text-body-sm text-text-secondary">{label}</span>
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="h-11 rounded-sm border border-border-default bg-bg-elevated px-3 text-body text-text-primary outline-none focus:border-accent"
      >
        {options.map((option) => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </select>
    </label>
  );
}
