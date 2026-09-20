"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { apiFetch } from "@/lib/api-client";
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
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["inquiries"] });
      queryClient.invalidateQueries({ queryKey: ["my-consultation-requests"] });
    },
  });
}

export function useRespondToConsultation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ requestId, decision }: { requestId: string; decision: "accepted" | "declined" }) =>
      apiFetch<{ id: string; status: AttorneyRequestStatus }>(
        `/api/v1/attorneys/request-consultation/${requestId}`,
        { method: "PATCH", body: JSON.stringify({ decision }) },
      ),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["inquiries"] });
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
