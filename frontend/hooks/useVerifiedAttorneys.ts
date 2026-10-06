"use client";

import { useQuery } from "@tanstack/react-query";

import { apiFetch } from "@/lib/api-client";

export type VerifiedAttorney = {
  id: string;
  firstName: string;
  lastName: string;
  barJurisdiction: string | null;
  firmWebsite: string | null;
};

/** Public, admin-approved attorneys for the home page showcase tiles. */
export function useVerifiedAttorneys(limit = 4) {
  return useQuery({
    queryKey: ["attorneys", "verified", limit],
    queryFn: () => apiFetch<{ items: VerifiedAttorney[] }>(`/api/v1/attorneys/verified?limit=${limit}`),
    staleTime: 60_000,
    select: (data) => data.items,
  });
}

export function attorneyDisplayName(a: VerifiedAttorney) {
  return `${a.firstName} ${a.lastName}`.trim() || "Verified Attorney";
}

export function attorneyInitials(a: VerifiedAttorney) {
  return `${a.firstName[0] ?? ""}${a.lastName[0] ?? ""}`.toUpperCase() || "VA";
}
