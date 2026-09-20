"use client";

import { ApiError } from "@/lib/api-client";
import { useRequestConsultation } from "@/hooks/useConsultationRequests";

/**
 * "Request Consultation" — the entire monetized purpose of the attorney
 * experience (M2.4), so styled as Primary (§4.2), distinct from the
 * citizen feed's more neutral Follow button. Disables/shows a distinct
 * state once a request is already pending for this inquiry-attorney
 * pair — the backend's own 409 already_requested makes a second attempt
 * meaningless, so the UI shouldn't imply repeating it does anything.
 */
export function RequestConsultationButton({ inquiryId }: { inquiryId: string }) {
  const requestConsultation = useRequestConsultation();

  if (requestConsultation.isSuccess) {
    return (
      <span className="rounded-sm bg-accent-subtle px-3.5 py-1.5 text-body-sm font-medium text-text-primary">
        Requested
      </span>
    );
  }

  const alreadyRequested =
    requestConsultation.error instanceof ApiError &&
    requestConsultation.error.code === "already_requested";

  return (
    <button
      type="button"
      onClick={() => requestConsultation.mutate(inquiryId)}
      disabled={requestConsultation.isPending || alreadyRequested}
      className="rounded-sm bg-accent px-3.5 py-1.5 text-body-sm font-medium text-accent-foreground hover:bg-accent-hover disabled:bg-bg-subtle disabled:text-text-muted disabled:cursor-not-allowed transition-colors focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2 outline-none"
    >
      {alreadyRequested ? "Already requested" : requestConsultation.isPending ? "Requesting…" : "Request Consultation"}
    </button>
  );
}
