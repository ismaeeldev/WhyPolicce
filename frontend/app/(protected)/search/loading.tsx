import { Skeleton } from "@/components/ui/skeleton";

/**
 * Search route skeleton — AgentGuide/02_ApplicationFlow.md §3.3 state 0.
 * Pill-shaped bar skeleton matching the real SearchBar's dimensions exactly,
 * per ThemeGuideline §4.9.
 */
export default function SearchLoading() {
  return (
    <div className="flex flex-1 flex-col items-center px-6 py-16 sm:py-20">
      <div className="w-full max-w-[760px]">
        <Skeleton className="h-14 sm:h-16 w-full rounded-lg" />
        <div className="mt-5 flex flex-wrap justify-center gap-2">
          <Skeleton className="h-8 w-40 rounded-full" />
          <Skeleton className="h-8 w-48 rounded-full" />
          <Skeleton className="h-8 w-36 rounded-full" />
        </div>
      </div>
    </div>
  );
}
