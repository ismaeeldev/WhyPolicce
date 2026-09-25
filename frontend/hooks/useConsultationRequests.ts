"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { apiFetch, ApiError } from "@/lib/api-client";
import type { StatusTag } from "@/hooks/useInquiries";

export type AttorneyRequestStatus = "pending" | "accepted" | "declined";

export type AttorneyRequestOnInquiry = {
  id: string;
  attorneyId: string;
  attorneyBarNo: string | null;
  attorneyBarJurisdiction: string | null;
  status: AttorneyRequestStatus;
  createdAt: string;
};

export type MyConsultationRequest = {
  id: string;
  status: AttorneyRequestStatus;
  createdAt: string;
  inquiry: {
    id: string;
    title: string;
    statusTag: StatusTag;
    state: string;
    city: string;
  };
};

/**
 * Consultation-request hooks — forum rebuild, Milestone 2 Step M2.4
 * (WhyPoliceForum_MasterGuide.md). POST/PATCH match the M1.4 backend
 * endpoints exactly: request_consultation takes inquiry_id as a QUERY
 * param (not a JSON body — the backend route has no Pydantic body
 * model), respond_to_consultation takes {decision} as a JSON body.
 */
export function useRequestConsultation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (inquiryId: string) =>
      apiFetch<{ id: string; status: AttorneyRequestStatus }>(
        `/api/v1/attorneys/request-consultation?inquiry_id=${inquiryId}`,
        { method: "POST" },
      ),
    onSuccess: (_data, inquiryId) => {
      // Real bug found via Playwright E2E re-testing, same class as
      // useFollowInquiry's own fix: only invalidating the feed's
      // ["inquiries"] key left a single inquiry's own thread-page cache
      // (["inquiry", id]) stale after a real, successful request.
      queryClient.invalidateQueries({ queryKey: ["inquiries"] });
      queryClient.invalidateQueries({ queryKey: ["inquiry", inquiryId] });
      queryClient.invalidateQueries({ queryKey: ["my-consultation-requests"] });
    },
    onError: (err, inquiryId) => {
      // Same reasoning as onSuccess above, for the specific race where
      // the request actually exists server-side already (a request
      // landed between this component's last fetch and this click) —
      // without this, the feed's myRequestStatus stays stale/null and
      // the button would keep offering "Request Consultation" again.
      if (err instanceof ApiError && err.code === "already_requested") {
        queryClient.invalidateQueries({ queryKey: ["inquiries"] });
        queryClient.invalidateQueries({ queryKey: ["inquiry", inquiryId] });
      }
    },
  });
}

export function useRespondToConsultation(inquiryId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ requestId, decision }: { requestId: string; decision: "accepted" | "declined" }) =>
      apiFetch<{ id: string; status: AttorneyRequestStatus }>(
        `/api/v1/attorneys/request-consultation/${requestId}`,
        { method: "PATCH", body: JSON.stringify({ decision }) },
      ),
    onSuccess: () => {
      // The single-inquiry thread view (useInquiry, key ["inquiry", id])
      // is what actually renders this row's own attorneyRequests array —
      // invalidating only the feed's ["inquiries"] key left the author's
      // own page showing stale pending state until a manual reload.
      queryClient.invalidateQueries({ queryKey: ["inquiry", inquiryId] });
      queryClient.invalidateQueries({ queryKey: ["inquiries"] });
      queryClient.invalidateQueries({ queryKey: ["my-consultation-requests"] });
    },
  });
}

const MY_REQUESTS_KEY = ["my-consultation-requests"];

export function useMyConsultationRequests() {
  return useQuery<{ items: MyConsultationRequest[]; total: number }>({
    queryKey: MY_REQUESTS_KEY,
    queryFn: () => apiFetch("/api/v1/attorneys/me/requests"),
  });
}
