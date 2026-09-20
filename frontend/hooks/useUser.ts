"use client";

import { useUser as useAuth0User } from "@auth0/nextjs-auth0";
import { useQuery } from "@tanstack/react-query";

import { apiFetch } from "@/lib/api-client";

export type MeResponse = {
  id: string;
  email: string;
  tier: "free" | "pro";
  // Forum rebuild, Milestone 2 Step M2.1 (WhyPoliceForum_MasterGuide.md) —
  // rides the same GET /api/me request as everything else here, per that
  // step's own explicit requirement (no second loading state to
  // coordinate). verificationStatus is null for every citizen row and for
  // an attorney row that hasn't started the "Become an Attorney" flow yet.
  role: "citizen" | "attorney";
  verificationStatus: "pending" | "approved" | "rejected" | null;
};

/**
 * Server-data hook wrapping GET /api/me — AgentGuide/01_ThemeGuideline.md
 * §10 (TanStack Query for all server/remote data, not plain useState/useEffect).
 * Only fires once Auth0 confirms a real session exists, so it never fires a
 * doomed request while logged out.
 */
export function useUser() {
  const { user: auth0User, isLoading: authLoading } = useAuth0User();

  const query = useQuery<MeResponse>({
    queryKey: ["me"],
    queryFn: () => apiFetch<MeResponse>("/api/me"),
    enabled: !!auth0User,
    retry: 1,
  });

  return {
    ...query,
    isLoading: authLoading || (!!auth0User && query.isLoading),
  };
}
