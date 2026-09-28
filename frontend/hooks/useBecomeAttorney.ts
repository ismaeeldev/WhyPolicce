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
    mutationFn: (vars: {
      barNo: string;
      jurisdiction: string;
      legalFirstName: string;
      legalLastName: string;
      firmEmail: string;
      // Scope Revision 1 §5.5 — optional, client's own wording: "if provided".
      firmWebsite?: string;
    }) =>
      apiFetch<{ role: string; verificationStatus: string; domainMismatchWarning: string | null }>(
        "/api/me/become-attorney",
        {
          method: "POST",
          body: JSON.stringify({
            bar_no: vars.barNo,
            jurisdiction: vars.jurisdiction,
            legal_first_name: vars.legalFirstName,
            legal_last_name: vars.legalLastName,
            firm_email_address: vars.firmEmail,
            firm_website: vars.firmWebsite || undefined,
          }),
        },
      ),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["me"] });
    },
  });
}
