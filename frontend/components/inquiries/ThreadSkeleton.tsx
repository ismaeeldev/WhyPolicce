import { Skeleton } from "@/components/ui/skeleton";

/**
 * Inquiry thread skeleton. Shared by app/inquiries/[id]/loading.tsx (route
 * level) and the page's own data-loading state so both stages render the
 * exact same placeholder — otherwise Next falls back to the root
 * app/loading.tsx (the home-page skeleton) first, then this one swaps in.
 * Sized close to the real layout, including comment-row placeholders, so
 * the final swap doesn't shift the page.
 */
export function ThreadSkeleton() {
  return (
    <div className="mx-auto w-full max-w-[760px] px-5 sm:px-6 py-12 sm:py-16">
      <div className="rounded-md border border-border-default bg-bg-elevated p-4 sm:p-6">
        <Skeleton className="h-5 w-32 rounded-full" />
        <Skeleton className="mt-4 h-8 w-3/4" />
        <Skeleton className="mt-6 h-24 w-full" />
      </div>
      <div className="mt-8 flex flex-col gap-3">
        <Skeleton className="h-4 w-24" />
        {Array.from({ length: 3 }).map((_, i) => (
          <Skeleton key={i} className="h-20 w-full" />
        ))}
      </div>
    </div>
  );
}
