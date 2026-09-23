"use client";

import { CheckCircle2, XCircle } from "lucide-react";
import { useRouter, useSearchParams } from "next/navigation";
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
import { useAdminAttorneys, useVerifyAttorney, type AdminAttorney, type VerificationStatus } from "@/hooks/useAdmin";
import { useToastStore } from "@/stores/useToastStore";

const TABS: { key: VerificationStatus; label: string }[] = [
  { key: "pending", label: "Pending" },
  { key: "approved", label: "Approved" },
  { key: "rejected", label: "Rejected" },
];

const dateFormatter = new Intl.DateTimeFormat("en-US", { month: "short", day: "numeric", year: "numeric" });

/**
 * Admin attorney review — new admin panel (client's explicit request):
 * Pending/Approved/Rejected tabs, a detail dialog per attorney with the
 * real approve/reject action, production-grade skeleton loading and a
 * real refresh path on every table. Tab state lives in the URL
 * (?tab=pending) so the dashboard's own stat-card links can deep-link
 * straight into the right tab.
 */
export default function AdminAttorneysPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const tabParam = searchParams.get("tab");
  const activeTab: VerificationStatus = TABS.some((t) => t.key === tabParam)
    ? (tabParam as VerificationStatus)
    : "pending";

  const [selected, setSelected] = useState<AdminAttorney | null>(null);
  const query = useAdminAttorneys(activeTab);
  const verifyAttorney = useVerifyAttorney();
  const showToast = useToastStore((s) => s.show);

  const setTab = (tab: VerificationStatus) => {
    router.push(`/admin/attorneys?tab=${tab}`);
  };

  const handleDecision = (userId: string, decision: "approved" | "rejected") => {
    verifyAttorney.mutate(
      { userId, decision },
      {
        onSuccess: () => {
          showToast(decision === "approved" ? "Attorney approved" : "Attorney rejected");
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
        <h1 className="font-display text-h1 text-text-primary">Attorneys</h1>
        <button
          type="button"
          onClick={() => query.refetch()}
          disabled={query.isFetching}
          className="rounded-sm border border-border-strong px-3.5 py-2 text-body-sm font-medium text-text-primary transition-colors hover:bg-bg-subtle disabled:opacity-50 focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2 outline-none"
        >
          {query.isFetching ? "Refreshing…" : "Refresh"}
        </button>
      </div>

      <div className="mb-4 flex items-center gap-1 border-b border-border-default">
        {TABS.map((tab) => (
          <button
            key={tab.key}
            type="button"
            onClick={() => setTab(tab.key)}
            aria-current={activeTab === tab.key ? "page" : undefined}
            className={`relative px-4 py-2.5 text-body-sm font-medium transition-colors focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2 outline-none ${
              activeTab === tab.key ? "text-text-primary" : "text-text-secondary hover:text-text-primary"
            }`}
          >
            {tab.label}
            {activeTab === tab.key && (
              <span className="absolute inset-x-0 -bottom-px h-0.5 bg-accent" />
            )}
          </button>
        ))}
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
          <div className="flex flex-col divide-y divide-border-default" role="status" aria-label="Loading attorneys">
            {Array.from({ length: 5 }).map((_, i) => (
              <div key={i} className="flex items-center gap-4 bg-bg-elevated p-4">
                <Skeleton className="h-4 w-40" />
                <Skeleton className="h-4 w-24" />
                <Skeleton className="h-4 w-28" />
                <Skeleton className="ml-auto h-4 w-20" />
              </div>
            ))}
          </div>
        </div>
      )}

      {!query.isLoading && !query.isError && query.data && (
        query.data.items.length === 0 ? (
          <div className="rounded-md border border-dashed border-border-strong bg-bg-elevated py-16 text-center px-6">
            <p className="text-body-sm text-text-secondary">No {activeTab} attorneys.</p>
          </div>
        ) : (
          <div className="overflow-x-auto rounded-md border border-border-default">
            <table className="w-full min-w-[560px] border-collapse text-left">
              <thead>
                <tr className="border-b border-border-default bg-bg-subtle">
                  <th className="px-4 py-2.5 text-caption font-medium uppercase tracking-wide text-text-muted">Email</th>
                  <th className="px-4 py-2.5 text-caption font-medium uppercase tracking-wide text-text-muted">Bar number</th>
                  <th className="px-4 py-2.5 text-caption font-medium uppercase tracking-wide text-text-muted">Jurisdiction</th>
                  <th className="px-4 py-2.5 text-caption font-medium uppercase tracking-wide text-text-muted">Applied</th>
                  <th className="px-4 py-2.5" />
                </tr>
              </thead>
              <tbody className="divide-y divide-border-default bg-bg-elevated">
                {query.data.items.map((attorney) => (
                  <tr key={attorney.id} className="transition-colors hover:bg-bg-subtle">
                    <td className="px-4 py-3 text-body-sm text-text-primary">{attorney.email}</td>
                    <td className="px-4 py-3 text-body-sm text-text-secondary">{attorney.verifiedBarNo ?? "—"}</td>
                    <td className="px-4 py-3 text-body-sm text-text-secondary">{attorney.barJurisdiction ?? "—"}</td>
                    <td className="px-4 py-3 text-body-sm text-text-secondary tabular-nums">
                      {dateFormatter.format(new Date(attorney.createdAt))}
                    </td>
                    <td className="px-4 py-3 text-right">
                      <button
                        type="button"
                        onClick={() => setSelected(attorney)}
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
        <DialogContent className="bg-bg-elevated rounded-lg max-w-[440px]">
          {selected && (
            <>
              <DialogHeader>
                <DialogTitle className="font-display text-xl">{selected.email}</DialogTitle>
                <DialogDescription className="text-body-sm text-text-secondary">
                  Applied {dateFormatter.format(new Date(selected.createdAt))}
                </DialogDescription>
              </DialogHeader>

              <div className="flex flex-col gap-3 mt-2">
                <div className="rounded-sm border border-border-default bg-bg p-3">
                  <p className="text-caption uppercase tracking-wide text-text-muted mb-0.5">Bar number</p>
                  <p className="text-body-sm text-text-primary">{selected.verifiedBarNo ?? "Not provided"}</p>
                </div>
                <div className="rounded-sm border border-border-default bg-bg p-3">
                  <p className="text-caption uppercase tracking-wide text-text-muted mb-0.5">Jurisdiction</p>
                  <p className="text-body-sm text-text-primary">{selected.barJurisdiction ?? "Not provided"}</p>
                </div>
                <div className="rounded-sm border border-border-default bg-bg p-3">
                  <p className="text-caption uppercase tracking-wide text-text-muted mb-0.5">Status</p>
                  <p className="text-body-sm text-text-primary capitalize">{selected.verificationStatus}</p>
                </div>
              </div>

              {activeTab === "pending" && (
                <div className="mt-4 flex items-center gap-2">
                  <button
                    type="button"
                    onClick={() => handleDecision(selected.id, "approved")}
                    disabled={verifyAttorney.isPending}
                    className="flex flex-1 items-center justify-center gap-1.5 rounded-sm bg-accent px-4 py-2.5 text-body-sm font-medium text-accent-foreground transition-colors hover:bg-accent-hover disabled:opacity-50 focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2 outline-none"
                  >
                    <CheckCircle2 className="h-4 w-4" />
                    Approve
                  </button>
                  <button
                    type="button"
                    onClick={() => handleDecision(selected.id, "rejected")}
                    disabled={verifyAttorney.isPending}
                    className="flex flex-1 items-center justify-center gap-1.5 rounded-sm border border-border-strong px-4 py-2.5 text-body-sm font-medium text-text-primary transition-colors hover:bg-bg-subtle disabled:opacity-50 focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2 outline-none"
                  >
                    <XCircle className="h-4 w-4" />
                    Reject
                  </button>
                </div>
              )}

              {activeTab !== "pending" && (
                <div className="mt-4 flex items-center gap-2">
                  <button
                    type="button"
                    onClick={() => handleDecision(selected.id, activeTab === "approved" ? "rejected" : "approved")}
                    disabled={verifyAttorney.isPending}
                    className="w-full rounded-sm border border-border-strong px-4 py-2.5 text-body-sm font-medium text-text-primary transition-colors hover:bg-bg-subtle disabled:opacity-50 focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2 outline-none"
                  >
                    {activeTab === "approved" ? "Revoke approval" : "Approve instead"}
                  </button>
                </div>
              )}
            </>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}
