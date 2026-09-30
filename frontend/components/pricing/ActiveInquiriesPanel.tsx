"use client";

import Link from "next/link";

import { StatusPill } from "@/components/feed/StatusPill";
import { Skeleton } from "@/components/ui/skeleton";
import { useInquiryUpgradeCheckout } from "@/hooks/useForumBilling";
import { useMyInquiries } from "@/hooks/useInquiries";

/**
 * "Your Active Inquiries" — Scope Revision 2 §3.1 (AgentGuide/newscoperev2.md).
 * New panel on the pricing page for logged-in users, listing every inquiry
 * they've posted with a direct, one-click upgrade path for free-tier ones —
 * client's own wording ("upgrade instantly without hunting for it") decided
 * this to be a direct action straight to Stripe Checkout, no confirmation
 * step in between, reusing the exact same useInquiryUpgradeCheckout() hook
 * already proven working on the inquiry detail page.
 *
 * Reuses useMyInquiries() verbatim (same query key as /account/my-inquiries,
 * so both share one React Query cache entry) rather than a new query —
 * no backend change needed for this panel.
 */
export function ActiveInquiriesPanel() {
  const query = useMyInquiries();
  const inquiryUpgradeCheckout = useInquiryUpgradeCheckout();

  const allItems = query.data?.pages.flatMap((page) => page.items) ?? [];

  return (
    <div className="mx-auto mt-16 max-w-[900px]">
      <h2 className="font-display text-h2 text-text-primary mb-6 text-center sm:text-left">
        Your Active Inquiries
      </h2>

      {query.isLoading && (
        <div className="flex flex-col gap-3" role="status" aria-label="Loading your inquiries">
          {Array.from({ length: 2 }).map((_, i) => (
            <div key={i} className="rounded-md border border-border-default bg-bg-elevated p-4 sm:p-5">
              <Skeleton className="h-5 w-28 rounded-full" />
              <Skeleton className="mt-3 h-5 w-2/3" />
            </div>
          ))}
        </div>
      )}

      {query.isError && (
        <div className="rounded-md border border-danger bg-danger-subtle p-5 text-center">
          <p className="text-body-sm text-text-primary mb-3">Your inquiries didn&apos;t load.</p>
          <button
            type="button"
            onClick={() => query.refetch()}
            className="rounded-sm px-4 py-2 text-body-sm font-medium text-text-primary hover:bg-bg-subtle transition-colors focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2 outline-none"
          >
            Try again
          </button>
        </div>
      )}

      {!query.isLoading && !query.isError && allItems.length === 0 && (
        <div className="rounded-md border border-dashed border-border-strong bg-bg-elevated py-12 text-center px-6">
          <p className="text-body-sm text-text-secondary">
            You haven&apos;t posted an inquiry yet.
          </p>
          <Link
            href="/inquiries/new"
            className="mt-3 inline-block rounded-sm bg-accent px-4 py-2 text-body-sm font-medium text-accent-foreground transition-colors hover:bg-accent-hover focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2 outline-none"
          >
            Post your first inquiry
          </Link>
        </div>
      )}

      {!query.isLoading && !query.isError && allItems.length > 0 && (
        <div className="flex flex-col gap-3">
          {allItems.map((inquiry) => (
            <div
              key={inquiry.id}
              className="flex flex-col gap-3 rounded-md border border-border-default bg-bg-elevated p-4 sm:flex-row sm:items-center sm:justify-between sm:p-5"
            >
              <div className="min-w-0 flex-1">
                <div className="flex items-center gap-2">
                  <StatusPill status={inquiry.statusTag} />
                </div>
                <Link
                  href={`/inquiries/${inquiry.id}`}
                  className="mt-2 block text-body font-medium text-text-primary hover:text-accent transition-colors rounded-sm focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2 outline-none [overflow-wrap:anywhere]"
                >
                  {inquiry.title}
                </Link>
              </div>

              <div className="shrink-0">
                {inquiry.tier === "free" ? (
                  <button
                    type="button"
                    onClick={() => inquiryUpgradeCheckout.mutate(inquiry.id)}
                    disabled={inquiryUpgradeCheckout.isPending}
                    className="w-full rounded-sm bg-accent px-4 py-2 text-body-sm font-medium text-accent-foreground transition-colors hover:bg-accent-hover disabled:cursor-not-allowed disabled:opacity-60 focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2 outline-none sm:w-auto"
                  >
                    {inquiryUpgradeCheckout.isPending ? "Redirecting…" : "Upgrade This Post ($2.99)"}
                  </button>
                ) : (
                  <span className="text-body-sm font-medium text-text-muted">Upgraded</span>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
