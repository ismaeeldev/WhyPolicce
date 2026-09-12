"use client";

import { useQuery } from "@tanstack/react-query";

import { apiFetch } from "@/lib/api-client";

export type SupportedState = {
  code: string;
  name: string;
};

const SUPPORTED_STATES_KEY = ["supported-states"];

/**
 * State Selector, Step 6 — real client-requested feature (their own
 * pasted SearchBar draft hardcoded 5 placeholder states: NY/CA/TX/FL/IL).
 *
 * TanStack Query hook wrapping GET /api/search/states, same pattern as
 * useSearchHistory.ts. Deliberately fetches the REAL, current list from
 * the backend rather than hardcoding it here — the whole point of Steps
 * 1-3 was making this list live-derived from actual coverage, so the
 * frontend must not reintroduce a second, hand-maintained copy.
 *
 * A long staleTime is appropriate here (unlike history, which changes
 * per-search): the supported-states list only changes when a new
 * city-expansion phase ships, not per-user-action — no need to refetch
 * on every mount/focus the way TanStack Query's defaults would.
 */
export function useSupportedStates() {
  return useQuery<SupportedState[]>({
    queryKey: SUPPORTED_STATES_KEY,
    queryFn: () => apiFetch<SupportedState[]>("/api/search/states"),
    staleTime: 60 * 60 * 1000, // 1 hour — see docstring above
  });
}
