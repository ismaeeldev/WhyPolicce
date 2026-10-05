import { dehydrate, HydrationBoundary } from "@tanstack/react-query";

import { HomeFeedClient } from "@/components/feed/HomeFeedClient";
import { BentoGrid } from "@/components/home/BentoGrid";
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
    <div className="mx-auto w-full max-w-[1400px] px-4 sm:px-6 lg:px-8 pb-8 sm:pb-12 space-y-8">
      <HydrationBoundary state={dehydrate(queryClient)}>
        {/* Modern Civic Action Hero */}
        <HomeHero />

        {/* 4-Tile Bento Intelligence Matrix */}
        <BentoGrid />

        {/* Dynamic Split Dashboard Feed & Sidebar */}
        <HomeFeedClient />
      </HydrationBoundary>
    </div>
  );
}
