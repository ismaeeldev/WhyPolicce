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
}: {
  label: string;
  value: string;
  options: { value: string; label: string }[];
  onChange: (value: string) => void;
}) {
  const activeLabel = options.find((o) => o.value === value)?.label ?? label;
  const isActive = value !== options[0]?.value;

  return (
    <DropdownMenu>
      <DropdownMenuTrigger
        render={
          <button
            type="button"
            className={`flex items-center gap-1.5 rounded-sm border px-3.5 py-2 text-body-sm transition-colors focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2 outline-none ${
              isActive
                ? "border-accent bg-accent-subtle text-text-primary"
                : "border-border-default bg-bg-elevated text-text-secondary hover:border-border-strong"
            }`}
          />
        }
      >
        {activeLabel}
        <ChevronDown className="h-3.5 w-3.5" />
      </DropdownMenuTrigger>
      <DropdownMenuContent align="start" className="min-w-40">
        <DropdownMenuRadioGroup value={value} onValueChange={onChange}>
          {options.map((option) => (
            <DropdownMenuRadioItem key={option.value} value={option.value}>
              {option.label}
            </DropdownMenuRadioItem>
          ))}
        </DropdownMenuRadioGroup>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
