"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { apiFetch } from "@/lib/api-client";

export type HistorySession = {
  id: string;
  title: string;
  createdAt: string;
  isDeepSearch: boolean;
  /** Real gap found via UI review (plan.md "Product/quality work"): the
   * source-citations feature already surfaces real public-record
   * attribution on the live answer view and session-detail replay, but
   * the history list never showed it. Mirrors isDeepSearch's own
   * per-session boolean-flag pattern rather than introducing a new one. */
  hasSources: boolean;
};

const HISTORY_KEY = ["search-history"];

/**
 * TanStack Query hook wrapping GET /api/search/history —
 * AgentGuide/03_MasterPromptGuide.md Step 6, ThemeGuideline §10.
 */
export function useSearchHistory() {
  return useQuery<HistorySession[]>({
    queryKey: HISTORY_KEY,
    queryFn: () => apiFetch<HistorySession[]>("/api/search/history"),
  });
}

/**
 * Clear-history mutation with an optimistic update — ThemeGuideline §10
 * point 3: empty the list immediately, roll back to the previous cache on
 * failure rather than leaving a stuck/incorrect UI.
 */
export function useClearHistory() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: () => apiFetch<{ cleared: boolean }>("/api/search/history", { method: "DELETE" }),
    onMutate: async () => {
      await queryClient.cancelQueries({ queryKey: HISTORY_KEY });
      const previous = queryClient.getQueryData<HistorySession[]>(HISTORY_KEY);
      queryClient.setQueryData<HistorySession[]>(HISTORY_KEY, []);
      return { previous };
    },
    onError: (_err, _vars, context) => {
      if (context?.previous) {
        queryClient.setQueryData(HISTORY_KEY, context.previous);
      }
    },
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: HISTORY_KEY });
    },
  });
}
