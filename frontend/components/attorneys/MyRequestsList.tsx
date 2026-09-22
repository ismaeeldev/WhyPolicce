"use client";

import { Check, Clock, X } from "lucide-react";
import Link from "next/link";

import { useMyConsultationRequests, type AttorneyRequestStatus } from "@/hooks/useConsultationRequests";

const dateFormatter = new Intl.DateTimeFormat("en-US", { month: "short", day: "numeric", year: "numeric" });

const STATUS_CONFIG: Record<AttorneyRequestStatus, { label: string; className: string; icon: React.ReactNode }> = {
  pending: {
    label: "Pending",
    className: "bg-bg-subtle text-text-muted",
    icon: <Clock className="h-3 w-3" />,
  },
  accepted: {
    label: "Accepted",
    className: "bg-success/15 text-success",
    icon: <Check className="h-3 w-3" />,
  },
  declined: {
    label: "Declined",
    className: "bg-bg-subtle text-text-muted",
    icon: <X className="h-3 w-3" />,
  },
};

/**
 * "My Requests" — attorney's own past consultation requests (M2.4).
 * Without this, an attorney who requests a consultation has no way to
 * ever find out whether the citizen responded, making the accept/
 * decline endpoint invisible from the attorney's side of the product.
 * Reuses the feed card's compact layout philosophy but as a lighter
 * list row, replacing Follow/Request-Consultation with a status pill
 * (§4.6's badge pattern).
 */
export function MyRequestsList() {
  const { data, isLoading, isError } = useMyConsultationRequests();

  if (isLoading) {
    return (
      <div className="flex flex-col gap-2">
        {Array.from({ length: 3 }).map((_, i) => (
          <div key={i} className="h-16 animate-pulse rounded-sm border border-border-default bg-bg-elevated" />
        ))}
      </div>
    );
  }

  if (isError) {
    return <p className="text-body-sm text-text-muted">Couldn&apos;t load your requests.</p>;
  }

  if (!data || data.items.length === 0) {
    return (
      <p className="text-body-sm text-text-muted">
        You haven&apos;t requested a consultation on any case yet.
      </p>
    );
  }

  return (
    <div className="flex flex-col gap-2">
      {data.items.map((request) => {
        const config = STATUS_CONFIG[request.status];
        return (
          <div
            key={request.id}
            className="flex items-center justify-between gap-3 rounded-sm border border-border-default bg-bg-elevated p-3 transition-colors duration-150 hover:border-border-strong"
          >
            <div className="min-w-0">
              <Link
                href={`/inquiries/${request.inquiry.id}`}
                className="block truncate text-body-sm font-medium text-text-primary hover:text-accent transition-colors rounded-sm focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2 outline-none"
              >
                {request.inquiry.title}
              </Link>
              <p className="text-caption text-text-muted">
                {request.inquiry.city}, {request.inquiry.state} &middot;{" "}
                {dateFormatter.format(new Date(request.createdAt))}
              </p>
            </div>
            <span
              className={`flex shrink-0 items-center gap-1 rounded-full px-2.5 py-0.5 text-caption font-medium ${config.className}`}
            >
              {config.icon}
              {config.label}
            </span>
          </div>
        );
      })}
    </div>
  );
}
