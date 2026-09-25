"use client";

import { Flag } from "lucide-react";
import { useState } from "react";

import { ApiError } from "@/lib/api-client";
import { useReportContent } from "@/hooks/useReportContent";
import { useToastStore } from "@/stores/useToastStore";

/**
 * Report/Flag action — forum rebuild, Milestone 2 Step M2.4
 * (WhyPoliceForum_MasterGuide.md). Small ghost-style icon+text button,
 * --text-muted, Lucide flag icon per §5's iconography rule. A minimal
 * inline reason input on click, not a full modal — deliberately
 * lightweight, matching the low-stakes/low-frequency nature of the
 * action. Reuses the existing Toast component/store on success.
 *
 * Real Bug Fix scenario handled explicitly: if the target (inquiry or
 * comment) is deleted by its own author in another tab/session between
 * opening this report flow and submitting it, the backend's own
 * create_report already 404s cleanly for a fabricated/gone target_id
 * (M1.4) — this component surfaces that as a clear inline error rather
 * than crashing or silently succeeding.
 */
export function ReportButton({
  targetType,
  targetId,
}: {
  targetType: "inquiry" | "thread_comment";
  targetId: string;
}) {
  const [open, setOpen] = useState(false);
  const [reason, setReason] = useState("");
  const [error, setError] = useState<string | null>(null);
  const reportMutation = useReportContent();
  const showToast = useToastStore((s) => s.show);

  const handleSubmit = () => {
    if (!reason.trim()) return;
    setError(null);
    reportMutation.mutate(
      { targetType, targetId, reason: reason.trim() },
      {
        onSuccess: () => {
          setOpen(false);
          setReason("");
          showToast("Report submitted");
        },
        onError: (err) => {
          // Real bug found during a state-handling audit: every failure
          // — including a logged-out visitor's real 401 (reading the
          // forum needs no login, so this is a common path to hit this
          // button at all) or a rate-limit 429 — was hardcoded to a
          // 404-flavored "content may have been removed" message. A
          // logged-out user got told to refresh, did, found the
          // content still there, and reasonably concluded the button
          // was broken.
          if (err instanceof ApiError && err.status === 401) {
            setError("Sign in to report content.");
          } else if (err instanceof ApiError && err.status === 404) {
            setError("This content may have been removed. Please refresh and try again.");
          } else {
            setError(err instanceof ApiError ? err.message : "Couldn't submit that report. Try again.");
          }
        },
      },
    );
  };

  if (!open) {
    return (
      <button
        type="button"
        onClick={() => setOpen(true)}
        className="flex items-center gap-1 rounded-sm px-2 py-1.5 text-caption text-text-muted transition-colors hover:bg-bg-subtle hover:text-text-primary focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2 outline-none"
      >
        <Flag className="h-3 w-3" />
        Report
      </button>
    );
  }

  return (
    <div className="flex flex-col gap-1.5 rounded-sm border border-border-default bg-bg-elevated p-2.5">
      <input
        autoFocus
        value={reason}
        onChange={(e) => setReason(e.target.value)}
        placeholder="Why are you reporting this?"
        className="h-8 w-full rounded-sm border border-border-default bg-bg px-2.5 text-caption text-text-primary outline-none focus:border-accent"
      />
      {error && <p className="text-caption text-danger">{error}</p>}
      <div className="flex items-center gap-2">
        <button
          type="button"
          onClick={handleSubmit}
          disabled={!reason.trim() || reportMutation.isPending}
          className="rounded-sm bg-accent px-2.5 py-1 text-caption font-medium text-accent-foreground hover:bg-accent-hover disabled:opacity-50 disabled:cursor-not-allowed transition-colors focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2 outline-none"
        >
          Submit report
        </button>
        <button
          type="button"
          onClick={() => {
            setOpen(false);
            setReason("");
            setError(null);
          }}
          className="text-caption text-text-muted hover:text-text-primary transition-colors rounded-sm focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2 outline-none"
        >
          Cancel
        </button>
      </div>
    </div>
  );
}
