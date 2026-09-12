import { Skeleton } from "@/components/ui/skeleton";

/**
 * Session detail skeleton — AgentGuide/01_ThemeGuideline.md §4.9: alternating
 * short/long text-line bars mimicking Q&A rhythm, not a generic gray box.
 */
export default function SessionDetailLoading() {
  return (
    <div className="mx-auto w-full min-w-0 max-w-[760px] px-5 sm:px-6 py-12 sm:py-16">
      <Skeleton className="h-4 w-28 mb-6" />
      <Skeleton className="h-8 w-2/3 mb-8" />

      <div className="flex flex-col gap-10">
        {[0, 1].map((i) => (
          <div key={i}>
            <Skeleton className="h-6 w-1/2 mb-4" />
            <div className="rounded-md border border-border-default bg-bg-elevated p-5 sm:p-6 space-y-2">
              <Skeleton className="h-4 w-full" />
              <Skeleton className="h-4 w-4/5" />
              <Skeleton className="h-4 w-3/5" />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
