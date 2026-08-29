"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { apiFetch } from "@/lib/api-client";

export type MemoryNote = {
  id: string;
  content: string;
  createdAt: string;
  updatedAt: string;
};

const MEMORY_KEY = ["memory-notes"];

/**
 * TanStack Query hook wrapping /api/memory — AgentGuide/03_MasterPromptGuide.md
 * Step 6.5, ThemeGuideline §10. List + 3 mutations, all optimistic per §10
 * point 3 (apply immediately, roll back the exact previous snapshot on
 * failure).
 */
export function useMemoryNotes() {
  return useQuery<MemoryNote[]>({
    queryKey: MEMORY_KEY,
    queryFn: () => apiFetch<MemoryNote[]>("/api/memory"),
  });
}

function useOptimisticMemoryMutation<TVars>(
  mutationFn: (vars: TVars) => Promise<unknown>,
  optimisticUpdate: (prev: MemoryNote[] | undefined, vars: TVars) => MemoryNote[],
) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn,
    onMutate: async (vars: TVars) => {
      await queryClient.cancelQueries({ queryKey: MEMORY_KEY });
      const previous = queryClient.getQueryData<MemoryNote[]>(MEMORY_KEY);
      queryClient.setQueryData<MemoryNote[]>(MEMORY_KEY, (prev) => optimisticUpdate(prev, vars));
      return { previous };
    },
    onError: (_err, _vars, context) => {
      if (context && "previous" in context) {
        queryClient.setQueryData(MEMORY_KEY, context.previous);
      }
    },
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: MEMORY_KEY });
    },
  });
}

export const TEMP_ID_PREFIX = "temp-";

export function useAddMemoryNote() {
  return useOptimisticMemoryMutation<{ content: string }>(
    ({ content }) => apiFetch("/api/memory", { method: "POST", body: JSON.stringify({ content }) }),
    (prev, { content }) => [
      {
        id: `${TEMP_ID_PREFIX}${Date.now()}`,
        content,
        createdAt: new Date().toISOString(),
        updatedAt: new Date().toISOString(),
      },
      ...(prev ?? []),
    ],
  );
}

export function useEditMemoryNote() {
  return useOptimisticMemoryMutation<{ id: string; content: string }>(
    ({ id, content }) =>
      apiFetch(`/api/memory/${id}`, { method: "PATCH", body: JSON.stringify({ content }) }),
    (prev, { id, content }) =>
      (prev ?? []).map((note) =>
        note.id === id ? { ...note, content, updatedAt: new Date().toISOString() } : note,
      ),
  );
}

export function useDeleteMemoryNote() {
  return useOptimisticMemoryMutation<{ id: string }>(
    ({ id }) => apiFetch(`/api/memory/${id}`, { method: "DELETE" }),
    (prev, { id }) => (prev ?? []).filter((note) => note.id !== id),
  );
}
