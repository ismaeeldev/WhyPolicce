"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { apiFetch } from "@/lib/api-client";

/**
 * Admin panel data hooks — new admin panel (client's explicit request:
 * a secure, dedicated dashboard for attorney approval + report review,
 * since app/routers/admin.py's endpoints existed with no frontend at
 * all before this). Every hook here hits an ADMIN_AUTH0_SUBS-gated
 * backend endpoint; a non-admin gets a real 403 from every one of these
 * except useAdminMe, which is the one endpoint specifically designed to
 * answer "am I an admin?" without itself being gated (see its own
 * backend docstring).
 */

export type AdminMe = {
  isAdmin: boolean;
  email?: string | null;
};

export function useAdminMe() {
  return useQuery<AdminMe>({
    queryKey: ["admin", "me"],
    queryFn: () => apiFetch<AdminMe>("/api/v1/admin/me"),
  });
}

export type AdminDashboard = {
  pendingAttorneys: number;
  approvedAttorneys: number;
  rejectedAttorneys: number;
  openReports: number;
};

export function useAdminDashboard() {
  return useQuery<AdminDashboard>({
    queryKey: ["admin", "dashboard"],
    queryFn: () => apiFetch<AdminDashboard>("/api/v1/admin/dashboard"),
  });
}

export type VerificationStatus = "pending" | "approved" | "rejected";

export type AdminAttorney = {
  id: string;
  email: string;
  verifiedBarNo: string | null;
  barJurisdiction: string | null;
  verificationStatus: VerificationStatus | null;
  createdAt: string;
};

export type AdminAttorneysPage = {
  items: AdminAttorney[];
  total: number;
  limit: number;
  offset: number;
};

export function useAdminAttorneys(status: VerificationStatus | "all") {
  return useQuery<AdminAttorneysPage>({
    queryKey: ["admin", "attorneys", status],
    queryFn: () => {
      const params = new URLSearchParams();
      if (status !== "all") params.set("status", status);
      params.set("limit", "100");
      return apiFetch<AdminAttorneysPage>(`/api/v1/admin/attorneys?${params.toString()}`);
    },
  });
}

export function useVerifyAttorney() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ userId, decision }: { userId: string; decision: "approved" | "rejected" }) =>
      apiFetch(`/api/v1/admin/attorneys/${userId}/verify`, {
        method: "POST",
        body: JSON.stringify({ decision }),
      }),
    onSuccess: () => {
      // Real gap avoided: an approve/reject changes which of the 3
      // status-filtered lists this attorney belongs to AND the
      // dashboard's own counts — invalidating only one and not the
      // other would leave either the list or the summary stat stale
      // after a real, successful decision.
      queryClient.invalidateQueries({ queryKey: ["admin", "attorneys"] });
      queryClient.invalidateQueries({ queryKey: ["admin", "dashboard"] });
    },
  });
}

export type AdminReportTarget = { title: string; description: string } | { body: string } | null;

export type AdminReport = {
  id: string;
  targetType: "inquiry" | "thread_comment";
  targetId: string;
  reason: string;
  reporterId: string;
  status: "open" | "resolved" | "dismissed";
  createdAt: string;
  target: AdminReportTarget;
};

export type AdminReportsPage = {
  items: AdminReport[];
  total: number;
  limit: number;
  offset: number;
};

export function useAdminReports() {
  return useQuery<AdminReportsPage>({
    queryKey: ["admin", "reports"],
    queryFn: () => apiFetch<AdminReportsPage>("/api/v1/admin/reports?limit=100"),
  });
}

export function useReviewReport() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ reportId, decision }: { reportId: string; decision: "resolved" | "dismissed" }) =>
      apiFetch(`/api/v1/admin/reports/${reportId}`, {
        method: "PATCH",
        body: JSON.stringify({ decision }),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["admin", "reports"] });
      queryClient.invalidateQueries({ queryKey: ["admin", "dashboard"] });
    },
  });
}
