"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";

import { apiFetch } from "@/lib/api-client";

/**
 * "Become an Attorney" entry point — forum rebuild, Milestone 2 Step M2.1
 * (WhyPoliceForum_MasterGuide.md). Not optimistic (unlike useMemoryNotes'
 * mutations): this changes the account's own role/verification state,
 * which downstream route guards (the attorney portal) depend on being
 * correct — better to wait for the real server response than show a
 * pending-state UI that might have to be rolled back.
 */
export function useBecomeAttorney() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (vars: { barNo: string; jurisdiction: string }) =>
      apiFetch<{ role: string; verificationStatus: string }>("/api/me/become-attorney", {
        method: "POST",
        body: JSON.stringify({ bar_no: vars.barNo, jurisdiction: vars.jurisdiction }),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["me"] });
    },
  });
}
