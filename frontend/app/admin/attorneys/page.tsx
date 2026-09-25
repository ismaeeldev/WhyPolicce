"use client";

import { CheckCircle2, ChevronLeft, ChevronRight, XCircle } from "lucide-react";
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
import {
  ADMIN_PAGE_SIZE,
  useAdminAttorneys,
  useVerifyAttorney,
  type AdminAttorney,
  type VerificationStatus,
} from "@/hooks/useAdmin";
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
  const [offset, setOffset] = useState(0);
  const query = useAdminAttorneys(activeTab, offset);
  const verifyAttorney = useVerifyAttorney();
  const showToast = useToastStore((s) => s.show);

  const items = query.data?.items ?? [];
  const total = query.data?.total ?? 0;
  const page = Math.floor(offset / ADMIN_PAGE_SIZE) + 1;
  const pageCount = Math.max(1, Math.ceil(total / ADMIN_PAGE_SIZE));

  // Real bug found during a UI audit: approving/rejecting the last row
  // on a non-first page emptied that page with no way back — the
  // "No {tab} attorneys" empty state rendered instead of the table with
  // no pagination controls at all, stranding the admin (Refresh
  // re-fetched the same now-past-the-end offset; only a tab switch or
  // manual URL edit recovered). Detected during render (not written to
  // state here) and corrected via the mutation's own onSuccess below —
  // the moment we know a decision just landed, not via a generic effect
  // watching every render's data shape.
  const isPastEnd = !query.isLoading && offset > 0 && offset >= total && total > 0;

  // Real gap found during a UI-polish pass: switching tabs used to leave
  // whatever page you were on in the previous tab still selected — e.g.
  // land on page 3 of Pending, switch to Approved, and Approved silently
  // opens on offset 40 instead of its own first page. Reset happens
  // directly in the click handler (a real user action), not an effect
  // watching activeTab — the URL push already re-renders this page with
  // the new tab, so there's nothing left to "synchronize" after the fact.
  const setTab = (tab: VerificationStatus) => {
    setOffset(0);
    router.push(`/admin/attorneys?tab=${tab}`);
  };

  const handleDecision = (userId: string, decision: "approved" | "rejected") => {
    // Only meaningful when this decision moves the row OUT of the
    // currently-filtered tab (e.g. approving a still-Pending row) — a
    // Revoke/Approve-instead action on an already-decided row doesn't
    // shrink this list, so no clamp is needed there.
    const isLastRowOnNonFirstPage =
      selected?.verificationStatus === "pending" && items.length === 1 && offset > 0;
    verifyAttorney.mutate(
      { userId, decision },
      {
        onSuccess: () => {
          showToast(decision === "approved" ? "Attorney approved" : "Attorney rejected");
          setSelected(null);
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
        <h1 className="font-display text-h1 text-text-primary">Attorneys</h1>
        <button
          type="button"
          onClick={() => query.refetch()}
          disabled={query.isFetching}
          className="rounded-sm border border-border-strong px-3.5 py-2 text-body-sm font-medium text-text-primary transition-colors hover:bg-bg-subtle disabled:cursor-not-allowed disabled:opacity-50 focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2 outline-none"
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
        items.length === 0 ? (
          <div className="rounded-md border border-dashed border-border-strong bg-bg-elevated py-16 text-center px-6">
            <p className="text-body-sm text-text-secondary">
              {isPastEnd ? "This page is now empty." : `No ${activeTab} attorneys.`}
            </p>
            {/* Defensive fallback for the class of bug found during a
                UI audit: a decision made elsewhere (another admin, or a
                missed case here) can empty a non-first page with no
                pagination controls rendered to get back — this stays
                reachable even if handleDecision's own clamp above
                doesn't cover the exact scenario. */}
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
                    <th className="px-4 py-2.5 text-caption font-medium uppercase tracking-wide text-text-muted">Email</th>
                    <th className="px-4 py-2.5 text-caption font-medium uppercase tracking-wide text-text-muted">Bar number</th>
                    <th className="px-4 py-2.5 text-caption font-medium uppercase tracking-wide text-text-muted">Jurisdiction</th>
                    <th className="px-4 py-2.5 text-caption font-medium uppercase tracking-wide text-text-muted">Applied</th>
                    <th className="px-4 py-2.5" />
                  </tr>
                </thead>
                <tbody className="divide-y divide-border-default bg-bg-elevated">
                  {items.map((attorney) => (
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

              {/* Real bug found during a state-handling audit: these
                  branches used to key off `activeTab` (the URL's tab
                  state) instead of `selected.verificationStatus` (the
                  actual row's own real status). A fast tab switch —
                  click Pending, click Approved before the fetch
                  settles, open a row — could show "Revoke approval" on
                  an attorney who was actually still pending, since the
                  dialog's own action set followed the label under your
                  cursor, not the data you were looking at. Now derived
                  from the attorney's own field, which can never be
                  stale relative to itself. */}
              {selected.verificationStatus === "pending" && (
                <div className="mt-4 flex items-center gap-2">
                  <button
                    type="button"
                    onClick={() => handleDecision(selected.id, "approved")}
                    disabled={verifyAttorney.isPending}
                    className="flex flex-1 items-center justify-center gap-1.5 rounded-sm bg-accent px-4 py-2.5 text-body-sm font-medium text-accent-foreground transition-colors hover:bg-accent-hover disabled:cursor-not-allowed disabled:opacity-50 focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2 outline-none"
                  >
                    <CheckCircle2 className="h-4 w-4" />
                    {verifyAttorney.isPending && verifyAttorney.variables?.decision === "approved"
                      ? "Approving…"
                      : "Approve"}
                  </button>
                  <button
                    type="button"
                    onClick={() => handleDecision(selected.id, "rejected")}
                    disabled={verifyAttorney.isPending}
                    className="flex flex-1 items-center justify-center gap-1.5 rounded-sm border border-border-strong px-4 py-2.5 text-body-sm font-medium text-text-primary transition-colors hover:bg-bg-subtle disabled:cursor-not-allowed disabled:opacity-50 focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2 outline-none"
                  >
                    <XCircle className="h-4 w-4" />
                    {verifyAttorney.isPending && verifyAttorney.variables?.decision === "rejected"
                      ? "Rejecting…"
                      : "Reject"}
                  </button>
                </div>
              )}

              {selected.verificationStatus !== "pending" && (
                <div className="mt-4 flex items-center gap-2">
                  <button
                    type="button"
                    onClick={() =>
                      handleDecision(
                        selected.id,
                        selected.verificationStatus === "approved" ? "rejected" : "approved",
                      )
                    }
                    disabled={verifyAttorney.isPending}
                    className="w-full rounded-sm border border-border-strong px-4 py-2.5 text-body-sm font-medium text-text-primary transition-colors hover:bg-bg-subtle disabled:cursor-not-allowed disabled:opacity-50 focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2 outline-none"
                  >
                    {verifyAttorney.isPending
                      ? "Saving…"
                      : selected.verificationStatus === "approved"
                        ? "Revoke approval"
                        : "Approve instead"}
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
