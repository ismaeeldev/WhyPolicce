"use client";

import { CheckCircle2, ChevronLeft, ChevronRight, XCircle } from "lucide-react";
import { useState } from "react";

import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Skeleton } from "@/components/ui/skeleton";
import { ApiError } from "@/lib/api-client";
import { ADMIN_PAGE_SIZE, useAdminReports, useReviewReport, type AdminReport } from "@/hooks/useAdmin";
import { useToastStore } from "@/stores/useToastStore";

const dateFormatter = new Intl.DateTimeFormat("en-US", { month: "short", day: "numeric", year: "numeric" });

function targetPreview(report: AdminReport): string {
  if (report.target === null) {
    return "This content was deleted by its author.";
  }
  if ("title" in report.target) {
    return report.target.title;
  }
  return report.target.body;
}

/**
 * Admin report review — new admin panel (client's explicit request).
 * Only ever lists OPEN reports (the backend endpoint's own scope) —
 * a resolved/dismissed report leaves this list the moment it's
 * decided, since re-invalidating ["admin","reports"] after a review
 * refetches this exact query.
 */
export default function AdminReportsPage() {
  const [selected, setSelected] = useState<AdminReport | null>(null);
  const [confirmingDismiss, setConfirmingDismiss] = useState(false);
  const [offset, setOffset] = useState(0);
  const query = useAdminReports(offset);
  const reviewReport = useReviewReport();
  const showToast = useToastStore((s) => s.show);

  const items = query.data?.items ?? [];
  const total = query.data?.total ?? 0;
  const page = Math.floor(offset / ADMIN_PAGE_SIZE) + 1;
  const pageCount = Math.max(1, Math.ceil(total / ADMIN_PAGE_SIZE));

  // Real bug found during a UI audit (same fix as admin/attorneys):
  // resolving/dismissing the last report on a non-first page emptied
  // that page with no way back — this list only ever shows OPEN
  // reports, so every decision here removes the row, unlike the
  // attorneys page where only some decisions do.
  const isPastEnd = !query.isLoading && offset > 0 && offset >= total && total > 0;

  const handleDecision = (reportId: string, decision: "resolved" | "dismissed") => {
    const isLastRowOnNonFirstPage = items.length === 1 && offset > 0;
    reviewReport.mutate(
      { reportId, decision },
      {
        onSuccess: () => {
          showToast(decision === "resolved" ? "Report resolved" : "Report dismissed");
          setSelected(null);
          setConfirmingDismiss(false);
          if (isLastRowOnNonFirstPage) {
            setOffset((o) => Math.max(0, o - ADMIN_PAGE_SIZE));
          }
        },
        onError: (err) => {
          showToast(err instanceof ApiError ? err.message : "Couldn't save that decision. Try again.");
        },
      },
    );
  };

  return (
    <div className="mx-auto w-full max-w-[1000px]">
      <div className="mb-6 flex items-center justify-between gap-3">
        <h1 className="font-display text-h1 text-text-primary">Reports</h1>
        <button
          type="button"
          onClick={() => query.refetch()}
          disabled={query.isFetching}
          className="rounded-sm border border-border-strong px-3.5 py-2 text-body-sm font-medium text-text-primary transition-colors hover:bg-bg-subtle disabled:cursor-not-allowed disabled:opacity-50 focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2 outline-none"
        >
          {query.isFetching ? "Refreshing…" : "Refresh"}
        </button>
      </div>

      {query.isError && (
        <div className="rounded-md border border-danger bg-danger-subtle p-5 text-center">
          <p className="text-body-sm text-text-primary mb-3">This list didn&apos;t load.</p>
          <button
            type="button"
            onClick={() => query.refetch()}
            className="rounded-sm px-4 py-2 text-body-sm font-medium text-text-primary hover:bg-bg-subtle transition-colors focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2 outline-none"
          >
            Try again
          </button>
        </div>
      )}

      {query.isLoading && (
        <div className="overflow-hidden rounded-md border border-border-default">
          <div className="flex flex-col divide-y divide-border-default" role="status" aria-label="Loading reports">
            {Array.from({ length: 5 }).map((_, i) => (
              <div key={i} className="flex items-center gap-4 bg-bg-elevated p-4">
                <Skeleton className="h-4 w-20" />
                <Skeleton className="h-4 w-64" />
                <Skeleton className="ml-auto h-4 w-20" />
              </div>
            ))}
          </div>
        </div>
      )}

      {!query.isLoading && !query.isError && query.data && (
        items.length === 0 ? (
          <div className="rounded-md border border-dashed border-border-strong bg-bg-elevated py-16 text-center px-6">
            <p className="text-body-sm text-text-secondary">
              {isPastEnd ? "This page is now empty." : "No open reports."}
            </p>
            {isPastEnd && (
              <button
                type="button"
                onClick={() => setOffset(0)}
                className="mt-3 rounded-sm border border-border-strong px-4 py-2 text-body-sm font-medium text-text-primary transition-colors hover:bg-bg-subtle focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2 outline-none"
              >
                Back to page 1
              </button>
            )}
          </div>
        ) : (
          <>
            <div className="overflow-x-auto rounded-md border border-border-default">
              <table className="w-full min-w-[560px] border-collapse text-left">
                <thead>
                  <tr className="border-b border-border-default bg-bg-subtle">
                    <th className="px-4 py-2.5 text-caption font-medium uppercase tracking-wide text-text-muted">Type</th>
                    <th className="px-4 py-2.5 text-caption font-medium uppercase tracking-wide text-text-muted">Reason</th>
                    <th className="px-4 py-2.5 text-caption font-medium uppercase tracking-wide text-text-muted">Filed</th>
                    <th className="px-4 py-2.5" />
                  </tr>
                </thead>
                <tbody className="divide-y divide-border-default bg-bg-elevated">
                  {items.map((report) => (
                    <tr key={report.id} className="transition-colors hover:bg-bg-subtle">
                      <td className="px-4 py-3 text-body-sm text-text-primary capitalize">
                        {report.targetType === "thread_comment" ? "Comment" : "Inquiry"}
                      </td>
                      <td className="px-4 py-3 text-body-sm text-text-secondary truncate max-w-xs">{report.reason}</td>
                      <td className="px-4 py-3 text-body-sm text-text-secondary tabular-nums">
                        {dateFormatter.format(new Date(report.createdAt))}
                      </td>
                      <td className="px-4 py-3 text-right">
                        <button
                          type="button"
                          onClick={() => {
                          setSelected(report);
                          setConfirmingDismiss(false);
                        }}
                          className="rounded-sm px-3 py-1.5 text-body-sm font-medium text-accent hover:bg-accent-subtle transition-colors focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2 outline-none"
                        >
                          View
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <div className="mt-3 flex items-center justify-between text-caption text-text-muted">
              <span>
                Showing {offset + 1}–{Math.min(offset + items.length, total)} of {total}
              </span>
              <div className="flex items-center gap-1">
                <button
                  type="button"
                  onClick={() => setOffset((o) => Math.max(0, o - ADMIN_PAGE_SIZE))}
                  disabled={offset === 0 || query.isFetching}
                  aria-label="Previous page"
                  className="flex items-center gap-1 rounded-sm border border-border-strong px-2.5 py-1.5 text-body-sm font-medium text-text-primary transition-colors hover:bg-bg-subtle disabled:cursor-not-allowed disabled:opacity-50 focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2 outline-none"
                >
                  <ChevronLeft className="h-3.5 w-3.5" />
                </button>
                <span className="px-2 tabular-nums">
                  Page {page} of {pageCount}
                </span>
                <button
                  type="button"
                  onClick={() => setOffset((o) => o + ADMIN_PAGE_SIZE)}
                  disabled={offset + ADMIN_PAGE_SIZE >= total || query.isFetching}
                  aria-label="Next page"
                  className="flex items-center gap-1 rounded-sm border border-border-strong px-2.5 py-1.5 text-body-sm font-medium text-text-primary transition-colors hover:bg-bg-subtle disabled:cursor-not-allowed disabled:opacity-50 focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2 outline-none"
                >
                  <ChevronRight className="h-3.5 w-3.5" />
                </button>
              </div>
            </div>
          </>
        )
      )}

      <Dialog
        open={selected !== null}
        onOpenChange={(open) => {
          if (!open) {
            setSelected(null);
            setConfirmingDismiss(false);
          }
        }}
      >
        <DialogContent className="bg-bg-elevated rounded-lg max-w-[480px]">
          {selected && (
            <>
              <DialogHeader>
                <DialogTitle className="font-display text-xl capitalize">
                  Reported {selected.targetType === "thread_comment" ? "comment" : "inquiry"}
                </DialogTitle>
                <DialogDescription className="text-body-sm text-text-secondary">
                  Filed {dateFormatter.format(new Date(selected.createdAt))}
                </DialogDescription>
              </DialogHeader>

              <div className="flex flex-col gap-3 mt-2">
                <div className="rounded-sm border border-border-default bg-bg p-3">
                  <p className="text-caption uppercase tracking-wide text-text-muted mb-0.5">Reason</p>
                  <p className="text-body-sm text-text-primary [overflow-wrap:anywhere]">{selected.reason}</p>
                </div>
                <div className="rounded-sm border border-border-default bg-bg p-3">
                  <p className="text-caption uppercase tracking-wide text-text-muted mb-0.5">Reported content</p>
                  <p className="text-body-sm text-text-primary [overflow-wrap:anywhere]">{targetPreview(selected)}</p>
                </div>
              </div>

              {/* Real gap found during a state-handling audit: both
                  buttons shared reviewReport.isPending with static
                  labels — clicking Resolve on a slow connection greyed
                  out BOTH buttons with no indication which one was
                  actually processing. Now shows which specific decision
                  is in flight via mutation.variables, matching every
                  other pending-state button in this codebase. */}
              <div className="mt-4 flex items-center gap-2">
                {confirmingDismiss ? (
                  // Real gap found during a UI audit: once confirming, the
                  // only way to back out was closing the whole dialog —
                  // this swaps the Resolve slot for a real Cancel so a
                  // misclick on "Dismiss" doesn't force a full dialog
                  // reopen just to change your mind.
                  <button
                    type="button"
                    onClick={() => setConfirmingDismiss(false)}
                    disabled={reviewReport.isPending}
                    className="flex flex-1 items-center justify-center gap-1.5 rounded-sm border border-border-strong px-4 py-2.5 text-body-sm font-medium text-text-primary transition-colors hover:bg-bg-subtle disabled:cursor-not-allowed disabled:opacity-50 focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2 outline-none"
                  >
                    Cancel
                  </button>
                ) : (
                  <button
                    type="button"
                    onClick={() => handleDecision(selected.id, "resolved")}
                    disabled={reviewReport.isPending}
                    className="flex flex-1 items-center justify-center gap-1.5 rounded-sm bg-accent px-4 py-2.5 text-body-sm font-medium text-accent-foreground transition-colors hover:bg-accent-hover disabled:cursor-not-allowed disabled:opacity-50 focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2 outline-none"
                  >
                    <CheckCircle2 className="h-4 w-4" />
                    {reviewReport.isPending && reviewReport.variables?.decision === "resolved"
                      ? "Resolving…"
                      : "Resolve"}
                  </button>
                )}
                {/* Dismiss is final on the backend (no re-review once
                    decided), so a misclick can't be undone — require a
                    second click before it fires. */}
                {confirmingDismiss ? (
                  <button
                    type="button"
                    onClick={() => handleDecision(selected.id, "dismissed")}
                    disabled={reviewReport.isPending}
                    className="flex flex-1 items-center justify-center gap-1.5 rounded-sm border border-danger bg-danger-subtle px-4 py-2.5 text-body-sm font-medium text-text-primary transition-colors hover:bg-danger-subtle/80 disabled:cursor-not-allowed disabled:opacity-50 focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2 outline-none"
                  >
                    <XCircle className="h-4 w-4" />
                    {reviewReport.isPending && reviewReport.variables?.decision === "dismissed"
                      ? "Dismissing…"
                      : "Confirm dismiss?"}
                  </button>
                ) : (
                  <button
                    type="button"
                    onClick={() => setConfirmingDismiss(true)}
                    disabled={reviewReport.isPending}
                    className="flex flex-1 items-center justify-center gap-1.5 rounded-sm border border-border-strong px-4 py-2.5 text-body-sm font-medium text-text-primary transition-colors hover:bg-bg-subtle disabled:cursor-not-allowed disabled:opacity-50 focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2 outline-none"
                  >
                    <XCircle className="h-4 w-4" />
                    Dismiss
                  </button>
                )}
              </div>
            </>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}
