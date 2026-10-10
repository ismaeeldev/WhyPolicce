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
    <div className="w-full animate-pulse">
      {/* Hero Full Bleed Skeleton */}
      <div className="w-full -mt-20 pt-24 sm:pt-28 pb-14 sm:pb-20 border-b border-border-default/60 bg-[#060605]">
        <div className="mx-auto w-full max-w-[1400px] px-4 sm:px-6 lg:px-8">
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-10 items-center">
            <div className="lg:col-span-7 space-y-4">
              <Skeleton className="h-6 w-44 rounded-full bg-bg-subtle" />
              <Skeleton className="h-12 w-4/5 rounded-md bg-bg-subtle" />
              <Skeleton className="h-12 w-3/5 rounded-md bg-bg-subtle" />
              <Skeleton className="h-5 w-full max-w-lg rounded bg-bg-subtle/80" />
              <div className="pt-4 flex gap-6">
                <Skeleton className="h-12 w-36 rounded-md bg-bg-subtle" />
                <Skeleton className="h-12 w-36 rounded-md bg-bg-subtle" />
                <Skeleton className="h-12 w-36 rounded-md bg-bg-subtle" />
              </div>
            </div>
            <div className="hidden lg:flex lg:col-span-5 justify-end">
              <Skeleton className="h-44 w-72 rounded-xl bg-bg-subtle/60" />
            </div>
          </div>
        </div>
      </div>

      {/* Main Page Content Skeleton */}
      <div className="mx-auto w-full max-w-[1400px] px-4 sm:px-6 lg:px-8 py-8 sm:py-10 space-y-8">
        {/* 4-Tile Bento Grid Skeleton */}
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-4 sm:gap-5">
          {Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="rounded-xl border border-border-default/60 bg-bg-elevated p-5 space-y-3">
              <div className="flex justify-between items-center">
                <Skeleton className="h-5 w-32 rounded bg-bg-subtle" />
                <Skeleton className="h-4 w-12 rounded bg-bg-subtle" />
              </div>
              <Skeleton className="h-28 w-full rounded-lg bg-bg-subtle/70" />
              <div className="flex justify-between pt-2 border-t border-border-default/40">
                <Skeleton className="h-4 w-16 rounded bg-bg-subtle" />
                <Skeleton className="h-4 w-16 rounded bg-bg-subtle" />
              </div>
            </div>
          ))}
        </div>

        {/* Feed & Sidebar Skeleton */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start pt-2">
          <div className="lg:col-span-8 space-y-4">
            <div className="flex justify-between items-center">
              <Skeleton className="h-7 w-56 rounded bg-bg-subtle" />
              <Skeleton className="h-5 w-20 rounded bg-bg-subtle" />
            </div>
            <Skeleton className="h-12 w-full rounded-lg bg-bg-subtle" />
            <div className="space-y-4 pt-2">
              {Array.from({ length: 3 }).map((_, i) => (
                <div key={i} className="rounded-xl border border-border-default/60 bg-bg-elevated p-6 space-y-3">
                  <div className="flex justify-between">
                    <Skeleton className="h-5 w-28 rounded bg-bg-subtle" />
                    <Skeleton className="h-4 w-10 rounded bg-bg-subtle" />
                  </div>
                  <Skeleton className="h-6 w-3/4 rounded bg-bg-subtle" />
                  <Skeleton className="h-4 w-full rounded bg-bg-subtle/70" />
                </div>
              ))}
            </div>
          </div>
          <div className="lg:col-span-4 space-y-6">
            <div className="rounded-xl border border-border-default/60 bg-bg-elevated p-6 space-y-4">
              <Skeleton className="h-5 w-36 rounded bg-bg-subtle" />
              <Skeleton className="h-16 w-full rounded-lg bg-bg-subtle" />
              <Skeleton className="h-10 w-full rounded-md bg-bg-subtle" />
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
