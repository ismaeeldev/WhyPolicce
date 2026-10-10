import { dehydrate, HydrationBoundary } from "@tanstack/react-query";

import { HomeFeedClient } from "@/components/feed/HomeFeedClient";
import { HomeHero } from "@/components/home/HomeHero";
import { serverApiFetch } from "@/lib/api-server-fetch";
import { getQueryClient } from "@/lib/get-query-client";
import { fetchInquiriesPage, inquiriesQueryKey } from "@/lib/inquiries-query";
import type { InquiryStats } from "@/hooks/useInquiries";

const DEFAULT_FILTERS = { region: "", status: "", sort: "newest" as const, q: "" };

export const dynamic = "force-dynamic";

export default async function HomeFeedPage() {
  const queryClient = getQueryClient();
  await Promise.all([
    queryClient.prefetchInfiniteQuery({
      queryKey: inquiriesQueryKey(DEFAULT_FILTERS),
      queryFn: ({ pageParam }) => fetchInquiriesPage(DEFAULT_FILTERS, pageParam as number, serverApiFetch),
      initialPageParam: 0,
    }),
    queryClient.prefetchQuery({
      queryKey: ["inquiries", "stats"],
      queryFn: () => serverApiFetch<InquiryStats>("/api/v1/inquiries/stats"),
    }),
  ]);

  return (
    <HydrationBoundary state={dehydrate(queryClient)}>
      {/* Modern Civic Action Hero - Full Bleed Edge-to-Edge */}
      <HomeHero />

      {/* Main Page Content Container */}
      <div className="mx-auto w-full max-w-[1400px] px-4 sm:px-6 lg:px-8 py-8 sm:py-10">
        {/* Dynamic Split Dashboard with Live Synchronized Bento Matrix & Sticky Sidebar */}
        <HomeFeedClient />
      </div>
    </HydrationBoundary>
  );
}
