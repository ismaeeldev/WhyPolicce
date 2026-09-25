"use client";

import { ApiError } from "@/lib/api-client";
import { useRequestConsultation } from "@/hooks/useConsultationRequests";
import type { AttorneyRequestStatus } from "@/hooks/useConsultationRequests";
import { useToastStore } from "@/stores/useToastStore";

/**
 * "Request Consultation" — the entire monetized purpose of the attorney
 * experience (M2.4), so styled as Primary (§4.2), distinct from the
 * citizen feed's more neutral Follow button. Disables/shows a distinct
 * state once a request is already pending for this inquiry-attorney
 * pair — the backend's own 409 already_requested makes a second attempt
 * meaningless, so the UI shouldn't imply repeating it does anything.
 *
 * Real gap found during a full-scope re-audit: "already requested" used
 * to live ONLY in this component's own local mutation state
 * (isSuccess/error.code), which a background refetch or remount wipes
 * (refetchOnWindowFocus is app-wide) — an attorney who'd already sent a
 * request would see "Request Consultation" again, click it, and get a
 * silently-swallowed 409 with no explanation. The backend already
 * computes myRequestStatus per feed item for exactly this reason
 * (inquiries.py's list_inquiries); serverStatus is that real,
 * persisted source of truth, checked ahead of local mutation state so
 * it survives any refetch.
 */
export function RequestConsultationButton({
  inquiryId,
  serverStatus,
}: {
  inquiryId: string;
  serverStatus: AttorneyRequestStatus | null;
}) {
  const requestConsultation = useRequestConsultation();
  const showToast = useToastStore((s) => s.show);

  if (serverStatus || requestConsultation.isSuccess) {
    return (
      <span className="rounded-sm bg-accent-subtle px-3.5 py-1.5 text-body-sm font-medium text-text-primary">
        {serverStatus === "accepted" ? "Accepted" : serverStatus === "declined" ? "Declined" : "Requested"}
      </span>
    );
  }

  const alreadyRequested =
    requestConsultation.error instanceof ApiError &&
    requestConsultation.error.code === "already_requested";

  return (
    <button
      type="button"
      onClick={() =>
        requestConsultation.mutate(inquiryId, {
          onError: (err) => {
            // Real gap found during a full-scope re-audit: this used to
            // silently swallow already_requested with no toast at all —
            // now that serverStatus (above) is the primary guard, this
            // branch only fires on a genuine race (a request landed
            // between this component's last fetch and this click), so
            // it deserves the same explanation as any other failure
            // rather than a silent revert.
            showToast(
              err instanceof ApiError && err.code === "already_requested"
                ? "You've already requested this consultation."
                : err instanceof ApiError
                  ? err.message
                  : "Couldn't send that request. Try again.",
            );
          },
        })
      }
      disabled={requestConsultation.isPending || alreadyRequested}
      className="rounded-sm bg-accent px-3.5 py-1.5 text-body-sm font-medium text-accent-foreground hover:bg-accent-hover disabled:bg-bg-subtle disabled:text-text-muted disabled:cursor-not-allowed transition-colors focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2 outline-none"
    >
      {alreadyRequested ? "Already requested" : requestConsultation.isPending ? "Requesting…" : "Request Consultation"}
    </button>
  );
}
