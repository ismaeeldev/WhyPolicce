"use client";

import { CheckCircle2, XCircle } from "lucide-react";
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
import { useAdminReports, useReviewReport, type AdminReport } from "@/hooks/useAdmin";
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
  const query = useAdminReports();
  const reviewReport = useReviewReport();
  const showToast = useToastStore((s) => s.show);

  const handleDecision = (reportId: string, decision: "resolved" | "dismissed") => {
    reviewReport.mutate(
      { reportId, decision },
      {
        onSuccess: () => {
          showToast(decision === "resolved" ? "Report resolved" : "Report dismissed");
          setSelected(null);
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
          className="rounded-sm border border-border-strong px-3.5 py-2 text-body-sm font-medium text-text-primary transition-colors hover:bg-bg-subtle disabled:opacity-50 focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2 outline-none"
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
        query.data.items.length === 0 ? (
          <div className="rounded-md border border-dashed border-border-strong bg-bg-elevated py-16 text-center px-6">
            <p className="text-body-sm text-text-secondary">No open reports.</p>
          </div>
        ) : (
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
                {query.data.items.map((report) => (
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
                        onClick={() => setSelected(report)}
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
        )
      )}

      <Dialog open={selected !== null} onOpenChange={(open) => !open && setSelected(null)}>
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

              <div className="mt-4 flex items-center gap-2">
                <button
                  type="button"
                  onClick={() => handleDecision(selected.id, "resolved")}
                  disabled={reviewReport.isPending}
                  className="flex flex-1 items-center justify-center gap-1.5 rounded-sm bg-accent px-4 py-2.5 text-body-sm font-medium text-accent-foreground transition-colors hover:bg-accent-hover disabled:opacity-50 focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2 outline-none"
                >
                  <CheckCircle2 className="h-4 w-4" />
                  Resolve
                </button>
                <button
                  type="button"
                  onClick={() => handleDecision(selected.id, "dismissed")}
                  disabled={reviewReport.isPending}
                  className="flex flex-1 items-center justify-center gap-1.5 rounded-sm border border-border-strong px-4 py-2.5 text-body-sm font-medium text-text-primary transition-colors hover:bg-bg-subtle disabled:opacity-50 focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2 outline-none"
                >
                  <XCircle className="h-4 w-4" />
                  Dismiss
                </button>
              </div>
            </>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}
