import { Skeleton } from "@/components/ui/skeleton";

/**
 * Pricing skeleton — AgentGuide/01_ThemeGuideline.md §4.9. Matches
 * PricingCards' real dimensions exactly (same padding, same card count,
 * same feature-row count) so the swap never shifts layout.
 */
export default function PricingLoading() {
  return (
    <div className="px-6 py-20 sm:py-28">
      <div className="mx-auto max-w-[680px] text-center mb-14 space-y-3">
        <Skeleton className="h-10 w-3/4 mx-auto" />
        <Skeleton className="h-5 w-1/2 mx-auto" />
      </div>
      <div className="grid gap-6 sm:grid-cols-2 max-w-[880px] mx-auto">
        {[0, 1].map((i) => (
          <div
            key={i}
            className="rounded-lg border border-border-default bg-bg-elevated p-6 sm:p-8"
          >
            <Skeleton className="h-6 w-1/3 mb-2" />
            <Skeleton className="h-4 w-2/3 mb-6" />
            <Skeleton className="h-9 w-1/2 mb-6" />
            <Skeleton className="h-10 w-full mb-7" />
            <div className="space-y-3">
              {Array.from({ length: 6 }).map((_, j) => (
                <Skeleton key={j} className="h-4 w-full" />
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
