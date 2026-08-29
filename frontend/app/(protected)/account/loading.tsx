import { Skeleton } from "@/components/ui/skeleton";

/**
 * Account page skeleton — AgentGuide/01_ThemeGuideline.md §4.9. Matches the
 * real account/page.tsx layout exactly — page heading, avatar row, tier
 * card, two link rows, logout line — so the loading -> loaded swap has zero
 * shift. Re-matched during the UI modernization pass that added the
 * heading and py-16/20 spacing to the real page.
 */
export default function AccountLoading() {
  return (
    <div className="mx-auto max-w-[560px] px-6 py-16 sm:py-20">
      <Skeleton className="h-8 w-28 mb-8" />
      <div className="flex items-center gap-4">
        <Skeleton className="h-16 w-16 rounded-full" />
        <div className="space-y-2">
          <Skeleton className="h-5 w-40" />
          <Skeleton className="h-4 w-28" />
        </div>
      </div>
      <Skeleton className="mt-6 h-[86px] w-full rounded-md" />
      <div className="mt-3 flex flex-col gap-2">
        <Skeleton className="h-[46px] w-full rounded-sm" />
        <Skeleton className="h-[46px] w-full rounded-sm" />
      </div>
      <Skeleton className="mt-8 h-4 w-16 mx-auto" />
    </div>
  );
}
