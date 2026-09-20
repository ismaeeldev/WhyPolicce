"use client";

import { useInfiniteQuery } from "@tanstack/react-query";

import { apiFetch } from "@/lib/api-client";

/**
 * Home feed data hook — forum rebuild, Milestone 2 Step M2.2
 * (WhyPoliceForum_MasterGuide.md). This codebase's first use of
 * useInfiniteQuery (no local precedent existed) — every other server-data
 * hook here (useSearchHistory, useSupportedStates) uses plain useQuery,
 * but the feed needs real pagination against GET /api/v1/inquiries.
 *
 * Pagination style: "Load more" button, not scroll-triggered
 * infinite-scroll (Standing Implementation Discipline item 5's own
 * required decision) — simpler to implement correctly, easier to test
 * deterministically, and avoids IntersectionObserver edge cases/
 * accidental re-fetches on fast scroll.
 */
export type StatusTag = "community_trace" | "awaiting_police_statement";

export type Inquiry = {
  id: string;
  title: string;
  description: string;
  state: string;
  city: string;
  precinct: string | null;
  statusTag: StatusTag;
  tier: "free" | "expanded";
  followerCount: number;
  commentCount: number;
  hasAttachments: boolean;
  createdAt: string;
  updatedAt: string;
  isFollowing: boolean;
};

export type InquiriesPage = {
  items: Inquiry[];
  total: number;
  limit: number;
  offset: number;
};

export type InquiriesFilters = {
  region: string;
  status: string;
  sort: "newest" | "most_followed";
  q: string;
};

const PAGE_SIZE = 20;

export function useInquiries(filters: InquiriesFilters) {
  return useInfiniteQuery<InquiriesPage>({
    queryKey: ["inquiries", filters],
    queryFn: ({ pageParam }) => {
      const params = new URLSearchParams();
      if (filters.region) params.set("region", filters.region);
      if (filters.status) params.set("status", filters.status);
      params.set("sort", filters.sort);
      if (filters.q) params.set("q", filters.q);
      params.set("limit", String(PAGE_SIZE));
      params.set("offset", String(pageParam));
      return apiFetch<InquiriesPage>(`/api/v1/inquiries?${params.toString()}`);
    },
    initialPageParam: 0,
    getNextPageParam: (lastPage) => {
      const nextOffset = lastPage.offset + lastPage.items.length;
      return nextOffset < lastPage.total ? nextOffset : undefined;
    },
  });
}
