import { dehydrate, HydrationBoundary } from "@tanstack/react-query";

import { HomeFeedClient } from "@/components/feed/HomeFeedClient";
import { serverApiFetch } from "@/lib/api-server-fetch";
import { getQueryClient } from "@/lib/get-query-client";
import { fetchInquiriesPage, inquiriesQueryKey } from "@/lib/inquiries-query";

const DEFAULT_FILTERS = { region: "", status: "", sort: "newest" as const, q: "" };

// Without this, Next.js prerenders this page as fully static at BUILD
// time (confirmed via a real production build — "/" came back marked
// static) — every visitor would get the same first-page snapshot baked
// in then, and a real inquiry posted after that build simply wouldn't
// appear on the home feed until the next deploy. This is a live,
// nationwide, constantly-changing feed, so it must render fresh per
// request, not once at build time.
export const dynamic = "force-dynamic";

/**
 * Home feed — forum rebuild, Milestone 2 Step M2.2 (WhyPoliceForum_
 * MasterGuide.md). Replaces the old RAG-search product's landing page
 * entirely (per this step's own Manual Step decision, confirmed by the
 * user) — this is now the new product's primary landing surface at `/`,
 * public/unauthenticated per the scope PDF (reading the forum needs no
 * login; only submitting/managing content does, per M2.0's proxy.ts).
 *
 * Content max-width 1200px (ThemeGuideline §3), feed itself single-column
 * at max-w-[760px] matching the client's own reference mockup layout, not
 * a multi-column grid. Pagination: "Load more" button (Standing
 * Implementation Discipline item 5's own required, documented decision) —
 * simpler to implement correctly and test deterministically than
 * scroll-triggered infinite-scroll, and avoids IntersectionObserver edge
 * cases/accidental re-fetches on fast scroll.
 *
 * Real fix for a reported slow first load: this used to be entirely
 * "use client" — the server shipped empty HTML, then the browser had to
 * download/hydrate the JS bundle and only THEN fetch the first page of
 * posts, a full extra client round-trip before anything appeared. This
 * is now a Server Component that prefetches the default-filter first
 * page on the server (in parallel with everything else Next.js is
 * already doing to build the response) and embeds it in the initial
 * HTML via HydrationBoundary — posts are already there on first paint.
 * "Load more" and every filter/search change are UNCHANGED: still a
 * plain client-side fetch through the exact same useInquiries hook,
 * same page size, same behavior — only the very first page's very
 * first load is now server-prefetched.
 */
export default async function HomeFeedPage() {
  const queryClient = getQueryClient();
  await queryClient.prefetchInfiniteQuery({
    queryKey: inquiriesQueryKey(DEFAULT_FILTERS),
    queryFn: ({ pageParam }) => fetchInquiriesPage(DEFAULT_FILTERS, pageParam as number, serverApiFetch),
    initialPageParam: 0,
  });

  return (
    <div className="mx-auto w-full max-w-[1200px] px-5 sm:px-6 py-8 sm:py-12">
      <div className="mx-auto max-w-[760px]">
        <h1 className="font-display text-h1 text-text-primary mb-6">Community Forum</h1>
        <HydrationBoundary state={dehydrate(queryClient)}>
          <HomeFeedClient />
        </HydrationBoundary>
      </div>
    </div>
  );
}
