"use client";

import { useMutation } from "@tanstack/react-query";

import { apiFetch } from "@/lib/api-client";

/**
 * Report/Flag mutation — forum rebuild, Milestone 2 Step M2.4
 * (WhyPoliceForum_MasterGuide.md). Matches the backend's ReportCreate
 * schema exactly (target_type/target_id/reason, snake_case).
 *
 * Real product decision (M2.4's own Test requirement to decide, not
 * leave as an accidental unhandled case): reporting the same content
 * twice from the same user is ALLOWED, not blocked — the backend has
 * no uniqueness constraint on (reporter_id, target_id) and this
 * mutation doesn't add one client-side either. A user genuinely
 * changing their mind about severity, or simply re-flagging after
 * seeing the content resurface, is normal moderation-adjacent
 * behavior; silently blocking a second report would hide a real
 * signal from the admin review queue for no real benefit.
 */
export function useReportContent() {
  return useMutation({
    mutationFn: (payload: { targetType: "inquiry" | "thread_comment"; targetId: string; reason: string }) =>
      apiFetch("/api/v1/reports", {
        method: "POST",
        body: JSON.stringify({
          target_type: payload.targetType,
          target_id: payload.targetId,
          reason: payload.reason,
        }),
      }),
  });
}
