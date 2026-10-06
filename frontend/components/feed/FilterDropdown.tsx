"use client";

import { ChevronDown } from "lucide-react";

import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuRadioGroup,
  DropdownMenuRadioItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";

/**
 * Region/Status/Sort filter dropdown — forum rebuild, Milestone 2 Step
 * M2.2 (WhyPoliceForum_MasterGuide.md). No dedicated Select component
 * exists in this codebase yet, so this is built on the existing
 * DropdownMenu primitive's radio-group mode, styled per ThemeGuideline's
 * dropdown spec (--bg-elevated, --border, --radius-sm, --text-secondary
 * default, hover --border-strong).
 *
 * Standing UI Discipline rule 11 (active-filter indication): the
 * currently-applied option is shown directly in the closed trigger's own
 * label, not just reflected in URL/query state.
 */
export function FilterDropdown({
  label,
  value,
  options,
  onChange,
  renderOptionPrefix,
}: {
  label: string;
  value: string;
  options: { value: string; label: string }[];
  onChange: (value: string) => void;
  /** Optional per-option marker (e.g. the status color dot) rendered before the label. */
  renderOptionPrefix?: (optionValue: string) => React.ReactNode;
}) {
  const activeLabel = options.find((o) => o.value === value)?.label ?? label;
  const isActive = value !== options[0]?.value;

  return (
    <DropdownMenu>
      <DropdownMenuTrigger
        render={
          <button
            type="button"
            className={`flex h-12 items-center gap-1.5 rounded-lg border px-3.5 text-body-sm shadow-card transition-all duration-150 ease-out focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2 outline-none ${
              isActive
                ? "border-accent bg-accent-subtle text-text-primary hover:bg-accent-subtle/80"
                : "border-border-default bg-bg-elevated text-text-secondary hover:border-border-strong hover:bg-bg-subtle"
            }`}
          />
        }
      >
        {/* Monospace field label + value, echoing the record cards' own
            date/counter typography (InquiryCard.tsx, HomeFeedClient.tsx)
            so the filter bar reads as part of the same "ledger" system
            rather than a generic dropdown pill — a real, deliberate tie
            to the client's own "structured record" framing, not just
            decoration. */}
        <span className="font-mono text-caption uppercase tracking-[0.08em] text-text-muted">
          {label}
        </span>
        <span className="max-w-[12ch] truncate">{activeLabel}</span>
        <ChevronDown className="h-3.5 w-3.5 shrink-0" />
      </DropdownMenuTrigger>
      <DropdownMenuContent
        align="start"
        side="bottom"
        sideOffset={6}
        // Always open directly below the trigger (never flip over it): the list
        // shrinks to the space available and scrolls instead.
        collisionAvoidance={{ side: "none", align: "shift" }}
        className="wp-filter-dropdown-panel w-max min-w-40 max-w-[min(90vw,320px)] max-h-[min(350px,var(--available-height))] overflow-y-auto"
      >
        <DropdownMenuRadioGroup value={value} onValueChange={onChange}>
          {options.map((option) => (
            <DropdownMenuRadioItem key={option.value} value={option.value} className="whitespace-nowrap">
              {renderOptionPrefix?.(option.value)}
              {option.label}
            </DropdownMenuRadioItem>
          ))}
        </DropdownMenuRadioGroup>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
