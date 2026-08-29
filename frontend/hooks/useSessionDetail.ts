"use client";

import { useQuery } from "@tanstack/react-query";

import { apiFetch } from "@/lib/api-client";

export type SessionMessage = {
  id: string;
  role: "user" | "assistant";
  content: string;
  isDeepSearch: boolean;
  memorySnippets: string[];
  createdAt: string;
};

export type SessionDetail = {
  id: string;
  title: string;
  messages: SessionMessage[];
};

/**
 * TanStack Query hook wrapping GET /api/search/{session_id} —
 * AgentGuide/03_MasterPromptGuide.md Step 6. `enabled` guards against
 * firing with an empty/undefined id during the route's first render.
 */
export function useSessionDetail(sessionId: string | undefined) {
  return useQuery<SessionDetail>({
    queryKey: ["search-session", sessionId],
    queryFn: () => apiFetch<SessionDetail>(`/api/search/${sessionId}`),
    enabled: !!sessionId,
    retry: false,
  });
}
