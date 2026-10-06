import { Skeleton } from "@/components/ui/skeleton";

/**
 * Header + card-list skeleton shared by the list-style portals
 * (/account/my-inquiries, /attorneys/dashboard) — used by their route
 * loading.tsx AND the page's own loading branch so the two stages render
 * identically instead of flashing different placeholders.
 */
export function ListPageSkeleton() {
  return (
    <div className="mx-auto w-full max-w-[1200px] px-5 sm:px-6 py-8 sm:py-12">
      <div className="mx-auto max-w-[760px]">
        <div className="mb-8 border-b border-border-default/60 pb-6 space-y-3">
          <Skeleton className="h-5 w-32 rounded-full" />
          <Skeleton className="h-9 w-56" />
          <Skeleton className="h-4 w-72 max-w-full" />
        </div>
        <div className="flex flex-col gap-4">
          {Array.from({ length: 3 }).map((_, i) => (
            <div key={i} className="rounded-xl border border-border-default/60 bg-bg-elevated p-6 space-y-3">
              <div className="flex justify-between">
                <Skeleton className="h-5 w-28" />
                <Skeleton className="h-4 w-10" />
              </div>
              <Skeleton className="h-6 w-3/4" />
              <Skeleton className="h-4 w-full" />
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
