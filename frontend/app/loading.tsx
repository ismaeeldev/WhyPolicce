import { Skeleton } from "@/components/ui/skeleton";

/**
 * Home feed route-level skeleton — forum rebuild, Milestone 2 Step M2.2
 * (WhyPoliceForum_MasterGuide.md), AgentGuide/01_ThemeGuideline.md §4.9/§9.
 * 4-6 card-shaped skeletons matching InquiryCard's exact real dimensions
 * (rounded-md border border-border-default bg-bg-elevated p-4 sm:p-6),
 * never a bare spinner or blank white flash.
 */
export default function HomeFeedLoading() {
  return (
    <div className="mx-auto w-full max-w-[1200px] px-5 sm:px-6 py-8 sm:py-12">
      <div className="mx-auto max-w-[760px]">
        <Skeleton className="h-9 w-48 mb-6" />

        <div className="flex items-center gap-2">
          <Skeleton className="h-12 flex-1 rounded-lg" />
          <Skeleton className="hidden md:block h-9 w-28 rounded-sm" />
          <Skeleton className="hidden md:block h-9 w-24 rounded-sm" />
          <Skeleton className="hidden md:block h-9 w-24 rounded-sm" />
          <Skeleton className="md:hidden h-12 w-20 rounded-lg" />
        </div>

        <div className="mt-6 flex flex-col gap-4">
          {Array.from({ length: 5 }).map((_, i) => (
            <div key={i} className="rounded-md border border-border-default bg-bg-elevated p-4 sm:p-6">
              <div className="flex items-center justify-between">
                <Skeleton className="h-5 w-40 rounded-full" />
                <Skeleton className="h-4 w-8" />
              </div>
              <Skeleton className="mt-3 h-5 w-3/4" />
              <Skeleton className="mt-2 h-3.5 w-1/2" />
              <Skeleton className="mt-3 h-4 w-full" />
              <Skeleton className="mt-1.5 h-4 w-5/6" />
              <div className="mt-4 flex items-center justify-between">
                <Skeleton className="h-4 w-32" />
                <Skeleton className="h-8 w-24 rounded-sm" />
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
