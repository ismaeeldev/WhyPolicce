import { Skeleton } from "@/components/ui/skeleton";

/**
 * History route skeleton — AgentGuide/01_ThemeGuideline.md §4.9. 4-6 card
 * skeletons matching SessionCard's exact padding/radius so the loading ->
 * loaded swap has zero layout shift.
 */
export default function HistoryLoading() {
  return (
    <div className="mx-auto max-w-[760px] px-6 py-12 sm:py-16">
      <div className="mb-8 flex items-center justify-between">
        <Skeleton className="h-8 w-32" />
        <Skeleton className="h-9 w-28 rounded-sm" />
      </div>
      <div className="flex flex-col gap-3">
        {Array.from({ length: 5 }).map((_, i) => (
          <div
            key={i}
            className="rounded-md border border-border-default bg-bg-elevated p-4 sm:p-6"
          >
            <Skeleton className="h-5 w-3/4" />
            <Skeleton className="mt-3 h-4 w-20" />
          </div>
        ))}
      </div>
    </div>
  );
}
