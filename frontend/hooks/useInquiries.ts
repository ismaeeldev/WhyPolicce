"use client";

import { useInfiniteQuery, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { apiFetch } from "@/lib/api-client";
import type { AttorneyRequestOnInquiry } from "@/hooks/useConsultationRequests";

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
  // Real gap found + fixed in M2.4: the raw author identity is never
  // exposed, only this per-viewer computed boolean — the frontend
  // needs it to decide whether to show its own Edit/Delete controls;
  // only present on GET /api/v1/inquiries/{id} (single-inquiry), not
  // the feed list.
  isAuthor?: boolean;
  // Only populated (non-empty) for the inquiry's own author, per M2.4's
  // backend fix — every other viewer (including the requesting
  // attorney) always gets an empty array here.
  attorneyRequests?: AttorneyRequestOnInquiry[];
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

export type InquiryCreatePayload = {
  title: string;
  description: string;
  state: string;
  city: string;
  precinct?: string;
  statusTag: StatusTag;
};

/**
 * New-inquiry submission — forum rebuild, Milestone 2 Step M2.3
 * (WhyPoliceForum_MasterGuide.md). Payload is converted to the backend's
 * snake_case InquiryCreate schema here (statusTag -> status_tag) since
 * every response the frontend reads back is camelCase but every request
 * body this codebase sends is snake_case, matching InquiryCreate/
 * InquiryUpdate's own established convention. Never sends `tier` —
 * that field's own backend docstring is explicit that a client-sent
 * "expanded" claim is not trusted at face value without a real
 * webhook-confirmed upgrade (Milestone 3), so this mutation only ever
 * creates a free-tier submission; the $2.99 upgrade path is entirely a
 * client-side gate on submission (intercept before ever calling this),
 * not something this endpoint call itself unlocks.
 */
export function useCreateInquiry() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: InquiryCreatePayload) =>
      apiFetch<Inquiry>("/api/v1/inquiries", {
        method: "POST",
        body: JSON.stringify({
          title: payload.title,
          description: payload.description,
          state: payload.state,
          city: payload.city,
          precinct: payload.precinct,
          status_tag: payload.statusTag,
        }),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["inquiries"] });
    },
  });
}

/**
 * Single-inquiry fetch — forum rebuild, Milestone 2 Step M2.4
 * (WhyPoliceForum_MasterGuide.md). Deliberately a SEPARATE query from
 * useInquiries' feed cache, not a lookup into already-loaded feed pages
 * — the thread page needs the FULL untruncated description and the
 * author-only attorneyRequests field, neither of which the feed's own
 * truncated preview data carries (M1.4's own resolved ambiguity note).
 */
export function useInquiry(id: string) {
  return useQuery<Inquiry>({
    queryKey: ["inquiry", id],
    queryFn: () => apiFetch<Inquiry>(`/api/v1/inquiries/${id}`),
  });
}

export type InquiryUpdatePayload = Partial<InquiryCreatePayload>;

export function useUpdateInquiry(id: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: InquiryUpdatePayload) =>
      apiFetch<Inquiry>(`/api/v1/inquiries/${id}`, {
        method: "PATCH",
        body: JSON.stringify({
          ...(payload.title !== undefined && { title: payload.title }),
          ...(payload.description !== undefined && { description: payload.description }),
          ...(payload.state !== undefined && { state: payload.state }),
          ...(payload.city !== undefined && { city: payload.city }),
          ...(payload.precinct !== undefined && { precinct: payload.precinct }),
          ...(payload.statusTag !== undefined && { status_tag: payload.statusTag }),
        }),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["inquiry", id] });
      queryClient.invalidateQueries({ queryKey: ["inquiries"] });
    },
  });
}

export function useDeleteInquiry(id: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => apiFetch(`/api/v1/inquiries/${id}`, { method: "DELETE" }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["inquiries"] });
    },
  });
}

export type ThreadComment = {
  id: string;
  inquiryId: string;
  authorId: string;
  body: string;
  createdAt: string;
};

export type ThreadPage = {
  items: ThreadComment[];
  total: number;
  limit: number;
  offset: number;
};

export function useThread(inquiryId: string) {
  return useQuery<ThreadPage>({
    queryKey: ["thread", inquiryId],
    queryFn: () => apiFetch<ThreadPage>(`/api/v1/inquiries/${inquiryId}/thread?limit=100`),
  });
}

export function useCreateComment(inquiryId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (body: string) =>
      apiFetch<ThreadComment>(`/api/v1/inquiries/${inquiryId}/thread`, {
        method: "POST",
        body: JSON.stringify({ body }),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["thread", inquiryId] });
      queryClient.invalidateQueries({ queryKey: ["inquiry", inquiryId] });
      queryClient.invalidateQueries({ queryKey: ["inquiries"] });
    },
  });
}

export function useUpdateComment(inquiryId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ commentId, body }: { commentId: string; body: string }) =>
      apiFetch<ThreadComment>(`/api/v1/inquiries/${inquiryId}/thread/${commentId}`, {
        method: "PATCH",
        body: JSON.stringify({ body }),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["thread", inquiryId] });
    },
  });
}

export function useDeleteComment(inquiryId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (commentId: string) =>
      apiFetch(`/api/v1/inquiries/${inquiryId}/thread/${commentId}`, { method: "DELETE" }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["thread", inquiryId] });
      queryClient.invalidateQueries({ queryKey: ["inquiry", inquiryId] });
      queryClient.invalidateQueries({ queryKey: ["inquiries"] });
    },
  });
}
