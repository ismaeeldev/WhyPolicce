"use client";

import { AlertTriangle, CheckCircle2, Clock, Flag, XCircle } from "lucide-react";
import Link from "next/link";

import { Skeleton } from "@/components/ui/skeleton";
import { useAdminDashboard } from "@/hooks/useAdmin";

const CARDS = [
  {
    key: "pendingAttorneys" as const,
    label: "Pending attorneys",
    icon: Clock,
    href: "/admin/attorneys?tab=pending",
    tone: "text-warning",
  },
  {
    key: "approvedAttorneys" as const,
    label: "Approved attorneys",
    icon: CheckCircle2,
    href: "/admin/attorneys?tab=approved",
    tone: "text-success",
  },
  {
    key: "rejectedAttorneys" as const,
    label: "Rejected attorneys",
    icon: XCircle,
    href: "/admin/attorneys?tab=rejected",
    tone: "text-text-muted",
  },
  {
    key: "openReports" as const,
    label: "Open reports",
    icon: Flag,
    href: "/admin/reports",
    tone: "text-danger",
  },
];

/**
 * Admin dashboard — the landing screen, real aggregate counts from
 * GET /api/v1/admin/dashboard, each card linking straight to the
 * filtered view it summarizes rather than requiring a second click
 * through a tab to get there.
 */
export default function AdminDashboardPage() {
  const { data, isLoading, isError, refetch } = useAdminDashboard();

  return (
    <div className="mx-auto w-full max-w-[1000px]">
      <h1 className="font-display text-h1 text-text-primary mb-6">Dashboard</h1>

      {isError && (
        <div className="rounded-md border border-danger bg-danger-subtle p-5 text-center">
          <p className="text-body-sm text-text-primary mb-3">The dashboard didn&apos;t load.</p>
          <button
            type="button"
            onClick={() => refetch()}
            className="rounded-sm px-4 py-2 text-body-sm font-medium text-text-primary hover:bg-bg-subtle transition-colors focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2 outline-none"
          >
            Try again
          </button>
        </div>
      )}

      {isLoading && (
        <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <Skeleton key={i} className="h-28 w-full rounded-md" />
          ))}
        </div>
      )}

      {!isLoading && !isError && data && (
        <>
          <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
            {CARDS.map((card) => {
              const Icon = card.icon;
              return (
                <Link
                  key={card.key}
                  href={card.href}
                  className="rounded-md border border-border-default bg-bg-elevated p-5 transition-all duration-150 hover:border-border-strong hover:shadow-card focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2 outline-none"
                >
                  <Icon className={`h-5 w-5 ${card.tone}`} strokeWidth={1.75} />
                  <p className="mt-3 font-display text-h1 text-text-primary tabular-nums">
                    {data[card.key]}
                  </p>
                  <p className="mt-1 text-body-sm text-text-secondary">{card.label}</p>
                </Link>
              );
            })}
          </div>

          {/* Real correctness gap found by a production-readiness
              audit: an attorney account can end up with a null
              verification_status (never via normal signup, but
              nothing currently prevents it via a future admin action
              or a manual data fix), invisible to all 3 cards above.
              Only rendered when genuinely non-zero — this is a rare
              data-integrity alert, not permanent dashboard clutter. */}
          {data.unknownStatusAttorneys > 0 && (
            <Link
              href="/admin/attorneys"
              className="mt-4 flex items-center gap-3 rounded-md border border-warning bg-warning-subtle p-4 transition-colors hover:border-warning focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2 outline-none"
            >
              <AlertTriangle className="h-5 w-5 shrink-0 text-warning" strokeWidth={1.75} />
              <p className="text-body-sm text-text-primary">
                {data.unknownStatusAttorneys} attorney{data.unknownStatusAttorneys === 1 ? "" : "s"} with an
                unrecognized status — not counted above. View all attorneys to investigate.
              </p>
            </Link>
          )}
        </>
      )}
    </div>
  );
}
