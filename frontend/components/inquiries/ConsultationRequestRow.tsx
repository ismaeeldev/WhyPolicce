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
    // Real gap found during a UI audit: the label had no min-w-0 while
    // its sibling buttons were shrink-0 — a long bar-number+jurisdiction
    // string (e.g. "Attorney (Bar #NY1234567, New York)") could push
    // the Accept/Decline buttons off-screen at narrow widths instead of
    // the label wrapping. flex-wrap lets the label take a full line on
    // its own on narrow screens, buttons dropping to their own row.
    <div className="flex flex-wrap items-center justify-between gap-3 rounded-sm border border-accent/30 bg-accent-subtle/40 p-3 transition-colors duration-150 hover:border-accent/50">
      <p className="min-w-0 flex-1 text-body-sm text-text-primary">{attorneyLabel} requested a consultation.</p>

      {request.status === "pending" && (
        // Real gap found during a state-handling audit: both buttons
        // shared respond.isPending with static labels — accepting on a
        // slow connection greyed out BOTH Accept and Decline with no
        // indication which one was clicked. Now shows which specific
        // decision is in flight via mutation.variables.
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
            className="rounded-sm bg-accent px-3 py-1.5 text-caption font-medium text-accent-foreground hover:bg-accent-hover disabled:cursor-not-allowed disabled:opacity-50 transition-colors focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2 outline-none"
          >
            {respond.isPending && respond.variables?.decision === "accepted" ? "Accepting…" : "Accept"}
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
            className="rounded-sm px-3 py-1.5 text-caption text-text-secondary hover:bg-bg-subtle disabled:cursor-not-allowed disabled:opacity-50 transition-colors focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2 outline-none"
          >
            {respond.isPending && respond.variables?.decision === "declined" ? "Declining…" : "Decline"}
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
