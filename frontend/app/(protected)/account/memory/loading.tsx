import { Skeleton } from "@/components/ui/skeleton";

/**
 * Memory route skeleton — AgentGuide/01_ThemeGuideline.md §4.9. A few short
 * skeleton lines matching the note-card shape, per Step 6.5.
 */
export default function MemoryLoading() {
  return (
    <div className="mx-auto w-full min-w-0 max-w-[760px] px-5 sm:px-6 py-12 sm:py-16">
      <div className="mb-8 flex items-center justify-between">
        <div>
          <Skeleton className="h-8 w-28" />
          <Skeleton className="mt-2 h-4 w-56" />
        </div>
        <Skeleton className="h-9 w-28 rounded-sm" />
      </div>
      <div className="flex flex-col gap-3">
        {Array.from({ length: 3 }).map((_, i) => (
          <div key={i} className="rounded-md border border-border-default bg-bg-elevated p-4 sm:p-6">
            <Skeleton className="h-4 w-full" />
            <Skeleton className="mt-2 h-4 w-2/3" />
          </div>
        ))}
      </div>
    </div>
  );
}
