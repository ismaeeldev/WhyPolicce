"use client";

import { StatusPill, type StatusTag } from "@/components/feed/StatusPill";

const OPTIONS: { value: StatusTag; label: string }[] = [
  { value: "community_trace", label: "Community Trace" },
  { value: "awaiting_police_statement", label: "Awaiting Police Statement" },
];

/**
 * Status tag selector — forum rebuild, Milestone 2 Step M2.3
 * (WhyPoliceForum_MasterGuide.md). Reuses the exact same StatusPill
 * component the feed cards render (M2.2), so a citizen picking a status
 * here sees the identical labels/colors they'll recognize from the feed —
 * per this step's own explicit "using identical labels/colors" requirement,
 * not a second, differently-styled status control.
 */
export function StatusTagSelector({
  value,
  onChange,
}: {
  value: StatusTag | null;
  onChange: (value: StatusTag) => void;
}) {
  return (
    <div>
      <span className="mb-1.5 block text-body-sm text-text-secondary">Status</span>
      <div className="flex flex-wrap gap-2">
        {OPTIONS.map((option) => (
          <button
            key={option.value}
            type="button"
            onClick={() => onChange(option.value)}
            aria-pressed={value === option.value}
            className={`rounded-full transition-all focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2 outline-none ${
              value === option.value ? "ring-2 ring-accent ring-offset-2 ring-offset-bg" : "opacity-70 hover:opacity-100"
            }`}
          >
            <StatusPill status={option.value} />
          </button>
        ))}
      </div>
    </div>
  );
}
