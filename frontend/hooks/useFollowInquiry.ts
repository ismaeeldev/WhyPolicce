"use client";

import { useMutation, useQueryClient, type InfiniteData } from "@tanstack/react-query";

import { apiFetch } from "@/lib/api-client";
import type { Inquiry, InquiriesPage } from "@/hooks/useInquiries";

/**
 * Real bug found via Playwright E2E re-testing (Milestone 1/2
 * re-verification pass): this hook only ever updated/invalidated the
 * feed's ["inquiries"] cache — the thread page reads a single inquiry
 * via useInquiry(id), key ["inquiry", id], which this hook never
 * touched. Following an inquiry from its own thread page silently
 * succeeded on the backend (confirmed via a real 201 response) but the
 * button never flipped to "Following," since nothing ever told that
 * page's own cache entry the follow happened. The exact same class of
 * stale-query-key bug already found once this session in
 * useRespondToConsultation (see that hook's own fix), now recurring
 * here — updateSingleInquiryInCache + the matching invalidation below
 * close it the same way.
 */
function updateSingleInquiryInCache(
  data: Inquiry | undefined,
  inquiryId: string,
  isFollowing: boolean,
  followerCountDelta: number,
): Inquiry | undefined {
  if (!data || data.id !== inquiryId) return data;
  return {
    ...data,
    isFollowing,
    followerCount: Math.max(0, data.followerCount + followerCountDelta),
  };
}

/**
 * Follow/unfollow mutation for feed cards — forum rebuild, Milestone 2
 * Step M2.2 (WhyPoliceForum_MasterGuide.md). Optimistic per ThemeGuideline
 * §10 rule 3 (updates the button state instantly, rolls back on failure) —
 * a follow/unfollow failure is rare and safely recoverable, unlike a paid
 * -tier gate, which §10 explicitly says never to fake optimistically.
 *
 * Applies the update across every cached feed page (any filter
 * combination), not just the currently-viewed one, since the same
 * inquiry can appear in multiple filtered views (e.g. unfiltered feed AND
 * a region-filtered one) and both must stay consistent.
 */
function updateInquiryInCache(
  data: InfiniteData<InquiriesPage> | undefined,
  inquiryId: string,
  isFollowing: boolean,
  followerCountDelta: number,
): InfiniteData<InquiriesPage> | undefined {
  if (!data) return data;
  return {
    ...data,
    pages: data.pages.map((page) => ({
      ...page,
      items: page.items.map((item: Inquiry) =>
        item.id === inquiryId
          ? {
              ...item,
              isFollowing,
              followerCount: Math.max(0, item.followerCount + followerCountDelta),
            }
          : item,
      ),
    })),
  };
}

// Real race condition, found by walking through M2.2's own Bug Fix
// adversarial scenario before writing tests, not caught by a failed run:
// rapidly toggling Follow (follow -> unfollow -> follow) fires three
// overlapping mutations. Each one's own onSettled independently calls
// invalidateQueries, and an EARLIER mutation's slower network response
// can resolve/invalidate AFTER a later one, silently overwriting the
// correct final state with a stale one. Fixed with a per-inquiry mutation
// counter: onSettled only invalidates if this call is still the most
// recent mutation issued for that inquiry id, so a late-arriving stale
// response can never clobber a newer optimistic update or its own
// eventual real result.
const latestMutationId = new Map<string, number>();
let mutationCounter = 0;

function useFollowMutation(method: "POST" | "DELETE", isFollowing: boolean, delta: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (inquiryId: string) =>
      apiFetch(`/api/v1/inquiries/${inquiryId}/follow`, { method }),
    onMutate: async (inquiryId: string) => {
      mutationCounter += 1;
      const thisMutationId = mutationCounter;
      latestMutationId.set(inquiryId, thisMutationId);

      await queryClient.cancelQueries({ queryKey: ["inquiries"] });
      await queryClient.cancelQueries({ queryKey: ["inquiry", inquiryId] });

      const previous = queryClient.getQueriesData<InfiniteData<InquiriesPage>>({
        queryKey: ["inquiries"],
      });
      previous.forEach(([key, data]) => {
        queryClient.setQueryData(key, updateInquiryInCache(data, inquiryId, isFollowing, delta));
      });

      const previousSingle = queryClient.getQueryData<Inquiry>(["inquiry", inquiryId]);
      queryClient.setQueryData<Inquiry>(
        ["inquiry", inquiryId],
        (data) => updateSingleInquiryInCache(data, inquiryId, isFollowing, delta),
      );

      return { previous, previousSingle, thisMutationId };
    },
    onError: (_err, inquiryId, context) => {
      context?.previous.forEach(([key, data]) => {
        queryClient.setQueryData(key, data);
      });
      if (context?.previousSingle !== undefined) {
        queryClient.setQueryData(["inquiry", inquiryId], context.previousSingle);
      }
    },
    onSettled: (_data, _err, inquiryId, context) => {
      if (latestMutationId.get(inquiryId) !== context?.thisMutationId) return;
      queryClient.invalidateQueries({ queryKey: ["inquiries"] });
      queryClient.invalidateQueries({ queryKey: ["inquiry", inquiryId] });
    },
  });
}

export function useFollowInquiry() {
  return useFollowMutation("POST", true, 1);
}

export function useUnfollowInquiry() {
  return useFollowMutation("DELETE", false, -1);
}
