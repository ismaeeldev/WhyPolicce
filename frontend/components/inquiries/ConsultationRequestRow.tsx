"use client";

import { CheckCircle2, XCircle } from "lucide-react";

import type { AttorneyRequestOnInquiry } from "@/hooks/useConsultationRequests";
import { useRespondToConsultation } from "@/hooks/useConsultationRequests";
import { ApiError } from "@/lib/api-client";
import { useToastStore } from "@/stores/useToastStore";

/**
 * A single consultation-request row on the inquiry author's own thread
 * view (M2.4) — the citizen's real answer to "an attorney wants to
 * help." Accept (Primary) and Decline (Ghost) always shown together
 * while pending, per this step's own explicit requirement — never one
 * without the other. Once decided, replaced with a status label
 * instead of leaving disabled buttons implying the action might still
 * be available.
 */
export function ConsultationRequestRow({
  request,
  inquiryId,
}: {
  request: AttorneyRequestOnInquiry;
  inquiryId: string;
}) {
  const respond = useRespondToConsultation(inquiryId);
  const showToast = useToastStore((s) => s.show);
  const onRespondError = (err: unknown) =>
    showToast(err instanceof ApiError ? err.message : "Couldn't save your response. Try again.");

  const attorneyLabel = request.attorneyBarNo
    ? `Attorney (Bar #${request.attorneyBarNo}${request.attorneyBarJurisdiction ? `, ${request.attorneyBarJurisdiction}` : ""})`
    : "An attorney";

  return (
    <div className="flex items-center justify-between gap-3 rounded-sm border border-accent/30 bg-accent-subtle/40 p-3 transition-colors duration-150 hover:border-accent/50">
      <p className="text-body-sm text-text-primary">{attorneyLabel} requested a consultation.</p>

      {request.status === "pending" && (
        <div className="flex shrink-0 items-center gap-2">
          <button
            type="button"
            onClick={() =>
              respond.mutate(
                { requestId: request.id, decision: "accepted" },
                { onError: onRespondError },
              )
            }
            disabled={respond.isPending}
            className="rounded-sm bg-accent px-3 py-1.5 text-caption font-medium text-accent-foreground hover:bg-accent-hover disabled:opacity-50 transition-colors focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2 outline-none"
          >
            Accept
          </button>
          <button
            type="button"
            onClick={() =>
              respond.mutate(
                { requestId: request.id, decision: "declined" },
                { onError: onRespondError },
              )
            }
            disabled={respond.isPending}
            className="rounded-sm px-3 py-1.5 text-caption text-text-secondary hover:bg-bg-subtle disabled:opacity-50 transition-colors focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2 outline-none"
          >
            Decline
          </button>
        </div>
      )}

      {request.status === "accepted" && (
        <span className="flex shrink-0 items-center gap-1 text-caption text-success">
          <CheckCircle2 className="h-3.5 w-3.5" />
          Accepted
        </span>
      )}

      {request.status === "declined" && (
        <span className="flex shrink-0 items-center gap-1 text-caption text-text-muted">
          <XCircle className="h-3.5 w-3.5" />
          Declined
        </span>
      )}
    </div>
  );
}
